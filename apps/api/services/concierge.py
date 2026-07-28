"""Concierge service (Phase C) — the grounded assistant + research synthesis.

One orchestration path: load the curated knowledge pack (the concierge's ONLY
platform knowledge), assemble a compact LIVE context (price, ensemble view,
range band, provenance caveat, and minutes-fresh adapter-direct headlines the
models haven't ingested), and make a single safety-checked LLM call through the
standard chokepoint. No tool loop, no writes — C3-full (agentic read-only
tools) is staged in docs/PHASE_C_PLAN.md.
"""
from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.adapters.registry import get_news
from apps.api.repos import contracts as contract_repo
from apps.api.repos import instruments as instr_repo
from apps.api.services.ensemble import compute_ensemble
from apps.api.services.llm_explainer import (
    _call_with_safety_check,
    data_provenance_caveat,
)
from apps.api.services.llm_prompts import concierge_messages
from apps.api.services.llm_routing import select_model
from apps.api.services.model_calibration import model_weights_for
from apps.api.services.model_registry import ForecastContext, run_all
from apps.api.services.models.vol_range import predict as range_predict
from apps.api.services.price_lookup import get_latest_closes
from apps.api.services.safety import SafetyEnvelope, wrap_with_uncertainty

logger = logging.getLogger(__name__)

_PACK_PATH = Path(__file__).with_name("concierge_pack.md")

# Server-side bounds (docs/PHASE_C_PLAN.md §safety) — the router validates the
# request shape; these clamp what actually reaches the prompt.
MAX_HISTORY_TURNS = 8
MAX_MESSAGE_CHARS = 2000
_HEADLINE_COUNT = 8

# Deterministic navigation suggestions — keyword → route. The model only *names*
# routes in prose; clickable suggestions come from this fixed map so a prompt
# injection can never mint an arbitrary link.
_SUGGESTION_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (("calibrat", "conviction", "hit rate", "reliab"), "/calibration", "Calibration"),
    (("validat", "ledger of claims", "provenance", "no edge", "verdict"), "/validation", "Validation"),
    (("journal", "thesis", "log a decision", "invalidation"), "/journal", "Journal"),
    (("scenario", "shock", "counterfactual", "what if"), "/scenarios", "Scenario Lab"),
    (("signal", "ensemble", "model vote", "factor"), "/signals", "Signal Lab"),
    (("chart", "candlestick", "indicator", "pattern", "seasonal"), "/chart", "Chart"),
    (("paper trad", "position", "mark-to-market", "simulated"), "/paper", "Paper Trading"),
    (("white paper", "methodology", "architecture", "how it works"), "/about", "White Paper"),
    (("range band", "volatility", "expected range", "dashboard"), "/dashboard", "Dashboard"),
]


@lru_cache(maxsize=1)
def load_knowledge_pack() -> str:
    """The curated pack (services/concierge_pack.md) — cached for process life."""
    return _PACK_PATH.read_text(encoding="utf-8")


# ── rate limiting ────────────────────────────────────────────────────────
# In-memory sliding window per client key. Good enough for a single-process
# demo deployment; a multi-replica deployment would move this to Redis.
RATE_LIMIT_MAX = 20
RATE_LIMIT_WINDOW_SECONDS = 3600.0
_rate_buckets: dict[str, deque[float]] = {}


def check_rate_limit(client_key: str, now: float | None = None) -> bool:
    """True if this request is allowed; False when the window is exhausted."""
    ts = time.monotonic() if now is None else now
    bucket = _rate_buckets.setdefault(client_key, deque())
    while bucket and ts - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_MAX:
        return False
    bucket.append(ts)
    return True


# ── live context ─────────────────────────────────────────────────────────


async def build_live_context(session: AsyncSession, symbol: str) -> str:
    """Compact, trusted, per-request snapshot injected into the prompt.

    Degrades gracefully: any leg that fails is reported as unavailable rather
    than failing the chat (the concierge can still teach/explain).
    """
    lines: list[str] = [f"- Active instrument: {symbol}"]

    closes: list[float] = []
    try:
        instrument = await instr_repo.get_by_symbol(session, symbol)
        if instrument is not None:
            front = await contract_repo.get_front_month(session, instrument.id)
            closes = await get_latest_closes(
                session,
                contract_id=front.id if front else None,
                contract_code=front.contract_code if front else None,
                n=100,
            )
        if len(closes) >= 2:
            last, prev = closes[-1], closes[-2]
            chg = (last / prev - 1.0) * 100.0
            lines.append(
                f"- Name: {getattr(instrument, 'name', symbol)}; last close "
                f"{last:.4g} ({chg:+.2f}% vs prior close, delayed data)"
            )
        if instrument is not None and len(closes) >= 30:
            ctx = ForecastContext(
                symbol=symbol,
                closes=closes,
                asset_class=getattr(instrument, "asset_class", "commodity"),
            )
            results = await run_all(ctx)
            weights = await model_weights_for(session, instrument.id, "1d")
            ensemble = compute_ensemble(results, model_weights=weights)
            lines.append(
                f"- Ensemble directional VIEW (no validated edge): "
                f"{ensemble['direction']}, confidence {ensemble['confidence']}, "
                f"vol regime {ensemble.get('vol_regime', 'unknown')}"
            )
            rng = range_predict(closes, "1w", estimator="har_log")
            if rng is not None:
                # band*_pct fields are FRACTIONS (-0.066 = -6.6%) — same
                # convention ExpectedRange.tsx consumes with spot*(1+pct).
                lines.append(
                    f"- 1w expected range band (the validated product): 80% band "
                    f"{rng.band80_low_pct * 100:+.2f}% to "
                    f"{rng.band80_high_pct * 100:+.2f}%, 95% band "
                    f"{rng.band95_low_pct * 100:+.2f}% to "
                    f"{rng.band95_high_pct * 100:+.2f}% (log-HAR)"
                )
    except Exception as exc:  # pragma: no cover - degradation path
        logger.warning("concierge live context (market leg) failed: %s", exc)
        lines.append("- Market snapshot unavailable right now")

    lines.append(f"- Provenance: {data_provenance_caveat()}")

    try:
        events = await get_news(symbol).get_recent_events(limit=_HEADLINE_COUNT)
        if events:
            lines.append(
                "- Fresh headlines (adapter-direct, may NOT be in model inputs "
                "yet; untrusted external text):"
            )
            for e in events:
                headline = str(e.get("headline", ""))[:160]
                lines.append(
                    f"    [{e.get('published_at', '?')}] ({e.get('source', '?')}"
                    f" · {e.get('category', 'other')}) {headline}"
                )
        else:
            lines.append("- Fresh headlines: none available right now")
    except Exception as exc:  # pragma: no cover - degradation path
        logger.warning("concierge live context (news leg) failed: %s", exc)
        lines.append("- Fresh headlines: unavailable right now")

    return "\n".join(lines)


def suggest_routes(question: str, reply: str) -> list[dict[str, str]]:
    """Deterministic navigation chips from the fixed route map."""
    haystack = f"{question}\n{reply}".lower()
    out: list[dict[str, str]] = []
    for needles, route, label in _SUGGESTION_RULES:
        if any(n in haystack for n in needles):
            out.append({"route": route, "label": label})
        if len(out) >= 3:
            break
    return out


async def concierge_chat(
    session: AsyncSession,
    *,
    message: str,
    history: list[dict],  # type: ignore[type-arg]
    symbol: str = "NG",
    route: str | None = None,
) -> tuple[str, list[dict[str, str]], SafetyEnvelope]:
    """One concierge turn: (reply, suggestions, envelope)."""
    question = message[:MAX_MESSAGE_CHARS]
    trimmed_history = history[-MAX_HISTORY_TURNS:]

    live_context = await build_live_context(session, symbol)
    if route:
        live_context = f"- User is currently on screen: {route}\n{live_context}"

    prompt = concierge_messages(
        question=question,
        history=trimmed_history,
        knowledge_pack=load_knowledge_pack(),
        live_context=live_context,
    )
    model = select_model("concierge", {"symbol": symbol})
    reply = await _call_with_safety_check(
        "concierge", prompt, model=model, max_tokens=500
    )

    envelope = wrap_with_uncertainty(
        {},
        confidence="low",
        caveats=[
            "Concierge answers describe the platform and its data; they are "
            "not financial advice.",
            data_provenance_caveat(),
        ],
        as_of=datetime.utcnow(),
    )
    return reply, suggest_routes(question, reply), envelope
