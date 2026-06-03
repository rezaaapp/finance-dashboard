import re


AMBIGUOUS_MARKETPLACE_KEYWORDS = (
    "tokopedia",
    "shopee",
    "transfer",
    "bca",
    "mandiri",
)

SUGGESTION_RULES = (
    {
        "keywords": ("income", "gaji", "salary", "bonus"),
        "direction": "income",
        "financial_type": "income",
        "category": "Income",
        "confidence_score": 0.92,
        "reason": "Matched income keyword",
    },
    {
        "keywords": ("saving", "tabungan", "investasi", "reksadana", "saham", "emas"),
        "direction": "saving_transfer",
        "financial_type": "saving",
        "category": "Saving",
        "confidence_score": 0.92,
        "reason": "Matched saving keyword",
    },
    {
        "keywords": ("tagihan tahunan", "tagihan non rutin"),
        "direction": "expense",
        "financial_type": "need",
        "category": "Bills",
        "confidence_score": 0.91,
        "reason": "Matched bills keyword",
    },
    {
        "keywords": ("gift",),
        "direction": "expense",
        "financial_type": "want",
        "category": "Gift",
        "confidence_score": 0.90,
        "reason": "Matched gift keyword",
    },
    {
        "keywords": ("netflix", "spotify", "subscription"),
        "direction": "expense",
        "financial_type": "want",
        "category": "Subscription",
        "confidence_score": 0.90,
        "reason": "Matched subscription keyword",
    },
    {
        "keywords": ("laundry", "perlengkapan rumah", "service", "maintenance"),
        "direction": "expense",
        "financial_type": "need",
        "category": "Household",
        "confidence_score": 0.82,
        "reason": "Matched household keyword",
    },
    {
        "keywords": ("cafe", "resto", "jajan"),
        "direction": "expense",
        "financial_type": "want",
        "category": "Food",
        "confidence_score": 0.86,
        "reason": "Matched food want keyword",
    },
    {
        "keywords": ("bensin", "parkir", "transportasi"),
        "direction": "expense",
        "financial_type": "need",
        "category": "Transport",
        "confidence_score": 0.86,
        "reason": "Matched transport keyword",
    },
    {
        "keywords": ("transportasi non rutin",),
        "direction": "expense",
        "financial_type": "want",
        "category": "Transport",
        "confidence_score": 0.91,
        "reason": "Matched non-routine transport keyword",
    },
)


def normalize_text(value) -> str:
    normalized = str(value or "").strip().casefold()
    return re.sub(r"\s+", " ", normalized)


def infer_pattern_type(group: dict) -> str:
    if group["group_type"] == "raw_category":
        return "raw_category_equals"

    if group["group_type"] == "source_fund":
        return "source_fund_contains"

    return "title_contains"


def is_ambiguous_marketplace(pattern: str) -> bool:
    normalized_pattern = normalize_text(pattern)
    return any(keyword in normalized_pattern for keyword in AMBIGUOUS_MARKETPLACE_KEYWORDS)


def suggest_rule_for_group(group: dict) -> dict | None:
    pattern = str(group.get("pattern") or "").strip()
    normalized_pattern = normalize_text(pattern)

    if not normalized_pattern:
        return None

    for rule in SUGGESTION_RULES:
        for keyword in rule["keywords"]:
            if keyword not in normalized_pattern:
                continue

            if is_ambiguous_marketplace(pattern):
                return None

            confidence_score = float(rule["confidence_score"])
            if confidence_score < 0.70:
                return None

            return {
                "pattern_type": infer_pattern_type(group),
                "pattern": pattern,
                "suggested_direction": rule["direction"],
                "suggested_financial_type": rule["financial_type"],
                "suggested_category": rule["category"],
                "confidence_score": confidence_score,
                "matched_transactions": int(group.get("rows") or 0),
                "total_amount": float(group.get("total_amount") or 0),
                "reason": f"{rule['reason']}: {keyword}",
                "auto_apply_eligible": confidence_score >= 0.90,
            }

    return None


def build_suggestions(groups: list[dict]) -> list[dict]:
    suggestions = []

    for group in groups:
        suggestion = suggest_rule_for_group(group)

        if suggestion:
            suggestions.append(suggestion)

    return suggestions
