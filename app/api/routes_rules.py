from __future__ import annotations

from fastapi import APIRouter

from app.intake.models import DealInput, ValidatedDeal
from app.rules.config import load_config
from app.rules.engine import EvaluationResult, evaluate_deal

router = APIRouter(prefix="/deals", tags=["rules"])


@router.post("/evaluate", response_model=EvaluationResult, status_code=200)
async def evaluate_deal_endpoint(deal: DealInput) -> EvaluationResult:
    """Validate a deal and evaluate it against the deterministic rule engine."""
    validated = ValidatedDeal.from_input(deal)
    config = load_config()
    return evaluate_deal(validated, config)
