"""
UK dividend calendar, sourced live from yfinance with a static-CSV fallback.

Why this exists
---------------
The original page relied on per-company IR-site scrapers (regex on hardcoded
date strings, plus a Selenium/ChromeDriver scraper that cannot run on Streamlit
Community Cloud). Those produced static CSVs that went stale and stopped
yielding any future-dated rows. This module replaces that with a self-updating
source:

  * forward ex-date / pay-date come from yfinance `.calendar` when available;
  * the most recently declared dividend (amount + date) comes from the reliable
    `.get_dividends()` history;
  * if no genuine forward date is published yet, an *indicative* next ex-date is
    projected from the historical payment cadence and clearly flagged as such;
  * everything is wrapped so a Yahoo failure degrades to whatever static CSV
    exists rather than crashing.

No Streamlit imports here so the module stays importable/testable; callers wrap
the live fetch in st.cache_data.
"""

import os
import glob
from datetime import date, datetime

import pandas as pd
import yfinance as yf

DATA_DIR = "Data"

COLUMNS = [
    "Ticker", "Company", "Last Declared", "Last Ex-Date",
    "Next Ex-Date", "Next Pay Date", "Basis", "Source",
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _to_date(x):
    if x is None:
        return None
    if isinstance(x, (list, tuple)):
        x = x[0] if x else None
    try:
        ts = pd.to_datetime(x, errors="coerce")
        if pd.isna(ts):
            return None
        return ts.date()
    except Exception:
        return None


def _fmt(d):
    return d.strftime("%d %b %Y") if isinstance(d, date) else "TBA"


def _currency_for(tkr_obj):
    try:
        cur = tkr_obj.fast_info.get("currency")
        if cur:
            return cur
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# live fetch (single ticker)
# ---------------------------------------------------------------------------
def fetch_one_live(yf_ticker: str) -> dict:
    """
    Return a dict of dividend fields for one LSE ticker, or {} if unavailable.
    Never raises.
    """
    out = {
        "Last Declared": None, "Last Ex-Date": None,
        "Next Ex-Date": None, "Next Pay Date": None,
        "Basis": None, "Source": None,
    }
    try:
        t = yf.Ticker(yf_ticker)
        currency = _currency_for(t)

        # --- historical dividends (reliable) ---
        divs = t.get_dividends()
        last_amt = last_ex = None
        cadence_days = None
        if divs is not None and not divs.empty:
            divs = divs.sort_index()
            last_amt = float(divs.iloc[-1])
            last_ex = _to_date(divs.index[-1])
            if len(divs) >= 3:
                gaps = divs.index.to_series().diff().dropna().dt.days
                gaps = gaps[gaps > 20]  # drop special/duplicate same-period entries
                if not gaps.empty:
                    cadence_days = int(gaps.tail(6).median())

        if last_amt is not None:
            unit = currency if currency else ""
            out["Last Declared"] = f"{last_amt:.4f} {unit}".strip()
            out["Last Ex-Date"] = last_ex

        # --- forward dates from the calendar (when published) ---
        cal_ex = cal_pay = None
        try:
            cal = t.calendar
            if isinstance(cal, dict):
                cal_ex = _to_date(cal.get("Ex-Dividend Date"))
                cal_pay = _to_date(cal.get("Dividend Date"))
            elif isinstance(cal, pd.DataFrame) and not cal.empty:
                # older yfinance returned a DataFrame
                if "Ex-Dividend Date" in cal.index:
                    cal_ex = _to_date(cal.loc["Ex-Dividend Date"].iloc[0])
                if "Dividend Date" in cal.index:
                    cal_pay = _to_date(cal.loc["Dividend Date"].iloc[0])
        except Exception:
            pass

        today = date.today()
        if cal_ex and cal_ex >= today:
            out["Next Ex-Date"] = cal_ex
            out["Next Pay Date"] = cal_pay
            out["Basis"] = "Declared (Yahoo calendar)"
            out["Source"] = "live"
        elif last_ex and cadence_days:
            # project the next ex-date from cadence; advance until it's in the future
            projected = last_ex
            guard = 0
            while projected < today and guard < 12:
                projected = projected + pd.Timedelta(days=cadence_days)
                projected = projected.date() if hasattr(projected, "date") else projected
                guard += 1
            out["Next Ex-Date"] = projected
            out["Basis"] = f"Indicative (≈{cadence_days}d cadence — not yet declared)"
            out["Source"] = "live"
        elif last_amt is not None:
            out["Basis"] = "History only (no forward date)"
            out["Source"] = "live"

        return out if out["Source"] else {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# static fallback (the legacy upcoming_*.csv files)
# ---------------------------------------------------------------------------
def fetch_one_static(ticker: str, full_name: str) -> dict:
    file = os.path.join(DATA_DIR, f"upcoming_{ticker.lower()}.csv")
    if not os.path.exists(file):
        return {}
    try:
        df = pd.read_csv(file)
    except Exception:
        return {}
    if df.empty:
        return {}

    df.columns = [c.strip() for c in df.columns]
    rename_map = {"PayDate": "Pay Date", "Payment Date": "Pay Date",
                  "ExDiv": "Ex Date", "Ex-dividend date": "Ex Date"}
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    pay = pd.to_datetime(df.get("Pay Date"), errors="coerce", dayfirst=True)
    ex = pd.to_datetime(df.get("Ex Date"), errors="coerce", dayfirst=True)
    div = df.get("Dividend", pd.Series(["TBA"] * len(df)))

    out_rows = pd.DataFrame({"Pay": pay, "Ex": ex, "Div": div})
    today = pd.Timestamp(date.today())
    future = out_rows[out_rows["Pay"].notna() & (out_rows["Pay"] >= today)].sort_values("Pay")
    if future.empty:
        return {}
    r = future.iloc[0]
    return {
        "Last Declared": str(r["Div"]) if pd.notna(r["Div"]) else None,
        "Last Ex-Date": r["Ex"].date() if pd.notna(r["Ex"]) else None,
        "Next Ex-Date": r["Ex"].date() if pd.notna(r["Ex"]) else None,
        "Next Pay Date": r["Pay"].date() if pd.notna(r["Pay"]) else None,
        "Basis": "Stored CSV",
        "Source": "stored",
    }


# ---------------------------------------------------------------------------
# public: build the full view
# ---------------------------------------------------------------------------
def get_uk_dividend_view(companies: dict, yf_suffix: str = ".L") -> pd.DataFrame:
    """
    companies: {ticker: full_name}, e.g. {"HSBA": "HSBC Holdings", ...}
    Returns a normalised DataFrame (one row per company).
    """
    rows = []
    for ticker, full_name in companies.items():
        yf_ticker = f"{ticker}{yf_suffix}"
        rec = fetch_one_live(yf_ticker)
        if not rec:
            rec = fetch_one_static(ticker, full_name)
        if not rec:
            rec = {"Last Declared": None, "Last Ex-Date": None, "Next Ex-Date": None,
                   "Next Pay Date": None, "Basis": "No data", "Source": "none"}

        rows.append({
            "Ticker": ticker,
            "Company": full_name,
            "Last Declared": rec.get("Last Declared") or "TBA",
            "Last Ex-Date": _fmt(rec.get("Last Ex-Date")),
            "Next Ex-Date": _fmt(rec.get("Next Ex-Date")),
            "Next Pay Date": _fmt(rec.get("Next Pay Date")),
            "Basis": rec.get("Basis") or "—",
            "Source": rec.get("Source") or "none",
        })

    return pd.DataFrame(rows, columns=COLUMNS)


def raw_static_extract() -> pd.DataFrame:
    """Concatenate all legacy upcoming_*.csv files for the raw-extract expander."""
    files = glob.glob(os.path.join(DATA_DIR, "upcoming_*.csv"))
    frames = []
    for f in files:
        try:
            d = pd.read_csv(f)
            if not d.empty:
                frames.append(d.assign(Source=os.path.basename(f)))
        except Exception:
            continue
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
