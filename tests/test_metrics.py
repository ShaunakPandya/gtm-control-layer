"""Unit tests for metrics computation and simulation."""

import pytest
from pathlib import Path

from app.db.database import init_db, insert_deal, insert_override, reset_db, update_deal_decision
from app.intake.models import DealInput, ValidatedDeal
from app.metrics.compute import compute_metrics
from app.metrics.seed import seed_deals
from app.metrics.simulation import SimulationInput, run_simulation
from app.routing.engine import route_deal
from app.rules.config import RulesConfig, ThresholdConfig
from app.rules.engine import evaluate_deal

VALID_DEAL = dict(
    deal_type="New",
    customer_segment="Mid-Market",
    annual_contract_value=100_000,
    discount_percentage=15,
    payment_terms_days=30,
    region="NA",
    custom_security_clause=False,
)


@pytest.fixture()
def db_path(tmp_path):
    p = tmp_path / "test.db"
    init_db(p)
    return p


def _make_deal(**overrides) -> ValidatedDeal:
    return ValidatedDeal.from_input(DealInput(**{**VALID_DEAL, **overrides}))


def _process_and_store(deal: ValidatedDeal, db_path: Path):
    config = RulesConfig()
    evaluation = evaluate_deal(deal, config)
    decision = route_deal(evaluation, config)
    insert_deal(deal, db_path)
    update_deal_decision(deal.id, evaluation, decision, None, db_path)
    return decision


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestMetrics:
    def test_empty_db(self, db_path):
        m = compute_metrics(db_path)
        assert m.total_deals == 0
        assert m.auto_approval_rate == 0.0

    def test_auto_approved_count(self, db_path):
        for _ in range(3):
            _process_and_store(_make_deal(), db_path)
        m = compute_metrics(db_path)
        assert m.auto_approved == 3
        assert m.escalated == 0
        assert m.auto_approval_rate == 1.0

    def test_escalated_count(self, db_path):
        for _ in range(2):
            _process_and_store(_make_deal(discount_percentage=25), db_path)
        m = compute_metrics(db_path)
        assert m.escalated == 2
        assert m.auto_approved == 0
        assert m.escalation_rate == 1.0

    def test_mixed_deals(self, db_path):
        _process_and_store(_make_deal(), db_path)  # auto-approve
        _process_and_store(_make_deal(discount_percentage=25), db_path)  # escalate
        m = compute_metrics(db_path)
        assert m.total_deals == 2
        assert m.auto_approved == 1
        assert m.escalated == 1
        assert m.auto_approval_rate == 0.5

    def test_escalation_by_team(self, db_path):
        _process_and_store(_make_deal(discount_percentage=25), db_path)
        _process_and_store(_make_deal(region="EU"), db_path)
        m = compute_metrics(db_path)
        assert "Finance" in m.escalation_by_team
        assert "Legal" in m.escalation_by_team

    def test_top_rule_triggers(self, db_path):
        _process_and_store(_make_deal(discount_percentage=25), db_path)
        m = compute_metrics(db_path)
        rule_ids = [t["rule_id"] for t in m.top_rule_triggers]
        assert "DISCOUNT_THRESHOLD" in rule_ids

    def test_override_rate(self, db_path):
        deal = _make_deal(discount_percentage=25)
        decision = _process_and_store(deal, db_path)
        insert_override(deal.id, "Test", None, decision.model_dump_json(), db_path=db_path)
        m = compute_metrics(db_path)
        assert m.overridden == 1
        assert m.override_rate > 0


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------


class TestSeed:
    def test_seed_generates_deals(self, db_path):
        ids = seed_deals(count=10, auto_process=True, db_path=db_path)
        assert len(ids) == 10
        m = compute_metrics(db_path)
        assert m.total_deals == 10


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


class TestSimulation:
    def test_simulation_no_change(self, db_path):
        seed_deals(count=20, auto_process=True, db_path=db_path)
        sim_input = SimulationInput()
        result = run_simulation(sim_input, db_path)
        assert result.original.total_deals == 20
        assert result.simulated.total_deals == 20
        # No change in config → deltas should be zero
        assert result.delta["auto_approval_rate"] == 0.0
        assert result.delta["escalation_rate"] == 0.0

    def test_simulation_looser_threshold_increases_approval(self, db_path):
        # Create deals that trigger at default (20%) but not at 50%
        for _ in range(10):
            _process_and_store(_make_deal(discount_percentage=25), db_path)
        sim_input = SimulationInput(
            defaults=ThresholdConfig(discount_threshold=50)
        )
        result = run_simulation(sim_input, db_path)
        assert result.simulated.auto_approved > result.original.auto_approved
        assert result.delta["auto_approval_rate"] > 0

    def test_simulation_stricter_threshold_increases_escalation(self, db_path):
        for _ in range(10):
            _process_and_store(_make_deal(discount_percentage=15), db_path)
        sim_input = SimulationInput(
            defaults=ThresholdConfig(discount_threshold=10)
        )
        result = run_simulation(sim_input, db_path)
        assert result.simulated.escalated > result.original.escalated

    def test_simulation_disable_rule(self, db_path):
        for _ in range(10):
            _process_and_store(_make_deal(discount_percentage=25), db_path)
        sim_input = SimulationInput(disabled_rules=["DISCOUNT_THRESHOLD"])
        result = run_simulation(sim_input, db_path)
        assert result.simulated.auto_approved > result.original.auto_approved

    def test_simulation_does_not_mutate_data(self, db_path):
        seed_deals(count=5, auto_process=True, db_path=db_path)
        m_before = compute_metrics(db_path)
        sim_input = SimulationInput(
            defaults=ThresholdConfig(discount_threshold=50)
        )
        run_simulation(sim_input, db_path)
        m_after = compute_metrics(db_path)
        assert m_before.total_deals == m_after.total_deals
        assert m_before.auto_approved == m_after.auto_approved
        assert m_before.escalated == m_after.escalated

    def test_simulation_result_structure(self, db_path):
        seed_deals(count=5, auto_process=True, db_path=db_path)
        result = run_simulation(SimulationInput(), db_path)
        assert result.original is not None
        assert result.simulated is not None
        assert "auto_approval_rate" in result.delta
        assert "escalation_rate" in result.delta
        assert "escalation_by_team" in result.delta
