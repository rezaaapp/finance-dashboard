from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_current_user
from app.database import get_db_connection
from app.repositories.google_oauth_repository import (
    disconnect_google_oauth_connection,
    get_google_oauth_connection_status,
)
from app.repositories.workspaces import (
    ensure_default_workspace_for_user,
    get_primary_workspace_for_user,
)


router = APIRouter(
    prefix="/api/google/connection",
    tags=["Google Connection"],
)


def get_current_workspace(current_user=Depends(require_current_user)):
    with get_db_connection() as connection:
        with connection.transaction():
            workspace = get_primary_workspace_for_user(
                connection,
                user_id=current_user["sub"],
            )

            # TODO: Replace this default workspace fallback when OAuth onboarding
            # has a final workspace selection flow.
            if not workspace:
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
    with get_db_connection() as connection:
        connection_status = get_google_oauth_connection_status(
            connection,
            workspace_id=str(workspace["id"]),
            user_id=current_user["sub"],
        )

    if not connection_status:
        return {"connected": False}

    return {
        "connected": True,
        "google_email": connection_status["google_email"],
        "status": connection_status["status"],
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
