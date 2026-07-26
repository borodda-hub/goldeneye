"""Phase A3 — the validation ledger endpoint for the "How We Validate" page.

Read-only, anonymous. Serves the structured provenance ledger
(`services/validation_ledger.py`, drift-locked to `docs/MODEL_DILIGENCE.md`
in CI) plus the two vintage-archive day counts (real-source only) so the
page's "what we can't test yet" section shows live accumulation.

Not model output — no SafetyEnvelope; the standard disclaimer renders in
the app shell. Every row carries its `provenance` field (the
MODEL_DILIGENCE non-negotiable applies to the payload shape itself).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import curve_vintages as cv_repo
from apps.api.repos import weather_vintages as wv_repo
from apps.api.services.validation_ledger import ledger_rows

router = APIRouter(prefix="/v1/validation", tags=["validation"])


class LedgerRowOut(BaseModel):
    key: str
    claim: str
    verdict: str
    provenance: str
    summary: str
    evidence: str
    rerun: str | None
    gate_ref: str
    updated: str


class ArchivesOut(BaseModel):
    weather_vintage_days: int
    curve_vintage_days: int


class ValidationOut(BaseModel):
    rows: list[LedgerRowOut]
    archives: ArchivesOut
    generated_at: datetime


@router.get("", response_model=ValidationOut)
async def get_validation(session: AsyncSession = Depends(get_db)) -> ValidationOut:
    weather_days = await wv_repo.count_vintage_days(session, source="nws")
    curve_days = await cv_repo.count_vintage_days(session, source="yahoo_delayed")
    return ValidationOut(
        rows=[LedgerRowOut(**r) for r in ledger_rows()],
        archives=ArchivesOut(
            weather_vintage_days=weather_days, curve_vintage_days=curve_days
        ),
        generated_at=datetime.now(UTC),
    )
