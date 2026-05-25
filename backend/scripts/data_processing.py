import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
import base64
import json
import os


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

def load_and_process_data(filename):
    all_sheets = pd.read_excel(filename, sheet_name=None)
    df_list = []
    for sheet_name, df in all_sheets.items():
        df['Sheet'] = sheet_name
        df_list.append(df)
    df_all = pd.concat(df_list, ignore_index=True)
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
        ("2026-01-05", "Gaji Reza", "Income", 18000000, "Reza"),
        ("2026-01-05", "Gaji Divya", "Income", 15000000, "Divya"),
        ("2026-01-06", "Tabungan Rumah", "Saving", 6000000, "Reza"),
        ("2026-01-07", "Investasi Bulanan", "Saving", 4500000, "Divya"),
        ("2026-01-09", "Belanja Bulanan", "Grocery", 1850000, "Reza"),
        ("2026-01-12", "Makan Weekend", "Makanan", 750000, "Divya"),
        ("2026-01-15", "Internet", "Tagihan", 450000, "Reza"),
        ("2026-02-05", "Gaji Reza", "Income", 18000000, "Reza"),
        ("2026-02-05", "Gaji Divya", "Income", 15000000, "Divya"),
        ("2026-02-06", "Tabungan Rumah", "Saving", 6200000, "Reza"),
        ("2026-02-07", "Investasi Bulanan", "Saving", 4700000, "Divya"),
        ("2026-02-09", "Belanja Bulanan", "Grocery", 2100000, "Divya"),
        ("2026-02-11", "Makan Siang", "Makanan", 880000, "Reza"),
        ("2026-02-20", "Transport", "Transportasi", 650000, "Reza"),
        ("2026-03-05", "Gaji Reza", "Income", 18500000, "Reza"),
        ("2026-03-05", "Gaji Divya", "Income", 15000000, "Divya"),
        ("2026-03-06", "Tabungan Rumah", "Saving", 6500000, "Reza"),
        ("2026-03-07", "Investasi Bulanan", "Saving", 4800000, "Divya"),
        ("2026-03-08", "Asuransi Tahunan", "Tagihan Tahunan", 12500000, "Reza"),
        ("2026-03-13", "Belanja Dapur", "Grocery", 1950000, "Divya"),
        ("2026-03-18", "Restoran", "Makanan", 950000, "Divya"),
        ("2026-04-05", "Gaji Reza", "Income", 18500000, "Reza"),
        ("2026-04-05", "Gaji Divya", "Income", 15500000, "Divya"),
        ("2026-04-06", "Tabungan Rumah", "Saving", 7000000, "Reza"),
        ("2026-04-07", "Investasi Bulanan", "Saving", 5000000, "Divya"),
        ("2026-04-10", "Belanja Bulanan", "Grocery", 2300000, "Reza"),
        ("2026-04-14", "Makan Keluarga", "Makanan", 1200000, "Divya"),
        ("2026-04-22", "Kesehatan", "Kesehatan", 850000, "Divya"),
        ("2026-05-05", "Gaji Reza", "Income", 19000000, "Reza"),
        ("2026-05-05", "Gaji Divya", "Income", 15500000, "Divya"),
        ("2026-05-06", "Tabungan Rumah", "Saving", 7200000, "Reza"),
        ("2026-05-07", "Investasi Bulanan", "Saving", 5200000, "Divya"),
        ("2026-05-09", "Belanja Bulanan", "Grocery", 2250000, "Reza"),
        ("2026-05-12", "Makan Weekend", "Makanan", 1100000, "Reza"),
        ("2026-05-19", "Listrik", "Tagihan", 780000, "Divya"),
    ]

    df_all = pd.DataFrame(
        records,
        columns=["Waktu Transaksi", "Nama Transaksi", "Kategori", "Harga", "Nama"],
    )
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

    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)

    df_list = []

    # --- ambil semua sheet ---
    for worksheet in spreadsheet.worksheets():
        sheet_name = worksheet.title
        records = worksheet.get_all_records()

        if not records:
            continue  # skip sheet kosong

        df = pd.DataFrame(records)
        df["Sheet"] = sheet_name
        df_list.append(df)

    if not df_list:
        raise ValueError("Tidak ada data yang bisa diproses")

    df_all = pd.concat(df_list, ignore_index=True)

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
