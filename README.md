# 学マス声優节目日历 → 自动更新的 ICS

分析依据：2026-11-01 上传的完整网站 HAR 文件，以及其中的 `main-Birmlctr.js`。

确认来源：`https://gakusei-cheer-portal.web.app/calendar`。网站通过 Firebase Firestore 项目 `my-schedule-pwa-121d0` 的公开日程集合 `schedules` 加载记录，含 `title`, `start`, `end`, `selectedCasts`, `broadcastType`, `linkUrl`, `allDay`, `id` 等字段。网站开启 App Check；本项目不会复制任何 HAR 中的 token 或尝试绕过验证。

## 重要：验证状态

**这是依据 HAR 构建的可执行方案，尚未在 GitHub Actions 上验证。** 当前构建环境无法对源站进行实时网络请求。应用脚本可能随站点更新而改变；部分无头浏览器可能无法通过 App Check。GitHub Actions 若失败，必须查看日志、修订方案，不应视为已经成功订阅。

## 如何部署

1. 在 GitHub 建立 **Public** 仓库，例如 `gakusei-calendar-ics`。
2. 把本文件夹内**所有内容**上传到仓库根目录，包括隐藏目录 `.github/workflows/refresh.yml`。请不要上传 HAR 文件。
3. 进入 GitHub 仓库 → **Settings → Actions → General → Workflow permissions**，允许 **Read and write permissions**（若可用），否则使用具有内容写入权限的工作流配置。
4. 在 **Actions → Refresh ICS subscription → Run workflow** 手动启动第一次更新。
5. 进入该次运行记录，确认输出 `Wrote calendar.ics: N current/future events`，以及仓库根目录生成了 `calendar.ics`。
6. 在 **Settings → Pages → Build and deployment** 选择 **Deploy from a branch**，Branch 选 `main`，Folder 选 `/ (root)`，保存；如果默认分支不是 `main`，使用实际分支。
7. 订阅 URL：`https://YOUR_GITHUB_USERNAME.github.io/gakusei-calendar-ics/calendar.ics`（如果仓库名称不同，换成实际名称）。确认浏览器能打开并显示 `BEGIN:VCALENDAR` 才能订阅。
8. 在 Google Calendar 网页版 → 其他日历 → `+` → **通过网址添加**，粘贴 ICS URL。此方式是订阅，**不是**一次性导入；Google 自身刷新周期不可控。

GitHub Actions 在每小时第 7 分钟尝试更新（cron 在 UTC 运行），实际启动可能会延迟、跳过，定时工作流也可能因仓库长期不活跃而暂停。执行失败时，旧文件会保留。

## 本地测试

需要 Python 3.10+（建议 3.12）：

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m unittest discover -s tests -v
python update_calendar.py --output calendar.ics
```

如果抓取失败，可用可见浏览器观察原因：

```bash
python update_calendar.py --visible
```

`--visible` 适合 Windows 的本地桌面环境，不适合 GitHub Actions 无桌面 Linux。

## 运行原理与边界

本项目仅将源网站 JavaScript 的 `loadAllScheduleEvents` 函数和共享数据数组暴露给本次浏览器进程，随后通过页面自身 Firebase 客户端读取 `schedules`。所有请求仍经过源站原本的 App Check 和 Firestore 权限检查。没有使用 HAR 中的 App Check token 或 API key。

- 使用 `Asia/Tokyo` 解读网站的无时区日期文本（如 `2026-11-01T19:00`），ICS 写为 UTC，日历应用按用户时区显示。
- 包含日本时区“今天”开始或仍跨越今天的活动。网站的明日/未来活动如源数据库里有，也会提取。
- 全天活动的 `DTEND` 使用 RFC 5545 的次日独占格式。
- 对有结束时间的节目如实写入；结束时间缺失时不猜测长度。
- 固定 `UID` 根据原数据库 ID 生成，避免重复；源站删除的事件会从下次更新的 ICS 中消失（实际订阅客户端如何处理取消依赖客户端）。
- 不能保证网站维护者提供的每条活动都准确或全部处于公开访问权限。
- 本项目不包含自行破解 Firebase App Check 的任何机制。若源站限制自动化，请停止此方式并联系站点维护者申请官方公开日历 API 或 ICS。
- 为避免错误清空订阅，抓取失败或当前和未来事件为零时不覆盖旧文件。这也意味着正常情况下未来活动确实为零时，会保留旧内容，需人工审查。

## 常见报错

- `Website JS bundle has changed`: 网站构建后函数签名改变。需要根据更新后的公开页面 JS 调整 `BRIDGE_MARKER` 和 `BRIDGE_REPLACEMENT`。
- `Site returned no schedule data` 或 Firestore permission/app-check 错误：浏览器验证未成功或源站改了权限。查看 Actions 日志；不能用过期 HAR token 解决。
- `Page wait_for_function timeout`: 无法加载公开网站、浏览器反自动化检查阻拦，或者桥接 marker 变化。
- 订阅链接 404：首次 Actions 未成功、Pages 未启用、分支/仓库名不匹配。

该项目与原站无关联，请尊重网站管理员的数据使用政策和访问频率。
