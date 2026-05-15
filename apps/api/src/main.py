from __future__ import annotations

# Project-root bootstrap: ensure `apps.api.*` resolves regardless of how
# uvicorn was launched (with --directory apps/api, from the repo root, or
# directly via `python -m`). Without this, `uvicorn src.main:app` started
# inside apps/api/ would crash with ModuleNotFoundError: No module named
# 'apps' because the cwd entry on sys.path points at apps/api/, not the
# project root.
import sys as _sys
from pathlib import Path as _Path

_PROJECT_ROOT = _Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from contextlib import asynccontextmanager  # noqa: E402
from typing import AsyncGenerator  # noqa: E402

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from apps.api.routers import (  # noqa: E402
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
    instruments,
    ticker,
    indicators,
)
from apps.api.realtime.ticker import start_ticker  # noqa: E402
from apps.api.services.safety import SafetyViolation  # noqa: E402


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
app.include_router(instruments.router)
app.include_router(ticker.router)
app.include_router(indicators.router)


@app.get("/v1/health")
async def health() -> dict[str, bool]:
    return {"ok": True}
