import streamlit as st
import pandas as pd
import altair as alt
import os

st.title("🔹 Dividend Growth (Unilever example) (2010–2025)")
st.markdown("""This dashboard analyses long-term dividend growth using Unilever as a model.

It processes 15+ years of dividend history to:
- calculate year-on-year dividend growth,
- measure long-term CAGR (compound annual growth rate),
- detect periods of dividend increases or cuts,
- visualise trends through combined line-and-bar charts.

This dashboard is ideal for studying dividend stability, assessing payout trajectory,  
and understanding the characteristics of mature, cash-generative companies.
""")
hist_path = "Data/history_ulvr_2010_2025.csv"

if os.path.exists(hist_path):

    hist = pd.read_csv(hist_path)

    hist["Pay Date"] = pd.to_datetime(hist["Pay Date"], errors="coerce")
    hist = hist.dropna(subset=["Pay Date"]).sort_values("Pay Date")

    hist["Year"] = hist["Pay Date"].dt.year.astype(int)

    yearly = (
        hist.groupby("Year")["Dividend"]
        .mean()
        .reset_index()
        .rename(columns={"Dividend": "Avg Dividend (£)"})
    )

    yearly["YoY %"] = yearly["Avg Dividend (£)"].pct_change() * 100

    yearly["Colour"] = yearly["YoY %"].apply(
        lambda x: "green" if x > 0 else ("red" if x < 0 else "grey")
    )

    first = yearly["Avg Dividend (£)"].iloc[0]
    last = yearly["Avg Dividend (£)"].iloc[-1]
    yrs = len(yearly) - 1
    cagr = ((last / first) ** (1/yrs) - 1) * 100

    # --- Line chart ---
    line = (
        alt.Chart(yearly)
        .mark_line(point=True)
        .encode(
            x=alt.X("Year:O", title="Year"),
            y=alt.Y("Avg Dividend (£):Q",
                    scale=alt.Scale(domain=[0.15, 0.40]),
                    title="Dividend per share (£)"),
            tooltip=["Year", "Avg Dividend (£)", "YoY %"]
        )
    )

    # --- YoY bars ---
    bars = (
        alt.Chart(yearly)
        .mark_bar()
        .encode(
            x="Year:O",
            y=alt.Y("YoY %:Q", title="YoY Change %"),
            color=alt.Color("Colour:N", scale=None),
            tooltip=["Year", "YoY %"]
        )
    )

    final_chart = alt.vconcat(
        line.properties(height=260),
        bars.properties(height=200)
    ).interactive()

    st.altair_chart(final_chart, use_container_width=True)

    st.markdown(f"""
    ### 📊 Dividend Growth Summary  
    • Latest dividend (2025): **£{last:.4f}**  
    • YoY Change: **{yearly['YoY %'].iloc[-1]:.2f}%**  
    • CAGR (2010–2025): **{cagr:.2f}%** annually  
    """)

    with st.expander("📄 View Full Annual Breakdown"):
        annual = yearly.copy()
        annual["Avg Dividend (£)"] = annual["Avg Dividend (£)"].map(lambda x: f"£{x:.4f}")
        annual["YoY %"] = annual["YoY %"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "-")
        st.dataframe(annual, hide_index=True, use_container_width=True)

else:
    st.error("Historical dataset missing — run fetch_ulvr_history.py")
