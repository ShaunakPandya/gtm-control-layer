"""Integration tests for Feature 5 API endpoints: metrics, override, simulation, seed."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Use a temp DB for tests
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["GTM_DB_PATH"] = _tmp.name
_tmp.close()

from app.api.main import app
from app.db.database import init_db, reset_db

client = TestClient(app)

VALID_DEAL = {
    "deal_type": "New",
    "customer_segment": "Mid-Market",
    "annual_contract_value": 100000,
    "discount_percentage": 15,
    "payment_terms_days": 30,
    "region": "NA",
    "custom_security_clause": False,
}

ESCALATED_DEAL = {
    "deal_type": "New",
    "customer_segment": "Mid-Market",
    "annual_contract_value": 100000,
    "discount_percentage": 25,
    "payment_terms_days": 30,
    "region": "NA",
    "custom_security_clause": False,
}


@pytest.fixture(autouse=True)
def _clean_db():
    init_db()
    reset_db()
    yield
    reset_db()


# ---------------------------------------------------------------------------
# Pipeline persistence
# ---------------------------------------------------------------------------


class TestPipelinePersistence:
    def test_deal_persisted_after_pipeline(self):
        client.post("/deals", json=VALID_DEAL)
        resp = client.get("/deals/list")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_multiple_deals_persisted(self):
        client.post("/deals", json=VALID_DEAL)
        client.post("/deals", json=ESCALATED_DEAL)
        resp = client.get("/deals/list")
        assert resp.json()["total"] == 2


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestMetricsEndpoint:
    def test_metrics_empty(self):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert resp.json()["total_deals"] == 0

    def test_metrics_after_deals(self):
        client.post("/deals", json=VALID_DEAL)
        client.post("/deals", json=ESCALATED_DEAL)
        resp = client.get("/metrics")
        body = resp.json()
        assert body["total_deals"] == 2
        assert body["auto_approved"] == 1
        assert body["escalated"] == 1
        assert body["auto_approval_rate"] == 0.5

    def test_metrics_shape(self):
        resp = client.get("/metrics")
        body = resp.json()
        assert "escalation_by_team" in body
        assert "top_rule_triggers" in body
        assert "override_rate" in body


# ---------------------------------------------------------------------------
# Override
# ---------------------------------------------------------------------------


class TestOverrideEndpoint:
    def test_override_escalated_deal(self):
        deal_resp = client.post("/deals", json=ESCALATED_DEAL).json()
        deal_id = deal_resp["deal"]["id"]
        resp = client.post(
            f"/deals/{deal_id}/override",
            json={"override_reason": "Strategic deal", "override_notes": "Test"},
        )
        assert resp.status_code == 201
        assert resp.json()["deal_id"] == deal_id

    def test_cannot_override_auto_approved(self):
        deal_resp = client.post("/deals", json=VALID_DEAL).json()
        deal_id = deal_resp["deal"]["id"]
        resp = client.post(
            f"/deals/{deal_id}/override",
            json={"override_reason": "Test"},
        )
        assert resp.status_code == 400

    def test_override_nonexistent_deal(self):
        resp = client.post(
            "/deals/nonexistent/override",
            json={"override_reason": "Test"},
        )
        assert resp.status_code == 404

    def test_override_shows_in_metrics(self):
        deal_resp = client.post("/deals", json=ESCALATED_DEAL).json()
        deal_id = deal_resp["deal"]["id"]
        client.post(
            f"/deals/{deal_id}/override",
            json={"override_reason": "Strategic deal"},
        )
        metrics = client.get("/metrics").json()
        assert metrics["overridden"] == 1


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------


class TestSeedEndpoint:
    def test_seed_generates_deals(self):
        resp = client.post("/seed", json={"count": 10, "auto_process": True})
        assert resp.status_code == 201
        assert resp.json()["generated"] == 10
        deals = client.get("/deals/list").json()
        assert deals["total"] == 10

    def test_reset_and_seed(self):
        client.post("/seed", json={"count": 5})
        resp = client.post("/seed/reset", json={"count": 10})
        assert resp.status_code == 201
        assert resp.json()["generated"] == 10
        deals = client.get("/deals/list").json()
        assert deals["total"] == 10  # old 5 wiped, new 10 created


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


class TestSimulationEndpoint:
    def test_simulation_returns_result(self):
        client.post("/seed", json={"count": 20, "auto_process": True})
        resp = client.post("/simulate", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert "original" in body
        assert "simulated" in body
        assert "delta" in body

    def test_simulation_with_config_change(self):
        client.post("/seed", json={"count": 20, "auto_process": True})
        resp = client.post(
            "/simulate",
            json={
                "defaults": {"discount_threshold": 50, "acv_exec_threshold": 1000000,
                             "payment_terms_limit": 120, "eu_requires_legal": False},
                "disabled_rules": [],
            },
        )
        body = resp.json()
        # Very loose thresholds → more auto-approvals
        assert body["simulated"]["auto_approved"] >= body["original"]["auto_approved"]

    def test_simulation_with_disabled_rules(self):
        # Seed deals that will have discount triggers
        for _ in range(5):
            client.post("/deals", json=ESCALATED_DEAL)

        resp = client.post(
            "/simulate",
            json={"disabled_rules": ["DISCOUNT_THRESHOLD"]},
        )
        body = resp.json()
        assert body["simulated"]["auto_approved"] >= body["original"]["auto_approved"]
