from __future__ import annotations

from fastapi import APIRouter

from app.db.database import init_db
from app.metrics.compute import MetricsSummary, compute_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=MetricsSummary, status_code=200)
async def get_metrics() -> MetricsSummary:
    """Compute and return current operational metrics."""
    init_db()
    return compute_metrics()
