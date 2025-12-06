import streamlit as st
import pandas as pd
import yfinance as yf

st.title("🔹 Scrip Dividend Arbitrage (LMP example)")
st.markdown("""This dashboard evaluates the economic value of electing cash vs scrip dividends for LMP.

It provides:
- real-time market price retrieval,
- correct scrip-share calculation using issue price,
- comparison of cash vs scrip economic outcomes,
- optimal election recommendation,
- lender-vs-borrower election analysis.

This dashboard is built for dividend arbitrage practitioners,  
especially those analysing scrip events and non-cash dividend alternatives.
""")

# ======================================================================
# 🔵 UNIVERSAL LIGHT-BLUE INPUT STYLING
# ======================================================================
st.markdown("""
<style>

    /* -------- TEXT INPUT -------- */
    div.stTextInput > div > div > input {
        background-color: #e9f2ff !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        color: #000 !important;
        border-radius: 8px !important;
        border: 1px solid #c7d9ff !important;
        padding: 10px 12px !important;
    }
    div.stTextInput > div > div > input:focus {
        border: 1.5px solid #4c84ff !important;
        box-shadow: 0 0 0 2px rgba(76,132,255,0.25) !important;
    }

    /* -------- NUMBER INPUTS (shares, cash rate, manual price) -------- */
    div[data-baseweb="input"] input {
        background-color: #e9f2ff !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        color: #000 !important;
        border-radius: 8px !important;
        border: 1px solid #c7d9ff !important;
        padding: 8px 10px !important;
    }
    div[data-baseweb="input"] input:focus {
        border: 1.5px solid #4c84ff !important;
        box-shadow: 0 0 0 2px rgba(76,132,255,0.25) !important;
    }

    /* -------- SELECTBOX (Lender elects) FIX: bigger height + padding -------- */
    div[data-baseweb="select"] > div {
        background-color: #e9f2ff !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        color: #000 !important;
        border-radius: 8px !important;
        border: 1px solid #c7d9ff !important;
        padding: 12px !important;              /* larger padding */
        min-height: 48px !important;           /* FIX: ensures text isn't clipped */
        display: flex !important;
        align-items: center !important;        /* vertical centering */
    }

    /* Dropdown menu items (when opened) */
    div[role="listbox"] div {
        font-size: 1.10rem !important;
        font-weight: 600 !important;
    }

</style>
""", unsafe_allow_html=True)


# ======================================================================
# LOAD LATEST SCRIP DIVIDEND DATA
# ======================================================================
try:
    df_scrip = pd.read_csv("Data/lmp_scrip_dividends.csv")
    latest = df_scrip.iloc[0]
except Exception as e:
    st.error(f"Could not load LMP scrip data: {e}")
    st.stop()

quarter = latest["Dividend"]
deadline = latest["Election deadline"]
scrip_price = float(latest["Scrip Calculation Price"])

st.subheader("Latest Scrip Dividend")
st.write(f"**Quarter:** {quarter}")
st.write(f"**Election Deadline:** {deadline}")
st.write(f"**Scrip Issue Price:** {scrip_price:.2f} pence")


# ======================================================================
# FETCH MARKET PRICE (AUTO WITH SPLIT FIX)
# ======================================================================
ticker = "LMP.L"
deadline_dt = pd.to_datetime(deadline, errors="coerce")
market_pence = None

if pd.notna(deadline_dt):
    start = (deadline_dt - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    end   = (deadline_dt + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    data = yf.download(ticker, start=start, end=end, progress=False)

    if not data.empty:
        raw_price_gbp = float(data["Close"].iloc[-1])

        if raw_price_gbp > 20:
            price_gbp = raw_price_gbp / 100.0
        else:
            price_gbp = raw_price_gbp

        market_pence = price_gbp * 100.0

if market_pence:
    st.metric("Market Price (pence)", f"{market_pence:.2f}p")
else:
    st.warning("Could not fetch market price.")


# ======================================================================
# ARBITRAGE CALCULATION
# ======================================================================
st.subheader("🔍 Scrip vs Cash Arbitrage")

shares = st.number_input("Number of shares held", min_value=1, step=100, value=1_000_000)
cash_rate = st.number_input("Cash Dividend Rate (pence)", value=3.05, step=0.01)
manual_price = st.number_input("Manual Override Market Price (optional, pence)", value=0.00, step=0.01)

if manual_price > 0:
    use_price_pence = manual_price
else:
    use_price_pence = market_pence or 0.0

cash_value = cash_rate * shares / 100.0
scrip_shares = int((cash_rate * shares) / scrip_price)
scrip_value = scrip_shares * (use_price_pence / 100.0)

st.metric("Cash Dividend (£)", f"£{cash_value:,.2f}")
st.metric("Scrip Shares Issued", f"{scrip_shares:,}")
st.metric("Scrip Value (£)", f"£{scrip_value:,.2f}")

diff = scrip_value - cash_value
if diff > 0:
    st.success(f"📈 Scrip is richer by **£{diff:,.2f}**")
else:
    st.error(f"📉 Cash is richer by **£{abs(diff):,.2f}**")

# store values for later
st.session_state["lmp_cash_value"] = cash_value
st.session_state["lmp_scrip_shares"] = scrip_shares
st.session_state["lmp_use_price"] = use_price_pence / 100.0


# ======================================================================
# OPTIMAL ELECTION VS LENDER
# ======================================================================
st.subheader("📌 Optimal Election vs Lender Election (Cash vs Scrip)")

required = ["lmp_cash_value", "lmp_scrip_shares", "lmp_use_price"]
if not all(k in st.session_state for k in required):
    st.info("Run the arbitrage section above first.")
else:
    cash_value = st.session_state["lmp_cash_value"]
    scrip_shares = st.session_state["lmp_scrip_shares"]
    use_price_gbp = st.session_state["lmp_use_price"]

    scrip_value = scrip_shares * use_price_gbp

    lender = st.selectbox("Lender elects:", ["Cash", "Scrip"])

    values = {"Cash": cash_value, "Scrip": scrip_value}
    best = max(values, key=values.get)

    advantage = (values[best] / values[lender] - 1) * 100 if values[lender] else 0

    comp_df = pd.DataFrame({
        "Election Option": ["Cash", "Scrip"],
        "Value (£)": [cash_value, scrip_value],
    })
    st.table(comp_df)

    if best == lender:
        st.success(f"✔ Given lender = **{lender}**, best choice is to **match**.")
    else:
        st.warning(
            f"📌 Given lender = **{lender}**, optimal election is **{best}** "
            f"(+{advantage:.2f}% advantage)."
        )

    rel_pct = (scrip_value / cash_value - 1) * 100 if cash_value else 0
    if rel_pct > 0:
        st.info(f"Scrip offers +{rel_pct:.2f}% more value than Cash.")
    else:
        st.info(f"Cash offers +{abs(rel_pct):.2f}% more value than Scrip.")
