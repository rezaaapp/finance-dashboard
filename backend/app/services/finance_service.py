from scripts.data_processing import load_and_process_data_from_spreadsheet
from app.config import settings

def get_financial_data():
    return load_and_process_data_from_spreadsheet(
        settings.GOOGLE_SHEET_ID
    )

def get_monthly_spending():
    _, df_pengeluaran, _, _ = get_financial_data()

    monthly = (
        df_pengeluaran
        .groupby("Bulan")["Harga"]
        .sum()
        .reset_index()
    )

    monthly["Bulan"] = monthly["Bulan"].astype(str)

    return monthly.to_dict(orient="records")