import pandas as pd
import logging
from sklearn.ensemble import IsolationForest


def detect_anomaly_pengeluaran(
    df_pengeluaran: pd.DataFrame,
    contamination: float = 0.03,
    random_state: int = 42
) -> pd.DataFrame:
    """
    Deteksi anomali pengeluaran menggunakan Isolation Forest
    Log hasil anomali ke logs/proses.log
    """

    if df_pengeluaran.empty:
        logging.info("Data pengeluaran kosong, tidak ada anomali.")
        return pd.DataFrame()

    df = df_pengeluaran.copy()
    df["Harga"] = pd.to_numeric(df["Harga"], errors="coerce").fillna(0)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=random_state
    )

    df["anomaly_flag"] = model.fit_predict(df[["Harga"]])
    anomaly_df = df[df["anomaly_flag"] == -1]

    logging.info(
        "Deteksi anomali selesai | Total transaksi=%s | Anomali=%s",
        len(df), len(anomaly_df)
    )

    for _, row in anomaly_df.iterrows():
        logging.warning(
            "ANOMALI TRANSAKSI | Tanggal=%s | Kategori=%s | Harga=Rp %.0f | Sheet=%s",
            row.get("Waktu Transaksi"),
            row.get("Kategori"),
            row.get("Harga"),
            row.get("Sheet")
        )

    return anomaly_df
