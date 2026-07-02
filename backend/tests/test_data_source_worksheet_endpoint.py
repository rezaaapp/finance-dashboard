import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException


os.environ.setdefault("DASHBOARD_USERNAME", "admin")
os.environ.setdefault("DASHBOARD_PASSWORD", "test-password")
os.environ.setdefault("DASHBOARD_AUTH_TOKEN", "static-test-token")
os.environ.setdefault("JWT_SECRET", "jwt-test-secret")
os.environ.setdefault("TOKEN_ENCRYPTION_SECRET", "encrypt-test-secret")

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.data_sources import (
    _get_tabs_for_source,
    _serialize_sync_response,
    list_google_sheet_source_worksheets,
)


class _FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class WorksheetEndpointTestCase(unittest.TestCase):
    def test_import_result_details_preserve_summary_and_failed_reason(self):
        response = _serialize_sync_response(
            {
                "id": "job-1", "status": "failed", "total_rows": 2,
                "inserted_rows": 1, "updated_rows": 0,
                "skipped_rows": 0, "failed_rows": 1,
            },
            details={
                "inserted": [{"merchant": "Safe merchant", "reason": "IMPORTED"}],
                "updated": [], "skipped": [],
                "failed": [{"merchant": None, "reason": "VALIDATION_FAILED"}],
            },
        )
        self.assertEqual(1, response["inserted_rows"])
        self.assertEqual(1, response["summary"]["failed"])
        self.assertEqual("VALIDATION_FAILED", response["details"]["failed"][0]["reason"])

    @patch("app.api.data_sources._fetch_spreadsheet_metadata")
    def test_multi_sheet_selection_only_returns_selected_tabs(self, metadata):
        metadata.return_value = {
            "sheet_names": ["Start 1 Januari", "Start 1 Februari", "Summary"],
        }
        selected, skipped = _get_tabs_for_source(
            access_token="token",
            spreadsheet_id="sheet-1",
            sheet_name="Start 1 Januari",
            selected_tabs=["Start 1 Januari", "Start 1 Februari"],
        )
        self.assertEqual(["Start 1 Januari", "Start 1 Februari"], selected)
        self.assertEqual([], skipped)

    @patch("app.api.data_sources._fetch_spreadsheet_metadata")
    def test_select_all_monthly_tabs_excludes_non_transaction_tabs(self, metadata):
        metadata.return_value = {
            "sheet_names": ["Start 1 Januari", "Start 1 Februari", "Configuration"],
        }
        selected, _skipped = _get_tabs_for_source(
            access_token="token",
            spreadsheet_id="sheet-1",
            sheet_name=None,
            selected_tabs=["Start 1 Januari", "Start 1 Februari", "Configuration"],
        )
        self.assertEqual(["Start 1 Januari", "Start 1 Februari"], selected)

    @patch("app.api.data_sources._fetch_spreadsheet_metadata")
    def test_legacy_default_tab_remains_backward_compatible(self, metadata):
        selected, skipped = _get_tabs_for_source(
            access_token="token",
            spreadsheet_id="sheet-1",
            sheet_name="Start 1 Januari",
            selected_tabs=[],
        )
        self.assertEqual(["Start 1 Januari"], selected)
        self.assertEqual([], skipped)
        metadata.assert_called_once()

    def test_invalid_source_id_format_returns_400(self):
        with self.assertRaises(HTTPException) as raised:
            list_google_sheet_source_worksheets(
                source_id="not-a-uuid",
                current_user={"sub": "user-1"},
                workspace={"id": "workspace-1"},
            )

        self.assertEqual(400, raised.exception.status_code)
        self.assertEqual("Invalid Google Sheet source ID", raised.exception.detail)

    def test_non_existing_source_returns_404(self):
        with patch("app.api.data_sources.get_db_connection", return_value=_FakeConnection()), \
             patch("app.api.data_sources.get_google_sheet_source", return_value=None), \
             patch("app.api.data_sources.get_google_sheet_source_by_id", return_value=None):
            with self.assertRaises(HTTPException) as raised:
                list_google_sheet_source_worksheets(
                    source_id="11111111-1111-1111-1111-111111111111",
                    current_user={"sub": "user-1"},
                    workspace={"id": "workspace-1"},
                )

        self.assertEqual(404, raised.exception.status_code)
        self.assertEqual("Google Sheet source not found", raised.exception.detail)

    def test_foreign_workspace_source_returns_403(self):
        with patch("app.api.data_sources.get_db_connection", return_value=_FakeConnection()), \
             patch("app.api.data_sources.get_google_sheet_source", return_value=None), \
             patch(
                 "app.api.data_sources.get_google_sheet_source_by_id",
                 return_value={
                     "id": "11111111-1111-1111-1111-111111111111",
                     "workspace_id": "workspace-foreign",
                 },
             ):
            with self.assertRaises(HTTPException) as raised:
                list_google_sheet_source_worksheets(
                    source_id="11111111-1111-1111-1111-111111111111",
                    current_user={"sub": "user-1"},
                    workspace={"id": "workspace-1"},
                )

        self.assertEqual(403, raised.exception.status_code)
        self.assertEqual("Google Sheet source access denied", raised.exception.detail)

    def test_valid_source_returns_worksheets(self):
        with patch("app.api.data_sources.get_db_connection", return_value=_FakeConnection()), \
             patch(
                 "app.api.data_sources.get_google_sheet_source",
                 return_value={
                     "id": "11111111-1111-1111-1111-111111111111",
                     "sheet_id": "sheet-123",
                     "spreadsheet_title": "Budget 2026",
                 },
             ), \
             patch("app.api.data_sources._get_access_context", return_value=(None, "access-token")), \
             patch(
                 "app.api.data_sources._fetch_spreadsheet_metadata",
                 return_value={
                     "title": "Budget 2026",
                     "sheet_names": ["Jan", "Feb"],
                 },
             ):
            response = list_google_sheet_source_worksheets(
                source_id="11111111-1111-1111-1111-111111111111",
                current_user={"sub": "user-1"},
                workspace={"id": "workspace-1"},
            )

        self.assertEqual("11111111-1111-1111-1111-111111111111", response["source_id"])
        self.assertEqual("sheet-123", response["spreadsheet_id"])
        self.assertEqual(["Jan", "Feb"], response["worksheets"])


if __name__ == "__main__":
    unittest.main()
