import yfinance as yf
import pandas as pd

def load_earnings(ticker):
    """
    Universal earnings loader using earnings_dates.
    Works on Python 3.14 and Streamlit Cloud.
    """

    print(">> DEBUG: earnings.py loaded from:", __file__)
    print(">> DEBUG: loading ticker:", ticker)

    t = yf.Ticker(ticker)

    # Try earnings_dates first (works in your REPL)
    try:
        df = t.earnings_dates
    except Exception as e:
        print(">> DEBUG ERROR earnings_dates:", e)
        return None, None

    if df is None or df.empty:
        print(">> DEBUG: earnings_dates returned EMPTY")
        return None, None

    # Normalise columns
    df = df.reset_index().rename(columns={"index": "Earnings Date"})

    # Detect estimate / reported columns (names vary!)
    est_col = next((c for c in df.columns if "estimate" in c.lower()), None)
    rep_col = next((c for c in df.columns if "reported" in c.lower()), None)

    if not est_col or not rep_col:
        print(">> DEBUG: Missing EPS columns")
        return None, None

    df = df.rename(columns={
        est_col: "EPS Estimate",
        rep_col: "Reported EPS"
    })

    df["Earnings Date"] = pd.to_datetime(df["Earnings Date"], errors="coerce")
    df["EPS Estimate"] = pd.to_numeric(df["EPS Estimate"], errors="coerce")
    df["Reported EPS"] = pd.to_numeric(df["Reported EPS"], errors="coerce")

    # Surprise
    df["Surprise(%)"] = (
        (df["Reported EPS"] - df["EPS Estimate"]) /
        df["EPS Estimate"]
    ) * 100

    # Next earnings
    now = pd.Timestamp.utcnow()
    future = df[df["Earnings Date"] > now]

    if not future.empty:
        nxt = future.sort_values("Earnings Date").iloc[0]
        next_date = nxt["Earnings Date"]
        next_eps = nxt["EPS Estimate"]
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
