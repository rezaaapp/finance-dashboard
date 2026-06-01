REQUIRED_COLUMNS = [
    "Waktu Transaksi",
    "Nama Transaksi",
    "Kategori",
    "Harga",
    "Source Dana",
    "Keterangan",
]

OPTIONAL_COLUMNS = [
    "Nama",
]


def _normalize_header(value: str) -> str:
    return str(value or "").strip().casefold()


HEADER_ALIASES = {
    "Waktu Transaksi": ("Waktu Transaksi", "Tanggal", "Tanggal Transaksi"),
    "Nama Transaksi": ("Nama Transaksi", "Transaksi", "Deskripsi"),
    "Kategori": ("Kategori", "Category"),
    "Harga": ("Harga", "Amount", "Nominal"),
    "Source Dana": ("Source Dana", "Sumber Dana", "Payment Source"),
    "Keterangan": ("Keterangan", "Note", "Notes"),
    "Nama": ("Nama",),
}

CANONICAL_HEADER_BY_ALIAS = {
    _normalize_header(alias): canonical
    for canonical, aliases in HEADER_ALIASES.items()
    for alias in aliases
}


def canonicalize_header(value: str) -> str:
    normalized_value = _normalize_header(value)
    return CANONICAL_HEADER_BY_ALIAS.get(normalized_value, str(value or "").strip())


def validate_sheet_header(header: list[str]) -> dict:
    canonical_header = {
        canonicalize_header(column)
        for column in header
        if str(column or "").strip()
    }
    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in canonical_header
    ]

    return {
        "valid": not missing_columns,
        "missing_columns": missing_columns,
    }
