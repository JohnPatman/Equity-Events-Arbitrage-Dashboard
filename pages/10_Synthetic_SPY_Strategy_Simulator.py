import datetime as dt

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import yfinance as yf

from modules.strategy.synthetic_spy_sim import SimParams, simulate_synthetic

st.set_page_config(page_title="Synthetic SPY Strategy Simulator", layout="wide")

# ============================
# Intro / Description
# ============================
st.title("🔹 Synthetic SPY Strategy Simulator")

st.markdown("""
This dashboard models a systematic synthetic long exposure to the S&P 500 using
a call–put combination that behaves like a forward contract (≈ 100 delta per contract),
rolled at fixed intervals.

It brings together:

- full equity delta exposure per contract,
- broker-style margin requirements as a percentage of notional,
- idle cash earning a risk-free rate while tied up as margin,
- optional dividend drag to reflect foregone SPY dividends,
- realistic margin stress, top-ups, and liquidation rules.

The goal is to evaluate capital efficiency, drawdowns, and survivability
of a synthetic equity strategy versus traditional buy-and-hold SPY.

This is an economic exposure and funding simulation, not option pricing.
""")

# ============================
# Inputs
# ============================
st.subheader("Simulation Inputs")

with st.expander("Adjust Assumptions", expanded=True):
    col1, col2, col3 = st.columns(3)

    with col1:
        start = st.date_input("Start Date", value=dt.date(2015, 1, 1))
        end = st.date_input("End Date", value=dt.date(2025, 12, 31))
        initial_cash = st.number_input(
            "Starting Capital in Synthetic / Buy-to-Hold ($)",
            min_value=1000.0,
            value=10000.0,
            step=1000.0,
        )

    with col2:
        contracts = st.number_input("Number of Contracts", min_value=1, value=1, step=1)
        roll_months = st.selectbox("Roll Frequency (Months)", [1, 3, 6, 12], index=2)
        margin_pct = st.slider("Margin Requirement (% of Notional)", 0.10, 0.50, 0.25, 0.01)

    with col3:
        use_dynamic_rf = st.checkbox("Use dynamic risk-free rate (13-week T-bill)", value=True)
        rf_rate = st.slider("Fallback risk-free rate (annual %)", 0.0, 10.0, 4.5, 0.1) / 100.0
        div_drag = (
            st.slider(
                "Dividend drag (annual %, optional)",
                0.0,
                3.0,
                1.2,
                0.1,
                help="Synthetic doesn’t receive dividends.",
            )
            / 100.0
        )

    mode = st.selectbox(
        "Margin Breach Handling",
        ["Top up to meet margin", "Liquidate on margin breach"],
    )
    topup_mode = "topup" if mode.startswith("Top up") else "liquidate"

    run = st.button("Run Simulation", type="primary")

# ============================
# Data loaders
# ============================
@st.cache_data(show_spinner=False)
def load_spy(start_date: dt.date, end_date: dt.date) -> pd.DataFrame:
    data = yf.download("SPY", start=start_date, end=end_date, auto_adjust=False, progress=False)
    return data[["Close", "Adj Close"]].dropna()


@st.cache_data(show_spinner=False)
def load_irx(start_date: dt.date, end_date: dt.date) -> pd.Series:
    data = yf.download("^IRX", start=start_date, end=end_date, auto_adjust=False, progress=False)
    if data.empty:
        return pd.Series(dtype=float)
    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    irx_dec = close.astype(float) / 100.0
    irx_dec.name = "RF_Annual"
    return irx_dec


# ============================
# Run simulation
# ============================
if run:
    if start >= end:
        st.error("Start date must be before end date.")
        st.stop()

    prices = load_spy(start, end)
    rf_series = None

    if use_dynamic_rf:
        irx = load_irx(start, end)
        if not irx.empty:
            rf_series = irx.reindex(prices.index).ffill().bfill()

    params = SimParams(
        initial_cash=float(initial_cash),
        contracts=int(contracts),
        margin_pct=float(margin_pct),
        rf_rate_annual=float(rf_rate),
        roll_months=int(roll_months),
        dividend_yield_drag_annual=float(div_drag),
        topup_mode=topup_mode,
    )

    res, m = simulate_synthetic(prices, params, rf_annual_series=rf_series)

    # ============================
    # Capital efficiency metrics (NEW)
    # ============================
    capital_required_total = initial_cash + m["peak_total_topup"]
    capital_per_contract = capital_required_total / contracts

    st.subheader("Capital Efficiency & Survivability")

    k1, k2, k3 = st.columns(3)
    k1.metric("Capital Required per Contract", f"${capital_per_contract:,.0f}")
    k2.metric("Total Capital Required", f"${capital_required_total:,.0f}")
    k3.metric("Peak Margin Requirement", f"${m['peak_margin_req']:,.0f}")

    # ============================
    # Performance metrics
    # ============================
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Final Value (Synthetic)", f"${m['final_synthetic_equity']:,.0f}")
    c2.metric("Final Value (Buy & Hold)", f"${m['final_buyhold_equity']:,.0f}")
    c3.metric("CAGR (Synthetic)", f"{m['cagr_synthetic']*100:,.1f}%")
    c4.metric("CAGR (Buy & Hold)", f"{m['cagr_buyhold']*100:,.1f}%")

    # ============================
    # Charts
    # ============================
    st.subheader("Synthetic vs Buy & Hold Equity Curves")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(res.index, res["Synthetic_Equity"], label="Synthetic")
    ax.plot(res.index, res["BuyHold_Equity"], label="Buy & Hold")
    ax.legend()
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)

    st.subheader("Margin Requirement vs Notional")
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.plot(res.index, res["Synthetic_Notional"], label="Notional")
    ax2.plot(res.index, res["Margin_Req"], label="Margin Req")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    st.pyplot(fig2)

    # ============================
    # Year-by-year returns
    # ============================
    st.subheader("Year-by-Year Returns (%)")

    yearly = pd.DataFrame(
        {
            "Synthetic %": res["Synthetic_Equity"],
            "Buy & Hold %": res["BuyHold_Equity"],
        }
    ).resample("Y").last()

    yearly_returns = yearly.pct_change().dropna() * 100
    yearly_returns.index = yearly_returns.index.year

    yearly_tbl = yearly_returns.reset_index()
    yearly_tbl = yearly_tbl.rename(columns={yearly_tbl.columns[0]: "Year"})
    yearly_tbl["Synthetic Outperformance"] = (
        yearly_tbl["Synthetic %"] - yearly_tbl["Buy & Hold %"]
    )

    st.dataframe(
        yearly_tbl.style
        .format("{:.2f}", subset=["Synthetic %", "Buy & Hold %", "Synthetic Outperformance"])
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{"selector": "th", "props": [("text-align", "center")]}]),
        use_container_width=True,
        hide_index=True,
    )

    # ============================
    # Raw data
    # ============================
    with st.expander("Results table / Raw Data (last 200 rows)", expanded=False):
        st.dataframe(res.tail(200), use_container_width=True)

else:
    st.info("Adjust parameters above and click **Run Simulation**.")
