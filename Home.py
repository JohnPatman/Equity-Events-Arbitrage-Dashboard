import streamlit as st

st.markdown("""
<style>
[data-testid="stHeader"] {
    background-color: #000000 !important;
}
</style>
""", unsafe_allow_html=True)

from modules.theme import apply_bloomberg_theme

st.set_page_config(
        page_title="Equity Events & Arbitrage Dashboard",
        page_icon="📊",
        layout="wide"
)

apply_bloomberg_theme()

st.title("Equity Events & Arbitrage Dashboard")
st.write("""

Use the sidebar on the left to navigate through the tools:
- **Scrip Arbitrage**
- **Dividend Growth Model**
- **Currency Arbitrage**
- **ADR Arbitrage**
- **Earnings Intelligence**
- **Upcoming Popular UK Dividends**
- **Global Equity Valuation**
- **Country Exposure with a Mix of Funds**
- **Macro Signals**
- **Synthetic SPY Simulator**

Each module is now fully separated for clarity, maintainability, and performance.

This homepage is intentionally simple — it's the central landing screen for the dashboard.
""")

st.info("Select a tool from the sidebar to begin.")