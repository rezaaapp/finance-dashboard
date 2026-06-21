from psycopg.rows import dict_row

from app.imports.repositories.fingerprint_registry_repository import (
    get_registered_transaction_fingerprints,
)


def create_import_job(
    connection,
    *,
    workspace_id: str,
    provider: str,
    filename: str,
    statement_owner: str,
    status: str = "uploaded",
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into import_jobs (
                workspace_id,
                provider,
                filename,
                statement_owner,
                status
            )
            values (%s, %s, %s, %s, %s)
            returning *
            """,
            (workspace_id, provider, filename, statement_owner, status),
        )

        return cursor.fetchone()


def update_import_job_summary(
    connection,
    *,
    job_id: str,
    transactions_found: int,
    new_transactions: int,
    existing_transactions: int,
    status: str | None = None,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update import_jobs
            set
                transactions_found = %s,
                new_transactions = %s,
                existing_transactions = %s,
                status = coalesce(%s, status)
            where id = %s
            returning *
            """,
            (
                transactions_found,
                new_transactions,
                existing_transactions,
                status,
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


def set_import_job_temp_file(
    connection,
    *,
    job_id: str,
    temp_file_path: str,
    expires_at,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update import_jobs
            set
                temp_file_path = %s,
                expires_at = %s
            where id = %s
            returning *
            """,
            (temp_file_path, expires_at, job_id),
        )

        return cursor.fetchone()


def update_import_job_status(
    connection,
    *,
    job_id: str,
    status: str,
    completed_at=None,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update import_jobs
            set
                status = %s,
                completed_at = coalesce(%s, completed_at)
            where id = %s
            returning *
            """,
            (status, completed_at, job_id),
        )

        return cursor.fetchone()


def update_import_job_provider(
    connection,
    *,
    job_id: str,
    provider: str,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update import_jobs
            set provider = %s
            where id = %s
            returning *
            """,
            (provider, job_id),
        )

        return cursor.fetchone()


def increment_import_job_rejected_count(
    connection,
    *,
    job_id: str,
    rejected_count: int,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update import_jobs
            set rejected_transactions = rejected_transactions + %s
            where id = %s
            returning *
            """,
            (rejected_count, job_id),
        )

        return cursor.fetchone()


def list_workspace_transaction_categories(connection, *, workspace_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select category
            from (
                select distinct btrim(raw_category) as category
                from transactions
                where workspace_id = %s
                  and raw_category is not null
                  and btrim(raw_category) <> ''
            ) categories
            order by category asc
            """,
            (workspace_id,),
        )

        return [row["category"] for row in cursor.fetchall()]


def get_existing_transaction_fingerprints(
    connection,
    *,
    workspace_id: str,
    transaction_fingerprints: list[str],
):
    return get_registered_transaction_fingerprints(
        connection,
        workspace_id=workspace_id,
        transaction_fingerprints=transaction_fingerprints,
    )


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
                canonical_fingerprint,
                canonical_fingerprint_date,
                statement_owner,
                source_fund,
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
                %(canonical_fingerprint)s,
                %(canonical_fingerprint_date)s,
                %(statement_owner)s,
                %(source_fund)s,
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
            select
                id,
                provider,
                filename,
                coalesce(statement_owner, '') as statement_owner,
                status,
                transactions_found,
                new_transactions,
                existing_transactions,
                rejected_transactions,
                temp_file_deleted_at,
                created_at
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
                canonical_fingerprint,
                canonical_fingerprint_date,
                statement_owner,
                source_fund,
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


def list_import_draft_transactions_paginated(
    connection,
    *,
    import_job_id: str,
    status: str = "new",
    limit: int,
    offset: int,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                import_job_id,
                transaction_fingerprint,
                canonical_fingerprint,
                canonical_fingerprint_date,
                statement_owner,
                source_fund,
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
            limit %s
            offset %s
            """,
            (import_job_id, status, limit, offset),
        )

        return cursor.fetchall()


def list_import_draft_transactions_by_ids(
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
            select
                id,
                import_job_id,
                transaction_fingerprint,
                canonical_fingerprint,
                canonical_fingerprint_date,
                statement_owner,
                source_fund,
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
              and id = any(%s)
              and status = 'new'
            order by created_at asc
            """,
            (import_job_id, draft_ids),
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


def delete_import_draft_transactions(
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
            returning id
            """,
            (import_job_id, draft_ids),
        )

        return cursor.fetchall()


def delete_import_draft_transactions_for_job(
    connection,
    *,
    import_job_id: str,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            delete from import_draft_transactions
            where import_job_id = %s
            returning id
            """,
            (import_job_id,),
        )

        return cursor.fetchall()


def count_new_import_draft_transactions(connection, *, import_job_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select count(*)::int as total
            from import_draft_transactions
            where import_job_id = %s
              and status = 'new'
            """,
            (import_job_id,),
        )

        row = cursor.fetchone()
        return row["total"] if row else 0


def get_import_review_filter_counts(connection, *, import_job_id: str, status: str = "new"):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            with review_stats as (
                select
                    review_group,
                    count(*)::int as review_count,
                    count(*) filter (
                        where category is null
                           or btrim(category) = ''
                    )::int as needs_review_count
                from import_draft_transactions
                where import_job_id = %s
                  and status = %s
                group by review_group
            )
            select
                coalesce(sum(review_count), 0)::int as total_count,
                coalesce(sum(needs_review_count), 0)::int as needs_review_count,
                coalesce(
                    json_agg(
                        json_build_object(
                            'review_group', review_group,
                            'count', review_count
                        )
                        order by review_group asc
                    ) filter (where review_group is not null and btrim(review_group) <> ''),
                    '[]'::json
                ) as review_groups
            from review_stats
            """,
            (import_job_id, status),
        )

        return cursor.fetchone()


def refresh_import_job_aggregates(connection, *, workspace_id: str, job_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            with transaction_stats as (
                select
                    count(*)::int as approved_transactions,
                    count(*) filter (where sync_status = 'success')::int as sync_success,
                    count(*) filter (
                        where sync_status is null
                           or sync_status in ('failed', 'needs_reconnect', 'pending')
                    )::int as sync_failed
                from transactions
                where workspace_id = %s
                  and import_job_id = %s
            )
            select
                j.id,
                j.workspace_id,
                j.provider,
                j.filename,
                j.status,
                j.created_at,
                j.completed_at,
                j.transactions_found,
                j.new_transactions,
                j.existing_transactions,
                j.rejected_transactions,
                j.temp_file_path,
                j.temp_file_deleted_at,
                j.expires_at,
                j.cleanup_completed_at,
                coalesce(ts.approved_transactions, 0) as approved_transactions,
                coalesce(ts.sync_success, 0) as sync_success,
                coalesce(ts.sync_failed, 0) as sync_failed
            from import_jobs j
            left join transaction_stats ts on true
            where j.workspace_id = %s
              and j.id = %s
            """,
            (workspace_id, job_id, workspace_id, job_id),
        )

        return cursor.fetchone()


def list_import_history(connection, *, workspace_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            with transaction_stats as (
                select
                    import_job_id,
                    count(*)::int as approved_transactions,
                    count(*) filter (where sync_status = 'success')::int as sync_success,
                    count(*) filter (
                        where sync_status is null
                           or sync_status in ('failed', 'needs_reconnect', 'pending')
                    )::int as sync_failed,
                    count(*) filter (where sync_status = 'needs_reconnect')::int as needs_reconnect_count,
                    count(*) filter (
                        where sync_status = 'pending'
                          and sync_error_message ilike 'Target Spreadsheet belum dikonfigurasi%%'
                    )::int as unconfigured_spreadsheet_count
                from transactions
                where workspace_id = %s
                  and import_job_id is not null
                group by import_job_id
            ),
            retry_stats as (
                select
                    import_job_id,
                    count(*)::int as retryable_sync_count
                from transactions
                where workspace_id = %s
                  and import_job_id is not null
                  and (
                    sync_status is null
                    or sync_status in ('failed', 'needs_reconnect', 'pending')
                  )
                group by import_job_id
            )
            select
                j.id,
                j.filename,
                j.provider,
                j.statement_owner,
                j.status,
                j.created_at,
                j.completed_at,
                j.transactions_found,
                j.new_transactions,
                j.existing_transactions,
                j.rejected_transactions,
                j.temp_file_deleted_at,
                coalesce(ts.approved_transactions, 0) as approved_transactions,
                coalesce(ts.sync_success, 0) as sync_success,
                coalesce(ts.sync_failed, 0) as sync_failed,
                coalesce(ts.needs_reconnect_count, 0) > 0 as needs_reconnect,
                coalesce(ts.unconfigured_spreadsheet_count, 0) > 0 as spreadsheet_unconfigured,
                coalesce(rs.retryable_sync_count, 0) as retryable_sync_count
            from import_jobs j
            left join transaction_stats ts
              on ts.import_job_id = j.id
            left join retry_stats rs
              on rs.import_job_id = j.id
            where j.workspace_id = %s
            order by j.created_at desc
            """,
            (workspace_id, workspace_id, workspace_id),
        )

        return cursor.fetchall()


def count_import_history(connection, *, workspace_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select count(*)::int as total
            from import_jobs
            where workspace_id = %s
            """,
            (workspace_id,),
        )

        row = cursor.fetchone()
        return row["total"] if row else 0


def list_import_history_paginated(
    connection,
    *,
    workspace_id: str,
    limit: int,
    offset: int,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            with transaction_stats as (
                select
                    import_job_id,
                    count(*)::int as approved_transactions,
                    count(*) filter (where sync_status = 'success')::int as sync_success,
                    count(*) filter (
                        where sync_status is null
                           or sync_status in ('failed', 'needs_reconnect', 'pending')
                    )::int as sync_failed,
                    count(*) filter (where sync_status = 'needs_reconnect')::int as needs_reconnect_count,
                    count(*) filter (
                        where sync_status = 'pending'
                          and sync_error_message ilike 'Target Spreadsheet belum dikonfigurasi%%'
                    )::int as unconfigured_spreadsheet_count
                from transactions
                where workspace_id = %s
                  and import_job_id is not null
                group by import_job_id
            ),
            retry_stats as (
                select
                    import_job_id,
                    count(*)::int as retryable_sync_count
                from transactions
                where workspace_id = %s
                  and import_job_id is not null
                  and (
                    sync_status is null
                    or sync_status in ('failed', 'needs_reconnect', 'pending')
                  )
                group by import_job_id
            )
            select
                j.id,
                j.filename,
                j.provider,
                j.statement_owner,
                j.status,
                j.created_at,
                j.completed_at,
                j.transactions_found,
                j.new_transactions,
                j.existing_transactions,
                j.rejected_transactions,
                j.temp_file_deleted_at,
                coalesce(ts.approved_transactions, 0) as approved_transactions,
                coalesce(ts.sync_success, 0) as sync_success,
                coalesce(ts.sync_failed, 0) as sync_failed,
                coalesce(ts.needs_reconnect_count, 0) > 0 as needs_reconnect,
                coalesce(ts.unconfigured_spreadsheet_count, 0) > 0 as spreadsheet_unconfigured,
                coalesce(rs.retryable_sync_count, 0) as retryable_sync_count
            from import_jobs j
            left join transaction_stats ts
              on ts.import_job_id = j.id
            left join retry_stats rs
              on rs.import_job_id = j.id
            where j.workspace_id = %s
            order by j.created_at desc
            limit %s
            offset %s
            """,
            (workspace_id, workspace_id, workspace_id, limit, offset),
        )

        return cursor.fetchall()


def get_import_history_detail(connection, *, workspace_id: str, job_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            with transaction_stats as (
                select
                    import_job_id,
                    count(*)::int as approved_transactions,
                    count(*) filter (where sync_status = 'success')::int as sync_success,
                    count(*) filter (
                        where sync_status is null
                           or sync_status in ('failed', 'needs_reconnect', 'pending')
                    )::int as sync_failed,
                    count(*) filter (where sync_status = 'needs_reconnect')::int as needs_reconnect_count,
                    count(*) filter (
                        where sync_status = 'pending'
                          and sync_error_message ilike 'Target Spreadsheet belum dikonfigurasi%%'
                    )::int as unconfigured_spreadsheet_count
                from transactions
                where workspace_id = %s
                  and import_job_id = %s
                group by import_job_id
            ),
            retry_stats as (
                select
                    import_job_id,
                    count(*)::int as retryable_sync_count
                from transactions
                where workspace_id = %s
                  and import_job_id = %s
                  and (
                    sync_status is null
                    or sync_status in ('failed', 'needs_reconnect', 'pending')
                  )
                group by import_job_id
            )
            select
                j.id,
                j.filename,
                j.provider,
                j.statement_owner,
                j.status,
                j.created_at,
                j.completed_at,
                j.transactions_found,
                j.new_transactions,
                j.existing_transactions,
                j.rejected_transactions,
                j.temp_file_deleted_at,
                j.expires_at,
                coalesce(ts.approved_transactions, 0) as approved_transactions,
                coalesce(ts.sync_success, 0) as sync_success,
                coalesce(ts.sync_failed, 0) as sync_failed,
                coalesce(ts.needs_reconnect_count, 0) > 0 as needs_reconnect,
                coalesce(ts.unconfigured_spreadsheet_count, 0) > 0 as spreadsheet_unconfigured,
                coalesce(rs.retryable_sync_count, 0) as retryable_sync_count
            from import_jobs j
            left join transaction_stats ts
              on ts.import_job_id = j.id
            left join retry_stats rs
              on rs.import_job_id = j.id
            where j.workspace_id = %s
              and j.id = %s
            """,
            (workspace_id, job_id, workspace_id, job_id, workspace_id, job_id),
        )

        return cursor.fetchone()


def list_expired_import_jobs(connection, *, expires_before):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                workspace_id,
                status,
                temp_file_path,
                temp_file_deleted_at,
                expires_at
            from import_jobs
            where expires_at is not null
              and expires_at <= %s
              and status in ('uploaded', 'review', 'expired')
            order by expires_at asc
            """,
            (expires_before,),
        )

        return cursor.fetchall()


def mark_import_job_temp_file_deleted(connection, *, job_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update import_jobs
            set temp_file_deleted_at = coalesce(temp_file_deleted_at, now())
            where id = %s
            returning *
            """,
            (job_id,),
        )

        return cursor.fetchone()


def mark_import_job_expired(connection, *, job_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update import_jobs
            set status = 'expired'
            where id = %s
            returning *
            """,
            (job_id,),
        )

        return cursor.fetchone()


def mark_import_job_cleanup_completed(connection, *, job_id: str):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update import_jobs
            set
                status = 'cleanup_completed',
                cleanup_completed_at = now(),
                completed_at = coalesce(completed_at, now())
            where id = %s
            returning *
            """,
            (job_id,),
        )

        return cursor.fetchone()
