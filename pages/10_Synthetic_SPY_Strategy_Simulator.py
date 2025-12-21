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
Implied volatility, Greeks, and option market microstructure are deliberately abstracted
to focus on leverage, carry, and risk management.
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
            "Starting Capital in Synthetic/Buy-to-Hold ($)",
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

    cap_topups = st.checkbox("Cap total top-ups (stress test)")
    max_total_topup = None
    if cap_topups:
        max_total_topup = st.number_input(
            "Max total top-ups allowed ($)",
            min_value=0.0,
            value=8000.0,
            step=500.0,
        )

    run = st.button("Run Simulation", type="primary")


# ============================
# Helpers
# ============================
def _flatten_yf_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    yfinance sometimes returns MultiIndex columns (esp. on Streamlit Cloud).
    This normalizes them into single-level columns like 'Close', 'Adj Close', etc.
    """
    if isinstance(df.columns, pd.MultiIndex):
        # Most common shape: ('Close','SPY') etc. Keep the first level.
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df


def _first_scalar(x) -> float:
    """
    Convert possibly Series/array-like to a single float.
    """
    if isinstance(x, pd.Series):
        return float(x.iloc[0])
    return float(x)


# ============================
# Data loaders
# ============================
@st.cache_data(show_spinner=False)
def load_spy(start_date: dt.date, end_date: dt.date) -> pd.DataFrame:
    data = yf.download("SPY", start=start_date, end=end_date, auto_adjust=False, progress=False)
    data = _flatten_yf_columns(data)

    out = data[["Close", "Adj Close"]].dropna()

    # Guarantee these are Series columns (not nested)
    for col in ["Close", "Adj Close"]:
        if isinstance(out[col], pd.DataFrame):
            out[col] = out[col].iloc[:, 0]

    return out


@st.cache_data(show_spinner=False)
def load_irx(start_date: dt.date, end_date: dt.date) -> pd.Series:
    data = yf.download("^IRX", start=start_date, end=end_date, auto_adjust=False, progress=False)
    data = _flatten_yf_columns(data)

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

    with st.spinner("Downloading SPY data..."):
        prices = load_spy(start, end)

    if prices.empty:
        st.error("No SPY data returned.")
        st.stop()

    rf_series = None
    if use_dynamic_rf:
        with st.spinner("Downloading ^IRX (risk-free proxy)..."):
            irx = load_irx(start, end)

        if not irx.empty:
            rf_series = irx.reindex(prices.index).ffill().bfill()
        else:
            st.warning("Could not load ^IRX. Using fallback rate.")

    # ============================
    # Initial margin feasibility check (broker-style) — use entry price at start
    # ============================
    start_dt = prices.index[0]
    start_spy = _first_scalar(prices.loc[start_dt, "Close"])

    contract_multiplier = 100
    est_notional = start_spy * int(contracts) * contract_multiplier
    est_initial_margin = float(margin_pct) * est_notional

    init_cash_f = float(initial_cash)

    if init_cash_f < float(est_initial_margin):
        shortfall = float(est_initial_margin) - init_cash_f
        st.warning(
            f"⚠️ Initial margin feasibility check (entry at {start_dt.date()})\n\n"
            f"- SPY entry price (Close): **${start_spy:,.2f}**\n"
            f"- Contracts: **{int(contracts)}** (multiplier {contract_multiplier})\n"
            f"- Estimated notional: **${est_notional:,.0f}**\n"
            f"- Initial margin required (@ {float(margin_pct)*100:.0f}%): **${est_initial_margin:,.0f}**\n"
            f"- Your starting capital: **${init_cash_f:,.0f}**\n"
            f"- Shortfall: **${shortfall:,.0f}**\n\n"
            "A real broker would likely reject opening this position without additional capital. "
            "The simulation will still run so you can stress-test top-ups / liquidation."
        )
    else:
        st.info(
            f"✅ Initial margin check passed (entry at {start_dt.date()}) — "
            f"Required ≈ ${est_initial_margin:,.0f} vs starting capital ${init_cash_f:,.0f}."
        )

    params = SimParams(
        initial_cash=init_cash_f,
        contracts=int(contracts),
        margin_pct=float(margin_pct),
        rf_rate_annual=float(rf_rate),
        roll_months=int(roll_months),
        dividend_yield_drag_annual=float(div_drag),
        topup_mode=topup_mode,
        max_total_topup=float(max_total_topup) if max_total_topup is not None else None,
    )

    res, m = simulate_synthetic(prices, params, rf_annual_series=rf_series)

    # ============================
    # Charts & Metrics
    # ============================
    st.subheader("SPY Price Graph")
    figp, axp = plt.subplots(figsize=(10, 4))
    axp.plot(prices.index, prices["Close"])
    axp.set_ylabel("Price per Share of SPY ($)")
    axp.grid(True, alpha=0.3)
    st.pyplot(figp)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Final Value (Synthetic)", f"${m['final_synthetic_equity']:,.0f}")
    c2.metric("Final Value (Buy & Hold)", f"${m['final_buyhold_equity']:,.0f}")
    c3.metric("CAGR (Synthetic)", f"{m['cagr_synthetic']*100:,.1f}%")
    c4.metric("CAGR (Buy & Hold)", f"{m['cagr_buyhold']*100:,.1f}%")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Max Drawdown in Selected Period (Synthetic)", f"{m['max_dd_synthetic']*100:,.1f}%")
    c6.metric("Max Drawdown in Selected Period (Buy & Hold)", f"{m['max_dd_buyhold']*100:,.1f}%")
    c7.metric("Peak Margin Requirement", f"${m['peak_margin_req']:,.0f}")
    c8.metric("Peak Total Margin Top-up", f"${m['peak_total_topup']:,.0f}")

    if m["liquidated"]:
        st.warning("Liquidation triggered under your settings.")

    st.subheader("Comparison: Synthetic VS Buy & Hold")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(res.index, res["Synthetic_Equity"], label="Synthetic")
    ax.plot(res.index, res["BuyHold_Equity"], label="Buy & Hold")
    ax.legend()
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)

    st.subheader("Account Margin in relation to Notional Value")
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.plot(res.index, res["Synthetic_Notional"], label="Notional")
    ax2.plot(res.index, res["Margin_Req"], label="Margin Req")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    st.pyplot(fig2)

    # ============================
    # Year-by-year table (prettified + year formatting)
    # ============================
    st.subheader("Year-by-Year Returns (%)")

    yearly = pd.DataFrame(
        {
            "Synthetic %": res["Synthetic_Equity"],
            "Buy & Hold %": res["BuyHold_Equity"],
        }
    ).resample("Y").last()

    yearly_returns = yearly.pct_change().dropna() * 100
    yearly_returns.index = yearly_returns.index.year  # int years

    yearly_tbl = yearly_returns.reset_index()
    first_col = yearly_tbl.columns[0]
    yearly_tbl = yearly_tbl.rename(columns={first_col: "Year"})
    yearly_tbl["Year"] = yearly_tbl["Year"].astype(int).astype(str)

    yearly_tbl["Synthetic Outperformance / Underperformance"] = (
        yearly_tbl["Synthetic %"] - yearly_tbl["Buy & Hold %"]
    )

    styler = (
        yearly_tbl.style
        .format(
            {
                "Synthetic %": "{:.2f}",
                "Buy & Hold %": "{:.2f}",
                "Synthetic Outperformance / Underperformance": "{:.2f}",
            }
        )
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
    )

    st.dataframe(styler, use_container_width=True, hide_index=True)

    # ============================
    # Raw data (collapsed by default)
    # ============================
    with st.expander("Results table / Raw Data (last 200 rows)", expanded=False):
        st.dataframe(res.tail(200), use_container_width=True)

        st.download_button(
            "Download full results CSV",
            data=res.to_csv().encode("utf-8"),
            file_name="synthetic_spy_sim.csv",
            mime="text/csv",
        )

else:
    st.info("Adjust parameters above and click **Run Simulation**.")
