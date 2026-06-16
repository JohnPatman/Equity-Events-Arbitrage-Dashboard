import os
import pandas as pd
import yfinance as yf

DATA_DIR = "Data/earnings"

SCHEMA_COLS = ["Earnings Date", "EPS Estimate", "Reported EPS", "Surprise(%)"]


# ---------------------------------------------------------------------------
# Cleaning / normalisation
# ---------------------------------------------------------------------------
def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce any earnings frame to the canonical schema and dtypes."""
    if df is None or df.empty:
        return pd.DataFrame(columns=SCHEMA_COLS)

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # The live API names the surprise column slightly differently across versions
    rename = {"Surprise (%)": "Surprise(%)", "Surprise(%)": "Surprise(%)"}
    df.rename(columns={k: v for k, v in rename.items() if k in df.columns}, inplace=True)

    if "Earnings Date" not in df.columns:
        # If the date is the index (live API), surface it
        df = df.reset_index().rename(columns={df.index.name or "index": "Earnings Date"})
        df.columns = [str(c).strip() for c in df.columns]

    df["Earnings Date"] = pd.to_datetime(df["Earnings Date"], errors="coerce", utc=True)
    df["Earnings Date"] = df["Earnings Date"].dt.tz_localize(None)

    for col in ["EPS Estimate", "Reported EPS", "Surprise(%)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = pd.NA

    # Recompute surprise where missing but both EPS legs are present
    need = df["Surprise(%)"].isna() & df["Reported EPS"].notna() & df["EPS Estimate"].notna()
    safe = need & (df["EPS Estimate"] != 0)
    df.loc[safe, "Surprise(%)"] = (
        (df.loc[safe, "Reported EPS"] - df.loc[safe, "EPS Estimate"])
        / df.loc[safe, "EPS Estimate"].abs()
    ) * 100

    df = df.dropna(subset=["Earnings Date"])
    return df[SCHEMA_COLS].sort_values("Earnings Date", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
def load_earnings_csv(ticker: str) -> pd.DataFrame:
    """Load the locally stored static earnings CSV for a ticker."""
    ticker = ticker.upper()
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=SCHEMA_COLS)
    try:
        return _normalise(pd.read_csv(path))
    except Exception as e:
        print(f"[ERROR] Failed to read CSV for {ticker}: {e}")
        return pd.DataFrame(columns=SCHEMA_COLS)


def fetch_earnings_live(ticker: str, limit: int = 24) -> pd.DataFrame:
    """
    Fetch earnings dates live from yfinance for a SINGLE ticker.

    Returns an empty frame (never raises) if Yahoo is unavailable or
    rate-limited, so callers can fall back to static data cleanly.
    """
    ticker = ticker.upper()
    try:
        t = yf.Ticker(ticker)
        # get_earnings_dates is the supported call; .earnings_dates is the legacy property
        if hasattr(t, "get_earnings_dates"):
            df = t.get_earnings_dates(limit=limit)
        else:
            df = t.earnings_dates
        return _normalise(df)
    except Exception as e:
        print(f"[WARN] Live earnings fetch failed for {ticker}: {e}")
        return pd.DataFrame(columns=SCHEMA_COLS)


def merge_earnings(static_df: pd.DataFrame, live_df: pd.DataFrame) -> pd.DataFrame:
    """Combine static + live, preferring live rows where dates overlap (by day)."""
    static_df = _normalise(static_df)
    live_df = _normalise(live_df)
    if live_df.empty:
        return static_df
    if static_df.empty:
        return live_df

    combined = pd.concat([live_df, static_df], ignore_index=True)
    combined["_day"] = combined["Earnings Date"].dt.normalize()
    # live rows came first, so keep="first" prefers live on a date collision
    combined = combined.drop_duplicates(subset="_day", keep="first").drop(columns="_day")
    return combined.sort_values("Earnings Date", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
def compute_stats(df: pd.DataFrame) -> dict:
    df = _normalise(df)
    now = pd.Timestamp.utcnow().tz_localize(None)

    upcoming = df[df["Earnings Date"] > now].sort_values("Earnings Date", ascending=True)
    next_date = upcoming["Earnings Date"].iloc[0] if not upcoming.empty else None
    next_eps = upcoming["EPS Estimate"].iloc[0] if not upcoming.empty else None

    reported = df[df["Reported EPS"].notna()]
    avg_surprise = reported["Surprise(%)"].mean() if not reported.empty else None
    std_surprise = reported["Surprise(%)"].std() if not reported.empty else None
    beat_rate = (reported["Surprise(%)"] > 0).mean() * 100 if not reported.empty else None

    return {
        "next_date": next_date,
        "next_eps": float(next_eps) if next_eps is not None and pd.notna(next_eps) else None,
        "avg_surprise": float(avg_surprise) if avg_surprise is not None and pd.notna(avg_surprise) else None,
        "std_surprise": float(std_surprise) if std_surprise is not None and pd.notna(std_surprise) else None,
        "beat_rate": float(beat_rate) if beat_rate is not None and pd.notna(beat_rate) else None,
    }


def is_stale(stats: dict, df: pd.DataFrame, max_age_days: int = 120) -> bool:
    """Stale if there's no future earnings date OR the newest reported quarter is old."""
    if stats.get("next_date") is None:
        return True
    df = _normalise(df)
    reported = df[df["Reported EPS"].notna()]
    if reported.empty:
        return True
    newest = reported["Earnings Date"].max()
    age = (pd.Timestamp.utcnow().tz_localize(None) - newest).days
    return age > max_age_days


# ---------------------------------------------------------------------------
# Backward-compatible entry point (static only)
# ---------------------------------------------------------------------------
def load_earnings(ticker: str):
    """Original signature: returns (df, stats) from the static CSV only."""
    df = load_earnings_csv(ticker)
    if df.empty:
        return None, None
    return df, compute_stats(df)
