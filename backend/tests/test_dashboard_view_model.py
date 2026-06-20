import os
import sys
import unittest
from pathlib import Path
import types
from unittest.mock import patch


os.environ.setdefault("DASHBOARD_USERNAME", "admin")
os.environ.setdefault("DASHBOARD_PASSWORD", "test-password")
os.environ.setdefault("DASHBOARD_AUTH_TOKEN", "static-test-token")
os.environ.setdefault("JWT_SECRET", "jwt-test-secret")
os.environ.setdefault("TOKEN_ENCRYPTION_SECRET", "encrypt-test-secret")

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

fake_psycopg_errors = types.ModuleType("psycopg.errors")
fake_psycopg_errors.UndefinedTable = type("UndefinedTable", (Exception,), {})
fake_psycopg_errors.NotSupportedError = type("NotSupportedError", (Exception,), {})
fake_psycopg = types.ModuleType("psycopg")
fake_psycopg_pool = types.ModuleType("psycopg_pool")
fake_psycopg_types = types.ModuleType("psycopg.types")
fake_psycopg_types_json = types.ModuleType("psycopg.types.json")
fake_psycopg.connect = lambda *args, **kwargs: None
fake_psycopg.errors = fake_psycopg_errors
fake_psycopg_pool.ConnectionPool = object
fake_psycopg_types_json.Jsonb = lambda value: value
sys.modules.setdefault("psycopg", fake_psycopg)
sys.modules.setdefault("psycopg.errors", fake_psycopg_errors)
sys.modules.setdefault("psycopg_pool", fake_psycopg_pool)
sys.modules.setdefault("psycopg.types", fake_psycopg_types)
sys.modules.setdefault("psycopg.types.json", fake_psycopg_types_json)

from app.api.dashboard import build_dashboard_view_model_payload


class DashboardViewModelTestCase(unittest.TestCase):
    def test_view_model_uses_latest_available_year_and_aggregates_payload(self):
        with patch(
            "app.api.dashboard.get_transaction_available_years_for_workspace",
            return_value=[2026, 2025],
        ), patch(
            "app.api.dashboard.get_google_sheet_sources",
            return_value=[{"id": "source-1", "status": "active"}],
        ), patch(
            "app.api.dashboard.get_google_oauth_connection_status",
            return_value={
                "google_email": "user@example.com",
                "status": "active",
            },
        ), patch(
            "app.api.dashboard.get_active_google_oauth_connection",
            return_value={"scopes": ["scope-a"]},
        ), patch(
            "app.api.dashboard.SpreadsheetSyncService"
        ) as sync_service_mock, patch(
            "app.api.dashboard.analytics.get_summary",
            return_value={"data_source": {"name": "Google Sheet 2026"}, "transaction_count": 10},
        ), patch(
            "app.api.dashboard.analytics.get_monthly_totals",
            side_effect=[[{"total": 1}], [{"total": 2}], [{"total": 3}]],
        ), patch(
            "app.api.dashboard.analytics.get_top_spending",
            return_value=[{"merchant": "A"}],
        ), patch(
            "app.api.dashboard.analytics.get_spending_by_category",
            return_value=[{"category": "Food"}],
        ), patch(
            "app.api.dashboard.analytics.get_financial_type_breakdown",
            return_value=[{"type": "need", "amount": 10}],
        ), patch(
            "app.api.dashboard.analytics.get_monthly_financial_type_breakdown",
            return_value=[{"month": 6, "need": 10}],
        ), patch(
            "app.api.dashboard.generate_rule_based_insights",
            return_value={"summary": "ok"},
        ), patch(
            "app.api.dashboard.get_effective_insight_settings",
            return_value={"anomaly_warning_multiplier": 2},
        ), patch(
            "app.api.dashboard.analytics.get_grocery_vs_food",
            return_value=[{"grocery": 1, "food": 2}],
        ), patch(
            "app.api.dashboard.analytics.get_category_heatmap",
            return_value={"rows": []},
        ), patch(
            "app.api.dashboard.analytics.get_transactions",
            return_value=[{"id": "trx-1"}],
        ), patch(
            "app.api.dashboard.analytics.get_category_trends",
            return_value={"series": []},
        ), patch(
            "app.api.dashboard.analytics.get_personal_analytics",
            return_value={"users": []},
        ), patch(
            "app.api.dashboard.analytics.get_budget_forecast",
            return_value={"forecast": []},
        ), patch(
            "app.api.dashboard.analytics.get_anomalies",
            return_value=[{"id": "anomaly-1"}],
        ):
            sync_service_mock.return_value.requires_reconnect.return_value = True
            payload = build_dashboard_view_model_payload(
                connection=object(),
                workspace={
                    "id": "workspace-1",
                    "name": "Workspace A",
                    "role": "owner",
                    "subscription_status": "free",
                    "google_sheet_id": None,
                    "google_sheet_sources": [],
                },
                current_user={"sub": "user-1", "role": "owner"},
                year=None,
                month=6,
                name="Reza",
            )

        self.assertEqual(2026, payload["selected_period"]["year"])
        self.assertEqual(6, payload["selected_period"]["month"])
        self.assertEqual("Reza", payload["selected_period"]["name"])
        self.assertEqual("workspace-1", payload["workspace"]["id"])
        self.assertEqual([2026, 2025], payload["available_years"])
        self.assertTrue(payload["has_active_google_sheet"])
        self.assertTrue(payload["google_connection"]["connected"])
        self.assertTrue(payload["google_connection"]["needs_reconnect"])
        self.assertEqual("Google Sheet 2026", payload["current_sheet_name"])
        self.assertEqual([{"total": 1}], payload["dashboard"]["monthly_spending"])
        self.assertEqual([{"total": 2}], payload["dashboard"]["monthly_saving"])
        self.assertEqual([{"total": 3}], payload["dashboard"]["monthly_income"])
        self.assertEqual([{"merchant": "A"}], payload["dashboard"]["top_spending"])
        self.assertEqual([{"category": "Food"}], payload["dashboard"]["spending_by_category"])
        self.assertEqual([{"type": "need", "amount": 10}], payload["dashboard"]["financial_types"])
        self.assertEqual([{"month": 6, "need": 10}], payload["dashboard"]["monthly_financial_types"])
        self.assertEqual({"summary": "ok"}, payload["dashboard"]["rule_based_insights"])
        self.assertEqual([{"id": "trx-1"}], payload["dashboard"]["transactions"])

    def test_view_model_returns_safe_empty_premium_sections_for_non_premium_users(self):
        with patch(
            "app.api.dashboard.get_transaction_available_years_for_workspace",
            return_value=[],
        ), patch(
            "app.api.dashboard.get_google_sheet_sources",
            return_value=[],
        ), patch(
            "app.api.dashboard.get_google_oauth_connection_status",
            return_value=None,
        ), patch(
            "app.api.dashboard.get_active_google_oauth_connection",
            return_value=None,
        ), patch(
            "app.api.dashboard.SpreadsheetSyncService"
        ) as sync_service_mock, patch(
            "app.api.dashboard.analytics.get_summary",
            return_value={},
        ), patch(
            "app.api.dashboard.analytics.get_monthly_totals",
            side_effect=[[], [], []],
        ), patch(
            "app.api.dashboard.analytics.get_top_spending",
            return_value=[],
        ), patch(
            "app.api.dashboard.analytics.get_spending_by_category",
            return_value=[],
        ), patch(
            "app.api.dashboard.analytics.get_financial_type_breakdown",
            return_value=[],
        ), patch(
            "app.api.dashboard.generate_rule_based_insights",
            return_value={},
        ):
            sync_service_mock.return_value.requires_reconnect.return_value = False
            payload = build_dashboard_view_model_payload(
                connection=object(),
                workspace={
                    "id": "workspace-2",
                    "name": "Workspace B",
                    "role": "member",
                    "subscription_status": "free",
                    "google_sheet_id": None,
                    "google_sheet_sources": [],
                },
                current_user={"sub": "user-2", "role": "user"},
                year=None,
                month=None,
                name=None,
            )

        self.assertEqual([], payload["available_years"])
        self.assertFalse(payload["has_active_google_sheet"])
        self.assertEqual({"connected": False}, payload["google_connection"])
        self.assertEqual([], payload["dashboard"]["grocery_vs_food"])
        self.assertEqual({}, payload["dashboard"]["category_heatmap"])
        self.assertEqual([], payload["dashboard"]["transactions"])
        self.assertEqual({}, payload["dashboard"]["category_trends"])
        self.assertEqual({}, payload["dashboard"]["personal_analytics"])
        self.assertEqual({}, payload["dashboard"]["budget_forecast"])
        self.assertEqual([], payload["dashboard"]["anomalies"])


if __name__ == "__main__":
    unittest.main()
