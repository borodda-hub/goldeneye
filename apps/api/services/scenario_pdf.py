"""Executive-grade PDF export for a single scenario run.

Layout: title block → executive summary → shocks table → assumptions /
counterarguments / data-to-monitor → narrative → caveats → disclaimer footer
on every page.

Light-on-white printable aesthetic — the dashboard is dark-themed for screens,
but PDFs need to print and read on paper. Brand chrome (NGTI banner + footer)
applied via the canvas-level onPage hook.
"""
from __future__ import annotations

import html
from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.api.services.safety import DISCLAIMER

# Brand palette — printable / executive, not the dark-mode web tokens.
INK_1 = colors.HexColor("#0f172a")  # near-black for primary text
INK_2 = colors.HexColor("#374151")  # darker neutral for body
INK_3 = colors.HexColor("#6b7280")  # muted labels / footer text
ACCENT = colors.HexColor("#0066cc")
SURFACE_2 = colors.HexColor("#f3f4f6")  # table header band
LINE = colors.HexColor("#e5e7eb")
UP = colors.HexColor("#0a7c5a")
DOWN = colors.HexColor("#b21f3d")
FLAT = INK_3


def _direction_color(direction: str | None) -> colors.Color:
    if direction == "bullish":
        return UP
    if direction == "bearish":
        return DOWN
    return FLAT


def _fmt_range(r: Any) -> str:
    if not isinstance(r, dict):
        return "—"
    lo, hi = r.get("low"), r.get("high")
    if lo is None or hi is None:
        return "—"
    return f"{float(lo) * 100:+.2f}% to {float(hi) * 100:+.2f}%"


def _fmt_shock_magnitude(s: dict[str, Any]) -> str:
    t = s.get("type")
    if t == "weather":
        return f"{s.get('region', '?')}: {s.get('delta_temp_f', 0):+.1f}°F"
    if t in ("lng_export", "production"):
        return f"{s.get('delta_bcfd', 0):+.2f} Bcf/d"
    if t == "storage":
        return f"{s.get('delta_bcf', 0):+.1f} Bcf vs consensus"
    return "—"


def _esc(text: Any) -> str:
    """Escape for reportlab's Paragraph mini-HTML, preserving line breaks."""
    if text is None:
        return ""
    return html.escape(str(text)).replace("\n", "<br/>")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "Brand",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=INK_3,
            spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=INK_1,
            leading=22,
            spaceAfter=4,
            alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontSize=9,
            textColor=INK_3,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=INK_1,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=INK_2,
            leading=14,
            alignment=TA_JUSTIFY,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["Normal"],
            fontSize=8,
            textColor=INK_3,
            leading=11,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontSize=10,
            textColor=INK_2,
            leading=14,
            leftIndent=14,
        ),
    }


def _summary_table(result: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    direction = str(result.get("directional_pressure") or "—")
    conf = str(result.get("confidence") or "—")
    dir_color = _direction_color(result.get("directional_pressure"))
    rows = [
        [
            Paragraph("<b>Directional Pressure</b>", styles["small"]),
            Paragraph(
                f'<font color="{dir_color.hexval()}"><b>{_esc(direction).upper()}</b></font>',
                styles["body"],
            ),
        ],
        [
            Paragraph("<b>Confidence Band</b>", styles["small"]),
            Paragraph(_esc(conf).title(), styles["body"]),
        ],
        [
            Paragraph("<b>Affected Timeframe</b>", styles["small"]),
            Paragraph(_esc(result.get("affected_timeframe") or "—"), styles["body"]),
        ],
        [
            Paragraph("<b>Expected Range</b>", styles["small"]),
            Paragraph(_fmt_range(result.get("expected_pct_range")), styles["body"]),
        ],
    ]
    tbl = Table(rows, colWidths=[2.0 * inch, 4.5 * inch])
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return tbl


def _shocks_table(shocks: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    rows: list[list[Any]] = [
        [
            Paragraph("<b>Type</b>", styles["small"]),
            Paragraph("<b>Magnitude</b>", styles["small"]),
            Paragraph("<b>Days</b>", styles["small"]),
        ]
    ]
    for s in shocks:
        rows.append(
            [
                Paragraph(_esc(s.get("type", "?")).replace("_", " "), styles["body"]),
                Paragraph(_fmt_shock_magnitude(s), styles["body"]),
                Paragraph(_esc(s.get("days", "—")), styles["body"]),
            ]
        )
    tbl = Table(rows, colWidths=[1.6 * inch, 3.8 * inch, 1.1 * inch])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), SURFACE_2),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return tbl


def _numbered_list_paragraphs(
    items: list[str], styles: dict[str, ParagraphStyle]
) -> list[Paragraph]:
    out: list[Paragraph] = []
    for i, item in enumerate(items, 1):
        out.append(Paragraph(f"<b>{i}.</b> {_esc(item)}", styles["bullet"]))
    return out


def _bullet_paragraphs(
    items: list[str], styles: dict[str, ParagraphStyle]
) -> list[Paragraph]:
    return [Paragraph(f"• {_esc(item)}", styles["bullet"]) for item in items]


def _on_page(canvas: Any, doc: Any) -> None:
    """Branded footer + page number on every page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(INK_3)
    canvas.drawString(
        0.75 * inch,
        0.45 * inch,
        "NGTI · Research and decision-support prototype. Not financial advice.",
    )
    canvas.drawRightString(
        letter[0] - 0.75 * inch,
        0.45 * inch,
        f"Page {canvas.getPageNumber()}",
    )
    # Hairline above the footer.
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(0.75 * inch, 0.65 * inch, letter[0] - 0.75 * inch, 0.65 * inch)
    canvas.restoreState()


def render_scenario_pdf(run: dict[str, Any]) -> bytes:
    """Render a scenario run dict to a PDF, return bytes.

    Args:
      run: shape from /v1/scenarios/runs/{run_id} — `name`, `created_at`,
           `shocks` (list), `result` (with directional_pressure, confidence,
           affected_timeframe, expected_pct_range, assumptions,
           counterarguments, data_needed_to_validate, narrative, safety).
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.85 * inch,
        title=f"NGTI Scenario: {run.get('name', 'Untitled')}",
        author="NGTI",
    )
    styles = _styles()
    story: list[Any] = []

    # ── Header band ──────────────────────────────────────────────────────
    name = run.get("name") or "Untitled Scenario"
    created_at = run.get("created_at") or datetime.utcnow().isoformat()
    story.append(Paragraph("NGTI · NATURAL GAS TRADING INTELLIGENCE", styles["brand"]))
    story.append(Paragraph("SCENARIO REPORT", styles["brand"]))
    story.append(Paragraph(_esc(name), styles["title"]))
    instrument_text = f"Instrument: NG · Henry Hub Natural Gas &nbsp;&nbsp;|&nbsp;&nbsp; Generated: {_esc(created_at)}"
    story.append(Paragraph(instrument_text, styles["subtitle"]))
    story.append(Spacer(1, 0.18 * inch))

    # ── Executive summary ────────────────────────────────────────────────
    result = run.get("result") or {}
    story.append(Paragraph("Executive Summary", styles["h2"]))
    story.append(_summary_table(result, styles))

    # ── Shocks applied ───────────────────────────────────────────────────
    shocks = run.get("shocks") or []
    if shocks:
        story.append(Paragraph("Shocks Applied", styles["h2"]))
        story.append(_shocks_table(shocks, styles))

    # ── Assumptions / Counterarguments / Data needed ─────────────────────
    section_map = [
        ("Key Assumptions", result.get("assumptions") or []),
        ("Counterarguments", result.get("counterarguments") or []),
        ("Data to Monitor", result.get("data_needed_to_validate") or []),
    ]
    for heading, items in section_map:
        if not items:
            continue
        story.append(Paragraph(heading, styles["h2"]))
        story.extend(_numbered_list_paragraphs(list(items), styles))

    # ── Narrative ────────────────────────────────────────────────────────
    narrative = result.get("narrative")
    if isinstance(narrative, str) and narrative.strip():
        story.append(Paragraph("Narrative", styles["h2"]))
        for chunk in narrative.split("\n\n"):
            chunk = chunk.strip()
            if chunk:
                story.append(Paragraph(_esc(chunk), styles["body"]))
                story.append(Spacer(1, 0.06 * inch))

    # ── Caveats ──────────────────────────────────────────────────────────
    safety = result.get("safety") or {}
    caveats = safety.get("caveats") or []
    if caveats:
        story.append(Paragraph("Safety &amp; Caveats", styles["h2"]))
        story.extend(_bullet_paragraphs(list(caveats), styles))

    # ── Disclaimer ───────────────────────────────────────────────────────
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph("<b>Disclaimer</b>", styles["small"]))
    story.append(Paragraph(_esc(DISCLAIMER), styles["small"]))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()
