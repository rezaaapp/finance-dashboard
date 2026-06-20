from fastapi import HTTPException, status


GLOBAL_WORKSPACE_ADMIN_ROLES = {"super_admin"}
WORKSPACE_MANAGEMENT_ROLES = {"owner"}


def can_manage_workspace(*, current_user: dict, workspace: dict | None) -> bool:
    if not workspace:
        return False

    global_role = str(current_user.get("role") or "").strip().lower()
    workspace_role = str(workspace.get("role") or "").strip().lower()

    return (
        global_role in GLOBAL_WORKSPACE_ADMIN_ROLES
        or workspace_role in WORKSPACE_MANAGEMENT_ROLES
    )


def require_workspace_manager(
    *,
    current_user: dict,
    workspace: dict | None,
    detail: str = "Only workspace owners can perform this action.",
) -> dict:
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    if not can_manage_workspace(
        current_user=current_user,
        workspace=workspace,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )

    return workspace
