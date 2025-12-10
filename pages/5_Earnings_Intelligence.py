import streamlit as st
import pandas as pd
import altair as alt
from modules.earnings.earnings import load_earnings

st.title("🔹 Earnings Intelligence – Surprise Analysis")

st.markdown("""
This dashboard analyses earnings surprise behaviour for US equities using **static CSV data**.

It automatically:
- loads historical EPS estimates and reported results,
- calculates surprise percentages and volatility,
- displays beat rate statistics,
- shows next earnings and forward consensus (if available),
- visualises recent surprise history with clear bar charts.
""")

# -----------------------------
# TICKER INPUT
# -----------------------------
ticker = st.text_input("Ticker", value="AAPL").strip().upper()
if not ticker:
    st.stop()

# -----------------------------
# LOAD STATIC CSV DATA
# -----------------------------
df_earn, stats_earn = load_earnings(ticker)

if df_earn is None or df_earn.empty:
    st.warning(f"No earnings data found for {ticker}. Make sure Data/earnings/{ticker}.csv exists.")
    st.stop()

# Format dates
df_earn["Earnings Date"] = pd.to_datetime(df_earn["Earnings Date"], errors="coerce")

# Only completed quarters
hist = df_earn[df_earn["Reported EPS"].notna()].copy()
if hist.empty:
    st.warning(f"{ticker} has no reported earnings history.")
    st.stop()

# -----------------------------
# METRICS
# -----------------------------
c1, c2, c3 = st.columns(3)

next_dt = stats_earn.get("next_date")
next_dt_fmt = next_dt.strftime("%d %b %Y") if next_dt is not None else "N/A"
c1.metric("Next Earnings Date", next_dt_fmt)

next_eps = stats_earn.get("next_eps")
next_eps_fmt = f"{next_eps:.2f}" if next_eps is not None else "N/A"
c2.metric("Consensus EPS (Next)", next_eps_fmt)

beat_rate = stats_earn.get("beat_rate")
beat_rate_fmt = f"{beat_rate:.1f}%" if beat_rate is not None else "N/A"
c3.metric("Beat Rate (%)", beat_rate_fmt)

# -----------------------------
# SURPRISE STATISTICS
# -----------------------------
st.subheader("Surprise Statistics")

avg_s = stats_earn.get("avg_surprise")
std_s = stats_earn.get("std_surprise")

st.write(f"- **Average surprise:** {avg_s:.2f}%" if avg_s is not None else "- **Average surprise:** N/A")
st.write(f"- **Surprise volatility:** {std_s:.2f} ppts" if std_s is not None else "- **Surprise volatility:** N/A")

# -----------------------------
# TABLE — LAST 6 QUARTERS
# -----------------------------
st.subheader("Recent Reported Quarters")

recent = hist.sort_values("Earnings Date", ascending=False).head(6)
recent = recent.sort_values("Earnings Date")

recent_fmt = recent.copy()
recent_fmt["Earnings Date"] = recent_fmt["Earnings Date"].dt.strftime("%Y-%m-%d")
recent_fmt["EPS Estimate"] = recent_fmt["EPS Estimate"].round(2)
recent_fmt["Reported EPS"] = recent_fmt["Reported EPS"].round(2)
recent_fmt["Surprise(%)"] = recent_fmt["Surprise(%)"].round(2)

st.dataframe(recent_fmt, use_container_width=True)

# Download CSV
csv_data = recent_fmt.to_csv(index=False).encode("utf-8")
st.download_button(
    "📥 Download CSV",
    csv_data,
    file_name=f"{ticker}_earnings_last_6.csv",
    mime="text/csv",
)

# -----------------------------
# BAR CHART
# -----------------------------
st.subheader("Earnings Surprise – Last 6 Quarters")

chart = (
    alt.Chart(recent_fmt)
    .mark_bar()
    .encode(
        x=alt.X("Earnings Date:N", title="Earnings Date"),
        y=alt.Y("Surprise(%)", title="EPS Surprise (%)"),
        tooltip=[
            "Earnings Date",
            alt.Tooltip("EPS Estimate", format=".2f"),
            alt.Tooltip("Reported EPS", format=".2f"),
            alt.Tooltip("Surprise(%)", format=".2f"),
        ],
    )
)

st.altair_chart(chart, use_container_width=True)
