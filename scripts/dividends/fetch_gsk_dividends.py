import requests
import pandas as pd
from bs4 import BeautifulSoup

URL = "https://www.gsk.com/en-gb/investors/dividend-and-share-price/dividend-calendar/"

print("📥 Fetching GSK dividend calendar...")

r = requests.get(URL, headers={"User-Agent":"Mozilla/5.0"})
soup = BeautifulSoup(r.text, "html.parser")

table = soup.find("table")
if not table:
    print("❌ Could not find table")
    exit()

df = pd.read_html(str(table))[0]

# Normalise columns
df.columns = [c.strip().replace(" ", "_") for c in df.columns]

# Identify future payments only
df["Payment_date"] = pd.to_datetime(df["Payment_date"], errors="ignore")
upcoming = df[df["Payment_date"] > pd.Timestamp.today()]

if upcoming.empty:
    print("ℹ No future GSK dividends")
    exit()

upcoming["Ticker"] = "GSK.L"
upcoming = upcoming.rename(columns={"Payment_date":"Pay_Date"})

# Save
upcoming.to_csv("Data/upcoming_gsk.csv", index=False)

print("✅ Saved → Data/upcoming_gsk.csv")
print(upcoming[["Ticker","Pay_Date","Dividend"]])
