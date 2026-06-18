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
        payload.get("user_name"),
        payload.get("source_origin"),
        payload.get("source_reference"),
        payload.get("canonical_fingerprint"),
        payload.get("canonical_fingerprint_date"),
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


def get_transaction_ids_by_external_row_keys(
    connection,
    *,
    workspace_id: str,
    sheet_source_id: str,
    external_row_keys: list[str],
) -> list[str]:
    if not external_row_keys:
        return []

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select id
            from transactions
            where workspace_id = %s
              and sheet_source_id = %s
              and external_row_key = any(%s)
            """,
            (workspace_id, sheet_source_id, external_row_keys),
        )

        return [row["id"] for row in cursor.fetchall()]


def get_existing_transactions_by_canonical_fingerprint(
    connection,
    *,
    workspace_id: str,
    canonical_fingerprints: list[str],
    canonical_fingerprint_dates: list[str] | None = None,
) -> dict[str, dict]:
    if not hasattr(connection, "cursor"):
        return {}

    if not canonical_fingerprints and not canonical_fingerprint_dates:
        return {}

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                sheet_source_id,
                external_row_key,
                source_origin,
                canonical_fingerprint,
                canonical_fingerprint_date
            from transactions
            where workspace_id = %s
              and (
                canonical_fingerprint = any(%s)
                or canonical_fingerprint_date = any(%s)
              )
            order by created_at asc
            """,
            (
                workspace_id,
                canonical_fingerprints or [],
                canonical_fingerprint_dates or [],
            ),
        )

        matches = {}
        for row in cursor.fetchall():
            if row["canonical_fingerprint"]:
                matches.setdefault(row["canonical_fingerprint"], row)
            if row["canonical_fingerprint_date"]:
                matches.setdefault(row["canonical_fingerprint_date"], row)
        return matches


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
                    normalized_hash,
                    user_name,
                    source_origin,
                    source_reference,
                    canonical_fingerprint,
                    canonical_fingerprint_date
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    user_name = %s,
                    source_origin = %s,
                    source_reference = %s,
                    canonical_fingerprint = %s,
                    canonical_fingerprint_date = %s,
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
                        row["payload"].get("user_name"),
                        row["payload"].get("source_origin"),
                        row["payload"].get("source_reference"),
                        row["payload"].get("canonical_fingerprint"),
                        row["payload"].get("canonical_fingerprint_date"),
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
            "inserted_transaction_ids": [],
            "updated_transaction_ids": [],
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
    rows_to_rekey = []
    skipped_count = 0
    skipped_duplicate_count = 0
    existing_canonical_matches = get_existing_transactions_by_canonical_fingerprint(
        connection,
        workspace_id=workspace_id,
        canonical_fingerprints=[
            row["payload"].get("canonical_fingerprint")
            for row in payloads
            if row["payload"].get("canonical_fingerprint")
        ],
        canonical_fingerprint_dates=[
            row["payload"].get("canonical_fingerprint_date")
            for row in payloads
            if row["payload"].get("canonical_fingerprint_date")
        ],
    )

    for row in payloads:
        existing_hash = existing_hashes.get(row["external_row_key"])
        canonical_match = (
            existing_canonical_matches.get(row["payload"].get("canonical_fingerprint"))
            or existing_canonical_matches.get(row["payload"].get("canonical_fingerprint_date"))
        )

        if existing_hash is None:
            if canonical_match:
                same_source_sheet_match = (
                    canonical_match.get("source_origin") == "google_sheet"
                    and str(canonical_match.get("sheet_source_id") or "") == str(sheet_source_id)
                )
                if same_source_sheet_match:
                    rows_to_rekey.append({
                        **row,
                        "existing_transaction_id": canonical_match["id"],
                    })
                else:
                    skipped_duplicate_count += 1
            else:
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
    updated_count += bulk_update_transactions_by_id(
        connection,
        rows_to_rekey,
        chunk_size=chunk_size,
    )
    inserted_transaction_ids = get_transaction_ids_by_external_row_keys(
        connection,
        workspace_id=workspace_id,
        sheet_source_id=sheet_source_id,
        external_row_keys=[
            row["external_row_key"]
            for row in rows_to_insert
        ],
    )
    updated_transaction_ids = get_transaction_ids_by_external_row_keys(
        connection,
        workspace_id=workspace_id,
        sheet_source_id=sheet_source_id,
        external_row_keys=[
            row["external_row_key"]
            for row in rows_to_update
        ] + [
            row["external_row_key"]
            for row in rows_to_rekey
        ],
    )

    return {
        "inserted": inserted_count,
        "updated": updated_count,
        "skipped": skipped_count + skipped_duplicate_count + (len(rows_to_insert) - inserted_count),
        "skipped_duplicates": skipped_duplicate_count,
        "failed": 0,
        "inserted_transaction_ids": inserted_transaction_ids,
        "updated_transaction_ids": updated_transaction_ids,
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
                normalized_hash,
                user_name,
                source_origin,
                source_reference,
                canonical_fingerprint,
                canonical_fingerprint_date
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                user_name = excluded.user_name,
                source_origin = excluded.source_origin,
                source_reference = excluded.source_reference,
                canonical_fingerprint = excluded.canonical_fingerprint,
                canonical_fingerprint_date = excluded.canonical_fingerprint_date,
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
                payload.get("user_name"),
                payload.get("source_origin"),
                payload.get("source_reference"),
                payload.get("canonical_fingerprint"),
                payload.get("canonical_fingerprint_date"),
            ),
        )
        result = cursor.fetchone()

        return result["action"] if result else "skipped"


def bulk_update_transactions_by_id(
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
                    external_row_key = %s,
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
                    user_name = %s,
                    source_origin = %s,
                    source_reference = %s,
                    canonical_fingerprint = %s,
                    canonical_fingerprint_date = %s,
                    updated_at = now()
                where id = %s
                """,
                [
                    (
                        row["external_row_key"],
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
                        row["payload"].get("user_name"),
                        row["payload"].get("source_origin"),
                        row["payload"].get("source_reference"),
                        row["payload"].get("canonical_fingerprint"),
                        row["payload"].get("canonical_fingerprint_date"),
                        row["existing_transaction_id"],
                    )
                    for row in chunk
                ],
            )
            updated_count += cursor.rowcount or 0

    return updated_count
