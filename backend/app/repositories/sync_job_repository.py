from psycopg.rows import dict_row


def create_sync_job(
    connection,
    *,
    workspace_id: str,
    sheet_source_id: str,
    job_type: str = "google_sheet_sync",
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into sync_jobs (
                workspace_id,
                sheet_source_id,
                job_type,
                status
            )
            values (%s, %s, %s, 'queued')
            returning *
            """,
            (workspace_id, sheet_source_id, job_type),
        )

        return cursor.fetchone()


def mark_sync_job_running(connection, *, job_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update sync_jobs
            set
                status = 'running',
                started_at = coalesce(started_at, now())
            where id = %s
            returning *
            """,
            (job_id,),
        )

        return cursor.fetchone()


def mark_sync_job_success(
    connection,
    *,
    job_id: str,
    total_rows: int,
    inserted_rows: int,
    updated_rows: int,
    skipped_rows: int,
    failed_rows: int,
    error_message: str | None = None,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update sync_jobs
            set
                status = 'success',
                total_rows = %s,
                inserted_rows = %s,
                updated_rows = %s,
                skipped_rows = %s,
                failed_rows = %s,
                error_message = %s,
                finished_at = now()
            where id = %s
            returning *
            """,
            (
                total_rows,
                inserted_rows,
                updated_rows,
                skipped_rows,
                failed_rows,
                error_message,
                job_id,
            ),
        )

        return cursor.fetchone()


def update_sync_job_progress(
    connection,
    *,
    job_id: str,
    total_rows: int,
    inserted_rows: int,
    updated_rows: int,
    skipped_rows: int,
    failed_rows: int,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update sync_jobs
            set
                total_rows = %s,
                inserted_rows = %s,
                updated_rows = %s,
                skipped_rows = %s,
                failed_rows = %s
            where id = %s
            returning *
            """,
            (
                total_rows,
                inserted_rows,
                updated_rows,
                skipped_rows,
                failed_rows,
                job_id,
            ),
        )

        return cursor.fetchone()


def mark_sync_job_failed(
    connection,
    *,
    job_id: str,
    error_message: str,
    total_rows: int = 0,
    inserted_rows: int = 0,
    updated_rows: int = 0,
    skipped_rows: int = 0,
    failed_rows: int = 0,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update sync_jobs
            set
                status = 'failed',
                total_rows = %s,
                inserted_rows = %s,
                updated_rows = %s,
                skipped_rows = %s,
                failed_rows = %s,
                error_message = %s,
                finished_at = now()
            where id = %s
            returning *
            """,
            (
                total_rows,
                inserted_rows,
                updated_rows,
                skipped_rows,
                failed_rows,
                error_message,
                job_id,
            ),
        )

        return cursor.fetchone()


def get_sync_job(connection, *, workspace_id: str, job_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select *
            from sync_jobs
            where workspace_id = %s
              and id = %s
            """,
            (workspace_id, job_id),
        )

        return cursor.fetchone()
