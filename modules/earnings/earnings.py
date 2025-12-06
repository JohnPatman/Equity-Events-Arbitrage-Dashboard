import yfinance as yf
import pandas as pd

def load_earnings(ticker):
    """
    Loads earnings history + next earnings estimate from Yahoo Finance.
    Automatically adapts to inconsistent Yahoo formats.
    Returns: (df, stats) or (None, None)
    """
    t = yf.Ticker(ticker)

    # -------- Attempt to load history -------- #
    try:
        hist = t.earnings_dates  # Newer endpoint
    except Exception:
        hist = None

    if hist is None or hist.empty:
        print(f"⚠ No earnings history available for {ticker}.")
        return None, None

    df = hist.reset_index()

    # -------- Automatically detect columns -------- #
    date_col = next((c for c in df.columns if "date" in c.lower()), None)
    est_col  = next((c for c in df.columns if "estimate" in c.lower()), None)
    rep_col  = next((c for c in df.columns if "reported" in c.lower()), None)

    if not date_col or not est_col or not rep_col:
        print("⚠ ERROR: Missing required columns.")
        print("Columns returned:", df.columns)
        return None, None

    # Standardise names
    df = df.rename(columns={
        date_col: "Earnings Date",
        est_col: "EPS Estimate",
        rep_col: "Reported EPS"
    })

    # Convert to datetime
    df["Earnings Date"] = pd.to_datetime(df["Earnings Date"], errors="coerce")

    # Surprise %
    df["Surprise(%)"] = (
        (df["Reported EPS"] - df["EPS Estimate"]) / df["EPS Estimate"] * 100
    )

    # -------- Get NEXT earnings date -------- #
    try:
        upcoming = t.get_earnings_dates().iloc[0]
        next_date = upcoming.name
        next_eps = upcoming.get("EPS Estimate", None)
    except Exception:
        next_date = None
        next_eps = None

    stats = {
        "next_date": next_date,
        "next_eps": next_eps,
        "avg_surprise": df["Surprise(%)"].mean(),
        "std_surprise": df["Surprise(%)"].std(),
        "beat_rate": (df["Surprise(%)"] > 0).mean() * 100,
    }

    return df, stats


# ---------------------- DEBUG RUN --------------------------
if __name__ == "__main__":
    ticker = "AAPL"
    print(f"📊 Debugging earnings module for {ticker}\n")

    t = yf.Ticker(ticker)

    print("=== Raw: t.get_earnings_dates() ===")
    try:
        print(t.get_earnings_dates().head())
    except Exception as e:
        print("Error:", e)

    print("\n=== Raw: t.earnings_dates ===")
    try:
        print(t.earnings_dates.head())
    except Exception as e:
        print("Error:", e)

    print("\n=== Running load_earnings() ===")
    df, stats = load_earnings(ticker)

    print("\n--- Parsed DataFrame ---")
    print(df)

    print("\n--- Stats ---")
    print(stats)
