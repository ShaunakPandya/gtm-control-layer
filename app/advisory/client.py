from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic
from pydantic import ValidationError

from app.advisory.models import ClauseAdvisory, ClauseCategory, RiskLevel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a contract clause analyst for enterprise B2B SaaS deals.
Analyze the provided clause and return a JSON object with exactly these fields:

{
  "summary": "<1-2 sentence plain-English summary of what the clause requires>",
  "risk_level": "<Low | Medium | High>",
  "categories": ["<one or more of: Audit, Data Residency, IP, Other>"],
  "confidence": <float 0.0 to 1.0 indicating your confidence in the analysis>
}

Rules:
- categories MUST be a list with at least one value
- risk_level MUST be exactly one of: Low, Medium, High
- confidence MUST be a number between 0.0 and 1.0
- Return ONLY valid JSON, no markdown fences, no extra text
"""

MAX_RETRIES = 3  # 1 initial + 2 retries
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def _get_model() -> str:
    return os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL)


def _get_mode() -> str:
    return os.environ.get("ADVISORY_MODE", "mock")


# ---------------------------------------------------------------------------
# Mock implementation
# ---------------------------------------------------------------------------

MOCK_RESPONSE: dict[str, Any] = {
    "summary": "This clause requires annual third-party security audits and data residency within the EU.",
    "risk_level": "Medium",
    "categories": ["Audit", "Data Residency"],
    "confidence": 0.87,
}


def _mock_analyze(clause_text: str) -> ClauseAdvisory:
    """Return a deterministic mock advisory for testing."""
    return ClauseAdvisory(
        summary=MOCK_RESPONSE["summary"],
        risk_level=RiskLevel(MOCK_RESPONSE["risk_level"]),
        categories=[ClauseCategory(c) for c in MOCK_RESPONSE["categories"]],
        confidence=MOCK_RESPONSE["confidence"],
        review_required=MOCK_RESPONSE["confidence"] < 0.75,
        raw_clause=clause_text,
        model_used="mock",
    )


# ---------------------------------------------------------------------------
# Live implementation
# ---------------------------------------------------------------------------


def _parse_advisory(raw: str, clause_text: str, model: str) -> ClauseAdvisory:
    """Parse raw LLM text into a validated ClauseAdvisory."""
    data = json.loads(raw)
    confidence = float(data["confidence"])
    return ClauseAdvisory(
        summary=data["summary"],
        risk_level=RiskLevel(data["risk_level"]),
        categories=[ClauseCategory(c) for c in data["categories"]],
        confidence=confidence,
        review_required=confidence < 0.75,
        raw_clause=clause_text,
        model_used=model,
    )


def _live_analyze(clause_text: str) -> ClauseAdvisory:
    """Call Claude API with retries and strict JSON enforcement."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is required for live mode")

    client = anthropic.Anthropic(api_key=api_key)
    model = _get_model()
    last_error: str = ""

    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=512,
                temperature=0.0,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": f"Analyze this contract clause:\n\n{clause_text}"}
                ],
            )
            raw_text = response.content[0].text
            return _parse_advisory(raw_text, clause_text, model)

        except (json.JSONDecodeError, KeyError, ValidationError, ValueError) as exc:
            last_error = f"Attempt {attempt + 1}/{MAX_RETRIES}: {type(exc).__name__}: {exc}"
            logger.warning("Advisory parse failed: %s", last_error)
            continue

        except Exception as exc:
            last_error = f"Attempt {attempt + 1}/{MAX_RETRIES}: {type(exc).__name__}: {exc}"
            logger.error("Advisory API call failed: %s", last_error)
            continue

    # All retries exhausted — flag for manual review
    logger.error("Advisory retries exhausted for clause: %.100s...", clause_text)
    return ClauseAdvisory(
        summary="Unable to analyze clause — flagged for manual review.",
        risk_level=RiskLevel.MEDIUM,
        categories=[ClauseCategory.OTHER],
        confidence=0.0,
        review_required=True,
        raw_clause=clause_text,
        model_used=model,
        error=last_error,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_clause(clause_text: str) -> ClauseAdvisory:
    """Analyze a contract clause. Routes to mock or live based on ADVISORY_MODE env var."""
    mode = _get_mode()
    if mode == "live":
        return _live_analyze(clause_text)
    return _mock_analyze(clause_text)
