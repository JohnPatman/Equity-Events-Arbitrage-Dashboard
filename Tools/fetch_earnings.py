# tools/fetch_earnings.py
import yfinance as yf
import pandas as pd
import os

# S&P 100 list
TICKERS = [
    "AAPL","MSFT","AMZN","NVDA","GOOGL","GOOG","META","TSLA","BRK-B","UNH",
    "XOM","JNJ","JPM","V","AVGO","LLY","PG","CVX","HD","MA",
    "MRK","ABBV","PEP","PFE","KO","COST","TMO","WMT","MCD","BAC",
    "DIS","CSCO","ORCL","ABT","DHR","CRM","ACN","CVS","LIN","QCOM",
    "TXN","NEE","UNP","PM","AMD","BMY","MS","RTX","UPS","AMT",
    "INTC","BLK","LOW","SCHW","CAT","AMAT","MDT","GS","NOW","BKNG",
    "ADBE","AXP","T","DE","ISRG","VRTX","C","SPGI","SYK","MDLZ",
    "ADI","MU","REGN","ELV","LRCX","COP","MMC","GILD","NFLX","LMT",
    "FDX","KLAC","ZTS","HON","EQIX","MAR","APD","WM","CTAS","SO",
    "PANW","CSX","NSC","ICE","ADP","BDX","PGR","AON","AEP","ETN"
]

OUTPUT_DIR = "Data/earnings"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_and_save(ticker):
    print(f"\n>>> Fetching earnings_dates for {ticker}")

    try:
        df = yf.Ticker(ticker).earnings_dates
    except Exception as e:
        print(f"[ERROR] Failed for {ticker}: {e}")
        return

    if df is None or df.empty:
        print(f"[ERROR] No earnings for {ticker}")
        return

    df = df.reset_index().rename(columns={"index": "Earnings Date"})
    path = f"{OUTPUT_DIR}/{ticker}.csv"

    df.to_csv(path, index=False)
    print(f"[OK] Saved {path} ({len(df)} rows)")


if __name__ == "__main__":
    print("\n=== Fetching S&P100 earnings ===")
    for t in TICKERS:
        fetch_and_save(t)
    print("\n=== DONE ===")
