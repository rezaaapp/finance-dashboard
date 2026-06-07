from fastapi import APIRouter, Depends

from app.auth import require_current_user
from app.database import get_db_connection
from app.repositories.workspaces import get_user_workspaces


router = APIRouter(
    prefix="/api/workspaces",
    tags=["Workspaces"],
)


def _serialize_workspace(workspace):
    return {
        "id": str(workspace["id"]),
        "name": workspace["name"],
        "role": workspace["role"],
    }


@router.get("")
def list_workspaces(current_user=Depends(require_current_user)):
    with get_db_connection() as connection:
        workspaces = get_user_workspaces(
            connection,
            user_id=current_user["sub"],
        )

    return {
        "workspaces": [_serialize_workspace(workspace) for workspace in workspaces],
    }
