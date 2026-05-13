import sys
from pathlib import Path

# Add repo root so `apps.api.*` imports resolve in all test suites under tests/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# Force the LLM into fake/canned mode for the entire test session, regardless
# of what apps/api/.env says. The dev .env may carry LLM_MODE=real for live
# Claude in the browser, but every test that exercises summarize_market /
# explain_signal / narrate_scenario / coach_dq / critique_thesis must use
# canned responses to stay deterministic, fast, and free.
def pytest_configure(config):  # noqa: D401 — pytest hook
    """Set llm_mode='fake' once at session start, before any test imports it."""
    from apps.api.src.settings import settings

    settings.llm_mode = "fake"  # type: ignore[assignment]
