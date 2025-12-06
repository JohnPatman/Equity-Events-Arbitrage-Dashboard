import pandas as pd

SRC = "Data/history_ulvr.csv"          # full 1999–2025 dataset
OUT = "Data/history_ulvr_2010_2025.csv"

df = pd.read_csv(SRC)

# Convert Pay Date to datetime (ensures proper filtering)
df["Pay Date"] = pd.to_datetime(df["Pay Date"], errors="coerce")

# Filter Date Range → 2010 Jan 1 + keep future 2025 Q3 included
trimmed = df[df["Pay Date"].dt.year >= 2010].reset_index(drop=True)

# Save clean trimmed dataset
trimmed.to_csv(OUT, index=False)

print(f"🔥 Saved → {OUT}")
print(trimmed.tail(10))   # preview last few rows
