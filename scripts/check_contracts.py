"""Contract drift guard — schema-parity half of the F1 contract lock.

Compares the *live* FastAPI OpenAPI schema (imported directly, no running server)
against the committed ``packages/contracts/openapi.json``. Date-shaped ``default``
values are normalized to ``<DATE>`` on both sides before comparison, so a parameter
whose default is (or later becomes) date-dependent can't make the diff flap from one
day to the next. See ``docs/PHASE_F_PLAN.md`` §0 for why this guard exists (the
"date-dependent ``chart/bars from``" premise came from a now-stale HANDOFF note; the
current code uses a fixed ``2025-05-10`` literal, but the guard is cheap insurance).

The *types-parity* half (committed ``openapi.json`` -> regenerated ``src/index.ts``)
is enforced separately by regenerating the types and running ``git diff --exit-code``;
see ``.github/workflows/ci.yml`` (job ``contracts``) and the ``contracts:check`` script.

Run via the ``apps/api`` uv environment (it imports the app):
    uv run --directory apps/api python ../../scripts/check_contracts.py
Exits 0 on parity, 1 on drift (with a readable diff).
"""

from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# Make `src` (the FastAPI app package) importable regardless of cwd. main.py then
# bootstraps the project root so `apps.api.*` resolves.
sys.path.insert(0, str(ROOT / "apps" / "api"))

from src.main import app  # noqa: E402

COMMITTED = ROOT / "packages" / "contracts" / "openapi.json"
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def normalize(obj: Any) -> Any:
    """Recursively replace date-shaped ``default`` string values with ``<DATE>``."""
    if isinstance(obj, dict):
        return {
            k: (
                "<DATE>"
                if k == "default" and isinstance(v, str) and _DATE_RE.match(v)
                else normalize(v)
            )
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [normalize(x) for x in obj]
    return obj


def main() -> int:
    fresh = normalize(app.openapi())
    if not COMMITTED.exists():
        print(f"contracts: committed schema missing at {COMMITTED}", file=sys.stderr)
        return 1
    committed = normalize(json.loads(COMMITTED.read_text(encoding="utf-8")))

    if fresh == committed:
        print("contracts: schema parity OK (date-normalized)")
        return 0

    fresh_lines = json.dumps(fresh, indent=2, sort_keys=True).splitlines()
    committed_lines = json.dumps(committed, indent=2, sort_keys=True).splitlines()
    diff = "\n".join(
        difflib.unified_diff(
            committed_lines,
            fresh_lines,
            fromfile="committed packages/contracts/openapi.json",
            tofile="live FastAPI schema",
            lineterm="",
        )
    )
    print(
        "contracts: SCHEMA DRIFT — the live FastAPI schema differs from "
        "packages/contracts/openapi.json\n"
    )
    print(diff[:8000])
    print(
        "\nFix: regenerate the contracts from the live schema:\n"
        "  curl -s http://localhost:8000/openapi.json -o packages/contracts/openapi.json"
        " && pnpm contracts:gen:local\n"
        "  (or run `pnpm contracts:check` locally — it imports the app directly, "
        "no server needed)"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
