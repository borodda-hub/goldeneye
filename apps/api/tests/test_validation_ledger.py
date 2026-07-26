"""Phase A3 — the drift-lock between the Validation page and the claims SOT.

`docs/MODEL_DILIGENCE.md` is the single source of truth for what is
validated; `services/validation_ledger.py` is its structured mirror that
the /validation page renders. A drifted honesty page is worse than none —
so these tests make the two structurally unable to diverge:

1. ANCHOR: every code row's `doc_anchor` appears on EXACTLY ONE line of
   the doc's ledger table (renamed/removed doc rows break the build).
2. VERDICT: that same line contains the row's `doc_marker` (a doc verdict
   change without a code change breaks the build).
3. PARITY: the doc table has exactly as many body rows as the code ledger
   (a row added to either side alone breaks the build).

Plus payload hygiene: provenance present on every row (the MODEL_DILIGENCE
non-negotiable) and no forbidden phrases in any user-facing string
(AI_BEHAVIOR §forbidden_phrases — this page is UI copy).
"""
from __future__ import annotations

import re
from pathlib import Path

from apps.api.services.safety import scan_for_forbidden
from apps.api.services.validation_ledger import ROWS, ledger_rows

_DOC = Path(__file__).resolve().parents[3] / "docs" / "MODEL_DILIGENCE.md"


def _ledger_table_lines() -> list[str]:
    """Body rows of the doc's '## Validation ledger' table."""
    text = _DOC.read_text(encoding="utf-8")
    section = text.split("## Validation ledger", 1)[1].split("\n## ", 1)[0]
    lines = [ln for ln in section.splitlines() if ln.startswith("|")]
    # Drop the header row and the |---| separator.
    return [ln for ln in lines if not re.match(r"^\|\s*-{2,}", ln)][1:]


def test_every_row_anchors_to_exactly_one_doc_line():
    lines = _ledger_table_lines()
    for row in ROWS:
        hits = [ln for ln in lines if row.doc_anchor in ln]
        assert len(hits) == 1, (
            f"row {row.key!r}: doc_anchor {row.doc_anchor!r} matched "
            f"{len(hits)} ledger lines (must be exactly 1) — the page and "
            f"MODEL_DILIGENCE.md have drifted"
        )


def test_verdict_marker_on_the_anchored_line():
    lines = _ledger_table_lines()
    for row in ROWS:
        line = next(ln for ln in lines if row.doc_anchor in ln)
        assert row.doc_marker in line, (
            f"row {row.key!r}: expected marker {row.doc_marker!r} on the "
            f"anchored doc line — the doc's verdict changed without the "
            f"page's ledger changing (or vice versa)"
        )


def test_row_count_parity_with_the_doc_table():
    doc_rows = _ledger_table_lines()
    assert len(doc_rows) == len(ROWS), (
        f"MODEL_DILIGENCE.md ledger has {len(doc_rows)} rows but the page "
        f"ledger has {len(ROWS)} — a claim was added or removed on one side "
        f"only. Update both in the same commit (S7)."
    )


def test_every_row_carries_provenance_and_unique_key():
    keys = [r["key"] for r in ledger_rows()]
    assert len(keys) == len(set(keys))
    for r in ledger_rows():
        assert r["provenance"], f"row {r['key']!r} missing provenance"
        assert r["verdict"], f"row {r['key']!r} missing verdict"
        assert "doc_anchor" not in r  # internal fields never leave the API


def test_no_forbidden_phrases_in_page_strings():
    """The ledger is UI copy — hold it to the AI_BEHAVIOR phrase bar."""
    for r in ledger_rows():
        for field in ("claim", "summary", "evidence"):
            hits = scan_for_forbidden(r[field])
            assert not hits, f"row {r['key']!r} field {field}: forbidden {hits}"
