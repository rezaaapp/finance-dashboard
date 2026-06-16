from datetime import datetime

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def create_import_transactions(
    connection,
    *,
    rows: list[dict],
):
    if not rows:
        return []

    with connection.cursor(row_factory=dict_row) as cursor:
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
                import_job_id,
                import_transaction_fingerprint,
                sync_status,
                sync_error_message
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
                %(sync_status)s,
                %(sync_error_message)s
            )
            returning id, import_transaction_fingerprint, sync_status
            """,
            [
                {
                    **row,
                    "raw_payload": Jsonb(row["raw_payload"]),
                }
                for row in rows
            ],
        )

        return cursor.fetchall()


def update_import_transaction_sync_status(
    connection,
    *,
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
            where import_transaction_fingerprint = any(%s)
            returning id, import_transaction_fingerprint, sync_status
            """,
            (
                sync_status,
                sync_error_message,
                transaction_fingerprints,
            ),
        )

        return cursor.fetchall()


def serialize_import_transaction_row(
    *,
    workspace_id: str,
    sheet_source_id: str,
    import_job_id: str,
    user_name: str,
    transaction: dict,
) -> dict:
    transaction_time = _parse_transaction_time(transaction.get("datetime", ""))

    return {
        "workspace_id": workspace_id,
        "sheet_source_id": sheet_source_id,
        "external_row_key": str(transaction.get("transaction_fingerprint", "")),
        "row_number": None,
        "transaction_date": transaction_time.date(),
        "transaction_time": transaction_time,
        "title": str(transaction.get("merchant_normalized", "")),
        "raw_category": str(transaction.get("category", "")) or None,
        "amount": transaction.get("amount", 0),
        "source_fund": "Blu",
        "note": str(transaction.get("notes", "")) or None,
        "direction": str(transaction.get("direction", "")) or "expense",
        "raw_payload": {
            "merchant_original": str(transaction.get("merchant_original", "")),
            "merchant_normalized": str(transaction.get("merchant_normalized", "")),
            "transaction_type": str(transaction.get("transaction_type", "")),
            "review_group": str(transaction.get("review_group", "")),
            "raw_text": str(transaction.get("raw_text", "")),
            "category": str(transaction.get("category", "")),
            "notes": str(transaction.get("notes", "")),
            "_import_provider": "blu",
            "_import_source": "smart_import",
        },
        "normalized_hash": str(transaction.get("transaction_fingerprint", "")),
        "user_name": user_name,
        "import_job_id": import_job_id,
        "import_transaction_fingerprint": str(transaction.get("transaction_fingerprint", "")),
        "sync_status": "pending",
        "sync_error_message": None,
    }


def _parse_transaction_time(raw_datetime: str) -> datetime:
    return datetime.strptime(str(raw_datetime or "").strip(), "%d/%m/%Y %H:%M")
