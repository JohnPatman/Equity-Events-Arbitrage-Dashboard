import requests
import pandas as pd

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"

# You do NOT need a key for basic access, but adding one removes limits (optional)
API_KEY = "09aebef66bcb5dc4f22f48cc63d82cd4"

def load_fred(series_code):
    """Fetch FRED series via the official API. Returns Date/Value DataFrame."""
    params = {
        "series_id": series_code,
        "api_key": API_KEY,
        "file_type": "json",
        "observation_start": "1970-01-01"
    }

    response = requests.get(FRED_URL, params=params)
    data = response.json()

    # Handle missing data gracefully
    if "observations" not in data:
        return pd.DataFrame(columns=["Date", "Value"])

    df = pd.DataFrame(data["observations"])
    df = df[["date", "value"]].rename(columns={"date": "Date", "value": "Value"})

    # Convert numeric values
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    return df.dropna()
