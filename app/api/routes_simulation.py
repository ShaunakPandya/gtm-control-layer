from __future__ import annotations

from fastapi import APIRouter

from app.db.database import init_db
from app.metrics.simulation import SimulationInput, SimulationResult, run_simulation

router = APIRouter(tags=["simulation"])


@router.post("/simulate", response_model=SimulationResult, status_code=200)
async def simulate_thresholds(sim_input: SimulationInput) -> SimulationResult:
    """Run threshold simulation against stored deals. No data mutation."""
    init_db()
    return run_simulation(sim_input)
