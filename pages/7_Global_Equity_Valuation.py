import streamlit as st
import pandas as pd
from modules.valuation.global_valuation import build_global_valuation_table

st.title("🔹 Global Equity Valuations")
st.markdown("""This dashboard compares valuation metrics across global markets.

It consolidates cross-country financial data to present:
- dividend yields, PE ratios, forward PE, and price-to-book values,
- multi-period equity performance (1Y, 5Y, 10Y),
- a proprietary value score (1–100),
- heat-mapped valuation zones for quick interpretation,
- CSV export for further research or modelling.

This dashboard is ideal for top-down equity allocators,  
country-selection research, and global macro valuation analysis.
""")
st.subheader("Ratios, Performance & Value Scores (Developed, Emerging, and Frontier examples)")


try:
    df = build_global_valuation_table().copy()

    # ------------------ Market classification ------------------ #
    classification = {
        "USA": "Developed",
        "UK": "Developed",
        "Germany": "Developed",
        "China": "Emerging",
        "India": "Emerging",
        "Mexico": "Emerging",
        "Vietnam": "Frontier",
        "Argentina": "Frontier",
        "Philippines": "Frontier",
    }
    df["Market"] = df["Country"].map(classification).fillna("Other")

    # ------------------ Verdict cleanup ------------------ #
    df["Verdict"] = df["Verdict"].apply(
        lambda x: x.split("(")[1].replace(")", "").strip()
    )

    # ------------------ Missing Forward PE ------------------ #
    df["PE_Fwd"] = df["PE_Fwd"].fillna("–")

    # ------------------ Rename columns for UI ------------------ #
    df = df.rename(columns={
        "DivYld": "Dividend Yield %",
        "PE": "PE Ratio",
        "PE_Fwd": "Forward PE Ratio",     # FIXED
        "PB": "Price-to-Book Ratio",
        "Perf_1Y": "1 Year Performance %",
        "Perf_5Y": "5 Year Performance %",
        "Perf_10Y": "10 Year Performance %",
        "Score": "Score (1–100)"
    })

    # ------------------ Convert numeric fields ------------------ #
    df["Score (1–100)"] = pd.to_numeric(df["Score (1–100)"], errors="coerce")
    df["PE Ratio"] = pd.to_numeric(df["PE Ratio"], errors="coerce")
    df["Price-to-Book Ratio"] = pd.to_numeric(df["Price-to-Book Ratio"], errors="coerce")

    # Forward PE: convert to numeric but preserve "–"
    df["Forward PE Ratio"] = pd.to_numeric(df["Forward PE Ratio"], errors="coerce")
    df["Forward PE Ratio"] = df["Forward PE Ratio"].apply(
        lambda v: "–" if pd.isna(v) else round(v, 2)
    )

    # Round performance and dividend metrics
    for c in [
        "Dividend Yield %", "PE Ratio", "Price-to-Book Ratio",
        "1 Year Performance %", "5 Year Performance %", "10 Year Performance %"
    ]:
        df[c] = pd.to_numeric(df[c], errors="coerce").round(2)

    # ------------------ Column order ------------------ #
    df = df[
        ["Country", "Market",
         "Dividend Yield %", "PE Ratio", "Forward PE Ratio", "Price-to-Book Ratio",
         "1 Year Performance %", "5 Year Performance %", "10 Year Performance %",
         "Score (1–100)", "Verdict"]
    ]

    
    def darker_heatmap(values):
        colors = []
        s = pd.Series(values)

        # Only numeric values get colour applied
        numeric_s = pd.to_numeric(s, errors="coerce")
        vmin, vmax = numeric_s.min(), numeric_s.max()
        vrange = vmax - vmin if vmax != vmin else 1

        for v_raw, v in zip(s, numeric_s):
            if pd.isna(v):
                colors.append("background-color: white;")
                continue

            # Normalise between 0–1
            t = (v - vmin) / vrange

            if t < 0.33:
                colors.append("background-color: rgb(205, 225, 210);")  # greenish
            elif t < 0.66:
                colors.append("background-color: rgb(225, 225, 225);")  # neutral grey
            else:
                colors.append("background-color: rgb(230, 200, 200);")  # muted red

        return colors

    styled = (
        df.style
        .apply(darker_heatmap, subset=["PE Ratio"])
        .apply(darker_heatmap, subset=["Forward PE Ratio"])
        .apply(darker_heatmap, subset=["Price-to-Book Ratio"])
        .apply(darker_heatmap, subset=["Score (1–100)"])
        .hide(axis="index")
        .format(precision=2)
    )

    
    st.markdown("""
    <style>
    table td, table th {
        text-align: center !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Render the styled table
    st.write(styled.to_html(), unsafe_allow_html=True)


    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name="global_equity_valuation.csv",
        mime="text/csv"
    )

except Exception as e:
    st.error(f"Global valuation module failed: {e}")
