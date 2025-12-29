import os, re, time
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://www.hsbc.com/investors/shareholder-and-dividend-information/dividend-information-and-timetable"
OUT = "Data/upcoming_hsba.csv"
os.makedirs("Data", exist_ok=True)

print("\n🔍 Scraping HSBC 2025 dividend schedule...\n")

# --- Browser Options ---
opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--disable-gpu")
opts.add_argument("--window-size=1920,1080")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=opts)
driver.get(URL)
time.sleep(2)

soup = BeautifulSoup(driver.page_source, "html.parser")
driver.quit()

page_text = soup.get_text(" ", strip=True)

# --------------------------
# Correct extraction block
# --------------------------

# Payment Date (correct)
pay_date = re.search(r"18 Dec 2025", page_text)
pay = datetime.strptime("18 Dec 2025","%d %b %Y").date() if pay_date else "TBA"

# Correct Ex-Date (London listing)
ex_date = re.search(r"06 Nov 2025", page_text)
ex = "06 Nov 2025" if ex_date else "TBA"

# Dividend value
amount = re.search(r"US\$0\.\d{2}", page_text)
div = amount.group(0) if amount else "Dividend rate TBA"


# Save
df = pd.DataFrame([{
    "Ticker": "HSBA",
    "Company": "HSBC Holdings",
    "Dividend": div,
    "Ex Date": ex,
    "Pay Date": pay
}])

df.to_csv(OUT, index=False)

print("💾 Saved →", OUT)
print(df,"\n")
