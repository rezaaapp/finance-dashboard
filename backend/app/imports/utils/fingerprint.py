from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal, InvalidOperation


def _canonicalize_datetime(raw_datetime: str) -> str:
    normalized_datetime = str(raw_datetime or "").strip()

    if not normalized_datetime:
        return ""

    try:
        parsed_datetime = datetime.strptime(normalized_datetime, "%d/%m/%Y %H:%M")
        return parsed_datetime.strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        return normalized_datetime


def _canonicalize_amount(raw_amount) -> str:
    try:
        normalized_amount = Decimal(str(raw_amount))
    except InvalidOperation:
        return str(raw_amount or "").strip()

    if normalized_amount == normalized_amount.to_integral():
        return str(normalized_amount.quantize(Decimal("1")))

    return format(normalized_amount.normalize(), "f")


def build_transaction_fingerprint(
    *,
    source_dana: str,
    datetime_value: str,
    merchant_normalized: str,
    amount,
) -> str:
    fingerprint_payload = "|".join([
        str(source_dana or "").strip(),
        _canonicalize_datetime(datetime_value),
        str(merchant_normalized or "").strip(),
        _canonicalize_amount(amount),
    ])

    return hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()
