"""Integration tests for advisory and pipeline endpoints."""

from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)

VALID_DEAL = {
    "deal_type": "New",
    "customer_segment": "Enterprise",
    "annual_contract_value": 100000,
    "discount_percentage": 15,
    "payment_terms_days": 30,
    "region": "NA",
    "custom_security_clause": False,
}


def deal_payload(**overrides) -> dict:
    return {**VALID_DEAL, **overrides}


# ---------------------------------------------------------------------------
# POST /deals/analyze-clause
# ---------------------------------------------------------------------------


class TestAnalyzeClauseEndpoint:
    def test_returns_200(self):
        resp = client.post(
            "/deals/analyze-clause",
            json={"clause_text": "Annual audit rights required."},
        )
        assert resp.status_code == 200

    def test_returns_advisory_shape(self):
        resp = client.post(
            "/deals/analyze-clause",
            json={"clause_text": "All data must remain in EU."},
        )
        body = resp.json()
        assert "summary" in body
        assert "risk_level" in body
        assert "categories" in body
        assert "confidence" in body
        assert "review_required" in body
        assert "raw_clause" in body

    def test_preserves_clause_text(self):
        clause = "Vendor must comply with SOC 2 Type II."
        resp = client.post(
            "/deals/analyze-clause", json={"clause_text": clause}
        )
        assert resp.json()["raw_clause"] == clause

    def test_empty_clause_returns_422(self):
        resp = client.post(
            "/deals/analyze-clause", json={"clause_text": ""}
        )
        assert resp.status_code == 422

    def test_missing_clause_returns_422(self):
        resp = client.post("/deals/analyze-clause", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /deals (full pipeline)
# ---------------------------------------------------------------------------


class TestPipelineEndpoint:
    def test_returns_201(self):
        resp = client.post("/deals", json=VALID_DEAL)
        assert resp.status_code == 201

    def test_pipeline_shape(self):
        resp = client.post("/deals", json=VALID_DEAL)
        body = resp.json()
        assert "deal" in body
        assert "decision" in body
        assert "advisory" in body

    def test_no_clause_advisory_is_null(self):
        resp = client.post("/deals", json=VALID_DEAL)
        body = resp.json()
        assert body["advisory"] is None

    def test_with_clause_advisory_populated(self):
        resp = client.post(
            "/deals",
            json=deal_payload(clause_text="Data must remain in EU."),
        )
        body = resp.json()
        assert body["advisory"] is not None
        assert body["advisory"]["summary"] is not None
        assert body["advisory"]["raw_clause"] == "Data must remain in EU."

    def test_advisory_does_not_affect_routing(self):
        # Same deal with and without clause — routing should be identical
        resp_no_clause = client.post("/deals", json=VALID_DEAL)
        resp_with_clause = client.post(
            "/deals",
            json=deal_payload(clause_text="Vendor indemnifies all IP claims."),
        )
        d1 = resp_no_clause.json()["decision"]
        d2 = resp_with_clause.json()["decision"]
        assert d1["approval_status"] == d2["approval_status"]
        assert d1["escalation_path"] == d2["escalation_path"]
        assert d1["priority"] == d2["priority"]

    def test_pipeline_with_escalation(self):
        resp = client.post(
            "/deals",
            json=deal_payload(
                discount_percentage=30,
                annual_contract_value=250000,
                clause_text="All source code placed in escrow.",
            ),
        )
        body = resp.json()
        assert body["decision"]["auto_approved"] is False
        assert body["decision"]["approval_status"] == "Escalated"
        assert body["advisory"] is not None

    def test_pipeline_invalid_input_returns_422(self):
        resp = client.post("/deals", json={"deal_type": "Bad"})
        assert resp.status_code == 422
