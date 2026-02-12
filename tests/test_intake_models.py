"""Unit tests for deal intake models and validation."""

import pytest
from pydantic import ValidationError

from app.intake.models import (
    CustomerSegment,
    DealInput,
    DealType,
    Region,
    ValidatedDeal,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_DEAL = dict(
    deal_type="New",
    customer_segment="Enterprise",
    annual_contract_value=100_000,
    discount_percentage=15,
    payment_terms_days=30,
    region="NA",
    custom_security_clause=False,
)


def make_deal(**overrides) -> dict:
    return {**VALID_DEAL, **overrides}


# ---------------------------------------------------------------------------
# DealInput – happy path
# ---------------------------------------------------------------------------


class TestDealInputValid:
    def test_minimal_valid_deal(self):
        deal = DealInput(**VALID_DEAL)
        assert deal.deal_type == DealType.NEW
        assert deal.customer_segment == CustomerSegment.ENTERPRISE
        assert deal.annual_contract_value == 100_000
        assert deal.discount_percentage == 15
        assert deal.payment_terms_days == 30
        assert deal.region == Region.NA
        assert deal.custom_security_clause is False
        assert deal.clause_text is None

    def test_deal_with_clause_text(self):
        deal = DealInput(**make_deal(clause_text="All data must remain in EU."))
        assert deal.clause_text == "All data must remain in EU."

    def test_all_deal_types(self):
        for dt in DealType:
            deal = DealInput(**make_deal(deal_type=dt.value))
            assert deal.deal_type == dt

    def test_all_customer_segments(self):
        for seg in CustomerSegment:
            deal = DealInput(**make_deal(customer_segment=seg.value))
            assert deal.customer_segment == seg

    def test_all_regions(self):
        for reg in Region:
            deal = DealInput(**make_deal(region=reg.value))
            assert deal.region == reg

    def test_boundary_discount_zero(self):
        deal = DealInput(**make_deal(discount_percentage=0))
        assert deal.discount_percentage == 0

    def test_boundary_discount_hundred(self):
        deal = DealInput(**make_deal(discount_percentage=100))
        assert deal.discount_percentage == 100

    def test_custom_security_clause_true(self):
        deal = DealInput(**make_deal(custom_security_clause=True))
        assert deal.custom_security_clause is True


# ---------------------------------------------------------------------------
# DealInput – invalid type rejected
# ---------------------------------------------------------------------------


class TestDealInputInvalidType:
    def test_invalid_deal_type(self):
        with pytest.raises(ValidationError) as exc_info:
            DealInput(**make_deal(deal_type="InvalidType"))
        assert "deal_type" in str(exc_info.value)

    def test_invalid_customer_segment(self):
        with pytest.raises(ValidationError) as exc_info:
            DealInput(**make_deal(customer_segment="Tiny"))
        assert "customer_segment" in str(exc_info.value)

    def test_invalid_region(self):
        with pytest.raises(ValidationError) as exc_info:
            DealInput(**make_deal(region="MARS"))
        assert "region" in str(exc_info.value)

    def test_acv_as_string(self):
        with pytest.raises(ValidationError):
            DealInput(**make_deal(annual_contract_value="not-a-number"))

    def test_discount_as_string(self):
        with pytest.raises(ValidationError):
            DealInput(**make_deal(discount_percentage="high"))

    def test_payment_terms_as_string(self):
        with pytest.raises(ValidationError):
            DealInput(**make_deal(payment_terms_days="thirty"))

    def test_security_clause_non_bool_string(self):
        with pytest.raises(ValidationError):
            DealInput(**make_deal(custom_security_clause="not-a-bool"))


# ---------------------------------------------------------------------------
# DealInput – missing field rejected
# ---------------------------------------------------------------------------


class TestDealInputMissingField:
    @pytest.mark.parametrize(
        "field",
        [
            "deal_type",
            "customer_segment",
            "annual_contract_value",
            "discount_percentage",
            "payment_terms_days",
            "region",
            "custom_security_clause",
        ],
    )
    def test_missing_required_field(self, field: str):
        data = make_deal()
        del data[field]
        with pytest.raises(ValidationError) as exc_info:
            DealInput(**data)
        assert field in str(exc_info.value)


# ---------------------------------------------------------------------------
# DealInput – boundary / constraint violations
# ---------------------------------------------------------------------------


class TestDealInputConstraints:
    def test_acv_zero_rejected(self):
        with pytest.raises(ValidationError):
            DealInput(**make_deal(annual_contract_value=0))

    def test_acv_negative_rejected(self):
        with pytest.raises(ValidationError):
            DealInput(**make_deal(annual_contract_value=-5000))

    def test_discount_negative_rejected(self):
        with pytest.raises(ValidationError):
            DealInput(**make_deal(discount_percentage=-1))

    def test_discount_over_100_rejected(self):
        with pytest.raises(ValidationError):
            DealInput(**make_deal(discount_percentage=101))

    def test_payment_terms_zero_rejected(self):
        with pytest.raises(ValidationError):
            DealInput(**make_deal(payment_terms_days=0))

    def test_payment_terms_negative_rejected(self):
        with pytest.raises(ValidationError):
            DealInput(**make_deal(payment_terms_days=-10))

    def test_empty_clause_text_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            DealInput(**make_deal(clause_text=""))
        assert "clause_text" in str(exc_info.value)

    def test_whitespace_only_clause_text_rejected(self):
        with pytest.raises(ValidationError):
            DealInput(**make_deal(clause_text="   "))


# ---------------------------------------------------------------------------
# ValidatedDeal
# ---------------------------------------------------------------------------


class TestValidatedDeal:
    def test_from_input_preserves_fields(self):
        inp = DealInput(**VALID_DEAL)
        validated = ValidatedDeal.from_input(inp)

        assert validated.deal_type == inp.deal_type
        assert validated.customer_segment == inp.customer_segment
        assert validated.annual_contract_value == inp.annual_contract_value
        assert validated.discount_percentage == inp.discount_percentage
        assert validated.payment_terms_days == inp.payment_terms_days
        assert validated.region == inp.region
        assert validated.custom_security_clause == inp.custom_security_clause
        assert validated.clause_text == inp.clause_text

    def test_from_input_generates_id(self):
        validated = ValidatedDeal.from_input(DealInput(**VALID_DEAL))
        assert validated.id is not None
        assert len(validated.id) == 32  # hex uuid4

    def test_from_input_generates_timestamp(self):
        validated = ValidatedDeal.from_input(DealInput(**VALID_DEAL))
        assert validated.created_at is not None

    def test_two_deals_get_unique_ids(self):
        v1 = ValidatedDeal.from_input(DealInput(**VALID_DEAL))
        v2 = ValidatedDeal.from_input(DealInput(**VALID_DEAL))
        assert v1.id != v2.id

    def test_validated_deal_is_frozen(self):
        validated = ValidatedDeal.from_input(DealInput(**VALID_DEAL))
        with pytest.raises(ValidationError):
            validated.discount_percentage = 99

    def test_input_not_mutated(self):
        data = make_deal()
        original_data = data.copy()
        inp = DealInput(**data)
        ValidatedDeal.from_input(inp)
        # original dict unchanged
        assert data == original_data
