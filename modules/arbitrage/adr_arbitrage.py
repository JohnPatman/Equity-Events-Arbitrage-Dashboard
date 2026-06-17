import time
import pandas as pd
import yfinance as yf


# ---------------- Robust price helper ---------------- #

def _last_close(ticker: str, attempts: int = 3):
    """
    Robustly fetch the most recent close for a ticker.

    Uses a 5-day window (so a single market holiday doesn't return empty),
    flattens any MultiIndex columns, retries on transient yfinance/Yahoo
    failures, and returns None instead of raising if nothing is available.
    """
    for i in range(attempts):
        try:
            df = yf.Ticker(ticker).history(period="5d", auto_adjust=False)
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df = df.copy()
                    df.columns = df.columns.get_level_values(0)
                closes = df["Close"].dropna()
                if not closes.empty:
                    return float(closes.iloc[-1])
        except Exception:
            pass
        time.sleep(0.6 * (i + 1))
    return None


def _require(ticker: str):
    price = _last_close(ticker)
    if price is None:
        raise ValueError(f"No price data available for {ticker} (Yahoo unavailable or rate-limited)")
    return price


# ---------------- FX Helper ---------------- #

def get_fx(from_ccy, to_ccy="USD"):
    """
    Fetch FX using Yahoo Finance.
    Example: get_fx("TWD", "USD") -> uses ticker TWDUSD=X
    """
    pair = f"{from_ccy}{to_ccy}=X"
    rate = _last_close(pair)
    if rate is None:
        raise ValueError(f"FX not available for pair {pair}")
    return rate


# ---------------- ADR Arbitrage Core ---------------- #

def compute_adr_arbitrage(adr_price, local_price, ratio, fx_local_to_usd):
    """
    adr_price: ADR price in USD
    local_price: local share price in local currency
    ratio: number of local shares per 1 ADR
    fx_local_to_usd: conversion rate local->USD
    """
    local_usd_value = (local_price * ratio) * fx_local_to_usd
    arb_pct = (adr_price / local_usd_value - 1) * 100

    if adr_price > local_usd_value:
        direction = "ADR expensive -> Sell ADR / Buy Local"
    elif adr_price < local_usd_value:
        direction = "ADR cheap -> Buy ADR / Sell Local"
    else:
        direction = "No arbitrage"

    return {
        "adr_price": adr_price,
        "local_price": local_price,
        "fx_local_to_usd": fx_local_to_usd,
        "ratio": ratio,
        "local_usd_equivalent": local_usd_value,
        "arb_pct": arb_pct,
        "recommendation": direction,
    }


# --------------- ADR Wrappers ---------------- #

# --- TSM ---
def tsm_arbitrage():
    adr_price = _require("TSM")
    local_price = _require("2330.TW")
    fx = get_fx("TWD", "USD")
    ratio = 5  # 1 ADR = 5 Taiwan shares
    return compute_adr_arbitrage(adr_price, local_price, ratio, fx)


# --- BABA ---
def baba_arbitrage():
    adr_price = _require("BABA")
    local_price = _require("9988.HK")
    fx = get_fx("HKD", "USD")
    ratio = 8  # 1 ADR = 8 HK shares
    return compute_adr_arbitrage(adr_price, local_price, ratio, fx)


# --- SONY ---
def sony_arbitrage():
    adr_price = _require("SONY")
    local_price = _require("6758.T")
    fx = get_fx("JPY", "USD")
    ratio = 1  # 1 ADR = 1 JP share
    return compute_adr_arbitrage(adr_price, local_price, ratio, fx)


# --- ASML ---
def asml_arbitrage():
    adr_price = _require("ASML")
    local_price = _require("ASML.AS")
    fx = get_fx("EUR", "USD")
    ratio = 1  # 1 ADR = 1 EU share
    return compute_adr_arbitrage(adr_price, local_price, ratio, fx)


# --- AZN (NYSE line is now a DIRECT ordinary-share listing, 1:1 with LSE) ---
def azn_arbitrage():
    # As of 2 Feb 2026 AstraZeneca harmonised its listing: the old 2-for-1 ADR
    # programme was withdrawn and ordinary shares now list directly on the NYSE,
    # 1:1 with the London ordinary line (which is why the US price ~doubled).
    # So this is a dual-primary parity check, ratio 1.0 — not the old 0.5 ADR ratio.
    adr_price = _require("AZN")

    # LSE quote is in GBp (pence) -> must convert to GBP by dividing by 100
    local_raw = _require("AZN.L")
    local_price = local_raw / 100.0  # convert GBp -> GBP

    fx = get_fx("GBP", "USD")
    ratio = 1.0  # 1 NYSE ordinary share = 1 LSE ordinary share
    return compute_adr_arbitrage(adr_price, local_price, ratio, fx)


# --------------- Test Mode ---------------- #

if __name__ == "__main__":
    funcs = {
        "TSM": tsm_arbitrage,
        "BABA": baba_arbitrage,
        "SONY": sony_arbitrage,
        "ASML": asml_arbitrage,
        "AZN": azn_arbitrage,
    }

    for name, fn in funcs.items():
        print(f"\n{name} ARBITRAGE:")
        try:
            print(fn())
        except Exception as e:
            print(f"{name} error:", e)
