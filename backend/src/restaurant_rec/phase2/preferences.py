"""
src/restaurant_rec/phase2/preferences.py
=========================================
Phase 2 — User Preferences Model

Defines and validates the user's search preferences using Pydantic.
All fields go through validators before being passed to the filter engine.

Fields:
    location   : Target city / neighbourhood (e.g. "Bangalore", "BTM")
    cuisine    : Desired cuisine type (e.g. "Chinese", "North Indian")
    min_rating : Minimum acceptable aggregate rating  [0.0 – 5.0]
    budget     : Cost bracket  "low" | "medium" | "high"

Optional fields default to "any-match" sentinels so callers can omit
filters they don't care about without sending None values through the stack.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# Valid budget tiers must match the ingestion script's classification
BudgetTier = Literal["low", "medium", "high"]


class UserPreferences(BaseModel):
    """
    Validated container for a single recommendation request.

    Example
    -------
    >>> prefs = UserPreferences(
    ...     location="BTM",
    ...     cuisine="Chinese",
    ...     min_rating=3.5,
    ...     budget="medium",
    ... )
    """

    location: str = Field(
        ...,
        min_length=1,
        description="City or area name to search in (e.g. 'Bangalore', 'BTM Layout').",
    )

    cuisine: str = Field(
        ...,
        min_length=1,
        description="Cuisine type (e.g. 'Chinese', 'North Indian', 'Italian').",
    )

    min_rating: float = Field(
        default=0.0,
        ge=0.0,
        le=5.0,
        description="Minimum aggregate rating on Zomato scale [0.0 – 5.0]. Default: 0.0 (no filter).",
    )

    budget: BudgetTier = Field(
        ...,
        description="Cost bracket: 'low' (< ₹500), 'medium' (₹500–₹1500), 'high' (> ₹1500).",
    )

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("location", "cuisine", mode="before")
    @classmethod
    def strip_and_non_empty(cls, v: str) -> str:
        """Strip whitespace; reject blank strings."""
        v = v.strip()
        if not v:
            raise ValueError("Value must not be blank or whitespace-only.")
        return v

    @field_validator("min_rating", mode="before")
    @classmethod
    def coerce_rating(cls, v) -> float:
        """Accept numeric strings like '3.5'."""
        try:
            return float(v)
        except (TypeError, ValueError):
            raise ValueError(f"min_rating must be a number; got {v!r}")

    @model_validator(mode="after")
    def log_preferences(self) -> "UserPreferences":
        """Post-init hook — useful for debugging / tracing."""
        return self

    # ── Helpers ───────────────────────────────────────────────────────────────

    def summary(self) -> str:
        """Human-readable one-liner for logging."""
        return (
            f"location={self.location!r}  cuisine={self.cuisine!r}  "
            f"min_rating={self.min_rating}  budget={self.budget!r}"
        )

    class Config:
        # Freeze the object after creation so it can be safely shared
        frozen = True
