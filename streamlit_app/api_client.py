"""Thin HTTP client for the FastAPI backend."""

from __future__ import annotations

import os
from typing import Any

import httpx

BASE_URL = os.environ.get("GTM_API_URL", "http://localhost:8000")


def _url(path: str) -> str:
    return f"{BASE_URL}{path}"


def _headers() -> dict[str, str]:
    key = os.environ.get("GTM_API_KEY")
    if key:
        return {"X-API-Key": key}
    return {}


def submit_deal(payload: dict[str, Any]) -> dict[str, Any]:
    resp = httpx.post(_url("/deals"), json=payload, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_metrics() -> dict[str, Any]:
    resp = httpx.get(_url("/metrics"), headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def list_deals() -> dict[str, Any]:
    resp = httpx.get(_url("/deals/list"), headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def seed_deals(count: int = 50, auto_process: bool = True) -> dict[str, Any]:
    resp = httpx.post(
        _url("/seed"),
        json={"count": count, "auto_process": auto_process},
        headers=_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def reset_and_seed(count: int = 50) -> dict[str, Any]:
    resp = httpx.post(
        _url("/seed/reset"),
        json={"count": count},
        headers=_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def override_deal(
    deal_id: str, reason: str, notes: str | None = None, overridden_by: str = "approver"
) -> dict[str, Any]:
    resp = httpx.post(
        _url(f"/deals/{deal_id}/override"),
        json={
            "override_reason": reason,
            "override_notes": notes,
            "overridden_by": overridden_by,
        },
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def run_simulation(payload: dict[str, Any]) -> dict[str, Any]:
    resp = httpx.post(
        _url("/simulate"), json=payload, headers=_headers(), timeout=30
    )
    resp.raise_for_status()
    return resp.json()


def analyze_clause(clause_text: str) -> dict[str, Any]:
    resp = httpx.post(
        _url("/deals/analyze-clause"),
        json={"clause_text": clause_text},
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
