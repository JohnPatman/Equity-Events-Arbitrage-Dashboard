#!/usr/bin/env python3
"""
Build Data/uk_dividends_declared.csv for the UK dividends page.

Run this on your Mac (where dividenddata.co.uk loads — it's behind Cloudflare,
which blocks Streamlit Cloud's datacenter IP). It writes a complete row for every
tracked company so the deployed app just reads the CSV and never has to hit
Yahoo for 20 names on every page load.

For each company it uses, in order:
  1. the declared dividend (declaration/ex/pay/amount) from dividenddata.co.uk, or
  2. a yfinance fallback: last declared amount + an indicative next ex-date from
     payment cadence (flagged as indicative).

USAGE (from the repo root):
    python scripts/fetch_uk_dividends.py
    git add Data/uk_dividends_declared.csv && git commit -m "Refresh UK dividends" && git push

Re-run whenever you want fresh data (a few times a quarter is plenty).
"""
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.getcwd())
from modules.dividends.uk_dividends import fetch_dividenddata, fetch_one_live  # noqa: E402

# 20 FTSE 100 blue chips (EPIC -> name). EPICs match dividenddata; yfinance uses EPIC + ".L".
COMPANIES = {
    "HSBA": "HSBC Holdings",
    "ULVR": "Unilever",
    "AZN":  "AstraZeneca",
    "GSK":  "GSK",
    "RIO":  "Rio Tinto",
    "SHEL": "Shell",
    "BP":   "BP",
    "GLEN": "Glencore",
    "BATS": "British American Tobacco",
    "DGE":  "Diageo",
    "LLOY": "Lloyds Banking Group",
    "BARC": "Barclays",
    "NWG":  "NatWest Group",
    "NG":   "National Grid",
    "LGEN": "Legal & General",
    "AAL":  "Anglo American",
    "REL":  "RELX",
    "IMB":  "Imperial Brands",
    "BA":   "BAE Systems",
    "AV":   "Aviva",
}
OUT = os.path.join("Data", "uk_dividends_declared.csv")


def _iso(d):
    return d.isoformat() if d else ""


def main():
    if not os.path.exists("Home.py"):
        print("✗ Run this from the repo root (where Home.py lives).")
        sys.exit(1)

    print("Fetching declared dividends from dividenddata.co.uk ...")
    declared = fetch_dividenddata(COMPANIES)
    print(f"  declared found for: {sorted(declared.keys()) or 'none'}")
    print("Filling the rest from yfinance (indicative) ...")

    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = []
    for tkr, name in COMPANIES.items():
        rec = declared.get(tkr)
        if rec:
            tag = "declared"
        else:
            rec = fetch_one_live(f"{tkr}.L")
            tag = "indicative"
        if not rec:
            print(f"  – {tkr}: no data from either source")
            continue
        rows.append({
            "Ticker": tkr,
            "Company": name,
            "Last Declared": rec.get("Last Declared") or "",
            "Declared Date": _iso(rec.get("Last Ex-Date")),
            "Ex Date": _iso(rec.get("Next Ex-Date")),
            "Pay Date": _iso(rec.get("Next Pay Date")),
            "Basis": rec.get("Basis") or "",
            "Source": rec.get("Source") or tag,
            "FetchedAt": fetched_at,
        })
        print(f"  ✔ {tkr:4s} [{tag}]: {rec.get('Last Declared')} | "
              f"ex {rec.get('Next Ex-Date')} | pay {rec.get('Next Pay Date')}")

    if not rows:
        print("\nNo data fetched — existing CSV left untouched.")
        return

    os.makedirs("Data", exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\nWrote {len(rows)} row(s) -> {OUT}  (fetched {fetched_at})")
    print("Commit it:  git add", OUT, "&& git commit -m 'Refresh UK dividends' && git push")


if __name__ == "__main__":
    main()
