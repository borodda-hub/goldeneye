"""Phase D1b — the implied-vs-forecast vol comparison endpoint.

Serves `services/vol_premium.analyze_pair` — the SAME function the D1
probe validates — for the Signal Lab VolPremium card. The pre-registered
SHIP GATE is computed live on every response: a pair whose forecast is
WORSE than the market's own (paired MAE delta ≥ +1 SE) reports
`ship_gate: false` and the card renders its honest note instead of the
comparison. Unsupported symbols (no free implied-vol index — e.g. NG)
return the honest-degradation shape, never a fabricated number.

Model-derived readout → safety-wrapped (caveats + disclaimer), per the
non-negotiable LLM/model-output rule.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Query

from apps.api.services.safety import wrap_with_uncertainty
from apps.api.services.vol_premium import PAIR_FOR_SYMBOL, analyze_symbol

router = APIRouter(prefix="/v1/vol-premium", tags=["vol-premium"])

_CAVEATS = [
    "The comparison is a measured juxtaposition of two volatility numbers, "
    "not a prediction; premium-timing is tested but not validated (see the "
    "validation ledger).",
    "Implied-vol indices reference ETF options (USO/GLD/SPY) — the same "
    "underlying as the forecast leg; 30-day tenor matched.",
]


@router.get("")
async def get_vol_premium(symbol: str = Query(default="NG")) -> dict:
    up = symbol.upper()
    if up not in PAIR_FOR_SYMBOL:
        return {
            "symbol": up,
            "supported": False,
            "reason": "No free implied-volatility index exists for this "
            "instrument; the comparison is only shown where both sides are "
            "real published numbers.",
        }
    result = await analyze_symbol(up)
    if result is None:
        return {
            "symbol": up,
            "supported": False,
            "reason": "Insufficient history from the implied-vol source.",
        }
    terciles = {
        name: (
            {"mean": t.mean, "se": t.se, "n": t.n} if t is not None else None
        )
        for name, t in result["terciles"].items()
    }
    safety = wrap_with_uncertainty(
        {},
        confidence="low",
        caveats=_CAVEATS,
        as_of=datetime.now(UTC),
    )
    return {
        "symbol": up,
        "supported": True,
        "pair": result["pair"],
        "current": result["current"],
        "ship_gate": result["ship_gate"],
        "g1": {
            "mae_forecast": result["mae_f"],
            "mae_iv": result["mae_iv"],
            "delta": result["g1_delta"],
            "se": result["g1_se"],
            "passes": result["g1_passes"],
        },
        "terciles": terciles,
        "timing_tested": result["timing_tested"],
        "sample": {
            "n": result["n"],
            "n_eff": result["n_eff"],
            "span": list(result["span"]),
            "mean_premium": result["g0_mean_prem"],
        },
        "safety": safety.model_dump(mode="json"),
    }
