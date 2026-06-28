"""The AI-narrative provenance caveat must reflect the ACTUAL data path, not the
old unconditional "synthetic mock data" claim (which was false whenever real
adapters + a real LLM were configured — the live deployment).

Locks: (1) real config → an accurate real-data caveat with no "synthetic/mock"
language; (2) mock/dev config → an honest illustrative caveat; (3) a source guard
so the old false string can't be reintroduced into the LLM caveats.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from apps.api.services.llm_explainer import data_provenance_caveat
from apps.api.src.settings import settings

_LLM_SRC = Path(__file__).resolve().parents[1] / "services" / "llm_explainer.py"


@pytest.fixture
def restore_settings():
    before = (settings.llm_mode, settings.adapter_market)
    yield
    settings.llm_mode, settings.adapter_market = before


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


def test_source_no_longer_hardcodes_the_false_caveat():
    """Guard: the unconditional 'synthetic mock data' caveat must not reappear in
    the LLM caveat lists (the docstring uses a hyphenated reference, not the phrase)."""
    src = _LLM_SRC.read_text(encoding="utf-8")
    assert "synthetic mock data" not in src
