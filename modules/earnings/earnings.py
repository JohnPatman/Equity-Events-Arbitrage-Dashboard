import yfinance as yf
import pandas as pd

def load_earnings(ticker):
    """
    Reliable earnings loader for localhost + Streamlit Cloud.
    Uses get_earnings_dates(), which returns a full table
    with EPS Estimate, Reported EPS, Surprise(%), and date index.
    """

    t = yf.Ticker(ticker)

    # 1) Use the reliable endpoint
    try:
        df = t.get_earnings_dates()
    except Exception:
        return None, None

    # Abort if empty
    if df is None or df.empty:
        return None, None

    # Reset index → make date into a column
    df = df.reset_index().rename(columns={"index": "Earnings Date"})

    # Convert dates
    df["Earnings Date"] = pd.to_datetime(df["Earnings Date"], errors="coerce")

    # Ensure required columns
    required = ["EPS Estimate", "Reported EPS"]
    if not all(col in df.columns for col in required):
        return None, None

    # Surprise %
    df["Surprise(%)"] = (
        (df["Reported EPS"] - df["EPS Estimate"]) /
        df["EPS Estimate"]
    ) * 100

    # 2) Detect NEXT earnings date (future row)
    now = pd.Timestamp.utcnow()
    future = df[df["Earnings Date"] > now]

    if not future.empty:
        next_row = future.sort_values("Earnings Date").iloc[0]
        next_date = next_row["Earnings Date"]
        next_eps  = next_row["EPS Estimate"]
    else:
        next_date = None
        next_eps  = None

    # 3) Stats summary
    stats = {
        "next_date": next_date,
        "next_eps": next_eps,
        "avg_surprise": df["Surprise(%)"].mean(),
        "std_surprise": df["Surprise(%)"].std(),
        "beat_rate": (df["Surprise(%)"] > 0).mean() * 100,
    }

    return df, stats
