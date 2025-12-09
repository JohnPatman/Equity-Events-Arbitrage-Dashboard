import yfinance as yf
import pandas as pd

def load_earnings(ticker):
    """
    Stable earnings loader for both localhost and Streamlit Cloud.
    Uses get_earnings(), which ALWAYS returns data for US stocks.
    """

    print(">> DEBUG: earnings.py loaded from:", __file__)
    print(">> DEBUG: loading ticker:", ticker)

    t = yf.Ticker(ticker)

    # ---- Cloud-safe endpoint ----
    try:
        df = t.get_earnings()
    except Exception as e:
        print(">> DEBUG ERROR get_earnings:", e)
        return None, None

    if df is None or df.empty:
        print(">> DEBUG: get_earnings returned EMPTY")
        return None, None

    df = df.reset_index().rename(columns={"index": "Earnings Date"})

    # Ensure numeric
    df["Earnings Date"] = pd.to_datetime(df["Earnings Date"], errors="coerce")
    df["EPS Estimate"] = pd.to_numeric(df["EPS Estimate"], errors="coerce")
    df["Reported EPS"] = pd.to_numeric(df["Reported EPS"], errors="coerce")

    # Surprise %
    df["Surprise(%)"] = (
        (df["Reported EPS"] - df["EPS Estimate"]) /
        df["EPS Estimate"]
    ) * 100

    # Next earnings date
    now = pd.Timestamp.utcnow()
    future = df[df["Earnings Date"] > now]

    if not future.empty:
        nxt = future.sort_values("Earnings Date").iloc[0]
        next_date = nxt["Earnings Date"]
        next_eps  = nxt["EPS Estimate"]
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

    print(">> DEBUG: SUCCESS — returning", len(df), "rows")
    return df, stats
