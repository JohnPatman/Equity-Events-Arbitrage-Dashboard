import streamlit as st
st.set_page_config(page_title="Upcoming Popular UK Dividends", layout="wide")
from modules.theme import apply_bloomberg_theme
apply_bloomberg_theme()
import pandas as pd

from modules.dividends.uk_dividends import get_uk_dividend_view, raw_static_extract

st.markdown("""
<style>
div[data-baseweb="base-input"] {
    background-color: #1A1A0E !important;
    border-color: #B8860B !important;
}
div[data-baseweb="base-input"] input {
    background-color: #1A1A0E !important;
    color: #FF8C00 !important;
    -webkit-text-fill-color: #FF8C00 !important;
}
div[data-baseweb="input"] {
    background-color: #1A1A0E !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🔹 Upcoming Popular UK Dividends")
st.markdown("""This dashboard tracks upcoming UK dividend events for major blue-chip companies
(HSBC, Unilever, AstraZeneca, GSK, Rio Tinto).

The tool:
- pulls the most recently declared dividend and historical cadence live from market data,
- shows the next ex-date / pay date where the company has formally declared one,
- projects an **indicative** next ex-date from payment cadence where one hasn't been declared yet (clearly flagged),
- falls back to stored announcements if live data is unavailable.
""")

COMPANIES = {
    "HSBA": "HSBC Holdings",
    "ULVR": "Unilever PLC",
    "AZN":  "AstraZeneca PLC",
    "GSK":  "GSK PLC",
    "RIO":  "Rio Tinto PLC",
}


@st.cache_data(ttl=60 * 60 * 6, show_spinner="Fetching dividend calendar…")
def load_view():
    return get_uk_dividend_view(COMPANIES)


col_a, col_b = st.columns([1, 5])
with col_a:
    if st.button("🔄 Refresh"):
        load_view.clear()

view = load_view()

# ---- Status table ----
st.subheader("Company Dividend Status")

def _status(r):
    if r["Next Pay Date"] != "TBA":
        return f"Next pay {r['Next Pay Date']}"
    if r["Next Ex-Date"] != "TBA":
        return f"Next ex-date {r['Next Ex-Date']}"
    if r["Last Declared"] != "TBA":
        return f"Last paid {r['Last Declared']} ({r['Last Ex-Date']})"
    return "No data"

status_df = view.copy()
status_df["Status"] = status_df.apply(_status, axis=1)
st.dataframe(
    status_df[["Ticker", "Company", "Status", "Basis"]],
    hide_index=True, use_container_width=True,
)

# ---- Forward calendar ----
st.subheader("Upcoming Dividend Calendar")

cal = view[(view["Next Ex-Date"] != "TBA") | (view["Next Pay Date"] != "TBA")].copy()
if not cal.empty:
    st.dataframe(
        cal[["Ticker", "Company", "Last Declared", "Next Ex-Date", "Next Pay Date", "Basis"]],
        hide_index=True, use_container_width=True,
    )
    st.caption(
        "‘Indicative’ rows are projected from historical payment cadence and are **not** "
        "company-declared dates. Amounts shown are the **last declared** dividend in the "
        "listing currency (UK listings are typically quoted in pence; HSBC declares in USD)."
    )
else:
    st.write("No forward dividend dates detected for the tracked names right now.")

# ---- Raw stored extract (legacy CSVs) ----
with st.expander("📥 View stored raw extract (legacy scrape files)"):
    raw = raw_static_extract()
    if not raw.empty:
        st.dataframe(raw, use_container_width=True, height=350)
    else:
        st.write("No stored scrape files found.")
