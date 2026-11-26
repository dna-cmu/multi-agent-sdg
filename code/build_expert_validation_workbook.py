"""
Build expert validation workbook v4.

Takes the v3 workbook as a visual template and adds a new column I
("Cross-References v4 — section-diverse retrieval") alongside the
existing column H (preserved as "Cross-References v3 — same-section
retrieval"). The scoring columns S/M/T/E/C are shifted one column to
the right to accommodate the insert.

This script addresses Expert 1's feedback that the v3 cross-references
were dominated by same-section hits, making the Consistency dimension
effectively impossible to score — see utils/retrieval.py for the
methodological fix (embedding-based retrieval with explicit section-
diversity targets, and NO padding below a relevance floor).

Usage:
    python build_expert_validation_workbook.py \
        --sample data/outputs/validation/expert_validation_sample_v2.json \
        --pipeline-dir data/outputs/main/full \
        --template data/outputs/validation/expert_validation_workbook_v3.xlsx \
        --output data/outputs/validation/expert_validation_workbook_v4.xlsx
"""

from __future__ import annotations

import argparse
import json
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
    RetrievalResult,
    retrieve_section_diverse_refs,
)


# Column indices in the v3 workbook (1-indexed)
V3_COL_CROSS_REFS = 8  # H
V3_COL_FIRST_SCORE = 9  # I (S) — everything from here shifts right by 1 in v4

# Header styling (matched to v3 workbook inspection)
HEADER_FILL_DARK = PatternFill(start_color="FF2C3E50", end_color="FF2C3E50", fill_type="solid")
HEADER_FILL_BLUE = PatternFill(start_color="FF2F5496", end_color="FF2F5496", fill_type="solid")
HEADER_FILL_GREEN = PatternFill(start_color="FF1F7A3D", end_color="FF1F7A3D", fill_type="solid")
HEADER_FONT_WHITE = Font(color="FFFFFFFF", bold=True)

# Body styling for cross-ref columns (matches v3 treatment)
CROSS_REF_ALIGNMENT = Alignment(wrap_text=True, vertical="top", horizontal="left")
THIN_BORDER = Border(
    left=Side(style="thin", color="FFCCCCCC"),
    right=Side(style="thin", color="FFCCCCCC"),
    top=Side(style="thin", color="FFCCCCCC"),
    bottom=Side(style="thin", color="FFCCCCCC"),
)


# ── Rendering ────────────────────────────────────────────────────────────────


def render_cross_ref_cell(result: RetrievalResult) -> str:
    """Turn a RetrievalResult into the multi-line text we show in Column I."""
    lines: list[str] = []

    lines.append("── Cross-section references (different section) ──")
    if result.cross_section:
        for ref in result.cross_section:
            # Truncate long claim text to keep the cell readable
            text = ref.claim_text.strip()
            if len(text) > 220:
                text = text[:217] + "…"
            lines.append(
                f"• [{ref.claim_id}] (sim={ref.similarity:.2f}) "
                f"§ {ref.section} — p.{ref.page}"
            )
            lines.append(f"  {text}")
    else:
        lines.append("  (none found)")

    lines.append("")
    lines.append("── Same-section references ──")
    if result.same_section:
        for ref in result.same_section:
            text = ref.claim_text.strip()
            if len(text) > 220:
                text = text[:217] + "…"
            lines.append(
                f"• [{ref.claim_id}] (sim={ref.similarity:.2f}) "
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


# ── Pipeline JSON lookup ─────────────────────────────────────────────────────


def build_report_index(pipeline_dir: Path) -> dict[str, dict]:
    """
    Build a lookup keyed by the claim source_file → the loaded JSON payload.

    The sample JSON uses `company` (e.g. "Charoen Pokphand Foods") and the
    pipeline files are named by ticker (e.g. CPF-2024-SR-EN_full.json) —
    so we can't key by company alone. We build the index by reading each
    file's metadata and keying by the `filename` it records (which is the
    PDF name, matching the sample's `source_file` if present — and if the
    sample doesn't carry source_file, we fall back to company).
    """
    by_filename: dict[str, dict] = {}
    by_company: dict[str, dict] = {}
    for path in sorted(pipeline_dir.glob("*_full.json")):
        with open(path) as f:
            data = json.load(f)
        meta = data.get("metadata", {})
        fname = meta.get("filename") or path.name
        by_filename[fname] = data
        if meta.get("company"):
            by_company[meta["company"]] = data
    return {"by_filename": by_filename, "by_company": by_company}


def find_report_for_sample_claim(sample_claim: dict, index: dict) -> tuple[dict | None, str]:
    """
    Resolve the full pipeline JSON for a given sample claim.
    Returns (data, report_key) or (None, "") if no match.

    Sample claims don't always carry source_file, so we try company as fallback.
    """
    # Try source_file first if present
    src = sample_claim.get("source_file")
    if src and src in index["by_filename"]:
        return index["by_filename"][src], src

    # Fallback: match by company
    company = sample_claim.get("company")
    if company and company in index["by_company"]:
        data = index["by_company"][company]
        return data, data.get("metadata", {}).get("filename", company)

    return None, ""


# ── Workbook manipulation ────────────────────────────────────────────────────


def copy_cell_style(src_cell, dst_cell) -> None:
    """Copy all style attributes from src_cell to dst_cell."""
    if src_cell.has_style:
        dst_cell.font = copy(src_cell.font)
        dst_cell.fill = copy(src_cell.fill)
        dst_cell.border = copy(src_cell.border)
        dst_cell.alignment = copy(src_cell.alignment)
        dst_cell.number_format = src_cell.number_format
        dst_cell.protection = copy(src_cell.protection)


def insert_cross_ref_v4_column(ws, new_col_idx: int = 9) -> None:
    """
    Insert a new column at `new_col_idx` in the Scoring sheet, shifting the
    score columns (I-N) right to J-O. Preserve/restore data validation that
    was anchored to the old I:M range.
    """
    # Preserve the old data validation rule so we can re-anchor it after insert.
    old_dvs = list(ws.data_validations.dataValidation)
    # Drop them from the sheet; we'll replace with a shifted copy.
    ws.data_validations.dataValidation = []

    # Insert the new column. openpyxl shifts data + basic styling.
    ws.insert_cols(new_col_idx)

    # Header for the new column — mirror old H styling but with a green fill
    # so the expert can see at a glance that this is the v4 column.
    header = ws.cell(row=1, column=new_col_idx)
    header.value = "Cross-References v4\n(section-diverse retrieval — NEW)"
    header.fill = HEADER_FILL_GREEN
    header.font = HEADER_FONT_WHITE
    header.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")

    # Rename old H header so its intent is unmistakable
    old_h = ws.cell(row=1, column=V3_COL_CROSS_REFS)
    old_h.value = "Cross-References v3\n(same-section retrieval — FOR COMPARISON)"
    old_h.fill = HEADER_FILL_BLUE
    old_h.font = HEADER_FONT_WHITE
    old_h.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")

    # Match column width to old H (60) so the new column is readable
    new_letter = get_column_letter(new_col_idx)
    ws.column_dimensions[new_letter].width = 60.0

    # openpyxl doesn't shift column_dimensions when we insert_cols — the width
    # settings are keyed by letter, so whatever was at column M stays at M even
    # though the data in M is now a different dimension. Re-assert widths for
    # the shifted score columns (narrow, 0-3) and the Expert Notes column (wide).
    for score_col_letter in ("J", "K", "L", "M", "N"):
        ws.column_dimensions[score_col_letter].width = 9.0
    ws.column_dimensions["O"].width = 30.0  # Expert Notes

    # Re-install data validation, shifted right by one column
    for dv in old_dvs:
        new_ranges = []
        for cell_range in list(dv.sqref.ranges):
            # Every range that started at col I (9) onward needs shifting
            min_col = cell_range.min_col
            max_col = cell_range.max_col
            min_row = cell_range.min_row
            max_row = cell_range.max_row
            if min_col >= new_col_idx:
                min_col += 1
            if max_col >= new_col_idx:
                max_col += 1
            new_ranges.append(
                f"{get_column_letter(min_col)}{min_row}:"
                f"{get_column_letter(max_col)}{max_row}"
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


def write_v4_cross_refs(
    ws,
    rendered_by_key: dict[tuple, str],
    new_col_idx: int = 9,
) -> None:
    """
    Write the rendered v4 cross-ref text into the new column for each row.

    We key by (claim_id, company) because claim_ids are NOT globally unique —
    they are issued per-report. Seven IDs in v2 (e.g. CLM-0013, CLM-0014)
    recur across different companies and would collide under a claim_id-only key.
    """
    for row in range(2, ws.max_row + 1):
        claim_id = ws.cell(row=row, column=2).value  # Column B = Claim ID
        company = ws.cell(row=row, column=3).value   # Column C = Company
        if not claim_id:
            continue
        text = rendered_by_key.get((claim_id, company), "")
        cell = ws.cell(row=row, column=new_col_idx)
        cell.value = text
        cell.alignment = CROSS_REF_ALIGNMENT
        cell.border = THIN_BORDER
        # Give the row enough height for the multi-line content. We use a
        # conservative estimate: ~14pt per line, capped.
        n_lines = (text.count("\n") + 1) if text else 1
        est_height = min(14 * max(n_lines, 6), 340)
        if ws.row_dimensions[row].height is None or ws.row_dimensions[row].height < est_height:
            ws.row_dimensions[row].height = est_height


def add_instructions_note(wb) -> None:
    """Add a brief note on the Instructions sheet explaining what v4 changed."""
    ws = wb["Instructions"]
    last_row = ws.max_row
    note_row = last_row + 2
    note_cell = ws.cell(row=note_row, column=1)
    note_cell.value = "v4 UPDATE (cross-references)"
    note_cell.font = Font(bold=True, size=12, color="FF1F7A3D")

    note_rows = [
        "",
        "• Column H — \"Cross-References v3\" is unchanged from the version you saw previously.",
        "  It contains same-section references from the original retrieval method.",
        "",
        "• Column I — \"Cross-References v4\" is new. It surfaces references selected to be",
        "  section-diverse: we target up to 3 from different sections of the report, plus up",
        "  to 2 from the same section as the claim. Similarity is measured by sentence",
        f"  embeddings (OpenAI text-embedding-3-small), with a relevance floor of",
        f"  {DEFAULT_MIN_SIMILARITY:.2f} cosine similarity — references below that floor are",
        "  NOT shown, even if that leaves the target count unfilled.",
        "",
        "• Where the floor cannot be met, the cell shows an explicit ⚠ flag explaining",
        "  the absence (e.g. \"no cross-section references above threshold — topic appears",
        "  only in this section of the report\"). That absence is itself information for",
        "  the Consistency dimension.",
        "",
        "• You can compare the two columns side-by-side. Please score using Column I as",
        "  your primary evidence pack; treat Column H as a reference to contrast against.",
    ]
    for i, line in enumerate(note_rows, start=1):
        c = ws.cell(row=note_row + i, column=1)
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
        "--pipeline-dir", type=Path,
        default=OUTPUTS_DIR / "main" / "full",
    )
    parser.add_argument(
        "--template", type=Path,
        default=OUTPUTS_DIR / "validation" / "expert_validation_workbook_v3.xlsx",
    )
    parser.add_argument(
        "--output", type=Path,
        default=OUTPUTS_DIR / "validation" / "expert_validation_workbook_v4.xlsx",
    )
    parser.add_argument(
        "--min-similarity", type=float,
        default=DEFAULT_MIN_SIMILARITY,
        help=f"Relevance floor for cosine similarity (default {DEFAULT_MIN_SIMILARITY})",
    )
    parser.add_argument(
        "--cross-section-target", type=int,
        default=DEFAULT_CROSS_SECTION_TARGET,
    )
    parser.add_argument(
        "--same-section-target", type=int,
        default=DEFAULT_SAME_SECTION_TARGET,
    )
    args = parser.parse_args()

    print(f"Loading sample: {args.sample}")
    with open(args.sample) as f:
        sample = json.load(f)
    sample_claims = sample["claims"] if isinstance(sample, dict) else sample
    print(f"  {len(sample_claims)} claims in sample")

    print(f"Indexing pipeline outputs in: {args.pipeline_dir}")
    index = build_report_index(args.pipeline_dir)
    print(f"  {len(index['by_filename'])} reports indexed")

    # Run retrieval for each sample claim.
    # Key the rendered text by (claim_id, company) because claim_ids are not
    # globally unique — they recur across reports (e.g. CLM-0013 exists in both
    # Minor International and BDMS reports), so keying by claim_id alone would
    # overwrite duplicates.
    rendered: dict[tuple, str] = {}
    missing_reports: list[str] = []

    for i, sc in enumerate(sample_claims, start=1):
        claim_id = sc["claim_id"]
        company = sc.get("company", "")
        key = (claim_id, company)
        report_data, report_key = find_report_for_sample_claim(sc, index)
        if report_data is None:
            print(f"  [{i:2}/{len(sample_claims)}] {claim_id} ({company}): no pipeline JSON found")
            missing_reports.append(claim_id)
            rendered[key] = (
                "── ERROR ──\n"
                f"Could not locate the source report for this claim "
                f"(company={company!r}). No cross-references were generated."
            )
            continue

        # Augment sample claim with section/page if missing — the sample doesn't
        # carry these but the pipeline JSON does. Look up by claim_id in the pool.
        pool = report_data.get("claims", [])
        pool_by_id = {c["claim_id"]: c for c in pool}
        enriched = dict(sc)
        if "section" not in enriched or not enriched["section"]:
            enriched["section"] = pool_by_id.get(claim_id, {}).get("section", "")
        if "page" not in enriched:
            enriched["page"] = pool_by_id.get(claim_id, {}).get("page", "?")

        result = retrieve_section_diverse_refs(
            enriched,
            pool,
            report_key=report_key,
            cross_section_target=args.cross_section_target,
            same_section_target=args.same_section_target,
            min_similarity=args.min_similarity,
        )
        rendered[key] = render_cross_ref_cell(result)
        n_cross = len(result.cross_section)
        n_same = len(result.same_section)
        flag_suffix = f" [{len(result.flags)} flag(s)]" if result.flags else ""
        print(f"  [{i:2}/{len(sample_claims)}] {claim_id} ({company[:24]}): {n_cross} cross + {n_same} same{flag_suffix}")

    # Copy template → output, then edit
    print(f"\nCopying template: {args.template}")
    shutil.copyfile(args.template, args.output)

    print("Loading output workbook to inject v4 column...")
    wb = load_workbook(args.output)
    ws = wb["Scoring"]

    insert_cross_ref_v4_column(ws, new_col_idx=V3_COL_FIRST_SCORE)
    write_v4_cross_refs(ws, rendered, new_col_idx=V3_COL_FIRST_SCORE)
    add_instructions_note(wb)

    print(f"Saving: {args.output}")
    wb.save(args.output)

    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"  Sample claims: {len(sample_claims)}")
    print(f"  Claims with cross-refs generated: {len(sample_claims) - len(missing_reports)}")
    if missing_reports:
        print(f"  Claims missing pipeline data: {len(missing_reports)} — {missing_reports}")
    print(f"  Output workbook: {args.output}")


if __name__ == "__main__":
    main()
