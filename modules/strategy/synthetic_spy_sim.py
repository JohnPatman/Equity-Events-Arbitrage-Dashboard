from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Tuple

import pandas as pd


TopUpMode = Literal["topup", "liquidate"]


@dataclass
class SimParams:
    initial_cash: float = 30000.0
    contracts: int = 1
    contract_multiplier: int = 100

    # broker-style approximation: margin requirement as % of notional
    margin_pct: float = 0.25

    # fallback annualized risk-free rate (decimal) if no dynamic series supplied
    rf_rate_annual: float = 0.045

    # roll frequency in months
    roll_months: int = 6

    # annual dividend drag (synthetic doesn't receive dividends)
    dividend_yield_drag_annual: float = 0.012  # ~1.2% default

    # margin breach handling
    topup_mode: TopUpMode = "topup"

    # optional cap on total top-ups; if exceeded -> liquidate
    max_total_topup: Optional[float] = None


def _should_roll(last_roll: pd.Timestamp, now: pd.Timestamp, roll_months: int) -> bool:
    a = last_roll.year * 12 + last_roll.month
    b = now.year * 12 + now.year * 0 + now.month  # explicit; avoids accidental shadowing
    return (b - a) >= roll_months


def _daily_rate_from_annual(annual: float) -> float:
    return (1.0 + annual) ** (1.0 / 365.25) - 1.0


def _daily_rate_from_annual_series(annual_series: pd.Series) -> pd.Series:
    # annual_series is decimal (e.g. 0.045). convert to daily comp factor
    return (1.0 + annual_series) ** (1.0 / 365.25) - 1.0


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def cagr(equity: pd.Series) -> float:
    if len(equity) < 2:
        return 0.0
    start = float(equity.iloc[0])
    end = float(equity.iloc[-1])
    days = (equity.index[-1] - equity.index[0]).days
    years = days / 365.25 if days > 0 else 0.0
    if years <= 0 or start <= 0:
        return 0.0
    return float((end / start) ** (1 / years) - 1)


def simulate_synthetic(
    prices: pd.DataFrame,
    params: SimParams,
    rf_annual_series: Optional[pd.Series] = None,  # decimal annual rate aligned to prices.index
) -> Tuple[pd.DataFrame, dict]:
    """
    Rule-based synthetic SPY simulator:
    - Synthetic long ≈ 100-delta exposure per contract (forward-like)
    - Roll every N months by REALISING P&L into cash, then resetting entry price
    - Margin requirement = margin_pct * notional
    - Interest earned on FREE CASH (equity - margin requirement)
    - Optional dividend drag to reflect missing dividends vs Adj Close
    - If margin breach: top up or liquidate
    - Optional dynamic risk-free rate series (rf_annual_series, decimal annualised)
    """
    df = prices.copy().dropna().sort_index()

    if "Close" not in df.columns:
        raise ValueError("prices must include column 'Close'")
    if "Adj Close" not in df.columns:
        df["Adj Close"] = df["Close"]

    mult = int(params.contract_multiplier)
    contracts = int(params.contracts)

    # daily dividend drag as constant (annual -> daily)
    div_drag_daily = _daily_rate_from_annual(params.dividend_yield_drag_annual)

    # risk-free daily: either dynamic series or constant
    if rf_annual_series is not None:
        rf = rf_annual_series.reindex(df.index).ffill().bfill()
        rf_daily_series = _daily_rate_from_annual_series(rf)
    else:
        rf_daily_const = _daily_rate_from_annual(params.rf_rate_annual)
        rf_daily_series = pd.Series(rf_daily_const, index=df.index)

    cash = float(params.initial_cash)
    total_topup = 0.0
    liquidated = False

    idx = df.index
    last_roll = idx[0]
    entry_price = float(df.loc[last_roll, "Close"])

    # Buy & hold benchmark: invest full initial cash into SPY Adj Close
    bh_shares = params.initial_cash / float(df.loc[idx[0], "Adj Close"])

    rows = []
    peak_single_topup = 0.0

    for i, dt in enumerate(idx):
        px = float(df.loc[dt, "Close"])
        adj = float(df.loc[dt, "Adj Close"])
        rf_daily = float(rf_daily_series.loc[dt])

        # --- Roll: realise P&L, then reset entry price ---
        if i > 0 and _should_roll(last_roll, dt, params.roll_months):
            pnl_to_realise = (px - entry_price) * contracts * mult
            cash += pnl_to_realise
            entry_price = px
            last_roll = dt

        notional = px * contracts * mult
        margin_req = params.margin_pct * notional

        # P&L since last roll
        pnl = (px - entry_price) * contracts * mult

        # Apply dividend drag as cash outflow (optional)
        cash -= notional * div_drag_daily

        equity = cash + pnl

        # Conservative interest: only on free cash above margin requirement
        free_cash = max(0.0, equity - margin_req)
        cash += free_cash * rf_daily
        equity = cash + pnl

        # Margin breach
        if equity < margin_req:
            shortfall = margin_req - equity

            if params.topup_mode == "topup":
                cash += shortfall
                total_topup += shortfall
                peak_single_topup = max(peak_single_topup, shortfall)

                if params.max_total_topup is not None and total_topup > params.max_total_topup:
                    liquidated = True
            else:
                liquidated = True

        if liquidated:
            # freeze equity from here forward (assume position closed)
            equity = cash
            rows.append(
                {
                    "Date": dt,
                    "SPY_Close": px,
                    "Synthetic_Equity": equity,
                    "Synthetic_Notional": notional,
                    "Margin_Req": margin_req,
                    "Free_Cash": 0.0,
                    "Total_Topup": total_topup,
                    "Liquidated": True,
                    "BuyHold_Equity": bh_shares * adj,
                    "RF_Annual": float((rf_annual_series.loc[dt] if rf_annual_series is not None else params.rf_rate_annual)),
                }
            )
            for dt2 in idx[i + 1 :]:
                px2 = float(df.loc[dt2, "Close"])
                adj2 = float(df.loc[dt2, "Adj Close"])
                rows.append(
                    {
                        "Date": dt2,
                        "SPY_Close": px2,
                        "Synthetic_Equity": equity,
                        "Synthetic_Notional": px2 * contracts * mult,
                        "Margin_Req": params.margin_pct * px2 * contracts * mult,
                        "Free_Cash": 0.0,
                        "Total_Topup": total_topup,
                        "Liquidated": True,
                        "BuyHold_Equity": bh_shares * adj2,
                        "RF_Annual": float((rf_annual_series.loc[dt2] if rf_annual_series is not None else params.rf_rate_annual)),
                    }
                )
            break

        rows.append(
            {
                "Date": dt,
                "SPY_Close": px,
                "Synthetic_Equity": equity,
                "Synthetic_Notional": notional,
                "Margin_Req": margin_req,
                "Free_Cash": free_cash,
                "Total_Topup": total_topup,
                "Liquidated": False,
                "BuyHold_Equity": bh_shares * adj,
                "RF_Annual": float((rf_annual_series.loc[dt] if rf_annual_series is not None else params.rf_rate_annual)),
            }
        )

    res = pd.DataFrame(rows).set_index("Date")

    metrics = {
        "final_synthetic_equity": float(res["Synthetic_Equity"].iloc[-1]),
        "final_buyhold_equity": float(res["BuyHold_Equity"].iloc[-1]),
        "cagr_synthetic": cagr(res["Synthetic_Equity"]),
        "cagr_buyhold": cagr(res["BuyHold_Equity"]),
        "max_dd_synthetic": max_drawdown(res["Synthetic_Equity"]),
        "max_dd_buyhold": max_drawdown(res["BuyHold_Equity"]),
        "peak_margin_req": float(res["Margin_Req"].max()),
        "peak_total_topup": float(res["Total_Topup"].max()),
        "peak_single_topup": float(peak_single_topup),
        "liquidated": bool(res["Liquidated"].any()),
    }

    return res, metrics
