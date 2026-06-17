"""
UK dividend calendar.

Source priority (per company):
  1. dividenddata.co.uk  — DECLARED dividend timetable (declaration date, ex-date,
     pay date, amount, type) scraped from clean static HTML. Each entry on that
     site is sourced from the company's own RNS dividend-declaration announcement,
     so these are real declared dates, not estimates. One resilient parser instead
     of five fragile per-IR-site scrapers (and no Selenium, so it runs on Cloud).
  2. yfinance — last declared amount + an INDICATIVE next ex-date projected from
     historical payment cadence (clearly flagged) when nothing is declared yet.
  3. stored upcoming_*.csv — last-resort fallback if the network is unavailable.

No Streamlit imports here so the module stays importable/testable; callers wrap
the live fetch in st.cache_data.
"""

import io
import os
import glob
import requests
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

DATA_DIR = "Data"

COLUMNS = [
    "Ticker", "Company", "Last Declared", "Last Ex-Date",
    "Next Ex-Date", "Next Pay Date", "Basis", "Source",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}

DD_EX_PAGE = "https://www.dividenddata.co.uk/exdividenddate.py?m=ftse100"
DD_PAY_PAGE = "https://www.dividenddata.co.uk/dividend-payment-dates.py?m=ftse100"

# Declared data is scraped LOCALLY by scripts/fetch_uk_dividends.py and committed
# here, because dividenddata.co.uk sits behind Cloudflare and blocks Streamlit
# Cloud's datacenter IP. The app reads this committed CSV (it never scrapes live).
DECLARED_CSV = os.path.join(DATA_DIR, "uk_dividends_declared.csv")


# ---------------------------------------------------------------------------
# date / formatting helpers
# ---------------------------------------------------------------------------
def _infer_year(daymon):
    """Parse dividenddata's 'DD-Mon' (no year) into a date, inferring the year.

    If the resulting date is more than ~45 days in the past, roll it to next year
    (dividenddata lists forward dates, so a far-past month means next year).
    """
    s = str(daymon).strip()
    if not s or s.lower() in ("nan", "tba", "-"):
        return None
    parsed = pd.to_datetime(s, format="%d-%b", errors="coerce")
    if pd.isna(parsed):
        parsed = pd.to_datetime(s, errors="coerce")
        if pd.isna(parsed):
            return None
        if parsed.year >= 2000:
            return parsed.date()
    try:
        d = date(date.today().year, parsed.month, parsed.day)
    except ValueError:
        return None
    if d < date.today() - timedelta(days=45):
        d = date(d.year + 1, d.month, d.day)
    return d


def _fmt(d):
    return d.strftime("%d %b %Y") if isinstance(d, date) else "TBA"


# ---------------------------------------------------------------------------
# dividenddata.co.uk scraper (PRIMARY — declared dates)
# ---------------------------------------------------------------------------
def _flatten_cols(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [" ".join(str(x) for x in tup).strip() for tup in df.columns]
    return df


def _find_col(df: pd.DataFrame, *keywords):
    """First column whose lowercased name contains ALL given keywords."""
    for c in df.columns:
        cl = str(c).lower()
        if all(k in cl for k in keywords):
            return c
    return None


def _read_tables(url: str):
    r = requests.get(url, headers=_HEADERS, timeout=15)
    r.raise_for_status()
    return [_flatten_cols(t) for t in pd.read_html(io.StringIO(r.text))]


def _row_ticker(row, ticker_col, name_col):
    """Get the row's ticker. Payment page has a dedicated Ticker column; the
    ex-dividend page puts it as the trailing token of the Name cell
    ('AstraZeneca AZN'). Normalised (upper, no trailing dot)."""
    if ticker_col is not None:
        raw = str(row[ticker_col])
    else:
        name = str(row[name_col]).strip()
        parts = name.split()
        raw = parts[-1] if len(parts) > 1 else name
    return raw.strip().upper().rstrip(".")


def _harvest(df: pd.DataFrame, companies: dict, out: dict, has_ex: bool):
    name_col = _find_col(df, "name")
    ticker_col = _find_col(df, "ticker")  # the payment page has a separate Ticker column
    amt_col = _find_col(df, "dividend") or _find_col(df, "div")
    type_col = _find_col(df, "type")
    pay_col = _find_col(df, "payment")
    ex_col = _find_col(df, "ex-div") or _find_col(df, "ex div")
    decl_col = _find_col(df, "declared")
    if pay_col is None or (name_col is None and ticker_col is None):
        return

    wanted = {t.upper().rstrip("."): t for t in companies}

    for _, row in df.iterrows():
        row_tkr = _row_ticker(row, ticker_col, name_col)
        ticker = wanted.get(row_tkr)
        if ticker is None:
            continue
        # don't let the pay-only page overwrite a richer ex-page record
        if not has_ex and ticker in out:
            continue

        amount = str(row[amt_col]).strip() if amt_col else ""
        dtype = str(row[type_col]).strip() if type_col else ""
        last_declared = f"{amount} ({dtype})" if dtype and dtype.lower() != "nan" else amount

        rec = out.get(ticker, {})
        rec["Last Declared"] = last_declared or rec.get("Last Declared")
        rec["Next Pay Date"] = _infer_year(row[pay_col]) or rec.get("Next Pay Date")
        if has_ex:
            rec["Next Ex-Date"] = _infer_year(row[ex_col]) if ex_col else None
            rec["Last Ex-Date"] = _infer_year(row[decl_col]) if decl_col else None  # declaration date
            rec["Basis"] = "Declared (RNS announcement)"
        else:
            rec.setdefault("Next Ex-Date", None)
            rec.setdefault("Last Ex-Date", None)
            rec.setdefault("Basis", "Declared — pay date (RNS announcement)")
        rec["Source"] = "declared"
        out[ticker] = rec


def fetch_dividenddata(companies: dict) -> dict:
    """Return {ticker: rec} of declared dividends. Never raises."""
    out = {}
    # ex-dividend page first (full timetable: declaration / ex / pay)
    try:
        for tbl in _read_tables(DD_EX_PAGE):
            if _find_col(tbl, "ex-div") or _find_col(tbl, "ex div"):
                _harvest(tbl, companies, out, has_ex=True)
    except Exception:
        pass
    # payment page (already-ex names awaiting payment: amount + pay date)
    try:
        for tbl in _read_tables(DD_PAY_PAGE):
            if _find_col(tbl, "payment"):
                _harvest(tbl, companies, out, has_ex=False)
    except Exception:
        pass
    return out


# ---------------------------------------------------------------------------
# yfinance fallback (INDICATIVE cadence projection)
# ---------------------------------------------------------------------------
def _currency_for(t):
    try:
        cur = t.fast_info.get("currency")
        if cur:
            return cur
    except Exception:
        pass
    return ""


def _to_date(x):
    if x is None:
        return None
    if isinstance(x, (list, tuple)):
        x = x[0] if x else None
    try:
        ts = pd.to_datetime(x, errors="coerce")
        return None if pd.isna(ts) else ts.date()
    except Exception:
        return None


def fetch_one_live(yf_ticker: str) -> dict:
    out = {"Last Declared": None, "Last Ex-Date": None, "Next Ex-Date": None,
           "Next Pay Date": None, "Basis": None, "Source": None}
    try:
        t = yf.Ticker(yf_ticker)
        currency = _currency_for(t)

        divs = t.get_dividends()
        last_amt = last_ex = None
        cadence_days = None
        if divs is not None and not divs.empty:
            divs = divs.sort_index()
            last_amt = float(divs.iloc[-1])
            last_ex = _to_date(divs.index[-1])
            if len(divs) >= 3:
                gaps = divs.index.to_series().diff().dropna().dt.days
                gaps = gaps[gaps > 20]
                if not gaps.empty:
                    cadence_days = int(gaps.tail(6).median())

        if last_amt is not None:
            out["Last Declared"] = f"{last_amt:.4f} {currency}".strip()
            out["Last Ex-Date"] = last_ex

        cal_ex = cal_pay = None
        try:
            cal = t.calendar
            if isinstance(cal, dict):
                cal_ex = _to_date(cal.get("Ex-Dividend Date"))
                cal_pay = _to_date(cal.get("Dividend Date"))
        except Exception:
            pass

        today = date.today()
        if cal_ex and cal_ex >= today:
            out["Next Ex-Date"] = cal_ex
            out["Next Pay Date"] = cal_pay
            out["Basis"] = "Declared (Yahoo calendar)"
            out["Source"] = "live"
        elif last_ex and cadence_days:
            projected = last_ex
            guard = 0
            while projected < today and guard < 12:
                projected = projected + timedelta(days=cadence_days)
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
# stored-CSV fallback
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

    rows = pd.DataFrame({"Pay": pay, "Ex": ex, "Div": div})
    today = pd.Timestamp(date.today())
    future = rows[rows["Pay"].notna() & (rows["Pay"] >= today)].sort_values("Pay")
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
# committed declared CSV (PRIMARY on Cloud — written locally by the fetch script)
# ---------------------------------------------------------------------------
def _parse_iso(x):
    s = str(x).strip()
    if not s or s.lower() in ("nan", "nat", "none", ""):
        return None
    ts = pd.to_datetime(s, errors="coerce")
    return None if pd.isna(ts) else ts.date()


def load_declared_csv():
    """Read Data/uk_dividends_declared.csv -> ({ticker: rec}, fetched_at_str)."""
    if not os.path.exists(DECLARED_CSV):
        return {}, None
    try:
        df = pd.read_csv(DECLARED_CSV)
    except Exception:
        return {}, None
    out, fetched = {}, None
    for _, r in df.iterrows():
        tkr = str(r.get("Ticker", "")).strip().upper()
        if not tkr:
            continue
        fa = r.get("FetchedAt")
        if isinstance(fa, str) and fa.strip():
            fetched = fa.strip()
        out[tkr] = {
            "Last Declared": (str(r.get("Last Declared")).strip()
                              if pd.notna(r.get("Last Declared")) else None),
            "Last Ex-Date": _parse_iso(r.get("Declared Date")),
            "Next Ex-Date": _parse_iso(r.get("Ex Date")),
            "Next Pay Date": _parse_iso(r.get("Pay Date")),
            "Basis": (str(r.get("Basis")).strip() if pd.notna(r.get("Basis"))
                      else "Declared (RNS announcement)"),
            "Source": (str(r.get("Source")).strip() if pd.notna(r.get("Source"))
                       else "declared"),
        }
    return out, fetched


def declared_asof():
    """The 'FetchedAt' stamp from the committed CSV, or None."""
    _, fetched = load_declared_csv()
    return fetched


# ---------------------------------------------------------------------------
# public: build the full view
# ---------------------------------------------------------------------------
def get_uk_dividend_view(companies: dict, yf_suffix: str = ".L") -> pd.DataFrame:
    declared, _ = load_declared_csv()              # 1) committed declared CSV

    rows = []
    for ticker, full_name in companies.items():
        rec = declared.get(ticker)
        if not rec:
            rec = fetch_one_live(f"{ticker}{yf_suffix}")  # 2) yfinance indicative
        if not rec:
            rec = fetch_one_static(ticker, full_name)     # 3) legacy stored CSV
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
