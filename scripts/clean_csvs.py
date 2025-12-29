import pandas as pd
import os

DATA_DIR = "Data/earnings"

def clean_file(path):
    print("Cleaning:", path)
    df = pd.read_csv(path)

    # Drop rows with missing or invalid earnings dates
    df = df.dropna(subset=["Earnings Date"])

    # Convert date
    df["Earnings Date"] = pd.to_datetime(df["Earnings Date"], errors="coerce")

    # Drop failed conversions
    df = df.dropna(subset=["Earnings Date"])

    # Sort properly
    df = df.sort_values("Earnings Date")

    # Reset index
    df = df.reset_index(drop=True)

    df.to_csv(path, index=False)
    print("✔ Cleaned and saved:", path)


def main():
    for f in os.listdir(DATA_DIR):
        if f.endswith(".csv"):
            clean_file(os.path.join(DATA_DIR, f))

    print("\nALL FILES CLEANED SUCCESSFULLY.\n")


if __name__ == "__main__":
    main()
