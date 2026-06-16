from fastapi import APIRouter, Depends, File, UploadFile

from app.api.google_connection import get_current_workspace
from app.auth import require_current_user
from app.database import get_db_connection
from app.imports.services.import_service import ImportService


router = APIRouter(
    prefix="/api/import",
    tags=["Import"],
)


@router.post("/upload")
def upload_import_file(
    file: UploadFile = File(...),
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    service = ImportService()

    with get_db_connection() as connection:
        with connection.transaction():
            result = service.receive_upload(
                connection,
                workspace_id=str(workspace["id"]),
                file=file,
            )

    return result.model_dump()
