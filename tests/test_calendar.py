import unittest
from datetime import date, datetime, timezone
from update_calendar import serialize_events, fold_ics

class TestCalendar(unittest.TestCase):
    def test_japan_time_and_today_filter(self):
        fixtures = [
            {'id':'a','title':'架空のテストイベント','start':'2026-11-01T19:00','end':'2026-11-01T20:00','selectedCasts':['テスト'],'broadcastType':'live'},
            {'id':'old','title':'Yesterday','start':'2026-10-31T19:00','end':'2026-10-31T20:00'},
            {'id':'day','title':'All day','start':'2026-11-03','end':'2026-11-03','allDay':True},
        ]
        content, count = serialize_events(fixtures, today=date(2026,11,1), now=datetime(2026,11,1,tzinfo=timezone.utc))
        s = content.decode()
        self.assertEqual(count,2)
        self.assertIn('UID:a@gakusei-cheer-portal.web.app', s)
        self.assertIn('DTSTART:20261101T100000Z', s)
        self.assertIn('DTEND:20261101T110000Z', s)
        self.assertIn('DTSTART;VALUE=DATE:20261103', s)
        self.assertIn('DTEND;VALUE=DATE:20261104', s)
        self.assertNotIn('Yesterday', s)
    def test_line_folding_75_octets(self):
        folded=fold_ics('SUMMARY:'+'学'*100)
        self.assertTrue(all(len(line.encode())<=75 for line in folded.split('\r\n')))

if __name__ == '__main__': unittest.main()
