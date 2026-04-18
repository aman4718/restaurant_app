"""
src/restaurant_rec/phase3/llm.py
================================
Phase 3 — LLM Integration (Groq)

Generates intelligent, personalized restaurant recommendations by reasoning
over a deterministic shortlist of restaurants using the Groq API.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from groq import Groq, GroqError
from pydantic import BaseModel, Field, ValidationError

from restaurant_rec.phase2.preferences import UserPreferences

logger = logging.getLogger(__name__)

# Explicitly resolve the path to the project root .env file
_env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

# We explicitly create the client during the function call
# rather than globally to catch config issues during hot-reload.

# Model to use
MODEL_NAME = "llama-3.3-70b-versatile"  # A fast, capable model for JSON/reasoning


# ─── Structured Output Models ──────────────────────────────────────────────────

class RecommendationItem(BaseModel):
    restaurant_id: int = Field(description="The 'id' of the recommended restaurant from the shortlist")
    rank: int = Field(description="The rank of this recommendation (1 to 5)")
    explanation: str = Field(description="A 2-3 sentence personalized explanation of why this restaurant is recommended based on the user's preferences.")


class RecommendationResponse(BaseModel):
    summary: str = Field(description="A brief, engaging introductory summary of the provided recommendations.")
    recommendations: List[RecommendationItem] = Field(description="List of ranked restaurant recommendations, maximum 5.")


# ─── System Prompts ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert restaurant recommendation assistant like the Zomato AI.
Your goal is to provide personalized, intelligent restaurant recommendations based on the user's preferences and a shortlist of available restaurants.

CRITICAL INSTRUCTIONS:
1. You MUST ONLY recommend restaurants that are present in the provided JSON shortlist. DO NOT hallucinate or recommend restaurants outside this list.
2. Provide a MAXIMUM of 5 recommendations. If the shortlist is smaller, return fewer recommendations.
3. Your output MUST be in valid JSON format matching exactly the given schema.
4. Base your reasoning on the restaurant's rating, cuisines, and cost compared to the user's preferences.
5. Make your explanations engaging and helpful.
6. The user budget tier maps to cost_for_two.
"""

# ─── Core Function ────────────────────────────────────────────────────────────

def get_recommendations(
    shortlist: pd.DataFrame,
    preferences: UserPreferences,
    max_retries: int = 2
) -> Dict[str, Any]:
    """
    Pass the filtered shortlist to the LLM to get personalized rankings.

    Parameters
    ----------
    shortlist : pd.DataFrame
        The deterministic shortlist from Phase 2 (max 40 rows).
    preferences : UserPreferences
        The user's original search preferences.
    max_retries : int
        Number of times to retry if the LLM returns invalid JSON or hallucinates.

    Returns
    -------
    dict
        A parsed JSON dictionary matching the RecommendationResponse schema.
        If all retries fail or the shortlist is empty, returns a fallback structure.
    """
    logger.info("--- Phase 3 LLM Engine ---")
    
    if shortlist.empty:
        logger.warning("Shortlist is empty. Bypassing LLM.")
        return {
            "summary": f"I couldn't find any restaurants in {preferences.location} matching your criteria.",
            "recommendations": []
        }

    # Initialize Groq right before we need it
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.error("OS ENV GROQ_API_KEY is absolutely empty or None.")
        groq_client = None
    else:
        try:
            groq_client = Groq(api_key=api_key)
        except Exception as e:
            logger.error("Groq initialization specifically crashed with error: %s", e)
            groq_client = None

    if not groq_client:
        logger.error("Groq client not initialized. Cannot fetch recommendations.")
        return {
            "summary": "LLM service is currently unavailable. Displaying raw shortlist.",
            "recommendations": [
                {
                    "restaurant_id": row["id"],
                    "rank": idx + 1,
                    "explanation": "No AI explanation available."
                }
                for idx, row in shortlist.head(5).iterrows()
            ]
        }

    # Format the shortlist into a lightweight JSON string robustly with Pandas
    columns_to_keep = ["id", "name", "location", "cuisines", "rating", "cost_for_two", "budget"]
    shortlist_json_str = shortlist[columns_to_keep].to_json(orient="records")
    
    # Format the user query
    user_prompt = _build_user_prompt(preferences, shortlist_json_str)

    # Attempt to call LLM with retry logic
    for attempt in range(max_retries + 1):
        try:
            logger.info("Calling Groq API (Attempt %d/%d)...", attempt + 1, max_retries + 1)
            response = groq_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.5, # Balance between deterministic and creative
            )
            
            raw_content = response.choices[0].message.content
            logger.debug("Raw LLM Response: %s", raw_content)
            
            # 1. Parse JSON
            parsed_json = json.loads(raw_content)
            
            # 2. Validate against Pydantic schema
            validated_data = RecommendationResponse(**parsed_json)
            
            # 3. Constrain check: Ensure all recommended IDs actually exist in shortlist
            valid_ids = set(shortlist["id"].tolist())
            clean_recs = []
            
            for rec in validated_data.recommendations:
                if rec.restaurant_id in valid_ids:
                    clean_recs.append(rec)
                else:
                    logger.warning("LLM hallucinates ID %s. Dropping.", rec.restaurant_id)
            
            # Reassign and return
            validated_data.recommendations = clean_recs[:5]
            
            logger.info("Successfully generated %d recommendations.", len(validated_data.recommendations))
            return validated_data.model_dump()
            
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("Failed to parse or validate LLM JSON. Retrying. Error: %s", e)
        except GroqError as e:
            logger.error("Groq API error: %s", e)
            break
        except Exception as e:
            logger.error("Unexpected error in LLM call: %s", e)
            break

    # If all attempts fail, return a safe fallback
    logger.error("LLM recommendation failed after %d retries.", max_retries)
    return {
        "summary": "We had trouble generating personalized recommendations, but here are the top matches based on highest rating.",
        "recommendations": [
            {
                "restaurant_id": row["id"],
                "rank": idx + 1,
                "explanation": f"Highest rated match: {row['rating']} stars."
            }
            for idx, row in shortlist.head(5).iterrows()
        ]
    }


def _build_user_prompt(preferences: UserPreferences, shortlist_json_str: str) -> str:
    """Construct the user message payload."""
    
    return f"""USER PREFERENCES:
Location: {preferences.location}
Cuisine: {preferences.cuisine}
Minimum Rating: {preferences.min_rating}
Budget Tier: {preferences.budget}

AVAILABLE RESTAURANT SHORTLIST (JSON):
{shortlist_json_str}

INSTRUCTIONS:
Pick the top 5 BEST matches from the shortlist above.
Respond ONLY with a JSON object holding a "summary" and a "recommendations" list.

JSON SCHEMA:
{{
  "summary": "string",
  "recommendations": [
    {{
      "restaurant_id": integer,
      "rank": integer (1-5),
      "explanation": "string"
    }}
  ]
}}
"""
