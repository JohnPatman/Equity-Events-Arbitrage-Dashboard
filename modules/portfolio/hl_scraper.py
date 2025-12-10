# modules/portfolio/hl_scraper.py

import requests
import pandas as pd
from bs4 import BeautifulSoup


def _parse_weight_to_float(weight_str: str) -> float:
    """
    Convert strings like '68.20%' or ' 5.2 % ' into 0.6820 or 0.052.
    Returns None if it can't parse.
    """
    if weight_str is None:
        return None

    s = weight_str.strip()
    # Remove percent sign and commas
    s = s.replace("%", "").replace(",", "")
    if not s:
        return None

    try:
        value = float(s)
        return value / 100.0
    except ValueError:
        return None


def scrape_country_weights(url: str) -> pd.DataFrame:
    """
    Scrape an HL fund page and return a DataFrame with:
    - Country (str)
    - Weight_str (original string, e.g. '68.20%')
    - Weight (float, e.g. 0.6820)

    If nothing is found, returns an empty DataFrame.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Strategy:
    # - Look through all tables
    # - Find one where the first header contains 'Country'
    #   and the second contains something like 'Weight', '%', or 'Allocation'.
    target_table = None

    for table in soup.find_all("table"):
        header_row = table.find("tr")
        if not header_row:
            continue

        headers_cells = header_row.find_all(["th", "td"])
        if len(headers_cells) < 2:
            continue

        h0 = headers_cells[0].get_text(strip=True).lower()
        h1 = headers_cells[1].get_text(strip=True).lower()

        if "country" in h0 and (
            "weight" in h1
            or "%" in h1
            or "allocation" in h1
        ):
            target_table = table
            break

    if target_table is None:
        # Nothing found – return empty DataFrame
        return pd.DataFrame(columns=["Country", "Weight_str", "Weight"])

    countries = []
    weight_strs = []
    weights = []

    # Skip header row (index 0)
    for row in target_table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        country = cols[0].get_text(strip=True)
        w_str = cols[1].get_text(strip=True)

        w_float = _parse_weight_to_float(w_str)

        # Only store rows with a valid country + weight string
        if country and w_str:
            countries.append(country)
            weight_strs.append(w_str)
            weights.append(w_float)

    df = pd.DataFrame(
        {
            "Country": countries,
            "Weight_str": weight_strs,
            "Weight": weights,
        }
    )

    # Sort by Weight (desc) if we have numeric weights
    if not df.empty and df["Weight"].notna().any():
        df = df.sort_values("Weight", ascending=False).reset_index(drop=True)

    return df
