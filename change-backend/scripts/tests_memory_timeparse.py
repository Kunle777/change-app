# tests/test_memory_timeparse.py
import unittest
from datetime import datetime, timedelta, timezone

from app.memory.time_parse import parse_time_window

NOW = datetime(2026, 10, 15, 6, 30, tzinfo=timezone.utc)   # 07:30 in Lagos, a Thursday


def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


class TimeParseTests(unittest.TestCase):
    def w(self, q):
        return parse_time_window(q, now=NOW, tz_name="Africa/Lagos")

    def test_no_window(self):
        self.assertIsNone(self.w("what am I avoiding?"))

    def test_yesterday(self):
        w = self.w("what did I write yesterday")
        self.assertEqual((w.since, w.until), (utc(2026, 10, 13, 23), utc(2026, 10, 14, 23)))

    def test_last_week_is_previous_calendar_week(self):
        w = self.w("how was I feeling last week")
        self.assertEqual((w.since, w.until), (utc(2026, 10, 4, 23), utc(2026, 10, 11, 23)))

    def test_this_week_is_open_ended(self):
        w = self.w("anything this week")
        self.assertEqual(w.since, utc(2026, 10, 11, 23))
        self.assertIsNone(w.until)

    def test_last_month(self):
        w = self.w("last month")
        self.assertEqual((w.since, w.until), (utc(2026, 8, 31, 23), utc(2026, 9, 30, 23)))

    def test_past_n_days(self):
        w = self.w("in the past 3 days")
        self.assertEqual(w.since, NOW - timedelta(days=3))
        self.assertIsNone(w.until)

    def test_named_month_in_the_future_means_last_year(self):
        w = self.w("what was I doing in december")
        self.assertEqual((w.since, w.until), (utc(2025, 11, 30, 23), utc(2025, 12, 31, 23)))


if __name__ == "__main__":
    unittest.main()