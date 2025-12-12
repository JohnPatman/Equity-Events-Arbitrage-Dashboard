from modules.macro.load_macro import load_fred
import pandas as pd

def load_us_inflation():
    headline = load_fred("CPIAUCSL")      # US CPI
    core = load_fred("CPILFESL")          # US Core CPI
    return headline, core

def load_uk_inflation():
    uk = load_fred("GBRCPIALLMINMEI")     # UK CPI index (monthly)
    return uk

def classify_inflation(latest_cpi_yoy):
    if latest_cpi_yoy < 2:
        return "Disinflation"
    elif latest_cpi_yoy < 4:
        return "Normalising"
    else:
        return "High Inflation"
