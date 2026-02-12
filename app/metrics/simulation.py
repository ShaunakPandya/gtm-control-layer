from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from app.db.database import get_processed_deals
from app.intake.models import DealInput, ValidatedDeal
from app.routing.engine import RoutingDecision, route_deal
from app.rules.config import RulesConfig, ThresholdConfig, load_config
from app.rules.engine import evaluate_deal


class SimulationInput(BaseModel):
    """Parameters for threshold simulation."""

    defaults: Optional[ThresholdConfig] = None
    segment_overrides: Optional[dict[str, ThresholdConfig]] = None
    rule_weights: Optional[dict[str, int]] = None
    escalation_order: Optional[list[str]] = None
    disabled_rules: list[str] = []


class SimulationMetrics(BaseModel):
    total_deals: int
    auto_approved: int
    escalated: int
    auto_approval_rate: float
    escalation_rate: float
    escalation_by_team: dict[str, int]
    top_rule_triggers: list[dict[str, Any]]


class SimulationResult(BaseModel):
    original: SimulationMetrics
    simulated: SimulationMetrics
    delta: dict[str, Any]


def _compute_sim_metrics(
    deals: list[dict[str, Any]],
    config: RulesConfig,
    disabled_rules: list[str],
) -> SimulationMetrics:
    """Re-evaluate deals against a config and compute metrics."""
    from collections import Counter

    auto_approved = 0
    escalated = 0
    team_counter: Counter[str] = Counter()
    rule_counter: Counter[str] = Counter()

    for deal_row in deals:
        # Reconstruct ValidatedDeal from stored data
        deal_input = DealInput(
            deal_type=deal_row["deal_type"],
            customer_segment=deal_row["customer_segment"],
            annual_contract_value=deal_row["annual_contract_value"],
            discount_percentage=deal_row["discount_percentage"],
            payment_terms_days=deal_row["payment_terms_days"],
            region=deal_row["region"],
            custom_security_clause=deal_row["custom_security_clause"],
            clause_text=deal_row.get("clause_text"),
        )
        validated = ValidatedDeal.from_input(deal_input)

        evaluation = evaluate_deal(validated, config)

        # Zero out disabled rules
        for trigger in evaluation.triggers:
            if trigger.rule_id in disabled_rules:
                trigger.triggered = False
                trigger.weight = 0

        # Recompute total weight after disabling
        evaluation.total_weight = sum(t.weight for t in evaluation.triggers)
        from app.rules.engine import _compute_priority
        evaluation.priority = _compute_priority(evaluation.total_weight, config)

        decision = route_deal(evaluation, config)

        if decision.auto_approved:
            auto_approved += 1
        else:
            escalated += 1
            for team in decision.escalation_path:
                team_counter[team] += 1

        for trigger in evaluation.triggers:
            if trigger.triggered:
                rule_counter[trigger.rule_id] += 1

    total = len(deals)
    return SimulationMetrics(
        total_deals=total,
        auto_approved=auto_approved,
        escalated=escalated,
        auto_approval_rate=auto_approved / total if total > 0 else 0.0,
        escalation_rate=escalated / total if total > 0 else 0.0,
        escalation_by_team=dict(team_counter.most_common()),
        top_rule_triggers=[
            {"rule_id": rule, "count": count}
            for rule, count in rule_counter.most_common()
        ],
    )


def run_simulation(
    sim_input: SimulationInput,
    db_path: Optional[Path] = None,
) -> SimulationResult:
    """Run threshold simulation against stored deals. No data mutation."""
    deals = get_processed_deals(db_path)
    original_config = load_config()

    # Build simulated config
    sim_config_data = original_config.model_dump()
    if sim_input.defaults:
        sim_config_data["defaults"] = sim_input.defaults.model_dump()
    if sim_input.segment_overrides is not None:
        sim_config_data["segment_overrides"] = {
            k: v.model_dump() for k, v in sim_input.segment_overrides.items()
        }
    if sim_input.rule_weights is not None:
        sim_config_data["rule_weights"] = sim_input.rule_weights
    if sim_input.escalation_order is not None:
        sim_config_data["escalation_order"] = sim_input.escalation_order
    sim_config = RulesConfig(**sim_config_data)

    original_metrics = _compute_sim_metrics(deals, original_config, [])
    simulated_metrics = _compute_sim_metrics(deals, sim_config, sim_input.disabled_rules)

    # Compute deltas
    delta: dict[str, Any] = {
        "auto_approval_rate": round(
            simulated_metrics.auto_approval_rate - original_metrics.auto_approval_rate, 4
        ),
        "escalation_rate": round(
            simulated_metrics.escalation_rate - original_metrics.escalation_rate, 4
        ),
        "auto_approved": simulated_metrics.auto_approved - original_metrics.auto_approved,
        "escalated": simulated_metrics.escalated - original_metrics.escalated,
        "escalation_by_team": {},
    }
    all_teams = set(original_metrics.escalation_by_team) | set(simulated_metrics.escalation_by_team)
    for team in all_teams:
        orig_count = original_metrics.escalation_by_team.get(team, 0)
        sim_count = simulated_metrics.escalation_by_team.get(team, 0)
        delta["escalation_by_team"][team] = sim_count - orig_count

    return SimulationResult(
        original=original_metrics,
        simulated=simulated_metrics,
        delta=delta,
    )
