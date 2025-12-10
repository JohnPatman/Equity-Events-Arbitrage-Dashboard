import os
import pandas as pd

DATA_DIR = "Data/earnings"


def load_earnings(ticker: str):
    """
    Loads static earnings CSV for a ticker and returns:
      - df: cleaned DataFrame
      - stats: dictionary with summary statistics
    """

    ticker = ticker.upper()
    path = os.path.join(DATA_DIR, f"{ticker}.csv")

    if not os.path.exists(path):
        print(f"[ERROR] CSV not found for {ticker}: {path}")
        return None, None

    # -------------------------------------------------------
    # LOAD CSV
    # -------------------------------------------------------
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"[ERROR] Could not read CSV for {ticker}: {e}")
        return None, None

    # -------------------------------------------------------
    # CLEAN HEADERS
    # -------------------------------------------------------
    df.columns = [c.strip() for c in df.columns]

    # -------------------------------------------------------
    # CLEAN DATETIME — FIX mixed timezone formats
    # -------------------------------------------------------
    df["Earnings Date"] = (
        pd.to_datetime(df["Earnings Date"], errors="coerce", utc=True)
        .dt.tz_convert(None)
    )

    df = df[df["Earnings Date"].notna()].copy()

    # -------------------------------------------------------
    # CLEAN NUMERIC FIELDS
    # -------------------------------------------------------
    numeric_cols = ["EPS Estimate", "Reported EPS", "Surprise(%)"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # -------------------------------------------------------
    # CALCULATE SURPRISE IF MISSING
    # -------------------------------------------------------
    if "Surprise(%)" not in df.columns or df["Surprise(%)"].isna().all():
        df["Surprise(%)"] = (
            (df["Reported EPS"] - df["EPS Estimate"]) /
            df["EPS Estimate"]
        ) * 100

    # -------------------------------------------------------
    # SORT newest → oldest
    # -------------------------------------------------------
    df = df.sort_values("Earnings Date", ascending=False).reset_index(drop=True)

    # -------------------------------------------------------
    # SUMMARY METRICS
    # -------------------------------------------------------
    # Make NOW timezone-naive to match df
    now = pd.Timestamp.utcnow().tz_convert(None)

    # Find next earnings (future dates)
    upcoming = df[df["Earnings Date"] > now]
    next_date = upcoming["Earnings Date"].iloc[0] if not upcoming.empty else None
    next_eps = upcoming["EPS Estimate"].iloc[0] if not upcoming.empty else None

    # Surprise stats
    reported = df[df["Reported EPS"].notna()]
    avg_surprise = reported["Surprise(%)"].mean()
    std_surprise = reported["Surprise(%)"].std()
    beat_rate = (reported["Surprise(%)"] > 0).mean() * 100

    stats = {
        "next_date": next_date,
        "next_eps": next_eps,
        "avg_surprise": float(avg_surprise) if avg_surprise is not None else None,
        "std_surprise": float(std_surprise) if std_surprise is not None else None,
        "beat_rate": float(beat_rate) if beat_rate is not None else None,
    }

    print(f"[OK] Loaded {len(df)} rows for {ticker}")
    return df, stats
