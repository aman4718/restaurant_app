import json
import pytest
from fastapi.testclient import TestClient

from restaurant_rec.phase4.app import app

# We use TestClient which spins up a synchronous version of the FastAPI app for testing
client = TestClient(app)

def print_result(test_name, status_code, json_data):
    print(f"\n=== {test_name} ===")
    print(f"Status Code : {status_code}")
    print(f"Response Body:\n{json.dumps(json_data, indent=2)}")
    print("=" * 40 + "\n")

def test_recommend_endpoint_success():
    """
    Test sending a valid request to the POST /api/v1/recommend endpoint.
    """
    payload = {
        "location": "Btm",
        "cuisine": "North Indian",
        "min_rating": 4.0,
        "budget": "low"
    }

    # Since we are using Live API by default, this will hit Groq.
    response = client.post("/api/v1/recommend", json=payload)
    data = response.json()
    
    print_result("Test 1: Valid Request", response.status_code, data)
    
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    assert "summary" in data
    assert "items" in data
    
    # Check that if items were found, they follow the model constraints
    for item in data["items"]:
        assert "name" in item
        assert "cuisines" in item
        assert "rank" in item
        assert "explanation" in item

def test_recommend_endpoint_empty_results():
    """
    Test a query that definitely yields zero results to ensure graceful fallback.
    """
    payload = {
        "location": "A City That Doesn't Exist In Dataset",
        "cuisine": "Martian Food",
        "min_rating": 4.0,
        "budget": "high"
    }

    response = client.post("/api/v1/recommend", json=payload)
    data = response.json()
    
    print_result("Test 2: No Results", response.status_code, data)

    assert response.status_code == 200
    assert data["items"] == []
    assert "summary" in data

def test_recommend_endpoint_validation_error():
    """
    Test sending a request with an invalid budget tier (should fail Pydantic validation).
    """
    payload = {
        "location": "Btm",
        "cuisine": "North Indian",
        "min_rating": 4.0,
        "budget": "super_cheap_not_real_tier"  # Invalid!
    }

    response = client.post("/api/v1/recommend", json=payload)
    data = response.json()
    
    print_result("Test 3: Invalid Input", response.status_code, data)
    
    # 422 is FastAPI's standard Unprocessable Entity for validation failure
    assert response.status_code == 422
    assert "detail" in data
