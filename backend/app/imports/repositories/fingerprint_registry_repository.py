from psycopg.rows import dict_row


def get_registered_transaction_fingerprint_statuses(
    connection,
    *,
    transaction_fingerprints: list[str],
):
    if not transaction_fingerprints:
        return {}

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update import_transaction_registry
            set last_seen_at = now()
            where transaction_fingerprint = any(%s)
            returning transaction_fingerprint, status
            """,
            (transaction_fingerprints,),
        )

        return {
            row["transaction_fingerprint"]: row["status"]
            for row in cursor.fetchall()
        }


def get_registered_transaction_fingerprints(
    connection,
    *,
    transaction_fingerprints: list[str],
):
    return set(
        get_registered_transaction_fingerprint_statuses(
            connection,
            transaction_fingerprints=transaction_fingerprints,
        ).keys()
    )


def register_transaction_fingerprints(
    connection,
    *,
    rows: list[dict],
):
    if not rows:
        return []

    with connection.cursor(row_factory=dict_row) as cursor:
        registered_rows = []

        for row in rows:
            cursor.execute(
                """
                insert into import_transaction_registry (
                    transaction_fingerprint,
                    provider,
                    status,
                    approved_at,
                    rejected_at,
                    last_seen_at
                )
                values (
                    %(transaction_fingerprint)s,
                    %(provider)s,
                    'approved',
                    now(),
                    null,
                    now()
                )
                on conflict (transaction_fingerprint)
                do update set
                    provider = excluded.provider,
                    status = 'approved',
                    approved_at = excluded.approved_at,
                    rejected_at = null,
                    last_seen_at = excluded.last_seen_at
                returning transaction_fingerprint, provider, status, approved_at, rejected_at, last_seen_at, created_at
                """,
                row,
            )
            registered_row = cursor.fetchone()

            if registered_row:
                registered_rows.append(registered_row)

        return registered_rows


def register_rejected_transaction_fingerprints(
    connection,
    *,
    rows: list[dict],
):
    if not rows:
        return []

    with connection.cursor(row_factory=dict_row) as cursor:
        registered_rows = []

        for row in rows:
            cursor.execute(
                """
                insert into import_transaction_registry (
                    transaction_fingerprint,
                    provider,
                    status,
                    approved_at,
                    rejected_at,
                    last_seen_at
                )
                values (
                    %(transaction_fingerprint)s,
                    %(provider)s,
                    'rejected',
                    null,
                    now(),
                    now()
                )
                on conflict (transaction_fingerprint)
                do update set
                    provider = excluded.provider,
                    status = 'rejected',
                    approved_at = null,
                    rejected_at = excluded.rejected_at,
                    last_seen_at = excluded.last_seen_at
                returning transaction_fingerprint, provider, status, approved_at, rejected_at, last_seen_at, created_at
                """,
                row,
            )
            registered_row = cursor.fetchone()

            if registered_row:
                registered_rows.append(registered_row)

        return registered_rows
