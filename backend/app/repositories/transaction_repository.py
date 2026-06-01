from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def _chunk_rows(rows: list[dict], chunk_size: int):
    for index in range(0, len(rows), chunk_size):
        yield rows[index:index + chunk_size]


def _transaction_params(row: dict):
    payload = row["payload"]

    return (
        row["workspace_id"],
        row["sheet_source_id"],
        row["external_row_key"],
        row["row_number"],
        payload["transaction_date"],
        payload["transaction_time"],
        payload["title"],
        payload["raw_category"],
        payload["amount"],
        payload["source_fund"],
        payload["note"],
        payload["direction"],
        Jsonb(payload["raw_payload"]),
        payload["normalized_hash"],
    )


def get_transaction_by_external_row_key(
    connection,
    *,
    workspace_id: str,
    sheet_source_id: str,
    external_row_key: str,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                normalized_hash
            from transactions
            where workspace_id = %s
              and sheet_source_id = %s
              and external_row_key = %s
            """,
            (workspace_id, sheet_source_id, external_row_key),
        )

        return cursor.fetchone()


def get_existing_transaction_hashes(
    connection,
    *,
    workspace_id: str,
    sheet_source_id: str,
    external_row_keys: list[str],
) -> dict:
    if not external_row_keys:
        return {}

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                external_row_key,
                normalized_hash
            from transactions
            where workspace_id = %s
              and sheet_source_id = %s
              and external_row_key = any(%s)
            """,
            (workspace_id, sheet_source_id, external_row_keys),
        )

        return {
            row["external_row_key"]: row["normalized_hash"]
            for row in cursor.fetchall()
        }


def bulk_insert_transactions(
    connection,
    rows: list[dict],
    chunk_size: int = 200,
) -> int:
    inserted_count = 0

    if not rows:
        return inserted_count

    with connection.cursor() as cursor:
        for chunk in _chunk_rows(rows, chunk_size):
            cursor.executemany(
                """
                insert into transactions (
                    workspace_id,
                    sheet_source_id,
                    external_row_key,
                    row_number,
                    transaction_date,
                    transaction_time,
                    title,
                    raw_category,
                    amount,
                    source_fund,
                    note,
                    direction,
                    raw_payload,
                    normalized_hash
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (workspace_id, sheet_source_id, external_row_key)
                do nothing
                """,
                [_transaction_params(row) for row in chunk],
            )
            inserted_count += cursor.rowcount or 0

    return inserted_count


def bulk_update_transactions(
    connection,
    rows: list[dict],
    chunk_size: int = 200,
) -> int:
    updated_count = 0

    if not rows:
        return updated_count

    with connection.cursor() as cursor:
        for chunk in _chunk_rows(rows, chunk_size):
            cursor.executemany(
                """
                update transactions
                set
                    row_number = %s,
                    transaction_date = %s,
                    transaction_time = %s,
                    title = %s,
                    raw_category = %s,
                    amount = %s,
                    source_fund = %s,
                    note = %s,
                    direction = %s,
                    raw_payload = %s,
                    normalized_hash = %s,
                    updated_at = now()
                where workspace_id = %s
                  and sheet_source_id = %s
                  and external_row_key = %s
                  and normalized_hash is distinct from %s
                """,
                [
                    (
                        row["row_number"],
                        row["payload"]["transaction_date"],
                        row["payload"]["transaction_time"],
                        row["payload"]["title"],
                        row["payload"]["raw_category"],
                        row["payload"]["amount"],
                        row["payload"]["source_fund"],
                        row["payload"]["note"],
                        row["payload"]["direction"],
                        Jsonb(row["payload"]["raw_payload"]),
                        row["payload"]["normalized_hash"],
                        row["workspace_id"],
                        row["sheet_source_id"],
                        row["external_row_key"],
                        row["payload"]["normalized_hash"],
                    )
                    for row in chunk
                ],
            )
            updated_count += cursor.rowcount or 0

    return updated_count


def batch_upsert_transactions(
    connection,
    *,
    workspace_id: str,
    sheet_source_id: str,
    payloads: list[dict],
    chunk_size: int = 200,
) -> dict:
    if not payloads:
        return {
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
        }

    existing_hashes = get_existing_transaction_hashes(
        connection,
        workspace_id=workspace_id,
        sheet_source_id=sheet_source_id,
        external_row_keys=[
            row["external_row_key"]
            for row in payloads
        ],
    )
    rows_to_insert = []
    rows_to_update = []
    skipped_count = 0

    for row in payloads:
        existing_hash = existing_hashes.get(row["external_row_key"])

        if existing_hash is None:
            rows_to_insert.append(row)
        elif existing_hash == row["payload"]["normalized_hash"]:
            skipped_count += 1
        else:
            rows_to_update.append(row)

    inserted_count = bulk_insert_transactions(
        connection,
        rows_to_insert,
        chunk_size=chunk_size,
    )
    updated_count = bulk_update_transactions(
        connection,
        rows_to_update,
        chunk_size=chunk_size,
    )

    return {
        "inserted": inserted_count,
        "updated": updated_count,
        "skipped": skipped_count + (len(rows_to_insert) - inserted_count),
        "failed": 0,
    }


def upsert_transaction(
    connection,
    *,
    workspace_id: str,
    sheet_source_id: str,
    external_row_key: str,
    row_number: int,
    payload: dict,
) -> str:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            insert into transactions (
                workspace_id,
                sheet_source_id,
                external_row_key,
                row_number,
                transaction_date,
                transaction_time,
                title,
                raw_category,
                amount,
                source_fund,
                note,
                direction,
                raw_payload,
                normalized_hash
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (workspace_id, sheet_source_id, external_row_key)
            do update set
                row_number = excluded.row_number,
                transaction_date = excluded.transaction_date,
                transaction_time = excluded.transaction_time,
                title = excluded.title,
                raw_category = excluded.raw_category,
                amount = excluded.amount,
                source_fund = excluded.source_fund,
                note = excluded.note,
                direction = excluded.direction,
                raw_payload = excluded.raw_payload,
                normalized_hash = excluded.normalized_hash,
                updated_at = now()
            where transactions.normalized_hash is distinct from excluded.normalized_hash
            returning
                case
                    when xmax = '0'::xid then 'inserted'
                    else 'updated'
                end as action
            """,
            (
                workspace_id,
                sheet_source_id,
                external_row_key,
                row_number,
                payload["transaction_date"],
                payload["transaction_time"],
                payload["title"],
                payload["raw_category"],
                payload["amount"],
                payload["source_fund"],
                payload["note"],
                payload["direction"],
                Jsonb(payload["raw_payload"]),
                payload["normalized_hash"],
            ),
        )
        result = cursor.fetchone()

        return result["action"] if result else "skipped"
