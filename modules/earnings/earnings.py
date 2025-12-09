import yfinance as yf
import pandas as pd


def load_earnings(ticker):
    """
    FINAL STABLE VERSION — works on Streamlit Cloud.
    Uses ONLY quarterly_earnings, which Cloud allows.
    """

    t = yf.Ticker(ticker)

    # 1) Load quarterly earnings (Cloud-safe endpoint)
    try:
        df = t.quarterly_earnings
    except Exception:
        return None, None

    if df is None or df.empty:
        return None, None

    # 2) Format DataFrame
    df = df.reset_index().rename(columns={"index": "Earnings Date"})

    # Make sure date column is datetime
    df["Earnings Date"] = pd.to_datetime(df["Earnings Date"], errors="coerce")

    # 3) Ensure required EPS columns exist
    if "EPS Estimate" not in df.columns or "Reported EPS" not in df.columns:
        return None, None

    # Convert to numeric
    df["EPS Estimate"] = pd.to_numeric(df["EPS Estimate"], errors="coerce")
    df["Reported EPS"] = pd.to_numeric(df["Reported EPS"], errors="coerce")

    # 4) Surprise %
    df["Surprise(%)"] = (
        (df["Reported EPS"] - df["EPS Estimate"]) / df["EPS Estimate"]
    ) * 100

    # 5) Next earnings date = MAX future date
    now = pd.Timestamp.utcnow()
    future = df[df["Earnings Date"] > now]

    if not future.empty:
        next_row = future.sort_values("Earnings Date").iloc[0]
        next_date = next_row["Earnings Date"]
        next_eps = next_row["EPS Estimate"]
    else:
        next_date = None
        next_eps = None

    # 6) Summary stats
    stats = {
        "next_date": next_date,
        "next_eps": next_eps,
        "avg_surprise": df["Surprise(%)"].mean(),
        "std_surprise": df["Surprise(%)"].std(),
        "beat_rate": (df["Surprise(%)"] > 0).mean() * 100,
    }

    return df, stats
