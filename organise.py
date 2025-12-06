import os
import shutil

folders = {
    "pages": [
        "1_Upcoming Popular UK Dividends.py",
        "2_Dividend_Growth Model.py",
        "3_Currency_Arbitrage.py",
        "4_ADR_Arbitrage.py",
        "5_Earnings_Intelligence.py",
        "6_Scrip_Arbitrage.py",
        "7_Global_Equity_Valuation.py"
    ],
    "modules/arbitrage": [
        "airtel.py", "fx.py", "adr_arbitrage.py", "lmp_scrip_arbitrage.py"
    ],
    "modules/dividends": [
        "fetch_hsbc_dividends.py","fetch_ulvr_dividends.py","fetch_rio_dividends.py",
        "fetch_gsk_dividends.py","fetch_azn_dividends.py","fetch_all_dividends.py"
    ],
    "modules/earnings": ["earnings.py"],
    "modules/valuation": ["global_valuation.py", "msci_fundamentals.csv", "msci_performance.csv"],
    "Data": [
        "history_ulvr.csv","history_ulvr_2010_2025.csv","lmp_scrip_dividends.csv",
        "upcoming_hsba.csv","upcoming_rio.csv","upcoming_gsk.csv","upcoming_ulvr.csv","upcoming_azn.csv"
    ],
}

for folder in folders:
    os.makedirs(folder, exist_ok=True)
    for f in folders[folder]:
        if os.path.exists(f):
            shutil.move(f, os.path.join(folder, f))
            print(f"Moved {f} -> {folder}")

print("Done.")
