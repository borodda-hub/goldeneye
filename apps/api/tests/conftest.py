"""Test-session config shared with the tests under apps/api/tests.

Mirrors the top-level tests/conftest.py: forces the LLM into fake/canned
mode at session start so tests are deterministic, fast, and free even when
apps/api/.env has LLM_MODE=real for the dev server.
"""
from __future__ import annotations


def pytest_configure(config):  # noqa: D401 — pytest hook
    """Set llm_mode='fake' once at session start."""
    from apps.api.src.settings import settings

    settings.llm_mode = "fake"  # type: ignore[assignment]
