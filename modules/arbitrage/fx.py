import requests

def get_market_fx_usd_gbp():
    """
    Returns (rate, date_string) for USD→GBP from the ECB (Frankfurter API).
    Frankfurter always provides one fixing per business day.
    """
    url = "https://api.frankfurter.app/latest"
    params = {"from": "USD", "to": "GBP"}

    r = requests.get(url, params=params, timeout=10)
    data = r.json()

    if "rates" not in data:
        raise ValueError(f"Unexpected FX response: {data}")

    rate = data["rates"]["GBP"]
    date = data["date"]

    return rate, date


# ========== DEBUG RUN ==========
if __name__ == "__main__":
    rate, date = get_market_fx_usd_gbp()
    print(f"Latest USD→GBP FX: {rate}")
    print(f"FX date: {date}")
