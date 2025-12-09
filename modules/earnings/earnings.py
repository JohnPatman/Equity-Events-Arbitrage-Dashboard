import yfinance as yf
import pandas as pd

def load_earnings(ticker):
    """
    UNIVERSAL earnings loader:
    - Tries get_earnings() (works on Streamlit Cloud)
    - If unavailable (local newer yfinance), falls back to earnings_dates
    - Normalises structure for both sources
    """

    t = yf.Ticker(ticker)
    df = None

    # 1) Try get_earnings() → works on Cloud
    try:
        df = t.get_earnings()
    except:
        df = None

    # 2) If local yfinance doesn't support get_earnings() → use earnings_dates
    if df is None or df.empty:
        try:
            df = t.earnings_dates
        except:
            df = None

    if df is None or df.empty:
        return None, None

    # Normalise structure
    df = df.reset_index().rename(columns={"index": "Earnings Date"})
    df["Earnings Date"] = pd.to_datetime(df["Earnings Date"], errors="coerce")

    # Detect EPS columns
    est_col = next((c for c in df.columns if "estimate" in c.lower()), None)
    rep_col = next((c for c in df.columns if "reported" in c.lower()), None)

    if not est_col or not rep_col:
        return None, None

    df = df.rename(columns={
        est_col: "EPS Estimate",
        rep_col: "Reported EPS"
    })

    # Numeric clean
    df["EPS Estimate"] = pd.to_numeric(df["EPS Estimate"], errors="coerce")
    df["Reported EPS"] = pd.to_numeric(df["Reported EPS"], errors="coerce")

    # Surprise %
    df["Surprise(%)"] = (
        (df["Reported EPS"] - df["EPS Estimate"]) /
        df["EPS Estimate"]
    ) * 100

    # Detect next future earnings
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

    return df, stats
