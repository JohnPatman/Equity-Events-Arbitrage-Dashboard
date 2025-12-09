import yfinance as yf
import pandas as pd

def load_earnings(ticker):
    """
    Loads earnings history + next earnings estimate from Yahoo Finance.
    Works with the updated Yahoo structure (2024–2025).
    """
    t = yf.Ticker(ticker)

    # Fetch the earnings table
    try:
        df = t.get_earnings_dates()
    except Exception:
        df = None

    if df is None or df.empty:
        print(f"No earnings data found for {ticker}")
        return None, None

    # Reset index to make "Earnings Date" a column
    df = df.reset_index()
    df = df.rename(columns={
        "Earnings Date": "Earnings Date",
        "EPS Estimate": "EPS Estimate",
        "Reported EPS": "Reported EPS",
        "Surprise(%)": "Surprise(%)"
    })

    # Convert earnings date
    df["Earnings Date"] = pd.to_datetime(df["Earnings Date"], errors="coerce")

    # Calculate surprise % if missing
    if "Surprise(%)" not in df or df["Surprise(%)"].isna().all():
        df["Surprise(%)"] = (
            (df["Reported EPS"] - df["EPS Estimate"]) / df["EPS Estimate"] * 100
        )

    # Next earnings event
    try:
        next_row = df[df["Reported EPS"].isna()].iloc[0]
        next_date = next_row["Earnings Date"]
        next_eps = next_row["EPS Estimate"]
    except:
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
