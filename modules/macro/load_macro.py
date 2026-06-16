import os
import requests
import pandas as pd

try:
    import streamlit as st
except Exception:  # allow running this module outside Streamlit (e.g. scripts)
    st = None

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


def _get_api_key():
    """
    Resolve the FRED API key from (in order):
      1. st.secrets["FRED_API_KEY"]  (Streamlit Cloud → app Settings → Secrets)
      2. environment variable FRED_API_KEY
      3. None  (FRED still serves limited data keyless for many series)

    NOTE: The previous hardcoded key was committed to a public repo and must be
    treated as compromised — rotate it at https://fredaccount.stlouisfed.org/apikeys
    and store the new one in Streamlit secrets, never in source.
    """
    if st is not None:
        try:
            if "FRED_API_KEY" in st.secrets:
                return st.secrets["FRED_API_KEY"]
        except Exception:
            pass
    return os.environ.get("FRED_API_KEY")


def load_fred(series_code: str) -> pd.DataFrame:
    """Fetch a FRED series via the official API. Returns a Date/Value DataFrame.

    Never raises on a network/API failure — returns an empty (but correctly
    shaped) DataFrame so the calling page can render a clean 'no data' state
    instead of crashing.
    """
    params = {
        "series_id": series_code,
        "file_type": "json",
        "observation_start": "1970-01-01",
    }

    api_key = _get_api_key()
    if api_key:
        params["api_key"] = api_key

    try:
        response = requests.get(FRED_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        if st is not None:
            st.warning(f"FRED request failed for {series_code}: {e}")
        return pd.DataFrame(columns=["Date", "Value"])
    except ValueError:
        # Non-JSON response (e.g. an HTML error page)
        return pd.DataFrame(columns=["Date", "Value"])

    # FRED returns {"error_code": ..., "error_message": ...} on a bad/missing key
    if "error_message" in data:
        if st is not None:
            st.warning(f"FRED error for {series_code}: {data.get('error_message')}")
        return pd.DataFrame(columns=["Date", "Value"])

    if "observations" not in data:
        return pd.DataFrame(columns=["Date", "Value"])

    df = pd.DataFrame(data["observations"])
    if df.empty or not {"date", "value"}.issubset(df.columns):
        return pd.DataFrame(columns=["Date", "Value"])

    df = df[["date", "value"]].rename(columns={"date": "Date", "value": "Value"})
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    return df.dropna()
