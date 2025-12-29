import requests
import pandas as pd
from bs4 import BeautifulSoup
import re

URL = "https://www.londonmetric.com/investors/shareholder-information"


def extract_fy(text):
    """Returns FY labels like '2025/26'."""
    m = re.match(r"^\d{4}/\d{2}$", text.strip())
    return m.group(0) if m else None


def fetch_lmp_scrip():
    print(f"Fetching Scrip Dividends from: {URL}")

    headers = {
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36")
    }

    r = requests.get(URL, headers=headers)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    # Only look inside the correct container
    scrip_section = soup.find("div", id="scrip-dividends")
    if not scrip_section:
        print("❌ No scrip-dividends section found.")
        return None

    tables = scrip_section.find_all("table", {"role": "presentation"})
    print(f"Found {len(tables)} raw tables.")

    all_rows = []

    # Each table is separated by an <h3> before it
    for tbl in tables:
        # Find FY label just above the table
        fy_label = None
        h3 = tbl.find_previous("h3")
        while h3:
            fy = extract_fy(h3.text)
            if fy:
                fy_label = fy
                break
            h3 = h3.find_previous("h3")

        df = pd.read_html(str(tbl))[0]
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

        if fy_label:
            df["FY"] = fy_label

        all_rows.append(df)

    combined = pd.concat(all_rows, ignore_index=True)

    # Remove header rows with no data
    combined = combined[combined["Scrip Calculation Price"].notna()]

    # Clean values
    combined["Scrip Calculation Price"] = (
        combined["Scrip Calculation Price"]
        .astype(str)
        .str.replace("pence", "", regex=False)
        .str.replace("p", "", regex=False)
        .str.strip()
    ).astype(float)

    return combined


if __name__ == "__main__":
    df = fetch_lmp_scrip()

    if df is not None:
        print("\nCleaned Scrip Data:")
        print(df)
        df.to_csv("lmp_scrip_dividends.csv", index=False)
        print("\n✅ Saved cleaned data to lmp_scrip_dividends.csv")
