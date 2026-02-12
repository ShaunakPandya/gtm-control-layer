from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException

from app.db.database import get_deal, init_db, insert_override

router = APIRouter(prefix="/deals", tags=["override"])

VALID_OVERRIDE_REASONS = [
    "Strategic deal",
    "Pre-approved by VP",
    "Customer relationship",
    "Competitive pressure",
    "One-time exception",
    "Other",
]


class OverrideRequest(BaseModel):
    override_reason: str = Field(
        description=f"One of: {', '.join(VALID_OVERRIDE_REASONS)}"
    )
    override_notes: Optional[str] = None
    overridden_by: str = "approver"


class OverrideResponse(BaseModel):
    override_id: int
    deal_id: str
    message: str


@router.post(
    "/{deal_id}/override",
    response_model=OverrideResponse,
    status_code=201,
)
async def override_deal(deal_id: str, request: OverrideRequest) -> OverrideResponse:
    """Override an escalated deal decision. Post-decision only."""
    init_db()
    deal = get_deal(deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")

    decision = deal.get("decision_json")
    if not decision:
        raise HTTPException(
            status_code=400, detail="Deal has not been processed yet"
        )

    if decision.get("auto_approved"):
        raise HTTPException(
            status_code=400,
            detail="Cannot override an auto-approved deal",
        )

    original_json = json.dumps(decision)
    override_id = insert_override(
        deal_id=deal_id,
        override_reason=request.override_reason,
        override_notes=request.override_notes,
        original_decision_json=original_json,
        overridden_by=request.overridden_by,
    )

    return OverrideResponse(
        override_id=override_id,
        deal_id=deal_id,
        message="Deal override recorded successfully",
    )
