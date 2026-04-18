"""
tests/phase3/test_llm.py
========================
Phase 3 — LLM Integration Tests

Validates parsing, retry logic, and real responses from the Groq API.
"""

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from restaurant_rec.catalog import load_catalog
from restaurant_rec.phase2 import UserPreferences, filter_restaurants
from restaurant_rec.phase3 import get_recommendations


@pytest.fixture(scope="session")
def catalog():
    return load_catalog()


def print_result(name: str, result: dict):
    print(f"\n--- Output for {name} ---")
    print(f"Summary: {result.get('summary', 'N/A')}")
    recs = result.get("recommendations", [])
    if len(recs) > 0:
        top = recs[0]
        print(
            f"Top Recommendation [Rank {top.get('rank', '?')}]: "
            f"ID {top.get('restaurant_id', 'N/A')} - {top.get('explanation', 'N/A')}"
        )
    else:
        print("Top Recommendation: None")
    print("---------------------------\n")


def test_normal_shortlist(catalog):
    """
    Test 1: valid shortlist hitting actual Groq API.
    Ensures recommendations are generated properly.
    """
    prefs = UserPreferences(
        location="Indiranagar",
        cuisine="Cafe",
        min_rating=4.0,
        budget="medium"
    )
    # Grab deterministic shortlist
    shortlist = filter_restaurants(catalog, prefs)
    
    # Keep the prompt size reasonable by passing just the top 10
    subset = shortlist.head(10)
    
    # Call actual API
    result = get_recommendations(subset, prefs)
    
    print_result("Test 1: Normal Shortlist (Live API)", result)
    
    assert "summary" in result
    assert "recommendations" in result
    assert len(result["recommendations"]) > 0
    
    # Verify the structure of the top rec
    top_rec = result["recommendations"][0]
    assert "restaurant_id" in top_rec
    assert "rank" in top_rec
    assert "explanation" in top_rec
    assert top_rec["rank"] == 1


def test_empty_shortlist():
    """
    Test 2: When shortlist is completely empty, it shouldn't call LLM
    and should return a fallback message.
    """
    prefs = UserPreferences(
        location="NowhereCity",
        cuisine="Alien",
        min_rating=5.0,
        budget="low"
    )
    empty_df = pd.DataFrame(
        columns=["id", "name", "location", "cuisines", "rating", "cost_for_two", "budget"]
    )
    
    result = get_recommendations(empty_df, prefs)
    
    print_result("Test 2: Empty Shortlist", result)
    
    assert result["recommendations"] == []
    # Verify custom message
    assert "NowhereCity" in result["summary"]


@patch("restaurant_rec.phase3.llm.Groq")
def test_invalid_json_retry(mock_groq_class):
    """
    Test 3: LLM hallucinates plain text instead of JSON on first try,
    but corrects itself on the second try. Tests the retry loop.
    """
    mock_groq_client = mock_groq_class.return_value
    prefs = UserPreferences(
        location="Btm",
        cuisine="North Indian",
        min_rating=3.0,
        budget="low"
    )
    df = pd.DataFrame([
        {
            "id": 101, "name": "Fake Name", "location": "Btm", 
            "cuisines": ["North Indian"], "rating": 4.5, "cost_for_two": 300, 
            "budget": "low"
        }
    ])
    
    # Mocking first response (invalid JSON)
    mock_invalid = MagicMock()
    mock_invalid.choices = [MagicMock()]
    mock_invalid.choices[0].message.content = "Oops, I forgot to write JSON! Here is text."
    
    # Mocking second response (valid JSON)
    valid_data = {
        "summary": "Here is the top pick after retry.",
        "recommendations": [
            {
                "restaurant_id": 101, 
                "rank": 1, 
                "explanation": "Perfect match."
            }
        ]
    }
    mock_valid = MagicMock()
    mock_valid.choices = [MagicMock()]
    mock_valid.choices[0].message.content = json.dumps(valid_data)
    
    # groq_client.chat.completions.create()
    mock_groq_client.chat.completions.create.side_effect = [
        mock_invalid, 
        mock_valid
    ]
    
    result = get_recommendations(df, prefs)
    
    print_result("Test 3: Invalid JSON Retry", result)
    
    # Assert retry happened
    assert mock_groq_client.chat.completions.create.call_count == 2
    
    # Assert result is extracted from the second (valid) run
    assert result["summary"] == "Here is the top pick after retry."
    assert len(result["recommendations"]) == 1
    assert result["recommendations"][0]["restaurant_id"] == 101
