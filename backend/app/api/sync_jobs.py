from fastapi import APIRouter, Depends, HTTPException, status

from app.api.google_connection import get_current_workspace
from app.auth import require_current_user
from app.database import get_db_connection
from app.repositories.sync_job_repository import get_sync_job


router = APIRouter(
    prefix="/api/sync-jobs",
    tags=["Sync Jobs"],
)


def serialize_sync_job(job):
    return {
        "job_id": str(job["id"]),
        "source_id": str(job["sheet_source_id"]) if job["sheet_source_id"] else None,
        "job_type": job["job_type"],
        "status": job["status"],
        "total_rows": job["total_rows"],
        "inserted_rows": job["inserted_rows"],
        "updated_rows": job["updated_rows"],
        "skipped_rows": job["skipped_rows"],
        "failed_rows": job["failed_rows"],
        "error_message": job["error_message"],
        "started_at": job["started_at"],
        "finished_at": job["finished_at"],
        "created_at": job["created_at"],
    }


@router.get("/{job_id}")
def get_sync_job_status(
    job_id: str,
    current_user=Depends(require_current_user),
    workspace=Depends(get_current_workspace),
):
    with get_db_connection() as connection:
        job = get_sync_job(
            connection,
            workspace_id=str(workspace["id"]),
            job_id=job_id,
        )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sync job not found",
        )

    return serialize_sync_job(job)
