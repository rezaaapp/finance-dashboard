import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
import base64
import json
import os

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


def load_and_process_data_from_spreadsheet(sheet_id):
    """
    Load & process data from Google Spreadsheet (ALL SHEETS)
    """

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    credentials_json_base64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_BASE64")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if credentials_json_base64:
        credentials_json = base64.b64decode(credentials_json_base64).decode("utf-8")

    if credentials_json:
        creds = Credentials.from_service_account_info(
            json.loads(credentials_json),
            scopes=scopes
        )
    else:
        if not credentials_path:
            raise ValueError(
                "Set GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SERVICE_ACCOUNT_JSON_BASE64, "
                "atau GOOGLE_APPLICATION_CREDENTIALS"
            )

        cred_path = Path(credentials_path).expanduser()

        if not cred_path.exists():
            raise FileNotFoundError(
                "GOOGLE_APPLICATION_CREDENTIALS belum diset atau file kredensial tidak ditemukan"
            )

        creds = Credentials.from_service_account_file(
            str(cred_path), scopes=scopes
        )

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
