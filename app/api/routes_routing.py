from __future__ import annotations

from fastapi import APIRouter

from app.intake.models import DealInput, ValidatedDeal
from app.routing.engine import RoutingDecision, route_deal
from app.rules.config import load_config
from app.rules.engine import evaluate_deal

router = APIRouter(prefix="/deals", tags=["routing"])


@router.post("/route", response_model=RoutingDecision, status_code=200)
async def route_deal_endpoint(deal: DealInput) -> RoutingDecision:
    """Full pipeline: validate → evaluate rules → route decision."""
    validated = ValidatedDeal.from_input(deal)
    config = load_config()
    evaluation = evaluate_deal(validated, config)
    return route_deal(evaluation, config)
