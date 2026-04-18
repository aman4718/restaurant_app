"""
src/restaurant_rec/phase4/app.py
================================
Phase 4 — FastAPI Backend

Exposes the filtering engine (Phase 2) and LLM recommender (Phase 3)
via a REST API at POST /api/v1/recommend.
"""

import logging
from contextlib import asynccontextmanager
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from restaurant_rec.catalog import load_catalog
from restaurant_rec.phase2.preferences import UserPreferences
from restaurant_rec.phase2.filter import filter_restaurants
from restaurant_rec.phase3.llm import get_recommendations

logger = logging.getLogger(__name__)


# ─── Response Models ──────────────────────────────────────────────────────────

class RestaurantItem(BaseModel):
    name: str
    cuisines: List[str]
    rating: Optional[float] = None
    cost_for_two: Optional[float] = None
    explanation: str
    rank: int


class RecommendResponse(BaseModel):
    summary: str
    items: List[RestaurantItem]


class OptionsResponse(BaseModel):
    locations: List[str]
    cuisines: List[str]

# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-loads the Parquet catalog into memory on server startup."""
    try:
        logger.info("Initializing system...")
        load_catalog()
    except Exception as e:
        logger.error("Failed to load catalog during startup: %s", e)
    yield


# ─── Application Setup ────────────────────────────────────────────────────────

app = FastAPI(
    title="Zomato AI Recommendation API",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/v1/options", response_model=OptionsResponse)
def get_options():
    """Provides unique locations and cuisines for frontend dropdowns."""
    try:
        catalog = load_catalog()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    locations = sorted(catalog["location"].dropna().unique().tolist())
    
    # Cuisines is a column of arrays, we flatten it to get unique values
    unique_cuisines = set()
    for c_array in catalog["cuisines"].dropna():
        unique_cuisines.update(c_array)
        
    cuisines = sorted(list(unique_cuisines))
    
    return OptionsResponse(locations=locations, cuisines=cuisines)

@app.post("/api/v1/recommend", response_model=RecommendResponse)
def recommend(preferences: UserPreferences):
    """
    Main recommendation endpoint.
    
    Flow:
    1. Validate input (handled cleanly by UserPreferences Pydantic model)
    2. Load catalog 
    3. Filter down to top 40 local matches
    4. Pass shortlist to Groq LLM
    5. Merge LLM explanation/rank with native dataset rows
    6. Return unified payload
    """
    try:
        catalog = load_catalog()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail="Database not initialized. Please ingest data first.") 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Deterministic Filtering
    try:
        shortlist = filter_restaurants(catalog, preferences)
    except Exception as e:
        logger.error("Error in filtering engine: %s", e)
        raise HTTPException(status_code=500, detail="Internal filtering error.")

    # LLM Inference
    try:
        llm_response = get_recommendations(shortlist, preferences)
    except Exception as e:
        logger.error("Error in LLM engine: %s", e)
        # We don't fail the whole request here, just return empty items
        llm_response = {
            "summary": "Our AI service encountered an error.",
            "recommendations": []
        }

    # Merge Data
    summary = llm_response.get("summary", "")
    raw_recs = llm_response.get("recommendations", [])
    items: List[RestaurantItem] = []

    if not shortlist.empty and raw_recs:
        # Create a quick-lookup dict of the shortlist by id
        shortlist_dict = shortlist.set_index("id").to_dict(orient="index")
        
        seen_ids = set()
        seen_names = set()
        for r in raw_recs:
            r_id = r.get("restaurant_id")
            
            # Guard against completely invalid IDs
            if r_id in shortlist_dict:
                row = shortlist_dict[r_id]
                name = str(row["name"]).strip().lower()
                
                # Check BOTH ID and Name to completely strip chain clones
                if r_id not in seen_ids and name not in seen_names:
                    seen_ids.add(r_id)
                    seen_names.add(name)
                    
                    # Handle pandas NaNs cleanly
                    rating = float(row["rating"]) if pd.notna(row["rating"]) else None
                    cost = float(row["cost_for_two"]) if pd.notna(row["cost_for_two"]) else None
                    
                    # Numpy arrays inside 'cuisines' need converting to standard list
                    cuisines_list = list(row["cuisines"])
                    
                    items.append(RestaurantItem(
                        name=str(row["name"]),
                        cuisines=cuisines_list,
                        rating=rating,
                        cost_for_two=cost,
                        explanation=str(r.get("explanation", "")),
                        rank=int(r.get("rank", 0))
                    ))
                
        # Guard against LLM returning weird ranks, enforce sort
        items.sort(key=lambda x: x.rank)

    return RecommendResponse(
        summary=summary,
        items=items
    )
