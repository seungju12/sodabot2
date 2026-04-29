import unittest
from datetime import datetime

from bot.utils.time_utils import KST, get_notice_target_date


class TimeUtilsTests(unittest.TestCase):
    def test_notice_target_date_for_30_day_month_is_28th_midnight(self):
        self.assertTrue(get_notice_target_date(datetime(2026, 4, 28, 0, 0, tzinfo=KST)))
        self.assertFalse(get_notice_target_date(datetime(2026, 4, 27, 0, 0, tzinfo=KST)))

    def test_notice_target_date_for_31_day_month_is_29th_midnight(self):
        self.assertTrue(get_notice_target_date(datetime(2026, 5, 29, 0, 0, tzinfo=KST)))
        self.assertFalse(get_notice_target_date(datetime(2026, 5, 28, 0, 0, tzinfo=KST)))

    def test_notice_target_date_for_february_is_adjusted_from_last_day(self):
        self.assertTrue(get_notice_target_date(datetime(2026, 2, 26, 0, 0, tzinfo=KST)))
        self.assertFalse(get_notice_target_date(datetime(2026, 2, 25, 0, 0, tzinfo=KST)))


if __name__ == "__main__":
    unittest.main()