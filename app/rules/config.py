from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ThresholdConfig(BaseModel):
    """Threshold values for rule evaluation."""

    discount_threshold: float = 20
    acv_exec_threshold: float = 150_000
    payment_terms_limit: int = 45
    eu_requires_legal: bool = True


class PriorityCutoffs(BaseModel):
    """Score boundaries for priority tiers. Score >= cutoff assigns that tier."""

    P1: int = 5
    P2: int = 3
    P3: int = 1


class RulesConfig(BaseModel):
    """Top-level config loaded from rules.json."""

    defaults: ThresholdConfig = Field(default_factory=ThresholdConfig)
    segment_overrides: dict[str, ThresholdConfig] = Field(default_factory=dict)
    escalation_order: list[str] = Field(
        default_factory=lambda: ["Finance", "Legal", "Security", "Exec"]
    )
    rule_weights: dict[str, int] = Field(
        default_factory=lambda: {
            "DISCOUNT_THRESHOLD": 2,
            "ACV_EXEC_THRESHOLD": 3,
            "EU_LEGAL_REVIEW": 2,
            "PAYMENT_TERMS_LIMIT": 1,
            "CUSTOM_SECURITY_CLAUSE": 3,
        }
    )
    priority_cutoffs: PriorityCutoffs = Field(default_factory=PriorityCutoffs)

    def resolve_thresholds(self, segment: str) -> ThresholdConfig:
        """Return merged thresholds: defaults overridden by segment-specific values."""
        if segment not in self.segment_overrides:
            return self.defaults
        base = self.defaults.model_dump()
        override = self.segment_overrides[segment].model_dump(exclude_unset=True)
        base.update(override)
        return ThresholdConfig(**base)


def load_config(path: Optional[str | Path] = None) -> RulesConfig:
    """Load rules config from a JSON file. Falls back to built-in defaults."""
    if path is None:
        path = Path(__file__).resolve().parent.parent.parent / "config" / "rules.json"
    else:
        path = Path(path)

    if not path.exists():
        return RulesConfig()

    with open(path) as f:
        raw = json.load(f)
    return RulesConfig(**raw)
