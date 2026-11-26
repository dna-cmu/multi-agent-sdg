"""
split_extract_merge.py — process oversized PDFs that ADE can't handle whole.

WHA-2024-SR-EN.pdf (364 pages, 128 MB) failed ADE submission twice with
"Document may be too large or memory-intensive to process". This script:

  1. Splits the source PDF into N roughly-equal halves with pymupdf,
     written to data/reports/2024/_split/.
  2. Submits each half to ADE through the existing extract_chunks pipeline
     (using the parse_jobs API + job-id registry, so each half is
     independently retryable).
  3. Stitches the per-half chunks JSONs into a single
     <stem>_chunks.json with page numbers reconciled to the original PDF.

The merged file plugs straight into the v5 retrieval — downstream code
sees one report with consistent pagination, not two halves.

Usage:
    python split_extract_merge.py --pdf WHA-2024-SR-EN.pdf
    python split_extract_merge.py --pdf <other>.pdf --n-parts 3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pymupdf
from landingai_ade import LandingAIADE

from config.settings import LANDINGAI_API_KEY, REPORTS_DIR
from extract_chunks import (
    CHUNKS_DIR,
    JOBS_REGISTRY_DIR,
    RAW_DIR,
    simplify_chunks,
    submit_and_wait,
)


def split_pdf(src: Path, parts_dir: Path, n_parts: int = 2) -> list[tuple[Path, int]]:
    """
    Split src into n_parts roughly-equal pieces. Returns a list of
    (output_path, page_count) tuples in original-document order.
    """
    parts_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(src)
    total = doc.page_count
    base = total // n_parts
    rem = total % n_parts

    out: list[tuple[Path, int]] = []
    cursor = 0
    for i in range(n_parts):
        size = base + (1 if i < rem else 0)
        if size == 0:
            continue
        start = cursor
        end = cursor + size - 1  # inclusive
        cursor = end + 1

        part_path = parts_dir / f"{src.stem}-part{i+1}.pdf"
        part_doc = pymupdf.open()
        part_doc.insert_pdf(doc, from_page=start, to_page=end)
        part_doc.save(str(part_path))
        part_doc.close()
        out.append((part_path, size))
        print(f"  Wrote {part_path.name}: original pages {start+1}-{end+1} ({size} pages)")

    doc.close()
    return out


def merge_chunks(part_files: list[Path], page_offsets: list[int],
                 source_name: str, out_path: Path) -> dict:
    """
    Merge per-part chunks JSONs into a single chunks file. Each chunk's
    page number gets shifted by its part's offset so the merged file's
    page numbers match the original PDF's pagination.
    """
    merged = {
        "source_file": source_name,
        "n_chunks_raw": 0,
        "n_chunks_kept": 0,
        "dropped_types": {},
        "job_ids": [],
        "merged_from": [str(p) for p in part_files],
        "merged_offsets": page_offsets,
        "chunks": [],
    }
    for part_path, offset in zip(part_files, page_offsets):
        with open(part_path) as f:
            d = json.load(f)
        merged["n_chunks_raw"] += d.get("n_chunks_raw", 0)
        merged["n_chunks_kept"] += d.get("n_chunks_kept", 0)
        for k, v in d.get("dropped_types", {}).items():
            merged["dropped_types"][k] = merged["dropped_types"].get(k, 0) + v
        if d.get("job_id"):
            merged["job_ids"].append(d["job_id"])
        for ch in d.get("chunks", []):
            ch_copy = dict(ch)
            page = ch_copy.get("page")
            if isinstance(page, int):
                ch_copy["page"] = page + offset
            merged["chunks"].append(ch_copy)
    with open(out_path, "w") as f:
        json.dump(merged, f, indent=2)
    return merged


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, help="PDF filename (located in --reports-dir).")
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR / "2024")
    parser.add_argument("--n-parts", type=int, default=2)
    args = parser.parse_args()

    if not LANDINGAI_API_KEY:
        sys.exit("LANDINGAI_API_KEY not set in .env")

    src = args.reports_dir / args.pdf
    if not src.exists():
        sys.exit(f"NOT FOUND: {src}")

    parts_dir = args.reports_dir / "_split"
    print(f"Splitting {src.name} into {args.n_parts} parts → {parts_dir}/")
    parts = split_pdf(src, parts_dir, args.n_parts)
    if len(parts) < args.n_parts:
        sys.exit("Split produced fewer parts than requested; aborting.")

    # Compute offsets: part 1 keeps its native pages; part 2's pages are
    # shifted by part 1's page count; etc.
    offsets = [0]
    for _, size in parts[:-1]:
        offsets.append(offsets[-1] + size)
    print(f"Page offsets per part: {offsets}")

    # Submit each part
    client = LandingAIADE(apikey=LANDINGAI_API_KEY)
    part_chunks_paths: list[Path] = []
    failures: list[str] = []
    for part_path, _size in parts:
        stem = part_path.stem
        chunk_out = CHUNKS_DIR / f"{stem}_chunks.json"
        raw_out = RAW_DIR / f"{stem}_parse.json"
        if chunk_out.exists():
            print(f"SKIP (exists): {chunk_out.name}")
            part_chunks_paths.append(chunk_out)
            continue
        try:
            raw = submit_and_wait(client, part_path)
        except Exception as e:
            print(f"FAIL on {part_path.name}: {type(e).__name__}: {e}")
            failures.append(stem)
            continue
        with open(raw_out, "w") as f:
            json.dump(raw, f, indent=2)
        simple = simplify_chunks(raw, pdf_name=part_path.name)
        with open(chunk_out, "w") as f:
            json.dump(simple, f, indent=2)
        print(f"OK {stem}: kept {simple['n_chunks_kept']}/{simple['n_chunks_raw']} chunks")
        part_chunks_paths.append(chunk_out)

    if not part_chunks_paths:
        sys.exit("No part successfully extracted; aborting merge.")

    if failures:
        print(f"\n⚠ Some parts failed ({failures}). Merge will proceed with the parts we have.")

    # Filter offsets to match successful parts (preserves correctness if
    # earlier parts succeeded but later ones failed)
    successful_offsets = []
    for (part_path, _size), off in zip(parts, offsets):
        if (CHUNKS_DIR / f"{part_path.stem}_chunks.json") in part_chunks_paths:
            successful_offsets.append(off)

    # Merge into the canonical filename matching the original PDF stem
    merged_out = CHUNKS_DIR / f"{src.stem}_chunks.json"
    print(f"\nMerging {len(part_chunks_paths)} part(s) → {merged_out}")
    merged = merge_chunks(part_chunks_paths, successful_offsets, src.name, merged_out)
    print(
        f"\nDone. Merged: {merged['n_chunks_kept']} chunks kept, "
        f"{merged['n_chunks_raw']} raw, dropped {merged['dropped_types']}."
    )
    print(f"Output: {merged_out}")
    print(f"Job IDs (per part): {merged['job_ids']}")


if __name__ == "__main__":
    main()
