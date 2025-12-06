import pandas as pd

# -----------------------------
# Load MSCI data (CSV file)
# -----------------------------
def load_msci_data():
    return pd.read_csv("Data/msci_fundamentals.csv")


# -----------------------------
# Valuation Scoring Function
# -----------------------------
def valuation_score(row):
    pe = row["PE"]
    pb = row["PB"]
    dy = row["DivYld"]

    # ---- NORMALISE DIVIDEND YIELD ----
    # MSCI data comes as % numbers (e.g., 3.21 means 3.21%)
    # Convert all yields > 1 into decimal form
    if pd.notna(dy):
        if dy > 1:        # 3.21 → 0.0321
            dy = dy / 100
        if dy > 0.5:      # 0.92 → 0.0092 (fix Argentina etc.)
            dy = dy / 100

    components = []

    # ---- P/E contribution ----
    if pd.notna(pe) and pe > 0:
        pe_score = min((pe / 25) * 100, 100)
        components.append((pe_score, 0.4))

    # ---- P/B contribution ----
    if pd.notna(pb) and pb > 0:
        pb_score = min((pb / 5) * 100, 100)
        components.append((pb_score, 0.4))

    # ---- Dividend Yield (cheap = low score) ----
    if pd.notna(dy) and dy > 0:
        dy_score = min((1 - dy / 0.05) * 100, 100)
        components.append((dy_score, 0.2))

    # If nothing available
    if not components:
        return None

    # Weighted average score
    total_weight = sum(w for _, w in components)
    score = sum(s * (w / total_weight) for s, w in components)

    return round(score)


# -----------------------------
# Verdict Labeling
# -----------------------------
def verdict_label(score):
    if score is None:
        return "No Data"
    if score <= 25: return f"{score} (Very Cheap)"
    if score <= 40: return f"{score} (Cheap)"
    if score <= 60: return f"{score} (Fair Value)"
    if score <= 80: return f"{score} (Expensive)"
    return f"{score} (Very Expensive)"


# -----------------------------
# Build full valuation table
# -----------------------------
def build_global_valuation_table():
    df = load_msci_data()

    df["Score"] = df.apply(valuation_score, axis=1)
    df["Verdict"] = df["Score"].apply(verdict_label)

    # Sort cheapest → expensive
    df = df.sort_values("Score", na_position="last")

    return df
