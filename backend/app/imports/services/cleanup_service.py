from datetime import datetime, timezone
from threading import Event, Thread
import time

from app.database import get_db_connection
from app.imports.models.import_models import ImportJobStatus
from app.imports.repositories.import_repository import (
    delete_import_draft_transactions_for_job,
    get_import_job,
    list_expired_import_jobs,
    mark_import_job_cleanup_completed,
    mark_import_job_expired,
    mark_import_job_temp_file_deleted,
)
from app.imports.utils.temp_storage import delete_temp_import_file


CLEANUP_INTERVAL_SECONDS = 60 * 60
_cleanup_stop_event = Event()
_cleanup_thread = None


class ImportCleanupService:
    def delete_temp_pdf_for_job(self, connection, *, workspace_id: str, job_id: str) -> bool:
        job = get_import_job(
            connection,
            workspace_id=workspace_id,
            job_id=job_id,
        )

        if not job or job.get("temp_file_deleted_at"):
            return False

        temp_path = str(job.get("temp_file_path") or "").strip()

        try:
            deleted = delete_temp_import_file(temp_path)
        except OSError:
            deleted = False

        mark_import_job_temp_file_deleted(
            connection,
            job_id=job_id,
        )

        return deleted

    def cleanup_expired_jobs(self, connection, *, now: datetime | None = None) -> dict:
        reference_time = now or datetime.now(timezone.utc)
        jobs = list_expired_import_jobs(
            connection,
            expires_before=reference_time,
        )
        cleaned_job_ids = []

        for job in jobs:
            workspace_id = str(job["workspace_id"])
            job_id = str(job["id"])

            if job["status"] != ImportJobStatus.EXPIRED.value:
                mark_import_job_expired(
                    connection,
                    job_id=job_id,
                )

            self.delete_temp_pdf_for_job(
                connection,
                workspace_id=workspace_id,
                job_id=job_id,
            )
            delete_import_draft_transactions_for_job(
                connection,
                import_job_id=job_id,
            )
            mark_import_job_cleanup_completed(
                connection,
                job_id=job_id,
            )
            cleaned_job_ids.append(job_id)

        return {
            "cleaned_jobs": len(cleaned_job_ids),
            "job_ids": cleaned_job_ids,
        }


def run_import_cleanup_cycle():
    service = ImportCleanupService()

    with get_db_connection() as connection:
        with connection.transaction():
            return service.cleanup_expired_jobs(connection)


def start_import_cleanup_scheduler():
    global _cleanup_thread

    if _cleanup_thread and _cleanup_thread.is_alive():
        return

    _cleanup_stop_event.clear()

    def _worker():
        while not _cleanup_stop_event.is_set():
            try:
                run_import_cleanup_cycle()
            except Exception:
                pass

            for _ in range(CLEANUP_INTERVAL_SECONDS):
                if _cleanup_stop_event.is_set():
                    return
                time.sleep(1)

    _cleanup_thread = Thread(
        target=_worker,
        name="import-cleanup-scheduler",
        daemon=True,
    )
    _cleanup_thread.start()


def stop_import_cleanup_scheduler():
    _cleanup_stop_event.set()
