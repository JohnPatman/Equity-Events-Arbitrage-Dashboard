import yfinance as yf

# ---------------- FX Helper ---------------- #

def get_fx(from_ccy, to_ccy="USD"):
    """
    Fetch FX using Yahoo Finance.
    Example: get_fx("TWD", "USD") → uses ticker TWDUSD=X
    """
    pair = f"{from_ccy}{to_ccy}=X"
    ticker = yf.Ticker(pair)
    data = ticker.history(period="1d")

    if data.empty:
        raise ValueError(f"FX not available for pair {pair}")

    return float(data["Close"].iloc[-1])


# ---------------- ADR Arbitrage Core ---------------- #

def compute_adr_arbitrage(adr_price, local_price, ratio, fx_local_to_usd):
    """
    adr_price: ADR price in USD
    local_price: local share price in local currency
    ratio: number of local shares per 1 ADR
    fx_local_to_usd: conversion rate local→USD
    """
    local_usd_value = (local_price * ratio) * fx_local_to_usd
    arb_pct = (adr_price / local_usd_value - 1) * 100

    if adr_price > local_usd_value:
        direction = "ADR expensive → Sell ADR / Buy Local"
    elif adr_price < local_usd_value:
        direction = "ADR cheap → Buy ADR / Sell Local"
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
    adr = yf.Ticker("TSM")
    local = yf.Ticker("2330.TW")

    adr_price = adr.history(period="1d")["Close"].iloc[-1]
    local_price = local.history(period="1d")["Close"].iloc[-1]

    fx = get_fx("TWD", "USD")
    ratio = 5  # 1 ADR = 5 Taiwan shares

    return compute_adr_arbitrage(adr_price, local_price, ratio, fx)


# --- BABA ---
def baba_arbitrage():
    adr = yf.Ticker("BABA")
    local = yf.Ticker("9988.HK")

    adr_price = adr.history(period="1d")["Close"].iloc[-1]
    local_price = local.history(period="1d")["Close"].iloc[-1]

    fx = get_fx("HKD", "USD")
    ratio = 8  # 1 ADR = 8 HK shares

    return compute_adr_arbitrage(adr_price, local_price, ratio, fx)


# --- SONY ---
def sony_arbitrage():
    adr = yf.Ticker("SONY")
    local = yf.Ticker("6758.T")

    adr_price = adr.history(period="1d")["Close"].iloc[-1]
    local_price = local.history(period="1d")["Close"].iloc[-1]

    fx = get_fx("JPY", "USD")
    ratio = 1  # 1 ADR = 1 JP share

    return compute_adr_arbitrage(adr_price, local_price, ratio, fx)


# --- ASML ---
def asml_arbitrage():
    adr = yf.Ticker("ASML")
    local = yf.Ticker("ASML.AS")

    adr_price = adr.history(period="1d")["Close"].iloc[-1]
    local_price = local.history(period="1d")["Close"].iloc[-1]

    fx = get_fx("EUR", "USD")
    ratio = 1  # 1 ADR = 1 EU share

    return compute_adr_arbitrage(adr_price, local_price, ratio, fx)


# --- AZN (IMPORTANT: LSE price is in pence → convert to GBP) ---
def azn_arbitrage():
    adr = yf.Ticker("AZN")
    local = yf.Ticker("AZN.L")

    # ADR (USD)
    adr_price = adr.history(period="1d")["Close"].iloc[-1]

    # LSE quote is in GBp (pence) — must convert to GBP by dividing by 100
    local_raw = local.history(period="1d")["Close"].iloc[-1]
    local_price = local_raw / 100.0  # convert GBp → GBP  ✔ FIXED

    fx = get_fx("GBP", "USD")

    # Ratio: 2 ADR = 1 ordinary share → 1 ADR = 0.5 shares
    ratio = 0.5

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
