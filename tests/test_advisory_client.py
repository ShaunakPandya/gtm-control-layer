"""Unit tests for the AI clause advisory client."""

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.advisory.client import (
    MAX_RETRIES,
    _mock_analyze,
    _parse_advisory,
    _live_analyze,
    analyze_clause,
)
from app.advisory.models import ClauseAdvisory, ClauseCategory, RiskLevel

SAMPLE_CLAUSE = "All data must be stored within the European Union and subject to annual third-party audits."


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------


class TestMockAnalyze:
    def test_returns_clause_advisory(self):
        result = _mock_analyze(SAMPLE_CLAUSE)
        assert isinstance(result, ClauseAdvisory)

    def test_mock_has_summary(self):
        result = _mock_analyze(SAMPLE_CLAUSE)
        assert len(result.summary) > 0

    def test_mock_has_valid_risk_level(self):
        result = _mock_analyze(SAMPLE_CLAUSE)
        assert result.risk_level in list(RiskLevel)

    def test_mock_has_categories(self):
        result = _mock_analyze(SAMPLE_CLAUSE)
        assert len(result.categories) >= 1
        for cat in result.categories:
            assert cat in list(ClauseCategory)

    def test_mock_has_confidence(self):
        result = _mock_analyze(SAMPLE_CLAUSE)
        assert 0 <= result.confidence <= 1

    def test_mock_preserves_raw_clause(self):
        result = _mock_analyze(SAMPLE_CLAUSE)
        assert result.raw_clause == SAMPLE_CLAUSE

    def test_mock_model_is_mock(self):
        result = _mock_analyze(SAMPLE_CLAUSE)
        assert result.model_used == "mock"

    def test_mock_high_confidence_no_review(self):
        result = _mock_analyze(SAMPLE_CLAUSE)
        assert result.confidence >= 0.75
        assert result.review_required is False

    def test_mock_is_deterministic(self):
        r1 = _mock_analyze(SAMPLE_CLAUSE)
        r2 = _mock_analyze(SAMPLE_CLAUSE)
        assert r1.summary == r2.summary
        assert r1.risk_level == r2.risk_level
        assert r1.categories == r2.categories


# ---------------------------------------------------------------------------
# _parse_advisory
# ---------------------------------------------------------------------------


class TestParseAdvisory:
    def test_valid_json_parses(self):
        raw = json.dumps({
            "summary": "Requires EU data residency.",
            "risk_level": "High",
            "categories": ["Data Residency"],
            "confidence": 0.92,
        })
        result = _parse_advisory(raw, SAMPLE_CLAUSE, "test-model")
        assert result.summary == "Requires EU data residency."
        assert result.risk_level == RiskLevel.HIGH
        assert result.categories == [ClauseCategory.DATA_RESIDENCY]
        assert result.confidence == 0.92
        assert result.review_required is False
        assert result.model_used == "test-model"

    def test_multiple_categories(self):
        raw = json.dumps({
            "summary": "Audit and IP clause.",
            "risk_level": "Medium",
            "categories": ["Audit", "IP"],
            "confidence": 0.80,
        })
        result = _parse_advisory(raw, SAMPLE_CLAUSE, "test-model")
        assert result.categories == [ClauseCategory.AUDIT, ClauseCategory.IP]

    def test_low_confidence_flags_review(self):
        raw = json.dumps({
            "summary": "Unclear clause.",
            "risk_level": "Low",
            "categories": ["Other"],
            "confidence": 0.60,
        })
        result = _parse_advisory(raw, SAMPLE_CLAUSE, "test-model")
        assert result.confidence == 0.60
        assert result.review_required is True

    def test_confidence_exactly_075_no_review(self):
        raw = json.dumps({
            "summary": "Borderline clause.",
            "risk_level": "Low",
            "categories": ["Other"],
            "confidence": 0.75,
        })
        result = _parse_advisory(raw, SAMPLE_CLAUSE, "test-model")
        assert result.review_required is False

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_advisory("not json", SAMPLE_CLAUSE, "test-model")

    def test_missing_field_raises(self):
        raw = json.dumps({"summary": "test"})
        with pytest.raises((KeyError, ValidationError)):
            _parse_advisory(raw, SAMPLE_CLAUSE, "test-model")

    def test_invalid_risk_level_raises(self):
        raw = json.dumps({
            "summary": "test",
            "risk_level": "Critical",
            "categories": ["Other"],
            "confidence": 0.8,
        })
        with pytest.raises(ValueError):
            _parse_advisory(raw, SAMPLE_CLAUSE, "test-model")

    def test_invalid_category_raises(self):
        raw = json.dumps({
            "summary": "test",
            "risk_level": "Low",
            "categories": ["NotACategory"],
            "confidence": 0.8,
        })
        with pytest.raises(ValueError):
            _parse_advisory(raw, SAMPLE_CLAUSE, "test-model")


# ---------------------------------------------------------------------------
# Live mode with mocked Anthropic client
# ---------------------------------------------------------------------------


def _make_mock_response(text: str) -> MagicMock:
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


class TestLiveAnalyze:
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key", "CLAUDE_MODEL": "test-model"})
    @patch("app.advisory.client.anthropic")
    def test_successful_call(self, mock_anthropic):
        valid_response = json.dumps({
            "summary": "EU data residency required.",
            "risk_level": "High",
            "categories": ["Data Residency"],
            "confidence": 0.95,
        })
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(valid_response)
        mock_anthropic.Anthropic.return_value = mock_client

        result = _live_analyze(SAMPLE_CLAUSE)
        assert result.risk_level == RiskLevel.HIGH
        assert result.confidence == 0.95
        assert result.review_required is False
        assert result.model_used == "test-model"

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("app.advisory.client.anthropic")
    def test_retry_on_invalid_json(self, mock_anthropic):
        valid_response = json.dumps({
            "summary": "OK.",
            "risk_level": "Low",
            "categories": ["Other"],
            "confidence": 0.80,
        })
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            _make_mock_response("not valid json"),
            _make_mock_response(valid_response),
        ]
        mock_anthropic.Anthropic.return_value = mock_client

        result = _live_analyze(SAMPLE_CLAUSE)
        assert result.risk_level == RiskLevel.LOW
        assert mock_client.messages.create.call_count == 2

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("app.advisory.client.anthropic")
    def test_all_retries_exhausted_flags_review(self, mock_anthropic):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            _make_mock_response("bad1"),
            _make_mock_response("bad2"),
            _make_mock_response("bad3"),
        ]
        mock_anthropic.Anthropic.return_value = mock_client

        result = _live_analyze(SAMPLE_CLAUSE)
        assert result.review_required is True
        assert result.confidence == 0.0
        assert result.error is not None
        assert result.raw_clause == SAMPLE_CLAUSE
        assert mock_client.messages.create.call_count == MAX_RETRIES

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("app.advisory.client.anthropic")
    def test_api_exception_retries(self, mock_anthropic):
        valid_response = json.dumps({
            "summary": "OK.",
            "risk_level": "Low",
            "categories": ["Other"],
            "confidence": 0.80,
        })
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            Exception("API timeout"),
            _make_mock_response(valid_response),
        ]
        mock_anthropic.Anthropic.return_value = mock_client

        result = _live_analyze(SAMPLE_CLAUSE)
        assert result.risk_level == RiskLevel.LOW
        assert mock_client.messages.create.call_count == 2

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key_raises(self):
        # Remove ANTHROPIC_API_KEY
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            _live_analyze(SAMPLE_CLAUSE)


# ---------------------------------------------------------------------------
# analyze_clause routing (mock vs live)
# ---------------------------------------------------------------------------


class TestAnalyzeClauseRouting:
    @patch.dict("os.environ", {"ADVISORY_MODE": "mock"})
    def test_mock_mode(self):
        result = analyze_clause(SAMPLE_CLAUSE)
        assert result.model_used == "mock"

    @patch.dict("os.environ", {"ADVISORY_MODE": "live", "ANTHROPIC_API_KEY": "test-key"})
    @patch("app.advisory.client.anthropic")
    def test_live_mode(self, mock_anthropic):
        valid_response = json.dumps({
            "summary": "OK.",
            "risk_level": "Low",
            "categories": ["Other"],
            "confidence": 0.80,
        })
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(valid_response)
        mock_anthropic.Anthropic.return_value = mock_client

        result = analyze_clause(SAMPLE_CLAUSE)
        assert result.model_used != "mock"

    def test_default_mode_is_mock(self):
        # Default when ADVISORY_MODE not set
        result = analyze_clause(SAMPLE_CLAUSE)
        assert result.model_used == "mock"
