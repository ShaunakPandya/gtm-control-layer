from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from app.db.database import count_overrides, get_all_deals, get_overrides


class MetricsSummary(BaseModel):
    total_deals: int
    auto_approved: int
    escalated: int
    overridden: int
    auto_approval_rate: float
    escalation_rate: float
    override_rate: float
    escalation_by_team: dict[str, int]
    top_rule_triggers: list[dict[str, Any]]
    override_by_reason: dict[str, int]
    override_by_team: dict[str, int]


def compute_metrics(db_path: Optional[Path] = None) -> MetricsSummary:
    deals = get_all_deals(db_path)
    overrides = get_overrides(db_path)

    total = len(deals)
    auto_approved = 0
    escalated = 0
    team_counter: Counter[str] = Counter()
    rule_counter: Counter[str] = Counter()

    for deal in deals:
        decision = deal.get("decision_json")
        if not decision:
            continue
        if decision.get("auto_approved"):
            auto_approved += 1
        else:
            escalated += 1
            for team in decision.get("escalation_path", []):
                team_counter[team] += 1

        for trigger in decision.get("rule_triggers", []):
            if trigger.get("triggered"):
                rule_counter[trigger["rule_id"]] += 1

    overridden = len(overrides)

    # Override breakdowns
    reason_counter: Counter[str] = Counter()
    override_team_counter: Counter[str] = Counter()
    for ov in overrides:
        reason_counter[ov["override_reason"]] += 1
        # Parse original decision to get teams
        orig = ov.get("original_decision_json")
        if orig:
            import json
            try:
                orig_dec = json.loads(orig) if isinstance(orig, str) else orig
                for team in orig_dec.get("escalation_path", []):
                    override_team_counter[team] += 1
            except (json.JSONDecodeError, TypeError):
                pass

    processed = auto_approved + escalated
    return MetricsSummary(
        total_deals=total,
        auto_approved=auto_approved,
        escalated=escalated,
        overridden=overridden,
        auto_approval_rate=auto_approved / processed if processed > 0 else 0.0,
        escalation_rate=escalated / processed if processed > 0 else 0.0,
        override_rate=overridden / processed if processed > 0 else 0.0,
        escalation_by_team=dict(team_counter.most_common()),
        top_rule_triggers=[
            {"rule_id": rule, "count": count}
            for rule, count in rule_counter.most_common()
        ],
        override_by_reason=dict(reason_counter.most_common()),
        override_by_team=dict(override_team_counter.most_common()),
    )
