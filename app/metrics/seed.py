from __future__ import annotations

import random
from pathlib import Path
from typing import Optional

from app.advisory.client import analyze_clause
from app.db.database import init_db, insert_deal, reset_db, update_deal_decision
from app.intake.models import (
    CustomerSegment,
    DealInput,
    DealType,
    Region,
    ValidatedDeal,
)
from app.routing.engine import route_deal
from app.rules.config import load_config
from app.rules.engine import evaluate_deal

SAMPLE_CLAUSES = [
    "All data must be stored within the European Union at all times.",
    "Vendor shall provide annual SOC 2 Type II audit reports.",
    "All intellectual property created during the engagement belongs to the customer.",
    "Customer retains the right to conduct on-site security audits quarterly.",
    "Data must not be transferred outside of the originating jurisdiction.",
    "Vendor indemnifies customer against all third-party IP infringement claims.",
    "Source code shall be placed in escrow with a neutral third party.",
    "Customer may terminate for convenience with 30 days written notice.",
    None,
    None,
    None,
    None,
]


def generate_random_deal() -> DealInput:
    """Generate a random but realistic deal for demo purposes."""
    deal_type = random.choice(list(DealType))
    segment = random.choice(list(CustomerSegment))
    region = random.choice(list(Region))

    # ACV ranges by segment
    acv_ranges = {
        CustomerSegment.SMB: (5_000, 50_000),
        CustomerSegment.MID_MARKET: (25_000, 200_000),
        CustomerSegment.ENTERPRISE: (75_000, 500_000),
        CustomerSegment.STRATEGIC: (150_000, 1_000_000),
    }
    low, high = acv_ranges[segment]
    acv = round(random.uniform(low, high), -3)  # round to nearest 1000

    discount = round(random.uniform(0, 35), 1)
    payment_days = random.choice([15, 30, 45, 60, 90])
    security_clause = random.random() < 0.3
    clause_text = random.choice(SAMPLE_CLAUSES)

    return DealInput(
        deal_type=deal_type,
        customer_segment=segment,
        annual_contract_value=acv,
        discount_percentage=discount,
        payment_terms_days=payment_days,
        region=region,
        custom_security_clause=security_clause,
        clause_text=clause_text,
    )


def seed_deals(
    count: int = 50,
    auto_process: bool = True,
    db_path: Optional[Path] = None,
) -> list[str]:
    """Generate and optionally process N random deals. Returns deal IDs."""
    init_db(db_path)
    config = load_config()
    deal_ids: list[str] = []

    for _ in range(count):
        deal_input = generate_random_deal()
        validated = ValidatedDeal.from_input(deal_input)
        insert_deal(validated, db_path)
        deal_ids.append(validated.id)

        if auto_process:
            evaluation = evaluate_deal(validated, config)
            decision = route_deal(evaluation, config)
            advisory = None
            if validated.clause_text:
                advisory = analyze_clause(validated.clause_text)
            update_deal_decision(
                validated.id, evaluation, decision, advisory, db_path
            )

    return deal_ids


def reset_and_seed(
    count: int = 50,
    db_path: Optional[Path] = None,
) -> list[str]:
    """Reset the database and seed with fresh data."""
    init_db(db_path)
    reset_db(db_path)
    return seed_deals(count, auto_process=True, db_path=db_path)
