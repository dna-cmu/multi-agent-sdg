"""
Build the FULL v5 workbook — chunk-aware retrieval for all 24 reports
contributing to the 63-claim validation sample.

This is the production build; the pilot version (build_expert_validation_
workbook_v5_pilot.py) covered only TRUE/BDMS/KTB and left the other 49 rows
as "Pilot batch only" placeholders. Now that ADE chunks exist for all 30
corpus reports, every sample claim gets a real chunk-aware evidence pack.

Adds Column J ("Cross-References v5 — chunk-aware") to the v4 workbook.
Scoring columns shift from J-N to K-O (data and validations move with
them). Same 63 claims, same order, same Claim IDs — Expert 1 was given
a paper print-out for scoring and her transcribed scores will line up
row-for-row.

Usage:
    python build_expert_validation_workbook_v5.py
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


# ── ADE markdown cleanup (matches pilot) ────────────────────────────────────

_ANCHOR_RE = re.compile(r"<a id=['\"][^'\"]*['\"]></a>")
_VISUAL_RE = re.compile(r"<::[^:]*::>")
_MULTI_BLANK_RE = re.compile(r"\n\s*\n+")


def _clean_chunk_text(text: str) -> str:
    t = _ANCHOR_RE.sub("", text or "")
    t = _VISUAL_RE.sub("", t)
    t = _MULTI_BLANK_RE.sub("\n", t)
    return t.strip()


def render_v5_cell(result: MixedResult) -> str:
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


# ── Workbook manipulation (same as pilot, but no pilot-placeholder branch) ──


def insert_v5_column(ws, new_col_idx: int = V5_NEW_COL_IDX) -> None:
    old_dvs = list(ws.data_validations.dataValidation)
    ws.data_validations.dataValidation = []

    ws.insert_cols(new_col_idx)

    header = ws.cell(row=1, column=new_col_idx)
    header.value = "Cross-References v5\n(chunk-aware retrieval)"
    header.fill = HEADER_FILL_GREEN_DARK
    header.font = HEADER_FONT_WHITE
    header.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")

    new_letter = get_column_letter(new_col_idx)
    ws.column_dimensions[new_letter].width = 60.0

    for score_letter in ("K", "L", "M", "N", "O"):
        ws.column_dimensions[score_letter].width = 9.0
    ws.column_dimensions["P"].width = 30.0  # Expert Notes

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
    missing: list[tuple[int, str]] = []
    for row in range(2, ws.max_row + 1):
        claim_id = ws.cell(row=row, column=2).value
        company = ws.cell(row=row, column=3).value
        if not claim_id:
            continue
        text = rendered.get((claim_id, company))
        if text is None:
            missing.append((row, str(claim_id)))
            text = (
                "── ERROR ──\n"
                f"No retrieval result was generated for this row "
                f"(claim_id={claim_id!r}, company={company!r}). "
                f"This indicates the source report's chunks file is missing."
            )
        cell = ws.cell(row=row, column=new_col_idx)
        cell.value = text
        cell.alignment = CROSS_REF_ALIGNMENT
        cell.border = THIN_BORDER
        n_lines = (text.count("\n") + 1) if text else 1
        est = min(14 * max(n_lines, 6), 340)
        if ws.row_dimensions[row].height is None or ws.row_dimensions[row].height < est:
            ws.row_dimensions[row].height = est
    if missing:
        print(f"  WARNING: {len(missing)} row(s) had no retrieval result: {missing}")


def add_v5_instructions(wb) -> None:
    ws = wb["Instructions"]
    last_row = ws.max_row
    row = last_row + 2
    title = ws.cell(row=row, column=1)
    title.value = "v5 UPDATE (chunk-aware retrieval)"
    title.font = Font(bold=True, size=12, color="FF145A32")

    rows = [
        "",
        "• Column J — \"Cross-References v5\" is the new chunk-aware evidence pack.",
        "  It pools both extracted claims AND raw text chunks (data tables, narrative",
        "  prose, governance boxes, executive summaries) from the same report, ranked",
        "  by semantic similarity to the claim with explicit section diversity.",
        "",
        "• Same retrieval policy as v4: target up to 3 from different sections of the",
        "  report + up to 2 from the same section, with a 0.35 cosine similarity floor",
        "  and NO padding when the floor cannot be met (the absence is flagged).",
        "",
        "• Each reference now shows a [CLAIM] or [chunkText]/[chunkTable]/[figure] tag",
        "  so you can see whether the corroborating material came from another extracted",
        "  claim or from raw report content (tables, figures, narrative prose).",
        "",
        "• Use Column J as your primary evidence pack; Columns H and I (v3 and v4)",
        "  are kept for reference and comparison if useful.",
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
    parser.add_argument("--full-dir", type=Path, default=OUTPUTS_DIR / "main" / "full")
    parser.add_argument("--chunks-dir", type=Path, default=OUTPUTS_DIR / "main" / "chunks")
    parser.add_argument(
        "--template", type=Path,
        default=OUTPUTS_DIR / "validation" / "expert_validation_workbook_v4.xlsx",
    )
    parser.add_argument(
        "--output", type=Path,
        default=OUTPUTS_DIR / "validation" / "expert_validation_workbook_v5.xlsx",
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

    # Index ALL reports' data (not just pilot) keyed by company name
    print(f"\nLoading per-report data from {args.full_dir} and {args.chunks_dir}")
    by_company: dict[str, dict] = {}
    for full_path in sorted(args.full_dir.glob("*_full.json")):
        with open(full_path) as f:
            full = json.load(f)
        meta = full.get("metadata", {}) or {}
        company = meta.get("company")
        if not company:
            continue
        stem = full_path.stem.replace("_full", "")
        chunks_path = args.chunks_dir / f"{stem}_chunks.json"
        if not chunks_path.exists():
            print(f"  SKIP (no chunks file): {company} ({stem})")
            continue
        chunks = load_chunks_from_chunks_json(chunks_path)
        by_company[company] = {
            "claims": full.get("claims", []),
            "sections": full.get("sections", []),
            "chunks": chunks,
            "report_key": f"{stem}_v5full",
        }
        print(f"  {company}: {len(full.get('claims', []))} claims, {len(chunks)} chunks")

    # Run retrieval for every sample claim
    rendered: dict[tuple, str] = {}
    n_processed = 0
    n_missing = 0
    for i, sc in enumerate(sample_claims, start=1):
        company = sc.get("company", "")
        claim_id = sc["claim_id"]
        if company not in by_company:
            print(f"  [{i:2}/{len(sample_claims)}] {claim_id} ({company}): MISSING report data")
            n_missing += 1
            continue
        d = by_company[company]

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
            f"  [{i:2}/{len(sample_claims)}] {claim_id} ({company[:24]}): "
            f"{n_c} cross ({n_chunk_c} chunks) + {n_s} same ({n_chunk_s} chunks){flag_suf}"
        )
        n_processed += 1

    print(f"\nProcessed {n_processed}/{len(sample_claims)} claims (missing report data: {n_missing})")

    # Copy template → output, then edit
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
