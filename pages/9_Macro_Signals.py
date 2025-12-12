import streamlit as st
import pandas as pd
import altair as alt

from modules.macro.yield_curve import load_us_yields, compute_slope, classify_curve, latest_value
from modules.macro.inflation import load_us_inflation, load_uk_inflation, classify_inflation
from modules.macro.real_yields import compute_real_yield
from modules.macro.regime import macro_regime

st.title("🔹 Macro Signals Dashboard")

st.markdown("""
This dashboard tracks core macro indicators that drive equity, bond, and currency markets.

It brings together:
- the US Treasury yield curve (3M to 30Y) and its slope dynamics,
- US vs UK inflation trends with selectable history windows,
- real (inflation-adjusted) US interest rates,
- a combined macro regime score signalling risk conditions.

These signals provide a high-level read on growth expectations, policy pressure,
market stress, and the attractiveness of risk assets versus safe assets.
Ideal for traders, asset allocators, and anyone following global macro conditions.
""")

# --------------------------- LOAD DATA ---------------------------
st.subheader("Loading Macro Data…")
yields = load_us_yields()
cpi_headline, cpi_core = load_us_inflation()
uk_cpi = load_uk_inflation()

# Safeguard: If ANY yield series is empty, stop gracefully
required_terms = ["3M", "2Y", "5Y", "10Y", "30Y"]
for term in required_terms:
    if term not in yields or yields[term].empty:
        st.error(f"No data available for {term} yield from FRED.")
        st.stop()

# --------------------------- YIELD CURVE ---------------------------
st.header("📈 US Yield Curve")

val_10y = latest_value(yields["10Y"])
val_2y = latest_value(yields["2Y"])
slope = compute_slope(yields["10Y"], yields["2Y"])
curve_state = classify_curve(slope)

col1, col2, col3 = st.columns(3)
col1.metric("10-Year Yield", f"{val_10y:.2f}%")
col2.metric("2-Year Yield", f"{val_2y:.2f}%")
col3.metric("10Y–2Y Slope", f"{slope:.2f}%")

st.write(f"**Curve classification:** {curve_state}")

# Yield curve chart (correct axis order)
curve_df = pd.DataFrame({
    "Term": ["3M", "2Y", "5Y", "10Y", "30Y"],
    "Yield": [latest_value(yields[t]) for t in ["3M","2Y","5Y","10Y","30Y"]],
})

chart = alt.Chart(curve_df).mark_line(point=True).encode(
    x=alt.X("Term:N", sort=["3M", "2Y", "5Y", "10Y", "30Y"]),
    y="Yield:Q"
)

st.altair_chart(chart, use_container_width=True)

# Commentary
st.caption("""
**Yield Curve Insight:**  
A positively sloped curve (long rates higher than short rates) often signals improving economic expectations.  
An inverted curve (short > long) has historically preceded recessions and periods of equity volatility.
""")

# --------------------------- INFLATION ---------------------------
st.header("US vs UK Inflation Trend")

# Compute YoY changes
cpi_headline["YoY"] = cpi_headline["Value"].pct_change(12) * 100
uk_cpi["YoY"] = uk_cpi["Value"].pct_change(12) * 100

# Clean data
cpi_clean = cpi_headline.dropna(subset=["YoY"])
uk_clean = uk_cpi.dropna(subset=["YoY"])

# Metrics block (US + UK)
latest_cpi_yoy = float(cpi_clean["YoY"].iloc[-1])
latest_uk_yoy = float(uk_clean["YoY"].iloc[-1])

infl_state_us = classify_inflation(latest_cpi_yoy)
infl_state_uk = classify_inflation(latest_uk_yoy)

col_us, col_uk = st.columns(2)
col_us.metric("US CPI YoY", f"{latest_cpi_yoy:.2f}%", infl_state_us)
col_uk.metric("UK CPI YoY", f"{latest_uk_yoy:.2f}%", infl_state_uk)

# ---------------- Selectable history window ----------------
period = st.selectbox(
    "Select inflation history:",
    ["Last 10 years", "Last 20 years", "Last 30 years", "Last 40 years", "Last 50 years", "Full history"],
    index=0
)

if period != "Full history":
    years = int(period.split()[1])
    cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)
    cpi_us_plot = cpi_clean[cpi_clean["Date"] >= cutoff]
    cpi_uk_plot = uk_clean[uk_clean["Date"] >= cutoff]
else:
    cpi_us_plot = cpi_clean
    cpi_uk_plot = uk_clean

# Prepare combined inflation chart
cpi_us_plot = cpi_us_plot[["Date", "YoY"]].assign(Country="US")
cpi_uk_plot = cpi_uk_plot[["Date", "YoY"]].assign(Country="UK")

infl_df = pd.concat([cpi_us_plot, cpi_uk_plot])

infl_chart = (
    alt.Chart(infl_df)
    .mark_line()
    .encode(
        x="Date:T",
        y=alt.Y("YoY:Q", title="Year-over-Year Inflation (%)"),
        color=alt.Color("Country:N", scale=alt.Scale(range=["#1f77b4", "#d62728"])),
        tooltip=["Date:T", "Country:N", "YoY:Q"]
    )
    .interactive()
)

st.altair_chart(infl_chart, use_container_width=True)

# Commentary
st.caption("""
**Inflation Insight:**  
Declining inflation reduces pressure on central banks and generally supports equity valuations.  
Sustained high inflation leads to higher real yields, tightening financial conditions and weighing on risk assets.  
Comparing US and UK inflation highlights differences in monetary policy cycles and economic shocks.
""")

# --------------------------- REAL YIELDS ---------------------------
st.header("Real Yields")

# US Real Yield
us_real_yield = compute_real_yield(val_10y, latest_cpi_yoy)

# UK Real Yield (approx using same 10Y nominal until UK curve added)
uk_nominal_10y = val_10y
uk_real_yield = compute_real_yield(uk_nominal_10y, latest_uk_yoy)

col1, col2 = st.columns(2)
col1.metric("US 10Y Real Yield", f"{us_real_yield:.2f}%")
col2.metric("UK 10Y Real Yield (approx)", f"{uk_real_yield:.2f}%")

st.caption("""
**Real Yield Insight:**  
Real yields (adjusted for inflation) are crucial for asset pricing.  
Higher real yields tend to compress equity multiples and strengthen the currency,  
while lower or negative real yields typically support risk-taking.
""")

# --------------------------- REGIME ---------------------------
st.header("Macro Market Regime")

regime_label = macro_regime(slope, latest_cpi_yoy, us_real_yield)

if "Green" in regime_label:
    st.success(regime_label)
elif "Yellow" in regime_label:
    st.warning(regime_label)
else:
    st.error(regime_label)

st.caption("""
**Macro Regime Insight:**  
A combined macro score based on curve shape, inflation, and real yields.  
Green = supportive environment.  
Yellow = mixed signals, moderate caution.  
Red = tightening conditions and elevated risk.
""")
