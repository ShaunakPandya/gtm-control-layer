"""Unit tests for rules config loading and segment override resolution."""

import json
import tempfile
from pathlib import Path

from app.rules.config import (
    PriorityCutoffs,
    RulesConfig,
    ThresholdConfig,
    load_config,
)


# ---------------------------------------------------------------------------
# ThresholdConfig defaults
# ---------------------------------------------------------------------------


class TestThresholdConfigDefaults:
    def test_default_values(self):
        t = ThresholdConfig()
        assert t.discount_threshold == 20
        assert t.acv_exec_threshold == 150_000
        assert t.payment_terms_limit == 45
        assert t.eu_requires_legal is True


# ---------------------------------------------------------------------------
# RulesConfig.resolve_thresholds
# ---------------------------------------------------------------------------


class TestResolveThresholds:
    def test_no_override_returns_defaults(self):
        config = RulesConfig()
        resolved = config.resolve_thresholds("Mid-Market")
        assert resolved.discount_threshold == 20
        assert resolved.acv_exec_threshold == 150_000

    def test_segment_override_merges_partial(self):
        config = RulesConfig(
            segment_overrides={
                "Enterprise": ThresholdConfig(discount_threshold=25),
            }
        )
        resolved = config.resolve_thresholds("Enterprise")
        assert resolved.discount_threshold == 25
        # Non-overridden values fall back to defaults in the override object
        # (ThresholdConfig fills defaults for unset fields)
        assert resolved.acv_exec_threshold == 150_000

    def test_segment_override_full(self):
        config = RulesConfig(
            segment_overrides={
                "SMB": ThresholdConfig(
                    discount_threshold=10,
                    acv_exec_threshold=50_000,
                    payment_terms_limit=30,
                    eu_requires_legal=False,
                ),
            }
        )
        resolved = config.resolve_thresholds("SMB")
        assert resolved.discount_threshold == 10
        assert resolved.acv_exec_threshold == 50_000
        assert resolved.payment_terms_limit == 30
        assert resolved.eu_requires_legal is False

    def test_unknown_segment_returns_defaults(self):
        config = RulesConfig(
            segment_overrides={
                "Enterprise": ThresholdConfig(discount_threshold=25),
            }
        )
        resolved = config.resolve_thresholds("Strategic")
        assert resolved.discount_threshold == 20


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_load_from_project_config(self):
        config = load_config()
        assert config.defaults.discount_threshold == 20
        assert "Enterprise" in config.segment_overrides
        assert config.escalation_order[0] == "Finance"

    def test_load_from_custom_path(self):
        data = {
            "defaults": {"discount_threshold": 50},
            "segment_overrides": {},
            "escalation_order": ["Security"],
            "rule_weights": {"DISCOUNT_THRESHOLD": 5},
            "priority_cutoffs": {"P1": 10, "P2": 5, "P3": 1},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            f.flush()
            config = load_config(f.name)
        assert config.defaults.discount_threshold == 50
        assert config.escalation_order == ["Security"]
        assert config.rule_weights["DISCOUNT_THRESHOLD"] == 5

    def test_missing_file_returns_defaults(self):
        config = load_config("/nonexistent/path/rules.json")
        assert config.defaults.discount_threshold == 20

    def test_config_has_priority_cutoffs(self):
        config = load_config()
        assert config.priority_cutoffs.P1 == 5
        assert config.priority_cutoffs.P2 == 3
        assert config.priority_cutoffs.P3 == 1

    def test_config_has_rule_weights(self):
        config = load_config()
        assert "DISCOUNT_THRESHOLD" in config.rule_weights
        assert "ACV_EXEC_THRESHOLD" in config.rule_weights
        assert "CUSTOM_SECURITY_CLAUSE" in config.rule_weights
