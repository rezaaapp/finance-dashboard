import os
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch


os.environ.setdefault("DASHBOARD_USERNAME", "admin")
os.environ.setdefault("DASHBOARD_PASSWORD", "test-password")
os.environ.setdefault("DASHBOARD_AUTH_TOKEN", "static-test-token")
os.environ.setdefault("JWT_SECRET", "jwt-test-secret")
os.environ.setdefault("TOKEN_ENCRYPTION_SECRET", "encrypt-test-secret")
os.environ.setdefault(
    "TOKEN_ENCRYPTION_KEY",
    "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
)
os.environ.setdefault("GOOGLE_OAUTH_CLIENT_ID", "client-id")
os.environ.setdefault("GOOGLE_OAUTH_CLIENT_SECRET", "client-secret")

fake_httpx = types.ModuleType("httpx")
fake_httpx.HTTPError = Exception
fake_httpx.post = lambda *args, **kwargs: None
fake_dotenv = types.ModuleType("dotenv")
fake_dotenv.dotenv_values = lambda _path: {}
sys.modules.setdefault("httpx", fake_httpx)
sys.modules.setdefault("dotenv", fake_dotenv)
fake_psycopg = types.ModuleType("psycopg")
fake_psycopg_rows = types.ModuleType("psycopg.rows")
fake_psycopg_rows.dict_row = object()
sys.modules.setdefault("psycopg", fake_psycopg)
sys.modules.setdefault("psycopg.rows", fake_psycopg_rows)


BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from app.services.google_token_service import (  # noqa: E402
    GoogleOAuthNeedsReconnectError,
    get_valid_google_access_token,
)


class GoogleTokenServiceTestCase(unittest.TestCase):
    def test_uses_existing_access_token_when_not_expired(self):
        oauth_connection = {
            "id": "oauth-1",
            "access_token_encrypted": "encrypted-access",
            "refresh_token_encrypted": "encrypted-refresh",
            "token_expiry": datetime.now(timezone.utc) + timedelta(minutes=15),
        }

        with patch(
            "app.services.google_token_service.decrypt_text",
            return_value="access-token",
        ) as decrypt_mock, patch(
            "app.services.google_token_service.httpx.post"
        ) as post_mock:
            access_token = get_valid_google_access_token(object(), oauth_connection)

        self.assertEqual("access-token", access_token)
        decrypt_mock.assert_called_once_with("encrypted-access")
        post_mock.assert_not_called()

    def test_refreshes_expired_access_token_and_updates_connection(self):
        oauth_connection = {
            "id": "oauth-1",
            "access_token_encrypted": "expired-access",
            "refresh_token_encrypted": "encrypted-refresh",
            "token_expiry": datetime.now(timezone.utc) - timedelta(minutes=5),
        }
        response = MagicMock()
        response.json.return_value = {
            "access_token": "new-access-token",
            "expires_in": 3600,
        }

        with patch(
            "app.services.google_token_service.decrypt_text",
            return_value="refresh-token",
        ) as decrypt_mock, patch(
            "app.services.google_token_service.encrypt_text",
            return_value="encrypted-new-access",
        ) as encrypt_mock, patch(
            "app.services.google_token_service.httpx.post",
            return_value=response,
        ) as post_mock, patch(
            "app.services.google_token_service.update_google_oauth_access_token"
        ) as update_mock:
            access_token = get_valid_google_access_token(object(), oauth_connection)

        self.assertEqual("new-access-token", access_token)
        decrypt_mock.assert_called_once_with("encrypted-refresh")
        encrypt_mock.assert_called_once_with("new-access-token")
        response.raise_for_status.assert_called_once()
        post_mock.assert_called_once()
        self.assertEqual("https://oauth2.googleapis.com/token", post_mock.call_args.args[0])
        self.assertEqual(
            "refresh_token",
            post_mock.call_args.kwargs["data"]["grant_type"],
        )
        update_mock.assert_called_once()
        self.assertEqual(
            "encrypted-new-access",
            update_mock.call_args.kwargs["access_token_encrypted"],
        )
        self.assertEqual("active", update_mock.call_args.kwargs["status"])

    def test_expired_access_token_without_refresh_token_needs_reconnect(self):
        oauth_connection = {
            "id": "oauth-1",
            "access_token_encrypted": "expired-access",
            "refresh_token_encrypted": None,
            "token_expiry": datetime.now(timezone.utc) - timedelta(minutes=5),
        }

        with self.assertRaises(GoogleOAuthNeedsReconnectError), patch(
            "app.services.google_token_service.httpx.post"
        ) as post_mock:
            get_valid_google_access_token(object(), oauth_connection)

        post_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
