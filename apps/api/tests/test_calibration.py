"""Phase 13 Step 3 — calibration service + endpoint tests.

Covers:
- Bucket edge construction + index lookup
- Legacy confidence_pct fallback when thesis snapshot is null
- Hit-rate guardrail (None when resolved_count < 3)
- Summary copy generation, including the no-gap case
- Endpoint validation (bad bucket_count, unknown symbol) + happy path
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.models.orm.journal import UserDecisionJournal
from apps.api.services import calibration as svc
from apps.api.src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _entry(
    *,
    conviction: int | None = None,
    thesis_snap: int | None = None,
    resolved: str | None = None,
) -> UserDecisionJournal:
    """Build a journal entry for use in calibration tests.

    `conviction` populates the legacy confidence_pct field. `thesis_snap`
    populates thesis_conviction_at_write. `resolved` sets resolved_direction.
    """
    return UserDecisionJournal(
        id=uuid.uuid4(),
        instrument_id=uuid.uuid4(),
        hypothesis="test",
        evidence=[],
        confidence_pct=conviction if conviction is not None else 50,
        resolved_direction=resolved,
        thesis_id_at_write=None,
        thesis_conviction_at_write=thesis_snap,
    )


# ── Bucket edges ──────────────────────────────────────────────────────────


def test_bucket_edges_default_5_buckets():
    assert svc._bucket_edges(5) == [
        (0, 20),
        (20, 40),
        (40, 60),
        (60, 80),
        (80, 100),
    ]


def test_bucket_edges_4_buckets():
    assert svc._bucket_edges(4) == [(0, 25), (25, 50), (50, 75), (75, 100)]


def test_bucket_edges_rejects_non_divisor():
    with pytest.raises(ValueError, match="evenly divide"):
        svc._bucket_edges(3)


def test_bucket_edges_rejects_zero():
    with pytest.raises(ValueError, match="must be > 0"):
        svc._bucket_edges(0)


# ── Bucket index lookup ──────────────────────────────────────────────────


def test_bucket_index_for_edges():
    edges = svc._bucket_edges(5)
    assert svc._bucket_index_for(0, edges) == 0
    assert svc._bucket_index_for(19, edges) == 0
    assert svc._bucket_index_for(20, edges) == 1
    assert svc._bucket_index_for(50, edges) == 2
    assert svc._bucket_index_for(80, edges) == 4
    assert svc._bucket_index_for(100, edges) == 4
    # Out-of-range clamps rather than crashes.
    assert svc._bucket_index_for(-5, edges) == 0
    assert svc._bucket_index_for(105, edges) == 4


# ── Conviction fallback ──────────────────────────────────────────────────


def test_conviction_for_prefers_thesis_snapshot():
    e = _entry(conviction=40, thesis_snap=70)
    assert svc._conviction_for(e) == 70


def test_conviction_for_falls_back_to_legacy_confidence_pct():
    e = _entry(conviction=40, thesis_snap=None)
    assert svc._conviction_for(e) == 40


# ── Hit-rate guardrail ───────────────────────────────────────────────────


def test_build_bucket_hit_rate_none_when_under_three_resolved():
    bucket = svc._build_bucket(
        (60, 80),
        is_last=False,
        entries=[
            _entry(thesis_snap=70, resolved="hit"),
            _entry(thesis_snap=72, resolved="miss"),
            # Only 2 resolved — under threshold.
        ],
    )
    assert bucket.resolved_count == 2
    assert bucket.hit_rate is None
    assert bucket.total_count == 2


def test_build_bucket_hit_rate_computed_at_threshold():
    bucket = svc._build_bucket(
        (60, 80),
        is_last=False,
        entries=[
            _entry(thesis_snap=70, resolved="hit"),
            _entry(thesis_snap=72, resolved="hit"),
            _entry(thesis_snap=68, resolved="miss"),
        ],
    )
    assert bucket.resolved_count == 3
    assert bucket.hit_count == 2
    assert bucket.hit_rate == pytest.approx(2 / 3)


def test_build_bucket_excludes_neutral_and_unresolved_from_rate():
    bucket = svc._build_bucket(
        (60, 80),
        is_last=False,
        entries=[
            _entry(thesis_snap=70, resolved="hit"),
            _entry(thesis_snap=70, resolved="hit"),
            _entry(thesis_snap=70, resolved="miss"),
            _entry(thesis_snap=70, resolved="neutral"),
            _entry(thesis_snap=70, resolved="unresolved"),
            _entry(thesis_snap=70, resolved=None),
        ],
    )
    assert bucket.total_count == 6
    assert bucket.resolved_count == 3
    assert bucket.hit_rate == pytest.approx(2 / 3)


def test_build_bucket_empty_returns_nones():
    bucket = svc._build_bucket((0, 20), is_last=False, entries=[])
    assert bucket.total_count == 0
    assert bucket.claimed_mean is None
    assert bucket.hit_rate is None


# ── Summary copy ─────────────────────────────────────────────────────────


def test_summary_picks_largest_gap_when_above_threshold():
    buckets = [
        svc.CalibrationBucket(
            label="60-80",
            lower_pct=60,
            upper_pct=80,
            claimed_mean=70.0,
            total_count=14,
            resolved_count=14,
            hit_count=9,
            hit_rate=9 / 14,  # ~0.643 → 64
        ),
        svc.CalibrationBucket(
            label="40-60",
            lower_pct=40,
            upper_pct=60,
            claimed_mean=50.0,
            total_count=8,
            resolved_count=6,
            hit_count=4,
            hit_rate=4 / 6,  # ~0.667 → 67, gap of 17 vs claimed 50
        ),
    ]
    summary = svc._summary_copy(buckets)
    assert summary is not None
    # Second bucket has the bigger gap (17 vs 6) and wins.
    assert summary.startswith("Your 50% theses resolved at 67%")
    assert "n=6" in summary


def test_summary_none_when_all_gaps_under_threshold():
    """When every bucket calibrates within 5 percentage points, no summary."""
    buckets = [
        svc.CalibrationBucket(
            label="60-80",
            lower_pct=60,
            upper_pct=80,
            claimed_mean=70.0,
            total_count=10,
            resolved_count=10,
            hit_count=7,
            hit_rate=0.7,  # gap = 0
        ),
        svc.CalibrationBucket(
            label="80-100",
            lower_pct=80,
            upper_pct=100,
            claimed_mean=85.0,
            total_count=6,
            resolved_count=6,
            hit_count=5,
            hit_rate=5 / 6,  # ~0.833 → 83, gap of 2
        ),
    ]
    assert svc._summary_copy(buckets) is None


def test_summary_skips_buckets_without_hit_rate():
    """A bucket with hit_rate=None (under-3-resolved) can't drive the copy."""
    buckets = [
        svc.CalibrationBucket(
            label="60-80",
            lower_pct=60,
            upper_pct=80,
            claimed_mean=70.0,
            total_count=2,
            resolved_count=2,
            hit_count=0,
            hit_rate=None,
        ),
    ]
    assert svc._summary_copy(buckets) is None


# ── compute_calibration end-to-end ────────────────────────────────────────


@pytest.mark.asyncio
async def test_compute_calibration_groups_entries_into_correct_buckets():
    entries = [
        _entry(thesis_snap=15, resolved="hit"),  # bucket 0 (0-20)
        _entry(thesis_snap=25, resolved="miss"),  # bucket 1 (20-40)
        _entry(thesis_snap=70, resolved="hit"),  # bucket 3 (60-80)
        _entry(thesis_snap=70, resolved="hit"),  # bucket 3
        _entry(thesis_snap=70, resolved="miss"),  # bucket 3
    ]
    with patch.object(
        svc.journal_repo,
        "list_with_resolutions",
        new=AsyncMock(return_value=entries),
    ):
        result = await svc.compute_calibration(
            session=None,  # type: ignore[arg-type]
            instrument_id=uuid.uuid4(),
            instrument_code="NG",
            bucket_count=5,
        )
    counts = [b.total_count for b in result.buckets]
    assert counts == [1, 1, 0, 3, 0]
    # Bucket 3 has 3 resolved entries → hit rate computable.
    assert result.buckets[3].hit_rate == pytest.approx(2 / 3)
    # Buckets 0 and 1 each have 1 resolved → under threshold.
    assert result.buckets[0].hit_rate is None
    assert result.total_entries == 5
    assert result.resolved_entries == 5


@pytest.mark.asyncio
async def test_compute_calibration_uses_legacy_confidence_pct_fallback():
    entries = [
        _entry(conviction=70, thesis_snap=None, resolved="hit"),
        _entry(conviction=70, thesis_snap=None, resolved="hit"),
        _entry(conviction=70, thesis_snap=None, resolved="miss"),
    ]
    with patch.object(
        svc.journal_repo,
        "list_with_resolutions",
        new=AsyncMock(return_value=entries),
    ):
        result = await svc.compute_calibration(
            session=None,  # type: ignore[arg-type]
            instrument_id=uuid.uuid4(),
            instrument_code="NG",
        )
    # Bucket 3 (60-80) should have all 3, despite thesis_snap being null.
    assert result.buckets[3].total_count == 3
    assert result.buckets[3].hit_rate == pytest.approx(2 / 3)


# ── Endpoint ──────────────────────────────────────────────────────────────


def test_endpoint_404_when_symbol_unknown(client: TestClient):
    with patch(
        "apps.api.routers.calibration.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get("/v1/calibration?instrument_code=ZZZ")
    assert resp.status_code == 404


def test_endpoint_rejects_bucket_count_above_10(client: TestClient):
    resp = client.get("/v1/calibration?bucket_count=15")
    assert resp.status_code == 422


def test_endpoint_rejects_bucket_count_below_2(client: TestClient):
    resp = client.get("/v1/calibration?bucket_count=1")
    assert resp.status_code == 422


def test_endpoint_returns_400_on_non_divisor_bucket_count(client: TestClient):
    instrument = type("I", (), {"id": uuid.uuid4()})()
    with patch(
        "apps.api.routers.calibration.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ):
        resp = client.get("/v1/calibration?bucket_count=3")
    assert resp.status_code == 400
    assert "evenly divide" in resp.json()["detail"]


def test_endpoint_happy_path(client: TestClient):
    instrument = type("I", (), {"id": uuid.uuid4()})()
    fake_result = svc.CalibrationResult(
        instrument_code="NG",
        buckets=[
            svc.CalibrationBucket(
                label="60-80",
                lower_pct=60,
                upper_pct=80,
                claimed_mean=70.0,
                total_count=14,
                resolved_count=14,
                hit_count=9,
                hit_rate=9 / 14,
            ),
        ],
        total_entries=14,
        resolved_entries=14,
        unresolved_entries=0,
        summary="Your 70% theses resolved at 64% (n=14).",
    )
    with patch(
        "apps.api.routers.calibration.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "apps.api.routers.calibration.compute_calibration",
        new=AsyncMock(return_value=fake_result),
    ):
        resp = client.get("/v1/calibration")
    assert resp.status_code == 200
    body = resp.json()
    assert body["instrument_code"] == "NG"
    assert body["summary"] == "Your 70% theses resolved at 64% (n=14)."
    assert body["total_entries"] == 14
    assert body["buckets"][0]["claimed_mean"] == 70.0
    assert body["buckets"][0]["hit_rate"] == pytest.approx(9 / 14)
