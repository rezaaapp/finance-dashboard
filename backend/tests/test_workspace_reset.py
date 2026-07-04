import os
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException


os.environ.setdefault("JWT_SECRET", "test-secret")
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.data_sources import reset_google_sheet_source_data
from app.api.workspace_resets import factory_reset_workspace
from app.services.workspace_reset_service import (
    factory_reset_workspace_data,
    reset_google_sheet_synced_data,
)


class FakeCursor:
    def __init__(self, rowcounts=None):
        self.rowcounts = list(rowcounts or [0])
        self.executed = []
        self.rowcount = 0

    def __enter__(self): return self
    def __exit__(self, *_args): return False

    def execute(self, statement, params):
        self.executed.append((" ".join(statement.split()), params))
        self.rowcount = self.rowcounts.pop(0) if self.rowcounts else 0


class FakeConnection:
    def __init__(self, rowcounts=None):
        self.cursor_instance = FakeCursor(rowcounts)
        self.transaction_exceptions = []

    def cursor(self): return self.cursor_instance

    @contextmanager
    def transaction(self):
        try:
            yield
        except Exception as exc:
            self.transaction_exceptions.append(type(exc))
            raise


@contextmanager
def connection_context(connection):
    yield connection


class WorkspaceResetServiceTestCase(unittest.TestCase):
    def test_google_sheet_reset_is_workspace_source_and_origin_scoped(self):
        connection = FakeConnection([3])
        deleted = reset_google_sheet_synced_data(
            connection, workspace_id="workspace-a", source_id="source-a",
        )
        statement, params = connection.cursor_instance.executed[0]
        self.assertEqual(3, deleted)
        self.assertIn("source_origin = 'google_sheet'", statement)
        self.assertEqual(("workspace-a", "source-a"), params)

    def test_factory_reset_deletes_operational_data_only_for_workspace(self):
        connection = FakeConnection([6, 2, 4, 3, 1, 5])
        deleted = factory_reset_workspace_data(connection, workspace_id="workspace-a")
        self.assertEqual(6, deleted["transactions"])
        self.assertEqual(2, deleted["import_jobs"])
        self.assertEqual(4, deleted["fingerprint_registry"])
        self.assertEqual(5, deleted["sync_history"])
        statements = " ".join(sql for sql, _ in connection.cursor_instance.executed)
        for preserved in (
            "users", "workspaces", "workspace_members", "google_oauth_connections",
            "google_sheet_sources", "workspace_configurations",
        ):
            self.assertNotIn(f"delete from {preserved}", statements)
        self.assertTrue(all(params == ("workspace-a",) for _, params in connection.cursor_instance.executed))


class WorkspaceResetEndpointTestCase(unittest.TestCase):
    def test_reset_endpoint_preserves_sheet_and_can_sync_again(self):
        connection = FakeConnection()
        with patch("app.api.data_sources.get_db_connection", return_value=connection_context(connection)), patch(
            "app.api.data_sources._get_workspace_source_or_raise", return_value={"id": "source-a"}
        ), patch(
            "app.api.data_sources.reset_google_sheet_synced_data", return_value=9
        ):
            response = reset_google_sheet_source_data(
                "11111111-1111-1111-1111-111111111111",
                current_user={"sub": "user-a"},
                workspace={"id": "workspace-a"},
            )
        self.assertEqual(9, response["deleted_transactions"])
        self.assertTrue(response["google_sheet_untouched"])

    def test_reset_endpoint_cannot_access_another_workspace_source(self):
        connection = FakeConnection()
        with patch("app.api.data_sources.get_db_connection", return_value=connection_context(connection)), patch(
            "app.api.data_sources._get_workspace_source_or_raise",
            side_effect=HTTPException(status_code=403, detail="access denied"),
        ):
            with self.assertRaises(HTTPException) as raised:
                reset_google_sheet_source_data(
                    "11111111-1111-1111-1111-111111111111",
                    current_user={"sub": "user-a"},
                    workspace={"id": "workspace-a"},
                )
        self.assertEqual(403, raised.exception.status_code)

    @patch("app.api.workspace_resets.settings.APP_ENV", "local-prod")
    def test_factory_reset_is_blocked_in_production(self):
        with self.assertRaises(HTTPException) as raised:
            factory_reset_workspace(
                current_user={"role": "super_admin"},
                workspace={"id": "workspace-a", "role": "owner"},
            )
        self.assertEqual(404, raised.exception.status_code)

    @patch("app.api.workspace_resets.settings.APP_ENV", "local-dev")
    def test_factory_reset_rejects_unauthorized_member(self):
        with self.assertRaises(HTTPException) as raised:
            factory_reset_workspace(
                current_user={"role": "member"},
                workspace={"id": "workspace-a", "role": "member"},
            )
        self.assertEqual(403, raised.exception.status_code)

    @patch("app.api.workspace_resets.settings.APP_ENV", "local-dev")
    def test_factory_reset_rolls_back_on_failure(self):
        connection = FakeConnection()
        with patch("app.api.workspace_resets.get_db_connection", return_value=connection_context(connection)), patch(
            "app.api.workspace_resets.factory_reset_workspace_data",
            side_effect=RuntimeError("database failure"),
        ):
            with self.assertRaises(RuntimeError):
                factory_reset_workspace(
                    current_user={"role": "super_admin"},
                    workspace={"id": "workspace-a", "role": "owner"},
                )
        self.assertEqual([RuntimeError], connection.transaction_exceptions)


if __name__ == "__main__":
    unittest.main()
