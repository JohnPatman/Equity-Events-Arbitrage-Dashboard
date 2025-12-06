import streamlit as st
import pandas as pd
from datetime import datetime

from modules.arbitrage.airtel import fetch_airtel_latest
from modules.arbitrage.fx import get_market_fx_usd_gbp

# ======================================================================
# PAGE TITLE & DESCRIPTION
# ======================================================================

st.title("🔹 Dividend FX & Arbitrage (Airtel example)")
st.markdown("""This dashboard evaluates dividend currency arbitrage opportunities for Airtel Africa.

It uses the company’s published USD→GBP FX rate and compares it to live market FX to:
- identify whether GBP or USD is the richer election,
- quantify pure FX arbitrage percentages,
- compute borrow-arbitrage based on lender and recipient elections,
- assess hedged arbitrage using forward FX,
- run P&L sensitivity analysis across a custom FX range.

This dashboard is designed for traders, corporate action specialists,  
and anyone analysing FX-driven dividend events in dual-currency markets.
""")

# ======================================================================
# GLOBAL BLUE INPUT BOX STYLING
# ======================================================================

st.markdown("""
<style>

    /* ------- TEXT INPUTS -------- */
    div.stTextInput > div > div > input {
        background-color: #e9f2ff !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        color: #000 !important;
        border-radius: 8px !important;
        border: 1px solid #c7d9ff !important;
        padding: 10px 12px !important;
    }

    /* ------- NUMBER INPUTS -------- */
    div[data-baseweb="input"] input {
        background-color: #e9f2ff !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        color: #000 !important;
        border-radius: 8px !important;
        border: 1px solid #c7d9ff !important;
        padding: 10px 12px !important;
    }

    /* ------- SELECTBOX -------- */
    div[data-baseweb="select"] > div {
        background-color: #e9f2ff !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        color: #000 !important;
        border-radius: 8px !important;
        border: 1px solid #c7d9ff !important;
        padding: 12px !important;
        min-height: 48px !important;
        display: flex !important;
        align-items: center !important;
    }

</style>
""", unsafe_allow_html=True)


# ======================================================================
# FETCH LATEST COMPANY + MARKET DATA
# ======================================================================

try:
    latest = fetch_airtel_latest()

    fx_company = latest["FX_USD_GBP"]
    usd_div = float(latest["Cents per ordinary share"].split()[0]) / 100.0

    fx_market, fx_date = get_market_fx_usd_gbp()

    arb_pct = (fx_company / fx_market - 1) * 100
    rich_ccy = "GBP" if fx_company > fx_market else ("USD" if fx_company < fx_market else None)
    best_choice = rich_ccy if rich_ccy else "Either (no advantage)"

    # ==================================================================
    # TOP METRICS
    # ==================================================================

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Airtel FX (USD→GBP)", f"{fx_company:.4f}")
    with c2: st.metric("Market FX (USD→GBP)", f"{fx_market:.4f}")
    with c3: st.metric("Arbitrage %", f"{arb_pct:.2f}%")

    st.caption(f"Market FX date: **{fx_date}**")

    if rich_ccy:
        st.success(f"📌 FX advantage detected — elect **{best_choice}**")
    else:
        st.info("⚖ No FX arbitrage detected.")

    # ==================================================================
    # DIVIDEND DETAILS TABLE (NO INDEX, CLEAN WIDTHS)
    # ==================================================================

    st.subheader("Dividend Details")

    def fmt(x):
        try:
            return pd.to_datetime(x, format="%d-%b").strftime("%d/%m")
        except:
            return x

    detail_df = pd.DataFrame({
        "Data": [
            "Announcement",
            "Ex-dividend (LSE)",
            "Record date",
            "Currency election deadline",
            "Payment date",
            "Published FX (USD→GBP)",
            "Dividend per share (USD)",
        ],
        "Value": [
            fmt(latest.get("Announcement date")),
            fmt(latest.get("Ex-dividend date (LSE)")),
            fmt(latest.get("Record date (NGX – settlement date)")),
            fmt(latest.get("Last date to currency election")),
            fmt(latest.get("Payment date")),
            f"{fx_company:.4f}",
            f"{usd_div:.4f}",
        ]
    })

    st.dataframe(
        detail_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Data": st.column_config.Column(width=260),
            "Value": st.column_config.Column(width=160),
        }
    )

    # Store values
    st.session_state["fx_company"] = fx_company
    st.session_state["fx_market"] = fx_market
    st.session_state["usd_div"] = usd_div
    st.session_state["rich_ccy"] = rich_ccy

except Exception as e:
    st.error(f"Failed to load Airtel data: {e}")
    st.stop()


# ======================================================================
# 📦 BORROW–ARBITRAGE
# ======================================================================

st.header("📦 Borrow-Arbitrage (Lender vs Your Election)")

shares = st.number_input("Borrowed Shares", min_value=100, value=1000, step=100)
lender_election = st.selectbox("Lender elects:", ["USD", "GBP"])
your_election = st.selectbox("You elect:", ["USD", "GBP"])

fx_company = st.session_state["fx_company"]
fx_market = st.session_state["fx_market"]
usd_div = st.session_state["usd_div"]
rich_ccy = st.session_state["rich_ccy"]

# Owed
if lender_election == "USD":
    owe_usd = usd_div * shares
    owe_gbp = owe_usd * fx_company
else:
    owe_gbp = usd_div * shares * fx_company
    owe_usd = owe_gbp / fx_market

# Received
if your_election == "USD":
    recv_usd = usd_div * shares
    recv_gbp = recv_usd * fx_company
else:
    recv_gbp = usd_div * shares * fx_company
    recv_usd = recv_gbp / fx_market

# Convert to lender currency
if lender_election == "USD":
    eff = recv_usd if your_election == "USD" else recv_gbp / fx_market
    owe = owe_usd
    sym = "$"
else:
    eff = recv_gbp if your_election == "GBP" else recv_usd * fx_market
    owe = owe_gbp
    sym = "£"

profit = eff - owe

cA, cB, cC = st.columns(3)
with cA: st.metric("Dividend Owed", f"{sym}{owe:,.2f}")
with cB: st.metric("You Receive", f"{sym}{eff:,.2f}")
with cC: st.metric("Profit / Loss", f"{sym}{profit:,.2f}")

if profit > 0:
    st.success(f"📈 Arbitrage Profit: {sym}{profit:,.2f}")
elif profit < 0:
    st.error(f"📉 Loss: {sym}{profit:,.2f}")
else:
    st.info("⚖ Zero arbitrage — identical economics.")


# ======================================================================
# 📌 OPTIMAL ELECTION
# ======================================================================

st.header("📌 Optimal Dividend Currency Election")

if lender_election == "USD":
    elect_usd = usd_div * shares
    elect_gbp = elect_usd * fx_company / fx_market

    if elect_gbp > elect_usd:
        diff = (elect_gbp / elect_usd - 1) * 100
        st.success(f"📈 Given lender = USD → Elect **GBP** (+{diff:.2f}%)")
    else:
        diff = (elect_usd / elect_gbp - 1) * 100
        st.success(f"📈 Given lender = USD → Elect **USD** (+{diff:.2f}%)")

else:
    elect_gbp = usd_div * shares * fx_company
    elect_usd = usd_div * shares * fx_market

    if elect_usd > elect_gbp:
        diff = (elect_usd / elect_gbp - 1) * 100
        st.success(f"📈 Given lender = GBP → Elect **USD** (+{diff:.2f}%)")
    else:
        diff = (elect_gbp / elect_usd - 1) * 100
        st.success(f"📈 Given lender = GBP → Elect **GBP** (+{diff:.2f}%)")


# ======================================================================
# 🔐 FORWARD HEDGE
# ======================================================================

st.header("🔐 Forward Hedge Impact")

if rich_ccy is None:
    st.caption("No FX arbitrage detected — hedge unnecessary.")
else:
    if your_election != rich_ccy or lender_election == your_election:
        st.caption("Forward hedge only relevant when you elect the richer currency and the lender elects the opposite.")
    else:
        forward_fx = st.number_input(
            "Forward FX (USD→GBP)",
            value=float(fx_market),
            step=0.0001,
            format="%.4f"
        )

        if rich_ccy == "GBP" and lender_election == "USD":
            usd_owed = usd_div * shares
            gbp_received = usd_owed * fx_company
            usd_forward = gbp_received / forward_fx
            profit_fwd = usd_forward - usd_owed
            pct = (usd_forward / usd_owed - 1) * 100
            st.metric("Hedged Return %", f"{pct:.2f}%")
            st.write(f"Hedged P&L: **${profit_fwd:,.2f}**")

        elif rich_ccy == "USD" and lender_election == "GBP":
            gbp_owed = usd_div * shares * fx_company
            usd_received = usd_div * shares
            gbp_forward = usd_received * forward_fx
            profit_fwd = gbp_forward - gbp_owed
            pct = (gbp_forward / gbp_owed - 1) * 100
            st.metric("Hedged Return %", f"{pct:.2f}%")
            st.write(f"Hedged P&L: **£{profit_fwd:,.2f}**")


# ======================================================================
# 📈 FX STRESS TEST
# ======================================================================

st.header("📈 Market FX Stress Test")

min_fx = round(fx_market * 0.90, 4)
max_fx = round(fx_market * 1.10, 4)

hypo_fx = st.slider(
    "Hypothetical Market FX (USD→GBP)",
    min_value=float(min_fx),
    max_value=float(max_fx),
    value=float(fx_market),
    step=0.0001,
    format="%.4f"
)

hypo_arb = (fx_company / hypo_fx - 1) * 100

st.write(f"At FX **{hypo_fx:.4f}**, arbitrage = **{hypo_arb:.2f}%**.")
st.info(f"Break-even FX (no arbitrage): **{fx_company:.4f}**")
