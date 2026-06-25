import unittest
from pathlib import Path

from fastapi import HTTPException

from backend.app.security.workspace_permissions import (
    can_manage_workspace,
    require_workspace_manager,
)


class WorkspacePermissionsTestCase(unittest.TestCase):
    def test_workspace_owner_can_manage_workspace(self):
        workspace = {"id": "workspace-1", "role": "owner"}

        self.assertTrue(
            can_manage_workspace(
                current_user={"role": "user"},
                workspace=workspace,
            )
        )
        self.assertIs(
            workspace,
            require_workspace_manager(
                current_user={"role": "user"},
                workspace=workspace,
            ),
        )

    def test_super_admin_can_manage_accessible_workspace(self):
        workspace = {"id": "workspace-1", "role": "member"}

        self.assertTrue(
            can_manage_workspace(
                current_user={"role": "super_admin"},
                workspace=workspace,
            )
        )

    def test_workspace_member_cannot_manage_workspace(self):
        with self.assertRaises(HTTPException) as raised:
            require_workspace_manager(
                current_user={"role": "user"},
                workspace={"id": "workspace-1", "role": "member"},
                detail="Members cannot change workspace configuration.",
            )

        self.assertEqual(403, raised.exception.status_code)
        self.assertEqual(
            "Members cannot change workspace configuration.",
            raised.exception.detail,
        )

    def test_missing_workspace_is_not_authorized(self):
        with self.assertRaises(HTTPException) as raised:
            require_workspace_manager(
                current_user={"role": "super_admin"},
                workspace=None,
            )

        self.assertEqual(404, raised.exception.status_code)

    def test_unknown_workspace_role_is_denied(self):
        self.assertFalse(
            can_manage_workspace(
                current_user={"role": "user"},
                workspace={"id": "workspace-1", "role": "admin"},
            )
        )

    def test_workspace_mutation_endpoints_use_central_policy(self):
        app_root = Path(__file__).resolve().parents[1] / "app"
        dashboard_source = (app_root / "api" / "dashboard.py").read_text(
            encoding="utf-8"
        )
        invitations_source = (
            app_root / "api" / "workspace_invitations.py"
        ).read_text(encoding="utf-8")
        configuration_block = dashboard_source.split(
            "def update_workspace_configuration(",
            maxsplit=1,
        )[1].split("\n@router.", maxsplit=1)[0]

        self.assertIn("require_workspace_manager(", configuration_block)
        self.assertNotIn('current_user.get("role")', configuration_block)
        self.assertIn(
            "return require_workspace_manager(",
            invitations_source,
        )

    def test_dashboard_read_endpoints_use_workspace_access_not_global_premium_role(self):
        app_root = Path(__file__).resolve().parents[1] / "app"
        dashboard_source = (app_root / "api" / "dashboard.py").read_text(
            encoding="utf-8"
        )

        read_endpoint_names = (
            "category_heatmap",
            "transactions",
            "category_trends",
            "source_dana_analytics",
            "monthly_allocation",
            "personal_analytics",
            "grocery_vs_food",
            "anomalies",
            "latest_insight",
            "budget_forecast",
        )

        for endpoint_name in read_endpoint_names:
            with self.subTest(endpoint_name=endpoint_name):
                endpoint_block = dashboard_source.split(
                    f"def {endpoint_name}(",
                    maxsplit=1,
                )[1].split("\n@router.", maxsplit=1)[0]

                self.assertIn(
                    "sheet_context=Depends(get_active_sheet_context)",
                    endpoint_block,
                )
                self.assertNotIn("premium_user=Depends", endpoint_block)
                self.assertNotIn("require_premium_role", endpoint_block)


if __name__ == "__main__":
    unittest.main()
