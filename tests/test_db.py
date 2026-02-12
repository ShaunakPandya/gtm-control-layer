"""Unit tests for the SQLite database layer."""

import tempfile
from pathlib import Path

import pytest

from app.db.database import (
    count_deals,
    count_overrides,
    get_all_deals,
    get_deal,
    get_overrides,
    get_overrides_for_deal,
    get_processed_deals,
    init_db,
    insert_deal,
    insert_override,
    reset_db,
    update_deal_decision,
)
from app.intake.models import DealInput, ValidatedDeal
from app.routing.engine import RoutingDecision, route_deal
from app.rules.config import RulesConfig
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


def _process_deal(deal: ValidatedDeal, db_path: Path):
    config = RulesConfig()
    evaluation = evaluate_deal(deal, config)
    decision = route_deal(evaluation, config)
    insert_deal(deal, db_path)
    update_deal_decision(deal.id, evaluation, decision, None, db_path)
    return decision


class TestDealCRUD:
    def test_insert_and_get(self, db_path):
        deal = _make_deal()
        insert_deal(deal, db_path)
        fetched = get_deal(deal.id, db_path)
        assert fetched is not None
        assert fetched["id"] == deal.id
        assert fetched["status"] == "validated"

    def test_update_decision(self, db_path):
        deal = _make_deal(discount_percentage=25)
        _process_deal(deal, db_path)
        fetched = get_deal(deal.id, db_path)
        assert fetched["status"] == "processed"
        assert fetched["decision_json"] is not None
        assert fetched["evaluation_json"] is not None

    def test_get_all_deals(self, db_path):
        for _ in range(3):
            deal = _make_deal()
            insert_deal(deal, db_path)
        assert len(get_all_deals(db_path)) == 3

    def test_get_processed_deals(self, db_path):
        d1 = _make_deal()
        d2 = _make_deal()
        insert_deal(d1, db_path)
        _process_deal(d2, db_path)
        processed = get_processed_deals(db_path)
        assert len(processed) == 1
        assert processed[0]["id"] == d2.id

    def test_count_deals(self, db_path):
        assert count_deals(db_path) == 0
        insert_deal(_make_deal(), db_path)
        assert count_deals(db_path) == 1

    def test_get_nonexistent_deal(self, db_path):
        assert get_deal("nonexistent", db_path) is None

    def test_reset_db(self, db_path):
        _process_deal(_make_deal(), db_path)
        assert count_deals(db_path) == 1
        reset_db(db_path)
        assert count_deals(db_path) == 0


class TestOverrideCRUD:
    def test_insert_and_get_override(self, db_path):
        deal = _make_deal(discount_percentage=25)
        decision = _process_deal(deal, db_path)
        oid = insert_override(
            deal.id, "Strategic deal", "Test notes",
            decision.model_dump_json(), "tester", db_path,
        )
        assert oid is not None
        overrides = get_overrides(db_path)
        assert len(overrides) == 1
        assert overrides[0]["deal_id"] == deal.id
        assert overrides[0]["override_reason"] == "Strategic deal"

    def test_override_updates_deal_status(self, db_path):
        deal = _make_deal(discount_percentage=25)
        decision = _process_deal(deal, db_path)
        insert_override(deal.id, "Test", None, decision.model_dump_json(), db_path=db_path)
        fetched = get_deal(deal.id, db_path)
        assert fetched["status"] == "overridden"

    def test_get_overrides_for_deal(self, db_path):
        deal = _make_deal(discount_percentage=25)
        decision = _process_deal(deal, db_path)
        insert_override(deal.id, "Reason1", None, decision.model_dump_json(), db_path=db_path)
        insert_override(deal.id, "Reason2", None, decision.model_dump_json(), db_path=db_path)
        overrides = get_overrides_for_deal(deal.id, db_path)
        assert len(overrides) == 2

    def test_count_overrides(self, db_path):
        assert count_overrides(db_path) == 0
        deal = _make_deal(discount_percentage=25)
        decision = _process_deal(deal, db_path)
        insert_override(deal.id, "Test", None, decision.model_dump_json(), db_path=db_path)
        assert count_overrides(db_path) == 1
