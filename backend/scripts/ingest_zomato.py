"""
scripts/ingest_zomato.py
========================
Phase 1 — Data Ingestion & Catalog

Loads the Zomato restaurant dataset from Hugging Face, cleans and normalizes it,
then saves a structured Parquet file to data/processed/restaurants.parquet.

Schema output:
    id            : int    — auto-generated row index
    name          : str    — restaurant name
    location      : str    — normalized city/location string
    cuisines      : list   — list of cuisine strings
    rating        : float  — aggregate numeric rating (0.0-5.0)
    cost_for_two  : float  — estimated cost for two people (INR)
    budget        : str    — tier: 'low' | 'medium' | 'high'

Budget tiers:
    < 500    → low
    500-1500 → medium
    > 1500   → high

Usage:
    python scripts/ingest_zomato.py [--output data/processed/restaurants.parquet]
"""

import argparse
import logging
import re
import sys
import uuid
from pathlib import Path

import pandas as pd

# ─── Logging Setup ────────────────────────────────────────────────────────────
# Force UTF-8 on the stream handler so Windows cp1252 terminals don't choke
_stream_handler = logging.StreamHandler(sys.stdout)
_stream_handler.stream.reconfigure(encoding="utf-8", errors="replace")  # Python 3.7+

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        _stream_handler,
        logging.FileHandler("data/ingestion.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ─── Constants ─────────────────────────────────────────────────────────────────
DATASET_REPO = "ManikaSaini/zomato-restaurant-recommendation"
BUDGET_LOW_MAX = 500
BUDGET_MED_MAX = 1500

# Possible column name variants from Hugging Face dataset
COLUMN_MAP = {
    "name": ["name", "restaurant_name", "Name", "Restaurant Name"],
    "location": ["location", "Location", "city", "City", "area", "Area"],
    "cuisines": ["cuisines", "Cuisines", "cuisine", "Cuisine"],
    "rating": ["rate", "Rate", "rating", "Rating", "aggregate_rating"],
    "cost_for_two": [
        "approx_cost(for two people)",
        "cost for two",
        "cost",
        "Cost",
        "avg_cost",
        "average_cost_for_two",
    ],
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def resolve_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the first candidate column name that exists in the DataFrame."""
    for col in candidates:
        if col in df.columns:
            return col
    return None


def clean_rating(value) -> float | None:
    """
    Convert a raw rating value to a float.
    Handles strings like '4.1/5', '4.1 /5', 'NEW', '-', etc.
    """
    if pd.isna(value):
        return None
    s = str(value).strip()
    # Remove '/5' suffix if present
    s = re.sub(r"\s*/\s*5.*", "", s)
    try:
        rating = float(s)
        # Zomato ratings are 0–5; reject anything outside that range
        return rating if 0.0 <= rating <= 5.0 else None
    except ValueError:
        return None


def clean_cost(value) -> float | None:
    """
    Convert a raw cost string to a float.
    Handles commas, currency symbols, etc. (e.g., '1,200', '₹800', '$15').
    """
    if pd.isna(value):
        return None
    s = str(value).strip()
    # Strip non-numeric chars except decimal point
    s = re.sub(r"[^\d.]", "", s)
    try:
        return float(s) if s else None
    except ValueError:
        return None


def clean_cuisines(value) -> list[str]:
    """
    Convert a raw cuisines string into a normalized list.
    Input can be comma-separated: 'North Indian, Chinese, Biryani'
    """
    if pd.isna(value):
        return []
    s = str(value).strip()
    if not s:
        return []
    parts = [c.strip().title() for c in s.split(",") if c.strip()]
    return parts


def normalize_location(value) -> str | None:
    """
    Normalize location string: strip whitespace, title-case.
    """
    if pd.isna(value):
        return None
    s = str(value).strip()
    # Remove commas and extra spaces, title-case
    s = re.sub(r"\s+", " ", s).title()
    return s if s else None


def assign_budget(cost: float | None) -> str | None:
    """
    Assign budget tier based on cost:
        < 500    → 'low'
        500–1500 → 'medium'
        > 1500   → 'high'
    """
    if cost is None or pd.isna(cost):
        return None
    if cost < BUDGET_LOW_MAX:
        return "low"
    elif cost <= BUDGET_MED_MAX:
        return "medium"
    else:
        return "high"


# ─── Core Functions ────────────────────────────────────────────────────────────

def load_dataset() -> pd.DataFrame:
    """Download and convert the HuggingFace dataset to a pandas DataFrame."""
    logger.info(f"Loading dataset: {DATASET_REPO}")
    try:
        from datasets import load_dataset as hf_load_dataset
    except ImportError:
        logger.error("The 'datasets' library is not installed. Run: pip install datasets")
        sys.exit(1)

    ds = hf_load_dataset(DATASET_REPO, trust_remote_code=True)
    # Use the first available split (usually 'train')
    split_name = list(ds.keys())[0]
    logger.info(f"Using split: '{split_name}' with {len(ds[split_name])} rows")
    df = ds[split_name].to_pandas()
    logger.info(f"Raw columns: {list(df.columns)}")
    logger.info(f"Raw shape:   {df.shape}")
    return df


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map raw columns → canonical schema, clean data, compute derived fields.
    Returns a clean DataFrame with the canonical schema.
    """
    logger.info("Starting transformation...")

    clean = pd.DataFrame()

    # ── name ──────────────────────────────────────────────────────────────────
    name_col = resolve_column(df, COLUMN_MAP["name"])
    if name_col:
        clean["name"] = df[name_col].astype(str).str.strip()
        logger.info(f"  name <- '{name_col}'")
    else:
        logger.warning("  name column NOT found; filling with 'Unknown'")
        clean["name"] = "Unknown"

    # ── location ──────────────────────────────────────────────────────────────
    location_col = resolve_column(df, COLUMN_MAP["location"])
    if location_col:
        clean["location"] = df[location_col].apply(normalize_location)
        logger.info(f"  location <- '{location_col}'")
    else:
        logger.warning("  location column NOT found; filling with None")
        clean["location"] = None

    # ── cuisines ──────────────────────────────────────────────────────────────
    cuisines_col = resolve_column(df, COLUMN_MAP["cuisines"])
    if cuisines_col:
        clean["cuisines"] = df[cuisines_col].apply(clean_cuisines)
        logger.info(f"  cuisines <- '{cuisines_col}'")
    else:
        logger.warning("  cuisines column NOT found; filling with []")
        clean["cuisines"] = [[] for _ in range(len(df))]

    # ── rating ────────────────────────────────────────────────────────────────
    rating_col = resolve_column(df, COLUMN_MAP["rating"])
    if rating_col:
        clean["rating"] = df[rating_col].apply(clean_rating).astype("Float64")
        logger.info(f"  rating <- '{rating_col}'")
    else:
        logger.warning("  rating column NOT found; filling with NaN")
        clean["rating"] = pd.NA

    # ── cost_for_two ──────────────────────────────────────────────────────────
    cost_col = resolve_column(df, COLUMN_MAP["cost_for_two"])
    if cost_col:
        clean["cost_for_two"] = df[cost_col].apply(clean_cost).astype("Float64")
        logger.info(f"  cost_for_two <- '{cost_col}'")
    else:
        logger.warning("  cost_for_two column NOT found; filling with NaN")
        clean["cost_for_two"] = pd.NA

    # ── budget (derived) ──────────────────────────────────────────────────────
    clean["budget"] = clean["cost_for_two"].apply(assign_budget)
    logger.info("  budget <- derived from cost_for_two")

    # ── id (generated) ────────────────────────────────────────────────────────
    clean.insert(0, "id", range(1, len(clean) + 1))
    logger.info(f"  id <- auto-generated (1 to {len(clean)})")

    logger.info(f"Transformation complete. Shape: {clean.shape}")
    return clean


def validate(df: pd.DataFrame) -> None:
    """
    Run validation checks on the clean DataFrame and log a quality report.
    Raises ValueError if critical checks fail.
    """
    logger.info("Running validation checks...")

    errors = []
    warnings = []

    # ── Critical: non-empty ───────────────────────────────────────────────────
    if len(df) == 0:
        errors.append("Dataset is empty after transformation.")

    # ── id uniqueness ─────────────────────────────────────────────────────────
    if df["id"].nunique() != len(df):
        errors.append("Duplicate IDs detected.")

    # ── Column existence ──────────────────────────────────────────────────────
    expected_cols = {"id", "name", "location", "cuisines", "rating", "cost_for_two", "budget"}
    missing_cols = expected_cols - set(df.columns)
    if missing_cols:
        errors.append(f"Missing expected columns: {missing_cols}")

    # ── Nullability checks ────────────────────────────────────────────────────
    null_rates = df.isnull().mean() * 100
    for col, pct in null_rates.items():
        if pct > 50:
            warnings.append(f"Column '{col}' has {pct:.1f}% null values.")

    # ── Rating range ──────────────────────────────────────────────────────────
    if "rating" in df.columns:
        out_of_range = df["rating"].dropna()
        out_of_range = out_of_range[(out_of_range < 0) | (out_of_range > 5)]
        if len(out_of_range) > 0:
            warnings.append(f"{len(out_of_range)} rows have rating outside [0, 5].")

    # ── Budget coverage ───────────────────────────────────────────────────────
    if "budget" in df.columns:
        budget_na = df["budget"].isna().sum()
        budget_counts = df["budget"].value_counts()
        logger.info(f"  Budget distribution: {budget_counts.to_dict()}")
        if budget_na > len(df) * 0.5:
            warnings.append(f"{budget_na} rows have no budget tier (cost data missing).")

    # ── Cuisines coverage ─────────────────────────────────────────────────────
    if "cuisines" in df.columns:
        empty_cuisines = df["cuisines"].apply(lambda x: len(x) == 0).sum()
        if empty_cuisines > len(df) * 0.3:
            warnings.append(f"{empty_cuisines} rows have empty cuisines list.")

    # ── Report ────────────────────────────────────────────────────────────────
    logger.info("-" * 60)
    logger.info("VALIDATION REPORT")
    logger.info("-" * 60)
    logger.info(f"  Total rows     : {len(df)}")
    logger.info(f"  Total columns  : {len(df.columns)}")
    logger.info(f"  Columns        : {list(df.columns)}")
    logger.info(f"  Null rates (%) :\n{null_rates.round(2).to_string()}")

    for w in warnings:
        logger.warning(f"  [WARN] {w}")
    for e in errors:
        logger.error(f"  [FAIL] {e}")

    if errors:
        raise ValueError(f"Validation failed with {len(errors)} error(s). See log above.")

    logger.info(f"  [OK] Validation passed with {len(warnings)} warning(s).")
    logger.info("-" * 60)


def save_parquet(df: pd.DataFrame, output_path: Path) -> None:
    """Save the clean DataFrame to a Parquet file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False, engine="pyarrow")
    size_kb = output_path.stat().st_size / 1024
    logger.info(f"Saved -> {output_path}  ({size_kb:.1f} KB, {len(df)} rows)")


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

def main():
    # Force stdout to use UTF-8
    sys.stdout.reconfigure(encoding='utf-8')
    
    parser = argparse.ArgumentParser(
        description="Phase 1: Ingest and clean the Zomato restaurant dataset."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/processed/restaurants.parquet",
        help="Output path for the Parquet file (default: data/processed/restaurants.parquet)",
    )
    args = parser.parse_args()
    output_path = Path(args.output)

    logger.info("=" * 60)
    logger.info("PHASE 1 — Data Ingestion & Catalog")
    logger.info("=" * 60)

    # Step 1: Load
    raw_df = load_dataset()

    # Step 2: Transform
    clean_df = transform(raw_df)

    # Step 3: Validate
    validate(clean_df)

    # Step 4: Save
    save_parquet(clean_df, output_path)

    logger.info("=" * 60)
    logger.info("Phase 1 complete [OK]")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
