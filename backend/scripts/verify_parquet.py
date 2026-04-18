import pandas as pd
from pathlib import Path

df = pd.read_parquet("data/processed/restaurants.parquet", engine="pyarrow")

print("=== PHASE 1 — OUTPUT VERIFICATION ===")
print(f"Shape            : {df.shape}")
print(f"Columns          : {list(df.columns)}")
print()
print("--- Dtypes ---")
print(df.dtypes)
print()
print("--- Null Rates (%) ---")
print((df.isnull().mean() * 100).round(2))
print()
print("--- Budget Distribution ---")
print(df["budget"].value_counts())
print()
print("--- Rating Stats ---")
print(df["rating"].describe())
print()
print("--- Top 10 Locations ---")
print(df["location"].value_counts().head(10))
print()
print("--- Sample Rows (first 5) ---")
for _, row in df.head(5).iterrows():
    cuisines_preview = str(row["cuisines"][:2])
    name = str(row["name"])[:40]
    loc = str(row["location"])[:20]
    print(f"  [{row['id']}] {name:40s} | {loc:20s} | rating={row['rating']} | cost={row['cost_for_two']} | budget={row['budget']}")
    print(f"       cuisines: {cuisines_preview}")

print()
file_size = Path("data/processed/restaurants.parquet").stat().st_size / 1024
print(f"File size        : {file_size:.1f} KB")
print("=== VERIFICATION COMPLETE ===")
