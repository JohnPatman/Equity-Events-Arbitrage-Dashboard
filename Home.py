import streamlit as st

st.set_page_config(
    page_title="Equity Events & Arbitrage Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Equity Events & Arbitrage Dashboard")
st.write("""
Welcome to your analytics hub.

Use the sidebar on the left to navigate through the tools:
- **Upcoming Popular UK Dividends**
- **Dividend Growth Model**
- **Currency Arbitrage**
- **ADR Arbitrage**
- **Earnings Intelligence**
- **Scrip Arbitrage**
- **Global Equity Valuation**

Each module is now fully separated for clarity, maintainability, and performance.

This homepage is intentionally simple — it's the central landing screen for the dashboard.
""")

st.info("Select a tool from the sidebar to begin.")
