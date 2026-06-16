import requests

# Frankfurter has two hosts; .dev is the current canonical one, .app still
# resolves but is occasionally down. We try .dev first, then fall back.
_FRANKFURTER_HOSTS = [
    "https://api.frankfurter.dev/v1/latest",
    "https://api.frankfurter.app/latest",
]


def get_market_fx_usd_gbp():
    """
    Returns (rate, date_string) for USD→GBP from the ECB (Frankfurter API).
    Frankfurter provides one fixing per business day.

    Raises ValueError only if *all* endpoints fail, so the caller can decide
    how to surface the problem (e.g. fall back to a manual FX override).
    """
    params = {"from": "USD", "to": "GBP"}
    last_err = None

    for url in _FRANKFURTER_HOSTS:
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()

            rates = data.get("rates", {})
            if "GBP" not in rates:
                last_err = ValueError(f"Unexpected FX response from {url}: {data}")
                continue

            return rates["GBP"], data.get("date", "unknown")
        except (requests.RequestException, ValueError) as e:
            last_err = e
            continue

    raise ValueError(f"Could not retrieve USD→GBP FX from any source: {last_err}")


# ========== DEBUG RUN ==========
if __name__ == "__main__":
    rate, date = get_market_fx_usd_gbp()
    print(f"Latest USD→GBP FX: {rate}")
    print(f"FX date: {date}")
