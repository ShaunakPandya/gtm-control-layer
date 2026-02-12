"""Integration tests for the /deals/route endpoint."""

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


class TestRouteEndpointHappy:
    def test_returns_200(self):
        resp = client.post("/deals/route", json=VALID_PAYLOAD)
        assert resp.status_code == 200

    def test_response_shape(self):
        resp = client.post("/deals/route", json=VALID_PAYLOAD)
        body = resp.json()
        assert "deal_id" in body
        assert "approval_status" in body
        assert "escalation_path" in body
        assert "rule_triggers" in body
        assert "auto_approved" in body
        assert "priority" in body
        assert "total_weight" in body

    def test_safe_deal_auto_approved(self):
        resp = client.post("/deals/route", json=VALID_PAYLOAD)
        body = resp.json()
        assert body["auto_approved"] is True
        assert body["approval_status"] == "Auto-Approved"
        assert body["escalation_path"] == []
        assert body["priority"] == "None"

    def test_discount_escalates(self):
        resp = client.post(
            "/deals/route", json=payload(discount_percentage=30)
        )
        body = resp.json()
        assert body["auto_approved"] is False
        assert body["approval_status"] == "Escalated"
        assert "Finance" in body["escalation_path"]

    def test_multi_trigger_full_path(self):
        resp = client.post(
            "/deals/route",
            json=payload(
                discount_percentage=30,
                annual_contract_value=200000,
                region="EU",
                payment_terms_days=60,
                custom_security_clause=True,
            ),
        )
        body = resp.json()
        assert body["escalation_path"] == ["Finance", "Legal", "Security", "Exec"]
        assert body["priority"] == "P1"
        assert body["total_weight"] == 11

    def test_segment_override_affects_routing(self):
        # Enterprise discount threshold is 25 in config
        # 22% discount: no trigger for Enterprise, would trigger for Mid-Market
        resp_ent = client.post(
            "/deals/route",
            json=payload(customer_segment="Enterprise", discount_percentage=22),
        )
        resp_mm = client.post(
            "/deals/route",
            json=payload(customer_segment="Mid-Market", discount_percentage=22),
        )
        assert resp_ent.json()["auto_approved"] is True
        assert resp_mm.json()["auto_approved"] is False

    def test_deduplication_discount_and_payment(self):
        resp = client.post(
            "/deals/route",
            json=payload(discount_percentage=25, payment_terms_days=60),
        )
        body = resp.json()
        # Both trigger Finance — should appear only once
        assert body["escalation_path"] == ["Finance"]


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestRouteEndpointErrors:
    def test_invalid_input_returns_422(self):
        resp = client.post("/deals/route", json={"deal_type": "Bad"})
        assert resp.status_code == 422
        assert resp.json()["type"] == "urn:gtm:error:validation"
