import requests
import pandas as pd
from bs4 import BeautifulSoup

url = "https://www.londonmetric.com/investors/shareholder-information"
html = requests.get(url).text
soup = BeautifulSoup(html, "html.parser")

tables = soup.find_all("table")

print(f"Found {len(tables)} tables")

for i, tbl in enumerate(tables):
    print("\n====================")
    print(f"TABLE {i}")
    print("====================")

    # Print first 300 chars so we can recognise the table
    print(str(tbl)[:500])
