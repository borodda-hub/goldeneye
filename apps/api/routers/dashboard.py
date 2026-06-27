from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from functools import lru_cache

from apps.api.adapters.news.rss import RssNewsAdapter
from apps.api.db.session import get_db
from apps.api.repos import instruments as instr_repo
from apps.api.repos import contracts as contract_repo
from apps.api.repos import price_bars as price_repo
from apps.api.services.price_lookup import get_latest_closes
from apps.api.adapters.registry import get_market
from apps.api.services.model_registry import ForecastContext, run_all
from apps.api.services.ensemble import compute_ensemble, derive_envelope_confidence
from apps.api.services.model_calibration import model_weights_for
from apps.api.services.llm_explainer import generate_thesis, summarize_market


@lru_cache(maxsize=None)
def _live_news(symbol: str) -> RssNewsAdapter:
    """Per-symbol RSS news adapter with its own 10-min response cache.
    Module-level cache so we don't recreate the HTTP client per request."""
    return RssNewsAdapter(symbol)

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

    # Recent news — per-symbol live RSS (Yahoo Finance per-instrument headline
    # feed). Each headline carries its source URL so the UI can link out.
    try:
        events = await _live_news(symbol).get_recent_events(limit=5)
    except Exception:  # noqa: BLE001 — never let the news feed take down the dashboard
        events = []
    recent_events = [
        {
            "id": e.get("url") or f"{e.get('source','')}-{e.get('headline','')[:32]}",
            "published_at": e.get("published_at"),
            "headline": e.get("headline"),
            "category": e.get("category", "other"),
            "impact_score": e.get("impact_score"),
            "url": e.get("url"),
            "source": e.get("source"),
            # 1-paragraph summary from the feed's <description> / Atom summary.
            "body": e.get("body") or "",
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
    ctx = ForecastContext(
        symbol=symbol,
        closes=closes,
        asset_class=getattr(instrument, "asset_class", "commodity"),
    )
    results = await run_all(ctx)
    weights = await model_weights_for(session, instrument.id, "1d")
    ensemble = compute_ensemble(results, model_weights=weights)

    # Derived LLM-envelope confidence (Phase A2): ensemble agreement + band width.
    _erange = ensemble.get("range") or {}
    _band_width = (
        _erange["high_pct"] - _erange["low_pct"]
        if _erange.get("high_pct") is not None and _erange.get("low_pct") is not None
        else None
    )
    env_conf = derive_envelope_confidence(
        ensemble_confidence=ensemble["confidence"],
        band_width=_band_width,
        band_cfg=ctx.cfg.ensemble_band,
    )

    # AI summary
    market_ctx = {
        "symbol": symbol,
        "last_price": last_price,
        "vol_regime": ensemble.get("vol_regime"),
        "direction": ensemble.get("direction"),
    }
    ai_text, safety_env = await summarize_market(market_ctx, envelope_confidence=env_conf)

    # AI thesis — richer per-instrument synthesis: news + factors + curve shape.
    # Curve shape from front-3 mids: monotonically rising = contango, falling =
    # backwardation, else flat/mixed.
    curve_shape = "unknown"
    if curve_snap and len(curve_snap) >= 3:
        mids = [c["mid_price"] for c in curve_snap[:3]]
        if mids[2] > mids[1] > mids[0]:
            curve_shape = "contango"
        elif mids[2] < mids[1] < mids[0]:
            curve_shape = "backwardation"
        else:
            curve_shape = "mixed"

    supporting_factors: list[str] = []
    contradicting_factors: list[str] = []
    for m in (ensemble.get("models") or [])[:4]:
        for f in (m.get("supporting") or [])[:2]:
            factor = str(f.get("factor", "")).strip()
            if factor and factor not in supporting_factors:
                supporting_factors.append(factor)
        for f in (m.get("contradicting") or [])[:2]:
            factor = str(f.get("factor", "")).strip()
            if factor and factor not in contradicting_factors:
                contradicting_factors.append(factor)

    thesis_ctx = {
        "symbol": symbol,
        "name": instrument.name,
        "last_price": last_price,
        "change_pct": change_pct,
        "vol_regime": ensemble.get("vol_regime"),
        "direction": ensemble.get("direction"),
        "confidence": ensemble.get("confidence"),
        "curve_shape": curve_shape,
        "recent_events": [e.get("headline", "") for e in events[:5]],
        "supporting_factors": supporting_factors[:5],
        "contradicting_factors": contradicting_factors[:5],
    }
    thesis_data, thesis_safety = await generate_thesis(
        thesis_ctx, envelope_confidence=env_conf
    )

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
        "ai_thesis": {
            "thesis": thesis_data.get("thesis", ""),
            "drivers": thesis_data.get("drivers", []),
            "watch": thesis_data.get("watch", []),
            "curve_shape": curve_shape,
            "safety": thesis_safety.model_dump(mode="json"),
        },
        "safety": safety_env.model_dump(mode="json"),
    }
