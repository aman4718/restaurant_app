"""
src/restaurant_rec/phase2/filter.py
=====================================
Phase 2 — Deterministic Filtering Engine

Core function:
    filter_restaurants(df, preferences) -> pd.DataFrame

Pipeline
--------
1. Location   — case-insensitive substring match on `location`
2. Cuisine    — case-insensitive any-match inside the `cuisines` list
3. Rating     — rating >= preferences.min_rating  (NaN rows always dropped)
4. Budget     — exact match on `budget` tier string
5. Sort       — by rating descending (NaN last)
6. Cap        — return top MAX_RESULTS rows

The function never raises on an empty mid-pipeline result; it returns an
empty DataFrame with the full schema so callers can check len(result) == 0.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from .preferences import UserPreferences

logger = logging.getLogger(__name__)

# Maximum number of restaurants returned to the LLM shortlist
MAX_RESULTS: int = 40


# ─── Cuisine helper ───────────────────────────────────────────────────────────

def _cuisine_matches(cuisines_value, query: str) -> bool:
    """
    Return True if `query` appears (case-insensitively) in the cuisines list.

    The parquet `cuisines` column stores numpy object arrays, plain Python
    lists, or occasionally bare strings — this function handles all three.

    Parameters
    ----------
    cuisines_value : any
        A single cell from the `cuisines` column.
    query : str
        The cuisine the user is searching for (e.g. "chinese").
    """
    query_lower = query.lower()

    # numpy array (most common after read_parquet)
    if isinstance(cuisines_value, np.ndarray):
        return any(query_lower in str(c).lower() for c in cuisines_value)

    # plain Python list
    if isinstance(cuisines_value, list):
        return any(query_lower in str(c).lower() for c in cuisines_value)

    # fallback: treat cell as a plain string
    return query_lower in str(cuisines_value).lower()


# ─── Main filter function ────────────────────────────────────────────────────

def filter_restaurants(
    df: pd.DataFrame,
    preferences: "UserPreferences",
) -> pd.DataFrame:
    """
    Apply deterministic filters to the catalog and return a ranked shortlist.

    Parameters
    ----------
    df : pd.DataFrame
        Full restaurant catalog (output of Phase 1 ingestion).
        Must contain columns: location, cuisines, rating, budget.
    preferences : UserPreferences
        Validated user preferences from Phase 2 Pydantic model.

    Returns
    -------
    pd.DataFrame
        Filtered, sorted DataFrame with at most MAX_RESULTS (40) rows.
        Returns an empty DataFrame (same schema) if no matches are found.
        The original index is reset (0-based) in the output.

    Notes
    -----
    - Rating NaN rows are excluded after the rating filter step.
    - All string comparisons are case-insensitive.
    - The function is pure (does not mutate `df`).
    """
    logger.info("--- Phase 2 Filter Engine ---")
    logger.info("Preferences: %s", preferences.summary())
    logger.info("Catalog size before filtering: %d rows", len(df))

    result = df.copy()

    # ── Step 1: Location filter ──────────────────────────────────────────────
    # Partial, case-insensitive match so "BTM" matches "Btm", "BTM Layout", etc.
    loc_query = preferences.location.lower()
    result = result[
        result["location"]
        .fillna("")
        .str.lower()
        .str.contains(loc_query, regex=False)
    ]
    logger.info("After location  filter ('%s'): %d rows", preferences.location, len(result))

    if result.empty:
        logger.warning("No restaurants found for location: %r", preferences.location)
        return _empty_result(df)

    # ── Step 2: Cuisine filter ───────────────────────────────────────────────
    cuisine_mask = result["cuisines"].apply(
        lambda c: _cuisine_matches(c, preferences.cuisine)
    )
    result = result[cuisine_mask]
    logger.info("After cuisine   filter ('%s'): %d rows", preferences.cuisine, len(result))

    if result.empty:
        logger.warning(
            "No restaurants found for cuisine %r in location %r",
            preferences.cuisine,
            preferences.location,
        )
        return _empty_result(df)

    # ── Step 3: Rating filter ────────────────────────────────────────────────
    # Drop rows with NaN rating first, then apply threshold
    result = result.dropna(subset=["rating"])
    result = result[result["rating"].astype(float) >= preferences.min_rating]
    logger.info(
        "After rating    filter (>= %.1f): %d rows", preferences.min_rating, len(result)
    )

    if result.empty:
        logger.warning(
            "No restaurants with rating >= %.1f for '%s' in '%s'",
            preferences.min_rating,
            preferences.cuisine,
            preferences.location,
        )
        return _empty_result(df)

    # ── Step 4: Budget filter ────────────────────────────────────────────────
    result = result[result["budget"] == preferences.budget]
    logger.info("After budget    filter ('%s'): %d rows", preferences.budget, len(result))

    if result.empty:
        logger.warning(
            "No restaurants with budget=%r remaining after all filters.",
            preferences.budget,
        )
        return _empty_result(df)

    # ── Step 5: Sort by rating descending ────────────────────────────────────
    result = result.sort_values("rating", ascending=False, na_position="last")

    # ── Step 6: Cap at MAX_RESULTS ───────────────────────────────────────────
    result = result.head(MAX_RESULTS).reset_index(drop=True)

    logger.info(
        "Shortlist size: %d (capped at %d)", len(result), MAX_RESULTS
    )
    return result


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _empty_result(df: pd.DataFrame) -> pd.DataFrame:
    """Return an empty DataFrame with the same columns as the catalog."""
    return pd.DataFrame(columns=df.columns).reset_index(drop=True)
