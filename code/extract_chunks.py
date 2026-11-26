"""
extract_chunks.py — pull per-page chunk data from PDFs via Landing.AI ADE.

Does NOT re-extract claims (those already exist in data/outputs/main/full/)
and does NOT call an LLM. This is the ADE extraction step only, run on its
own to persist the chunk pool that the original pipeline discarded.

Uses the modern landingai-ade Parse Jobs (async) API because:
  - It handles large files (>1MB) reliably.
  - Jobs are retrievable later via parse_jobs.list() — this is the
    permanent-recovery feature the original sync pipeline didn't use.

Outputs (per input PDF):
  - data/outputs/main/chunks/raw/<stem>_parse.json — full ADE response
  - data/outputs/main/chunks/<stem>_chunks.json — simplified list of
    {id, page, type, text} objects used by retrieval.

Usage:
    python extract_chunks.py --pdfs TRUE-2024-SR-EN.pdf BDMS-2024-SR-EN.pdf KTB-2024-SR-EN.pdf
    python extract_chunks.py --reports-dir data/reports/2024 --pattern "TRUE-*.pdf"
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

from landingai_ade import LandingAIADE

from config.settings import OUTPUTS_DIR, REPORTS_DIR, LANDINGAI_API_KEY

CHUNKS_DIR = OUTPUTS_DIR / "main" / "chunks"
RAW_DIR = CHUNKS_DIR / "raw"
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Persist the job_id once we submit it, so if the process crashes or hits
# a bug mid-run we can recover by polling the existing job instead of
# paying to resubmit. One sidecar file per report.
JOBS_REGISTRY_DIR = CHUNKS_DIR / "jobs"
JOBS_REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

# Types of ADE chunks to keep for the retrieval pool. Landing.AI's live API
# returns unprefixed type names (text, table, marginalia, figure, logo,
# attestation) — the pydantic schema advertises prefixed names but the JSON
# payload doesn't use them. We drop only obvious noise (logos / page numbers).
# We keep `marginalia` because it often holds section headings and callouts.
KEEP_CHUNK_TYPES = {
    "text",
    "table",
    "figure",
    "marginalia",
    "attestation",
    "title",
    "key_value",
    "form",
    # Also tolerate prefixed variants in case the API shape changes
    "chunkText", "chunkTable", "chunkFigure", "chunkMarginalia",
    "chunkAttestation", "chunkTitle", "chunkKeyValue", "chunkForm",
}

# Polling parameters for parse_jobs
POLL_INTERVAL_SECONDS = 5
POLL_MAX_MINUTES = 30


def _download_output(output_url: str, max_attempts: int = 3) -> dict:
    """
    Landing.AI returns a presigned S3 URL for files >1MB. Fetch and parse.
    The URL is valid for ~1 hour from completion. Retries transient socket
    timeouts because larger response bodies have hit the read deadline before.
    """
    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"  downloading output from signed S3 URL (attempt {attempt})...")
            with urllib.request.urlopen(output_url, timeout=600) as resp:
                raw = resp.read()
            return json.loads(raw)
        except (TimeoutError, urllib.error.URLError, ConnectionError) as e:
            last_err = e
            print(f"    attempt {attempt} failed: {type(e).__name__}: {e}")
            if attempt < max_attempts:
                time.sleep(5 * attempt)
    raise RuntimeError(f"Download failed after {max_attempts} attempts: {last_err}")


def _finalise_completed_job(status_resp) -> dict[str, Any]:
    """Assemble our saved-response dict from a completed job status."""
    data_field = None
    if status_resp.data is not None:
        data_field = status_resp.data.model_dump()
    elif getattr(status_resp, "output_url", None):
        data_field = _download_output(status_resp.output_url)

    if data_field is None:
        raise RuntimeError(
            f"Job {status_resp.job_id} completed but both data and output_url are missing."
        )

    return {
        "job_id": status_resp.job_id,
        "status": status_resp.status,
        "received_at": status_resp.received_at,
        "metadata": status_resp.metadata.model_dump() if status_resp.metadata else None,
        "data": data_field,
        "version": status_resp.version,
    }


def _wait_for_job(client: LandingAIADE, job_id: str) -> dict[str, Any]:
    """Poll `parse_jobs.get(job_id)` until completed, failed, or timeout."""
    deadline = time.time() + POLL_MAX_MINUTES * 60
    last_status = None
    while time.time() < deadline:
        status_resp = client.parse_jobs.get(job_id)
        if status_resp.status != last_status:
            print(f"  status: {status_resp.status} (progress {status_resp.progress:.2f})")
            last_status = status_resp.status

        if status_resp.status == "completed":
            return _finalise_completed_job(status_resp)

        if status_resp.status == "failed":
            raise RuntimeError(f"Job {job_id} failed: {status_resp.failure_reason}")

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Job {job_id} didn't complete within {POLL_MAX_MINUTES} minutes.")


def _registry_file(stem: str) -> Path:
    return JOBS_REGISTRY_DIR / f"{stem}.job"


def submit_and_wait(client: LandingAIADE, pdf_path: Path, split: str = "page") -> dict[str, Any]:
    """
    Submit one PDF to ADE parse_jobs (or resume an existing submission),
    poll until complete, return the parsed response dict.

    If a previous run already submitted this PDF and saved a job_id to the
    jobs registry, we reuse that job_id rather than re-paying for a new job.
    """
    stem = pdf_path.stem
    reg = _registry_file(stem)

    if reg.exists():
        job_id = reg.read_text().strip()
        print(f"  Resuming existing job for {pdf_path.name}: {job_id}")
    else:
        print(f"  Submitting {pdf_path.name} ({pdf_path.stat().st_size / 1e6:.1f} MB)...")
        with open(pdf_path, "rb") as f:
            job = client.parse_jobs.create(document=f, split=split)
        job_id = job.job_id
        reg.write_text(job_id)
        print(f"  job_id: {job_id}")

    return _wait_for_job(client, job_id)


def simplify_chunks(raw_response: dict[str, Any], pdf_name: str) -> dict[str, Any]:
    """
    Reduce the full ADE response to a compact per-chunk list we'll use for
    retrieval: {id, page, type, text}. Drops noise chunk types.
    """
    data = raw_response.get("data", {})
    # DataParseResponse (non-spreadsheet) uses `chunks` field
    raw_chunks = data.get("chunks") or []

    kept: list[dict] = []
    dropped_counts: dict[str, int] = {}
    for c in raw_chunks:
        ctype = c.get("type", "")
        if ctype not in KEEP_CHUNK_TYPES:
            dropped_counts[ctype] = dropped_counts.get(ctype, 0) + 1
            continue
        page = None
        if isinstance(c.get("grounding"), dict):
            page = c["grounding"].get("page")
        text = c.get("markdown") or ""
        if not text.strip():
            continue
        kept.append({
            "chunk_id": c.get("id", ""),
            "page": page,
            "type": ctype,
            "text": text.strip(),
        })

    return {
        "source_file": pdf_name,
        "n_chunks_raw": len(raw_chunks),
        "n_chunks_kept": len(kept),
        "dropped_types": dropped_counts,
        "job_id": raw_response.get("job_id"),
        "chunks": kept,
    }


def run_one(client: LandingAIADE, pdf_path: Path, force: bool = False) -> None:
    """Extract one PDF and write both raw and simplified outputs."""
    stem = pdf_path.stem
    raw_out = RAW_DIR / f"{stem}_parse.json"
    simple_out = CHUNKS_DIR / f"{stem}_chunks.json"

    if simple_out.exists() and not force:
        print(f"SKIP (exists): {simple_out.name}")
        return

    # If a raw response already exists on disk (e.g. a previous run saved it
    # but the type-filter was wrong), re-simplify from the local file instead
    # of paying to re-extract.
    if raw_out.exists() and not force:
        print(f"Re-simplifying from existing raw: {raw_out.name}")
        with open(raw_out) as f:
            raw = json.load(f)
    else:
        try:
            raw = submit_and_wait(client, pdf_path)
        except Exception as e:
            print(f"FAIL {stem}: {type(e).__name__}: {e}")
            return
        # Write raw response (for future mining, provenance, debugging)
        with open(raw_out, "w") as f:
            json.dump(raw, f, indent=2)

    simple = simplify_chunks(raw, pdf_name=pdf_path.name)
    with open(simple_out, "w") as f:
        json.dump(simple, f, indent=2)

    print(
        f"OK {stem}: kept {simple['n_chunks_kept']} / {simple['n_chunks_raw']} chunks. "
        f"Dropped: {simple['dropped_types']}"
    )


def _count_pages(pdf_path: Path) -> int:
    """Page count for cost estimation. Uses pymupdf if available; else 0."""
    try:
        import pymupdf
        doc = pymupdf.open(pdf_path)
        n = doc.page_count
        doc.close()
        return n
    except Exception:
        return 0


def _print_cost_preview(pdfs: list[Path]) -> int:
    """Print a table of PDFs with page counts and estimated cost. Returns total pages."""
    RATE_PER_PAGE_USD = 0.05
    print(f"\n{'Report':<30} {'Pages':>7} {'MB':>7}  Status")
    print("-" * 65)
    total_pages = 0
    will_submit = 0
    will_skip = 0
    for pdf in pdfs:
        pages = _count_pages(pdf)
        mb = pdf.stat().st_size / 1e6
        simple_out = CHUNKS_DIR / f"{pdf.stem}_chunks.json"
        registry = JOBS_REGISTRY_DIR / f"{pdf.stem}.job"
        if simple_out.exists():
            status = "SKIP (done)"
            will_skip += 1
        elif registry.exists():
            status = "RESUME (job submitted)"
            total_pages += pages
            # resuming doesn't re-bill; note it
        else:
            status = "NEW submission"
            total_pages += pages
            will_submit += 1
        print(f"{pdf.name:<30} {pages:>7} {mb:>6.1f}  {status}")
    print("-" * 65)
    est_usd = total_pages * RATE_PER_PAGE_USD
    est_credits = total_pages * 3
    print(
        f"NEW submissions: {will_submit} | RESUME existing: {len(pdfs) - will_submit - will_skip} "
        f"| SKIP: {will_skip}"
    )
    print(f"Billable page total (excludes RESUME and SKIP): {total_pages}")
    print(
        f"Estimated cost @ $0.05/page: ${est_usd:,.2f} "
        f"(~{est_credits:,} Landing.AI credits)"
    )
    return total_pages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdfs", nargs="*", default=[], help="Specific PDF filenames (located in --reports-dir).")
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR / "2024")
    parser.add_argument("--pattern", default=None, help="Glob pattern within --reports-dir (overrides --pdfs).")
    parser.add_argument("--force", action="store_true", help="Re-extract even if chunks file exists.")
    parser.add_argument("--yes", action="store_true", help="Skip the cost confirmation prompt.")
    parser.add_argument("--dry-run", action="store_true", help="Print cost preview and exit without submitting.")
    args = parser.parse_args()

    if not LANDINGAI_API_KEY:
        raise SystemExit("LANDINGAI_API_KEY not set in .env")

    # Resolve list of PDFs to extract
    pdfs: list[Path] = []
    if args.pattern:
        pdfs = sorted(args.reports_dir.glob(args.pattern))
    elif args.pdfs:
        for name in args.pdfs:
            p = args.reports_dir / name
            if not p.exists():
                print(f"NOT FOUND: {p}")
                continue
            pdfs.append(p)
    else:
        raise SystemExit("Provide --pdfs or --pattern")

    if not pdfs:
        raise SystemExit("No PDFs matched.")

    print(f"Extracting chunks from {len(pdfs)} PDF(s):")
    _print_cost_preview(pdfs)

    if args.dry_run:
        print("\n(--dry-run) exiting before submission.")
        return

    if not args.yes:
        reply = input("\nProceed with submission? Type 'yes' to continue: ").strip().lower()
        if reply != "yes":
            print("Aborted.")
            return

    client = LandingAIADE(apikey=LANDINGAI_API_KEY)
    for pdf in pdfs:
        run_one(client, pdf, force=args.force)

    print("\nDone.")


if __name__ == "__main__":
    main()
