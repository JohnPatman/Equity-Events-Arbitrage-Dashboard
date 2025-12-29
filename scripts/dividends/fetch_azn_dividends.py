import requests, re, pandas as pd
from datetime import datetime

URL = "https://www.astrazeneca.com/investor-relations/dividend-policy.html"
headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-GB,en;q=0.9"}

print("📥 Fetching AstraZeneca dividend policy page...\n")
html = requests.get(URL, headers=headers).text

# Find pay dates inside HTML — matches formats like "8 September 2025"
date_matches = re.findall(
    r"(\d{1,2} (January|February|March|April|May|June|July|August|September|October|November|December) 202\d)",
    html)

future_dates = []
for d,_ in date_matches:
    dt = datetime.strptime(d, "%d %B %Y")
    if dt > datetime.now():
        future_dates.append(dt)

if not future_dates:
    print("ℹ No upcoming AstraZeneca dividends announced yet.")
    exit()

# Extract dividend rate GBP
div_match = re.search(r"GBP[\s:]*([0-9.]+)", html)
dividend = div_match.group(1) if div_match else None

df = pd.DataFrame({
    "Ticker": "AZN.L",
    "Dividend": dividend,
    "Pay Date": future_dates
})

df.to_csv("Data/upcoming_azn.csv", index=False)
print("✅ Saved → Data/upcoming_azn.csv\n")
print(df)
