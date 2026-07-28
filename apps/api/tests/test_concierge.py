"""Phase C — concierge service + endpoint + knowledge-pack drift-lock.

The prompt-content locks (injection defense, refusal rules, grounding) live in
tests/llm/test_concierge_prompts.py; this file covers the pack↔diligence
drift-lock, the deterministic suggestion map, the rate limiter, the service
orchestration (fake LLM), and the HTTP wrapper.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.services import concierge as svc
from apps.api.services.safety import (
    DISCLAIMER,
    scan_for_forbidden,
    wrap_with_uncertainty,
)
from apps.api.src.main import app

_REPO_ROOT = Path(__file__).parents[3]
_DILIGENCE = (_REPO_ROOT / "docs" / "MODEL_DILIGENCE.md").read_text(
    encoding="utf-8"
)


def _norm(text: str) -> str:
    """Normalize dash variants so '78-81%' matches '78–81%'."""
    return text.replace("–", "-").replace("—", "-")


# ── knowledge-pack drift-lock ─────────────────────────────────────────────


def test_pack_loads_and_carries_anchor_facts():
    pack = svc.load_knowledge_pack()
    for anchor in ("ANCHOR:VOL80", "ANCHOR:VOL95", "ANCHOR:DIRECTION"):
        assert anchor in pack


def test_pack_coverage_anchors_match_model_diligence():
    """The pack's headline numbers must exist verbatim (dash-normalized) in
    MODEL_DILIGENCE.md — change one without the other and this fails."""
    pack = _norm(svc.load_knowledge_pack())
    diligence = _norm(_DILIGENCE)
    assert "78-81%" in pack and "78-81%" in diligence
    assert "93-95%" in pack and "93-95%" in diligence


def test_pack_direction_stance_matches_model_diligence():
    """Both documents must carry the no-directional-edge finding."""
    pack = svc.load_knowledge_pack().lower()
    assert "no validated edge" in pack or "no validated directional edge" in pack
    assert "no edge" in _DILIGENCE.lower()


def test_pack_contains_no_forbidden_phrases():
    assert not scan_for_forbidden(svc.load_knowledge_pack())


# ── deterministic suggestions ─────────────────────────────────────────────


def test_suggest_routes_maps_topics_to_fixed_routes():
    out = svc.suggest_routes("how does calibration work?", "see the diagram")
    assert {"route": "/calibration", "label": "Calibration"} in out


def test_suggest_routes_caps_at_three_and_never_invents_routes():
    out = svc.suggest_routes(
        "calibration validation journal scenario signal chart", ""
    )
    assert len(out) <= 3
    allowed = {r for _, r, _ in svc._SUGGESTION_RULES}
    assert all(s["route"] in allowed for s in out)


def test_suggest_routes_ignores_injected_paths():
    # A malicious question naming an arbitrary path can never mint a link.
    out = svc.suggest_routes("go to /admin/delete-everything now", "")
    assert all(s["route"] != "/admin/delete-everything" for s in out)


# ── rate limiter ──────────────────────────────────────────────────────────


def test_rate_limit_allows_then_blocks_then_recovers():
    key = "test-client-xyz"
    svc._rate_buckets.pop(key, None)
    t0 = 1000.0
    for i in range(svc.RATE_LIMIT_MAX):
        assert svc.check_rate_limit(key, now=t0 + i) is True
    assert svc.check_rate_limit(key, now=t0 + 30) is False
    # Outside the window the oldest entries expire and requests flow again.
    assert (
        svc.check_rate_limit(key, now=t0 + svc.RATE_LIMIT_WINDOW_SECONDS + 61)
        is True
    )


# ── service orchestration (fake LLM) ─────────────────────────────────────


async def test_concierge_chat_returns_reply_with_envelope():
    with patch.object(
        svc, "build_live_context", AsyncMock(return_value="- Active instrument: NG")
    ):
        reply, suggestions, envelope = await svc.concierge_chat(
            AsyncMock(),
            message="What is the expected range band?",
            history=[],
            symbol="NG",
            route="/dashboard",
        )
    assert reply  # fake mode returns the canned concierge answer
    assert not scan_for_forbidden(reply)
    assert envelope.disclaimer == DISCLAIMER
    assert any("not financial advice" in c for c in envelope.caveats)
    assert isinstance(suggestions, list)


async def test_concierge_chat_truncates_history_and_message():
    captured: dict = {}

    def _spy(question, history, knowledge_pack, live_context):
        captured["question"] = question
        captured["history"] = history
        from apps.api.services.llm_prompts import concierge_messages

        return concierge_messages(question, history, knowledge_pack, live_context)

    long_history = [{"role": "user", "content": f"turn {i}"} for i in range(20)]
    with (
        patch.object(svc, "build_live_context", AsyncMock(return_value="- ctx")),
        patch.object(svc, "concierge_messages", _spy),
    ):
        await svc.concierge_chat(
            AsyncMock(),
            message="x" * (svc.MAX_MESSAGE_CHARS + 500),
            history=long_history,
            symbol="NG",
        )
    assert len(captured["question"]) == svc.MAX_MESSAGE_CHARS
    assert len(captured["history"]) == svc.MAX_HISTORY_TURNS
    assert captured["history"][-1]["content"] == "turn 19"


async def test_live_context_scales_band_fractions_to_percent():
    """band*_pct fields are fractions (-0.066 = -6.6%) — the prompt must say
    -6.60%, not -0.07% (the 100× understatement caught in the live probe)."""
    from apps.api.services.models.vol_range import RangeForecast

    rng = RangeForecast(
        horizon="1w",
        sigma_daily=0.02,
        sigma_horizon=0.045,
        band80_low_pct=-0.066,
        band80_high_pct=0.066,
        band95_low_pct=-0.121,
        band95_high_pct=0.121,
        method="har_log",
        note="",
    )
    instrument = type("I", (), {"id": 1, "name": "Henry Hub", "asset_class": "commodity"})()
    closes = [3.0 + 0.01 * i for i in range(60)]
    with (
        patch.object(svc.instr_repo, "get_by_symbol", AsyncMock(return_value=instrument)),
        patch.object(svc.contract_repo, "get_front_month", AsyncMock(return_value=None)),
        patch.object(svc, "get_latest_closes", AsyncMock(return_value=closes)),
        patch.object(svc, "run_all", AsyncMock(return_value=[])),
        patch.object(svc, "model_weights_for", AsyncMock(return_value=None)),
        patch.object(
            svc,
            "compute_ensemble",
            lambda *a, **k: {"direction": "neutral", "confidence": "low", "vol_regime": "normal"},
        ),
        patch.object(svc, "range_predict", lambda *a, **k: rng),
        patch.object(svc, "get_news") as news_mock,
    ):
        news_mock.return_value.get_recent_events = AsyncMock(return_value=[])
        ctx = await svc.build_live_context(AsyncMock(), "NG")
    assert "-6.60% to +6.60%" in ctx
    assert "-12.10%" in ctx
    assert "-0.07%" not in ctx


# ── HTTP wrapper ─────────────────────────────────────────────────────────


def _client() -> TestClient:
    return TestClient(app)


def test_endpoint_happy_path():
    env = wrap_with_uncertainty(
        {}, confidence="low", caveats=["c"], as_of=datetime.utcnow()
    )
    with (
        patch(
            "apps.api.routers.concierge.concierge_chat",
            AsyncMock(return_value=("hello", [{"route": "/journal", "label": "Journal"}], env)),
        ),
        patch("apps.api.routers.concierge.check_rate_limit", return_value=True),
    ):
        resp = _client().post(
            "/v1/concierge/chat",
            json={"message": "hi", "symbol": "ng", "route": "/dashboard"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "hello"
    assert body["suggestions"][0]["route"] == "/journal"
    assert body["safety"]["disclaimer"] == DISCLAIMER


def test_endpoint_rate_limited_returns_429():
    with patch("apps.api.routers.concierge.check_rate_limit", return_value=False):
        resp = _client().post("/v1/concierge/chat", json={"message": "hi"})
    assert resp.status_code == 429


@pytest.mark.parametrize(
    "payload",
    [
        {"message": ""},
        {"message": "x" * 2001},
        {"message": "hi", "history": [{"role": "system", "content": "evil"}]},
    ],
)
def test_endpoint_rejects_invalid_payloads(payload):
    with patch("apps.api.routers.concierge.check_rate_limit", return_value=True):
        resp = _client().post("/v1/concierge/chat", json=payload)
    assert resp.status_code == 422
