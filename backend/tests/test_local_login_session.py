import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


os.environ.setdefault("DASHBOARD_USERNAME", "admin")
os.environ.setdefault("DASHBOARD_PASSWORD", "test-password")
os.environ.setdefault("DASHBOARD_AUTH_TOKEN", "static-test-token")
os.environ.setdefault("JWT_SECRET", "jwt-test-secret")
os.environ.setdefault("TOKEN_ENCRYPTION_SECRET", "encrypt-test-secret")
os.environ.setdefault("SUPER_ADMIN_EMAILS", "local-admin@local.finance-dashboard")

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.auth import LoginRequest, login
from app.auth import require_auth, require_current_user


class _FakeTransaction:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def transaction(self):
        return _FakeTransaction()


class LocalLoginSessionTestCase(unittest.TestCase):
    def test_local_login_returns_internal_user_session_token(self):
        fake_user = {
            "id": "user-123",
            "email": "admin@local.finance-dashboard",
            "name": "Admin",
            "role": "super_admin",
        }
        fake_workspace = {
            "id": "workspace-123",
            "name": "Admin's Household",
            "role": "owner",
            "google_sheet_id": None,
            "google_sheet_sources": [],
        }

        with patch("app.api.auth.authenticate_user", return_value=True), \
             patch("app.api.auth.get_db_connection", return_value=_FakeConnection()), \
             patch("app.api.auth.upsert_user", return_value=fake_user) as upsert_user_mock, \
             patch(
                 "app.api.auth.ensure_default_workspace_for_user",
                 return_value=fake_workspace,
             ):
            response = login(LoginRequest(username="admin", password="test-password"))

        self.assertEqual("local", response["provider"])
        self.assertEqual("workspace-123", response["workspaceId"])
        self.assertEqual("user-123", response["userId"])
        self.assertEqual("admin@local.finance-dashboard", response["email"])
        self.assertNotEqual("static-test-token", response["token"])

        auth_payload = require_auth(
            credentials=types.SimpleNamespace(
                scheme="Bearer",
                credentials=response["token"],
            )
        )
        current_user = require_current_user(auth_payload=auth_payload)

        self.assertEqual("user-123", current_user["sub"])
        self.assertEqual("admin@local.finance-dashboard", current_user["email"])
        self.assertEqual("super_admin", current_user["role"])

        upsert_user_mock.assert_called_once()
        _, kwargs = upsert_user_mock.call_args
        self.assertEqual("admin@local.finance-dashboard", kwargs["email"])
        self.assertEqual("Admin", kwargs["name"])
        self.assertEqual("super_admin", kwargs["role"])

    def test_local_login_preserves_email_usernames(self):
        fake_user = {
            "id": "user-456",
            "email": "owner@example.com",
            "name": "Owner",
            "role": "user",
        }
        fake_workspace = {
            "id": "workspace-456",
            "name": "Owner's Household",
            "role": "owner",
            "google_sheet_id": None,
            "google_sheet_sources": [],
        }

        with patch("app.api.auth.authenticate_user", return_value=True), \
             patch("app.api.auth.get_db_connection", return_value=_FakeConnection()), \
             patch("app.api.auth.upsert_user", return_value=fake_user) as upsert_user_mock, \
             patch(
                 "app.api.auth.ensure_default_workspace_for_user",
                 return_value=fake_workspace,
             ):
            response = login(
                LoginRequest(
                    username="owner@example.com",
                    password="test-password",
                )
            )

        self.assertEqual("owner@example.com", response["email"])
        self.assertEqual("Owner", response["username"])

        _, kwargs = upsert_user_mock.call_args
        self.assertEqual("owner@example.com", kwargs["email"])
        self.assertEqual("Owner", kwargs["name"])
        self.assertEqual("user", kwargs["role"])


if __name__ == "__main__":
    unittest.main()
