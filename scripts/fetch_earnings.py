# scripts/fetch_earnings.py
#
# Refreshes the static Data/earnings/<TICKER>.csv files used by the
# Earnings Intelligence page. The page now self-heals via a live single-ticker
# refresh, but running this occasionally keeps the stored base current and fast.
#
# Hardened vs the original:
#   * uses the supported get_earnings_dates(limit=...) call
#   * retries + polite sleep to avoid Yahoo rate-limiting on 100 names
#   * normalises columns and never overwrites a good CSV with an empty result
import os
import time
import pandas as pd
import yfinance as yf

TICKERS = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "TSLA", "BRK-B", "UNH",
    "XOM", "JNJ", "JPM", "V", "AVGO", "LLY", "PG", "CVX", "HD", "MA",
    "MRK", "ABBV", "PEP", "PFE", "KO", "COST", "TMO", "WMT", "MCD", "BAC",
    "DIS", "CSCO", "ORCL", "ABT", "DHR", "CRM", "ACN", "CVS", "LIN", "QCOM",
    "TXN", "NEE", "UNP", "PM", "AMD", "BMY", "MS", "RTX", "UPS", "AMT",
    "INTC", "BLK", "LOW", "SCHW", "CAT", "AMAT", "MDT", "GS", "NOW", "BKNG",
    "ADBE", "AXP", "T", "DE", "ISRG", "VRTX", "C", "SPGI", "SYK", "MDLZ",
    "ADI", "MU", "REGN", "ELV", "LRCX", "COP", "MMC", "GILD", "NFLX", "LMT",
    "FDX", "KLAC", "ZTS", "HON", "EQIX", "MAR", "APD", "WM", "CTAS", "SO",
    "PANW", "CSX", "NSC", "ICE", "ADP", "BDX", "PGR", "AON", "AEP", "ETN",
]

OUTPUT_DIR = "Data/earnings"
os.makedirs(OUTPUT_DIR, exist_ok=True)

SCHEMA = ["Earnings Date", "EPS Estimate", "Reported EPS", "Surprise(%)"]


def fetch_one(ticker: str, limit: int = 24, attempts: int = 3) -> pd.DataFrame:
    for i in range(attempts):
        try:
            t = yf.Ticker(ticker)
            df = t.get_earnings_dates(limit=limit) if hasattr(t, "get_earnings_dates") else t.earnings_dates
            if df is not None and not df.empty:
                df = df.reset_index()
                df.columns = [str(c).strip() for c in df.columns]
                # first column is the date index
                df = df.rename(columns={df.columns[0]: "Earnings Date"})
                if "Surprise (%)" in df.columns:
                    df = df.rename(columns={"Surprise (%)": "Surprise(%)"})
                for col in SCHEMA:
                    if col not in df.columns:
                        df[col] = pd.NA
                return df[SCHEMA]
        except Exception as e:
            print(f"   attempt {i+1} failed for {ticker}: {e}")
        time.sleep(1.5 * (i + 1))
    return pd.DataFrame(columns=SCHEMA)


def fetch_and_save(ticker: str):
    print(f">>> {ticker}")
    df = fetch_one(ticker)
    if df.empty:
        print(f"   [SKIP] no data returned for {ticker} (existing CSV left untouched)")
        return
    path = f"{OUTPUT_DIR}/{ticker}.csv"
    df.to_csv(path, index=False)
    print(f"   [OK] saved {path} ({len(df)} rows)")


if __name__ == "__main__":
    print("\n=== Fetching S&P100 earnings ===")
    for t in TICKERS:
        fetch_and_save(t)
        time.sleep(0.8)  # be polite to Yahoo
    print("\n=== DONE ===")
