"""
Build the v5 PILOT workbook — chunk-aware retrieval for the three pilot
reports only (True Corporation, BDMS, Krungthai Bank).

Adds a new Column J ("Cross-References v5 — chunk-aware") to the v4
workbook. Populates real content for the 14 sample claims that come from
the pilot reports; marks the remaining rows as pending.

Purpose: verify that mixing ADE text chunks into the retrieval pool
visibly improves the evidence pack over the claims-only v4 retrieval.
If the pilot succeeds, we expand to the full 24-report run.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from copy import copy
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from config.settings import OUTPUTS_DIR
from utils.retrieval import (
    DEFAULT_CROSS_SECTION_TARGET,
    DEFAULT_MIN_SIMILARITY,
    DEFAULT_SAME_SECTION_TARGET,
    MixedResult,
    load_chunks_from_chunks_json,
    retrieve_chunk_aware_refs,
)

# Map company name (as it appears in the v2 sample JSON) → report stem used
# for chunks/full JSON filename lookups.
PILOT_COMPANY_TO_STEM = {
    "True Corporation": "TRUE-2024-SR-EN",
    "Bangkok Dusit Medical Services": "BDMS-2024-SR-EN",
    "Krungthai Bank": "KTB-2024-SR-EN",
}

# Target the insert at Column J (10). v4 has H=v3 refs, I=v4 refs, J-N=scores,
# O=notes. After insert-at-10: H=v3, I=v4, J=v5 NEW, K-O=scores, P=notes.
V5_NEW_COL_IDX = 10

HEADER_FILL_GREEN_DARK = PatternFill(start_color="FF145A32", end_color="FF145A32", fill_type="solid")
HEADER_FONT_WHITE = Font(color="FFFFFFFF", bold=True)
CROSS_REF_ALIGNMENT = Alignment(wrap_text=True, vertical="top", horizontal="left")
THIN_BORDER = Border(
    left=Side(style="thin", color="FFCCCCCC"),
    right=Side(style="thin", color="FFCCCCCC"),
    top=Side(style="thin", color="FFCCCCCC"),
    bottom=Side(style="thin", color="FFCCCCCC"),
)


# ── Rendering ────────────────────────────────────────────────────────────────

# ADE output contains HTML-ish anchor tags and visual-content placeholders that
# are useful for grounding but noisy for an expert reader. Strip them for display.
_ANCHOR_RE = re.compile(r"<a id=['\"][^'\"]*['\"]></a>")
_VISUAL_RE = re.compile(r"<::[^:]*::>")
_MULTI_BLANK_RE = re.compile(r"\n\s*\n+")


def _clean_chunk_text(text: str) -> str:
    """Remove ADE grounding artifacts and collapse excess whitespace for display."""
    t = _ANCHOR_RE.sub("", text or "")
    t = _VISUAL_RE.sub("", t)
    t = _MULTI_BLANK_RE.sub("\n", t)
    return t.strip()


def render_v5_cell(result: MixedResult) -> str:
    """Render a MixedResult for display in Excel. Shows source_type per ref."""
    lines: list[str] = []
    lines.append("── Cross-section references (different section) ──")
    if result.cross_section:
        for ref in result.cross_section:
            tag = "CLAIM" if ref.source_type == "claim" else ref.chunk_type or "CHUNK"
            text = _clean_chunk_text(ref.text) if ref.source_type == "chunk" else ref.text.strip()
            if len(text) > 300:
                text = text[:297] + "…"
            lines.append(
                f"• [{ref.id or '—'}] [{tag}] (sim={ref.similarity:.2f}) "
                f"§ {ref.section} — p.{ref.page}"
            )
            lines.append(f"  {text}")
    else:
        lines.append("  (none found)")

    lines.append("")
    lines.append("── Same-section references ──")
    if result.same_section:
        for ref in result.same_section:
            tag = "CLAIM" if ref.source_type == "claim" else ref.chunk_type or "CHUNK"
            text = _clean_chunk_text(ref.text) if ref.source_type == "chunk" else ref.text.strip()
            if len(text) > 300:
                text = text[:297] + "…"
            lines.append(
                f"• [{ref.id or '—'}] [{tag}] (sim={ref.similarity:.2f}) "
                f"§ {ref.section} — p.{ref.page}"
            )
            lines.append(f"  {text}")
    else:
        lines.append("  (none found)")

    if result.flags:
        lines.append("")
        lines.append("── Flags ──")
        for flag in result.flags:
            lines.append(f"⚠ {flag}")

    return "\n".join(lines)


# ── Workbook manipulation ────────────────────────────────────────────────────


def insert_v5_column(ws, new_col_idx: int = V5_NEW_COL_IDX) -> None:
    """Insert a new column for v5 refs and re-anchor data validation."""
    old_dvs = list(ws.data_validations.dataValidation)
    ws.data_validations.dataValidation = []

    ws.insert_cols(new_col_idx)

    header = ws.cell(row=1, column=new_col_idx)
    header.value = "Cross-References v5\n(chunk-aware — PILOT)"
    header.fill = HEADER_FILL_GREEN_DARK
    header.font = HEADER_FONT_WHITE
    header.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")

    new_letter = get_column_letter(new_col_idx)
    ws.column_dimensions[new_letter].width = 60.0

    # Re-assert scoring column widths after the shift
    for score_letter in ("K", "L", "M", "N", "O"):
        ws.column_dimensions[score_letter].width = 9.0
    ws.column_dimensions["P"].width = 30.0  # Expert Notes

    # Shift data validation ranges: columns at/after new_col_idx shift right by 1
    for dv in old_dvs:
        new_ranges = []
        for cr in list(dv.sqref.ranges):
            min_col = cr.min_col + (1 if cr.min_col >= new_col_idx else 0)
            max_col = cr.max_col + (1 if cr.max_col >= new_col_idx else 0)
            new_ranges.append(
                f"{get_column_letter(min_col)}{cr.min_row}:{get_column_letter(max_col)}{cr.max_row}"
            )
        new_dv = DataValidation(
            type=dv.type,
            formula1=dv.formula1,
            formula2=dv.formula2,
            operator=dv.operator,
            allow_blank=dv.allow_blank,
            showErrorMessage=dv.showErrorMessage,
            errorTitle=dv.errorTitle,
            error=dv.error,
            showInputMessage=dv.showInputMessage,
            promptTitle=dv.promptTitle,
            prompt=dv.prompt,
        )
        new_dv.sqref = " ".join(new_ranges)
        ws.add_data_validation(new_dv)


def write_v5_content(ws, rendered: dict[tuple, str], new_col_idx: int = V5_NEW_COL_IDX) -> None:
    """Write v5 content into the new column for each row."""
    for row in range(2, ws.max_row + 1):
        claim_id = ws.cell(row=row, column=2).value
        company = ws.cell(row=row, column=3).value
        if not claim_id:
            continue
        text = rendered.get((claim_id, company))
        if text is None:
            # Not in pilot — render a placeholder
            text = (
                "── Pilot batch only ──\n"
                f"ADE chunks for '{company}' have not yet been extracted. "
                f"This row will be populated when the pilot is expanded to all 24 reports."
            )
        cell = ws.cell(row=row, column=new_col_idx)
        cell.value = text
        cell.alignment = CROSS_REF_ALIGNMENT
        cell.border = THIN_BORDER
        n_lines = (text.count("\n") + 1) if text else 1
        est = min(14 * max(n_lines, 6), 340)
        if ws.row_dimensions[row].height is None or ws.row_dimensions[row].height < est:
            ws.row_dimensions[row].height = est


def add_v5_instructions(wb) -> None:
    ws = wb["Instructions"]
    last_row = ws.max_row
    row = last_row + 2
    title = ws.cell(row=row, column=1)
    title.value = "v5 PILOT UPDATE (chunk-aware retrieval)"
    title.font = Font(bold=True, size=12, color="FF145A32")

    rows = [
        "",
        "• Column J — \"Cross-References v5\" adds text chunks extracted directly from the",
        "  PDF via Landing.AI ADE. This includes data tables, CEO-letter narrative, governance",
        "  boxes, and other non-claim material that v3 and v4 couldn't see.",
        "",
        "• This version is a PILOT. Only the three reports below have been extracted so far:",
        "    - True Corporation (TRUE-2024-SR-EN)",
        "    - Bangkok Dusit Medical Services (BDMS-2024-SR-EN)",
        "    - Krungthai Bank (KTB-2024-SR-EN)",
        "  Other companies show a \"Pilot batch only\" placeholder in Column J. They will be",
        "  populated when the pilot expands to the full 24 reports in the sample.",
        "",
        "• Each reference now shows a [CLAIM] or [chunkText]/[chunkTable] tag so you can",
        "  distinguish extracted claims from raw report passages.",
    ]
    for i, line in enumerate(rows, start=1):
        c = ws.cell(row=row + i, column=1)
        c.value = line
        c.alignment = Alignment(wrap_text=True, vertical="top")


# ── Main ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample", type=Path,
        default=OUTPUTS_DIR / "validation" / "expert_validation_sample_v2.json",
    )
    parser.add_argument(
        "--full-dir", type=Path,
        default=OUTPUTS_DIR / "main" / "full",
    )
    parser.add_argument(
        "--chunks-dir", type=Path,
        default=OUTPUTS_DIR / "main" / "chunks",
    )
    parser.add_argument(
        "--template", type=Path,
        default=OUTPUTS_DIR / "validation" / "expert_validation_workbook_v4.xlsx",
    )
    parser.add_argument(
        "--output", type=Path,
        default=OUTPUTS_DIR / "validation" / "expert_validation_workbook_v5_pilot.xlsx",
    )
    parser.add_argument("--min-similarity", type=float, default=DEFAULT_MIN_SIMILARITY)
    parser.add_argument("--cross-section-target", type=int, default=DEFAULT_CROSS_SECTION_TARGET)
    parser.add_argument("--same-section-target", type=int, default=DEFAULT_SAME_SECTION_TARGET)
    args = parser.parse_args()

    print(f"Loading sample: {args.sample}")
    with open(args.sample) as f:
        sample = json.load(f)
    sample_claims = sample["claims"] if isinstance(sample, dict) else sample
    print(f"  {len(sample_claims)} claims in sample")

    # Pre-load pilot report data
    pilot_data: dict[str, dict] = {}
    for company, stem in PILOT_COMPANY_TO_STEM.items():
        full_path = args.full_dir / f"{stem}_full.json"
        chunks_path = args.chunks_dir / f"{stem}_chunks.json"
        if not full_path.exists():
            print(f"  ERROR: missing full JSON for {company}: {full_path}")
            continue
        if not chunks_path.exists():
            print(f"  SKIP (no chunks yet): {company} — run extract_chunks.py first")
            continue
        with open(full_path) as f:
            full = json.load(f)
        chunks = load_chunks_from_chunks_json(chunks_path)
        pilot_data[company] = {
            "claims": full.get("claims", []),
            "sections": full.get("sections", []),
            "chunks": chunks,
            "report_key": f"{stem}_v5",  # separate embedding cache namespace from v4
        }
        print(f"  Loaded {company}: {len(full.get('claims', []))} claims, {len(chunks)} chunks")

    # Run retrieval for each pilot-eligible sample claim
    rendered: dict[tuple, str] = {}
    processed = 0
    for i, sc in enumerate(sample_claims, start=1):
        company = sc.get("company", "")
        claim_id = sc["claim_id"]
        if company not in pilot_data:
            continue
        d = pilot_data[company]

        # Enrich sample claim with section/page if missing (sample JSON lacks these)
        enriched = dict(sc)
        pool_by_id = {c["claim_id"]: c for c in d["claims"]}
        if not enriched.get("section"):
            enriched["section"] = pool_by_id.get(claim_id, {}).get("section", "")
        if "page" not in enriched:
            enriched["page"] = pool_by_id.get(claim_id, {}).get("page", "?")

        result = retrieve_chunk_aware_refs(
            sample_claim=enriched,
            claims_pool=d["claims"],
            chunks_pool=d["chunks"],
            sections=d["sections"],
            report_key=d["report_key"],
            cross_section_target=args.cross_section_target,
            same_section_target=args.same_section_target,
            min_similarity=args.min_similarity,
        )
        rendered[(claim_id, company)] = render_v5_cell(result)
        n_c = len(result.cross_section)
        n_s = len(result.same_section)
        n_chunk_c = sum(1 for r in result.cross_section if r.source_type == "chunk")
        n_chunk_s = sum(1 for r in result.same_section if r.source_type == "chunk")
        flag_suf = f" [{len(result.flags)} flag(s)]" if result.flags else ""
        print(
            f"  [{i:2}/{len(sample_claims)}] {claim_id} ({company[:22]}): "
            f"{n_c} cross ({n_chunk_c} chunks) + {n_s} same ({n_chunk_s} chunks){flag_suf}"
        )
        processed += 1

    print(f"\nProcessed {processed} pilot claims")

    # Copy template → output
    print(f"\nCopying template: {args.template}")
    shutil.copyfile(args.template, args.output)

    print("Injecting v5 column...")
    wb = load_workbook(args.output)
    ws = wb["Scoring"]
    insert_v5_column(ws)
    write_v5_content(ws, rendered)
    add_v5_instructions(wb)

    print(f"Saving: {args.output}")
    wb.save(args.output)
    print("\nDone.")


if __name__ == "__main__":
    main()
