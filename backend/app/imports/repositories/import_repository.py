from psycopg.rows import dict_row


def create_import_job(
    connection,
    *,
    workspace_id: str,
    provider: str,
    filename: str,
    status: str = "uploaded",
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into import_jobs (
                workspace_id,
                provider,
                filename,
                status
            )
            values (%s, %s, %s, %s)
            returning *
            """,
            (workspace_id, provider, filename, status),
        )

        return cursor.fetchone()


def get_import_job(connection, *, workspace_id: str, job_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select *
            from import_jobs
            where workspace_id = %s
              and id = %s
            """,
            (workspace_id, job_id),
        )

        return cursor.fetchone()
