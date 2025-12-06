import streamlit as st
import pandas as pd
from modules.arbitrage.adr_arbitrage import (
    tsm_arbitrage,
    baba_arbitrage,
    sony_arbitrage,
    asml_arbitrage,
    azn_arbitrage,
)

st.title("🔹 ADR vs Local Share Arbitrage")
st.markdown("""This dashboard compares ADR prices against their underlying local shares  
to detect cross-market valuation gaps.

For each supported security, the tool:
- fetches ADR price, local price, FX, and ADR ratio,
- converts the local share into USD terms,
- calculates ADR premium or discount,
- provides clear buy/sell arbitrage recommendations.

This dashboard is useful for monitoring market inefficiencies,  
pricing discrepancies, and ADR/local conversion opportunities.
""")

def display_adr_block(name, result):

    adr_price = float(result["adr_price"])
    local_price = float(result["local_price"])
    fx = float(result["fx_local_to_usd"])
    ratio = float(result["ratio"])
    local_equiv = float(result["local_usd_equivalent"])
    arb_pct = float(result["arb_pct"])
    rec = result["recommendation"]

    colA, colB, colC, colD = st.columns(4)

    with colA:
        st.metric(f"{name} ADR Price (USD)", f"${adr_price:.2f}")

    with colB:
        st.metric(f"{name} Local Price", f"{local_price:,.2f}")

    with colC:
        st.metric("FX (Local → USD)", f"{fx:.4f}")

    with colD:
        ratio_disp = str(ratio).rstrip("0").rstrip(".")
        st.metric("ADR Ratio", ratio_disp)

    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Local Value in USD (after ratio)",
            f"${local_equiv:,.2f}"
        )
    with col2:
        st.metric(
            "ADR Premium / Discount",
            f"{arb_pct:.2f}%"
        )

    if arb_pct > 0:
        st.error(f"📉 {rec}")
    elif arb_pct < 0:
        st.success(f"📈 {rec}")
    else:
        st.info("⚖ Fully aligned (no arbitrage).")

    st.divider()

adr_functions = {
    "TSM": tsm_arbitrage,
    "BABA": baba_arbitrage,
    "SONY": sony_arbitrage,
    "ASML": asml_arbitrage,
    "AZN": azn_arbitrage,
}

for name, fn in adr_functions.items():
    try:
        result = fn()
        display_adr_block(name, result)
    except Exception as e:
        st.error(f"{name}: data unavailable — {e}")
