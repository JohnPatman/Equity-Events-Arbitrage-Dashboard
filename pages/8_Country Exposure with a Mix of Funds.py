import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from modules.portfolio.hl_scraper import scrape_country_weights

# ----------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------
st.set_page_config(page_title="Country Exposure with a Mix of Funds", layout="wide")

st.title("🔹 Country Exposure with Mix of Funds")

st.markdown("""
This dashboard blends country exposures across multiple fund investments  
based on your custom allocation percentages.

The tool automatically:
- scrapes each fund’s latest published country weights,
- applies your chosen allocation mix,
- aggregates all exposures into a single blended portfolio,
- fills missing exposure with an 'Other' bucket when funds publish only top holdings,
- classifies each country into Developed, Emerging, Frontier, Cash, or Other,
- visualises results using ranked bar charts and market-classification breakdowns.

Use this dashboard to understand portfolio geographic concentration,  
diversification quality, and exposure risks across a range of fund investments.
""")


# ----------------------------------------------------
# FUND LIST — HL URLs
# ----------------------------------------------------
FUNDS = {
    "Fidelity Index World Fund P Acc":
        "https://www.hl.co.uk/funds/fund-discounts,-prices--and--factsheets/search-results/f/fidelity-index-world-class-p-accumulation",

    "Legal & General Global Technology Index Trust (C)":
        "https://www.hl.co.uk/funds/fund-discounts,-prices--and--factsheets/search-results/l/legal-and-general-global-technology-index-trust-c-accumulation",

    "Redwheel Next Generation EM Eq (R Acc GBP)":
        "https://www.hl.co.uk/funds/fund-discounts,-prices--and--factsheets/search-results/r/redwheel-next-generation-emerging-market-eq-r-accumulation",

    "Fidelity China Focus (Class Y – Income GBP)":
        "https://www.hl.co.uk/funds/fund-discounts,-prices--and--factsheets/search-results/f/fidelity-china-focus-gbp-class-y-income",

    "Invesco Emerging Markets ex-China (Class Z Acc)":
        "https://www.hl.co.uk/funds/fund-discounts,-prices--and--factsheets/search-results/i/invesco-emerging-markets-ex-china-class-z-accumulation",

    "Jupiter India Select (Class D GBP Acc)":
        "https://www.hl.co.uk/funds/fund-discounts,-prices--and--factsheets/search-results/j/jupiter-india-select-class-d-gbp-accumulation",

    "Fidelity Japan Class W Acc":
        "https://www.hl.co.uk/funds/fund-discounts,-prices--and--factsheets/search-results/f/fidelity-japan-class-w-accumulation",

    "Fidelity European Class W Acc":
        "https://www.hl.co.uk/funds/fund-discounts,-prices--and--factsheets/search-results/f/fidelity-european-class-w-accumulation",

    "Fidelity Index UK Class P Acc":
        "https://www.hl.co.uk/funds/fund-discounts,-prices--and--factsheets/search-results/f/fidelity-index-uk-class-p-accumulation",
}


# ----------------------------------------------------
# MARKET CLASSIFICATION
# ----------------------------------------------------
DEVELOPED = {
    "United States", "United Kingdom", "Japan", "France", "Germany",
    "Switzerland", "Netherlands", "Ireland", "Canada", "Australia",
    "New Zealand", "Singapore", "Hong Kong", "Sweden",
    "Finland", "Spain", "Italy", "Belgium", "Austria",
    "Denmark", "Norway",
}

EMERGING = {
    "China", "India", "Brazil", "Taiwan", "South Korea", "South Africa",
    "Mexico", "Thailand", "Indonesia", "Malaysia", "Turkey", "Philippines",
    "Poland", "Chile", "Czech Republic", "Hungary", "Qatar",
    "Saudi Arabia", "Kuwait", "United Arab Emirates", "UAE",
}

FRONTIER = {
    "Vietnam", "Pakistan", "Sri Lanka", "Argentina", "Kenya",
    "Kazakhstan", "Bangladesh", "Nigeria", "Romania", "Bahrain",
}


def classify_country(country: str) -> str:
    if country in DEVELOPED:
        return "Developed"
    if country in EMERGING:
        return "Emerging"
    if country in FRONTIER:
        return "Frontier"
    if "Cash" in country:
        return "Cash"
    return "Other"


# ----------------------------------------------------
# STEP 1 — USER ALLOCATION INPUTS
# ----------------------------------------------------
st.subheader("Step 1 — Set your fund allocation (%)")

alloc_cols = st.columns(3)
allocations = {}
total_alloc = 0.0

for i, (name, _) in enumerate(FUNDS.items()):
    with alloc_cols[i % 3]:
        val = st.number_input(
            name,
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=1.0,
            key=f"alloc_{i}",
        )
        allocations[name] = val
        total_alloc += val

st.write(f"**Total entered:** {total_alloc:.2f}%")

# Warnings
if total_alloc < 100:
    st.warning("Your allocations sum to less than 100%. They will be normalised automatically.")
elif total_alloc > 100:
    st.error("Your allocations exceed 100%. They will be normalised automatically.")
else:
    st.success("Perfect — allocations sum to exactly 100%.")

if total_alloc == 0:
    st.stop()

normalised_alloc = {k: v / total_alloc for k, v in allocations.items()}


# ----------------------------------------------------
# SCRAPING (CACHED)
# ----------------------------------------------------
@st.cache_data(show_spinner=False)
def get_fund_countries(url: str) -> pd.DataFrame:
    df = scrape_country_weights(url)
    if df is None or df.empty:
        return pd.DataFrame(columns=["Country", "Weight"])

    df["Weight"] = pd.to_numeric(df["Weight"], errors="coerce").fillna(0.0)

    # --- NEW FIX: Add 'Other' when weights do not sum to 100% ---
    total_w = df["Weight"].sum()
    if total_w < 0.999:  # allow small rounding errors
        df_other = pd.DataFrame({
            "Country": ["Other"],
            "Weight": [1 - total_w]
        })
        df = pd.concat([df, df_other], ignore_index=True)

    return df[["Country", "Weight"]]


# ----------------------------------------------------
# BUILD BLENDED PORTFOLIO
# ----------------------------------------------------
parts = []

for fund_name, url in FUNDS.items():
    alloc_frac = normalised_alloc.get(fund_name, 0.0)
    if alloc_frac == 0:
        continue

    df = get_fund_countries(url)
    if df.empty:
        continue

    df["BlendWeight"] = df["Weight"] * alloc_frac
    parts.append(df[["Country", "BlendWeight"]])

if parts:
    portfolio = pd.concat(parts).groupby("Country", as_index=False)["BlendWeight"].sum()
else:
    portfolio = pd.DataFrame(columns=["Country", "BlendWeight"])

portfolio["WeightPct"] = portfolio["BlendWeight"] * 100
portfolio = portfolio.sort_values("WeightPct", ascending=False).reset_index(drop=True)


# ----------------------------------------------------
# DISPLAY TABLE
# ----------------------------------------------------
st.subheader("Final Blended Portfolio Country Exposure")

table, chart = st.columns([1.1, 1.6])

display_table = portfolio[["Country", "WeightPct"]].copy()
display_table["Weight %"] = display_table["WeightPct"].round(2).map(lambda x: f"{x:.2f}%")
display_table = display_table.drop(columns=["WeightPct"])

with table:
    html = (
        display_table.style
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
        .hide(axis="index")
        .to_html()
    )
    st.markdown(html, unsafe_allow_html=True)


# ----------------------------------------------------
# BAR CHART — largest at top
# ----------------------------------------------------
with chart:
    fig = px.bar(
        portfolio,
        x="WeightPct",
        y="Country",
        orientation="h",
        height=1400,
    )

    fig.update_yaxes(autorange="reversed")

    fig.update_layout(
        title="By Country (sorted, % of portfolio)",
        xaxis_title="Weight (%)",
        yaxis_title="",
        plot_bgcolor="white",
        margin=dict(l=10, r=20, t=60, b=20),
    )
    fig.update_traces(hovertemplate="%{y}: %{x:.2f}%")
    st.plotly_chart(fig, use_container_width=True)


# ----------------------------------------------------
# CLASSIFICATION BREAKDOWN
# ----------------------------------------------------
st.subheader("Market Classification Breakdown")

portfolio["Class"] = portfolio["Country"].apply(classify_country)
class_df = (
    portfolio.groupby("Class", as_index=False)["BlendWeight"]
    .sum()
    .sort_values("BlendWeight", ascending=False)
)
class_df["WeightPct"] = class_df["BlendWeight"] * 100

class_table = class_df[["Class", "WeightPct"]].copy()
class_table["Weight %"] = class_table["WeightPct"].round(2).map(lambda x: f"{x:.2f}%")
class_table = class_table.drop(columns=["WeightPct"])

html2 = (
    class_table.style
    .set_properties(**{"text-align": "center"})
    .set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
    .hide(axis="index")
    .to_html()
)
st.markdown(html2, unsafe_allow_html=True)


# ----------------------------------------------------
# PIE CHART
# ----------------------------------------------------
st.subheader("Market Classification Share")

fig2 = go.Figure(
    data=[
        go.Pie(
            labels=class_df["Class"],
            values=class_df["WeightPct"],
            hole=0.25,
            textinfo="percent",
            hovertemplate="%{label}: %{value:.2f}%",
            sort=False,
        )
    ]
)

fig2.update_layout(
    height=550,
    width=750,
    margin=dict(l=10, r=10, t=40, b=10),
    showlegend=True,
)

st.plotly_chart(fig2, use_container_width=False)
