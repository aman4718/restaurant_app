"""
src/restaurant_rec/catalog.py
==============================
Shared catalog loader for all phases.

Loads the Phase 1 Parquet output into a pandas DataFrame, caching the
result in memory so repeated calls within a process are instant.

Usage
-----
    from restaurant_rec.catalog import load_catalog

    df = load_catalog()          # uses default path
    df = load_catalog("path/to/restaurants.parquet")
"""

from __future__ import annotations

import logging
from pathlib import Path
from functools import lru_cache

import pandas as pd

logger = logging.getLogger(__name__)

# Default path relative to the project root
_DEFAULT_PARQUET = (
    Path(__file__).resolve().parents[2]  # up to e:\nextleap\zomato-ai
    / "data"
    / "processed"
    / "restaurants.parquet"
)


@lru_cache(maxsize=1)
def load_catalog(path: str | None = None) -> pd.DataFrame:
    """
    Load the restaurant catalog Parquet file into a DataFrame.

    The result is cached (LRU) so subsequent calls with the same path return
    the same object without re-reading disk.

    Parameters
    ----------
    path : str | None
        Absolute or relative path to the Parquet file.
        Defaults to ``data/processed/restaurants.parquet`` relative to the
        project root.

    Returns
    -------
    pd.DataFrame
        Full catalog with columns:
        id, name, location, cuisines, rating, cost_for_two, budget

    Raises
    ------
    FileNotFoundError
        If the Parquet file does not exist at the resolved path.
    """
    resolved = Path(path) if path else _DEFAULT_PARQUET

    if not resolved.exists():
        raise FileNotFoundError(
            f"Catalog not found at {resolved}.\n"
            "Run: python scripts/ingest_zomato.py"
        )

    logger.info("Loading catalog from %s", resolved)
    df = pd.read_parquet(resolved, engine="pyarrow")
    logger.info("Catalog loaded: %d rows, %d columns", len(df), len(df.columns))
    return df
