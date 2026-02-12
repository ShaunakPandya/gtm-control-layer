from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter

from app.advisory.client import analyze_clause
from app.advisory.models import ClauseAdvisory

router = APIRouter(prefix="/deals", tags=["advisory"])


class ClauseRequest(BaseModel):
    clause_text: str = Field(min_length=1)


@router.post("/analyze-clause", response_model=ClauseAdvisory, status_code=200)
async def analyze_clause_endpoint(request: ClauseRequest) -> ClauseAdvisory:
    """Analyze a contract clause using AI. Strictly advisory — no routing impact."""
    return analyze_clause(request.clause_text)
