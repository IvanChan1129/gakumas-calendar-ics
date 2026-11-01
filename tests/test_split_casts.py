import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from split_casts import split, unfold_lines, get_prop, extract_casts, parse_date_prop, is_current_or_future


class SplitTests(unittest.TestCase):
    def test_parsing(self):
        long = 'DESCRIPTION:出演者: 花岩香奈、伊藤舞音\\n配信種別: 配信'
        physical = long[:33] + '\r\n ' + long[33:]
        component = unfold_lines(physical)
        self.assertEqual(extract_casts(component), ['花岩香奈', '伊藤舞音'])
        self.assertEqual(parse_date_prop(['DTSTART:20261101T010000Z'], 'DTSTART'), date(2026, 11, 1))
        self.assertTrue(is_current_or_future(['DTSTART;VALUE=DATE:20261031','DTEND;VALUE=DATE:20261102'], date(2026, 11, 1)))

    def test_outputs_and_shared_event(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'calendar.ics'
            source.write_text('''BEGIN:VCALENDAR\nVERSION:2.0\nCALSCALE:GREGORIAN\nX-WR-CALNAME:学マス全員\nBEGIN:VEVENT\nUID:evt-1@site\nDTSTART:20261201T100000Z\nSUMMARY:みんなの番組\nDESCRIPTION:出演者: 花岩香奈、伊藤舞音\\n出典: https://example.org\nEND:VEVENT\nBEGIN:VEVENT\nUID:evt-2@site\nDTSTART;VALUE=DATE:20261202\nDTEND;VALUE=DATE:20261203\nSUMMARY:誕生日\nDESCRIPTION:出典: https://example.org\nEND:VEVENT\nBEGIN:VEVENT\nUID:evt-3@site\nDTSTART:20250101T000000Z\nSUMMARY:昔の番組\nDESCRIPTION:出演者: 花岩香奈\nEND:VEVENT\nEND:VCALENDAR\n''', encoding='utf-8')
            out = root / 'casts'
            manifest = split(source, out, base_url='https://example.github.io/test', today=date(2026,11,1))
            self.assertEqual(len(manifest), 2)
            self.assertEqual({x['name'] for x in manifest}, {'花岩香奈', '伊藤舞音'})
            for item in manifest:
                b = (out / item['file']).read_bytes()
                self.assertEqual(b.count(b'BEGIN:VEVENT'), 1)
                self.assertTrue(b.startswith(b'BEGIN:VCALENDAR\r\n'))
                self.assertIn(b'UID:evt-1@site', b)
                self.assertTrue(all(len(line) <= 75 for line in b.split(b'\r\n')))
            self.assertTrue((out/'index.html').exists())
            self.assertTrue((out/'index.json').exists())

    def test_existing_cast_has_stable_empty_calendar(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'calendar.ics'
            source.write_text('BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:evt\nDTSTART;VALUE=DATE:20261201\nSUMMARY:配信\nDESCRIPTION:出演者: 花岩香奈\nEND:VEVENT\nEND:VCALENDAR\n', encoding='utf-8')
            out = root / 'casts'
            first = split(source, out, base_url='https://example.org', today=date(2026, 11, 1))
            second = split(source, out, base_url='https://example.org', today=date(2027, 1, 1))
            self.assertEqual(first[0]['file'], second[0]['file'])
            self.assertEqual(second[0]['count'], 0)
            self.assertEqual((out / first[0]['file']).read_text().count('BEGIN:VEVENT'), 0)

    def test_no_cast_does_not_overwrite_old(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            out = root/'casts';out.mkdir();(out/'keep.txt').write_text('saved')
            (root/'calendar.ics').write_text('BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR\n')
            with self.assertRaisesRegex(ValueError, '没有找到'):
                split(root/'calendar.ics', out, base_url='https://example.org', today=date(2026,11,1))
            self.assertEqual((out/'keep.txt').read_text(), 'saved')

if __name__ == '__main__': unittest.main()
