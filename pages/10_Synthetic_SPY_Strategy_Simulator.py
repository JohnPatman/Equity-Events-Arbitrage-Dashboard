import datetime as dt
import time
from typing import Optional, List, Dict, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import yfinance as yf

from modules.strategy.synthetic_spy_sim import SimParams, simulate_synthetic

st.set_page_config(page_title="Synthetic SPY Strategy Simulator", layout="wide")

# ============================
# Option net-debit table (your screenshot)
# ============================
# Interpreted as: net debit ($) to establish ~100-delta synthetic at that tenor,
# measured at some reference SPY price (e.g. SPY=689.56 in your screenshot).
DEFAULT_NET_DEBIT_TABLE: Dict[int, float] = {
    3: 747.0,
    6: 1232.0,
    12: 1745.0,
    27: 2794.0,
}

DEFAULT_TABLE_SPY_PRICE = 689.56  # from your screenshot


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

### Caveats & Modelling Assumptions
This simulator models economic exposure, not traded option P&L. The synthetic position is treated as a
continuously maintained forward-like exposure with ≈100 delta per contract. Option pricing dynamics such as
implied volatility changes, skew, gamma, theta decay paths, early exercise risk, and liquidity constraints are
not explicitly modelled. Instead, option costs are represented via an annualised carry rate, derived from
user-supplied net-debit snapshots by tenor and interpolated for the chosen roll frequency.

Net-debit carry is applied continuously to notional and should be interpreted as a proxy for financing, dividends,
and structural option costs rather than realised trading fills. Longer roll tenors reduce effective annual carry
in line with the observed term structure, but assume stable parity relationships over time. Margin requirements are
stylised and broker-agnostic; forced deleveraging, widening margin schedules, and volatility-driven margin shocks are
approximated via stress rules rather than broker-specific formulas.

Results are therefore directionally informative rather than prescriptive. The simulator is designed to compare
capital efficiency, drawdown behaviour, and survivability across synthetic exposure, unlevered equity, and
daily-reset leveraged ETFs — not to predict real-world execution outcomes.
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

        roll_months = st.selectbox(
            "Roll Frequency (Months)",
            [3, 6, 9, 12, 15, 18, 21, 24, 27],
            index=1,  # default 6 months
        )

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
                help="Synthetic doesn’t receive dividends (unless your net debit already prices this in).",
            )
            / 100.0
        )

    # ---- Extra realism controls
    colA, colB, colC = st.columns(3)
    with colA:
        roll_cost_bps = st.slider(
            "Roll friction (bps of notional per roll)",
            0.0,
            25.0,
            5.0,
            0.5,
            help="Applied at each roll date as a cost: Notional × (bps/10,000).",
        )
    with colB:
        parity_net_debit = st.checkbox(
            "Net debit already reflects dividends/rates (put–call parity) → disable dividend drag",
            value=True,
        )
    with colC:
        use_net_debit_carry = st.checkbox(
            "Apply option net-debit carry curve (your table) → roll frequency affects total return",
            value=True,
            help="Converts your net debits into an annualised carry rate by tenor, interpolates for the selected roll, and applies it daily to notional.",
        )

    with st.expander("Option net-debit curve (editable)", expanded=False):
        st.caption(
            "These are your snapshot net debits ($) for ~100-delta synthetic at each tenor, "
            "taken at some reference SPY price (e.g. your screenshot shows SPY≈689.56). "
            "We convert $ debits → % of notional at that reference price, then annualise as: (debit_pct / years), "
            "then interpolate between tenors."
        )

        table_spy_price = st.number_input(
            "SPY price used for this net-debit table (reference spot)",
            value=float(DEFAULT_TABLE_SPY_PRICE),
            step=0.01,
            help="Important: your $ net debits depend on spot level. We scale them as % of notional at this reference SPY price.",
        )

        nd_3 = st.number_input("Net debit ($) for 3 months", value=float(DEFAULT_NET_DEBIT_TABLE[3]), step=1.0)
        nd_6 = st.number_input("Net debit ($) for 6 months", value=float(DEFAULT_NET_DEBIT_TABLE[6]), step=1.0)
        nd_12 = st.number_input("Net debit ($) for 12 months", value=float(DEFAULT_NET_DEBIT_TABLE[12]), step=1.0)
        nd_27 = st.number_input("Net debit ($) for 27 months", value=float(DEFAULT_NET_DEBIT_TABLE[27]), step=1.0)
        net_debit_table = {3: float(nd_3), 6: float(nd_6), 12: float(nd_12), 27: float(nd_27)}

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
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df


def _first_scalar(x) -> float:
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


def _clamp_end_date(end_date: dt.date) -> dt.date:
    today = dt.date.today()
    return min(end_date, today)


def _yf_download_retry(
    ticker: str,
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
    period: Optional[str] = None,
    attempts: int = 3,
) -> pd.DataFrame:
    for i in range(attempts):
        try:
            if period is not None:
                df = yf.download(
                    ticker,
                    period=period,
                    auto_adjust=False,
                    progress=False,
                    threads=False,
                )
            else:
                df = yf.download(
                    ticker,
                    start=start_date,
                    end=end_date,
                    auto_adjust=False,
                    progress=False,
                    threads=False,
                )

            df = _flatten_yf_columns(df)
            if not df.empty:
                return df
        except Exception:
            pass

        time.sleep(0.8 * (i + 1))

    return pd.DataFrame()


def _roll_dates(index: pd.DatetimeIndex, roll_months: int) -> List[pd.Timestamp]:
    if index.empty:
        return []
    start_ts = pd.Timestamp(index[0]).normalize()
    end_ts = pd.Timestamp(index[-1]).normalize()

    targets = []
    k = 1
    while True:
        t = start_ts + pd.DateOffset(months=int(roll_months) * k)
        if t > end_ts:
            break
        targets.append(t)
        k += 1

    roll_days = []
    for t in targets:
        pos = index.searchsorted(t, side="left")
        if pos < len(index):
            roll_days.append(index[pos])

    return sorted(set(roll_days))


def _annualised_carry_from_table(
    roll_months: int,
    net_debit_table_months: Dict[int, float],
    table_spy_price: float,
    contracts: int,
    multiplier: int = 100,
) -> Tuple[float, pd.DataFrame]:
    """
    Convert net debit table into annualised carry rates, then interpolate
    an annual carry for the chosen roll_months.

    CRITICAL: The $ debits are measured at a reference spot (table_spy_price).
    So we convert: debit_pct = debit_$ / (table_spy_price * 100 * contracts)
    Then annualise: annual_carry(T) ≈ debit_pct / years
    """
    ref_notional = float(table_spy_price) * float(multiplier) * float(contracts)
    if ref_notional <= 0:
        return 0.0, pd.DataFrame()

    rows = []
    for mths, debit in sorted(net_debit_table_months.items()):
        T = float(mths) / 12.0
        if T <= 0:
            continue
        debit_pct = float(debit) / ref_notional
        annual_carry = debit_pct / T
        rows.append(
            {
                "Months": int(mths),
                "Years": T,
                "NetDebit_$": float(debit),
                "Debit_%Notional": debit_pct,
                "AnnualCarry": annual_carry,
            }
        )

    curve = pd.DataFrame(rows).sort_values("Months")
    if curve.empty:
        return 0.0, curve

    x = curve["Months"].astype(float).values
    y = curve["AnnualCarry"].astype(float).values

    # Clamp + linear interpolate
    rm = float(roll_months)
    if rm <= x.min():
        r = float(y[x.argmin()])
    elif rm >= x.max():
        r = float(y[x.argmax()])
    else:
        r = float(pd.Series(y, index=x).reindex(sorted(set(list(x) + [rm]))).interpolate().loc[rm])

    return r, curve


# ============================
# Data loaders (ROBUST)
# ============================
@st.cache_data(show_spinner=False)
def load_spy(start_date: dt.date, end_date: dt.date) -> pd.DataFrame:
    end_date = _clamp_end_date(end_date)

    df = _yf_download_retry("SPY", start_date=start_date, end_date=end_date, period=None, attempts=3)

    if df.empty:
        df = _yf_download_retry("SPY", period="max", attempts=3)
        if not df.empty:
            df = df.loc[(df.index.date >= start_date) & (df.index.date <= end_date)]

    if df.empty:
        return pd.DataFrame()

    cols = [c for c in ["Close", "Adj Close"] if c in df.columns]
    if not cols:
        return pd.DataFrame()

    out = df[cols].dropna()

    for col in cols:
        if isinstance(out[col], pd.DataFrame):
            out[col] = out[col].iloc[:, 0]

    return out


@st.cache_data(show_spinner=False)
def load_irx(start_date: dt.date, end_date: dt.date) -> pd.Series:
    end_date = _clamp_end_date(end_date)

    df = _yf_download_retry("^IRX", start_date=start_date, end_date=end_date, period=None, attempts=3)

    if df.empty:
        df = _yf_download_retry("^IRX", period="max", attempts=3)
        if not df.empty:
            df = df.loc[(df.index.date >= start_date) & (df.index.date <= end_date)]

    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)

    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    irx_dec = close.astype(float) / 100.0
    irx_dec.name = "RF_Annual"
    return irx_dec


@st.cache_data(show_spinner=False)
def load_benchmark_adjclose(ticker: str, start_date: dt.date, end_date: dt.date) -> pd.Series:
    end_date = _clamp_end_date(end_date)

    df = _yf_download_retry(ticker, start_date=start_date, end_date=end_date, period=None, attempts=3)

    if df.empty:
        df = _yf_download_retry(ticker, period="max", attempts=3)
        if not df.empty:
            df = df.loc[(df.index.date >= start_date) & (df.index.date <= end_date)]

    if df.empty or "Adj Close" not in df.columns:
        return pd.Series(dtype=float, name=ticker)

    adj = df["Adj Close"]
    if isinstance(adj, pd.DataFrame):
        adj = adj.iloc[:, 0]

    adj = adj.dropna().astype(float)
    adj.name = ticker
    return adj


# ============================
# Run simulation
# ============================
if run:
    end = _clamp_end_date(end)

    if start >= end:
        st.error("Start date must be before end date.")
        st.stop()

    # If net debit already reflects dividends/rates, don't double-penalise with dividend drag.
    div_drag_eff = 0.0 if parity_net_debit else float(div_drag)
    if parity_net_debit and float(div_drag) != 0.0:
        st.info("Dividend drag disabled because you marked the net debit as parity-consistent (avoid double-counting).")

    with st.spinner("Downloading SPY data..."):
        prices = load_spy(start, end)

    if prices.empty:
        st.error(
            "No SPY data returned.\n\n"
            "On Streamlit Cloud this can happen if Yahoo blocks/rate-limits the shared IP. "
            "Try again in a minute, or use a shorter date range. "
            "If it keeps happening, the durable fix is to serve prices from cached CSVs."
        )
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
    # Initial margin feasibility check (broker-style)
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
        dividend_yield_drag_annual=float(div_drag_eff),
        topup_mode=topup_mode,
        max_total_topup=float(max_total_topup) if max_total_topup is not None else None,
    )

    # Core synthetic (as your module defines it)
    res, m = simulate_synthetic(prices, params, rf_annual_series=rf_series)
    res = res.copy()

    # ============================
    # Roll friction (bps of notional per roll)
    # ============================
    roll_bps = float(roll_cost_bps)
    roll_cost_rate = roll_bps / 10_000.0

    roll_days = _roll_dates(res.index, int(roll_months))
    res["Roll_Cost"] = 0.0
    if roll_cost_rate > 0 and roll_days:
        roll_notional = res.loc[roll_days, "Synthetic_Notional"].astype(float)
        res.loc[roll_days, "Roll_Cost"] = (roll_notional * roll_cost_rate).values
    res["Cum_Roll_Cost"] = res["Roll_Cost"].cumsum()

    # ============================
    # ✅ OPTION B: Net-debit carry curve (FIXED scaling)
    # ============================
    res["Option_Carry_Cost"] = 0.0
    res["Cum_Option_Carry_Cost"] = 0.0
    carry_r_annual = 0.0
    carry_curve = pd.DataFrame()

    if use_net_debit_carry:
        carry_r_annual, carry_curve = _annualised_carry_from_table(
            roll_months=int(roll_months),
            net_debit_table_months=net_debit_table,
            table_spy_price=float(table_spy_price),   # ✅ FIX: use reference spot from your table
            contracts=int(contracts),
            multiplier=contract_multiplier,
        )

        # Day fractions (actual calendar days)
        day_frac = (
            res.index.to_series()
            .diff()
            .dt.total_seconds()
            .div(365.25 * 24 * 3600)
            .fillna(0.0)
        )

        # Cost applied continuously on notional
        res["Option_Carry_Cost"] = res["Synthetic_Notional"].astype(float) * float(carry_r_annual) * day_frac.values
        res["Cum_Option_Carry_Cost"] = res["Option_Carry_Cost"].cumsum()

    # Net equity after both roll friction and option carry
    res["Synthetic_Equity_Net"] = (
        res["Synthetic_Equity"]
        - res["Cum_Roll_Cost"]
        - res["Cum_Option_Carry_Cost"]
    )

    syn_final_net = float(res["Synthetic_Equity_Net"].iloc[-1])
    syn_cagr_net = _cagr_from_equity(res["Synthetic_Equity_Net"])
    syn_dd_net = _max_drawdown(res["Synthetic_Equity_Net"])

    # ============================
    # Benchmarks: SPY / SSO / UPRO
    # ============================
    with st.spinner("Downloading benchmark ETFs (SPY / SSO / UPRO)..."):
        spy_adj = load_benchmark_adjclose("SPY", start, end)
        sso_adj = load_benchmark_adjclose("SSO", start, end)
        upro_adj = load_benchmark_adjclose("UPRO", start, end)

    idx = res.index
    spy_adj = spy_adj.reindex(idx).ffill().bfill()
    sso_adj = sso_adj.reindex(idx).ffill().bfill()
    upro_adj = upro_adj.reindex(idx).ffill().bfill()

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
    # Margin calls + largest call
    # ============================
    if "Total_Topup" in res.columns:
        topup_changes = res["Total_Topup"].diff().fillna(0.0)
        margin_calls = int((topup_changes > 0).sum())
        largest_margin_call = float(topup_changes[topup_changes > 0].max()) if (topup_changes > 0).any() else 0.0
    else:
        margin_calls = 0
        largest_margin_call = 0.0

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
    c1.metric("Final Value (Synthetic, net)", f"${syn_final_net:,.0f}")
    c2.metric("Final Value (SPY Buy & Hold)", f"${spy_bh_eq.iloc[-1]:,.0f}")
    c3.metric("Final Value (SSO Buy & Hold)", f"${sso_bh_eq.iloc[-1]:,.0f}" if sso_bh_eq.notna().any() else "n/a")
    c4.metric("Final Value (UPRO Buy & Hold)", f"${upro_bh_eq.iloc[-1]:,.0f}" if upro_bh_eq.notna().any() else "n/a")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("CAGR (Synthetic, net)", f"{syn_cagr_net*100:,.1f}%" if pd.notna(syn_cagr_net) else "n/a")
    c6.metric("CAGR (SPY Buy & Hold)", f"{spy_cagr*100:,.1f}%" if pd.notna(spy_cagr) else "n/a")
    c7.metric("CAGR (SSO Buy & Hold)", f"{sso_cagr*100:,.1f}%" if pd.notna(sso_cagr) else "n/a")
    c8.metric("CAGR (UPRO Buy & Hold)", f"{upro_cagr*100:,.1f}%" if pd.notna(upro_cagr) else "n/a")

    c9, c10, c11, c12 = st.columns(4)
    c9.metric("Max Drawdown (Synthetic, net)", f"{syn_dd_net*100:,.1f}%" if pd.notna(syn_dd_net) else "n/a")
    c10.metric("Max Drawdown (SPY Buy & Hold)", f"{spy_dd*100:,.1f}%" if pd.notna(spy_dd) else "n/a")
    c11.metric("Max Drawdown (SSO Buy & Hold)", f"{sso_dd*100:,.1f}%" if pd.notna(sso_dd) else "n/a")
    c12.metric("Max Drawdown (UPRO Buy & Hold)", f"{upro_dd*100:,.1f}%" if pd.notna(upro_dd) else "n/a")

    c13, c14, c15, c16 = st.columns(4)
    c13.metric("Peak Margin Requirement (Synthetic)", f"${m['peak_margin_req']:,.0f}")
    c14.metric("Max Additional Capital Required (Synthetic)", f"${m['peak_total_topup']:,.0f}")
    c15.metric("Number of Margin Calls (Synthetic)", f"{margin_calls}")
    c16.metric("Largest Single Margin Call", f"${largest_margin_call:,.0f}")

    # Disclosures: roll + option carry
    if roll_bps > 0:
        total_roll_cost = float(res["Cum_Roll_Cost"].iloc[-1])
        st.caption(
            f"Roll friction: {roll_bps:.1f} bps per roll | Roll events: {len(roll_days)} | Total roll cost: ${total_roll_cost:,.0f}"
        )

    if use_net_debit_carry:
        total_opt_carry = float(res["Cum_Option_Carry_Cost"].iloc[-1])
        st.caption(
            f"Option net-debit carry (annualised, interpolated): {carry_r_annual*100:.2f}%/yr | "
            f"Total option carry cost: ${total_opt_carry:,.0f} | "
            f"Table spot used: SPY={float(table_spy_price):.2f}"
        )
        if not carry_curve.empty:
            with st.expander("Implied carry curve from your net-debit table", expanded=False):
                curve_show = carry_curve.copy()
                curve_show["Debit_%Notional"] = curve_show["Debit_%Notional"] * 100
                curve_show["AnnualCarry"] = curve_show["AnnualCarry"] * 100
                st.dataframe(
                    curve_show.rename(
                        columns={
                            "NetDebit_$": "NetDebit ($)",
                            "Debit_%Notional": "Debit (% of notional @ table spot)",
                            "AnnualCarry": "Implied annual carry (%)",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

    if m.get("liquidated", False):
        st.warning("Liquidation triggered under your settings.")

    st.subheader("Comparison: Synthetic vs Equal-Cash Buy & Hold (SPY / SSO / UPRO)")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(res.index, res["Synthetic_Equity_Net"], label="Synthetic (net)")
    ax.plot(spy_bh_eq.index, spy_bh_eq.values, label="SPY Buy & Hold")
    if sso_bh_eq.notna().any():
        ax.plot(sso_bh_eq.index, sso_bh_eq.values, label="SSO Buy & Hold (2x)")
    if upro_bh_eq.notna().any():
        ax.plot(upro_bh_eq.index, upro_bh_eq.values, label="UPRO Buy & Hold (3x)")
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

    st.subheader("Year-by-Year Returns (%)")
    yearly = pd.DataFrame(
        {
            "Synthetic (net) %": res["Synthetic_Equity_Net"],
            "SPY %": spy_bh_eq,
            "SSO %": sso_bh_eq,
            "UPRO %": upro_bh_eq,
        }
    ).resample("Y").last()

    yearly_returns = yearly.pct_change().dropna() * 100
    yearly_returns.index = yearly_returns.index.year

    yearly_tbl = yearly_returns.reset_index()
    first_col = yearly_tbl.columns[0]
    yearly_tbl = yearly_tbl.rename(columns={first_col: "Year"})
    yearly_tbl["Year"] = yearly_tbl["Year"].astype(int).astype(str)
    yearly_tbl["Synthetic vs SPY (pp)"] = yearly_tbl["Synthetic (net) %"] - yearly_tbl["SPY %"]

    styler = (
        yearly_tbl.style.format(
            {
                "Synthetic (net) %": "{:.2f}",
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
