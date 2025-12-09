import streamlit as st
import pandas as pd
import altair as alt
from modules.earnings.earnings import load_earnings

st.title("🔹 Earnings Intelligence – Surprise Analysis")
st.markdown("""
This dashboard analyses earnings surprise behaviour for US equities.

It automatically:
- loads historical EPS estimates and reported results,
- calculates surprise percentages and volatility,
- displays beat rate statistics,
- shows the upcoming earnings date and forward consensus,
- visualises recent surprise history with clear bar charts.
""")

ticker = st.text_input("Ticker", value="AAPL").strip().upper()

if not ticker:
    st.stop()

# Load data
df_earn, stats_earn = load_earnings(ticker)

if df_earn is None or df_earn.empty:
    st.warning(f"No earnings data available for {ticker}.")
    st.stop()

df_earn["Earnings Date"] = pd.to_datetime(df_earn["Earnings Date"], errors="coerce")

hist = df_earn[df_earn["Reported EPS"].notna()].copy()
if hist.empty:
    st.warning(f"{ticker} has no completed earnings history.")
    st.stop()

# ======================
# METRICS
# ======================
c1, c2, c3 = st.columns(3)

next_dt = stats_earn.get("next_date")
next_dt_fmt = next_dt.strftime("%d %b %Y") if pd.notna(next_dt) else "N/A"
c1.metric("Next Earnings Date", next_dt_fmt)

next_eps = stats_earn.get("next_eps")
next_eps_fmt = f"{next_eps:.2f}" if next_eps is not None else "N/A"
c2.metric("Consensus EPS (Next)", next_eps_fmt)

beat_rate = stats_earn.get("beat_rate")
beat_rate_fmt = f"{beat_rate:.1f}%" if beat_rate is not None else "N/A"
c3.metric("Beat Rate (%)", beat_rate_fmt)

# ======================
# SURPRISE STATS
# ======================
st.subheader("Surprise Statistics")
st.write(f"- Average surprise: **{stats_earn['avg_surprise']:.2f}%**")
st.write(f"- Surprise volatility (stdev): **{stats_earn['std_surprise']:.2f} ppts**")

# ======================
# TABLE
# ======================
st.subheader("Recent Reported Quarters")

recent = hist.sort_values("Earnings Date").tail(6).copy()

recent["Earnings Date"] = recent["Earnings Date"].dt.strftime("%Y-%m-%d")
recent["EPS Estimate"] = recent["EPS Estimate"].round(2)
recent["Reported EPS"] = recent["Reported EPS"].round(2)
recent["Surprise(%)"] = recent["Surprise(%)"].round(2)

st.dataframe(recent, use_container_width=True)

# ======================
# CSV DOWNLOAD
# ======================
csv_data = recent.to_csv(index=False).encode()
st.download_button(
    "📥 Download CSV",
    csv_data,
    file_name=f"{ticker}_earnings.csv",
    mime="text/csv",
)

# ======================
# CHART
# ======================
chart = (
    alt.Chart(recent)
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

st.subheader("Earnings Surprise – Last 6 Quarters")
st.altair_chart(chart, use_container_width=True)