import pandas as pd
import re

URL = "https://www.airtel.africa/dividend"

def clean_airtel_table(raw_table):
    """
    Convert Airtel's 'columns as dividends' table layout into 
    a row-per-dividend DataFrame.
    """
    labels = raw_table.iloc[:, 0].tolist()
    events = raw_table.columns[1:]
    out_rows = []
    
    for col in events:
        series = raw_table[col]
        event_data = {"Event": col}

        for label, value in zip(labels, series):
            event_data[str(label).strip()] = str(value).strip()

        out_rows.append(event_data)

    return pd.DataFrame(out_rows)

def extract_usd_gbp_fx(row):
    """
    Search across all cell values in the row for a GBP FX rate.
    Format: '1 USD = X GBP'
    """
    for val in row.values:
        match = re.search(r"1\s*USD\s*=\s*([\d\.]+)\s*GBP", str(val), re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None

def fetch_airtel_latest():
    """
    Fetches Airtel tables, converts to normal structure,
    and returns ONLY the most recent dividend (the first one in table 0).
    """
    t0, t1 = pd.read_html(URL)

    df0 = clean_airtel_table(t0)   # most recent dividends first

    # most recent event is always row 0
    latest = df0.iloc[0].copy()

    # extract FX
    latest_fx = extract_usd_gbp_fx(latest)
    latest["FX_USD_GBP"] = latest_fx

    return latest

# ---------------------- TEST BLOCK ----------------------
if __name__ == "__main__":
    latest = fetch_airtel_latest()
    print("\nMOST RECENT DIVIDEND EVENT:\n")
    print(latest)
