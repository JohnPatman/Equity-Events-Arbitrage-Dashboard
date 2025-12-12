from modules.macro.load_macro import load_fred

YIELD_CODES = {
    "3M": "DGS3MO",
    "2Y": "DGS2",
    "5Y": "DGS5",
    "10Y": "DGS10",
    "30Y": "DGS30",
}

def load_us_yields():
    """Load all key US Treasury yields from FRED."""
    data = {label: load_fred(code) for label, code in YIELD_CODES.items()}
    return data

def latest_value(df):
    return float(df["Value"].iloc[-1])

def compute_slope(df_10y, df_2y):
    """10Y - 2Y slope"""
    return latest_value(df_10y) - latest_value(df_2y)

def classify_curve(slope):
    if slope > 0.50:
        return "Normal"
    elif slope > 0:
        return "Flat"
    else:
        return "Inverted"
