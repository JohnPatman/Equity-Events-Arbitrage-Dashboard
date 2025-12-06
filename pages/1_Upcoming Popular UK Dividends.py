import streamlit as st
import pandas as pd
import glob, os
from datetime import datetime

st.title("🔹 Upcoming Popular UK Dividends")
st.markdown("""This dashboard tracks upcoming UK dividend events for major blue-chip companies  
(HSBC, Unilever, AstraZeneca, GSK, Rio Tinto).

The tool automatically:
- reads the latest dividend announcements scraped from company IR websites,
- standardises ex-dates, pay dates and dividend amounts,
- highlights whether each company has an upcoming dividend or not,
- displays a clean forward calendar of expected payments.

This dashboard is ideal for monitoring dividend timetables, running income strategies,  
and staying ahead of corporate actions in the UK market.
""")

DATA_DIR = "Data"
files = glob.glob(f"{DATA_DIR}/upcoming_*.csv")

company_names = {
    "HSBA": "HSBC Holdings",
    "ULVR": "Unilever PLC",
    "AZN":  "AstraZeneca PLC",
    "GSK":  "GSK PLC",
    "RIO":  "Rio Tinto PLC",
}

status_rows = []
upcoming_rows = []

today = datetime.now().date()

for ticker, full_name in company_names.items():
    file = f"{DATA_DIR}/upcoming_{ticker.lower()}.csv"

    if not os.path.exists(file):
        status_rows.append([ticker, full_name, "⚠ No data collected yet"])
        continue

    df = pd.read_csv(file)
    df.columns = [c.strip() for c in df.columns]

    rename_map = {
        "PayDate": "Pay Date", "Payment Date": "Pay Date",
        "ExDiv": "Ex Date", "Ex-dividend date": "Ex Date"
    }
    df.rename(columns={k:v for k,v in rename_map.items() if k in df.columns}, inplace=True)

    df["Dividend"] = df.get("Dividend", "Dividend rate to be announced").fillna("Dividend rate to be announced")
    df["Pay Date"] = pd.to_datetime(df.get("Pay Date"), errors="coerce").dt.date
    df["Ex Date"]  = pd.to_datetime(df.get("Ex Date"),  errors="coerce").dt.date

    future = df[df["Pay Date"].notna() & (df["Pay Date"] >= today)].sort_values("Pay Date")

    if future.empty:
        status_rows.append([ticker, full_name, "No future dividend announced"])
        continue

    row = future.iloc[0]

    def f(x): return x.strftime("%d/%m/%Y") if pd.notna(x) else "TBA"

    pay_uk, ex_uk = f(row["Pay Date"]), f(row["Ex Date"])
    div = row["Dividend"]

    status_rows.append([ticker, full_name, f"Next: {pay_uk} | {div}"])
    upcoming_rows.append([ticker, full_name, div, ex_uk, pay_uk])


st.subheader("Company Dividend Status")
st.dataframe(pd.DataFrame(status_rows, columns=["Ticker","Company","Status"]),
             hide_index=True, use_container_width=True)

st.subheader("Upcoming Dividend Payments")

if upcoming_rows:
    st.dataframe(pd.DataFrame(upcoming_rows,
                columns=["Ticker","Company","Dividend","Ex Date","Pay Date"]),
                hide_index=True, use_container_width=True)
else:
    st.write("No future dividends detected.")

with st.expander("📥 View Full Raw Extract"):
    if files:
        dfs=[pd.read_csv(f).assign(Source=os.path.basename(f)) for f in files]
        st.dataframe(pd.concat(dfs, ignore_index=True), use_container_width=True, height=350)
    else:
        st.write("No raw scrape files found.")
