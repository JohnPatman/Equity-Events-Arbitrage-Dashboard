import os
import pandas as pd

# Ensure Data folder exists
os.makedirs("Data", exist_ok=True)

# ==============================
# 1. Load individual company data
# ==============================

files = [
    "Data/upcoming_hsbc.csv",
    "Data/upcoming_ulvr.csv",
    # More to come...
]

frames = []

for f in files:
    if os.path.exists(f):
        df = pd.read_csv(f)
        frames.append(df)
        print(f"📄 Loaded: {f}")
    else:
        print(f"⚠ Missing file: {f}")

# ==============================
# 2. Combine results & sort
# ==============================

if not frames:
    print("\n❌ No dividend files found. Run company scrapers first.")
    exit()

merged = pd.concat(frames, ignore_index=True)

# Convert Pay Date → datetime then sort
merged["Pay Date"] = pd.to_datetime(merged["Pay Date"], errors="coerce")
merged = merged.dropna(subset=["Pay Date"])
merged = merged.sort_values(by="Pay Date")

# Save final dataset
output_file = "Data/dividends_upcoming.csv"
merged.to_csv(output_file, index=False)

print("\n🎉 Successfully generated combined upcoming dividend file!")
print(f"💾 Saved → {output_file}\n")

print(merged.head(20))
