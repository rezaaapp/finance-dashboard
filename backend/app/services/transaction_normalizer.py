from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re

from app.services.transaction_classifier import (
    classify_direction,
    normalize_category,
)
from app.services.sheet_header_validator import canonicalize_header
from app.imports.utils.fingerprint import (
    build_canonical_fingerprint,
    build_canonical_fingerprint_date,
    normalize_owner_name,
)


REQUIRED_ROW_FIELDS = [
    "Waktu Transaksi",
    "Nama Transaksi",
    "Harga",
]

NON_TRANSACTION_KEYWORDS = (
    "total",
    "subtotal",
    "grand total",
    "saldo",
    "balance",
    "summary",
)

SKIPPED_REASONS = {
    "empty_row",
    "repeated_header",
    "summary_row",
    "future_transaction_date",
}


class RowNormalizationError(ValueError):
    def __init__(self, reason: str, *, skipped: bool = False, category: str | None = None):
        super().__init__(reason)
        self.reason = reason
        self.skipped = skipped
        self.category = category

INDONESIAN_MONTHS = {
    "januari": "January",
    "jan": "Jan",
    "februari": "February",
    "feb": "Feb",
    "maret": "March",
    "mar": "Mar",
    "april": "April",
    "apr": "Apr",
    "mei": "May",
    "juni": "June",
    "jun": "Jun",
    "juli": "July",
    "jul": "Jul",
    "agustus": "August",
    "agu": "Aug",
    "aug": "Aug",
    "september": "September",
    "sep": "Sep",
    "oktober": "October",
    "okt": "Oct",
    "oct": "Oct",
    "november": "November",
    "nov": "Nov",
    "desember": "December",
    "des": "Dec",
    "dec": "Dec",
}


def _normalize_key(value: str) -> str:
    return str(value or "").strip().casefold()


def map_sheet_rows(header: list[str], rows: list[list]) -> list[tuple[int, dict]]:
    normalized_header = [
        canonicalize_header(str(column or "").strip())
        for column in header
    ]
    mapped_rows = []

    for index, row in enumerate(rows, start=2):
        normalized_values = [
            str(value or "").strip()
            for value in row
        ]

        row_dict = {
            "_empty_row": not any(normalized_values),
        }

        for column_index, column_name in enumerate(normalized_header):
            if not column_name:
                continue

            row_dict[column_name] = (
                normalized_values[column_index]
                if column_index < len(normalized_values)
                else ""
            )

        mapped_rows.append((index, row_dict))

    return mapped_rows


def _get_value(row: dict, column_name: str) -> str:
    normalized_column = _normalize_key(column_name)

    for key, value in row.items():
        if _normalize_key(key) == normalized_column:
            return str(value or "").strip()

    return ""


def parse_amount(value: str) -> Decimal:
    raw_value = str(value or "").strip()

    if not raw_value:
        raise ValueError("Transaction amount is required")

    is_negative = raw_value.startswith("-") or raw_value.startswith("(")
    cleaned_value = re.sub(r"[^0-9,.-]", "", raw_value)
    cleaned_value = cleaned_value.replace("-", "")

    if not cleaned_value:
        raise ValueError("Transaction amount is invalid")

    if "," in cleaned_value and "." in cleaned_value:
        if cleaned_value.rfind(",") > cleaned_value.rfind("."):
            cleaned_value = cleaned_value.replace(".", "").replace(",", ".")
        else:
            cleaned_value = cleaned_value.replace(",", "")
    elif "," in cleaned_value:
        comma_parts = cleaned_value.split(",")

        if len(comma_parts[-1]) == 3:
            cleaned_value = cleaned_value.replace(",", "")
        else:
            cleaned_value = cleaned_value.replace(",", ".")
    elif "." in cleaned_value:
        dot_parts = cleaned_value.split(".")

        if len(dot_parts[-1]) == 3:
            cleaned_value = cleaned_value.replace(".", "")

    try:
        amount = Decimal(cleaned_value)
    except InvalidOperation as exc:
        raise ValueError("Transaction amount is invalid") from exc

    normalized_amount = -amount if is_negative else amount
    normalized_amount = abs(normalized_amount)

    if normalized_amount == 0:
        raise ValueError("Transaction amount must be greater than zero")

    return normalized_amount


def _normalize_month_names(value: str) -> str:
    normalized_value = value

    for source, target in INDONESIAN_MONTHS.items():
        normalized_value = re.sub(
            rf"\b{re.escape(source)}\b",
            target,
            normalized_value,
            flags=re.IGNORECASE,
        )

    return normalized_value


def _parse_slash_date(value: str) -> datetime | None:
    match = re.fullmatch(
        r"(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(.+))?",
        value,
    )

    if not match:
        return None

    first_part = int(match.group(1))
    second_part = int(match.group(2))
    year = int(match.group(3))
    time_part = (match.group(4) or "").strip()

    if first_part > 12 and second_part > 12:
        raise RowNormalizationError("invalid_date")

    if first_part > 12:
        day = first_part
        month = second_part
    else:
        month = first_part
        day = second_part

    if not time_part:
        try:
            return datetime(year, month, day)
        except ValueError as exc:
            raise RowNormalizationError("invalid_date") from exc

    for time_format in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p"):
        try:
            parsed_time = datetime.strptime(time_part.upper(), time_format).time()
            return datetime.combine(datetime(year, month, day), parsed_time)
        except ValueError:
            continue

    raise RowNormalizationError("invalid_date")


def parse_transaction_time(value: str) -> datetime:
    raw_value = str(value or "").strip()

    if not raw_value:
        raise RowNormalizationError("invalid_date")

    if re.fullmatch(r"\d+(\.\d+)?", raw_value):
        serial_value = float(raw_value)

        if serial_value > 59:
            return datetime(1899, 12, 30) + timedelta(days=serial_value)

    slash_date = _parse_slash_date(raw_value)

    if slash_date:
        return slash_date

    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y",
        "%d %b %Y %H:%M",
        "%d %b %Y %H:%M:%S",
        "%d %b %Y",
        "%d %B %Y %H:%M",
        "%d %B %Y %H:%M:%S",
        "%d %B %Y",
    ]
    normalized_value = _normalize_month_names(raw_value)

    for date_format in formats:
        try:
            return datetime.strptime(normalized_value, date_format)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(normalized_value)
    except ValueError as exc:
        raise RowNormalizationError("invalid_date") from exc


def _build_normalized_hash(payload: dict) -> str:
    stable_payload = {
        key: str(value) if isinstance(value, Decimal) else value
        for key, value in payload.items()
        if key != "raw_payload"
    }
    raw_payload = payload.get("raw_payload") or {}
    stable_payload["category_normalized"] = raw_payload.get("_category_normalized")
    stable_payload["direction_rule"] = raw_payload.get("_direction_rule")
    serialized_payload = json.dumps(
        stable_payload,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )

    return hashlib.sha256(serialized_payload.encode("utf-8")).hexdigest()


def _is_repeated_header(title: str, raw_category: str, raw_amount: str) -> bool:
    return (
        _normalize_key(title) == _normalize_key("Nama Transaksi")
        or _normalize_key(raw_category) == _normalize_key("Kategori")
        or _normalize_key(raw_amount) == _normalize_key("Harga")
    )


def _contains_non_transaction_keyword(*values: str) -> bool:
    normalized_values = {_normalize_key(value) for value in values if _normalize_key(value)}
    return any(keyword in normalized_values for keyword in NON_TRANSACTION_KEYWORDS)


def _looks_like_template(title: str, raw_category: str, raw_amount: str) -> bool:
    normalized_values = [
        _normalize_key(title),
        _normalize_key(raw_category),
        _normalize_key(raw_amount),
    ]
    return any(value in {"-", "template", "sample", "contoh"} for value in normalized_values)


def normalize_transaction_row(row: dict, *, raw_metadata: dict | None = None) -> dict:
    if row.get("_empty_row"):
        raise RowNormalizationError("empty_row", skipped=True)

    raw_transaction_time = _get_value(row, "Waktu Transaksi")
    title = _get_value(row, "Nama Transaksi")
    raw_category = _get_value(row, "Kategori")
    raw_amount = _get_value(row, "Harga")
    source_fund = _get_value(row, "Source Dana")
    note = _get_value(row, "Keterangan")
    user_name = _get_value(row, "Nama")
    sheet_name = str((raw_metadata or {}).get("_sheet_name") or "").strip()
    row_number = (raw_metadata or {}).get("_row_number")

    if _is_repeated_header(title, raw_category, raw_amount):
        raise RowNormalizationError("repeated_header", skipped=True, category=raw_category)

    if _contains_non_transaction_keyword(title, raw_category):
        raise RowNormalizationError("summary_row", skipped=True, category=raw_category)

    if _looks_like_template(title, raw_category, raw_amount):
        raise RowNormalizationError("non_transaction_row", skipped=True, category=raw_category)

    if not title and not raw_transaction_time and not raw_amount:
        raise RowNormalizationError("empty_row", skipped=True, category=raw_category)

    if not title:
        raise RowNormalizationError("empty_title", category=raw_category)

    transaction_time = parse_transaction_time(raw_transaction_time)

    if transaction_time.date() > date.today():
        raise RowNormalizationError(
            "future_transaction_date",
            skipped=True,
            category=raw_category,
        )

    try:
        amount = parse_amount(raw_amount)
    except ValueError as exc:
        raise RowNormalizationError("invalid_amount", category=raw_category) from exc

    raw_payload = {
        key: str(value or "").strip()
        for key, value in row.items()
    }

    if raw_metadata:
        raw_payload.update(raw_metadata)

    category_normalized = normalize_category(raw_category)
    direction = classify_direction(
        raw_category=raw_category,
        title=title,
        source_fund=source_fund,
        note=note,
        sheet_name=sheet_name,
    )
    raw_payload.update({
        "_category_normalized": category_normalized,
        "_direction_rule": "rule_based_v1",
        "_currency": "IDR",
    })

    payload = {
        "transaction_date": transaction_time.date(),
        "transaction_time": transaction_time,
        "title": title,
        "raw_category": raw_category or None,
        "amount": amount,
        "source_fund": source_fund or None,
        "note": note or None,
        "direction": direction,
        "raw_payload": raw_payload,
        "currency": "IDR",
        "user_name": normalize_owner_name(user_name) or None,
        "source_origin": "google_sheet",
        "source_reference": (
            f"sheet:{sheet_name}|row:{row_number}"
            if sheet_name and row_number
            else (f"sheet:{sheet_name}" if sheet_name else None)
        ),
    }
    payload["canonical_fingerprint"] = build_canonical_fingerprint(
        owner_name=payload["user_name"] or "",
        datetime_value=transaction_time,
        merchant_name=title,
        amount=amount,
        direction=direction,
        source_fund=source_fund or "",
    )
    payload["canonical_fingerprint_date"] = build_canonical_fingerprint_date(
        owner_name=payload["user_name"] or "",
        datetime_value=transaction_time,
        merchant_name=title,
        amount=amount,
        direction=direction,
        source_fund=source_fund or "",
    )
    payload["normalized_hash"] = _build_normalized_hash(payload)

    return payload
