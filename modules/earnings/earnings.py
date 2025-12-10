import pandas as pd
import os

DATA_DIR = "Data/earnings"

def load_earnings(ticker):
    """
    Load earnings data from static CSV produced by fetch_earnings.py.
    Returns (df, stats) where stats always contains all required keys.
    """

    path = os.path.join(DATA_DIR, f"{ticker}.csv")

    if not os.path.exists(path):
        return None, {
            "next_date": None,
            "next_eps": None,
            "avg_surprise": None,
            "std_surprise": None,
            "beat_rate": None,
        }

    df = pd.read_csv(path)

    # Parse dates
    if "Earnings Date" in df.columns:
        df["Earnings Date"] = pd.to_datetime(df["Earnings Date"], errors="coerce")
    else:
        df["Earnings Date"] = pd.NaT

    # Numeric conversion
    for col in ["EPS Estimate", "Reported EPS", "Surprise(%)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Identify reported rows only (these count as "history")
    hist = df[df["Reported EPS"].notna()].copy()

    # Compute stats safely
    avg_surprise = hist["Surprise(%)"].mean() if not hist.empty else None
    std_surprise = hist["Surprise(%)"].std() if not hist.empty else None
    beat_rate = (hist["Surprise(%)"] > 0).mean() * 100 if not hist.empty else None

    # Detect future earnings (if any exist)
    now = pd.Timestamp.utcnow()

    future = df[(df["Earnings Date"].notna()) & (df["Earnings Date"] > now)]
    if not future.empty:
        nxt = future.sort_values("Earnings Date").iloc[0]
        next_date = nxt["Earnings Date"]
        next_eps = nxt["EPS Estimate"]
    else:
        next_date = None
        next_eps = None

    # ALWAYS return these keys — never missing
    stats = {
        "next_date": next_date,
        "next_eps": next_eps,
        "avg_surprise": float(avg_surprise) if avg_surprise is not None else None,
        "std_surprise": float(std_surprise) if std_surprise is not None else None,
        "beat_rate": float(beat_rate) if beat_rate is not None else None,
    }

    return df, stats
