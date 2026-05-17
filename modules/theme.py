import streamlit as st

BLOOMBERG_CSS = """
<style>
/* ============================================================
   Bloomberg Terminal Theme — Equity Events Arbitrage Dashboard
   ============================================================ */

@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap');

/* ---- Root / Body ---- */
html, body, [class*="css"] {
    font-family: 'IBM Plex Mono', 'Courier New', monospace !important;
    background-color: #000000 !important;
    color: #FF8C00 !important;
}

.stApp {
    background-color: #000000 !important;
}

/* ---- Hide header bar ---- */
[data-testid="stHeader"] {
    background-color: #000000 !important;
    display: none !important;
}

/* ---- Sidebar ---- */
[data-testid="stSidebar"] {
    background-color: #0A0A0A !important;
    border-right: 1px solid #FF8C00 !important;
}
[data-testid="stSidebar"] * {
    color: #FF8C00 !important;
    font-family: 'IBM Plex Mono', monospace !important;
}
[data-testid="stSidebarNavLink"] {
    color: #FF8C00 !important;
    border-left: 2px solid transparent !important;
    padding: 4px 8px !important;
}
[data-testid="stSidebarNavLink"]:hover,
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background-color: #1A0A00 !important;
    border-left: 2px solid #FF8C00 !important;
    color: #FFB347 !important;
}

/* ---- Headings ---- */
h1, h2, h3, h4, h5, h6 {
    font-family: 'IBM Plex Mono', monospace !important;
    color: #FFB347 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    border-bottom: 1px solid #FF8C00 !important;
    padding-bottom: 4px !important;
}

/* ---- Paragraph and body text — warm white ---- */
.stMarkdown p,
div[data-testid="stMarkdownContainer"] p {
    color: #E8E0D0 !important;
    -webkit-text-fill-color: #E8E0D0 !important;
}

/* ---- List items — warm white ---- */
.stMarkdown li,
div[data-testid="stMarkdownContainer"] li,
ul li, ol li {
    color: #E8E0D0 !important;
    -webkit-text-fill-color: #E8E0D0 !important;
}

/* ---- Sidebar nav items stay orange ---- */
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] a,
[data-testid="stSidebar"] .stMarkdown li {
    color: #FF8C00 !important;
    -webkit-text-fill-color: #FF8C00 !important;
}

/* ---- Widget labels stay orange ---- */
label p,
[data-testid="stWidgetLabel"] p {
    color: #FF8C00 !important;
    -webkit-text-fill-color: #FF8C00 !important;
}

/* ---- Alert / info box text ---- */
[data-testid="stAlert"] p,
[data-testid="stAlertContainer"] p {
    color: #E8E0D0 !important;
    -webkit-text-fill-color: #E8E0D0 !important;
}

/* ---- Metrics ---- */
[data-testid="stMetric"] {
    background-color: #0D0D00 !important;
    border: 1px solid #FF8C00 !important;
    border-radius: 0px !important;
    padding: 8px 12px !important;
}
[data-testid="stMetricLabel"] {
    color: #888 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
}
[data-testid="stMetricValue"] {
    color: #00FF41 !important;
    font-size: 1.4rem !important;
    font-weight: 600 !important;
}
[data-testid="stMetricDelta"] svg { display: none; }
[data-testid="stMetricDelta"] { color: #00FF41 !important; }

/* ---- Dataframes / Tables ---- */
[data-testid="stDataFrame"] { border: 1px solid #FF8C00 !important; }
th {
    background-color: #1A0A00 !important;
    color: #FF8C00 !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    font-size: 0.75rem !important;
    border-bottom: 1px solid #FF8C00 !important;
}
td {
    color: #00FF41 !important;
    background-color: #050500 !important;
    font-size: 0.8rem !important;
    border-bottom: 1px solid #1A1A00 !important;
}
tr:hover td {
    background-color: #1A0A00 !important;
    color: #FFB347 !important;
}

/* ---- Buttons ---- */
.stButton > button {
    background-color: #000000 !important;
    color: #FF8C00 !important;
    border: 1px solid #FF8C00 !important;
    border-radius: 0px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    font-weight: 600 !important;
    padding: 6px 16px !important;
}
.stButton > button:hover {
    background-color: #FF8C00 !important;
    color: #000000 !important;
    border-color: #FF8C00 !important;
}

/* ---- Input boxes — dark background ---- */
div[data-baseweb="base-input"] {
    background-color: #1A1A0E !important;
    border-color: #B8860B !important;
}
div[data-baseweb="base-input"] input {
    background-color: #1A1A0E !important;
    color: #FF8C00 !important;
    -webkit-text-fill-color: #FF8C00 !important;
    caret-color: #FF8C00 !important;
}
div[data-baseweb="input"] {
    background-color: #1A1A0E !important;
}
.stNumberInput input,
.stTextInput input,
input[type="number"],
input[type="text"] {
    background-color: #1A1A0E !important;
    color: #FF8C00 !important;
    border: 1px solid #B8860B !important;
    -webkit-text-fill-color: #FF8C00 !important;
}
input[type="number"]:focus,
input[type="text"]:focus {
    background-color: #1A1A0E !important;
    color: #FF8C00 !important;
    -webkit-text-fill-color: #FF8C00 !important;
    box-shadow: 0 0 0 2px #B8860B !important;
    outline: none !important;
}
textarea {
    background-color: #1A1A0E !important;
    color: #FF8C00 !important;
    border-color: #B8860B !important;
}

/* ---- Dropdowns / Select boxes ---- */
.stSelectbox select,
div[data-baseweb="select"] > div,
div[data-baseweb="select"] > div > div,
div[data-baseweb="select"] input {
    background-color: #1A1A0E !important;
    color: #FF8C00 !important;
    border: 1px solid #B8860B !important;
}
[data-baseweb="select"] * { background-color: #1A1A0E !important; color: #FF8C00 !important; }
div[data-baseweb="popover"] { background-color: #1A1A0E !important; }
li[role="option"] { background-color: #1A1A0E !important; color: #FF8C00 !important; }
li[role="option"]:hover { background-color: #2A2A1E !important; }

/* ---- Date inputs ---- */
[data-testid="stDateInput"] input,
div[data-baseweb="datepicker"] input,
div[data-baseweb="calendar"] {
    background-color: #1A1A0E !important;
    color: #FF8C00 !important;
    border: 1px solid #B8860B !important;
    border-radius: 0px !important;
    font-family: 'IBM Plex Mono', monospace !important;
}

/* ---- Checkboxes ---- */
[data-testid="stCheckbox"] label { color: #FF8C00 !important; }
[data-baseweb="checkbox"],
[data-testid="stCheckbox"] span[role="checkbox"] {
    background-color: #0D0D00 !important;
    border: 2px solid #FF8C00 !important;
    border-radius: 0px !important;
}

/* ---- Sliders ---- */
[data-testid="stSlider"] [role="slider"] { background-color: #FF8C00 !important; }
[data-testid="stSlider"] [class*="Track"] { background-color: #333300 !important; }
div[data-testid="stSlider"] div[role="slider"] { background-color: #FF8C00 !important; }

/* ---- Alerts ---- */
[data-testid="stAlert"],
[data-testid="stAlertContainer"],
[data-baseweb="notification"],
div[role="alert"],
.stAlert {
    background-color: #0D0D00 !important;
    border: 1px solid #FF8C00 !important;
    border-radius: 0px !important;
    color: #FF8C00 !important;
    font-family: 'IBM Plex Mono', monospace !important;
}
[data-testid="stAlert"] *,
[data-testid="stAlertContainer"] *,
[data-baseweb="notification"] * {
    color: #FF8C00 !important;
    background-color: transparent !important;
}

/* ---- Expanders ---- */
[data-testid="stExpander"] {
    border: 1px solid #FF8C00 !important;
    border-radius: 0px !important;
    background-color: #050500 !important;
}
[data-testid="stExpander"] summary {
    color: #FF8C00 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    text-transform: uppercase !important;
}
[data-testid="stExpander"] > div { background-color: #050500 !important; }

/* ---- Tabs ---- */
[data-testid="stTab"] {
    color: #555 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    border-bottom: 2px solid transparent !important;
}
[data-testid="stTab"][aria-selected="true"] {
    color: #FF8C00 !important;
    border-bottom: 2px solid #FF8C00 !important;
}

/* ---- Scrollbars ---- */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: #FF8C00; }
::-webkit-scrollbar-thumb:hover { background: #FFB347; }

/* ---- Hide Streamlit branding ---- */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stToolbar"] { visibility: hidden; }

</style>
"""

def apply_bloomberg_theme():
    """Inject Bloomberg Terminal CSS into the Streamlit app."""
    st.markdown(BLOOMBERG_CSS, unsafe_allow_html=True)
