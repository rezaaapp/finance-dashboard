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


def get_existing_transaction_fingerprints(
    connection,
    *,
    workspace_id: str,
    transaction_fingerprints: list[str],
):
    if not transaction_fingerprints:
        return set()

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select distinct draft.transaction_fingerprint
            from import_draft_transactions as draft
            inner join import_jobs as job
                on job.id = draft.import_job_id
            where job.workspace_id = %s
              and job.status in ('approved', 'completed')
              and draft.transaction_fingerprint = any(%s)
            """,
            (workspace_id, transaction_fingerprints),
        )

        rows = cursor.fetchall()

    return {row["transaction_fingerprint"] for row in rows}


def create_import_draft_transactions(
    connection,
    *,
    draft_transactions: list[dict],
):
    if not draft_transactions:
        return

    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into import_draft_transactions (
                import_job_id,
                transaction_fingerprint,
                datetime,
                merchant_original,
                merchant_normalized,
                amount,
                direction,
                transaction_type,
                review_group,
                raw_text,
                is_existing
            )
            values (
                %(import_job_id)s,
                %(transaction_fingerprint)s,
                %(datetime)s,
                %(merchant_original)s,
                %(merchant_normalized)s,
                %(amount)s,
                %(direction)s,
                %(transaction_type)s,
                %(review_group)s,
                %(raw_text)s,
                %(is_existing)s
            )
            """,
            draft_transactions,
        )
