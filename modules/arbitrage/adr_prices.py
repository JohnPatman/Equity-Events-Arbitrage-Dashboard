import yfinance as yf

def get_price(ticker):
    """
    Fetches the latest market price for any ticker using yfinance.
    Returns a float or raises an error if data unavailable.
    """
    data = yf.Ticker(ticker).history(period="1d")
    if data.empty:
        raise ValueError(f"No price data for ticker: {ticker}")
    return float(data["Close"].iloc[-1])


# ========== TSM ==========

def get_tsm_prices():
    adr = get_price("TSM")
    local = get_price("2330.TW")
    ratio = 5
    return {"adr_price": adr, "local_price": local, "ratio": ratio}


# ========== BABA ==========

def get_baba_prices():
    adr = get_price("BABA")
    local = get_price("9988.HK")
    ratio = 8
    return {"adr_price": adr, "local_price": local, "ratio": ratio}


# ========== SONY ==========

def get_sony_prices():
    adr = get_price("SONY")
    local = get_price("6758.T")  # Tokyo listing
    ratio = 1                    # 1 ADR = 1 local share
    return {"adr_price": adr, "local_price": local, "ratio": ratio}


# ========== ASML ==========

def get_asml_prices():
    adr = get_price("ASML")
    local = get_price("ASML.AS")  # Amsterdam listing
    ratio = 1                     # 1 ADR = 1 local share
    return {"adr_price": adr, "local_price": local, "ratio": ratio}


# ========== AZN ==========

def get_azn_prices():
    adr = get_price("AZN")
    local = get_price("AZN.L")  # London listing (GBP)
    ratio = 0.5                 # 2 ADR = 1 local share → 1 ADR = 0.5 local
    return {"adr_price": adr, "local_price": local, "ratio": ratio}


# ========== Test Mode ==========

if __name__ == "__main__":
    tests = {
        "TSM": get_tsm_prices,
        "BABA": get_baba_prices,
        "SONY": get_sony_prices,
        "ASML": get_asml_prices,
        "AZN": get_azn_prices
    }

    for name, func in tests.items():
        print(f"\n{name} Prices:")
        try:
            print(func())
        except Exception as e:
            print(f"{name} error: {e}")
