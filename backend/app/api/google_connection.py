from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.auth import require_current_user
from app.database import get_db_connection
from app.repositories.google_oauth_repository import (
    disconnect_google_oauth_connection,
    get_active_google_oauth_connection,
    get_google_oauth_connection_status,
)
from app.imports.services.spreadsheet_sync_service import SpreadsheetSyncService
from app.services.google_token_service import (
    can_refresh_google_access_token,
    is_google_access_token_expired,
)
from app.repositories.workspaces import (
    ensure_default_workspace_for_user,
    get_primary_workspace_for_user,
    get_workspace_for_user,
)


router = APIRouter(
    prefix="/api/google/connection",
    tags=["Google Connection"],
)


def get_current_workspace(
    current_user=Depends(require_current_user),
    active_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
):
    with get_db_connection() as connection:
        with connection.transaction():
            workspace = None

            if active_workspace_id:
                workspace = get_workspace_for_user(
                    connection,
                    user_id=current_user["sub"],
                    workspace_id=active_workspace_id,
                )

                if not workspace:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Workspace access denied",
                    )
            else:
                workspace = get_primary_workspace_for_user(
                    connection,
                    user_id=current_user["sub"],
                )

            # TODO: Replace this default workspace fallback when OAuth onboarding
            # has a final workspace selection flow.
            if not workspace and not active_workspace_id:
                workspace = ensure_default_workspace_for_user(
                    connection,
                    user_id=current_user["sub"],
                    user_name=current_user.get("name") or "User",
                )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    return workspace


@router.get("/status")
def get_connection_status(
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    sync_service = SpreadsheetSyncService()

    with get_db_connection() as connection:
        connection_status = get_google_oauth_connection_status(
            connection,
            workspace_id=str(workspace["id"]),
            user_id=current_user["sub"],
        )
        active_connection = get_active_google_oauth_connection(
            connection,
            workspace_id=str(workspace["id"]),
            user_id=current_user["sub"],
        )

    if not connection_status:
        return {"connected": False}

    token_expired = (
        is_google_access_token_expired(active_connection)
        if active_connection
        else False
    )
    can_refresh = (
        can_refresh_google_access_token(active_connection)
        if active_connection
        else False
    )
    needs_reconnect = sync_service.requires_reconnect(
        (active_connection or {}).get("scopes") or []
    ) or (token_expired and not can_refresh)

    return {
        "connected": True,
        "google_email": connection_status["google_email"],
        "status": connection_status["status"],
        "needs_reconnect": needs_reconnect,
        "authorization_failed": token_expired and not can_refresh,
    }


@router.post("/disconnect")
def disconnect_connection(
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    with get_db_connection() as connection:
        with connection.transaction():
            disconnect_google_oauth_connection(
                connection,
                workspace_id=str(workspace["id"]),
                user_id=current_user["sub"],
            )

    return {"disconnected": True}
