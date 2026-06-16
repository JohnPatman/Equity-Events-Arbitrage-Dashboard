import pandas as pd
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import re


# =====================================
# CONSTANTS
# =====================================
LMP_URL = "https://www.londonmetric.com/investors/shareholder-information"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36"
    )
}

# Latest dividend rate for LondonMetric (2025/26 First Quarter)
LATEST_DIVIDEND_PENCE = 3.05    # total dividend per share, in pence


# =====================================
# SCRAPER — GET SCRIP TABLES
# =====================================
def fetch_scrip_tables():
    print(f"Fetching Scrip Dividends from: {LMP_URL}")

    r = requests.get(LMP_URL, headers=HEADERS, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    tables = soup.find_all("table")
    print(f"Found {len(tables)} raw tables.")

    cleaned = []

    for tbl in tables:
        try:
            df = pd.read_html(str(tbl))[0]
        except Exception:
            continue

        cols = [c.lower() for c in df.columns]
        if not any("scrip" in c for c in cols):
            continue

        df.columns = [
            "Dividend" if "dividend" in c.lower() else
            "Election deadline" if "election" in c.lower() else
            "Scrip Calculation Price" if "calculation" in c.lower() else
            "Date New Ordinary Shares issued" if "issue" in c.lower() else
            c
            for c in df.columns
        ]

        cleaned.append(df)

    if not cleaned:
        print("❌ No scrip tables found.")
        return pd.DataFrame()

    df = pd.concat(cleaned, ignore_index=True)

    df["Scrip Calculation Price"] = (
        df["Scrip Calculation Price"]
        .astype(str)
        .str.replace("pence", "", regex=False)
        .str.replace("p", "", regex=False)
        .str.strip()
    )

    df["Scrip Calculation Price"] = pd.to_numeric(df["Scrip Calculation Price"], errors="coerce")
    df = df.dropna(subset=["Scrip Calculation Price"])

    df.to_csv("lmp_scrip_dividends.csv", index=False)
    print("✔ Saved cleaned scrip data → lmp_scrip_dividends.csv")

    return df


# =====================================
# PRICE FETCHER — FIX YAHOO'S BAD DATA
# =====================================
def _last_close(df: pd.DataFrame):
    """
    Last 'Close' as a float, robust to yfinance now returning MultiIndex
    columns (Price, Ticker) even for a single ticker.
    """
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    if "Close" not in df.columns:
        return None
    closes = df["Close"].dropna()
    if closes.empty:
        return None
    val = closes.iloc[-1]
    if isinstance(val, pd.Series):
        val = val.iloc[0]
    return float(val)


def get_lmp_price_pence(deadline_date):
    """
    Fetches LMP share price from Yahoo Finance.
    Yahoo often returns 100x too large (split-adjusted). This corrects it.
    Returns price in pence.
    """
    ticker = "LMP.L"

    start = deadline_date - pd.Timedelta(days=5)
    end = deadline_date + pd.Timedelta(days=1)

    print(f"\nFetching LMP price from {start.date()} to {end.date()}...")

    data = yf.download(
        ticker,
        start=start,
        end=end,
        progress=False,
        auto_adjust=False,
    )

    raw_price_gbp = _last_close(data)
    if raw_price_gbp is None:
        raise ValueError("No price data returned by Yahoo Finance.")

    # Fix Yahoo bug: LMP has NEVER been £180+; this is split-adjusted noise
    if raw_price_gbp > 20:
        print(f"⚠ Yahoo returned bad split-adjusted price: {raw_price_gbp} GBP")
        corrected_price_gbp = raw_price_gbp / 100
        print(f"✔ Corrected price: {corrected_price_gbp:.2f} GBP")
    else:
        corrected_price_gbp = raw_price_gbp

    price_p = corrected_price_gbp * 100  # convert to pence

    print(f"✔ Final LMP Price near deadline: {price_p:.2f}p ({corrected_price_gbp:.2f} GBP)")
    return price_p


# =====================================
# ARBITRAGE ENGINE
# =====================================
def calculate_arbitrage(df):
    latest = df.iloc[0]
    print("\nLatest Scrip Record:")
    print(latest)

    deadline = pd.to_datetime(latest["Election deadline"], dayfirst=True)
    share_price_p = get_lmp_price_pence(deadline)

    scrip_price_p = float(latest["Scrip Calculation Price"])
    div_p = LATEST_DIVIDEND_PENCE

    SHARES = 10_000

    print("\n=== ARBITRAGE CALCULATION ===")
    print(f"Cash Dividend Rate: {div_p}p")
    print(f"Shares Tested: {SHARES:,}")

    cash_value_p = SHARES * div_p
    scrip_shares = (div_p / scrip_price_p) * SHARES
    scrip_value_p = scrip_shares * share_price_p

    cash_gbp = cash_value_p / 100
    scrip_gbp = scrip_value_p / 100
    pnl_gbp = scrip_gbp - cash_gbp

    print(f"\nCash Value: £{cash_gbp:,.2f}")
    print(f"Scrip Shares Issued: {scrip_shares:.4f}")
    print(f"Scrip Value: £{scrip_gbp:,.2f}")
    print(f"\nArbitrage P&L: £{pnl_gbp:,.2f}")

    if pnl_gbp > 0:
        print("📈 Arbitrage Opportunity: SCRIP is richer")
    elif pnl_gbp < 0:
        print("📉 Arbitrage: CASH is richer")
    else:
        print("⚖ No arbitrage – equal value")


# =====================================
# MAIN
# =====================================
if __name__ == "__main__":
    print("\n=== LONDONMETRIC SCRIP ARBITRAGE MODULE ===")

    df = fetch_scrip_tables()
    if df.empty:
        print("❌ No data scraped. Exiting.")
        raise SystemExit

    calculate_arbitrage(df)

    print("\n=== DONE ===\n")
