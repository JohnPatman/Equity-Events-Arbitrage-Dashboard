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
st.markdown("""This dashboard tracks upcoming UK dividend events for major blue-chip companies
(HSBC, Unilever, AstraZeneca, GSK, Rio Tinto).

The tool, in order of preference per company:
- reads the **declared** dividend timetable — declaration date, ex-date, pay date and
  amount — from each company's RNS announcement (via dividenddata.co.uk), refreshed by a
  local fetch script and committed to the repo,
- where nothing is declared yet, falls back to an **indicative** next ex-date projected
  from historical payment cadence (clearly flagged),
- and to legacy stored announcements as a last resort.

The **Basis** column shows exactly which of these each row came from.
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

_asof = declared_asof()
if _asof:
    st.caption(f"Declared data last refreshed: {_asof}")

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
        "Rows marked **Declared** are company-announced dates from RNS filings "
        "(via dividenddata.co.uk). Rows marked **Indicative** are projected from "
        "historical payment cadence and are **not** company-declared. Amounts are shown "
        "as declared, in the listing currency — UK listings are typically quoted in pence, "
        "and some (e.g. HSBC) declare in USD with a sterling equivalent."
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
