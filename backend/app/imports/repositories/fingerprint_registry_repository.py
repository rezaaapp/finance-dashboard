from psycopg.rows import dict_row


def get_registered_transaction_fingerprints(
    connection,
    *,
    transaction_fingerprints: list[str],
):
    if not transaction_fingerprints:
        return set()

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select transaction_fingerprint
            from import_transaction_registry
            where transaction_fingerprint = any(%s)
            """,
            (transaction_fingerprints,),
        )

        return {
            row["transaction_fingerprint"]
            for row in cursor.fetchall()
        }


def register_transaction_fingerprints(
    connection,
    *,
    rows: list[dict],
):
    if not rows:
        return []

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.executemany(
            """
            insert into import_transaction_registry (
                transaction_fingerprint,
                provider,
                approved_at
            )
            values (
                %(transaction_fingerprint)s,
                %(provider)s,
                now()
            )
            on conflict (transaction_fingerprint)
            do update set
                approved_at = excluded.approved_at
            returning transaction_fingerprint, provider, approved_at
            """,
            rows,
        )

        return cursor.fetchall()
