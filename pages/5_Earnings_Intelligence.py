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

st.markdown("""
<span style="font-size: 1.25rem; font-weight: 700;">
Enter US Earnings Ticker (e.g. AAPL, MSFT, NVDA):
</span>
""", unsafe_allow_html=True)

ticker = st.text_input("", value="AAPL").strip().upper()


if ticker:

    df_earn, stats_earn = load_earnings(ticker)

    # --- If the module returns nothing ---
    if df_earn is None or df_earn.empty:
        st.warning(f"No earnings data available for {ticker}.")
        st.stop()

    # --- Standardise column names ---
    df_earn = df_earn.rename(columns={
        "Earnings_Date": "Earnings Date",
        "Date": "Earnings Date"
    })

    df_earn["Earnings Date"] = pd.to_datetime(df_earn["Earnings Date"], errors="coerce")

    # --- Historical rows (Reported EPS not null) ---
    hist = df_earn[df_earn["Reported EPS"].notna()].copy()
    if hist.empty:
        st.warning(f"{ticker} has no reported earnings history.")
        st.stop()

    # =======================
    # METRICS
    # =======================

    c1, c2, c3 = st.columns(3)

    # Next earnings date
    next_dt = stats_earn.get("next_date")
    next_dt_fmt = next_dt.strftime("%d %b %Y") if pd.notna(next_dt) else "N/A"
    with c1:
        st.metric("Next Earnings Date", next_dt_fmt)

    # Forward EPS estimate
    next_eps = stats_earn.get("next_eps")
    next_eps_fmt = f"{float(next_eps):.2f}" if next_eps else "N/A"
    with c2:
        st.metric("Consensus EPS (Next)", next_eps_fmt)

    beat_rate = stats_earn.get("beat_rate")
    beat_rate_fmt = f"{float(beat_rate):.1f}%" if beat_rate else "N/A"
    with c3:
        st.metric("Beat Rate (%)", beat_rate_fmt)

    # =======================
    # Surprise stats
    # =======================
    avg_s = stats_earn.get("avg_surprise")
    std_s = stats_earn.get("std_surprise")

    st.subheader("Surprise Statistics")
    st.write(f"- Average surprise: **{float(avg_s):.2f}%**" if avg_s is not None else "- Average surprise: N/A")
    st.write(f"- Surprise volatility (stdev): **{float(std_s):.2f} ppts**" if std_s is not None else "- Surprise volatility: N/A")


    # =======================
    # Recent table
    # =======================
    st.subheader("Recent Reported Quarters")

    recent = hist.sort_values("Earnings Date").tail(6).copy()

    recent_tbl = recent[[
        "Earnings Date",
        "EPS Estimate",
        "Reported EPS",
        "Surprise(%)"
    ]].copy()

    # Formatting
    recent_tbl["Earnings Date"] = recent_tbl["Earnings Date"].dt.strftime("%Y-%m-%d")
    recent_tbl["EPS Estimate"] = recent_tbl["EPS Estimate"].round(2)
    recent_tbl["Reported EPS"] = recent_tbl["Reported EPS"].round(2)
    recent_tbl["Surprise(%)"] = recent_tbl["Surprise(%)"].round(2)

    # Center table
    st.markdown("""
    <style>
        table.centered-table th, table.centered-table td {
            text-align: center !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        recent_tbl.to_html(index=False, justify="center", classes="centered-table"),
        unsafe_allow_html=True
    )

    # CSV
    csv_data = recent_tbl.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Earnings Data (CSV)",
        data=csv_data,
        file_name=f"{ticker}_earnings_last_6_quarters.csv",
        mime="text/csv",
    )


    # =======================
    # Surprise Chart
    # =======================

    chart = (
        alt.Chart(recent_tbl)
        .mark_bar()
        .encode(
            x=alt.X("Earnings Date:N", title="Earnings Date"),
            y=alt.Y("Surprise(%)", title="EPS Surprise (%)"),
            tooltip=[
                "Earnings Date",
                alt.Tooltip("EPS Estimate:Q", format=".2f"),
                alt.Tooltip("Reported EPS:Q", format=".2f"),
                alt.Tooltip("Surprise(%):Q", format=".2f")
            ]
        )
    )

    st.subheader("Earnings Surprise – Last 6 Quarters")
    st.altair_chart(chart, use_container_width=True)
