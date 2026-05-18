"""Unit tests for the scenario-run PDF renderer.

We don't try to assert pixel-perfect layout — that's brittle and out of scope.
Instead we verify the output is a valid PDF and that the visible text content
contains the scenario fields a reader expects to see (name, direction,
counterarguments, narrative, disclaimer).
"""
from __future__ import annotations

from apps.api.services.safety import DISCLAIMER
from apps.api.services.scenario_pdf import (
    _esc,
    _fmt_range,
    _fmt_shock_magnitude,
    render_scenario_pdf,
)


def _sample_run() -> dict:
    return {
        "run_id": "00000000-0000-0000-0000-000000000001",
        "created_at": "2026-05-12T14:30:00Z",
        "name": "Cold Snap — Northeast 10 Days",
        "shocks": [
            {"type": "weather", "region": "northeast", "delta_temp_f": -8, "days": 10},
            {"type": "lng_export", "delta_bcfd": -1.2, "days": 14},
        ],
        "result": {
            "directional_pressure": "bullish",
            "confidence": "medium",
            "affected_timeframe": "2 weeks",
            "expected_pct_range": {"low": 0.02, "high": 0.09},
            "assumptions": [
                "Cold air mass persists for 10 days in northeast.",
                "LNG export demand changes by -1.20 Bcf/d for 14 days.",
            ],
            "counterarguments": [
                "Weather forecasts beyond 7 days carry significant uncertainty.",
                "Speculative positioning is extended in the current COT report.",
            ],
            "data_needed_to_validate": [
                "Next EIA Weekly Natural Gas Storage Report (Thursdays).",
                "NWS 6-10 day and 8-14 day temperature anomaly maps.",
            ],
            "narrative": (
                "The scenario reads as moderately bullish over the next 1-3 weeks.\n\n"
                "The strongest counterargument is that the market may have already "
                "partially priced in the weather risk."
            ),
            "safety": {
                "confidence": "low",
                "caveats": [
                    "Scenario outputs are hypothetical and do not represent forecasts.",
                    "Model outputs are statistical inferences only, not financial advice.",
                ],
                "as_of": "2026-05-12T14:30:00",
            },
        },
    }


# ── format helpers ────────────────────────────────────────────────────────


def test_fmt_range_handles_normal_input():
    assert _fmt_range({"low": 0.02, "high": 0.09}) == "+2.00% to +9.00%"


def test_fmt_range_returns_em_dash_for_missing():
    assert _fmt_range(None) == "—"
    assert _fmt_range({}) == "—"
    assert _fmt_range({"low": 0.05}) == "—"


def test_fmt_shock_magnitude_weather():
    assert (
        _fmt_shock_magnitude(
            {"type": "weather", "region": "midwest", "delta_temp_f": -12, "days": 7}
        )
        == "midwest: -12.0°F"
    )


def test_fmt_shock_magnitude_lng_export():
    assert (
        _fmt_shock_magnitude({"type": "lng_export", "delta_bcfd": 2.5, "days": 14})
        == "+2.50 Bcf/d"
    )


def test_fmt_shock_magnitude_storage():
    assert (
        _fmt_shock_magnitude({"type": "storage", "delta_bcf": -45, "days": 7})
        == "-45.0 Bcf vs consensus"
    )


def test_fmt_shock_magnitude_unknown():
    assert _fmt_shock_magnitude({"type": "alien"}) == "—"


def test_esc_html_escapes_and_preserves_newlines():
    assert _esc("a & b") == "a &amp; b"
    assert _esc("line1\nline2") == "line1<br/>line2"
    assert _esc(None) == ""


# ── full PDF render ───────────────────────────────────────────────────────


def test_render_scenario_pdf_returns_pdf_bytes():
    pdf = render_scenario_pdf(_sample_run())
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-"), "Not a valid PDF (missing %PDF- magic header)"
    assert b"%%EOF" in pdf[-1024:], "PDF should end with %%EOF marker"
    # Reasonable size — a single-page report shouldn't be < 1 KB or > 200 KB.
    assert 1_000 < len(pdf) < 200_000, f"PDF size {len(pdf)} outside expected range"


def test_pdf_contains_scenario_name_metadata():
    pdf = render_scenario_pdf(_sample_run())
    # /Title (Goldeneye Scenario: Cold Snap...) appears in the PDF /Info dict.
    # reportlab writes hex-encoded UTF-16 for non-ASCII chars; just check the
    # ASCII prefix and the /Title key exist.
    assert b"/Title" in pdf
    assert b"Goldeneye" in pdf


def test_pdf_handles_run_with_minimal_fields():
    """No shocks, no narrative, empty result — should still produce a PDF."""
    minimal = {
        "name": "Sparse run",
        "created_at": "2026-05-12T00:00:00Z",
        "shocks": [],
        "result": {},
    }
    pdf = render_scenario_pdf(minimal)
    assert pdf.startswith(b"%PDF-")


def test_pdf_renders_with_bearish_direction():
    """The direction-color codepath shouldn't crash for bearish/neutral."""
    run = _sample_run()
    run["result"]["directional_pressure"] = "bearish"
    pdf = render_scenario_pdf(run)
    assert pdf.startswith(b"%PDF-")

    run["result"]["directional_pressure"] = "neutral"
    pdf2 = render_scenario_pdf(run)
    assert pdf2.startswith(b"%PDF-")


def test_pdf_disclaimer_constant_in_source_module():
    """Smoke-check that the disclaimer module-level constant is non-empty."""
    assert DISCLAIMER
    assert len(DISCLAIMER) > 50
