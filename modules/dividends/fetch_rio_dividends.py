import pandas as pd
import requests

URL = "https://www.riotinto.com/en/invest/shareholder-information/dividends/dividend-history-and-calculator"
OUTPUT = "Data/upcoming_rio.csv"

print("\n📥 Fetching Rio Tinto dividend history page...")

# Step 1 — download page
html = requests.get(URL, headers={"User-Agent":"Mozilla/5.0"}).text

# Step 2 — extract table
dfs = pd.read_html(html)
df = dfs[0]   # first table is the dividend table

# Step 3 — clean & rename columns
df.columns = ["Year","Type","USD","GBP","Ex Date","Pay Date"]

# Step 4 — convert date columns
df["Pay Date"] = pd.to_datetime(df["Pay Date"], dayfirst=True, errors="coerce")
df["Ex Date"]  = pd.to_datetime(df["Ex Date"],  dayfirst=True, errors="coerce")

# Step 5 — keep only future dividends
future = df[df["Pay Date"] > pd.Timestamp.today()]

if future.empty:
    print("ℹ No future Rio dividends found.")
    exit()

next_div = future.iloc[0]

out = pd.DataFrame([{
    "Ticker":"RIO",
    "Company":"Rio Tinto PLC",
    "Dividend":f"£{float(next_div['GBP']):.4f}",
    "Ex Date": next_div["Ex Date"].strftime("%d/%m/%Y"),
    "Pay Date":next_div["Pay Date"].strftime("%d/%m/%Y"),
}])

out.to_csv(OUTPUT,index=False)

print(f"\n📁 Saved → {OUTPUT}\n")
print(out)
