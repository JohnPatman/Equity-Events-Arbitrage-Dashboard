import streamlit as st
import pandas as pd
import altair as alt
from modules.earnings.earnings import load_earnings

st.title("🔹 Earnings Intelligence – Surprise Analysis")
st.markdown("""
This dashboard analyses earnings surprise behaviour for US equities.
""")

st.markdown("""
<span style="font-size: 1.25rem; font-weight: 700;">
Enter US Earnings Ticker (e.g. AAPL, MSFT, NVDA):
</span>
""", unsafe_allow_html=True)

ticker = st.text_input("Ticker", value="AAPL").strip().upper()

if ticker:

    df_earn, stats_earn = load_earnings(ticker)

    if df_earn is None or df_earn.empty:
        st.warning(f"No earnings data available for {ticker}.")
        st.stop()

    # Convert date column
    df_earn["Earnings Date"] = pd.to_datetime(df_earn["Earnings Date"], errors="coerce")

    # Historical reported quarters
    hist = df_earn[df_earn["Reported EPS"].notna()].copy()
    if hist.empty:
        st.warning(f"{ticker} has no reported earnings history.")
        st.stop()

    # =====================
    # METRICS
    # =====================

    c1, c2, c3 = st.columns(3)

    next_dt = stats_earn.get("next_date")
    next_dt_fmt = next_dt.strftime("%d %b %Y") if pd.notna(next_dt) else "N/A"
    c1.metric("Next Earnings Date", next_dt_fmt)

    next_eps = stats_earn.get("next_eps")
    next_eps_fmt = f"{float(next_eps):.2f}" if next_eps else "N/A"
    c2.metric("Consensus EPS (Next)", next_eps_fmt)

    beat_rate = stats_earn.get("beat_rate")
    beat_rate_fmt = f"{float(beat_rate):.1f}%" if beat_rate else "N/A"
    c3.metric("Beat Rate (%)", beat_rate_fmt)

    # =====================
    # Surprise statistics
    # =====================

    st.subheader("Surprise Statistics")
    st.write(f"- Average surprise: **{stats_earn['avg_surprise']:.2f}%**")
    st.write(f"- Surprise volatility (stdev): **{stats_earn['std_surprise']:.2f} ppts**")

    # =====================
    # Recent quarters table
    # =====================

    st.subheader("Recent Reported Quarters")

    recent = hist.sort_values("Earnings Date").tail(6).copy()
    recent["Earnings Date"] = recent["Earnings Date"].dt.strftime("%Y-%m-%d")

    table_html = recent[[
        "Earnings Date",
        "EPS Estimate",
        "Reported EPS",
        "Surprise(%)"
    ]].round(2).to_html(index=False, justify="center")

    st.markdown(table_html, unsafe_allow_html=True)

    # =====================
    # Chart
    # =====================

    st.subheader("Earnings Surprise – Last 6 Quarters")

    chart = (
        alt.Chart(recent)
        .mark_bar()
        .encode(
            x=alt.X("Earnings Date:N", title="Earnings Date"),
            y=alt.Y("Surprise(%)", title="EPS Surprise (%)"),
            tooltip=[
                "Earnings Date",
                "EPS Estimate",
                "Reported EPS",
                "Surprise(%)"
            ]
        )
    )

    st.altair_chart(chart, use_container_width=True)
