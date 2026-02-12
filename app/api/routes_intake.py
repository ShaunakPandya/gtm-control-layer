from __future__ import annotations

from fastapi import APIRouter

from app.intake.models import DealInput, ValidatedDeal

router = APIRouter(prefix="/deals", tags=["intake"])


@router.post("/validate", response_model=ValidatedDeal, status_code=201)
async def validate_deal(deal: DealInput) -> ValidatedDeal:
    """Validate a raw deal submission and return a structured ValidatedDeal."""
    return ValidatedDeal.from_input(deal)
