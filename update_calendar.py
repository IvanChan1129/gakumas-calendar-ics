#!/usr/bin/env python3
"""Use the public site's normal date-filtered queries to build an ICS feed.

The script does not bypass App Check or Firestore security rules.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import quote

SITE = "https://gakusei-cheer-portal.web.app/calendar"
JST = ZoneInfo("Asia/Tokyo")
UTC = timezone.utc


def escape_ics(value: object) -> str:
    """Escape an iCalendar TEXT value (RFC 5545)."""
    return (str(value).replace("\\", "\\\\")
            .replace("\r\n", "\n").replace("\r", "\n")
            .replace("\n", "\\n").replace(",", "\\,")
            .replace(";", "\\;"))


def fold_ics(line: str) -> str:
    """Fold lines at 75 octets without splitting UTF-8 code points."""
    result = []
    current = ""
    size = 0
    for char in line:
        b = len(char.encode("utf-8"))
        if size + b > 75:
            result.append(current)
            current = " " + char
            size = 1 + b
        else:
            current += char
            size += b
    result.append(current)
    return "\r\n".join(result)


def parse_date(value: object):
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(s)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=JST)
        return parsed.astimezone(JST)
    except ValueError:
        return None


def date_only(value: object):
    parsed = parse_date(value)
    return parsed.date() if parsed else None


def ics_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def clean_url(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip() if re.match(r"^https?://", value.strip(), re.I) else ""


def serialize_events(events: list[dict], *, today: date | None = None, now: datetime | None = None) -> tuple[bytes, int]:
    today = today or datetime.now(JST).date()
    now = now or datetime.now(UTC)
    stamp = ics_utc(now)
    output = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Gakusei Cheer Portal ICS Bridge//ZH",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:" + escape_ics("学マス声優番組スケジュール"),
        "X-WR-TIMEZONE:Asia/Tokyo",
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
    ]
    unique = set()
    used = 0
    for event in events:
        if not isinstance(event, dict) or not event.get("start"):
            continue
        start = parse_date(event["start"])
        if start is None:
            continue
        all_day = bool(event.get("allDay", False))
        end = parse_date(event.get("end"))
        if all_day:
            start_date = start.date()
            end_date = (end.date() if end else start_date)
            # Mirrors the site's all-day normalization: an end equal to start
            # represents a one-day event. Other end dates are exclusive.
            if end_date <= start_date:
                end_date = start_date + timedelta(days=1)
            if end_date <= today:
                continue
        elif start.date() < today and (end is None or end.date() < today):
            continue
        elif start.date() >= today:
            pass
        if not all_day and end is not None and end < start:
            end = None  # Malformed end: omit DTEND rather than invent a duration.

        doc_id = str(event.get("id") or "")
        if not doc_id:
            doc_id = hashlib.sha256(json.dumps(event, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
        uid = quote(doc_id, safe="~()*! .'".replace(" ", "")) + "@gakusei-cheer-portal.web.app"
        if uid in unique:
            continue
        unique.add(uid)
        title = str(event.get("title") or "（無題）")
        casts = event.get("selectedCasts") or []
        lines = []
        if isinstance(casts, list) and casts:
            lines.append("出演者: " + "、".join(str(c) for c in casts if c))
        kind = event.get("broadcastType")
        if kind:
            lines.append("配信種別: " + str(kind))
        url = clean_url(event.get("linkUrl"))
        lines.append("出典: " + SITE)
        output.extend(["BEGIN:VEVENT", "UID:" + uid, "DTSTAMP:" + stamp,
                       "SUMMARY:" + escape_ics(title)])
        if all_day:
            output.extend(["DTSTART;VALUE=DATE:" + start_date.strftime("%Y%m%d"),
                           "DTEND;VALUE=DATE:" + end_date.strftime("%Y%m%d")])
        else:
            output.append("DTSTART:" + ics_utc(start))
            if end is not None and end > start:
                output.append("DTEND:" + ics_utc(end))
        output.append("DESCRIPTION:" + escape_ics("\n".join(lines)))
        if url:
            output.append("URL:" + url)
        else:
            output.append("URL:" + SITE)
        output.append("END:VEVENT")
        used += 1
    output.append("END:VCALENDAR")
    content = "\r\n".join(fold_ics(line) for line in output) + "\r\n"
    return content.encode("utf-8"), used


def fetch_events(*, visible: bool = False, months: int = 18) -> list[dict]:
    """Read the original site's module after its initial server query finishes.

    No bundle replacement, credential copying, or security-check changes.
    Any denied query aborts the export instead of publishing partial results.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not visible)
        context = browser.new_context(locale="ja-JP", timezone_id="Asia/Tokyo")
        page = context.new_page()
        errors = []
        ready = {"server": False}

        def on_console(msg):
            message = msg.text
            if "サーバーの最新データで更新しました" in message:
                ready["server"] = True
            if msg.type == "error" and any(word in message for word in (
                "Firestore", "FirebaseError", "permission-denied", "AppCheck", "appCheck")):
                errors.append(message[:800])

        page.on("console", on_console)
        try:
            print("Stage 1: loading the unmodified calendar page", flush=True)
            page.goto(SITE, wait_until="domcontentloaded", timeout=60000)
            import time as clock
            deadline = clock.monotonic() + 60
            while not ready["server"]:
                if errors:
                    raise RuntimeError("Initial website query failed: " + errors[-1])
                if clock.monotonic() >= deadline:
                    raise RuntimeError("No confirmed initial server response within 60 seconds")
                page.wait_for_timeout(250)
            print("Stage 1: normal website server query succeeded", flush=True)
            page.evaluate(r"""async () => {
                const script = [...document.querySelectorAll('script[type="module"][src]')]
                    .find(el => /\/assets\/main-[^/]+\.js(?:\?.*)?$/.test(el.src));
                if (!script) throw Error('Website main module not found');
                const app = await import(script.src);
                if (typeof app.i !== 'function') throw Error('Website module export changed');
                const state = app.i();
                if (!Array.isArray(state.events?.value) || typeof state.loadVisibleMonths !== 'function')
                    throw Error('Website calendar state changed');
                window.__ICS_READ_STATE__ = state;
            }""")
            # One preceding month retains ongoing events that began last month.
            for offset in range(-1, months):
                print(f"Stage 2: reading month offset {offset}", flush=True)
                page.evaluate("""async offset => {
                    const state = window.__ICS_READ_STATE__;
                    const now = new Date();
                    const month = new Date(now.getFullYear(), now.getMonth() + offset, 1);
                    await state.loadVisibleMonths(month, month);
                }""", offset)
                if errors:
                    raise RuntimeError(f"Month offset {offset} failed: " + errors[-1])
            events = page.evaluate("JSON.parse(JSON.stringify(window.__ICS_READ_STATE__.events.value))")
            if not isinstance(events, list) or not events:
                raise RuntimeError("No schedule data; preserving previous calendar")
            print(f"Stage 2: received {len(events)} source events", flush=True)
            return events
        finally:
            context.close()
            browser.close()


def main():
    parser = argparse.ArgumentParser(description="Refresh the public Gakusei Cheer ICS subscription")
    parser.add_argument("--output", default="calendar.ics")
    parser.add_argument("--visible", action="store_true", help="Open Chromium UI for troubleshooting")
    parser.add_argument("--months", type=int, default=18, help="Rolling months to query, default 18")
    parser.add_argument("--from-json", help="Offline test input: public event objects as a JSON array")
    args = parser.parse_args()
    try:
        if args.from_json:
            events = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        else:
            if not 1 <= args.months <= 120:
                parser.error("--months must be 1 to 120")
            events = fetch_events(visible=args.visible, months=args.months)
        data, count = serialize_events(events)
        if count == 0:
            raise RuntimeError("No today/future events found; refuse to overwrite existing calendar")
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            old = output.read_text(encoding="utf-8")
            old_count = old.count("BEGIN:VEVENT")
            if old_count >= 12 and count < old_count * 0.45:
                raise RuntimeError(f"Event count dropped from {old_count} to {count}; refusing replacement")
        temp = output.with_suffix(output.suffix + ".tmp")
        temp.write_bytes(data)
        temp.replace(output)
        print(f"Wrote {output}: {count} current/future events, {len(data):,} bytes")
    except Exception as exc:
        print(f"Update failed: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
