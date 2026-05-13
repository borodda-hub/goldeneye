from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.routers import (
    dashboard,
    chart,
    signals,
    scenarios,
    journal,
    paper,
    admin,
    explain,
    news,
    backtest,
    realtime,
    thesis,
    signal_quality,
    calibration,
)
from apps.api.realtime.ticker import start_ticker
from apps.api.services.safety import SafetyViolation


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await start_ticker()
    yield


app = FastAPI(title="Goldeneye API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Error handlers ────────────────────────────────────────────────────────────

@app.exception_handler(SafetyViolation)
async def safety_violation_handler(request: Request, exc: SafetyViolation) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "safety_violation",
                "message": str(exc),
                "details": {},
            }
        },
    )


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(dashboard.router)
app.include_router(chart.router)
app.include_router(signals.router)
app.include_router(scenarios.router)
app.include_router(journal.router)
app.include_router(paper.router)
app.include_router(admin.router)
app.include_router(explain.router)
app.include_router(news.router)
app.include_router(backtest.router)
app.include_router(realtime.router)
app.include_router(thesis.router)
app.include_router(signal_quality.router)
app.include_router(calibration.router)


@app.get("/v1/health")
async def health() -> dict[str, bool]:
    return {"ok": True}
