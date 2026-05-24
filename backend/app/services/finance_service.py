from scripts.data_processing import load_and_process_data_from_spreadsheet
from scripts.anomaly_detection import detect_anomaly_pengeluaran
from app.config import settings
from app.cache.data_cache import (
    cached_data,
    last_fetch_time,
    CACHE_DURATION
)
from datetime import datetime

def get_financial_data():
    global cached_data
    global last_fetch_time

    now = datetime.now()

    # Pakai cache jika belum expired
    if (
        cached_data is not None and
        last_fetch_time is not None and
        now - last_fetch_time < CACHE_DURATION
    ):
        print("USING CACHE")
        return cached_data

    print("FETCH FROM GOOGLE SHEETS")

    data = load_and_process_data_from_spreadsheet(
        settings.GOOGLE_SHEET_ID
    )

    cached_data = data
    last_fetch_time = now

    return data

def get_summary(year=None, month=None):

    df_all, df_pengeluaran, df_saving, df_income = get_financial_data()

    # FILTER YEAR
    if year:
        df_pengeluaran = df_pengeluaran[
            df_pengeluaran["Waktu Transaksi"].dt.year == int(year)
        ]

        df_saving = df_saving[
            df_saving["Waktu Transaksi"].dt.year == int(year)
        ]

        df_income = df_income[
            df_income["Waktu Transaksi"].dt.year == int(year)
        ]

    # FILTER MONTH
    if month:
        df_pengeluaran = df_pengeluaran[
            df_pengeluaran["Waktu Transaksi"].dt.month == int(month)
        ]

        df_saving = df_saving[
            df_saving["Waktu Transaksi"].dt.month == int(month)
        ]

        df_income = df_income[
            df_income["Waktu Transaksi"].dt.month == int(month)
        ]

    total_pengeluaran = float(df_pengeluaran["Harga"].sum())

    total_saving = float(df_saving["Harga"].sum())

    total_income = float(df_income["Harga"].sum())

    saving_ratio = (
        (total_saving / total_pengeluaran) * 100
        if total_pengeluaran > 0 else 0
    )

    surplus = total_income - total_pengeluaran

    return {
        "total_pengeluaran": total_pengeluaran,
        "total_saving": total_saving,
        "total_income": total_income,
        "saving_ratio": round(saving_ratio, 2),
        "surplus": surplus
    }

def get_monthly_spending(year=None, month=None):
    _, df_pengeluaran, _, _ = get_financial_data()

    if year:
        df_pengeluaran = df_pengeluaran[
            df_pengeluaran["Waktu Transaksi"].dt.year == year
        ]

    if month:
        df_pengeluaran = df_pengeluaran[
            df_pengeluaran["Waktu Transaksi"].dt.month == month
        ]

    grouped = (
        df_pengeluaran
        .groupby("Bulan")["Harga"]
        .sum()
        .reset_index()
    )

    grouped["Bulan"] = grouped["Bulan"].astype(str)

    return [
        {
            "bulan": row["Bulan"],
            "total": float(row["Harga"])
        }
        for _, row in grouped.iterrows()
    ]
def get_monthly_saving(year=None, month=None):
    _, _, df_saving, _ = get_financial_data()

    if year:
        df_saving = df_saving[
            df_saving["Waktu Transaksi"].dt.year == int(year)
        ]

    if month:
        df_saving = df_saving[
            df_saving["Waktu Transaksi"].dt.month == month
        ]

    monthly = (
        df_saving
        .groupby("Bulan")["Harga"]
        .sum()
        .reset_index()
    )

    monthly["Bulan"] = monthly["Bulan"].astype(str)

    return [
        {
            "bulan": row["Bulan"],
            "total": float(row["Harga"])
        }
        for _, row in monthly.iterrows()
    ]

def get_monthly_income(year=None, month=None):
    _, _, _, df_income = get_financial_data()

    if year:
        df_income = df_income[
            df_income["Waktu Transaksi"].dt.year == int(year)
        ]

    if month:
        df_income = df_income[
            df_income["Waktu Transaksi"].dt.month == month
        ]

    grouped = (
        df_income
        .groupby("Bulan")["Harga"]
        .sum()
        .reset_index()
    )

    grouped["Bulan"] = grouped["Bulan"].astype(str)

    return [
        {
            "bulan": row["Bulan"],
            "total": float(row["Harga"])
        }
        for _, row in grouped.iterrows()
    ]

def get_top_spending(year=None, month=None, limit=10):
    _, df_pengeluaran, _, _ = get_financial_data()

    if year:
        df_pengeluaran = df_pengeluaran[
            df_pengeluaran["Waktu Transaksi"].dt.year == int(year)
        ]

    if month:
        df_pengeluaran = df_pengeluaran[
            df_pengeluaran["Waktu Transaksi"].dt.month == month
        ]

    if df_pengeluaran.empty:
        return []

    latest_month = (
        df_pengeluaran["Bulan"]
        .sort_values()
        .iloc[-1]
    )

    top_spending = (
        df_pengeluaran[
            df_pengeluaran["Bulan"] == latest_month
        ]
        .sort_values("Harga", ascending=False)
        .head(limit)
    )

    return [
        {
            "nama_transaksi": row["Nama Transaksi"],
            "kategori": row["Kategori"],
            "harga": float(row["Harga"]),
            "nama": row["Nama"],
            "bulan": str(row["Bulan"])
        }
        for _, row in top_spending.iterrows()
    ]

def get_spending_by_category(year=None, month=None):
    _, df_pengeluaran, _, _ = get_financial_data()

    if year:
        df_pengeluaran = df_pengeluaran[
            df_pengeluaran["Waktu Transaksi"].dt.year == int(year)
        ]

    if month:
        df_pengeluaran = df_pengeluaran[
            df_pengeluaran["Waktu Transaksi"].dt.month == month
        ]

    kategori = (
        df_pengeluaran
        .groupby("Kategori")["Harga"]
        .sum()
        .reset_index()
        .sort_values("Harga", ascending=False)
    )

    return kategori.to_dict(orient="records")

def get_spending_per_person(year=None, month=None):
    _, df_pengeluaran, _, _ = get_financial_data()

    if year:
        df_pengeluaran = df_pengeluaran[
            df_pengeluaran["Waktu Transaksi"].dt.year == int(year)
        ]

    if month:
        df_pengeluaran = df_pengeluaran[
            df_pengeluaran["Waktu Transaksi"].dt.month == month
        ]

    person = (
        df_pengeluaran
        .groupby("Nama")["Harga"]
        .sum()
        .reset_index()
    )

    return person.to_dict(orient="records")

def get_grocery_vs_food(year=None, month=None):
    _, df_pengeluaran, _, _ = get_financial_data()

    if year:
            df_pengeluaran = df_pengeluaran[    
                df_pengeluaran["Waktu Transaksi"].dt.year == int(year)
            ]   
    if month:
        df_pengeluaran = df_pengeluaran[
            df_pengeluaran["Waktu Transaksi"].dt.month == month
        ]
    df_food = df_pengeluaran[
        df_pengeluaran["Kategori"]
        .isin(["Grocery", "Makanan"])
    ]

    grouped = (
        df_food
        .groupby(["Bulan", "Kategori"])["Harga"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )

    grouped["Bulan"] = grouped["Bulan"].astype(str)

    return grouped.to_dict(orient="records")

def get_anomalies(year=None, month=None):
    _, df_pengeluaran, _, _ = get_financial_data()

    if year:
        df_pengeluaran = df_pengeluaran[
            df_pengeluaran["Waktu Transaksi"].dt.year == int(year)
        ]

    if month:
        df_pengeluaran = df_pengeluaran[
            df_pengeluaran["Waktu Transaksi"].dt.month == month
        ]

    anomalies = detect_anomaly_pengeluaran(
        df_pengeluaran
    )

    anomalies["Bulan"] = anomalies["Bulan"].astype(str)

    return anomalies[
        [
            "Waktu Transaksi",
            "Kategori",
            "Harga",
            "Nama",
            "Nama Transaksi"
        ]
    ].to_dict(orient="records")

def get_latest_insight(year=None, month=None):
    _, df_pengeluaran, df_saving, df_income = get_financial_data()

    if year:
        df_pengeluaran = df_pengeluaran[
            df_pengeluaran["Waktu Transaksi"].dt.year == int(year)
        ]

    if month:
        df_pengeluaran = df_pengeluaran[
            df_pengeluaran["Waktu Transaksi"].dt.month == month
        ]

    latest_month = (
        df_pengeluaran["Bulan"]
        .sort_values()
        .iloc[-1]
    )

    current_spending = (
        df_pengeluaran[
            df_pengeluaran["Bulan"] == latest_month
        ]["Harga"].sum()
    )

    current_saving = (
        df_saving[
            df_saving["Bulan"] == latest_month
        ]["Harga"].sum()
    )

    current_income = (
        df_income[
            df_income["Bulan"] == latest_month
        ]["Harga"].sum()
    )

    saving_ratio = (
        (current_saving / current_spending) * 100
        if current_spending > 0 else 0
    )

    return {
        "bulan": str(latest_month),
        "spending": current_spending,
        "saving": current_saving,
        "income": current_income,
        "saving_ratio": round(saving_ratio, 2),
        "status": (
            "HEALTHY"
            if saving_ratio >= 30
            else "WARNING"
        )
    }

def get_available_years():
    df_all, _, _, _ = get_financial_data()

    years = (
        df_all["Waktu Transaksi"]
        .dt.year
        .dropna()
        .unique()
    )

    years = sorted(years.tolist(), reverse=True)

    return years

# =========================
# FILTER YEAR HELPER
# =========================
def filter_by_year(df, year):
    if year:
        return df[
            df["Waktu Transaksi"].dt.year == int(year)
        ]
    return df
