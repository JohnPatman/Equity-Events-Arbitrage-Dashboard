import streamlit as st
st.set_page_config(page_title="Upcoming Popular UK Dividends", layout="wide")
from modules.theme import apply_bloomberg_theme
apply_bloomberg_theme()
import pandas as pd

from modules.dividends.uk_dividends import get_uk_dividend_view, raw_static_extract, declared_asof

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
st.markdown(
    "Dividend timing for 20 of the largest UK-listed companies. Where a company has "
    "formally announced its next dividend, you get the real dates: when the shares go "
    "ex-dividend and when the cash is paid. Where nothing has been announced yet, the next "
    "ex-date is an estimate based on how often the company has paid in the past, marked so "
    "it's obvious which is which. The Basis column tells you the source for each row."
)

COMPANIES = {
    "HSBA": "HSBC Holdings",
    "ULVR": "Unilever",
    "AZN":  "AstraZeneca",
    "GSK":  "GSK",
    "RIO":  "Rio Tinto",
    "SHEL": "Shell",
    "BP":   "BP",
    "GLEN": "Glencore",
    "BATS": "British American Tobacco",
    "DGE":  "Diageo",
    "LLOY": "Lloyds Banking Group",
    "BARC": "Barclays",
    "NWG":  "NatWest Group",
    "NG":   "National Grid",
    "LGEN": "Legal & General",
    "AAL":  "Anglo American",
    "REL":  "RELX",
    "IMB":  "Imperial Brands",
    "BA":   "BAE Systems",
    "AV":   "Aviva",
}


# Cache keyed on the data file's timestamp: when a freshly-fetched CSV is committed
# (new FetchedAt), the key changes and the view recomputes automatically — no manual
# refresh, and no stale table lingering after a redeploy.
@st.cache_data(ttl=60 * 60 * 6, show_spinner="Loading dividend calendar…")
def load_view(cache_key):
    return get_uk_dividend_view(COMPANIES)


view = load_view(declared_asof() or "none")

# ---- Status table ----
st.subheader("Company Dividend Status")

_asof = declared_asof()
if _asof:
    st.caption(f"Data last refreshed: {_asof}")

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
        "Declared rows are the company's announced dates. Indicative rows are an estimate "
        "from past payment timing, not confirmed dates. Amounts are shown as the company "
        "declared them — usually pence for UK shares, though a few (HSBC, for one) declare "
        "in dollars and show a sterling equivalent."
    )
    st.markdown(
        "<small>Declared data source: "
        "<a href='https://www.dividenddata.co.uk/' target='_blank'>dividenddata.co.uk</a> "
        "(FTSE dividend RNS aggregator)</small>",
        unsafe_allow_html=True,
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
