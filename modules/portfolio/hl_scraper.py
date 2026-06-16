# modules/portfolio/hl_scraper.py

import io
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}


def _parse_weight_to_float(weight_str) -> float:
    """Convert '68.20%' or ' 5.2 % ' into 0.6820 / 0.052. None if unparseable."""
    if weight_str is None:
        return None
    s = str(weight_str).strip().replace("%", "").replace(",", "")
    if not s:
        return None
    try:
        return float(s) / 100.0
    except ValueError:
        return None


def _looks_like_country_table(columns) -> bool:
    cols = [str(c).lower() for c in columns]
    if len(cols) < 2:
        return False
    head = cols[0]
    rest = " ".join(cols[1:])
    return ("country" in head or "region" in head or "geograph" in head) and (
        "weight" in rest or "%" in rest or "allocation" in rest or "exposure" in rest
    )


def _normalise_two_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.iloc[:, :2].copy()
    df.columns = ["Country", "Weight_str"]
    df["Country"] = df["Country"].astype(str).str.strip()
    df["Weight"] = df["Weight_str"].apply(_parse_weight_to_float)
    df = df[df["Country"].astype(bool) & df["Weight"].notna()]
    if not df.empty:
        df = df.sort_values("Weight", ascending=False).reset_index(drop=True)
    return df[["Country", "Weight_str", "Weight"]]


def scrape_country_weights(url: str, attempts: int = 2) -> pd.DataFrame:
    """
    Scrape an HL fund page and return Country / Weight_str / Weight.

    Resilience notes
    ----------------
    HL increasingly renders factsheet tables client-side (JavaScript), which a
    plain HTTP request cannot see. This function:
      * retries transient failures,
      * tries pandas.read_html first (catches most static table markups),
      * falls back to a tolerant BeautifulSoup header match,
      * returns an empty (correctly shaped) DataFrame instead of raising if the
        page yields no parseable table — so the page can show a clean message.

    If a fund consistently returns nothing, the table is almost certainly
    JS-rendered and needs a different source (HL fund API / a stored CSV).
    """
    empty = pd.DataFrame(columns=["Country", "Weight_str", "Weight"])

    html = None
    for i in range(attempts):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            html = resp.text
            break
        except requests.RequestException:
            time.sleep(0.8 * (i + 1))
    if html is None:
        return empty

    # --- Strategy 1: pandas.read_html (robust to many table layouts) ---
    try:
        for tbl in pd.read_html(io.StringIO(html)):
            if _looks_like_country_table(tbl.columns):
                out = _normalise_two_cols(tbl)
                if not out.empty:
                    return out
    except Exception:
        pass

    # --- Strategy 2: tolerant BeautifulSoup parse ---
    try:
        soup = BeautifulSoup(html, "html.parser")
        for table in soup.find_all("table"):
            header_row = table.find("tr")
            if not header_row:
                continue
            header_cells = [c.get_text(strip=True) for c in header_row.find_all(["th", "td"])]
            if not _looks_like_country_table(header_cells):
                continue

            countries, weight_strs, weights = [], [], []
            for row in table.find_all("tr")[1:]:
                cols = row.find_all(["td", "th"])
                if len(cols) < 2:
                    continue
                country = cols[0].get_text(strip=True)
                w_str = cols[1].get_text(strip=True)
                if country and w_str:
                    countries.append(country)
                    weight_strs.append(w_str)
                    weights.append(_parse_weight_to_float(w_str))

            df = pd.DataFrame({"Country": countries, "Weight_str": weight_strs, "Weight": weights})
            df = df[df["Weight"].notna()]
            if not df.empty:
                return df.sort_values("Weight", ascending=False).reset_index(drop=True)
    except Exception:
        pass

    return empty
