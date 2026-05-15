from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import instruments as instr_repo
from apps.api.repos import contracts as contract_repo
from apps.api.repos import price_bars as price_repo
from apps.api.services.price_lookup import get_latest_closes
from apps.api.repos import news as news_repo
from apps.api.adapters.registry import get_market
from apps.api.services.model_registry import ForecastContext, run_all
from apps.api.services.ensemble import compute_ensemble
from apps.api.services.llm_explainer import summarize_market

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_summary(
    symbol: str = Query(default="NG"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    instrument = await instr_repo.get_by_symbol(session, symbol)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol!r} not found")

    front = await contract_repo.get_front_month(session, instrument.id)
    market = get_market()

    # Latest price
    as_of = datetime.utcnow()
    last_price: float | None = None
    change_abs: float | None = None
    change_pct: float | None = None
    front_code = front.contract_code if front else f"{symbol}M26"

    latest = await market.get_latest_price(front_code)
    if latest:
        last_price = latest["close"]
        bars_2d = await market.get_bars(
            front_code, "1d",
            from_dt=datetime(2020, 1, 1),
            to_dt=datetime.utcnow(),
        )
        if len(bars_2d) >= 2:
            prev_close = bars_2d[-2]["close"]
            change_abs = round(last_price - prev_close, 4)
            change_pct = round((last_price / prev_close - 1), 6) if prev_close else None
        as_of = latest["ts"]

    # Futures curve
    curve_snap = await market.get_curve_snapshot(symbol, datetime.utcnow())

    # Recent news
    events = await news_repo.get_recent(session, limit=5)
    recent_events = [
        {
            "id": str(e.id),
            "published_at": e.published_at.isoformat() if e.published_at else None,
            "headline": e.headline,
            "category": e.category,
            "impact_score": float(e.impact_score) if e.impact_score is not None else None,
        }
        for e in events
    ]

    # Ensemble signal
    closes = await get_latest_closes(
        session,
        contract_id=front.id if front else None,
        contract_code=front.contract_code if front else None,
        n=100,
    )
    ctx = ForecastContext(symbol=symbol, closes=closes)
    results = await run_all(ctx)
    ensemble = compute_ensemble(results)

    # AI summary
    market_ctx = {
        "symbol": symbol,
        "last_price": last_price,
        "vol_regime": ensemble.get("vol_regime"),
        "direction": ensemble.get("direction"),
    }
    ai_text, safety_env = await summarize_market(market_ctx)

    return {
        "instrument": {
            "symbol": instrument.symbol,
            "name": instrument.name,
            "currency": instrument.currency,
            "unit": instrument.unit,
        },
        "front_month": {
            "contract_code": front_code,
            "last_price": last_price,
            "change_abs": change_abs,
            "change_pct": change_pct,
            "as_of": as_of.isoformat() if isinstance(as_of, datetime) else str(as_of),
        },
        "vol_regime": ensemble.get("vol_regime"),
        "directional_bias": {
            "direction": ensemble["direction"],
            "confidence": ensemble["confidence"],
        },
        "futures_curve": [
            {"contract_code": c["contract_code"], "expiry": c["expiry"], "mid": c["mid_price"]}
            for c in (curve_snap or [])
        ],
        "recent_events": recent_events,
        "ai_summary": ai_text,
        "safety": safety_env.model_dump(mode="json"),
    }
