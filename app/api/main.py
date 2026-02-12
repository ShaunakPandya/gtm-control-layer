from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.errors import validation_exception_handler
from app.api.routes_intake import router as intake_router
from app.api.routes_advisory import router as advisory_router
from app.api.routes_metrics import router as metrics_router
from app.api.routes_override import router as override_router
from app.api.routes_pipeline import router as pipeline_router
from app.api.routes_routing import router as routing_router
from app.api.routes_rules import router as rules_router
from app.api.routes_seed import router as seed_router
from app.api.routes_simulation import router as simulation_router

app = FastAPI(
    title="GTM Control Layer",
    version="0.1.0",
    description="Programmable GTM Control Layer – deterministic deal policy engine",
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.include_router(intake_router)
app.include_router(rules_router)
app.include_router(routing_router)
app.include_router(advisory_router)
app.include_router(pipeline_router)
app.include_router(metrics_router)
app.include_router(override_router)
app.include_router(simulation_router)
app.include_router(seed_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
