"""Integration tests for the /deals/evaluate endpoint."""

from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)

VALID_PAYLOAD = {
    "deal_type": "New",
    "customer_segment": "Mid-Market",
    "annual_contract_value": 100000,
    "discount_percentage": 15,
    "payment_terms_days": 30,
    "region": "NA",
    "custom_security_clause": False,
}


def payload(**overrides) -> dict:
    return {**VALID_PAYLOAD, **overrides}


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestEvaluateEndpointHappy:
    def test_returns_200(self):
        resp = client.post("/deals/evaluate", json=VALID_PAYLOAD)
        assert resp.status_code == 200

    def test_returns_evaluation_result_shape(self):
        resp = client.post("/deals/evaluate", json=VALID_PAYLOAD)
        body = resp.json()
        assert "deal_id" in body
        assert "triggers" in body
        assert "total_weight" in body
        assert "priority" in body
        assert isinstance(body["triggers"], list)
        assert len(body["triggers"]) == 5

    def test_no_triggers_on_safe_deal(self):
        resp = client.post("/deals/evaluate", json=VALID_PAYLOAD)
        body = resp.json()
        triggered = [t for t in body["triggers"] if t["triggered"]]
        assert len(triggered) == 0
        assert body["priority"] == "None"

    def test_discount_triggers_via_api(self):
        resp = client.post(
            "/deals/evaluate", json=payload(discount_percentage=30)
        )
        body = resp.json()
        triggered = {t["rule_id"] for t in body["triggers"] if t["triggered"]}
        assert "DISCOUNT_THRESHOLD" in triggered

    def test_multi_trigger_via_api(self):
        resp = client.post(
            "/deals/evaluate",
            json=payload(
                discount_percentage=30,
                annual_contract_value=200000,
                region="EU",
                payment_terms_days=60,
                custom_security_clause=True,
            ),
        )
        body = resp.json()
        triggered = {t["rule_id"] for t in body["triggers"] if t["triggered"]}
        assert len(triggered) == 5
        assert body["priority"] == "P1"

    def test_segment_override_applied(self):
        # Enterprise has discount_threshold=25 in config/rules.json
        resp = client.post(
            "/deals/evaluate",
            json=payload(
                customer_segment="Enterprise", discount_percentage=22
            ),
        )
        body = resp.json()
        discount_trigger = next(
            t for t in body["triggers"] if t["rule_id"] == "DISCOUNT_THRESHOLD"
        )
        # 22% < 25% (Enterprise threshold) → should NOT trigger
        assert discount_trigger["triggered"] is False


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestEvaluateEndpointErrors:
    def test_invalid_input_returns_422(self):
        resp = client.post("/deals/evaluate", json={"deal_type": "Invalid"})
        assert resp.status_code == 422
        body = resp.json()
        assert body["type"] == "urn:gtm:error:validation"
