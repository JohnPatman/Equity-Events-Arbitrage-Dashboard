import requests
import pandas as pd

BOE_SERIES = {
    "3M": "IUMAMNP3M",
    "2Y": "IUDMNPY",
    "5Y": "IUDMP5Y",
    "10Y": "IUDMNP10",
    "30Y": "IUDMNP30",
}


def fetch_boe_series(series_id):
    """Fetch a single BoE series and return a clean DataFrame."""
    url = f"https://api.bankofengland.co.uk/observations?series_id={series_id}&format=json"

    try:
        r = requests.get(url, timeout=10)
    except Exception:
        return pd.DataFrame()

    if r.status_code != 200:
        return pd.DataFrame()

    data = r.json()
    if "observations" not in data:
        return pd.DataFrame()

    rows = []
    for obs in data["observations"]:
        if "value" in obs and obs["value"] not in (None, ""):
            rows.append([pd.to_datetime(obs["date"]), float(obs["value"])])

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["Date", "Value"])
    df = df.sort_values("Date")
    return df


def load_uk_yields():
    """Return dict of DataFrames matching the US yield dict structure."""
    results = {}
    for term, code in BOE_SERIES.items():
        df = fetch_boe_series(code)
        results[term] = df
    return results


def latest_uk_value(df):
    """Return most recent observation from a series."""
    if df is None or df.empty:
        return None
    return float(df["Value"].iloc[-1])
