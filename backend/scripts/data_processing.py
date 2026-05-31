import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import dotenv_values
from pathlib import Path
import base64
import json
import os
import sys

from gspread.utils import absolute_range_name


REQUIRED_SERVICE_ACCOUNT_FIELDS = {
    "type",
    "project_id",
    "private_key",
    "client_email",
    "token_uri",
}


def _load_service_account_info(credentials_json):
    try:
        service_account_info = json.loads(credentials_json)
    except json.JSONDecodeError as error:
        raise ValueError(
            "GOOGLE_SERVICE_ACCOUNT_JSON bukan JSON valid. "
            "Gunakan isi file service account JSON secara utuh, atau pakai "
            "GOOGLE_SERVICE_ACCOUNT_JSON_BASE64."
        ) from error

    missing_fields = REQUIRED_SERVICE_ACCOUNT_FIELDS - set(service_account_info)

    if missing_fields:
        missing_list = ", ".join(sorted(missing_fields))
        raise ValueError(
            "GOOGLE_SERVICE_ACCOUNT_JSON tidak lengkap. "
            f"Field yang hilang: {missing_list}. "
            "Pastikan value berisi seluruh isi file service account JSON dari Google Cloud, "
            "bukan placeholder atau sebagian JSON."
        )

    return service_account_info


def _load_credentials_from_file(credentials_path, scopes):
    if not credentials_path:
        raise ValueError(
            "Set GOOGLE_SERVICE_ACCOUNT_JSON_BASE64, GOOGLE_SERVICE_ACCOUNT_JSON, "
            "atau GOOGLE_APPLICATION_CREDENTIALS"
        )

    cred_path = Path(credentials_path).expanduser()

    if not cred_path.is_absolute():
        backend_root = Path(__file__).resolve().parents[1]
        repo_root = backend_root.parent
        candidates = [
            Path.cwd() / cred_path,
            backend_root / cred_path,
            repo_root / cred_path,
        ]
        cred_path = next(
            (candidate for candidate in candidates if candidate.exists()),
            candidates[0]
        )

    if not cred_path.exists():
        raise FileNotFoundError(
            f"File kredensial Google tidak ditemukan: {cred_path}"
        )

    return Credentials.from_service_account_file(
        str(cred_path),
        scopes=scopes
    )


def get_google_sheets_client(scopes):
    credentials_json = (os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or "").strip()
    credentials_json_base64 = (
        os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_BASE64") or ""
    ).strip()
    credentials_path = (os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()

    if credentials_json_base64:
        try:
            credentials_json = base64.b64decode(
                credentials_json_base64
            ).decode("utf-8")
        except Exception as error:
            raise ValueError(
                "GOOGLE_SERVICE_ACCOUNT_JSON_BASE64 tidak valid. "
                "Generate ulang dari file service account JSON asli."
            ) from error

    if credentials_json:
        try:
            service_account_info = _load_service_account_info(credentials_json)
            creds = Credentials.from_service_account_info(
                service_account_info,
                scopes=scopes
            )
        except ValueError:
            if not credentials_path:
                raise

            creds = _load_credentials_from_file(credentials_path, scopes)
    else:
        creds = _load_credentials_from_file(credentials_path, scopes)

    return gspread.authorize(creds)


def _normalize_source_dana(df):
    if "Source Dana" not in df.columns:
        df["Source Dana"] = "Lainnya"

    df["Source Dana"] = (
        df["Source Dana"]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", "Lainnya")
    )

    return df


def _normalize_match_text(value):
    return str(value or "").strip().lower()


def _resolve_column(df, candidates):
    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    return None


def _load_classification_predictions(classification_path=None):
    backend_root = Path(__file__).resolve().parents[1]
    repo_root = backend_root.parent
    classification_json_base64 = (
        os.getenv("FINANCIAL_CLASSIFICATION_JSON_BASE64") or ""
    ).strip()
    classification_json = (
        os.getenv("FINANCIAL_CLASSIFICATION_JSON") or ""
    ).strip()

    if not classification_json_base64 and not classification_json:
        for env_path in [repo_root / ".env", backend_root / ".env"]:
            env_values = dotenv_values(env_path)
            classification_json_base64 = (
                env_values.get("FINANCIAL_CLASSIFICATION_JSON_BASE64")
                or classification_json_base64
                or ""
            ).strip()
            classification_json = (
                env_values.get("FINANCIAL_CLASSIFICATION_JSON")
                or classification_json
                or ""
            ).strip()

            if classification_json_base64 or classification_json:
                break

    if classification_json_base64:
        classification_json = base64.b64decode(
            classification_json_base64
        ).decode("utf-8")

    if classification_json:
        payload = json.loads(classification_json)

        if isinstance(payload, dict):
            return payload.get("predictions", [])

        if isinstance(payload, list):
            return payload

        return []

    if classification_path is None:
        classification_path = (
            backend_root
            / "output"
            / "financial-classification-reference.json"
        )

    classification_path = Path(classification_path)

    if not classification_path.exists():
        return []

    with classification_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if isinstance(payload, dict):
        return payload.get("predictions", [])

    if isinstance(payload, list):
        return payload

    return []


def aggregate_monthly_allocation(df_all, classification_path=None):
    """
    Join natural spreadsheet transaction text with AI classification output,
    then aggregate Rupiah values by month and 50/30/20 allocation type.
    Spreadsheet text is not translated or mutated beyond match normalization.
    """

    if df_all.empty:
        return []

    predictions = _load_classification_predictions(classification_path)

    if not predictions:
        return []

    title_column = _resolve_column(df_all, ["input_title", "Nama Transaksi"])
    category_column = _resolve_column(df_all, ["input_category", "Kategori"])
    date_column = _resolve_column(df_all, ["Tanggal", "Waktu Transaksi"])

    if not title_column or not category_column or not date_column:
        return []

    composite_lookup = {}
    title_lookup = {}

    for prediction in predictions:
        title_key = _normalize_match_text(prediction.get("input_title"))
        category_key = _normalize_match_text(prediction.get("input_category"))
        allocation_type = prediction.get("allocation_type")

        if allocation_type not in {"Needs", "Wants", "Savings"}:
            continue

        if title_key:
            title_lookup.setdefault(title_key, allocation_type)

        if title_key and category_key:
            composite_lookup.setdefault(
                f"{title_key}::{category_key}",
                allocation_type
            )

    df = df_all.copy()
    df = df[df[category_column].astype(str).str.strip() != "Income"]
    df["allocation_type"] = df.apply(
        lambda row: composite_lookup.get(
            f"{_normalize_match_text(row[title_column])}::"
            f"{_normalize_match_text(row[category_column])}"
        ) or title_lookup.get(_normalize_match_text(row[title_column])),
        axis=1,
    )
    df = df[df["allocation_type"].isin(["Needs", "Wants", "Savings"])]

    if df.empty:
        return []

    df[date_column] = pd.to_datetime(df[date_column], errors="coerce")
    df = df.dropna(subset=[date_column])
    df["month"] = df[date_column].dt.strftime("%Y-%m")

    grouped = (
        df.groupby(["month", "allocation_type"])["Harga"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
        .sort_values("month")
    )

    rows = []

    for _, row in grouped.iterrows():
        rows.append({
            "month": row["month"],
            "Needs": float(row.get("Needs", 0)),
            "Wants": float(row.get("Wants", 0)),
            "Savings": float(row.get("Savings", 0)),
        })

    return rows


def load_and_process_data(filename):
    all_sheets = pd.read_excel(filename, sheet_name=None)
    df_list = []
    for sheet_name, df in all_sheets.items():
        df['Sheet'] = sheet_name
        df_list.append(df)
    df_all = pd.concat(df_list, ignore_index=True)
    df_all = _normalize_source_dana(df_all)
    df_all['Waktu Transaksi'] = pd.to_datetime(df_all['Waktu Transaksi'])
    df_all['Harga'] = (
        df_all['Harga']
        .astype(str)
        .str.replace('Rp', '', regex=False)
        .str.replace(',', '', regex=False)
        .str.strip()
        .replace('', '0')
        .astype(float)
    )
    df_all['Bulan'] = df_all['Waktu Transaksi'].dt.to_period('M')
    
    df_pengeluaran = df_all[~df_all['Kategori'].isin(['Saving', 'Income'])]
    df_saving = df_all[df_all['Kategori'] == 'Saving']
    df_income = df_all[df_all['Kategori'] == 'Income']
    return df_all, df_pengeluaran, df_saving, df_income


def load_mock_financial_data():
    records = [
        ("2026-01-05", "Gaji Reza", "Income", 18000000, "Reza", "Gaji Reza"),
        ("2026-01-05", "Gaji Divya", "Income", 15000000, "Divya", "Gaji Divya"),
        ("2026-01-06", "Tabungan Rumah", "Saving", 6000000, "Reza", "Tabungan Rumah"),
        ("2026-01-07", "Investasi Bulanan", "Saving", 4500000, "Divya", "Investasi"),
        ("2026-01-09", "Belanja Bulanan", "Grocery", 1850000, "Reza", "BCA"),
        ("2026-01-12", "Makan Weekend", "Makanan", 750000, "Divya", "QRIS"),
        ("2026-01-15", "Internet", "Tagihan", 450000, "Reza", "Autodebet"),
        ("2026-02-05", "Gaji Reza", "Income", 18000000, "Reza", "Gaji Reza"),
        ("2026-02-05", "Gaji Divya", "Income", 15000000, "Divya", "Gaji Divya"),
        ("2026-02-06", "Tabungan Rumah", "Saving", 6200000, "Reza", "Tabungan Rumah"),
        ("2026-02-07", "Investasi Bulanan", "Saving", 4700000, "Divya", "Investasi"),
        ("2026-02-09", "Belanja Bulanan", "Grocery", 2100000, "Divya", "BCA"),
        ("2026-02-11", "Makan Siang", "Makanan", 880000, "Reza", "QRIS"),
        ("2026-02-20", "Transport", "Transportasi", 650000, "Reza", "E-Wallet"),
        ("2026-03-05", "Gaji Reza", "Income", 18500000, "Reza", "Gaji Reza"),
        ("2026-03-05", "Gaji Divya", "Income", 15000000, "Divya", "Gaji Divya"),
        ("2026-03-06", "Tabungan Rumah", "Saving", 6500000, "Reza", "Tabungan Rumah"),
        ("2026-03-07", "Investasi Bulanan", "Saving", 4800000, "Divya", "Investasi"),
        ("2026-03-08", "Asuransi Tahunan", "Tagihan Tahunan", 12500000, "Reza", "Kartu Kredit"),
        ("2026-03-13", "Belanja Dapur", "Grocery", 1950000, "Divya", "BCA"),
        ("2026-03-18", "Restoran", "Makanan", 950000, "Divya", "QRIS"),
        ("2026-04-05", "Gaji Reza", "Income", 18500000, "Reza", "Gaji Reza"),
        ("2026-04-05", "Gaji Divya", "Income", 15500000, "Divya", "Gaji Divya"),
        ("2026-04-06", "Tabungan Rumah", "Saving", 7000000, "Reza", "Tabungan Rumah"),
        ("2026-04-07", "Investasi Bulanan", "Saving", 5000000, "Divya", "Investasi"),
        ("2026-04-10", "Belanja Bulanan", "Grocery", 2300000, "Reza", "BCA"),
        ("2026-04-14", "Makan Keluarga", "Makanan", 1200000, "Divya", "QRIS"),
        ("2026-04-22", "Kesehatan", "Kesehatan", 850000, "Divya", "Debit"),
        ("2026-05-05", "Gaji Reza", "Income", 19000000, "Reza", "Gaji Reza"),
        ("2026-05-05", "Gaji Divya", "Income", 15500000, "Divya", "Gaji Divya"),
        ("2026-05-06", "Tabungan Rumah", "Saving", 7200000, "Reza", "Tabungan Rumah"),
        ("2026-05-07", "Investasi Bulanan", "Saving", 5200000, "Divya", "Investasi"),
        ("2026-05-09", "Belanja Bulanan", "Grocery", 2250000, "Reza", "BCA"),
        ("2026-05-12", "Makan Weekend", "Makanan", 1100000, "Reza", "QRIS"),
        ("2026-05-19", "Listrik", "Tagihan", 780000, "Divya", "Autodebet"),
    ]

    df_all = pd.DataFrame(
        records,
        columns=[
            "Waktu Transaksi",
            "Nama Transaksi",
            "Kategori",
            "Harga",
            "Nama",
            "Source Dana",
        ],
    )
    df_all = _normalize_source_dana(df_all)
    df_all["Sheet"] = "Mock"
    df_all["Waktu Transaksi"] = pd.to_datetime(df_all["Waktu Transaksi"])
    df_all["Harga"] = df_all["Harga"].astype(float)
    df_all["Bulan"] = df_all["Waktu Transaksi"].dt.to_period("M")

    df_pengeluaran = df_all[~df_all["Kategori"].isin(["Saving", "Income"])]
    df_saving = df_all[df_all["Kategori"] == "Saving"]
    df_income = df_all[df_all["Kategori"] == "Income"]

    return df_all, df_pengeluaran, df_saving, df_income


def load_and_process_data_from_spreadsheet(sheet_id):
    """
    Load & process data from Google Spreadsheet (ALL SHEETS)
    """

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    client = get_google_sheets_client(scopes)
    spreadsheet = client.open_by_key(sheet_id)

    df_list = []
    worksheets = spreadsheet.worksheets()
    ranges = [
        absolute_range_name(worksheet.title)
        for worksheet in worksheets
    ]

    if not ranges:
        raise ValueError("Tidak ada data yang bisa diproses")

    values_response = spreadsheet.values_batch_get(ranges)
    value_ranges = values_response.get("valueRanges", [])

    # Ambil seluruh worksheet dalam satu Sheets API read request.
    for worksheet, value_range in zip(worksheets, value_ranges):
        values = value_range.get("values", [])

        if len(values) < 2:
            continue  # skip sheet kosong atau hanya header

        headers = [str(header).strip() for header in values[0]]
        records = []

        for row in values[1:]:
            if not any(str(value).strip() for value in row):
                continue

            padded_row = row + [""] * (len(headers) - len(row))
            records.append(dict(zip(headers, padded_row[:len(headers)])))

        if not records:
            continue

        sheet_name = worksheet.title
        df = pd.DataFrame(records)
        df["Sheet"] = sheet_name
        df_list.append(df)

    if not df_list:
        raise ValueError("Tidak ada data yang bisa diproses")

    df_all = pd.concat(df_list, ignore_index=True)
    df_all = _normalize_source_dana(df_all)

    # ===== PROSES DATA (SAMA DENGAN EXCEL) =====
    df_all["Waktu Transaksi"] = pd.to_datetime(df_all["Waktu Transaksi"], errors='coerce')

    df_all["Harga"] = (
        df_all["Harga"]
        .astype(str)
        .str.replace("Rp", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
        .replace("", "0")
        .astype(float)
    )

    df_all["Bulan"] = df_all["Waktu Transaksi"].dt.to_period("M")

    df_pengeluaran = df_all[~df_all["Kategori"].isin(["Saving", "Income"])]
    df_saving = df_all[df_all["Kategori"] == "Saving"]
    df_income = df_all[df_all["Kategori"] == "Income"]

    return df_all, df_pengeluaran, df_saving, df_income


def _run_monthly_allocation_cli():
    sheet_id = os.getenv("GOOGLE_SPREADSHEET_ID") or os.getenv("GOOGLE_SHEET_ID")

    if not sheet_id:
        raise ValueError("GOOGLE_SPREADSHEET_ID or GOOGLE_SHEET_ID is required")

    df_all, _, _, _ = load_and_process_data_from_spreadsheet(sheet_id)
    result = aggregate_monthly_allocation(df_all)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "monthly-allocation":
        _run_monthly_allocation_cli()
