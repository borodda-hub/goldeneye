"""The AI-narrative provenance caveat must reflect the ACTUAL data path, not the
old unconditional "synthetic mock data" claim (which was false whenever real
adapters + a real LLM were configured — the live deployment).

Locks: (1) real config → an accurate real-data caveat with no "synthetic/mock"
language; (2) mock/dev config → an honest illustrative caveat; (3) a source guard
so the old false string can't be reintroduced into the LLM caveats.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from apps.api.services.feature_provenance import (
    FeatureProvenance,
    derive_feature_provenance,
    set_cached_feature_provenance,
)
from apps.api.services.llm_explainer import data_provenance_caveat
from apps.api.src.settings import settings

_LLM_SRC = Path(__file__).resolve().parents[1] / "services" / "llm_explainer.py"


@pytest.fixture
def restore_settings():
    before = (settings.llm_mode, settings.adapter_market)
    set_cached_feature_provenance(None)  # each test states its own observation
    yield
    settings.llm_mode, settings.adapter_market = before
    set_cached_feature_provenance(None)


def _prov(cot: bool, storage: bool) -> FeatureProvenance:
    return FeatureProvenance(
        cot_real=cot, storage_real=storage, observed_at=datetime.now(UTC)
    )


def test_real_config_is_accurate_and_not_synthetic(restore_settings):
    settings.llm_mode = "real"
    settings.adapter_market = "yahoo_delayed"
    cav = data_provenance_caveat()
    assert "AI-generated narrative" in cav
    assert "delayed real market prices" in cav
    # The whole point: a real-data deployment must NOT claim it's synthetic/mock.
    low = cav.lower()
    assert "synthetic" not in low and "mock" not in low


def test_mock_config_is_honest_about_being_illustrative(restore_settings):
    settings.llm_mode = "fake"
    settings.adapter_market = "mock"
    cav = data_provenance_caveat()
    assert "Placeholder narrative" in cav
    assert "delayed/seeded market data" in cav
    assert "illustrative" in cav.lower()


def test_real_market_with_fake_llm_labels_placeholder_narrative(restore_settings):
    settings.llm_mode = "fake"
    settings.adapter_market = "yahoo_delayed"
    cav = data_provenance_caveat()
    assert "Placeholder narrative" in cav
    assert "delayed real market prices" in cav


# ── 31d: the positioning/storage clause is OBSERVED-derived ───────────────


def test_no_observation_keeps_the_conservative_clause(restore_settings):
    settings.llm_mode = "real"
    settings.adapter_market = "yahoo_delayed"
    assert "some positioning/storage inputs are illustrative" in data_provenance_caveat()


def test_observed_real_features_flip_the_clause(restore_settings):
    """The #12-flagged fragility, retired: once real COT+EIA actually flow,
    the caveat must say so instead of understating with 'illustrative'."""
    settings.llm_mode = "real"
    settings.adapter_market = "yahoo_delayed"
    set_cached_feature_provenance(_prov(cot=True, storage=True))
    cav = data_provenance_caveat()
    assert "positioning/storage inputs are real published CFTC/EIA data" in cav
    assert "illustrative" not in cav.lower()


def test_observed_mixed_states_are_labeled_per_feed(restore_settings):
    settings.llm_mode = "real"
    settings.adapter_market = "yahoo_delayed"
    set_cached_feature_provenance(_prov(cot=True, storage=False))
    cav = data_provenance_caveat()
    assert "positioning inputs are real CFTC data" in cav
    assert "storage inputs are illustrative" in cav
    set_cached_feature_provenance(_prov(cot=False, storage=True))
    cav = data_provenance_caveat()
    assert "storage inputs are real EIA data" in cav
    assert "positioning inputs are illustrative" in cav


def test_observed_nothing_real_stays_conservative(restore_settings):
    settings.llm_mode = "real"
    settings.adapter_market = "yahoo_delayed"
    set_cached_feature_provenance(_prov(cot=False, storage=False))
    assert "some positioning/storage inputs are illustrative" in data_provenance_caveat()


def test_derivation_requires_real_source_AND_freshness():
    """Stale-real must NOT be advertised as real (a dead ingestion job is
    exactly the issue-#13 failure mode)."""
    today = date(2026, 7, 25)
    fresh = today - timedelta(days=3)
    stale = today - timedelta(days=40)
    assert derive_feature_provenance("cftc", fresh, "eia", fresh, today) == (True, True)
    assert derive_feature_provenance("cftc", stale, "eia", stale, today) == (False, False)
    assert derive_feature_provenance("mock", fresh, "mock", fresh, today) == (False, False)
    assert derive_feature_provenance(None, None, None, None, today) == (False, False)
    # future-dated rows are suspicious, not fresh
    future = today + timedelta(days=2)
    assert derive_feature_provenance("cftc", future, "eia", fresh, today)[0] is False


def test_source_no_longer_hardcodes_the_false_caveat():
    """Guard: the unconditional 'synthetic mock data' caveat must not reappear in
    the LLM caveat lists (the docstring uses a hyphenated reference, not the phrase)."""
    src = _LLM_SRC.read_text(encoding="utf-8")
    assert "synthetic mock data" not in src
