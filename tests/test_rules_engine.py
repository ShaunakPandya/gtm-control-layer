"""Unit tests for the deterministic rule engine."""

import copy

from app.intake.models import DealInput, ValidatedDeal
from app.rules.config import RulesConfig, ThresholdConfig
from app.rules.engine import EvaluationResult, evaluate_deal


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


def triggered_ids(result: EvaluationResult) -> set[str]:
    return {t.rule_id for t in result.triggers if t.triggered}


def triggered_owners(result: EvaluationResult) -> set[str]:
    return {t.owner for t in result.triggers if t.triggered}


# ---------------------------------------------------------------------------
# Individual rule triggers
# ---------------------------------------------------------------------------


class TestDiscountRule:
    def test_discount_above_threshold_triggers(self):
        deal = make_validated(discount_percentage=25)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert "DISCOUNT_THRESHOLD" in triggered_ids(result)

    def test_discount_at_threshold_does_not_trigger(self):
        deal = make_validated(discount_percentage=20)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert "DISCOUNT_THRESHOLD" not in triggered_ids(result)

    def test_discount_below_threshold_does_not_trigger(self):
        deal = make_validated(discount_percentage=10)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert "DISCOUNT_THRESHOLD" not in triggered_ids(result)

    def test_discount_trigger_owner_is_finance(self):
        deal = make_validated(discount_percentage=25)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        trigger = next(t for t in result.triggers if t.rule_id == "DISCOUNT_THRESHOLD")
        assert trigger.owner == "Finance"


class TestACVRule:
    def test_acv_above_threshold_triggers(self):
        deal = make_validated(annual_contract_value=200_000)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert "ACV_EXEC_THRESHOLD" in triggered_ids(result)

    def test_acv_at_threshold_does_not_trigger(self):
        deal = make_validated(annual_contract_value=150_000)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert "ACV_EXEC_THRESHOLD" not in triggered_ids(result)

    def test_acv_below_threshold_does_not_trigger(self):
        deal = make_validated(annual_contract_value=50_000)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert "ACV_EXEC_THRESHOLD" not in triggered_ids(result)

    def test_acv_trigger_owner_is_exec(self):
        deal = make_validated(annual_contract_value=200_000)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        trigger = next(t for t in result.triggers if t.rule_id == "ACV_EXEC_THRESHOLD")
        assert trigger.owner == "Exec"


class TestEULegalRule:
    def test_eu_region_triggers_legal(self):
        deal = make_validated(region="EU")
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert "EU_LEGAL_REVIEW" in triggered_ids(result)

    def test_non_eu_region_does_not_trigger(self):
        for region in ["NA", "UK", "APAC", "LATAM", "MEA"]:
            deal = make_validated(region=region)
            result = evaluate_deal(deal, DEFAULT_CONFIG)
            assert "EU_LEGAL_REVIEW" not in triggered_ids(result), f"Failed for {region}"

    def test_eu_legal_disabled_does_not_trigger(self):
        config = RulesConfig(defaults=ThresholdConfig(eu_requires_legal=False))
        deal = make_validated(region="EU")
        result = evaluate_deal(deal, config)
        assert "EU_LEGAL_REVIEW" not in triggered_ids(result)

    def test_eu_trigger_owner_is_legal(self):
        deal = make_validated(region="EU")
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        trigger = next(t for t in result.triggers if t.rule_id == "EU_LEGAL_REVIEW")
        assert trigger.owner == "Legal"


class TestPaymentTermsRule:
    def test_payment_terms_above_limit_triggers(self):
        deal = make_validated(payment_terms_days=60)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert "PAYMENT_TERMS_LIMIT" in triggered_ids(result)

    def test_payment_terms_at_limit_does_not_trigger(self):
        deal = make_validated(payment_terms_days=45)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert "PAYMENT_TERMS_LIMIT" not in triggered_ids(result)

    def test_payment_terms_below_limit_does_not_trigger(self):
        deal = make_validated(payment_terms_days=30)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert "PAYMENT_TERMS_LIMIT" not in triggered_ids(result)

    def test_payment_trigger_owner_is_finance(self):
        deal = make_validated(payment_terms_days=60)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        trigger = next(t for t in result.triggers if t.rule_id == "PAYMENT_TERMS_LIMIT")
        assert trigger.owner == "Finance"


class TestSecurityClauseRule:
    def test_security_clause_true_triggers(self):
        deal = make_validated(custom_security_clause=True)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert "CUSTOM_SECURITY_CLAUSE" in triggered_ids(result)

    def test_security_clause_false_does_not_trigger(self):
        deal = make_validated(custom_security_clause=False)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert "CUSTOM_SECURITY_CLAUSE" not in triggered_ids(result)

    def test_security_trigger_owner_is_security(self):
        deal = make_validated(custom_security_clause=True)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        trigger = next(
            t for t in result.triggers if t.rule_id == "CUSTOM_SECURITY_CLAUSE"
        )
        assert trigger.owner == "Security"


# ---------------------------------------------------------------------------
# Multi-trigger scenarios
# ---------------------------------------------------------------------------


class TestMultiTrigger:
    def test_no_rules_triggered(self):
        deal = make_validated()  # all within defaults
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert triggered_ids(result) == set()

    def test_all_rules_triggered(self):
        deal = make_validated(
            discount_percentage=30,
            annual_contract_value=200_000,
            region="EU",
            payment_terms_days=60,
            custom_security_clause=True,
        )
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert triggered_ids(result) == {
            "DISCOUNT_THRESHOLD",
            "ACV_EXEC_THRESHOLD",
            "EU_LEGAL_REVIEW",
            "PAYMENT_TERMS_LIMIT",
            "CUSTOM_SECURITY_CLAUSE",
        }

    def test_two_rules_triggered(self):
        deal = make_validated(discount_percentage=25, custom_security_clause=True)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert triggered_ids(result) == {"DISCOUNT_THRESHOLD", "CUSTOM_SECURITY_CLAUSE"}

    def test_always_returns_five_triggers(self):
        deal = make_validated()
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert len(result.triggers) == 5


# ---------------------------------------------------------------------------
# Segment override behavior
# ---------------------------------------------------------------------------


class TestSegmentOverrides:
    def test_enterprise_higher_discount_threshold(self):
        config = RulesConfig(
            segment_overrides={
                "Enterprise": ThresholdConfig(discount_threshold=25),
            }
        )
        # 22% discount: triggers default (20) but NOT enterprise override (25)
        deal_enterprise = make_validated(
            customer_segment="Enterprise", discount_percentage=22
        )
        deal_midmarket = make_validated(
            customer_segment="Mid-Market", discount_percentage=22
        )

        result_ent = evaluate_deal(deal_enterprise, config)
        result_mm = evaluate_deal(deal_midmarket, config)

        assert "DISCOUNT_THRESHOLD" not in triggered_ids(result_ent)
        assert "DISCOUNT_THRESHOLD" in triggered_ids(result_mm)

    def test_config_change_alters_behavior(self):
        deal = make_validated(discount_percentage=22)

        config_strict = RulesConfig(
            defaults=ThresholdConfig(discount_threshold=15)
        )
        config_loose = RulesConfig(
            defaults=ThresholdConfig(discount_threshold=30)
        )

        result_strict = evaluate_deal(deal, config_strict)
        result_loose = evaluate_deal(deal, config_loose)

        assert "DISCOUNT_THRESHOLD" in triggered_ids(result_strict)
        assert "DISCOUNT_THRESHOLD" not in triggered_ids(result_loose)


# ---------------------------------------------------------------------------
# Priority computation
# ---------------------------------------------------------------------------


class TestPriorityComputation:
    def test_no_triggers_priority_none(self):
        deal = make_validated()
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert result.priority == "None"
        assert result.total_weight == 0

    def test_single_low_weight_trigger_p3(self):
        # Payment terms only: weight=1 → P3
        deal = make_validated(payment_terms_days=60)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert result.total_weight == 1
        assert result.priority == "P3"

    def test_discount_trigger_p3(self):
        # Discount only: weight=2 → P3 (>= 1, < 3)
        deal = make_validated(discount_percentage=25)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert result.total_weight == 2
        assert result.priority == "P3"

    def test_medium_weight_p2(self):
        # Discount(2) + Payment(1) = 3 → P2
        deal = make_validated(discount_percentage=25, payment_terms_days=60)
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert result.total_weight == 3
        assert result.priority == "P2"

    def test_high_weight_p1(self):
        # ACV(3) + Discount(2) = 5 → P1
        deal = make_validated(
            discount_percentage=25, annual_contract_value=200_000
        )
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert result.total_weight == 5
        assert result.priority == "P1"

    def test_all_triggers_p1(self):
        deal = make_validated(
            discount_percentage=30,
            annual_contract_value=200_000,
            region="EU",
            payment_terms_days=60,
            custom_security_clause=True,
        )
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        # 2+3+2+1+3 = 11
        assert result.total_weight == 11
        assert result.priority == "P1"

    def test_custom_cutoffs(self):
        from app.rules.config import PriorityCutoffs

        config = RulesConfig(
            priority_cutoffs=PriorityCutoffs(P1=100, P2=50, P3=10)
        )
        deal = make_validated(discount_percentage=25)  # weight=2
        result = evaluate_deal(deal, config)
        assert result.priority == "None"  # 2 < 10


# ---------------------------------------------------------------------------
# Idempotency and immutability
# ---------------------------------------------------------------------------


class TestIdempotencyAndImmutability:
    def test_idempotent_evaluation(self):
        deal = make_validated(discount_percentage=25, custom_security_clause=True)
        r1 = evaluate_deal(deal, DEFAULT_CONFIG)
        r2 = evaluate_deal(deal, DEFAULT_CONFIG)
        assert triggered_ids(r1) == triggered_ids(r2)
        assert r1.total_weight == r2.total_weight
        assert r1.priority == r2.priority

    def test_deal_not_mutated(self):
        deal = make_validated(discount_percentage=25)
        original_dump = deal.model_dump()
        evaluate_deal(deal, DEFAULT_CONFIG)
        assert deal.model_dump() == original_dump

    def test_config_not_mutated(self):
        config = RulesConfig()
        original_dump = config.model_dump()
        deal = make_validated(discount_percentage=25)
        evaluate_deal(deal, config)
        assert config.model_dump() == original_dump

    def test_result_contains_deal_id(self):
        deal = make_validated()
        result = evaluate_deal(deal, DEFAULT_CONFIG)
        assert result.deal_id == deal.id
