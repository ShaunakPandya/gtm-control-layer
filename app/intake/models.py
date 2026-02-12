from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DealType(StrEnum):
    NEW = "New"
    RENEWAL = "Renewal"
    EXPANSION = "Expansion"
    PILOT = "Pilot"


class CustomerSegment(StrEnum):
    ENTERPRISE = "Enterprise"
    MID_MARKET = "Mid-Market"
    SMB = "SMB"
    STRATEGIC = "Strategic"


class Region(StrEnum):
    NA = "NA"
    EU = "EU"
    UK = "UK"
    APAC = "APAC"
    LATAM = "LATAM"
    MEA = "MEA"


class DealInput(BaseModel):
    """Raw deal submission — validated on ingestion."""

    deal_type: DealType
    customer_segment: CustomerSegment
    annual_contract_value: float = Field(gt=0, description="ACV in USD, must be positive")
    discount_percentage: float = Field(
        ge=0, le=100, description="Discount as a percentage (0-100)"
    )
    payment_terms_days: int = Field(gt=0, description="Net payment terms in days")
    region: Region
    custom_security_clause: bool
    clause_text: Optional[str] = Field(
        default=None, description="Free-text contract clause for AI advisory"
    )

    @field_validator("clause_text")
    @classmethod
    def clause_text_not_empty_if_present(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() == "":
            raise ValueError("clause_text must not be empty when provided")
        return v


class ValidatedDeal(BaseModel):
    """Immutable deal object produced after successful validation."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    deal_type: DealType
    customer_segment: CustomerSegment
    annual_contract_value: float
    discount_percentage: float
    payment_terms_days: int
    region: Region
    custom_security_clause: bool
    clause_text: Optional[str] = None

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_input(cls, deal: DealInput) -> ValidatedDeal:
        return cls(**deal.model_dump())
