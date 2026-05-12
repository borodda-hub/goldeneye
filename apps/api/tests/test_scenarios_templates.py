"""Regression test for the /v1/scenarios/templates endpoint.

The endpoint reads packages/fixtures/scenario_templates.json. The fixture
path was previously computed with Path(__file__).parents[4], which walked
one level above the repo root — the file never existed at that location
and the endpoint always returned an empty list. The Scenario Lab UI
therefore had no template gallery to render.
"""
from __future__ import annotations

from pathlib import Path

from apps.api.routers.scenarios import _FIXTURES_DIR


def test_fixtures_dir_resolves_to_real_packages_fixtures_directory():
    assert _FIXTURES_DIR.exists(), (
        f"Fixtures dir {_FIXTURES_DIR} does not exist — path resolution is wrong"
    )
    assert _FIXTURES_DIR.is_dir(), f"{_FIXTURES_DIR} is not a directory"
    assert _FIXTURES_DIR.name == "fixtures"
    assert _FIXTURES_DIR.parent.name == "packages"


def test_scenario_templates_fixture_exists():
    path = _FIXTURES_DIR / "scenario_templates.json"
    assert path.exists(), f"Expected fixture at {path}"


def test_scenario_templates_fixture_has_six_well_formed_templates():
    import json

    path = _FIXTURES_DIR / "scenario_templates.json"
    templates = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(templates, list)
    assert len(templates) == 6, f"Expected 6 templates, got {len(templates)}"
    valid_types = {"weather", "lng_export", "production", "storage"}
    for t in templates:
        assert isinstance(t, dict)
        assert "name" in t and isinstance(t["name"], str)
        assert "shocks" in t and isinstance(t["shocks"], list) and t["shocks"]
        for shock in t["shocks"]:
            assert shock.get("type") in valid_types, f"bad shock type: {shock}"
