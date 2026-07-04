from fastapi import APIRouter, Depends, HTTPException, status

from app.api.google_connection import get_current_workspace
from app.auth import require_current_user
from app.config import settings
from app.database import get_db_connection
from app.security.workspace_permissions import require_workspace_manager
from app.services.workspace_reset_service import factory_reset_workspace_data


router = APIRouter(prefix="/api/workspace", tags=["Workspace Reset"])


@router.post("/factory-reset-data")
def factory_reset_workspace(
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    if settings.APP_ENV != "local-dev":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace factory reset is not available",
        )
    require_workspace_manager(
        current_user=current_user,
        workspace=workspace,
        detail="Only workspace owners or super admins can reset workspace data.",
    )
    workspace_id = str(workspace["id"])
    with get_db_connection() as connection:
        with connection.transaction():
            deleted = factory_reset_workspace_data(
                connection,
                workspace_id=workspace_id,
            )
    return {
        "workspace_id": workspace_id,
        "deleted": deleted,
        "preserved": {
            "google_sheet_config": True,
            "oauth_connection": True,
            "workspace": True,
            "users": True,
            "memberships": True,
        },
        "google_sheet_untouched": True,
    }
