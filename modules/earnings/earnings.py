import yfinance as yf
import pandas as pd

def load_earnings(ticker):
    """
    Stable earnings loader using earnings_dates.
    Works on Python 3.14 and Streamlit Cloud.
    """

    t = yf.Ticker(ticker)

    # Try earnings_dates (best data source)
    try:
        df = t.earnings_dates
    except Exception:
        return None, None

    if df is None or df.empty:
        return None, None

    # Reset index -> create column "Earnings Date"
    df = df.reset_index().rename(columns={"index": "Earnings Date"})

    # Detect EPS estimate and EPS reported columns
    est_col = next((c for c in df.columns if "estimate" in c.lower()), None)
    rep_col = next((c for c in df.columns if "reported" in c.lower()), None)

    if not est_col or not rep_col:
        return None, None

    df = df.rename(columns={
        est_col: "EPS Estimate",
        rep_col: "Reported EPS"
    })

    # Datatypes
    df["Earnings Date"] = pd.to_datetime(df["Earnings Date"], errors="coerce")
    df["EPS Estimate"] = pd.to_numeric(df["EPS Estimate"], errors="coerce")
    df["Reported EPS"] = pd.to_numeric(df["Reported EPS"], errors="coerce")

    # Surprise %
    df["Surprise(%)"] = (
        (df["Reported EPS"] - df["EPS Estimate"]) /
        df["EPS Estimate"]
    ) * 100

    # Detect next earnings date (future)
    now = pd.Timestamp.utcnow()
    future = df[df["Earnings Date"] > now]

    if not future.empty:
        next_row = future.sort_values("Earnings Date").iloc[0]
        next_date = next_row["Earnings Date"]
        next_eps = next_row["EPS Estimate"]
    else:
        next_date = None
        next_eps = None

    # Summary stats
    stats = {
        "next_date": next_date,
        "next_eps": next_eps,
        "avg_surprise": df["Surprise(%)"].mean(),
        "std_surprise": df["Surprise(%)"].std(),
        "beat_rate": (df["Surprise(%)"] > 0).mean() * 100,
    }

    return df, stats
