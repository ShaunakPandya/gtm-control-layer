from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details response."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None
    errors: list[dict] | None = None


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    detail_parts = []
    error_list = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err["loc"] if l != "body")
        msg = err["msg"]
        detail_parts.append(f"{loc}: {msg}")
        error_list.append({"field": loc, "message": msg, "type": err["type"]})

    problem = ProblemDetail(
        type="urn:gtm:error:validation",
        title="Validation Error",
        status=422,
        detail="; ".join(detail_parts),
        instance=str(request.url),
        errors=error_list,
    )
    return JSONResponse(status_code=422, content=problem.model_dump(exclude_none=True))
