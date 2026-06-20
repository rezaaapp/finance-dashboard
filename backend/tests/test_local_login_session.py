import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException


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
            "id": "11111111-1111-4111-8111-111111111111",
            "email": "admin@local.finance-dashboard",
            "name": "Admin",
            "role": "super_admin",
        }
        fake_workspace = {
            "id": "22222222-2222-4222-8222-222222222222",
            "name": "Admin's Household",
            "role": "owner",
            "google_sheet_id": None,
            "google_sheet_sources": [],
        }

        with patch("app.api.auth.settings.DASHBOARD_USERNAME", "admin"), \
             patch(
                 "app.api.auth.settings.SUPER_ADMIN_EMAILS",
                 ["admin@local.finance-dashboard"],
             ), \
             patch("app.api.auth.authenticate_user", return_value=True), \
             patch("app.api.auth.get_db_connection", return_value=_FakeConnection()), \
             patch("app.api.auth.upsert_user", return_value=fake_user) as upsert_user_mock, \
             patch(
                 "app.api.auth.ensure_default_workspace_for_user",
                 return_value=fake_workspace,
             ):
            response = login(LoginRequest(username="admin", password="test-password"))

        self.assertEqual("local", response["provider"])
        self.assertEqual("22222222-2222-4222-8222-222222222222", response["workspaceId"])
        self.assertEqual("11111111-1111-4111-8111-111111111111", response["userId"])
        self.assertEqual("admin@local.finance-dashboard", response["email"])
        self.assertNotEqual("static-test-token", response["token"])

        auth_payload = require_auth(
            credentials=types.SimpleNamespace(
                scheme="Bearer",
                credentials=response["token"],
            )
        )
        with patch("app.auth.get_db_connection", return_value=_FakeConnection()), \
             patch("app.auth.upsert_session_user", return_value=fake_user):
            current_user = require_current_user(auth_payload=auth_payload)

        self.assertEqual("11111111-1111-4111-8111-111111111111", current_user["sub"])
        self.assertEqual("admin@local.finance-dashboard", current_user["email"])
        self.assertEqual("super_admin", current_user["role"])

        upsert_user_mock.assert_called_once()
        _, kwargs = upsert_user_mock.call_args
        self.assertEqual("admin@local.finance-dashboard", kwargs["email"])
        self.assertEqual("Admin", kwargs["name"])
        self.assertEqual("super_admin", kwargs["role"])

    def test_local_login_preserves_email_usernames(self):
        fake_user = {
            "id": "33333333-3333-4333-8333-333333333333",
            "email": "owner@example.com",
            "name": "Owner",
            "role": "user",
        }
        fake_workspace = {
            "id": "44444444-4444-4444-8444-444444444444",
            "name": "Owner's Household",
            "role": "owner",
            "google_sheet_id": None,
            "google_sheet_sources": [],
        }

        with patch("app.api.auth.settings.DASHBOARD_USERNAME", "owner@example.com"), \
             patch("app.api.auth.settings.SUPER_ADMIN_EMAILS", []), \
             patch("app.api.auth.authenticate_user", return_value=True), \
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

    def test_require_current_user_upserts_missing_session_user_row(self):
        auth_payload = {
            "sub": "c4896d51-c7df-4efb-b26e-b8a6de7fa0b7",
            "email": "owner@example.com",
            "name": "Owner",
            "role": "user",
        }
        fake_user = {
            "id": auth_payload["sub"],
            "email": auth_payload["email"],
            "name": auth_payload["name"],
            "role": auth_payload["role"],
        }

        with patch("app.auth.get_db_connection", return_value=_FakeConnection()), \
             patch("app.auth.upsert_session_user", return_value=fake_user) as upsert_session_user_mock:
            current_user = require_current_user(auth_payload=auth_payload)

        self.assertEqual(auth_payload["sub"], current_user["sub"])
        self.assertEqual(auth_payload["email"], current_user["email"])
        self.assertEqual(auth_payload["name"], current_user["name"])
        upsert_session_user_mock.assert_called_once()
        _, kwargs = upsert_session_user_mock.call_args
        self.assertEqual(auth_payload["sub"], kwargs["user_id"])
        self.assertEqual(auth_payload["email"], kwargs["email"])
        self.assertEqual(auth_payload["name"], kwargs["name"])

    def test_require_current_user_returns_401_for_invalid_session_user(self):
        auth_payload = {
            "sub": "not-a-valid-user-id",
            "email": "owner@example.com",
            "name": "Owner",
            "role": "user",
        }

        with patch("app.auth.get_db_connection", return_value=_FakeConnection()), \
             patch(
                 "app.auth.upsert_session_user",
                 side_effect=ValueError("User session has an invalid subject identifier."),
             ):
            with self.assertRaises(HTTPException) as raised:
                require_current_user(auth_payload=auth_payload)

        self.assertEqual(401, raised.exception.status_code)
        self.assertEqual(
            "User session has an invalid subject identifier.",
            raised.exception.detail,
        )


if __name__ == "__main__":
    unittest.main()
