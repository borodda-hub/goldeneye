"""THROWAWAY — Phase B5 golden-baseline capture (delete before the final commit).

Run ONCE on the UNREFACTORED engine to freeze the commodity baseline into
fixtures/b5_golden.json, then run the golden test to confirm green. After the
refactor the same fixture is the byte-identical lock. The JSON fixture is kept;
this script is not.

    uv run --directory apps/api python _b5_golden_capture.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `apps.api.*` importable when run as a bare script from apps/api.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.api.tests.test_asset_config_golden import GOLDEN_PATH, build_golden  # noqa: E402

GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
GOLDEN_PATH.write_text(build_golden(), encoding="utf-8")
print(f"wrote golden baseline → {GOLDEN_PATH} ({GOLDEN_PATH.stat().st_size} bytes)")
