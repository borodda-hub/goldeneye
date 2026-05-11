"""
Verifies that the FastAPI OpenAPI schema can be generated without errors
and that key endpoint paths are present.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_openapi_schema_generates():
    from apps.api.src.main import app

    schema = app.openapi()
    assert schema is not None
    assert "openapi" in schema
    assert "paths" in schema


def test_health_path_present():
    from apps.api.src.main import app

    schema = app.openapi()
    paths = schema["paths"]
    assert "/v1/health" in paths


def test_required_paths_present():
    from apps.api.src.main import app

    schema = app.openapi()
    paths = schema["paths"]

    required = [
        "/v1/dashboard/summary",
        "/v1/chart/bars",
        "/v1/chart/curve",
        "/v1/signals/current",
        "/v1/signals/history",
        "/v1/scenarios/run",
        "/v1/scenarios/templates",
        "/v1/scenarios/runs",
        "/v1/journal",
        "/v1/paper-trades/open",
        "/v1/admin/data-health",
        "/v1/admin/alerts",
        "/v1/explain/market",
        "/v1/explain/signal",
        "/v1/explain/scenario",
        "/v1/explain/journal",
    ]

    missing = [p for p in required if p not in paths]
    assert not missing, f"Missing paths in OpenAPI schema: {missing}"
