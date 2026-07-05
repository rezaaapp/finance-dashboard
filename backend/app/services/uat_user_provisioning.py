from app.config import settings
from app.repositories.password_credentials import create_password_credential
from app.repositories.users import create_user
from app.repositories.workspaces import (
    create_workspace,
    upsert_workspace_configuration,
    upsert_workspace_member,
)
from app.security.passwords import hash_password


SAFE_ENVIRONMENTS = {"local-dev", "dev", "uat"}
BLOCKED_ENVIRONMENTS = {"local-prod", "prod"}
TESTER_ROLES = {"owner", "member", "user"}


def is_uat_provisioning_allowed() -> bool:
    app_env = str(settings.APP_ENV or "").strip().lower()
    env_profile = str(settings.ENV_PROFILE or "").strip().lower()
    if app_env in BLOCKED_ENVIRONMENTS or env_profile in BLOCKED_ENVIRONMENTS:
        return False
    return app_env in SAFE_ENVIRONMENTS or env_profile in SAFE_ENVIRONMENTS


def provision_test_user(
    connection,
    *,
    email: str,
    name: str,
    role: str,
    password: str,
    workspace_name: str,
):
    normalized_role = str(role or "").strip().lower()
    if normalized_role not in TESTER_ROLES:
        raise ValueError("Role tester harus owner, member, atau user.")

    password_hash = hash_password(password)
    user = create_user(
        connection,
        email=email,
        name=name,
        role=normalized_role,
    )
    create_password_credential(
        connection,
        user_id=str(user["id"]),
        password_hash=password_hash,
    )
    workspace = create_workspace(connection, name=workspace_name)
    membership = upsert_workspace_member(
        connection,
        workspace_id=str(workspace["id"]),
        user_id=str(user["id"]),
        role="owner",
    )
    configuration = upsert_workspace_configuration(
        connection,
        workspace_id=str(workspace["id"]),
    )

    return {
        "user": user,
        "workspace": workspace,
        "membership": membership,
        "configuration": configuration,
    }
