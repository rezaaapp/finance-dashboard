from scripts.data_processing import load_and_process_data_from_spreadsheet
from scripts.anomaly_detection import detect_anomaly_pengeluaran
from app.config import settings
from app.cache.data_cache import cached_data, last_fetch_time, CACHE_DURATION
from datetime import datetime
import pandas as pd


# =========================
# CACHE DATA
# =========================
def get_financial_data():
    global cached_data, last_fetch_time

    now = datetime.now()

    if (
        cached_data is not None
        and last_fetch_time is not None
        and now - last_fetch_time < CACHE_DURATION
    ):
        print("USING CACHE")
        return cached_data

    print("FETCH FROM GOOGLE SHEETS")

    data = load_and_process_data_from_spreadsheet(settings.GOOGLE_SHEET_ID)

    cached_data = data
    last_fetch_time = now

    return data


# =========================
# SAFE FILTER HELPERS
# =========================
def _filter(df, year=None, month=None):
    if year:
        df = df[df["Waktu Transaksi"].dt.year == int(year)]

    if month:
        df = df[df["Waktu Transaksi"].dt.month == int(month)]

    return df


def _trend_vs_last_month(df, year=None, month=None):
    if df.empty:
        return 0

    if month:
        current_period = pd.Period(
            f"{int(year)}-{int(month):02d}",
            freq="M"
        )
    else:
        year_df = _filter(df, year)

        if year_df.empty:
            return 0

        current_period = year_df["Bulan"].max()

    previous_period = current_period - 1
    current_total = df[df["Bulan"] == current_period]["Harga"].sum()
    previous_total = df[df["Bulan"] == previous_period]["Harga"].sum()

    if previous_total <= 0:
        return 0

    return round((current_total - previous_total) / previous_total * 100, 2)


# =========================
# SUMMARY
# =========================
def get_summary(year=None, month=None):
    _, df_pengeluaran, df_saving, df_income = get_financial_data()

    trend_pengeluaran = _trend_vs_last_month(df_pengeluaran, year, month)
    trend_saving = _trend_vs_last_month(df_saving, year, month)
    trend_income = _trend_vs_last_month(df_income, year, month)

    df_pengeluaran = _filter(df_pengeluaran, year, month)
    df_saving = _filter(df_saving, year, month)
    df_income = _filter(df_income, year, month)

    total_pengeluaran = float(df_pengeluaran["Harga"].sum())
    total_saving = float(df_saving["Harga"].sum())
    total_income = float(df_income["Harga"].sum())

    saving_ratio = (total_saving / total_pengeluaran * 100) if total_pengeluaran > 0 else 0
    surplus = total_income - total_pengeluaran

    return {
        "total_pengeluaran": total_pengeluaran,
        "total_saving": total_saving,
        "total_income": total_income,
        "trend_pengeluaran": trend_pengeluaran,
        "trend_saving": trend_saving,
        "trend_income": trend_income,
        "saving_ratio": round(saving_ratio, 2),
        "surplus": float(surplus),
    }


# =========================
# MONTHLY SERIES
# =========================
def get_monthly_spending(year=None, month=None):
    _, df_pengeluaran, _, _ = get_financial_data()
    df_pengeluaran = _filter(df_pengeluaran, year, month)

    grouped = df_pengeluaran.groupby("Bulan")["Harga"].sum().reset_index()

    return [
        {"bulan": str(row["Bulan"]), "total": float(row["Harga"])}
        for _, row in grouped.iterrows()
    ]


def get_monthly_saving(year=None, month=None):
    _, _, df_saving, _ = get_financial_data()
    df_saving = _filter(df_saving, year, month)

    grouped = df_saving.groupby("Bulan")["Harga"].sum().reset_index()

    return [
        {"bulan": str(row["Bulan"]), "total": float(row["Harga"])}
        for _, row in grouped.iterrows()
    ]


def get_monthly_income(year=None, month=None):
    _, _, _, df_income = get_financial_data()
    df_income = _filter(df_income, year, month)

    grouped = df_income.groupby("Bulan")["Harga"].sum().reset_index()

    return [
        {"bulan": str(row["Bulan"]), "total": float(row["Harga"])}
        for _, row in grouped.iterrows()
    ]


# =========================
# TOP SPENDING (FIXED BUG IMPORTANT)
# =========================
def get_top_spending(year=None, month=None, limit=10):
    _, df_pengeluaran, _, _ = get_financial_data()
    df_pengeluaran = _filter(df_pengeluaran, year, month)

    if df_pengeluaran.empty:
        return []

    latest_month = df_pengeluaran["Bulan"].max()

    top = (
        df_pengeluaran[df_pengeluaran["Bulan"] == latest_month]
        .sort_values("Harga", ascending=False)
        .head(limit)
    )

    return [
        {
            "nama_transaksi": row["Nama Transaksi"],
            "kategori": row["Kategori"],
            "harga": float(row["Harga"]),
            "nama": row["Nama"],
            "bulan": str(row["Bulan"]),
        }
        for _, row in top.iterrows()
    ]


# =========================
# CATEGORY
# =========================
def get_spending_by_category(year=None, month=None):
    _, df_pengeluaran, _, _ = get_financial_data()
    df_pengeluaran = _filter(df_pengeluaran, year, month)

    grouped = (
        df_pengeluaran.groupby("Kategori")["Harga"]
        .sum()
        .reset_index()
        .sort_values("Harga", ascending=False)
    )

    return grouped.to_dict(orient="records")


# =========================
# PERSON
# =========================
def get_spending_per_person(year=None, month=None):
    _, df_pengeluaran, _, _ = get_financial_data()
    df_pengeluaran = _filter(df_pengeluaran, year, month)

    grouped = df_pengeluaran.groupby("Nama")["Harga"].sum().reset_index()

    return grouped.to_dict(orient="records")


# =========================
# GROCERY VS FOOD
# =========================
def get_grocery_vs_food(year=None, month=None):
    _, df_pengeluaran, _, _ = get_financial_data()
    df_pengeluaran = _filter(df_pengeluaran, year, month)

    df_food = df_pengeluaran[df_pengeluaran["Kategori"].isin(["Grocery", "Makanan"])]

    grouped = (
        df_food.groupby(["Bulan", "Kategori"])["Harga"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )

    return [
        {
            "bulan": str(row["Bulan"]),
            "Grocery": float(row.get("Grocery", 0)),
            "Makanan": float(row.get("Makanan", 0)),
        }
        for _, row in grouped.iterrows()
    ]


# =========================
# ANOMALY
# =========================
def get_anomalies(year=None, month=None):
    _, df_pengeluaran, _, _ = get_financial_data()
    df_pengeluaran = _filter(df_pengeluaran, year, month)

    anomalies = detect_anomaly_pengeluaran(df_pengeluaran)

    if anomalies.empty:
        return []

    return anomalies[
        ["Waktu Transaksi", "Kategori", "Harga", "Nama", "Nama Transaksi"]
    ].to_dict(orient="records")


# =========================
# INSIGHT
# =========================
def get_latest_insight(year=None, month=None):
    _, df_pengeluaran, df_saving, df_income = get_financial_data()

    df_pengeluaran = _filter(df_pengeluaran, year, month)
    df_saving = _filter(df_saving, year, month)
    df_income = _filter(df_income, year, month)

    if df_pengeluaran.empty:
        return {
            "bulan": None,
            "spending": 0,
            "saving": 0,
            "income": 0,
            "saving_ratio": 0,
            "status": "NO_DATA",
        }

    latest_month = df_pengeluaran["Bulan"].max()

    spending = df_pengeluaran[df_pengeluaran["Bulan"] == latest_month]["Harga"].sum()
    saving = df_saving[df_saving["Bulan"] == latest_month]["Harga"].sum()
    income = df_income[df_income["Bulan"] == latest_month]["Harga"].sum()

    saving_ratio = (saving / spending * 100) if spending > 0 else 0

    return {
        "bulan": str(latest_month),
        "spending": float(spending),
        "saving": float(saving),
        "income": float(income),
        "saving_ratio": round(saving_ratio, 2),
        "status": "HEALTHY" if saving_ratio >= 30 else "WARNING",
    }


# =========================
# AVAILABLE YEARS (FIX FLOAT ISSUE)
# =========================
def get_available_years():
    df_all, _, _, _ = get_financial_data()

    years = (
        df_all["Waktu Transaksi"]
        .dt.year
        .dropna()
        .astype(int)
        .unique()
    )

    return sorted(years.tolist(), reverse=True)
