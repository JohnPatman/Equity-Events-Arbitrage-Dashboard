#!/usr/bin/env python3
"""
Fetch DECLARED UK dividend dates and write Data/uk_dividends_declared.csv.

WHY THIS RUNS LOCALLY (not in the app):
dividenddata.co.uk sits behind Cloudflare, which serves the page fine to a normal
browser / residential IP but blocks Streamlit Cloud's datacenter IP. So the scrape
can't run inside the deployed app. Instead you run this on your Mac, where it works,
and commit the resulting CSV. The app then just reads that CSV.

USAGE (from the repo root):
    python scripts/fetch_uk_dividends.py
    git add Data/uk_dividends_declared.csv && git commit -m "Refresh UK dividends" && git push

Re-run it whenever you want to refresh (dividends change a few times a quarter).
"""
import os
import sys
from datetime import datetime

import pandas as pd

# make the repo root importable when run as `python scripts/fetch_uk_dividends.py`
sys.path.insert(0, os.getcwd())
from modules.dividends.uk_dividends import fetch_dividenddata  # noqa: E402

COMPANIES = {
    "HSBA": "HSBC Holdings",
    "ULVR": "Unilever PLC",
    "AZN":  "AstraZeneca PLC",
    "GSK":  "GSK PLC",
    "RIO":  "Rio Tinto PLC",
}
OUT = os.path.join("Data", "uk_dividends_declared.csv")


def main():
    if not os.path.exists("Home.py"):
        print("✗ Run this from the repo root (where Home.py lives).")
        sys.exit(1)

    print("Fetching declared UK dividends from dividenddata.co.uk ...")
    recs = fetch_dividenddata(COMPANIES)
    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    rows = []
    for tkr, name in COMPANIES.items():
        r = recs.get(tkr)
        if not r:
            print(f"  – {tkr}: no declared dividend pending")
            continue
        rows.append({
            "Ticker": tkr,
            "Company": name,
            "Last Declared": r.get("Last Declared") or "",
            "Declared Date": r["Last Ex-Date"].isoformat() if r.get("Last Ex-Date") else "",
            "Ex Date": r["Next Ex-Date"].isoformat() if r.get("Next Ex-Date") else "",
            "Pay Date": r["Next Pay Date"].isoformat() if r.get("Next Pay Date") else "",
            "Basis": r.get("Basis") or "Declared (dividenddata.co.uk · RNS)",
            "FetchedAt": fetched_at,
        })
        print(f"  ✔ {tkr}: {r.get('Last Declared')} | ex {r.get('Next Ex-Date')} | pay {r.get('Next Pay Date')}")

    if not rows:
        print("\nNo declared dividends found. This usually means none of the five names "
              "has a pending declared dividend right now, OR the scrape was blocked.\n"
              "Existing CSV left untouched.")
        return

    os.makedirs("Data", exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\nWrote {len(rows)} row(s) -> {OUT}  (fetched {fetched_at})")
    print("Now commit it:  git add", OUT, "&& git commit -m 'Refresh UK dividends' && git push")


if __name__ == "__main__":
    main()
