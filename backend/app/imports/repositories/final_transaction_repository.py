from datetime import datetime

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.imports.utils.fingerprint import normalize_owner_name
from app.services.transaction_normalizer import normalize_search_text


def create_import_transactions(
    connection,
    *,
    rows: list[dict],
):
    if not rows:
        return []

    with connection.cursor(row_factory=dict_row) as cursor:
        inserted_rows = []

        for row in rows:
            search_text_normalized = (
                str(row.get("search_text_normalized", "")).strip()
                or normalize_search_text(
                    row.get("title"),
                    row.get("raw_category"),
                    (row.get("raw_payload") or {}).get("_category_normalized"),
                    row.get("source_fund"),
                    row.get("note"),
                )
            )
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
                    import_job_id,
                    import_transaction_fingerprint,
                    source_origin,
                    source_reference,
                    canonical_fingerprint,
                    canonical_fingerprint_date,
                    sync_status,
                    sync_error_message,
                    search_text_normalized
                )
                values (
                    %(workspace_id)s,
                    %(sheet_source_id)s,
                    %(external_row_key)s,
                    %(row_number)s,
                    %(transaction_date)s,
                    %(transaction_time)s,
                    %(title)s,
                    %(raw_category)s,
                    %(amount)s,
                    %(source_fund)s,
                    %(note)s,
                    %(direction)s,
                    %(raw_payload)s,
                    %(normalized_hash)s,
                    %(user_name)s,
                    %(import_job_id)s,
                    %(import_transaction_fingerprint)s,
                    %(source_origin)s,
                    %(source_reference)s,
                    %(canonical_fingerprint)s,
                    %(canonical_fingerprint_date)s,
                    %(sync_status)s,
                    %(sync_error_message)s,
                    %(search_text_normalized)s
                )
                on conflict (workspace_id, import_transaction_fingerprint)
                where import_transaction_fingerprint is not null
                do nothing
                returning id, import_transaction_fingerprint, sync_status
                """,
                {
                    **row,
                    "raw_payload": Jsonb(row["raw_payload"]),
                    "search_text_normalized": search_text_normalized,
                },
            )
            inserted_row = cursor.fetchone()

            if inserted_row:
                inserted_rows.append(inserted_row)

        return inserted_rows


def update_import_transaction_sync_status(
    connection,
    *,
    workspace_id: str,
    transaction_fingerprints: list[str],
    sync_status: str,
    sync_error_message: str | None = None,
):
    if not transaction_fingerprints:
        return []

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update transactions
            set
                sync_status = %s,
                sync_error_message = %s,
                updated_at = now()
            where workspace_id = %s
              and import_transaction_fingerprint = any(%s)
            returning id, import_transaction_fingerprint, sync_status
            """,
            (
                sync_status,
                sync_error_message,
                workspace_id,
                transaction_fingerprints,
            ),
        )

        return cursor.fetchall()


def update_import_transaction_sync_status_by_ids(
    connection,
    *,
    transaction_ids: list[str],
    sync_status: str,
    sync_error_message: str | None = None,
):
    if not transaction_ids:
        return []

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            update transactions
            set
                sync_status = %s,
                sync_error_message = %s,
                updated_at = now()
            where id = any(%s)
            returning id, import_transaction_fingerprint, sync_status
            """,
            (
                sync_status,
                sync_error_message,
                transaction_ids,
            ),
        )

        return cursor.fetchall()


def list_retryable_import_transactions(
    connection,
    *,
    workspace_id: str,
    import_job_id: str,
):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                id,
                user_name,
                import_transaction_fingerprint as transaction_fingerprint,
                to_char(transaction_time, 'YYYY-MM-DD HH24:MI') as datetime,
                to_char(transaction_time, 'DD/MM/YYYY') as date,
                coalesce(raw_payload ->> 'merchant_original', title) as merchant_original,
                title as merchant_normalized,
                coalesce(raw_payload ->> 'merchant_display', title) as merchant_display,
                amount::float8 as amount,
                direction,
                coalesce(raw_payload ->> 'transaction_type', '') as transaction_type,
                coalesce(raw_payload ->> 'review_group', '') as review_group,
                coalesce(raw_payload ->> 'raw_text', '') as raw_text,
                coalesce(raw_category, '') as category,
                coalesce(note, '') as notes,
                source_fund as source_dana,
                coalesce(sync_status, 'pending') as sync_status,
                sync_error_message
            from transactions
            where workspace_id = %s
              and import_job_id = %s
              and (
                sync_status is null
                or sync_status in ('failed', 'needs_reconnect', 'pending')
              )
            order by transaction_time asc, created_at asc
            """,
            (workspace_id, import_job_id),
        )

        return cursor.fetchall()


def count_successful_import_transactions(
    connection,
    *,
    workspace_id: str,
    import_job_id: str,
) -> int:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select count(*)::int as total
            from transactions
            where workspace_id = %s
              and import_job_id = %s
              and sync_status = 'success'
            """,
            (workspace_id, import_job_id),
        )

        row = cursor.fetchone()
        return int(row["total"]) if row else 0


def list_workspace_transaction_user_names(connection, *, workspace_id: str) -> list[str]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select user_name
            from (
                select distinct btrim(user_name) as user_name
                from transactions
                where workspace_id = %s
                  and user_name is not null
                  and btrim(user_name) <> ''
            ) names
            order by user_name asc
            """,
            (workspace_id,),
        )

        normalized_names: list[str] = []
        seen_names: set[str] = set()

        for row in cursor.fetchall():
            normalized_name = normalize_owner_name(row["user_name"])
            if normalized_name and normalized_name not in seen_names:
                normalized_names.append(normalized_name)
                seen_names.add(normalized_name)

        return normalized_names


def list_workspace_transaction_source_funds(connection, *, workspace_id: str) -> list[str]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select source_fund
            from (
                select distinct btrim(source_fund) as source_fund
                from transactions
                where workspace_id = %s
                  and source_fund is not null
                  and btrim(source_fund) <> ''
            ) sources
            order by source_fund asc
            """,
            (workspace_id,),
        )

        return [row["source_fund"] for row in cursor.fetchall()]


def serialize_import_transaction_row(
    *,
    workspace_id: str,
    sheet_source_id: str | None,
    import_job_id: str,
    user_name: str,
    source_fund: str = "Blu",
    transaction: dict,
) -> dict:
    transaction_time = _parse_transaction_time(transaction.get("datetime", ""))
    title = str(
        transaction.get("merchant_display")
        or transaction.get("merchant_normalized", "")
    )
    raw_category = str(transaction.get("category", "")) or None
    note = str(transaction.get("notes", "")) or None

    return {
        "workspace_id": workspace_id,
        "sheet_source_id": sheet_source_id,
        "external_row_key": str(transaction.get("transaction_fingerprint", "")),
        "row_number": None,
        "transaction_date": transaction_time.date(),
        "transaction_time": transaction_time,
        "title": title,
        "raw_category": raw_category,
        "amount": transaction.get("amount", 0),
        "source_fund": source_fund,
        "note": note,
        "direction": str(transaction.get("direction", "")) or "expense",
        "raw_payload": {
            "Nama": user_name,
            "merchant_original": str(transaction.get("merchant_original", "")),
            "merchant_normalized": str(transaction.get("merchant_normalized", "")),
            "merchant_display": str(
                transaction.get("merchant_display")
                or transaction.get("merchant_normalized", "")
            ),
            "transaction_type": str(transaction.get("transaction_type", "")),
            "review_group": str(transaction.get("review_group", "")),
            "raw_text": str(transaction.get("raw_text", "")),
            "category": str(transaction.get("category", "")),
            "notes": str(transaction.get("notes", "")),
            "source_fund": source_fund,
            "_import_provider": "blu",
            "_import_source": "smart_import",
        },
        "normalized_hash": str(transaction.get("transaction_fingerprint", "")),
        "user_name": user_name,
        "import_job_id": import_job_id,
        "import_transaction_fingerprint": str(transaction.get("transaction_fingerprint", "")),
        "source_origin": "blu_pdf",
        "source_reference": f"import_job:{import_job_id}|fingerprint:{transaction.get('transaction_fingerprint', '')}",
        "canonical_fingerprint": str(transaction.get("canonical_fingerprint", "")) or None,
        "canonical_fingerprint_date": str(transaction.get("canonical_fingerprint_date", "")) or None,
        "sync_status": "pending",
        "sync_error_message": None,
        "search_text_normalized": normalize_search_text(
            title,
            raw_category,
            None,
            source_fund,
            note,
        ),
    }


def _parse_transaction_time(raw_datetime: str) -> datetime:
    return datetime.strptime(str(raw_datetime or "").strip(), "%d/%m/%Y %H:%M")
