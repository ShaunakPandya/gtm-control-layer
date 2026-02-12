from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter

from app.db.database import get_all_deals, init_db
from app.metrics.seed import reset_and_seed, seed_deals

router = APIRouter(tags=["seed"])


class SeedRequest(BaseModel):
    count: int = Field(default=50, ge=1, le=500)
    auto_process: bool = True


class SeedResponse(BaseModel):
    generated: int
    deal_ids: list[str]


@router.post("/seed", response_model=SeedResponse, status_code=201)
async def seed_data(request: SeedRequest) -> SeedResponse:
    """Generate random deals for demo purposes."""
    init_db()
    ids = seed_deals(count=request.count, auto_process=request.auto_process)
    return SeedResponse(generated=len(ids), deal_ids=ids)


@router.post("/seed/reset", response_model=SeedResponse, status_code=201)
async def reset_and_seed_data(request: SeedRequest) -> SeedResponse:
    """Reset database and seed with fresh random deals."""
    ids = reset_and_seed(count=request.count)
    return SeedResponse(generated=len(ids), deal_ids=ids)


class DealsListResponse(BaseModel):
    total: int
    deals: list[dict]


@router.get("/deals/list", response_model=DealsListResponse, status_code=200)
async def list_deals() -> DealsListResponse:
    """List all stored deals."""
    init_db()
    deals = get_all_deals()
    return DealsListResponse(total=len(deals), deals=deals)
