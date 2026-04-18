"""
tests/phase1/test_ingestion.py
==============================
Phase 1 — Data Ingestion Tests

Validates the output Parquet catalog produced by scripts/ingest_zomato.py.

Tests:
    1. test_parquet_loads          — file exists and loads without error
    2. test_schema_correct         — all 7 expected columns present, no extras
    3. test_no_null_names          — name column is fully populated
    4. test_location_null_rate     — location nulls < 1%
    5. test_budget_classification  — budget values only in {low, medium, high}
    6. test_budget_tiers_match_cost — budget tier matches raw cost_for_two
    7. test_rating_range           — all non-null ratings are in [0.0, 5.0]
    8. test_cuisines_are_lists     — cuisines column contains list objects
    9. test_row_count              — dataset has at least 1000 rows
   10. test_ids_unique             — id column has no duplicates

Run:
    pytest tests/phase1/ -v
"""

from pathlib import Path
import pandas as pd
import pytest

# ─── Paths ────────────────────────────────────────────────────────────────────
# Allow running from both the repo root and from within tests/
_ROOT = Path(__file__).resolve().parents[2]  # e:\nextleap\zomato-ai
PARQUET_PATH = _ROOT / "data" / "processed" / "restaurants.parquet"

# ─── Expected Schema ──────────────────────────────────────────────────────────
EXPECTED_COLUMNS = {"id", "name", "location", "cuisines", "rating", "cost_for_two", "budget"}
VALID_BUDGETS    = {"low", "medium", "high"}

# Budget tier boundaries (must match ingest_zomato.py)
BUDGET_LOW_MAX = 500
BUDGET_MED_MAX = 1500


# ─── Session-scoped Fixture ───────────────────────────────────────────────────
@pytest.fixture(scope="session")
def catalog() -> pd.DataFrame:
    """Load the Parquet catalog once for the whole test session."""
    if not PARQUET_PATH.exists():
        pytest.skip(
            f"Parquet file not found at {PARQUET_PATH}. "
            "Run: python scripts/ingest_zomato.py"
        )
    df = pd.read_parquet(PARQUET_PATH, engine="pyarrow")

    # ── Print summary header ──────────────────────────────────────────────────
    print("\n")
    print("=" * 60)
    print("PHASE 1 — CATALOG SUMMARY")
    print("=" * 60)
    print(f"  Parquet path   : {PARQUET_PATH}")
    print(f"  Total rows     : {len(df):,}")
    print(f"  Total columns  : {len(df.columns)}")
    print(f"  Columns        : {list(df.columns)}")
    print()
    print("  Budget distribution:")
    for tier, cnt in df["budget"].value_counts().items():
        print(f"    {tier:8s}: {cnt:,}")
    print()
    print("  Null rates (%):")
    for col, rate in (df.isnull().mean() * 100).round(2).items():
        flag = " <-- WARNING" if rate > 5 else ""
        print(f"    {col:15s}: {rate:.2f}%{flag}")
    print()
    print("  Sample 5 records:")
    print("  " + "-" * 90)
    for _, row in df.head(5).iterrows():
        cuisines_str = str(list(row["cuisines"])[:3]).replace("array(", "").replace(", dtype=object)", "")
        print(
            f"  [{row['id']:5d}] "
            f"{str(row['name'])[:35]:35s} | "
            f"{str(row['location'])[:18]:18s} | "
            f"rating={row['rating']} | "
            f"cost={row['cost_for_two']} | "
            f"budget={row['budget']}"
        )
        print(f"          cuisines: {cuisines_str}")
    print("  " + "-" * 90)
    print("=" * 60)
    print()

    return df


# ─── Tests ────────────────────────────────────────────────────────────────────

def test_parquet_loads(catalog):
    """Parquet file loads into a non-empty DataFrame."""
    assert catalog is not None, "Catalog fixture returned None"
    assert isinstance(catalog, pd.DataFrame), "Catalog is not a DataFrame"
    assert len(catalog) > 0, "Catalog DataFrame is empty"
    print(f"\n  [PASS] Loaded {len(catalog):,} rows from Parquet.")


def test_schema_correct(catalog):
    """
    Exact 7-column schema must be present.
    No expected column may be missing.
    """
    actual_cols = set(catalog.columns)
    missing = EXPECTED_COLUMNS - actual_cols

    print(f"\n  Expected columns : {sorted(EXPECTED_COLUMNS)}")
    print(f"  Actual columns   : {sorted(actual_cols)}")

    assert not missing, f"Missing columns in schema: {missing}"
    print(f"  [PASS] All {len(EXPECTED_COLUMNS)} expected columns present.")


def test_no_null_names(catalog):
    """
    'name' column must have 0 null values.
    Every restaurant row must have a name.
    """
    null_count = catalog["name"].isnull().sum()
    print(f"\n  Null names: {null_count}")
    assert null_count == 0, f"Found {null_count} null values in 'name' column"
    print("  [PASS] No null names.")


def test_location_null_rate(catalog):
    """
    'location' nulls should be < 1% of total rows.
    (Some Zomato entries have no location — acceptable up to 1%.)
    """
    null_pct = catalog["location"].isnull().mean() * 100
    print(f"\n  Location null rate: {null_pct:.2f}%")
    assert null_pct < 1.0, (
        f"Location null rate is {null_pct:.2f}% — exceeds 1% threshold"
    )
    print(f"  [PASS] Location null rate {null_pct:.2f}% < 1%.")


def test_budget_classification(catalog):
    """
    'budget' column must only contain valid tier strings.
    Null values (from missing cost) are allowed but every non-null
    budget must be one of: low, medium, high.
    """
    non_null_budgets = catalog["budget"].dropna()
    invalid = set(non_null_budgets.unique()) - VALID_BUDGETS

    dist = catalog["budget"].value_counts(dropna=False).to_dict()
    print(f"\n  Budget distribution: {dist}")
    print(f"  Invalid budget values found: {invalid}")

    assert not invalid, f"Unexpected budget values: {invalid}"
    print(f"  [PASS] All budget values are in {VALID_BUDGETS}.")


def test_budget_tiers_match_cost(catalog):
    """
    Budget tier must agree with the cost_for_two thresholds:
        cost < 500    → 'low'
        500 <= cost <= 1500 → 'medium'
        cost > 1500   → 'high'

    Only checks rows where both cost_for_two and budget are non-null.
    """
    df = catalog.dropna(subset=["cost_for_two", "budget"]).copy()

    def expected_budget(cost):
        if cost < BUDGET_LOW_MAX:
            return "low"
        elif cost <= BUDGET_MED_MAX:
            return "medium"
        else:
            return "high"

    df["expected_budget"] = df["cost_for_two"].apply(expected_budget)
    mismatches = df[df["budget"] != df["expected_budget"]]

    print(f"\n  Rows checked   : {len(df):,}")
    print(f"  Mismatched rows: {len(mismatches)}")

    if len(mismatches) > 0:
        print("  Sample mismatches:")
        for _, row in mismatches.head(3).iterrows():
            print(f"    id={row['id']} cost={row['cost_for_two']} "
                  f"assigned={row['budget']} expected={row['expected_budget']}")

    assert len(mismatches) == 0, (
        f"{len(mismatches)} rows have incorrect budget tier. "
        "Thresholds: low < 500, medium 500-1500, high > 1500"
    )
    print("  [PASS] All budget tiers match cost_for_two thresholds.")


def test_rating_range(catalog):
    """
    All non-null ratings must be within [0.0, 5.0].
    The Zomato scale is 0–5; any value outside is a cleaning bug.
    """
    ratings = catalog["rating"].dropna()
    out_of_range = ratings[(ratings < 0.0) | (ratings > 5.0)]

    print(f"\n  Non-null ratings : {len(ratings):,}")
    print(f"  Out-of-range     : {len(out_of_range)}")
    print(f"  Rating min/max   : {float(ratings.min()):.2f} / {float(ratings.max()):.2f}")
    print(f"  Rating mean      : {float(ratings.mean()):.2f}")

    assert len(out_of_range) == 0, (
        f"{len(out_of_range)} ratings are outside [0.0, 5.0]"
    )
    print("  [PASS] All ratings within valid range [0.0, 5.0].")


def test_cuisines_are_lists(catalog):
    """
    'cuisines' column must contain list-like objects (not raw strings).
    Every row should be iterable with a length.
    """
    sample = catalog["cuisines"].head(200)
    bad_rows = [
        i for i, val in enumerate(sample)
        if not hasattr(val, "__len__")
    ]

    print(f"\n  Sample size for check: {len(sample)}")
    print(f"  Rows where cuisines is not list-like: {len(bad_rows)}")

    if bad_rows:
        print(f"  Examples: {[sample.iloc[i] for i in bad_rows[:3]]}")

    # Also check no cuisines is a plain old string (should be array/list)
    plain_strings = [
        i for i, val in enumerate(sample)
        if isinstance(val, str)
    ]
    print(f"  Rows where cuisines is a plain string: {len(plain_strings)}")

    assert len(bad_rows) == 0, "Some 'cuisines' entries are not list-like"
    assert len(plain_strings) == 0, "Some 'cuisines' entries are plain strings, not lists"
    print("  [PASS] All cuisines entries are list-like.")


def test_row_count(catalog):
    """
    Dataset must have at least 1,000 rows to be usable.
    (Zomato dataset is known to have ~50k+ rows.)
    """
    print(f"\n  Row count: {len(catalog):,}")
    assert len(catalog) >= 1_000, (
        f"Dataset has only {len(catalog)} rows — expected at least 1,000"
    )
    print(f"  [PASS] Row count {len(catalog):,} >= 1,000.")


def test_ids_unique(catalog):
    """
    'id' column must contain no duplicates.
    Auto-generated IDs must be globally unique.
    """
    total   = len(catalog)
    unique  = catalog["id"].nunique()
    dupes   = total - unique

    print(f"\n  Total rows : {total:,}")
    print(f"  Unique IDs : {unique:,}")
    print(f"  Duplicates : {dupes}")

    assert dupes == 0, f"Found {dupes} duplicate IDs in 'id' column"
    print("  [PASS] All IDs are unique.")
