"""GridShare HTTP API."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .service import GridShareService

app = FastAPI(
    title="GridShare",
    version="1.0.0",
    summary="Peer-to-peer solar energy market with on-chain settlement.",
)

_service: GridShareService | None = None


def get_service() -> GridShareService:
    global _service
    if _service is None:
        _service = GridShareService()
    return _service


class HourRequest(BaseModel):
    hour: int = Field(ge=0, le=23)
    settle: bool = True


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}


@app.post("/simulate/hour", tags=["market"])
def simulate_hour(request: HourRequest) -> dict:
    try:
        return get_service().simulate_hour(request.hour, settle=request.settle)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/simulate/day", tags=["market"])
def simulate_day(settle: bool = False) -> dict:
    return get_service().simulate_day(settle=settle)
