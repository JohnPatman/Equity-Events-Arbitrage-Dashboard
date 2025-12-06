import streamlit as st
import pandas as pd
import altair as alt

from modules.earnings.earnings import load_earnings

st.title("🔹 Earnings Intelligence – Surprise Analysis")
st.markdown("""This dashboard analyses earnings surprise behaviour for US equities.

It automatically:
- loads historical EPS estimates and reported results,
- calculates surprise percentages and volatility,
- displays beat rate statistics,
- shows the upcoming earnings date and forward consensus,
- visualises recent surprise history with clear bar charts.

This dashboard is ideal for studying how a company behaves around earnings,  
supporting pre-earnings strategy design, and understanding expectations vs reality.
""")

# ---------------------------------------------------------
# 📌 Ticker Input — Enhanced Styling
# ---------------------------------------------------------

st.markdown("""
<style>

div.stTextInput label {
    margin-bottom: 4px !important;
}

div.stTextInput > div > div > input {
    background-color: #e9f2ff !important;
    font-size: 1.20rem !important;
    font-weight: 700 !important;
    color: #000000 !important;
    border-radius: 10px !important;
    padding: 12px !important;
    border: 1px solid #c7d9ff !important;
}

div.stTextInput > div > div > input:focus {
    border: 1.5px solid #4c84ff !important;
    box-shadow: 0 0 0 2px rgba(76,132,255,0.25) !important;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<span style="font-size: 1.25rem; font-weight: 700;">
Enter US Earnings Ticker (e.g. AAPL, MSFT, NVDA):
</span>
""", unsafe_allow_html=True)

ticker = st.text_input("", value="AAPL").strip().upper()


# ---------------------------------------------------------
# 🎯 Earnings Logic
# ---------------------------------------------------------
if ticker:

    try:
        df_earn, stats_earn = load_earnings(ticker)

        if df_earn is None or stats_earn is None or df_earn.empty:
            st.warning(f"No earnings data available for {ticker}.")
            st.stop()

        df_earn = df_earn.rename(columns={
            "Earnings_Date": "Earnings Date",
            "Date": "Earnings Date"
        })
        df_earn["Earnings Date"] = pd.to_datetime(df_earn["Earnings Date"], errors="coerce")

        hist = df_earn[df_earn["Reported EPS"].notna()].copy()
        if hist.empty:
            st.warning("Ticker has no reported earnings.")
            st.stop()

        # ---------------------------------------------------------
        # 📈 TOP SUMMARY METRICS
        # ---------------------------------------------------------
        c1, c2, c3 = st.columns(3)

        next_dt = stats_earn.get("next_date")
        next_dt_fmt = next_dt.strftime("%d %b %Y") if next_dt else "N/A"
        with c1:
            st.metric("Next Earnings Date", next_dt_fmt)

        next_eps = stats_earn.get("next_eps")
        next_eps_fmt = f"{float(next_eps):.2f}" if next_eps else "N/A"
        with c2:
            st.metric("Consensus EPS (Next)", next_eps_fmt)

        beat_rate = stats_earn.get("beat_rate")
        beat_rate_fmt = f"{float(beat_rate):.1f}%" if beat_rate else "N/A"
        with c3:
            st.metric("Beat Rate (%)", beat_rate_fmt)

        # ---------------------------------------------------------
        # 📊 Surprise Statistics
        # ---------------------------------------------------------
        avg_s = stats_earn.get("avg_surprise")
        std_s = stats_earn.get("std_surprise")

        st.subheader("Surprise Statistics")
        st.write(f"- Average surprise: **{float(avg_s):.2f}%**" if avg_s is not None else "- Average surprise: N/A")
        st.write(f"- Surprise volatility (stdev): **{float(std_s):.2f} ppts**" if std_s is not None else "- Surprise volatility: N/A")

        # ---------------------------------------------------------
        # 📄 Recent Earnings Table (HTML-rendered, centred)
        # ---------------------------------------------------------
        st.subheader("Recent Reported Quarters")

        recent = hist.sort_values("Earnings Date").tail(6).copy()

        recent_tbl = recent[[
            "Earnings Date",
            "EPS Estimate",
            "Reported EPS",
            "Surprise(%)"
        ]].copy()

        # Format values
        recent_tbl["Earnings Date"] = recent_tbl["Earnings Date"].dt.strftime("%Y-%m-%d")
        recent_tbl["EPS Estimate"] = recent_tbl["EPS Estimate"].astype(float).round(2)
        recent_tbl["Reported EPS"] = recent_tbl["Reported EPS"].astype(float).round(2)
        recent_tbl["Surprise(%)"] = recent_tbl["Surprise(%)"].astype(float).round(2)

        # ⭐ TRUE centering with HTML table
        centered_html = recent_tbl.to_html(
            index=False,
            justify="center",
            classes="centered-table"
        )

        st.markdown("""
        <style>
        table.centered-table th, table.centered-table td {
            text-align: center !important;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown(centered_html, unsafe_allow_html=True)

        # ---------------------------------------------------------
        # 📥 CSV Export
        # ---------------------------------------------------------
        csv_data = recent_tbl.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Earnings Data (CSV)",
            data=csv_data,
            file_name=f"{ticker}_earnings_last_6_quarters.csv",
            mime="text/csv",
        )

        # ---------------------------------------------------------
        # 📈 Surprise Bar Chart
        # ---------------------------------------------------------
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

    except Exception as e:
        st.error(f"Earnings module failed for {ticker}: {e}")
