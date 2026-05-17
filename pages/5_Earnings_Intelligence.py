import streamlit as st
st.set_page_config(page_title="Earnings Intelligence", layout="wide")
from modules.theme import apply_bloomberg_theme
import pandas as pd
import altair as alt
from modules.earnings.earnings import load_earnings

apply_bloomberg_theme()

st.title("🔹 Earnings Intelligence – Surprise Analysis")

st.markdown("""
This dashboard analyses earnings surprise behaviour for US equities using locally stored S&P 100 earnings CSVs.

It:
- loads historical EPS estimates and reported results,
- calculates surprise percentages and volatility,
- displays beat-rate statistics,
- shows upcoming earnings date & consensus estimate (if available),
- visualises the last 6 quarters with clear bar charts.
""")

SP100 = {
    "AAPL": "Apple", "MSFT": "Microsoft", "AMZN": "Amazon", "NVDA": "NVIDIA",
    "GOOGL": "Alphabet (Class A)", "GOOG": "Alphabet (Class C)", "META": "Meta Platforms",
    "TSLA": "Tesla", "BRK-B": "Berkshire Hathaway (B)", "UNH": "UnitedHealth",
    "XOM": "Exxon Mobil", "JNJ": "Johnson & Johnson", "JPM": "JPMorgan Chase",
    "V": "Visa", "AVGO": "Broadcom", "LLY": "Eli Lilly", "PG": "Procter & Gamble",
    "CVX": "Chevron", "HD": "Home Depot", "MA": "Mastercard", "MRK": "Merck",
    "ABBV": "AbbVie", "PEP": "PepsiCo", "PFE": "Pfizer", "KO": "Coca-Cola",
    "COST": "Costco", "TMO": "Thermo Fisher", "WMT": "Walmart", "MCD": "McDonald's",
    "BAC": "Bank of America", "DIS": "Walt Disney", "CSCO": "Cisco", "ORCL": "Oracle",
    "ABT": "Abbott Labs", "DHR": "Danaher", "CRM": "Salesforce", "ACN": "Accenture",
    "CVS": "CVS Health", "LIN": "Linde", "QCOM": "Qualcomm", "TXN": "Texas Instruments",
    "NEE": "NextEra Energy", "UNP": "Union Pacific", "PM": "Philip Morris",
    "AMD": "Advanced Micro Devices", "BMY": "Bristol Myers Squibb", "MS": "Morgan Stanley",
    "RTX": "RTX Corp.", "UPS": "United Parcel Service", "AMT": "American Tower",
    "INTC": "Intel", "BLK": "BlackRock", "LOW": "Lowe's", "SCHW": "Charles Schwab",
    "CAT": "Caterpillar", "AMAT": "Applied Materials", "MDT": "Medtronic",
    "GS": "Goldman Sachs", "NOW": "ServiceNow", "BKNG": "Booking Holdings",
    "ADBE": "Adobe", "AXP": "American Express", "T": "AT&T", "DE": "Deere & Co.",
    "ISRG": "Intuitive Surgical", "VRTX": "Vertex Pharma", "C": "Citigroup",
    "SPGI": "S&P Global", "SYK": "Stryker", "MDLZ": "Mondelez", "ADI": "Analog Devices",
    "MU": "Micron Technology", "REGN": "Regeneron", "ELV": "Elevance Health",
    "LRCX": "Lam Research", "COP": "ConocoPhillips", "MMC": "Marsh & McLennan",
    "GILD": "Gilead Sciences", "NFLX": "Netflix", "LMT": "Lockheed Martin",
    "FDX": "FedEx", "KLAC": "KLA Corp.", "ZTS": "Zoetis", "HON": "Honeywell",
    "EQIX": "Equinix", "MAR": "Marriott", "APD": "Air Products & Chemicals",
    "WM": "Waste Management", "CTAS": "Cintas", "SO": "Southern Co.",
    "PANW": "Palo Alto Networks", "CSX": "CSX Corp.", "NSC": "Norfolk Southern",
    "ICE": "Intercontinental Exchange", "ADP": "Automatic Data Processing",
    "BDX": "Becton Dickinson", "PGR": "Progressive", "AON": "Aon",
    "AEP": "American Electric Power", "ETN": "Eaton"
}

sp100_labels = [f"{ticker} – {name}" for ticker, name in SP100.items()]
default_index = sp100_labels.index("AAPL – Apple") if "AAPL – Apple" in sp100_labels else 0

selection = st.selectbox("Select S&P 100 Company", sp100_labels, index=default_index)
ticker = selection.split(" – ")[0]

df_earn, stats_earn = load_earnings(ticker)

if df_earn is None or df_earn.empty:
    st.warning(f"No earnings data found for {ticker}. Make sure `Data/earnings/{ticker}.csv` exists.")
    st.stop()

df_earn["Earnings Date"] = pd.to_datetime(df_earn["Earnings Date"], errors="coerce")
hist = df_earn[df_earn["Reported EPS"].notna()].copy()

if hist.empty:
    st.warning(f"{ticker} has no reported earnings history.")
    st.stop()

c1, c2, c3 = st.columns(3)

next_dt = stats_earn.get("next_date")
next_dt_str = next_dt.strftime("%d %b %Y") if isinstance(next_dt, pd.Timestamp) and pd.notna(next_dt) else "N/A"
c1.metric("Next Earnings Date", next_dt_str)

next_eps = stats_earn.get("next_eps")
next_eps_str = f"{float(next_eps):.2f}" if next_eps is not None and pd.notna(next_eps) else "N/A"
c2.metric("Consensus EPS (Next)", next_eps_str)

beat_rate = stats_earn.get("beat_rate")
beat_rate_str = f"{float(beat_rate):.1f}%" if beat_rate is not None and pd.notna(beat_rate) else "N/A"
c3.metric("Beat Rate (%)", beat_rate_str)

st.subheader("Surprise Statistics")

avg_s = stats_earn.get("avg_surprise")
std_s = stats_earn.get("std_surprise")

st.write(f"- **Average surprise:** {float(avg_s):.2f}%" if avg_s is not None and pd.notna(avg_s) else "- **Average surprise:** N/A")
st.write(f"- **Surprise volatility (stdev):** {float(std_s):.2f} ppts" if std_s is not None and pd.notna(std_s) else "- **Surprise volatility (stdev):** N/A")

st.subheader("Recent Reported Quarters")

recent = hist.sort_values("Earnings Date", ascending=False).head(6)
recent = recent.sort_values("Earnings Date", ascending=True).copy()

recent_display = recent.copy()
recent_display["Earnings Date"] = recent_display["Earnings Date"].dt.strftime("%Y-%m-%d")
recent_display["EPS Estimate"] = recent_display["EPS Estimate"].round(2)
recent_display["Reported EPS"] = recent_display["Reported EPS"].round(2)
recent_display["Surprise(%)"] = recent_display["Surprise(%)"].round(2)

st.dataframe(recent_display, use_container_width=True)

csv_data = recent_display.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Download CSV",
    data=csv_data,
    file_name=f"{ticker}_earnings_last_6.csv",
    mime="text/csv",
)

st.subheader("Earnings Surprise – Last 6 Quarters")

chart = (
    alt.Chart(recent_display)
    .mark_bar()
    .encode(
        x=alt.X("Earnings Date:N", title="Earnings Date"),
        y=alt.Y("Surprise(%)", title="EPS Surprise (%)"),
        tooltip=[
            "Earnings Date",
            alt.Tooltip("EPS Estimate:Q", format=".2f"),
            alt.Tooltip("Reported EPS:Q", format=".2f"),
            alt.Tooltip("Surprise(%):Q", format=".2f"),
        ],
    )
)

st.altair_chart(chart, use_container_width=True)