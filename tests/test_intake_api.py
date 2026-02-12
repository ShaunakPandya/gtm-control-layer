"""Integration tests for the /deals/validate endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)

VALID_PAYLOAD = {
    "deal_type": "New",
    "customer_segment": "Enterprise",
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


class TestValidateEndpointHappy:
    def test_valid_deal_returns_201(self):
        resp = client.post("/deals/validate", json=VALID_PAYLOAD)
        assert resp.status_code == 201

    def test_valid_deal_returns_id(self):
        resp = client.post("/deals/validate", json=VALID_PAYLOAD)
        body = resp.json()
        assert "id" in body
        assert len(body["id"]) == 32

    def test_valid_deal_returns_created_at(self):
        resp = client.post("/deals/validate", json=VALID_PAYLOAD)
        body = resp.json()
        assert "created_at" in body

    def test_valid_deal_preserves_fields(self):
        resp = client.post("/deals/validate", json=VALID_PAYLOAD)
        body = resp.json()
        assert body["deal_type"] == "New"
        assert body["customer_segment"] == "Enterprise"
        assert body["annual_contract_value"] == 100000
        assert body["discount_percentage"] == 15
        assert body["payment_terms_days"] == 30
        assert body["region"] == "NA"
        assert body["custom_security_clause"] is False
        assert body["clause_text"] is None

    def test_deal_with_clause_text(self):
        resp = client.post(
            "/deals/validate",
            json=payload(clause_text="Annual audit rights required."),
        )
        assert resp.status_code == 201
        assert resp.json()["clause_text"] == "Annual audit rights required."

    def test_all_deal_types_accepted(self):
        for dt in ["New", "Renewal", "Expansion", "Pilot"]:
            resp = client.post("/deals/validate", json=payload(deal_type=dt))
            assert resp.status_code == 201, f"Failed for deal_type={dt}"

    def test_all_segments_accepted(self):
        for seg in ["Enterprise", "Mid-Market", "SMB", "Strategic"]:
            resp = client.post("/deals/validate", json=payload(customer_segment=seg))
            assert resp.status_code == 201, f"Failed for segment={seg}"

    def test_all_regions_accepted(self):
        for reg in ["NA", "EU", "UK", "APAC", "LATAM", "MEA"]:
            resp = client.post("/deals/validate", json=payload(region=reg))
            assert resp.status_code == 201, f"Failed for region={reg}"


# ---------------------------------------------------------------------------
# RFC 7807 error responses
# ---------------------------------------------------------------------------


class TestValidateEndpointErrors:
    def test_missing_field_returns_422(self):
        data = payload()
        del data["deal_type"]
        resp = client.post("/deals/validate", json=data)
        assert resp.status_code == 422

    def test_error_is_rfc7807_format(self):
        resp = client.post("/deals/validate", json={})
        body = resp.json()
        assert body["type"] == "urn:gtm:error:validation"
        assert body["title"] == "Validation Error"
        assert body["status"] == 422
        assert "detail" in body
        assert "errors" in body

    def test_error_lists_all_missing_fields(self):
        resp = client.post("/deals/validate", json={})
        body = resp.json()
        fields = {e["field"] for e in body["errors"]}
        assert "deal_type" in fields
        assert "customer_segment" in fields
        assert "annual_contract_value" in fields

    def test_invalid_enum_returns_422(self):
        resp = client.post("/deals/validate", json=payload(region="MARS"))
        assert resp.status_code == 422
        body = resp.json()
        assert any("region" in e["field"] for e in body["errors"])

    def test_negative_acv_returns_422(self):
        resp = client.post("/deals/validate", json=payload(annual_contract_value=-1))
        assert resp.status_code == 422

    def test_discount_over_100_returns_422(self):
        resp = client.post("/deals/validate", json=payload(discount_percentage=150))
        assert resp.status_code == 422

    def test_empty_clause_text_returns_422(self):
        resp = client.post("/deals/validate", json=payload(clause_text=""))
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
