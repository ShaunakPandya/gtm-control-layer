"""Unit tests for the deterministic routing engine."""

from app.intake.models import DealInput, ValidatedDeal
from app.routing.engine import RoutingDecision, route_deal
from app.rules.config import RulesConfig, ThresholdConfig
from app.rules.engine import EvaluationResult, RuleTrigger, evaluate_deal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_DEAL = dict(
    deal_type="New",
    customer_segment="Mid-Market",
    annual_contract_value=100_000,
    discount_percentage=15,
    payment_terms_days=30,
    region="NA",
    custom_security_clause=False,
)

DEFAULT_CONFIG = RulesConfig()


def make_validated(**overrides) -> ValidatedDeal:
    return ValidatedDeal.from_input(DealInput(**{**VALID_DEAL, **overrides}))


def full_pipeline(config: RulesConfig | None = None, **deal_overrides) -> RoutingDecision:
    cfg = config or DEFAULT_CONFIG
    deal = make_validated(**deal_overrides)
    evaluation = evaluate_deal(deal, cfg)
    return route_deal(evaluation, cfg)


# ---------------------------------------------------------------------------
# Auto-Approve
# ---------------------------------------------------------------------------


class TestAutoApprove:
    def test_no_triggers_auto_approves(self):
        decision = full_pipeline()
        assert decision.auto_approved is True
        assert decision.approval_status == "Auto-Approved"
        assert decision.escalation_path == []

    def test_auto_approve_priority_is_none(self):
        decision = full_pipeline()
        assert decision.priority == "None"
        assert decision.total_weight == 0

    def test_auto_approve_still_has_all_triggers(self):
        decision = full_pipeline()
        assert len(decision.rule_triggers) == 5
        assert all(not t.triggered for t in decision.rule_triggers)


# ---------------------------------------------------------------------------
# Single escalation
# ---------------------------------------------------------------------------


class TestSingleEscalation:
    def test_discount_escalates_to_finance(self):
        decision = full_pipeline(discount_percentage=25)
        assert decision.auto_approved is False
        assert decision.approval_status == "Escalated"
        assert decision.escalation_path == ["Finance"]

    def test_acv_escalates_to_exec(self):
        decision = full_pipeline(annual_contract_value=200_000)
        assert decision.escalation_path == ["Exec"]

    def test_eu_escalates_to_legal(self):
        decision = full_pipeline(region="EU")
        assert decision.escalation_path == ["Legal"]

    def test_payment_terms_escalates_to_finance(self):
        decision = full_pipeline(payment_terms_days=60)
        assert decision.escalation_path == ["Finance"]

    def test_security_clause_escalates_to_security(self):
        decision = full_pipeline(custom_security_clause=True)
        assert decision.escalation_path == ["Security"]


# ---------------------------------------------------------------------------
# Multi-escalation & deduplication
# ---------------------------------------------------------------------------


class TestMultiEscalation:
    def test_discount_and_payment_deduplicates_finance(self):
        decision = full_pipeline(discount_percentage=25, payment_terms_days=60)
        assert decision.escalation_path == ["Finance"]
        assert decision.approval_status == "Escalated"

    def test_all_triggers_all_four_teams(self):
        decision = full_pipeline(
            discount_percentage=30,
            annual_contract_value=200_000,
            region="EU",
            payment_terms_days=60,
            custom_security_clause=True,
        )
        assert decision.escalation_path == ["Finance", "Legal", "Security", "Exec"]

    def test_two_teams_no_duplicates(self):
        decision = full_pipeline(discount_percentage=25, custom_security_clause=True)
        assert decision.escalation_path == ["Finance", "Security"]
        assert len(decision.escalation_path) == len(set(decision.escalation_path))

    def test_three_teams(self):
        decision = full_pipeline(
            discount_percentage=25,
            region="EU",
            custom_security_clause=True,
        )
        assert decision.escalation_path == ["Finance", "Legal", "Security"]


# ---------------------------------------------------------------------------
# Configurable escalation order
# ---------------------------------------------------------------------------


class TestEscalationOrder:
    def test_default_order_finance_legal_security_exec(self):
        decision = full_pipeline(
            discount_percentage=30,
            annual_contract_value=200_000,
            region="EU",
            custom_security_clause=True,
        )
        assert decision.escalation_path == ["Finance", "Legal", "Security", "Exec"]

    def test_custom_order_reverses_priority(self):
        config = RulesConfig(
            escalation_order=["Exec", "Security", "Legal", "Finance"]
        )
        decision = full_pipeline(
            config=config,
            discount_percentage=30,
            annual_contract_value=200_000,
            region="EU",
            custom_security_clause=True,
        )
        assert decision.escalation_path == ["Exec", "Security", "Legal", "Finance"]

    def test_custom_order_partial(self):
        config = RulesConfig(
            escalation_order=["Security", "Finance", "Legal", "Exec"]
        )
        decision = full_pipeline(
            config=config,
            discount_percentage=25,
            custom_security_clause=True,
        )
        assert decision.escalation_path == ["Security", "Finance"]

    def test_unknown_team_sorts_last(self):
        """If a rule owner isn't in escalation_order, it sorts to the end."""
        # Build a synthetic evaluation with an unknown owner
        deal = make_validated()
        triggers = [
            RuleTrigger(
                rule_id="CUSTOM_RULE",
                triggered=True,
                owner="Compliance",
                reason="test",
                weight=1,
            ),
            RuleTrigger(
                rule_id="DISCOUNT_THRESHOLD",
                triggered=True,
                owner="Finance",
                reason="test",
                weight=2,
            ),
        ]
        evaluation = EvaluationResult(
            deal_id=deal.id,
            triggers=triggers,
            total_weight=3,
            priority="P2",
        )
        decision = route_deal(evaluation, DEFAULT_CONFIG)
        assert decision.escalation_path == ["Finance", "Compliance"]


# ---------------------------------------------------------------------------
# Priority propagation
# ---------------------------------------------------------------------------


class TestPriorityPropagation:
    def test_p1_propagated(self):
        decision = full_pipeline(
            discount_percentage=30, annual_contract_value=200_000
        )
        assert decision.priority == "P1"

    def test_p2_propagated(self):
        decision = full_pipeline(discount_percentage=25, payment_terms_days=60)
        assert decision.priority == "P2"

    def test_p3_propagated(self):
        decision = full_pipeline(payment_terms_days=60)
        assert decision.priority == "P3"

    def test_total_weight_propagated(self):
        decision = full_pipeline(
            discount_percentage=30,
            annual_contract_value=200_000,
            region="EU",
            payment_terms_days=60,
            custom_security_clause=True,
        )
        assert decision.total_weight == 11


# ---------------------------------------------------------------------------
# Idempotency and immutability
# ---------------------------------------------------------------------------


class TestRoutingIdempotency:
    def test_idempotent(self):
        deal = make_validated(discount_percentage=25, custom_security_clause=True)
        evaluation = evaluate_deal(deal, DEFAULT_CONFIG)
        d1 = route_deal(evaluation, DEFAULT_CONFIG)
        d2 = route_deal(evaluation, DEFAULT_CONFIG)
        assert d1.escalation_path == d2.escalation_path
        assert d1.approval_status == d2.approval_status
        assert d1.priority == d2.priority

    def test_evaluation_not_mutated(self):
        deal = make_validated(discount_percentage=25)
        evaluation = evaluate_deal(deal, DEFAULT_CONFIG)
        original = evaluation.model_dump()
        route_deal(evaluation, DEFAULT_CONFIG)
        assert evaluation.model_dump() == original

    def test_decision_has_deal_id(self):
        deal = make_validated()
        evaluation = evaluate_deal(deal, DEFAULT_CONFIG)
        decision = route_deal(evaluation, DEFAULT_CONFIG)
        assert decision.deal_id == deal.id
