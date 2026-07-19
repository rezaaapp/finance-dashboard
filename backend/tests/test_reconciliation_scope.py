from __future__ import annotations

import unittest
from datetime import date

from app.services.reconciliation_service import (
    DEFAULT_REPAIR_MONTH,
    build_repair_statements,
    format_reconciliation_report,
    generate_reconciliation_report,
    resolve_reconciliation_scope,
)
from app.imports.utils.fingerprint import normalize_owner_name


class ReconciliationScopeTestCase(unittest.TestCase):
    def test_default_scope_uses_june_2026(self):
        scope = resolve_reconciliation_scope()

        self.assertEqual("2026-06", DEFAULT_REPAIR_MONTH)
        self.assertEqual(date(2026, 6, 1), scope.start_date)
        self.assertEqual(date(2026, 6, 30), scope.end_date)

    def test_month_scope_parses_full_month(self):
        scope = resolve_reconciliation_scope(month="2026-06")

        self.assertEqual(date(2026, 6, 1), scope.start_date)
        self.assertEqual(date(2026, 6, 30), scope.end_date)

    def test_custom_date_scope_is_supported(self):
        scope = resolve_reconciliation_scope(
            date_from="2026-06-05",
            date_to="2026-06-21",
        )

        self.assertEqual(date(2026, 6, 5), scope.start_date)
        self.assertEqual(date(2026, 6, 21), scope.end_date)

    def test_mixed_scope_inputs_raise_error(self):
        with self.assertRaises(ValueError):
            resolve_reconciliation_scope(
                month="2026-06",
                date_from="2026-06-01",
                date_to="2026-06-30",
            )

    def test_repair_statements_are_scoped_to_selected_window(self):
        scope = resolve_reconciliation_scope()
        statements = build_repair_statements(
            workspace_id="workspace-123",
            scope=scope,
        )

        self.assertTrue(statements)
        for statement in statements:
            self.assertIn("transaction_date between %s and %s", statement.sql)
            self.assertEqual("workspace-123", statement.params[0])
            self.assertEqual(date(2026, 6, 1), statement.params[1])
            self.assertEqual(date(2026, 6, 30), statement.params[2])

    def test_repair_plan_includes_reza_normalization_statement(self):
        scope = resolve_reconciliation_scope()
        statements = build_repair_statements(
            workspace_id="workspace-123",
            scope=scope,
        )

        statement = next(
            item
            for item in statements
            if item.name == "normalize_reza_owner_names"
        )
        self.assertIn("set user_name = 'Reza'", statement.sql)
        self.assertIn(
            "lower(btrim(coalesce(user_name, ''))) in ('reza putra pratama', 'reza')",
            statement.sql,
        )

    def test_source_origin_backfill_uses_registered_provider_metadata(self):
        statements = build_repair_statements(
            workspace_id="workspace-123",
            scope=resolve_reconciliation_scope(),
        )
        statement = next(
            item
            for item in statements
            if item.name == "backfill_source_origin_and_reference"
        )
        normalized_sql = " ".join(statement.sql.lower().split())

        self.assertIn("when 'blu' then 'blu_pdf'", normalized_sql)
        self.assertIn("when 'bca' then 'bca_pdf'", normalized_sql)
        self.assertIn("else source_origin end", normalized_sql)

    def test_normalize_owner_name_groups_reza_aliases(self):
        self.assertEqual("Reza", normalize_owner_name("Reza"))
        self.assertEqual("Reza", normalize_owner_name(" reza putra pratama "))

    def test_reconciliation_runtime_sql_has_no_literal_owner_placeholder(self):
        class FakeCursor:
            def __init__(self, executed_sql: list[str]):
                self.executed_sql = executed_sql
                self.last_sql = ""

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, sql, params):
                self.last_sql = sql
                self.executed_sql.append(sql)

            def fetchone(self):
                if "total_transactions" in self.last_sql:
                    return {
                        "total_transactions": 0,
                        "blu_pdf_transactions": 0,
                        "google_sheet_transactions": 0,
                        "unknown_owner_rows": 0,
                        "missing_source_origin_rows": 0,
                        "missing_canonical_fingerprint_rows": 0,
                        "missing_canonical_fingerprint_date_rows": 0,
                    }
                if "dashboard_row_count" in self.last_sql:
                    return {
                        "dashboard_row_count": 0,
                        "dashboard_expense_total": 0,
                        "dashboard_income_total": 0,
                        "canonical_row_count": 0,
                        "canonical_expense_total": 0,
                        "canonical_income_total": 0,
                    }
                if "historical_transactions" in self.last_sql:
                    return {
                        "historical_transactions": 0,
                        "historical_unknown_owner_rows": 0,
                        "historical_missing_source_origin_rows": 0,
                        "historical_missing_canonical_fingerprint_rows": 0,
                        "historical_duplicate_candidate_groups": 0,
                    }
                if "scoped_transactions" in self.last_sql:
                    return {
                        "total_transactions": 0,
                        "blu_pdf_transactions": 0,
                        "google_sheet_transactions": 0,
                        "scoped_transactions": 0,
                    }
                return {}

            def fetchall(self):
                return []

        class FakeConnection:
            def __init__(self):
                self.executed_sql: list[str] = []

            def cursor(self, row_factory=None):
                return FakeCursor(self.executed_sql)

        connection = FakeConnection()

        generate_reconciliation_report(
            connection,
            workspace_id="workspace-123",
            scope=resolve_reconciliation_scope(),
        )

        self.assertTrue(connection.executed_sql)
        for sql in connection.executed_sql:
            self.assertNotIn("{_owner_name_expr()}", sql)

    def test_report_formatter_calls_out_historical_rows_as_report_only(self):
        output = format_reconciliation_report(
            {
                "scope": {
                    "label": "June 2026",
                    "start_date": "2026-06-01",
                    "end_date": "2026-06-30",
                },
                "june_db_summary": {
                    "total_transactions": 10,
                    "blu_pdf_transactions": 4,
                    "google_sheet_transactions": 6,
                    "unknown_owner_rows": 1,
                    "missing_source_origin_rows": 2,
                    "missing_canonical_fingerprint_rows": 3,
                    "missing_canonical_fingerprint_date_rows": 4,
                },
                "june_owner_distribution": [],
                "june_source_origin_distribution": [],
                "june_duplicate_candidates": [],
                "june_missing_records": [],
                "june_dashboard_vs_sql_comparison": {
                    "dashboard_row_count": 10,
                    "canonical_row_count": 8,
                    "dashboard_expense_total": 1000,
                    "canonical_expense_total": 800,
                    "dashboard_income_total": 200,
                    "canonical_income_total": 200,
                },
                "historical_data_quality_notes": {
                    "historical_transactions": 99,
                    "historical_unknown_owner_rows": 5,
                    "historical_missing_source_origin_rows": 3,
                    "historical_missing_canonical_fingerprint_rows": 2,
                    "historical_duplicate_candidate_groups": 1,
                },
                "repair_plan": [],
            }
        )

        self.assertIn("Historical Data Quality Notes", output)
        self.assertIn("No repair action is generated for historical rows outside the scoped window.", output)


if __name__ == "__main__":
    unittest.main()
