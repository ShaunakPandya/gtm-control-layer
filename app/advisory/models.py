from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ClauseCategory(StrEnum):
    AUDIT = "Audit"
    DATA_RESIDENCY = "Data Residency"
    IP = "IP"
    OTHER = "Other"


class ClauseAdvisory(BaseModel):
    """Structured advisory output from AI clause analysis."""

    summary: str
    risk_level: RiskLevel
    categories: list[ClauseCategory] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    review_required: bool = False
    raw_clause: str
    model_used: str = ""
    error: str | None = None
