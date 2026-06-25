from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.google_connection import get_current_workspace
from app.auth import require_current_user
from app.database import get_db_connection
from app.imports.services.import_service import (
    ImportService,
    InvalidTargetSheetHeaderError,
    MissingGoogleSheetSourceError,
    MissingTargetSheetError,
)


router = APIRouter(
    prefix="/api/import",
    tags=["Import"],
)


class ImportReviewItemUpdateRequest(BaseModel):
    draft_id: str
    merchant_display: str | None = None
    category: str = ""
    notes: str = ""


class ImportReviewActionRequest(BaseModel):
    draft_ids: list[str] = Field(default_factory=list)
    item_updates: list[ImportReviewItemUpdateRequest] = Field(default_factory=list)
    sheet_source_id: str | None = None
    sheet_name: str | None = None


class ImportRetrySyncRequest(BaseModel):
    sheet_source_id: str | None = None
    sheet_name: str | None = None


@router.post("/upload")
def upload_import_file(
    file: UploadFile = File(...),
    statement_owner: str = Form(...),
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
                statement_owner=statement_owner,
            )

    return result.model_dump()


@router.get("/category-options")
def get_import_category_options(
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    service = ImportService()

    with get_db_connection() as connection:
        return service.get_category_options_payload(
            connection,
            workspace_id=str(workspace["id"]),
        )


@router.get("/review/{job_id}")
def get_import_review(
    job_id: str,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    service = ImportService()

    with get_db_connection() as connection:
        payload = service.get_review_payload(
            connection,
            workspace_id=str(workspace["id"]),
            job_id=job_id,
            limit=limit,
            offset=offset,
        )

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import review not found",
        )

    return payload


@router.get("/history")
def get_import_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    service = ImportService()

    with get_db_connection() as connection:
        payload = service.get_history_payload(
            connection,
            workspace_id=str(workspace["id"]),
            limit=limit,
            offset=offset,
        )

    return payload


@router.get("/history/{job_id}")
def get_import_history_detail(
    job_id: str,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    service = ImportService()

    with get_db_connection() as connection:
        payload = service.get_history_detail_payload(
            connection,
            workspace_id=str(workspace["id"]),
            job_id=job_id,
        )

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import history not found",
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

    try:
        with get_db_connection() as connection:
            approval_plan = service.prepare_review_approval(
                connection,
                workspace=workspace,
                current_user=current_user,
                workspace_id=str(workspace["id"]),
                import_job_id=job_id,
                draft_ids=request.draft_ids,
                item_updates=[item.model_dump() for item in request.item_updates],
                sheet_source_id=request.sheet_source_id,
                sheet_name=request.sheet_name,
            )
            if approval_plan is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Import review not found",
                )

        with get_db_connection() as connection:
            with connection.transaction():
                persistence_result = service.persist_review_approval(
                    connection,
                    workspace_id=str(workspace["id"]),
                    import_job_id=job_id,
                    approval_plan=approval_plan,
                )

        with get_db_connection() as connection:
            sync_result = service.execute_sync_plan(
                connection,
                workspace=workspace,
                current_user=current_user,
                sync_plan=persistence_result["sync_plan"],
            )

        with get_db_connection() as connection:
            with connection.transaction():
                result = service.record_review_sync_result(
                    connection,
                    workspace_id=str(workspace["id"]),
                    import_job_id=job_id,
                    transaction_fingerprints=persistence_result["transaction_fingerprints"],
                    sync_result=sync_result,
                )
                review_payload = service.get_review_payload(
                    connection,
                    workspace_id=str(workspace["id"]),
                    job_id=job_id,
                )
    except MissingGoogleSheetSourceError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=exc.to_response(),
        )
    except MissingTargetSheetError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=exc.to_response(),
        )
    except InvalidTargetSheetHeaderError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=exc.to_response(),
        )

    return {
        "approved_count": persistence_result["approved_count"],
        "skipped_existing_count": persistence_result["skipped_existing_count"],
        "skipped_rejected_count": persistence_result["skipped_rejected_count"],
        "draft_ids": persistence_result["draft_ids"],
        **result,
        "review": review_payload,
    }


@router.post("/retry-sync/{job_id}")
def retry_import_sync(
    job_id: str,
    request: ImportRetrySyncRequest,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    service = ImportService()

    try:
        with get_db_connection() as connection:
            retry_plan = service.prepare_retry_sync(
                connection,
                workspace=workspace,
                current_user=current_user,
                workspace_id=str(workspace["id"]),
                import_job_id=job_id,
                sheet_source_id=request.sheet_source_id,
                sheet_name=request.sheet_name,
            )
            if not retry_plan:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Import history not found",
                )

        if retry_plan.get("status") == "skipped":
            return retry_plan

        with get_db_connection() as connection:
            sync_result = service.execute_sync_plan(
                connection,
                workspace=workspace,
                current_user=current_user,
                sync_plan=retry_plan["sync_plan"],
            )

        with get_db_connection() as connection:
            with connection.transaction():
                result = service.record_retry_sync_result(
                    connection,
                    workspace_id=str(workspace["id"]),
                    import_job_id=job_id,
                    retry_plan=retry_plan,
                    sync_result=sync_result,
                )
    except MissingGoogleSheetSourceError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=exc.to_response(),
        )
    except MissingTargetSheetError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=exc.to_response(),
        )
    except InvalidTargetSheetHeaderError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=exc.to_response(),
        )

    return result


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
