from __future__ import annotations

import math
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import contracts as contract_repo
from apps.api.repos import instruments as instr_repo
from apps.api.repos import news as news_repo
from apps.api.repos import eia as eia_repo
from apps.api.adapters.registry import get_market

router = APIRouter(prefix="/v1/chart", tags=["chart"])


def _sma(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = []
    for i in range(len(values)):
        if i < period - 1:
            result.append(None)
        else:
            result.append(sum(values[i - period + 1 : i + 1]) / period)
    return result


def _ema(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = []
    k = 2.0 / (period + 1)
    ema = None
    for v in values:
        if ema is None:
            ema = v
        else:
            ema = v * k + ema * (1 - k)
        result.append(ema)
    return result


@router.get("/bars")
async def get_bars(
    contract_code: str = Query(...),
    resolution: str = Query(default="1d"),
    from_: date = Query(default=date(2025, 5, 10), alias="from"),
    to: date = Query(default_factory=date.today),
    session: AsyncSession = Depends(get_db),
) -> dict:
    contract = await contract_repo.get_by_code(session, contract_code)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Contract {contract_code!r} not found")

    market = get_market()
    from_dt = datetime(from_.year, from_.month, from_.day)
    to_dt = datetime(to.year, to.month, to.day, 23, 59, 59)

    bars = await market.get_bars(contract_code, resolution, from_dt=from_dt, to_dt=to_dt)

    closes = [b["close"] for b in bars]
    tss = [b["ts"] for b in bars]

    sma_20 = _sma(closes, 20)
    ema_50 = _ema(closes, 50)

    # EIA event markers
    eia_reports = await eia_repo.get_recent(session, limit=500)
    eia_markers = []
    from_d = from_
    to_d = to
    for rep in eia_reports:
        if rep.report_date and from_d <= rep.report_date <= to_d:
            vs = rep.consensus_estimate
            actual = rep.net_change_bcf
            surprise = rep.surprise_bcf or 0
            label = f"EIA: {actual:+.0f} Bcf (est {vs:+.0f}, Δ{surprise:+.0f})" if vs else f"EIA: {actual:+.0f} Bcf"
            eia_markers.append({
                "ts": datetime(rep.report_date.year, rep.report_date.month, rep.report_date.day, 14, 30).isoformat(),
                "kind": "eia_storage",
                "label": label,
                "delta": round(float(surprise), 1),
            })

    bar_list = [
        {
            "ts": b["ts"].isoformat() if isinstance(b["ts"], datetime) else b["ts"],
            "o": b["open"],
            "h": b["high"],
            "l": b["low"],
            "c": b["close"],
            "v": b["volume"],
        }
        for b in bars
    ]

    overlays: dict = {
        "sma_20": [
            {"ts": tss[i].isoformat() if isinstance(tss[i], datetime) else tss[i], "v": v}
            for i, v in enumerate(sma_20)
            if v is not None
        ],
        "ema_50": [
            {"ts": tss[i].isoformat() if isinstance(tss[i], datetime) else tss[i], "v": v}
            for i, v in enumerate(ema_50)
            if v is not None
        ],
    }

    return {
        "contract": {
            "code": contract_code,
            "expiry": contract.expiry_date.isoformat() if contract.expiry_date else None,
        },
        "resolution": resolution,
        "bars": bar_list,
        "overlays": overlays,
        "event_markers": eia_markers,
    }


@router.get("/curve")
async def get_curve(
    symbol: str = Query(default="NG"),
    as_of: date = Query(default_factory=date.today),
) -> dict:
    market = get_market()
    as_of_dt = datetime(as_of.year, as_of.month, as_of.day, 16, 0)
    curve = await market.get_curve_snapshot(symbol, as_of_dt)
    return {
        "symbol": symbol,
        "as_of": as_of.isoformat(),
        "curve": curve,
    }
