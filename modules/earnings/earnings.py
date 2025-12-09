import yfinance as yf
import pandas as pd


def load_earnings(ticker):
    """
    Fully robust earnings loader for both localhost and Streamlit Cloud.
    - Uses .earnings_dates when available.
    - Falls back to quarterly earnings when needed.
    - Standardises date column naming.
    - Computes surprise %, beat rate, and forward EPS estimate.
    """

    t = yf.Ticker(ticker)

    # =====================================
    # 1) Try PRIMARY endpoint: earnings_dates
    # =====================================
    df = None
    try:
        df = t.earnings_dates
    except Exception:
        df = None

    # If primary endpoint fails or empty → fallback
    if df is None or df.empty:
        try:
            df = t.quarterly_earnings  # fallback
        except Exception:
            return None, None

        if df is None or df.empty:
            return None, None

        df = df.reset_index()

    else:
        df = df.reset_index()

    # =====================================
    # 2) Detect and normalise date column
    # =====================================
    possible_date_cols = ["Earnings Date", "Earnings_Date", "Date", "index", "earningsDate"]
    date_col = next((c for c in possible_date_cols if c in df.columns), None)

    if date_col is None:
        return None, None

    df = df.rename(columns={date_col: "Earnings Date"})

    df["Earnings Date"] = pd.to_datetime(df["Earnings Date"], errors="coerce")

    # =====================================
    # 3) Detect EPS estimate & reported EPS columns
    # =====================================
    est_col = next((c for c in df.columns if "estimate" in c.lower()), None)
    rep_col = next((c for c in df.columns if "reported" in c.lower()), None)

    if not est_col or not rep_col:
        return None, None

    df = df.rename(columns={
        est_col: "EPS Estimate",
        rep_col: "Reported EPS"
    })

    # Ensure numeric
    df["EPS Estimate"] = pd.to_numeric(df["EPS Estimate"], errors="coerce")
    df["Reported EPS"] = pd.to_numeric(df["Reported EPS"], errors="coerce")

    # =====================================
    # 4) Surprise %
    # =====================================
    df["Surprise(%)"] = (
        (df["Reported EPS"] - df["EPS Estimate"]) /
        df["EPS Estimate"]
    ) * 100

    # =====================================
    # 5) Detect next future earnings date
    # =====================================
    now = pd.Timestamp.utcnow()
    future_rows = df[df["Earnings Date"] > now]

    if not future_rows.empty:
        next_row = future_rows.sort_values("Earnings Date").iloc[0]
        next_date = next_row["Earnings Date"]
        next_eps  = next_row["EPS Estimate"]
    else:
        next_date = None
        next_eps = None

    # =====================================
    # 6) Stats summary
    # =====================================
    stats = {
        "next_date": next_date,
        "next_eps": next_eps,
        "avg_surprise": df["Surprise(%)"].mean(),
        "std_surprise": df["Surprise(%)"].std(),
        "beat_rate": (df["Surprise(%)"] > 0).mean() * 100,
    }

    return df, stats
