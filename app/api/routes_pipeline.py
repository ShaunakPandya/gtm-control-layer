from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from fastapi import APIRouter

from app.advisory.client import analyze_clause
from app.advisory.models import ClauseAdvisory
from app.db.database import init_db, insert_deal, update_deal_decision
from app.intake.models import DealInput, ValidatedDeal
from app.routing.engine import RoutingDecision, route_deal
from app.rules.config import load_config
from app.rules.engine import evaluate_deal

router = APIRouter(tags=["pipeline"])


class PipelineResult(BaseModel):
    """Complete pipeline output: validation + rules + routing + optional advisory."""

    deal: ValidatedDeal
    decision: RoutingDecision
    advisory: Optional[ClauseAdvisory] = None


@router.post("/deals", response_model=PipelineResult, status_code=201)
async def process_deal(deal_input: DealInput) -> PipelineResult:
    """Full pipeline: validate → evaluate → route → optional AI clause advisory."""
    validated = ValidatedDeal.from_input(deal_input)
    config = load_config()
    evaluation = evaluate_deal(validated, config)
    decision = route_deal(evaluation, config)

    advisory = None
    if validated.clause_text:
        advisory = analyze_clause(validated.clause_text)

    # Persist to database
    init_db()
    insert_deal(validated)
    update_deal_decision(validated.id, evaluation, decision, advisory)

    return PipelineResult(
        deal=validated,
        decision=decision,
        advisory=advisory,
    )
