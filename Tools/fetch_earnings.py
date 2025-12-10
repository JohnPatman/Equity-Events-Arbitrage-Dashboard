import os
import pandas as pd

DATA_DIR = "Data/earnings"


def load_earnings_from_csv(ticker: str):
    """
    Loads static earnings CSV for a ticker.
    Ensures:
      - Correct datetime parsing
      - Clean numeric conversion
      - Sorted newest→oldest
      - Surprise column calculated if missing
    """

    ticker = ticker.upper()
    path = os.path.join(DATA_DIR, f"{ticker}.csv")

    if not os.path.exists(path):
        print(f"[ERROR] Earnings CSV not found: {path}")
        return None, None

    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"[ERROR] Failed to read CSV for {ticker}: {e}")
        return None, None

    # --- CLEANUP -------------------------------------------------------------
    # Fix column names
    df.columns = [c.strip() for c in df.columns]

    # Parse datetime
    df["Earnings Date"] = pd.to_datetime(df["Earnings Date"], errors="coerce")

    # Numeric fields
    for col in ["EPS Estimate", "Reported EPS", "Surprise(%)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # If Surprise is missing, compute it
    if "Surprise(%)" not in df.columns or df["Surprise(%)"].isna().all():
        df["Surprise(%)"] = (
            (df["Reported EPS"] - df["EPS Estimate"]) / df["EPS Estimate"]
        ) * 100

    # Sort newest→oldest
    df = df.sort_values("Earnings Date", ascending=False).reset_index(drop=True)

    # --- METRICS -------------------------------------------------------------
    # Next earnings: future date (if exists)
    now = pd.Timestamp.utcnow()
    upcoming = df[df["Earnings Date"] > now]

    next_date = upcoming["Earnings Date"].iloc[0] if not upcoming.empty else None
    next_eps  = upcoming["EPS Estimate"].iloc[0] if not upcoming.empty else None

    # Surprise stats
    reported = df[df["Reported EPS"].notna()]
    avg_surprise = reported["Surprise(%)"].mean()
    std_surprise = reported["Surprise(%)"].std()

    beat_rate = (reported["Surprise(%)"] > 0).mean() * 100

    stats = {
        "next_date": next_date,
        "next_eps":  next_eps,
        "avg_surprise": float(avg_surprise) if avg_surprise is not None else None,
        "std_surprise": float(std_surprise) if std_surprise is not None else None,
        "beat_rate": float(beat_rate)
    }

    print(f"[OK] Loaded {len(df)} earnings rows for {ticker}")
    return df, stats
