import sys
import types
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

fake_psycopg_errors = types.ModuleType("psycopg.errors")
fake_psycopg_errors.UndefinedTable = type("UndefinedTable", (Exception,), {})
sys.modules.setdefault("psycopg.errors", fake_psycopg_errors)

fake_psycopg_rows = types.ModuleType("psycopg.rows")
fake_psycopg_rows.dict_row = object()
sys.modules.setdefault("psycopg.rows", fake_psycopg_rows)

from app.repositories import analytics_repository as analytics


class AnalyticsDateFilterTestCase(unittest.TestCase):
    def test_period_bounds_match_previous_year_only_filter_semantics(self):
        period_start, period_end = analytics._period_bounds(2026)
        transaction_dates = [
            date(2025, 12, 31),
            date(2026, 1, 1),
            date(2026, 6, 15),
            date(2026, 12, 31),
            date(2027, 1, 1),
        ]

        legacy_matches = [
            item
            for item in transaction_dates
            if item.year == 2026
        ]
        range_matches = [
            item
            for item in transaction_dates
            if period_start <= item < period_end
        ]

        self.assertEqual(legacy_matches, range_matches)

    def test_period_bounds_match_previous_year_month_filter_semantics(self):
        period_start, period_end = analytics._period_bounds(2026, 6)
        transaction_dates = [
            date(2026, 5, 31),
            date(2026, 6, 1),
            date(2026, 6, 15),
            date(2026, 6, 30),
            date(2026, 7, 1),
        ]

        legacy_matches = [
            item
            for item in transaction_dates
            if item.year == 2026 and item.month == 6
        ]
        range_matches = [
            item
            for item in transaction_dates
            if period_start <= item < period_end
        ]

        self.assertEqual(legacy_matches, range_matches)

    def test_filters_use_date_range_when_year_is_present(self):
        clauses, params = analytics._filters(year=2026, month=6)

        self.assertIn("transaction_date >= %s", clauses)
        self.assertIn("transaction_date < %s", clauses)
        self.assertNotIn("extract(year from transaction_date)", clauses)
        self.assertNotIn("extract(month from transaction_date)", clauses)
        self.assertEqual(
            [date(2026, 6, 1), date(2026, 7, 1)],
            params,
        )

    def test_filters_keep_month_only_fallback_for_backward_compatibility(self):
        clauses, params = analytics._filters(month=6)

        self.assertIn("extract(month from transaction_date)::int = %s", clauses)
        self.assertNotIn("transaction_date >= %s", clauses)
        self.assertEqual([6], params)

    @patch("app.repositories.analytics_repository._fetch_all", return_value=[])
    def test_budget_history_by_category_uses_period_range_join(self, fetch_all_mock):
        analytics.get_budget_history_by_category(
            object(),
            workspace_id="workspace-1",
            periods=[
                {"year": 2026, "month": 6, "label": "2026-06"},
                {"year": 2026, "month": 5, "label": "2026-05"},
            ],
        )

        query = fetch_all_mock.call_args.args[1]
        params = fetch_all_mock.call_args.args[2]

        self.assertIn("t.transaction_date >= sp.period_start", query)
        self.assertIn("t.transaction_date < sp.period_end", query)
        self.assertNotIn("extract(year from t.transaction_date)", query)
        self.assertNotIn("extract(month from t.transaction_date)", query)
        self.assertEqual(date(2026, 6, 1), params[0])
        self.assertEqual(date(2026, 7, 1), params[1])
        self.assertEqual("2026-06", params[2])
        self.assertEqual("workspace-1", params[-1])

    @patch("app.repositories.analytics_repository._fetch_all", return_value=[])
    def test_monthly_financial_type_breakdown_uses_year_range_filter(self, fetch_all_mock):
        analytics.get_monthly_financial_type_breakdown(
            object(),
            workspace_id="workspace-1",
            year=2026,
        )

        query = fetch_all_mock.call_args.args[1]
        params = fetch_all_mock.call_args.args[2]

        self.assertIn("t.transaction_date >= %s", query)
        self.assertIn("t.transaction_date < %s", query)
        self.assertNotIn("extract(year from t.transaction_date)::int = %s", query)
        self.assertEqual("workspace-1", params[0])
        self.assertEqual(date(2026, 1, 1), params[1])
        self.assertEqual(date(2027, 1, 1), params[2])

    @patch("app.repositories.analytics_repository._fetch_all", return_value=[])
    def test_monthly_totals_apply_owner_filter(self, fetch_all_mock):
        analytics.get_monthly_totals(
            object(),
            workspace_id="workspace-1",
            year=2026,
            month=6,
            direction="expense",
            name="Divya",
        )

        query = fetch_all_mock.call_args.args[1]
        params = fetch_all_mock.call_args.args[2]

        self.assertIn("user_name", query)
        self.assertIn("raw_payload->>'Nama'", query)
        self.assertEqual("workspace-1", params[0])
        self.assertEqual(date(2026, 6, 1), params[1])
        self.assertEqual(date(2026, 7, 1), params[2])
        self.assertEqual("Divya", params[3])

    @patch(
        "app.repositories.analytics_repository.get_monthly_totals",
        return_value=[{"bulan": "2026-06", "total": 0}],
    )
    def test_monthly_allocation_forwards_owner_filter(self, monthly_totals_mock):
        connection = object()

        result = analytics.get_monthly_allocation(
            connection,
            workspace_id="workspace-1",
            year=2026,
            month=6,
            name="Divya",
        )

        monthly_totals_mock.assert_called_once_with(
            connection,
            workspace_id="workspace-1",
            year=2026,
            month=6,
            direction="expense",
            name="Divya",
        )
        self.assertEqual(
            [{"month": "2026-06", "Needs": 0, "Wants": 0, "Savings": 0}],
            result,
        )


if __name__ == "__main__":
    unittest.main()
