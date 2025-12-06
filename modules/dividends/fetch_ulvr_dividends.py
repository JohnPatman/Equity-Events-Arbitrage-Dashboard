import requests
import pandas as pd
from bs4 import BeautifulSoup

url = "https://www.unilever.com/investors/investor-centre/dividends/dividend-calculator-and-history/"

print("📥 Fetching Unilever (ULVR) dividend data...")

resp = requests.get(url, headers={"User-Agent":"Mozilla/5.0"})
soup = BeautifulSoup(resp.text, "html.parser")

rows = soup.select("table tbody tr")
data = []

for r in rows:
    cells = [c.get_text(strip=True) for c in r.select("td")]

    if "Q3 2025" in " ".join(cells) and "£" in cells[1]:   # only take GBP line
        period, div, ex_date, record, pay_date = cells[:5]

        data.append({
            "Ticker": "ULVR",
            "Company": "Unilever PLC",
            "Dividend": div,         # -> £0.3928
            "Ex Date": ex_date,      
            "Pay Date": pay_date     
        })

if not data:
    print("⚠ No future ULVR dividends found.")
    exit()

df = pd.DataFrame(data)
df.to_csv("Data/upcoming_ulvr.csv", index=False)

print("✅ Saved → Data/upcoming_ulvr.csv")
print(df)
