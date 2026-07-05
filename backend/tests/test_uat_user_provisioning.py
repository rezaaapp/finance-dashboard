import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import HTTPException


os.environ.setdefault("DASHBOARD_USERNAME", "admin")
os.environ.setdefault("DASHBOARD_PASSWORD", "test-password")
os.environ.setdefault("DASHBOARD_AUTH_TOKEN", "static-test-token")
os.environ.setdefault("JWT_SECRET", "jwt-test-secret")
os.environ.setdefault("TOKEN_ENCRYPTION_SECRET", "encrypt-test-secret")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.admin import UatTestUserProvision, provision_uat_test_user
from app.api.auth import LoginRequest, login
from app.auth import require_super_admin
from app.security.passwords import hash_password, verify_password
from app.services.uat_user_provisioning import (
    is_uat_provisioning_allowed,
    provision_test_user,
)


class FakeTransaction:
    def __init__(self):
        self.rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, _exc, _traceback):
        self.rolled_back = exc_type is not None
        return False


class FakeConnection:
    def __init__(self):
        self.transaction_state = FakeTransaction()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, _exc, _traceback):
        return False

    def transaction(self):
        return self.transaction_state


class UatUserProvisioningTestCase(unittest.TestCase):
    def setUp(self):
        self.payload = UatTestUserProvision(
            email="andi@example.com",
            name="Andi",
            role="owner",
            password="Omon-7Kp2xQ!",
            workspace_name="Andi's Household",
        )
        self.result = {
            "user": {
                "id": "11111111-1111-4111-8111-111111111111",
                "email": "andi@example.com",
                "name": "Andi",
                "avatar_url": None,
                "role": "owner",
                "created_at": "now",
                "updated_at": "now",
            },
            "workspace": {
                "id": "22222222-2222-4222-8222-222222222222",
                "name": "Andi's Household",
            },
            "membership": {"role": "owner"},
            "configuration": {"google_sheet_id": None},
        }

    def test_password_is_one_way_hashed_and_verifiable(self):
        encoded = hash_password(self.payload.password)
        self.assertNotIn(self.payload.password, encoded)
        self.assertTrue(verify_password(self.payload.password, encoded))
        self.assertFalse(verify_password("wrong-password", encoded))

    @patch("app.services.uat_user_provisioning.upsert_workspace_configuration")
    @patch("app.services.uat_user_provisioning.upsert_workspace_member")
    @patch("app.services.uat_user_provisioning.create_workspace")
    @patch("app.services.uat_user_provisioning.create_password_credential")
    @patch("app.services.uat_user_provisioning.create_user")
    def test_service_creates_user_credential_workspace_owner_and_configuration(
        self,
        create_user_mock,
        credential_mock,
        workspace_mock,
        member_mock,
        configuration_mock,
    ):
        create_user_mock.return_value = self.result["user"]
        workspace_mock.return_value = self.result["workspace"]
        member_mock.return_value = self.result["membership"]
        configuration_mock.return_value = self.result["configuration"]

        result = provision_test_user(
            MagicMock(),
            email=self.payload.email,
            name=self.payload.name,
            role=self.payload.role,
            password=self.payload.password,
            workspace_name=self.payload.workspace_name,
        )

        self.assertEqual("owner", result["membership"]["role"])
        credential_hash = credential_mock.call_args.kwargs["password_hash"]
        self.assertNotEqual(self.payload.password, credential_hash)
        self.assertTrue(verify_password(self.payload.password, credential_hash))
        configuration_mock.assert_called_once_with(
            unittest.mock.ANY,
            workspace_id=self.result["workspace"]["id"],
        )

    def test_super_admin_can_provision_in_safe_environment(self):
        connection = FakeConnection()
        with patch("app.api.admin.is_uat_provisioning_allowed", return_value=True), patch(
            "app.api.admin.get_db_connection", return_value=connection
        ), patch("app.api.admin.provision_test_user", return_value=self.result):
            response = provision_uat_test_user(self.payload)

        self.assertTrue(response["created"])
        self.assertEqual("Andi's Household", response["workspace_name"])
        self.assertNotIn("password", response)
        self.assertFalse(connection.transaction_state.rolled_back)

    def test_provisioned_password_can_login(self):
        password_hash = hash_password(self.payload.password)
        login_user = {**self.result["user"], "password_hash": password_hash}
        workspace = {
            **self.result["workspace"],
            "role": "owner",
            "google_sheet_id": None,
            "google_sheet_sources": [],
        }
        with patch("app.api.auth.authenticate_user", return_value=False), patch(
            "app.api.auth.get_db_connection", return_value=FakeConnection()
        ), patch(
            "app.api.auth.get_password_login_user", return_value=login_user
        ), patch(
            "app.api.auth.ensure_default_workspace_for_user", return_value=workspace
        ):
            response = login(LoginRequest(
                username=self.payload.email,
                password=self.payload.password,
            ))

        self.assertEqual(self.payload.email, response["email"])
        self.assertEqual(self.result["workspace"]["id"], response["workspaceId"])

    def test_duplicate_email_is_rejected_cleanly(self):
        with patch("app.api.admin.is_uat_provisioning_allowed", return_value=True), patch(
            "app.api.admin.get_db_connection", return_value=FakeConnection()
        ), patch(
            "app.api.admin.provision_test_user",
            side_effect=Exception("duplicate key violates users_email_key"),
        ):
            with self.assertRaises(HTTPException) as context:
                provision_uat_test_user(self.payload)
        self.assertEqual(409, context.exception.status_code)

    def test_production_environment_blocks_provisioning(self):
        with patch("app.api.admin.is_uat_provisioning_allowed", return_value=False):
            with self.assertRaises(HTTPException) as context:
                provision_uat_test_user(self.payload)
        self.assertEqual(403, context.exception.status_code)

    def test_environment_gate_matches_uat_and_production_contract(self):
        for environment in ("local-dev", "dev", "uat"):
            with self.subTest(environment=environment), patch(
                "app.services.uat_user_provisioning.settings.APP_ENV", environment
            ), patch(
                "app.services.uat_user_provisioning.settings.ENV_PROFILE", environment
            ):
                self.assertTrue(is_uat_provisioning_allowed())

        for environment in ("local-prod", "prod"):
            with self.subTest(environment=environment), patch(
                "app.services.uat_user_provisioning.settings.APP_ENV", environment
            ), patch(
                "app.services.uat_user_provisioning.settings.ENV_PROFILE", environment
            ):
                self.assertFalse(is_uat_provisioning_allowed())

        with patch(
            "app.services.uat_user_provisioning.settings.APP_ENV", "prod"
        ), patch(
            "app.services.uat_user_provisioning.settings.ENV_PROFILE", "uat"
        ):
            self.assertFalse(is_uat_provisioning_allowed())

        with patch(
            "app.services.uat_user_provisioning.settings.APP_ENV", "prod"
        ), patch(
            "app.services.uat_user_provisioning.settings.ENV_PROFILE", "uat"
        ):
            self.assertFalse(is_uat_provisioning_allowed())

        with patch(
            "app.services.uat_user_provisioning.settings.APP_ENV", "prod"
        ), patch(
            "app.services.uat_user_provisioning.settings.ENV_PROFILE", "uat"
        ):
            self.assertFalse(is_uat_provisioning_allowed())

    def test_non_super_admin_is_rejected(self):
        with self.assertRaises(HTTPException) as context:
            require_super_admin(auth_payload={"role": "owner"})
        self.assertEqual(403, context.exception.status_code)

    def test_transaction_marks_rollback_when_provisioning_fails(self):
        connection = FakeConnection()
        with patch("app.api.admin.is_uat_provisioning_allowed", return_value=True), patch(
            "app.api.admin.get_db_connection", return_value=connection
        ), patch(
            "app.api.admin.provision_test_user",
            side_effect=RuntimeError("configuration failed"),
        ):
            with self.assertRaises(RuntimeError):
                provision_uat_test_user(self.payload)
        self.assertTrue(connection.transaction_state.rolled_back)


if __name__ == "__main__":
    unittest.main()
