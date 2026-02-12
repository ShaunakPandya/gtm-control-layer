from __future__ import annotations

from pydantic import BaseModel

from app.intake.models import Region, ValidatedDeal
from app.rules.config import RulesConfig, ThresholdConfig


class RuleTrigger(BaseModel):
    """Result of a single rule evaluation."""

    rule_id: str
    triggered: bool
    owner: str
    reason: str
    weight: int = 0


class EvaluationResult(BaseModel):
    """Aggregated output from evaluating all rules against a deal."""

    deal_id: str
    triggers: list[RuleTrigger]
    total_weight: int
    priority: str  # P1, P2, P3, or "None"


def _eval_discount(
    deal: ValidatedDeal, thresholds: ThresholdConfig, weight: int
) -> RuleTrigger:
    triggered = deal.discount_percentage > thresholds.discount_threshold
    return RuleTrigger(
        rule_id="DISCOUNT_THRESHOLD",
        triggered=triggered,
        owner="Finance",
        reason=(
            f"Discount {deal.discount_percentage}% exceeds "
            f"threshold {thresholds.discount_threshold}%"
            if triggered
            else "Discount within threshold"
        ),
        weight=weight if triggered else 0,
    )


def _eval_acv(
    deal: ValidatedDeal, thresholds: ThresholdConfig, weight: int
) -> RuleTrigger:
    triggered = deal.annual_contract_value > thresholds.acv_exec_threshold
    return RuleTrigger(
        rule_id="ACV_EXEC_THRESHOLD",
        triggered=triggered,
        owner="Exec",
        reason=(
            f"ACV ${deal.annual_contract_value:,.0f} exceeds "
            f"threshold ${thresholds.acv_exec_threshold:,.0f}"
            if triggered
            else "ACV within threshold"
        ),
        weight=weight if triggered else 0,
    )


def _eval_eu_legal(
    deal: ValidatedDeal, thresholds: ThresholdConfig, weight: int
) -> RuleTrigger:
    triggered = deal.region == Region.EU and thresholds.eu_requires_legal
    return RuleTrigger(
        rule_id="EU_LEGAL_REVIEW",
        triggered=triggered,
        owner="Legal",
        reason=(
            "EU region requires legal review"
            if triggered
            else "Region does not require legal review"
        ),
        weight=weight if triggered else 0,
    )


def _eval_payment_terms(
    deal: ValidatedDeal, thresholds: ThresholdConfig, weight: int
) -> RuleTrigger:
    triggered = deal.payment_terms_days > thresholds.payment_terms_limit
    return RuleTrigger(
        rule_id="PAYMENT_TERMS_LIMIT",
        triggered=triggered,
        owner="Finance",
        reason=(
            f"Payment terms {deal.payment_terms_days} days exceeds "
            f"limit of {thresholds.payment_terms_limit} days"
            if triggered
            else "Payment terms within limit"
        ),
        weight=weight if triggered else 0,
    )


def _eval_security_clause(
    deal: ValidatedDeal, _thresholds: ThresholdConfig, weight: int
) -> RuleTrigger:
    triggered = deal.custom_security_clause
    return RuleTrigger(
        rule_id="CUSTOM_SECURITY_CLAUSE",
        triggered=triggered,
        owner="Security",
        reason=(
            "Custom security clause requires review"
            if triggered
            else "No custom security clause"
        ),
        weight=weight if triggered else 0,
    )


_RULE_EVALUATORS = [
    _eval_discount,
    _eval_acv,
    _eval_eu_legal,
    _eval_payment_terms,
    _eval_security_clause,
]


def _compute_priority(total_weight: int, config: RulesConfig) -> str:
    """Determine priority tier from total triggered weight using config cutoffs."""
    cutoffs = config.priority_cutoffs
    if total_weight >= cutoffs.P1:
        return "P1"
    if total_weight >= cutoffs.P2:
        return "P2"
    if total_weight >= cutoffs.P3:
        return "P3"
    return "None"


def evaluate_deal(deal: ValidatedDeal, config: RulesConfig) -> EvaluationResult:
    """Evaluate a deal against all rules. Pure, deterministic, idempotent."""
    thresholds = config.resolve_thresholds(deal.customer_segment.value)

    triggers = []
    for evaluator in _RULE_EVALUATORS:
        rule_id = evaluator.__name__.replace("_eval_", "").upper()
        # Map function names to rule_ids for weight lookup
        rule_id_map = {
            "_eval_discount": "DISCOUNT_THRESHOLD",
            "_eval_acv": "ACV_EXEC_THRESHOLD",
            "_eval_eu_legal": "EU_LEGAL_REVIEW",
            "_eval_payment_terms": "PAYMENT_TERMS_LIMIT",
            "_eval_security_clause": "CUSTOM_SECURITY_CLAUSE",
        }
        rid = rule_id_map[evaluator.__name__]
        weight = config.rule_weights.get(rid, 0)
        triggers.append(evaluator(deal, thresholds, weight))

    total_weight = sum(t.weight for t in triggers)
    priority = _compute_priority(total_weight, config)

    return EvaluationResult(
        deal_id=deal.id,
        triggers=triggers,
        total_weight=total_weight,
        priority=priority,
    )
