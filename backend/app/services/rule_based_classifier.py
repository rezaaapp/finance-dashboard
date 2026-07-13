import re
from collections.abc import Mapping

from app.services.category_normalization import canonicalize_category


VALID_DIRECTIONS = {"income", "expense", "saving_transfer"}
VALID_FINANCIAL_TYPES = {"income", "need", "want", "saving", "uncategorized"}

FIELD_PRIORITY = (
    ("raw_category", "category", 0.95),
    ("title", "title", 0.80),
    ("source_fund", "source fund", 0.80),
    ("note", "note", 0.80),
    ("_sheet_name", "sheet name", 0.80),
)

EXPLICIT_EXPENSE_RULES = (
    ("tagihan non rutin", "need"),
    ("tagihan tahunan", "need"),
    ("gift", "want"),
    ("transportasi non rutin", "want"),
)

INCOME_KEYWORDS = (
    "income",
    "gaji",
    "salary",
    "bonus",
    "pendapatan",
    "pemasukan",
)

SAVING_KEYWORDS = (
    "saving",
    "tabungan",
    "investasi",
    "reksadana",
    "saham",
    "emas",
    "deposito",
    "dana darurat",
    "rumah",
    "pendidikan",
    "mobil",
    "umroh",
)

NEED_KEYWORDS = (
    "groceries",
    "grocery",
    "belanja bulanan",
    "makanan pokok",
    "transportasi",
    "bensin",
    "parkir",
    "tagihan",
    "bills",
    "tagihan non rutin",
    "tagihan tahunan",
    "listrik",
    "internet",
    "sewa",
    "apartemen",
    "kesehatan",
    "obat",
    "dokter",
    "asuransi",
)

WANT_KEYWORDS = (
    "jajan",
    "resto",
    "restaurant",
    "cafe",
    "hiburan",
    "entertainment",
    "gift",
    "shopping",
    "subscription",
    "transportasi non rutin",
    "travel",
    "liburan",
    "pacaran",
)

CATEGORY_RULES = (
    ("Grocery", ("groceries", "grocery", "belanja bulanan")),
    ("Food", ("food", "makanan", "jajan", "resto", "restaurant")),
    ("Transportasi Rutin", ("transport", "transportasi", "bensin", "parkir")),
    ("Tagihan Bulanan", ("tagihan", "listrik", "internet", "bills")),
    ("Housing", ("sewa", "apartemen")),
    ("Health", ("kesehatan", "obat", "dokter")),
    ("Entertainment", ("entertainment", "hiburan")),
    ("Gift", ("gift",)),
    ("Income", ("income", "gaji", "salary", "bonus")),
    ("Saving", ("saving", "tabungan", "investasi")),
)


def _normalize_method(value) -> str:
    normalized = _normalize_text(value)
    return normalized if normalized in {"exact", "contains", "regex"} else "contains"


def _normalize_text(value) -> str:
    normalized = str(value or "").strip().casefold()
    return re.sub(r"\s+", " ", normalized)


def _clean_label(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _get_raw_payload(transaction: dict) -> Mapping:
    raw_payload = transaction.get("raw_payload")
    return raw_payload if isinstance(raw_payload, Mapping) else {}


def _get_field_value(transaction: dict, field_name: str) -> str:
    if field_name == "_sheet_name":
        return _clean_label(_get_raw_payload(transaction).get("_sheet_name"))

    return _clean_label(transaction.get(field_name))


def _candidate_fields(transaction: dict):
    for field_name, label, confidence in FIELD_PRIORITY:
        value = _get_field_value(transaction, field_name)
        yield {
            "field": field_name,
            "label": label,
            "value": value,
            "normalized": _normalize_text(value),
            "confidence": confidence,
        }


def _keyword_match(normalized_value: str, keywords: tuple[str, ...]):
    for keyword in keywords:
        if keyword in normalized_value:
            return keyword

    return None


def _normalize_category(value: str) -> str:
    normalized_value = _normalize_text(value)

    for category, keywords in CATEGORY_RULES:
        if _keyword_match(normalized_value, keywords):
            return category

    cleaned = _clean_label(value)
    return canonicalize_category(cleaned)


def _matches_user_rule(field_value: str, *, pattern: str, match_type: str) -> bool:
    normalized_pattern = _normalize_text(pattern)

    if not field_value or not normalized_pattern:
        return False

    if match_type == "exact":
        return field_value == normalized_pattern

    if match_type == "regex":
        try:
            return re.search(pattern, field_value, flags=re.IGNORECASE) is not None
        except re.error:
            return False

    return normalized_pattern in field_value


def _classify_with_user_rules(transaction: dict, user_rules: list[dict]) -> dict | None:
    for rule in user_rules or []:
        match_type = _normalize_method(rule.get("match_type"))
        title_pattern = rule.get("title_pattern")
        raw_category_pattern = rule.get("raw_category_pattern")

        title_value = _normalize_text(transaction.get("title"))
        category_value = _normalize_text(transaction.get("raw_category"))
        title_matches = _matches_user_rule(
            title_value,
            pattern=title_pattern,
            match_type=match_type,
        )
        category_matches = _matches_user_rule(
            category_value,
            pattern=raw_category_pattern,
            match_type=match_type,
        )

        if not title_matches and not category_matches:
            continue

        financial_type = _normalize_text(rule.get("financial_type"))
        direction = _normalize_text(rule.get("direction"))

        if not direction:
            if financial_type == "income":
                direction = "income"
            elif financial_type == "saving":
                direction = "saving_transfer"
            else:
                direction = "expense"

        category = _clean_label(rule.get("category")) or _normalize_category(
            raw_category_pattern or title_pattern
        )
        explanation_seed = _clean_label(raw_category_pattern or title_pattern)

        return _result(
            direction=direction,
            financial_type=financial_type,
            category=category,
            confidence_score=float(rule.get("confidence_score") or 0.95),
            explanation=f"Matched user rule: {explanation_seed}",
        )

    return None


def _result(
    *,
    direction: str,
    financial_type: str,
    category: str,
    confidence_score: float,
    explanation: str,
) -> dict:
    return {
        "direction": direction if direction in VALID_DIRECTIONS else "expense",
        "financial_type": (
            financial_type
            if financial_type in VALID_FINANCIAL_TYPES
            else "uncategorized"
        ),
        "category": canonicalize_category(category),
        "confidence_score": round(float(confidence_score), 2),
        "method": "rule",
        "explanation": explanation,
    }


def _confidence_for_field(field: dict, *, strong_category=False) -> float:
    if field["field"] == "raw_category":
        return 0.95 if strong_category else 0.90

    return field["confidence"]


def classify_transaction(transaction: dict, user_rules: list[dict] | None = None) -> dict:
    transaction = transaction or {}
    user_rule_result = _classify_with_user_rules(transaction, user_rules or [])

    if user_rule_result:
        return user_rule_result

    for field in _candidate_fields(transaction):
        if not field["normalized"]:
            continue

        for keyword, financial_type in EXPLICIT_EXPENSE_RULES:
            if keyword in field["normalized"]:
                return _result(
                    direction="expense",
                    financial_type=financial_type,
                    category=_normalize_category(keyword),
                    confidence_score=_confidence_for_field(field, strong_category=True),
                    explanation=f"Matched explicit expense rule: {keyword}",
                )

    for field in _candidate_fields(transaction):
        if not field["normalized"]:
            continue

        keyword = _keyword_match(field["normalized"], INCOME_KEYWORDS)
        if keyword:
            return _result(
                direction="income",
                financial_type="income",
                category=_normalize_category(keyword),
                confidence_score=_confidence_for_field(field, strong_category=True),
                explanation=f"Matched income keyword: {keyword}",
            )

    for field in _candidate_fields(transaction):
        if not field["normalized"]:
            continue

        keyword = _keyword_match(field["normalized"], SAVING_KEYWORDS)
        if keyword:
            return _result(
                direction="saving_transfer",
                financial_type="saving",
                category=_normalize_category(keyword),
                confidence_score=_confidence_for_field(field, strong_category=True),
                explanation=f"Matched saving keyword: {keyword}",
            )

    for field in _candidate_fields(transaction):
        if not field["normalized"]:
            continue

        keyword = _keyword_match(field["normalized"], NEED_KEYWORDS)
        if keyword:
            return _result(
                direction="expense",
                financial_type="need",
                category=_normalize_category(keyword),
                confidence_score=_confidence_for_field(field, strong_category=True),
                explanation=f"Matched need keyword: {keyword}",
            )

    for field in _candidate_fields(transaction):
        if not field["normalized"]:
            continue

        keyword = _keyword_match(field["normalized"], WANT_KEYWORDS)
        if keyword:
            return _result(
                direction="expense",
                financial_type="want",
                category=_normalize_category(keyword),
                confidence_score=_confidence_for_field(field, strong_category=True),
                explanation=f"Matched want keyword: {keyword}",
            )

    existing_direction = _normalize_text(transaction.get("direction"))
    if existing_direction == "income":
        return _result(
            direction="income",
            financial_type="income",
            category=_normalize_category(transaction.get("raw_category")),
            confidence_score=0.65,
            explanation="Fallback from existing direction: income",
        )

    if existing_direction == "saving_transfer":
        return _result(
            direction="saving_transfer",
            financial_type="saving",
            category=_normalize_category(transaction.get("raw_category")),
            confidence_score=0.65,
            explanation="Fallback from existing direction: saving_transfer",
        )

    if existing_direction == "expense":
        return _result(
            direction="expense",
            financial_type="uncategorized",
            category=_normalize_category(transaction.get("raw_category")),
            confidence_score=0.65,
            explanation="Fallback from existing direction: expense",
        )

    return _result(
        direction="expense",
        financial_type="uncategorized",
        category=_normalize_category(transaction.get("raw_category")),
        confidence_score=0.40,
        explanation="Fallback to uncategorized",
    )
