from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.api.google_connection import get_current_workspace
from app.auth import require_current_user
from app.database import get_db_connection
from app.imports.services.import_service import ImportService


router = APIRouter(
    prefix="/api/import",
    tags=["Import"],
)


class ImportReviewItemUpdateRequest(BaseModel):
    draft_id: str
    category: str = ""
    notes: str = ""


class ImportReviewActionRequest(BaseModel):
    draft_ids: list[str] = Field(default_factory=list)
    item_updates: list[ImportReviewItemUpdateRequest] = Field(default_factory=list)


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


@router.get("/review/{job_id}")
def get_import_review(
    job_id: str,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    service = ImportService()

    with get_db_connection() as connection:
        payload = service.get_review_payload(
            connection,
            workspace_id=str(workspace["id"]),
            job_id=job_id,
        )

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import review not found",
        )

    return payload


@router.post("/review/{job_id}/approve")
def approve_import_review(
    job_id: str,
    request: ImportReviewActionRequest,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    service = ImportService()

    with get_db_connection() as connection:
        with connection.transaction():
            result = service.approve_review_transactions(
                connection,
                workspace=workspace,
                current_user=current_user,
                workspace_id=str(workspace["id"]),
                import_job_id=job_id,
                draft_ids=request.draft_ids,
                item_updates=[item.model_dump() for item in request.item_updates],
            )
            if result is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Import review not found",
                )
            review_payload = service.get_review_payload(
                connection,
                workspace_id=str(workspace["id"]),
                job_id=job_id,
            )

    return {
        **result,
        "review": review_payload,
    }


@router.post("/review/{job_id}/reject")
def reject_import_review(
    job_id: str,
    request: ImportReviewActionRequest,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    service = ImportService()

    with get_db_connection() as connection:
        with connection.transaction():
            result = service.reject_review_transactions(
                connection,
                workspace_id=str(workspace["id"]),
                import_job_id=job_id,
                draft_ids=request.draft_ids,
            )
            if result is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Import review not found",
                )
            review_payload = service.get_review_payload(
                connection,
                workspace_id=str(workspace["id"]),
                job_id=job_id,
            )

    return {
        **result,
        "review": review_payload,
    }
