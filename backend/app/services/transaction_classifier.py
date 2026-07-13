import re


INCOME_KEYWORDS = (
    "income",
    "gaji",
    "salary",
    "bonus",
    "pendapatan",
    "pemasukan",
)

EXPLICIT_EXPENSE_KEYWORDS = (
    "tagihan non rutin",
    "tagihan tahunan",
    "gift",
    "transportasi non rutin",
)

FALLBACK_SAVING_KEYWORDS = (
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

CATEGORY_RULES = (
    ("Income", ("income",)),
    ("Saving", ("saving",)),
    ("Tagihan non rutin", ("tagihan non rutin",)),
    ("Tagihan Tahunan", ("tagihan tahunan",)),
    ("Gift", ("gift",)),
    ("Transportasi non rutin", ("transportasi non rutin",)),
    ("Grocery", ("groceries", "grocery", "belanja bulanan")),
    ("Food", ("food", "makanan", "jajan", "resto", "restaurant")),
    ("Transportasi Rutin", ("transport", "transportasi", "bensin", "parkir", "gojek", "grab")),
    ("Housing", ("rent", "apartemen", "sewa")),
    ("Utilities", ("listrik", "internet", "utility")),
    ("Health", ("health", "obat", "dokter")),
    ("Entertainment", ("entertainment", "hiburan", "pacaran")),
)


def _normalize_text(value: str | None) -> str:
    normalized = str(value or "").strip().casefold()
    return re.sub(r"\s+", " ", normalized)


def _contains_keyword(value: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in value for keyword in keywords)


def classify_direction(
    raw_category: str | None,
    title: str | None,
    source_fund: str | None,
    note: str | None,
    sheet_name: str | None,
) -> str:
    normalized_category = _normalize_text(raw_category)

    if normalized_category == "income":
        return "income"

    if normalized_category == "saving":
        return "saving_transfer"

    if normalized_category:
        return "expense"

    return "expense"


def normalize_category(raw_category: str | None) -> str:
    normalized_category = _normalize_text(raw_category)

    if not normalized_category:
        return "Uncategorized"

    for category, keywords in CATEGORY_RULES:
        if _contains_keyword(normalized_category, keywords):
            return category

    return str(raw_category or "").strip()
