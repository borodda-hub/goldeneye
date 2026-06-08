"""Phase A2 — lock the derived LLM-narrative envelope-confidence mapping.

``derive_envelope_confidence`` starts from the ensemble's agreement-derived confidence
and down-modulates by the predicted band width (wider band ⇒ lower confidence, never
higher). These tests pin the mapping and the structural "never upgrades" property so a
future change can't silently re-introduce an overconfident or hardcoded envelope.
"""
from __future__ import annotations

import pytest

from apps.api.services.ensemble import (
    _CONFIDENCE_RANK,
    _VERY_WIDE_BAND_PCT,
    _WIDE_BAND_PCT,
    derive_envelope_confidence,
)


@pytest.mark.parametrize(
    ("ensemble_confidence", "band_width", "expected"),
    [
        # band_width=None → agreement tier passes through unchanged
        ("high", None, "high"),
        ("medium", None, "medium"),
        ("low", None, "low"),
        # tight band (below the wide cutoff) → unchanged
        ("high", 0.04, "high"),
        ("medium", 0.04, "medium"),
        ("low", 0.0, "low"),
        # wide band → "high" capped to "medium"; medium/low unchanged
        ("high", _WIDE_BAND_PCT, "medium"),
        ("high", 0.12, "medium"),
        ("medium", 0.12, "medium"),
        ("low", 0.12, "low"),
        # very wide band → everything floored to "low"
        ("high", _VERY_WIDE_BAND_PCT, "low"),
        ("medium", _VERY_WIDE_BAND_PCT, "low"),
        ("high", 0.30, "low"),
        # unknown/garbage agreement tier → conservative "low"
        ("unknown", None, "low"),
        ("", 0.04, "low"),
    ],
)
def test_derive_envelope_confidence_mapping(ensemble_confidence, band_width, expected):
    assert (
        derive_envelope_confidence(
            ensemble_confidence=ensemble_confidence, band_width=band_width
        )
        == expected
    )


def test_boundaries_are_inclusive():
    """The cutoffs are >= (inclusive), exercised at the exact threshold values."""
    assert derive_envelope_confidence(
        ensemble_confidence="high", band_width=_WIDE_BAND_PCT
    ) == "medium"
    assert derive_envelope_confidence(
        ensemble_confidence="high", band_width=_VERY_WIDE_BAND_PCT
    ) == "low"
    # Just below the wide cutoff → no down-modulation.
    assert derive_envelope_confidence(
        ensemble_confidence="high", band_width=_WIDE_BAND_PCT - 1e-9
    ) == "high"


def test_never_upgrades_confidence():
    """Structural invariant: the derived rank is never higher than the agreement rank."""
    widths = [None, 0.0, 0.04, _WIDE_BAND_PCT, 0.12, _VERY_WIDE_BAND_PCT, 0.5]
    for base in ("low", "medium", "high"):
        for w in widths:
            out = derive_envelope_confidence(ensemble_confidence=base, band_width=w)
            assert _CONFIDENCE_RANK[out] <= _CONFIDENCE_RANK[base], (base, w, out)
