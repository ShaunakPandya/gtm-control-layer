from __future__ import annotations

from pydantic import BaseModel

from app.rules.config import RulesConfig
from app.rules.engine import EvaluationResult, RuleTrigger


class RoutingDecision(BaseModel):
    """Final decision object produced by the routing engine."""

    deal_id: str
    approval_status: str  # "Auto-Approved" or "Escalated"
    escalation_path: list[str]
    rule_triggers: list[RuleTrigger]
    auto_approved: bool
    priority: str
    total_weight: int


def route_deal(evaluation: EvaluationResult, config: RulesConfig) -> RoutingDecision:
    """Convert evaluation triggers into a routing decision. Pure, deterministic."""
    fired = [t for t in evaluation.triggers if t.triggered]

    if not fired:
        return RoutingDecision(
            deal_id=evaluation.deal_id,
            approval_status="Auto-Approved",
            escalation_path=[],
            rule_triggers=evaluation.triggers,
            auto_approved=True,
            priority=evaluation.priority,
            total_weight=evaluation.total_weight,
        )

    # Collect unique owners from triggered rules
    owners_seen: set[str] = set()
    unique_owners: list[str] = []
    for trigger in fired:
        if trigger.owner not in owners_seen:
            owners_seen.add(trigger.owner)
            unique_owners.append(trigger.owner)

    # Sort by configurable escalation order
    order_map = {team: idx for idx, team in enumerate(config.escalation_order)}
    escalation_path = sorted(
        unique_owners,
        key=lambda t: order_map.get(t, len(config.escalation_order)),
    )

    return RoutingDecision(
        deal_id=evaluation.deal_id,
        approval_status="Escalated",
        escalation_path=escalation_path,
        rule_triggers=evaluation.triggers,
        auto_approved=False,
        priority=evaluation.priority,
        total_weight=evaluation.total_weight,
    )
