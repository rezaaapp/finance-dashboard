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


def update_import_job_summary(
    connection,
    *,
    job_id: str,
    transactions_found: int,
    new_transactions: int,
    existing_transactions: int,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update import_jobs
            set
                transactions_found = %s,
                new_transactions = %s,
                existing_transactions = %s
            where id = %s
            returning *
            """,
            (
                transactions_found,
                new_transactions,
                existing_transactions,
                job_id,
            ),
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
              and draft.status = 'approved'
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
                is_existing,
                status,
                category,
                notes
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
                %(is_existing)s,
                %(status)s,
                %(category)s,
                %(notes)s
            )
            """,
            draft_transactions,
        )


def get_import_review_summary(connection, *, workspace_id: str, job_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select id, provider, filename, status, transactions_found, new_transactions, existing_transactions, created_at
            from import_jobs
            where workspace_id = %s
              and id = %s
            """,
            (workspace_id, job_id),
        )

        return cursor.fetchone()


def list_import_draft_transactions(connection, *, import_job_id: str, status: str = "new"):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
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
                is_existing,
                status,
                category,
                notes,
                created_at
            from import_draft_transactions
            where import_job_id = %s
              and status = %s
            order by datetime asc, created_at asc
            """,
            (import_job_id, status),
        )

        return cursor.fetchall()


def approve_import_draft_transactions(
    connection,
    *,
    import_job_id: str,
    draft_ids: list[str],
    updates_by_id: dict[str, dict] | None = None,
):
    if not draft_ids:
        return []

    updates_by_id = updates_by_id or {}

    with connection.cursor(row_factory=dict_row) as cursor:
        updated_rows = []

        for draft_id in draft_ids:
            cursor.execute(
                """
                update import_draft_transactions
                set
                    status = 'approved',
                    category = %s,
                    notes = %s,
                    updated_at = now()
                where import_job_id = %s
                  and id = %s
                  and status = 'new'
                returning id
                """,
                (
                    str(updates_by_id.get(draft_id, {}).get("category", "")),
                    str(updates_by_id.get(draft_id, {}).get("notes", "")),
                    import_job_id,
                    draft_id,
                ),
            )
            row = cursor.fetchone()
            if row:
                updated_rows.append(row)

        return updated_rows


def reject_import_draft_transactions(
    connection,
    *,
    import_job_id: str,
    draft_ids: list[str],
):
    if not draft_ids:
        return []

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            delete from import_draft_transactions
            where import_job_id = %s
              and id = any(%s)
              and status = 'new'
            returning id
            """,
            (import_job_id, draft_ids),
        )

        return cursor.fetchall()
