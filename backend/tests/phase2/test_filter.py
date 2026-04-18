"""
tests/phase2/test_filter.py
===========================
Phase 2 — Deterministic Filtering Engine Tests

Validates the logic in src/restaurant_rec/phase2/filter.py.

Tests:
    1. test_valid_filter        — basic valid filter returns <= 40 results
    2. test_high_rating_filter  — high min_rating returns fewer results
    3. test_invalid_location    — non-existent location returns empty DF
    4. test_cuisine_filter      — all returned rows match the cuisine
    5. test_budget_filter       — all returned rows match the budget tier
    6. test_empty_result_handling — unrealistic filter combo returns empty DF safely

Run:
    pytest tests/phase2/ -v -s
"""

import pytest
import pandas as pd

from restaurant_rec.catalog import load_catalog
from restaurant_rec.phase2 import UserPreferences, filter_restaurants, MAX_RESULTS


# ─── Session-scoped Fixture ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def catalog() -> pd.DataFrame:
    """Load the Parquet catalog once for the whole Phase 2 test session."""
    df = load_catalog()
    assert not df.empty, "Catalog is empty. Cannot run tests."
    return df


# ─── Tests ────────────────────────────────────────────────────────────────────

def test_valid_filter(catalog: pd.DataFrame):
    """
    Input: valid location, cuisine, rating, budget
    Expect: result is NOT empty, result length <= 40
    """
    prefs = UserPreferences(
        location="Btm",         # Valid area
        cuisine="North Indian", # Very common
        min_rating=3.0,
        budget="medium"
    )
    
    result = filter_restaurants(catalog, prefs)
    
    print(f"\n  [test_valid_filter] Shortlist size: {len(result)}")
    
    assert not result.empty, "Expected valid filter to return results."
    assert len(result) <= MAX_RESULTS, f"Result size {len(result)} exceeds max {MAX_RESULTS}."
    
    # Optional sanity check: rating order
    ratings = result["rating"].astype(float).tolist()
    assert ratings == sorted(ratings, reverse=True), "Results are not sorted by rating descending."


def test_high_rating_filter(catalog: pd.DataFrame):
    """
    Input: min_rating = 4.5+
    Expect: result size smaller than normal filter
    """
    prefs_normal = UserPreferences(
        location="Indiranagar",
        cuisine="Chinese",
        min_rating=3.0,
        budget="medium"
    )
    result_normal = filter_restaurants(catalog, prefs_normal)
    
    prefs_high = UserPreferences(
        location="Indiranagar",
        cuisine="Chinese",
        min_rating=4.5,
        budget="medium"
    )
    result_high = filter_restaurants(catalog, prefs_high)
    
    print(f"\n  [test_high_rating_filter] Normal shortlist size: {len(result_normal)}")
    print(f"  [test_high_rating_filter] High rating shortlist size: {len(result_high)}")
    
    assert len(result_high) < len(result_normal) or len(result_high) == 0, (
        "High rating filter should reduce result size or yield 0 results."
    )
    if not result_high.empty:
        assert all(result_high["rating"].astype(float) >= 4.5), "Found ratings < 4.5."


def test_invalid_location(catalog: pd.DataFrame):
    """
    Input: location = "InvalidCityXYZ"
    Expect: result is empty DataFrame
    """
    prefs = UserPreferences(
        location="InvalidCityXYZ",
        cuisine="Chinese",
        min_rating=3.0,
        budget="medium"
    )
    
    result = filter_restaurants(catalog, prefs)
    
    print(f"\n  [test_invalid_location] Shortlist size: {len(result)}")
    
    assert result.empty, "Expected empty result for invalid location."
    assert set(result.columns) == set(catalog.columns), "Empty result should maintain schema."


def test_cuisine_filter(catalog: pd.DataFrame):
    """
    Input: cuisine = "Chinese"
    Expect: all results contain Chinese cuisine
    """
    query_cuisine = "Chinese"
    prefs = UserPreferences(
        location="Btm",
        cuisine=query_cuisine,
        min_rating=3.0,
        budget="low"
    )
    
    result = filter_restaurants(catalog, prefs)
    
    print(f"\n  [test_cuisine_filter] Shortlist size: {len(result)}")
    assert not result.empty, "Expected some Asian/Chinese restaurants in Btm with low budget."
    
    # Verify every row has roughly the string "chinese" in its cuisine list
    for idx, row in result.iterrows():
        c_str = str(row["cuisines"]).lower()
        assert query_cuisine.lower() in c_str, f"Row {idx} missing '{query_cuisine}': {c_str}"


def test_budget_filter(catalog: pd.DataFrame):
    """
    Input: budget = "low"
    Expect: all results have budget = low
    """
    prefs = UserPreferences(
        location="Koramangala",
        cuisine="Cafe",
        min_rating=3.0,
        budget="low"
    )
    
    result = filter_restaurants(catalog, prefs)
    
    print(f"\n  [test_budget_filter] Shortlist size: {len(result)}")
    
    if not result.empty:
        # All rows must be 'low'
        unique_budgets = result["budget"].unique()
        assert len(unique_budgets) == 1, f"Expected only 1 budget tier, got: {unique_budgets}"
        assert unique_budgets[0] == "low", f"Expected 'low' budget, got: {unique_budgets[0]}"


def test_empty_result_handling(catalog: pd.DataFrame):
    """
    Input: unrealistic filters (high rating + rare cuisine)
    Expect: empty DataFrame, no crash
    """
    prefs = UserPreferences(
        location="Btm",
        cuisine="Ethiopian or Something Rare",
        min_rating=4.9,
        budget="low"
    )
    
    # Should not crash
    result = filter_restaurants(catalog, prefs)
    
    print(f"\n  [test_empty_result_handling] Shortlist size: {len(result)}")
    
    assert result.empty, "Expected an empty DataFrame for unrealistic criteria."
    assert len(result.columns) == len(catalog.columns), "Schema must be maintained on empty return."
