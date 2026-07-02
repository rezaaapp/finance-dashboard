from enum import StrEnum


DETAIL_LIMIT_PER_STATUS = 500


class ImportReason(StrEnum):
    IMPORTED = "IMPORTED"
    UPDATED = "UPDATED"
    DUPLICATE_BATCH = "DUPLICATE_BATCH"
    ALREADY_IMPORTED = "ALREADY_IMPORTED"
    EXISTING_TRANSACTION = "EXISTING_TRANSACTION"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    DATABASE_WRITE_FAILED = "DATABASE_WRITE_FAILED"
    UNKNOWN = "UNKNOWN"


def transaction_detail(row: dict, *, status: str, reason: ImportReason) -> dict:
    payload = row.get("payload") or {}
    raw_payload = payload.get("raw_payload") or {}
    return {
        "sheet_name": raw_payload.get("_sheet_name"),
        "date": str(payload.get("transaction_date") or "") or None,
        "merchant": payload.get("title") or None,
        "amount": payload.get("amount"),
        "owner": payload.get("user_name") or None,
        "status": status,
        "reason": reason.value,
    }


def empty_import_details() -> dict[str, list]:
    return {"inserted": [], "updated": [], "skipped": [], "failed": []}


def limited_details(details: dict[str, list]) -> dict[str, list]:
    return {
        status: list(details.get(status) or [])[:DETAIL_LIMIT_PER_STATUS]
        for status in ("inserted", "updated", "skipped", "failed")
    }
