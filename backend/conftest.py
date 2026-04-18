"""
conftest.py (project root)
===========================
Pytest configuration — adds `src/` to sys.path so every test can do:

    from restaurant_rec.phase2 import UserPreferences, filter_restaurants
    from restaurant_rec.catalog import load_catalog
"""

import sys
from pathlib import Path

# Insert src/ at the front of the import path
sys.path.insert(0, str(Path(__file__).parent / "src"))
