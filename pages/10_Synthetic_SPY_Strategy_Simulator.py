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

st.markdown(
    """
This dashboard models a systematic synthetic long exposure to the S&P 500 using
a call–put combination that behaves like a forward contract (≈ 100 delta per contract),
rolled at fixed intervals.

It brings together:

- full equity delta exposure per contract,
- broker-style margin requirements as a percentage of notional,
- idle cash earning a risk-free rate while tied up as margin,
- optional dividend drag to reflect foregone SPY dividends,
- realistic margin stress, top-ups, and liquidation rules.

### Benchmarks (equal starting cash)
Alongside the synthetic strategy, the dashboard plots equal-cash buy & hold equity curves for:

- **SPY** (unlevered S&P 500 ETF),
- **SSO** (≈2× daily S&P 500 leveraged ETF),
- **UPRO** (≈3× daily S&P 500 leveraged ETF).

Note: SSO/UPRO are daily-reset leveraged ETFs, so their long-run performance can diverge
materially from “2× or 3× SPY” due to volatility/path effects (“volatility drag”).

The goal is to evaluate capital efficiency, drawdowns, and survivability
of a synthetic equity strategy versus traditional buy-and-hold alternatives.

This is an economic exposure and funding simulation, not option pricing.
Implied volatility, Greeks, and option market microstructure are deliberately abstracted
to focus on leverage, carry, and risk management.
"""
)


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
        margin_pct = st.slider(
            "Margin Requirement (% of Notional)", 0.10, 0.50, 0.25, 0.01
        )

    with col3:
        use_dynamic_rf = st.checkbox(
            "Use dynamic risk-free rate (13-week T-bill)", value=True
        )
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
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df


def _first_scalar(x) -> float:
    """Convert possibly Series/array-like to a single float."""
    if isinstance(x, pd.Series):
        return float(x.iloc[0])
    return float(x)


def _cagr_from_equity(equity: pd.Series) -> float:
    equity = equity.dropna()
    if equity.empty:
        return float("nan")
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0:
        return float("nan")
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1)


def _max_drawdown(equity: pd.Series) -> float:
    equity = equity.dropna()
    if equity.empty:
        return float("nan")
    peak = equity.cummax()
    dd = (equity / peak) - 1.0
    return float(dd.min())


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


@st.cache_data(show_spinner=False)
def load_benchmark_adjclose(ticker: str, start_date: dt.date, end_date: dt.date) -> pd.Series:
    """
    Returns Adj Close as a clean Series for equal-cash buy & hold benchmarking.
    """
    data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False, progress=False)
    data = _flatten_yf_columns(data)

    if data.empty:
        return pd.Series(dtype=float, name=ticker)

    adj = data["Adj Close"]
    if isinstance(adj, pd.DataFrame):
        adj = adj.iloc[:, 0]

    adj = adj.dropna().astype(float)
    adj.name = ticker
    return adj


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

    # IMPORTANT: escape $ to avoid Streamlit Markdown interpreting math mode ($...$)
    if init_cash_f < float(est_initial_margin):
        shortfall = float(est_initial_margin) - init_cash_f
        st.warning(
            f"⚠️ Initial margin feasibility check (entry at {start_dt.date()})\n\n"
            f"- SPY entry price (Close): **\\${start_spy:,.2f}**\n"
            f"- Contracts: **{int(contracts)}** (multiplier {contract_multiplier})\n"
            f"- Estimated notional: **\\${est_notional:,.0f}**\n"
            f"- Initial margin required (@ {float(margin_pct)*100:.0f}%): **\\${est_initial_margin:,.0f}**\n"
            f"- Your starting capital: **\\${init_cash_f:,.0f}**\n"
            f"- Shortfall: **\\${shortfall:,.0f}**\n\n"
            "A real broker would likely reject opening this position without additional capital. "
            "The simulation will still run so you can stress-test top-ups / liquidation."
        )
    else:
        st.success(
            f"✅ Initial margin check passed (entry at {start_dt.date()}) — "
            f"Required ≈ \\${est_initial_margin:,.0f} vs starting capital \\${init_cash_f:,.0f}."
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
    # Equal-cash ETF benchmarks: SPY / SSO / UPRO (Buy & Hold)
    # ============================
    with st.spinner("Downloading benchmark ETFs (SPY / SSO / UPRO)..."):
        spy_adj = load_benchmark_adjclose("SPY", start, end)
        sso_adj = load_benchmark_adjclose("SSO", start, end)
        upro_adj = load_benchmark_adjclose("UPRO", start, end)

    # Align to simulation dates
    idx = res.index
    spy_adj = spy_adj.reindex(idx).ffill().bfill()
    sso_adj = sso_adj.reindex(idx).ffill().bfill()
    upro_adj = upro_adj.reindex(idx).ffill().bfill()

    # Equal-cash equity curves
    spy_bh_eq = init_cash_f * (spy_adj / spy_adj.iloc[0])
    sso_bh_eq = init_cash_f * (sso_adj / sso_adj.iloc[0]) if not sso_adj.empty else pd.Series(index=idx, dtype=float)
    upro_bh_eq = init_cash_f * (upro_adj / upro_adj.iloc[0]) if not upro_adj.empty else pd.Series(index=idx, dtype=float)

    spy_cagr = _cagr_from_equity(spy_bh_eq)
    sso_cagr = _cagr_from_equity(sso_bh_eq) if sso_bh_eq.notna().any() else float("nan")
    upro_cagr = _cagr_from_equity(upro_bh_eq) if upro_bh_eq.notna().any() else float("nan")

    spy_dd = _max_drawdown(spy_bh_eq)
    sso_dd = _max_drawdown(sso_bh_eq) if sso_bh_eq.notna().any() else float("nan")
    upro_dd = _max_drawdown(upro_bh_eq) if upro_bh_eq.notna().any() else float("nan")

    # ============================
    # Margin call count (top-up events)
    # A "margin call" occurs on any day where Total_Topup increases vs prior day.
    # ============================
    topup_changes = res["Total_Topup"].diff().fillna(0.0)
    margin_calls = int((topup_changes > 0).sum())

    # ============================
    # Charts & Metrics
    # ============================
    st.subheader("SPY Price Graph")
    figp, axp = plt.subplots(figsize=(10, 4))
    axp.plot(prices.index, prices["Close"])
    axp.set_ylabel("Price per Share of SPY ($)")
    axp.grid(True, alpha=0.3)
    st.pyplot(figp)

    # ---- Final Values (equal-cash comparisons)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Final Value (Synthetic)", f"${m['final_synthetic_equity']:,.0f}")
    c2.metric("Final Value (SPY Buy & Hold)", f"${spy_bh_eq.iloc[-1]:,.0f}")
    c3.metric("Final Value (SSO Buy & Hold)", f"${sso_bh_eq.iloc[-1]:,.0f}" if sso_bh_eq.notna().any() else "n/a")
    c4.metric("Final Value (UPRO Buy & Hold)", f"${upro_bh_eq.iloc[-1]:,.0f}" if upro_bh_eq.notna().any() else "n/a")

    # ---- CAGRs
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("CAGR (Synthetic)", f"{m['cagr_synthetic']*100:,.1f}%")
    c6.metric("CAGR (SPY Buy & Hold)", f"{spy_cagr*100:,.1f}%" if pd.notna(spy_cagr) else "n/a")
    c7.metric("CAGR (SSO Buy & Hold)", f"{sso_cagr*100:,.1f}%" if pd.notna(sso_cagr) else "n/a")
    c8.metric("CAGR (UPRO Buy & Hold)", f"{upro_cagr*100:,.1f}%" if pd.notna(upro_cagr) else "n/a")

    # ---- Risk / margin diagnostics (UPDATED: add SSO + UPRO max drawdowns)
    c9, c10, c11, c12 = st.columns(4)
    c9.metric("Max Drawdown (Synthetic)", f"{m['max_dd_synthetic']*100:,.1f}%")
    c10.metric("Max Drawdown (SPY Buy & Hold)", f"{spy_dd*100:,.1f}%" if pd.notna(spy_dd) else "n/a")
    c11.metric("Max Drawdown (SSO Buy & Hold)", f"{sso_dd*100:,.1f}%" if pd.notna(sso_dd) else "n/a")
    c12.metric("Max Drawdown (UPRO Buy & Hold)", f"{upro_dd*100:,.1f}%" if pd.notna(upro_dd) else "n/a")

    c13, c14, c15 = st.columns(3)
    c13.metric("Peak Margin Requirement (Synthetic)", f"${m['peak_margin_req']:,.0f}")
    c14.metric("Max Additional Capital Required (Synthetic)", f"${m['peak_total_topup']:,.0f}")
    c15.metric("Number of Margin Calls (Synthetic)", f"{margin_calls}")

    if m["liquidated"]:
        st.warning("Liquidation triggered under your settings.")

    # ============================
    # Equity curve comparison chart
    # ============================
    st.subheader("Comparison: Synthetic vs Equal-Cash Buy & Hold (SPY / SSO / UPRO)")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(res.index, res["Synthetic_Equity"], label="Synthetic")
    ax.plot(spy_bh_eq.index, spy_bh_eq.values, label="SPY Buy & Hold")
    if sso_bh_eq.notna().any():
        ax.plot(sso_bh_eq.index, sso_bh_eq.values, label="SSO Buy & Hold (2x)")
    if upro_bh_eq.notna().any():
        ax.plot(upro_bh_eq.index, upro_bh_eq.values, label="UPRO Buy & Hold (3x)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)

    # ============================
    # Margin diagnostics
    # ============================
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
            "SPY %": spy_bh_eq,
            "SSO %": sso_bh_eq,
            "UPRO %": upro_bh_eq,
        }
    ).resample("Y").last()

    yearly_returns = yearly.pct_change().dropna() * 100
    yearly_returns.index = yearly_returns.index.year  # int years

    yearly_tbl = yearly_returns.reset_index()
    first_col = yearly_tbl.columns[0]
    yearly_tbl = yearly_tbl.rename(columns={first_col: "Year"})
    yearly_tbl["Year"] = yearly_tbl["Year"].astype(int).astype(str)

    yearly_tbl["Synthetic vs SPY (pp)"] = yearly_tbl["Synthetic %"] - yearly_tbl["SPY %"]

    styler = (
        yearly_tbl.style.format(
            {
                "Synthetic %": "{:.2f}",
                "SPY %": "{:.2f}",
                "SSO %": "{:.2f}",
                "UPRO %": "{:.2f}",
                "Synthetic vs SPY (pp)": "{:.2f}",
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
