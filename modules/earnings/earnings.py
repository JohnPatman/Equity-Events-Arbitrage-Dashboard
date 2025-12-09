import yfinance as yf
import pandas as pd

def load_earnings(ticker):
    """
    Robust earnings loader that works on Streamlit Cloud.
    Avoids .get_earnings_dates() which Cloud blocks.
    Uses only .earnings_dates and auto-detects the next earnings row.
    """

    t = yf.Ticker(ticker)

    # ----- Load earnings history -----
    try:
        df = t.earnings_dates
    except Exception:
        return None, None

    if df is None or df.empty:
        return None, None

    df = df.reset_index().rename(columns={"index": "Earnings Date"})

    # auto-detect column names
    date_col = "Earnings Date"
    est_col = next((c for c in df.columns if "estimate" in c.lower()), None)
    rep_col = next((c for c in df.columns if "reported" in c.lower()), None)

    if not est_col or not rep_col:
        return None, None

    df = df.rename(columns={
        est_col: "EPS Estimate",
        rep_col: "Reported EPS"
    })

    df["Earnings Date"] = pd.to_datetime(df["Earnings Date"], errors="coerce")

    # Surprise %
    df["Surprise(%)"] = (
        (df["Reported EPS"] - df["EPS Estimate"]) /
        df["EPS Estimate"]
    ) * 100

    # ---- Detect NEXT earnings date (future-dated row) ----
    now = pd.Timestamp.utcnow()

    future_rows = df[df["Earnings Date"] > now]

    if not future_rows.empty:
        next_row = future_rows.sort_values("Earnings Date").iloc[0]
        next_date = next_row["Earnings Date"]
        next_eps = next_row["EPS Estimate"]
    else:
        next_date = None
        next_eps = None

    stats = {
        "next_date": next_date,
        "next_eps": next_eps,
        "avg_surprise": df["Surprise(%)"].mean(),
        "std_surprise": df["Surprise(%)"].std(),
        "beat_rate": (df["Surprise(%)"] > 0).mean() * 100
    }

    return df, stats
