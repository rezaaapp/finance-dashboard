from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re

from app.imports.utils.merchant_normalizer import MerchantNormalizer


_merchant_normalizer = MerchantNormalizer()


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


def _normalize_spaces(value: str) -> str:
    return " ".join(str(value or "").strip().split())


OWNER_NAME_ALIASES = {
    "reza putra pratama": "Reza",
    "reza": "Reza",
}


def normalize_owner_name(owner_name: str) -> str:
    normalized_owner = _normalize_spaces(owner_name)

    if not normalized_owner:
        return ""

    return OWNER_NAME_ALIASES.get(normalized_owner.casefold(), normalized_owner)


def normalize_source_fund_name(source_fund: str) -> str:
    return _normalize_spaces(source_fund).lower()


def normalize_description_for_fingerprint(description: str) -> str:
    normalized_fields = _merchant_normalizer.normalize(description)
    display_name = normalized_fields["merchant_display"] or normalized_fields["merchant_normalized"]
    normalized_display = _normalize_spaces(display_name).lower()
    return re.sub(r"\s+", " ", normalized_display).strip()


def _canonicalize_direction(direction: str) -> str:
    return _normalize_spaces(direction).lower()


def _parse_supported_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        return value

    normalized_value = str(value or "").strip()

    if not normalized_value:
        return None

    for date_format in (
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(normalized_value, date_format)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(normalized_value)
    except ValueError:
        return None


def _canonicalize_date(raw_datetime) -> str:
    parsed_datetime = _parse_supported_datetime(raw_datetime)

    if parsed_datetime is not None:
        return parsed_datetime.strftime("%Y-%m-%d")

    normalized_datetime = str(raw_datetime or "").strip()
    return normalized_datetime.split(" ", 1)[0]


def _has_explicit_time(raw_datetime) -> bool:
    parsed_datetime = _parse_supported_datetime(raw_datetime)

    if parsed_datetime is not None:
        raw_value = str(raw_datetime or "").strip()
        return ":" in raw_value

    return ":" in str(raw_datetime or "").strip()


def _hash_payload(parts: list[str]) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def build_canonical_fingerprint(
    *,
    owner_name: str,
    datetime_value,
    merchant_name: str,
    amount,
    direction: str,
    source_fund: str,
) -> str:
    parsed_datetime = _parse_supported_datetime(datetime_value)
    datetime_component = (
        parsed_datetime.strftime("%Y-%m-%dT%H:%M")
        if parsed_datetime is not None and _has_explicit_time(datetime_value)
        else _canonicalize_date(datetime_value)
    )
    return _hash_payload([
        normalize_owner_name(owner_name).lower(),
        datetime_component,
        normalize_description_for_fingerprint(merchant_name),
        _canonicalize_amount(amount),
        _canonicalize_direction(direction),
        normalize_source_fund_name(source_fund),
    ])


def build_canonical_fingerprint_date(
    *,
    owner_name: str,
    datetime_value,
    merchant_name: str,
    amount,
    direction: str,
    source_fund: str,
) -> str:
    return _hash_payload([
        normalize_owner_name(owner_name).lower(),
        _canonicalize_date(datetime_value),
        normalize_description_for_fingerprint(merchant_name),
        _canonicalize_amount(amount),
        _canonicalize_direction(direction),
        normalize_source_fund_name(source_fund),
    ])


def build_transaction_fingerprint(
    *,
    owner_name: str = "",
    source_dana: str,
    datetime_value: str,
    merchant_normalized: str,
    amount,
    direction: str = "",
) -> str:
    fingerprint_payload = "|".join([
        normalize_owner_name(owner_name).lower(),
        str(source_dana or "").strip(),
        _canonicalize_datetime(datetime_value),
        normalize_description_for_fingerprint(merchant_normalized),
        _canonicalize_amount(amount),
        _canonicalize_direction(direction),
    ])

    return hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()
