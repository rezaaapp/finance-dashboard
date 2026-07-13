import re


CANONICAL_CATEGORY_ALIASES = {
    "groceries": "Grocery",
    "grocery": "Grocery",
    "bills": "Tagihan Bulanan",
    "tagihan rutin": "Tagihan Bulanan",
    "tagihan bulanan": "Tagihan Bulanan",
    "makanan": "Food",
    "food": "Food",
    "transport": "Transportasi Rutin",
    "transportasi": "Transportasi Rutin",
}


def normalize_category_key(value) -> str:
    normalized = str(value or "").strip().casefold()
    return re.sub(r"\s+", " ", normalized)


def canonicalize_category(value, *, fallback: str = "Uncategorized") -> str:
    cleaned = re.sub(r"\s+", " ", str(value or "").strip())

    if not cleaned:
        return fallback

    key = normalize_category_key(cleaned)

    return CANONICAL_CATEGORY_ALIASES.get(key, cleaned)
