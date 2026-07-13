import sys
import unittest
from datetime import date
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.period_service import PeriodMode, resolve_period


class PeriodServiceTestCase(unittest.TestCase):
    def test_year_month_resolves_to_half_open_month_bounds(self):
        period = resolve_period(year=2026, month=6)

        self.assertEqual(PeriodMode.YEAR_MONTH, period.mode)
        self.assertEqual(date(2026, 6, 1), period.start_date)
        self.assertEqual(date(2026, 6, 30), period.end_date)
        self.assertEqual(date(2026, 7, 1), period.end_exclusive)

    def test_date_range_has_priority_over_year_month(self):
        period = resolve_period(
            year=2026,
            month=6,
            start_date="2026-02-10",
            end_date="2026-03-12",
        )

        self.assertEqual(PeriodMode.DATE_RANGE, period.mode)
        self.assertEqual(date(2026, 2, 10), period.start_date)
        self.assertEqual(date(2026, 3, 12), period.end_date)
        self.assertEqual(date(2026, 3, 13), period.end_exclusive)

    def test_all_time_keeps_period_unbounded(self):
        period = resolve_period(year=2026, period_mode="all_time")

        self.assertEqual(PeriodMode.ALL_TIME, period.mode)
        self.assertFalse(period.has_date_bounds)

    def test_preset_resolves_to_relative_date_range(self):
        period = resolve_period(
            period_mode="last_7_days",
            anchor_date=date(2026, 7, 13),
        )

        self.assertEqual(PeriodMode.PRESET, period.mode)
        self.assertEqual(date(2026, 7, 7), period.start_date)
        self.assertEqual(date(2026, 7, 13), period.end_date)
        self.assertEqual(date(2026, 7, 14), period.end_exclusive)

    def test_invalid_date_range_raises_user_readable_error(self):
        with self.assertRaisesRegex(
            ValueError,
            "start_date must be before or equal to end_date",
        ):
            resolve_period(start_date="2026-07-14", end_date="2026-07-13")


if __name__ == "__main__":
    unittest.main()
