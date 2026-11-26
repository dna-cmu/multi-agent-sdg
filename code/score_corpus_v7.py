"""
score_corpus_v7.py — re-score the FULL 30-report corpus under V7 prompt and
chunk-aware retrieval.

This is the production rerun that produces the headline credibility scores
reported in §4.4 (corpus-wide distribution) and §4.5 (sectoral / claim-type
analysis). It supersedes the original AI scoring (which used the same-section
claims-only retrieval) for all corpus-level results in the paper.

Design notes:
  - Per-report incremental saving: each report's output is written as soon
    as it finishes, so a mid-run interruption loses at most the in-flight
    report. Pre-existing output files are skipped on re-run (resume mode).
  - Async with concurrency cap: claims within a report are scored in
    parallel up to --concurrency simultaneous OpenAI calls. The script also
    retries on rate-limit errors with exponential backoff.
  - Doesn't touch the original main/full/*.json files. Writes to
    data/outputs/main/full_v7/*_full_v7.json with the same schema, plus
    `prompt_version` and `retrieval` metadata fields.
  - Supports --limit-reports N for a small pilot run before committing
    to the full corpus.

Usage:
    # Pilot (3 reports):
    python score_corpus_v7.py --limit-reports 3

    # Specific reports:
    python score_corpus_v7.py --reports BDMS-2024-SR-EN KTB-2024-SR-EN TRUE-2024-SR-EN

    # Full corpus:
    python score_corpus_v7.py

    # Resume after interruption (auto-skips reports with existing _v7.json):
    python score_corpus_v7.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from openai import AsyncOpenAI

from config.settings import (
    CREDIBILITY_DIMENSIONS,
    OPENAI_API_KEY,
    OUTPUTS_DIR,
    PRIMARY_MODEL,
    SCORING_RUNS,
    SCORING_TEMPERATURE,
    TIER_THRESHOLDS,
)
from prompts.credibility_scoring import CREDIBILITY_SCORING_PROMPT_V7
from utils.retrieval import (
    DEFAULT_CROSS_SECTION_TARGET,
    DEFAULT_MIN_SIMILARITY,
    DEFAULT_SAME_SECTION_TARGET,
    MixedResult,
    load_chunks_from_chunks_json,
    retrieve_chunk_aware_refs,
)

# Reuse the rendering and scoring primitives from the sample-scoring script.
# Keeping them in a single source file avoids drift between the validation
# run and the corpus run.
from score_sample_v7 import (
    render_context_v6 as render_context,
    classify_tier,
    compute_median,
    _async_one_run,
)


FULL_V7_DIR = OUTPUTS_DIR / "main" / "full_v7"
FULL_V7_DIR.mkdir(parents=True, exist_ok=True)


async def score_claim(client, claim, claims_pool, chunks_pool, sections, report_key, semaphore):
    """One claim through the V7 pipeline: retrieval → 3 runs → median + tier."""
    retrieval = retrieve_chunk_aware_refs(
        sample_claim=claim,
        claims_pool=claims_pool,
        chunks_pool=chunks_pool,
        sections=sections,
        report_key=report_key,
        cross_section_target=DEFAULT_CROSS_SECTION_TARGET,
        same_section_target=DEFAULT_SAME_SECTION_TARGET,
        min_similarity=DEFAULT_MIN_SIMILARITY,
    )
    context = render_context(retrieval)

    run_tasks = [_async_one_run(client, claim, context, semaphore) for _ in range(SCORING_RUNS)]
    run_results_raw = await asyncio.gather(*run_tasks)
    run_results = [r for r in run_results_raw if r is not None]

    if not run_results:
        claim_out = dict(claim)
        claim_out["credibility_scores"] = {}
        claim_out["composite_score"] = None
        claim_out["credibility_tier"] = "error"
        claim_out["overall_assessment"] = "All scoring runs failed"
        claim_out["n_cross_section"] = len(retrieval.cross_section)
        claim_out["n_same_section"] = len(retrieval.same_section)
        claim_out["retrieval_flags"] = list(retrieval.flags)
        return claim_out

    dimension_scores, overall = compute_median(run_results)
    composite = round(
        sum(dimension_scores[d]["score"] for d in CREDIBILITY_DIMENSIONS) / len(CREDIBILITY_DIMENSIONS),
        2,
    )
    tier = classify_tier(composite)

    claim_out = dict(claim)
    claim_out["credibility_scores"] = dimension_scores
    claim_out["composite_score"] = composite
    claim_out["credibility_tier"] = tier
    claim_out["overall_assessment"] = overall
    claim_out["n_cross_section"] = len(retrieval.cross_section)
    claim_out["n_same_section"] = len(retrieval.same_section)
    claim_out["retrieval_flags"] = list(retrieval.flags)
    return claim_out


async def score_report(client, full_path: Path, chunks_path: Path,
                       concurrency: int, output_path: Path) -> dict:
    """Score every mapped claim in one report, save incrementally."""
    with open(full_path) as f:
        full = json.load(f)
    chunks = load_chunks_from_chunks_json(chunks_path)

    claims = full.get("claims", [])
    sections = full.get("sections", [])
    metadata = full.get("metadata", {})
    company = metadata.get("company", full_path.stem)
    stem = full_path.stem.replace("_full", "")
    report_key = f"{stem}_corpus_v7"

    mapped = [c for c in claims if c.get("sdg_mappings")]
    unmapped = [c for c in claims if not c.get("sdg_mappings")]

    print(f"\n=== {company} — {len(mapped)} mapped claims (skip {len(unmapped)} unmapped) ===")

    semaphore = asyncio.Semaphore(concurrency)
    t0 = time.time()
    tasks = [score_claim(client, c, claims, chunks, sections, report_key, semaphore)
             for c in mapped]

    scored = []
    n_errors = 0
    for i, coro in enumerate(asyncio.as_completed(tasks), start=1):
        r = await coro
        scored.append(r)
        if r["credibility_tier"] == "error":
            n_errors += 1
        if i % 25 == 0 or i == len(tasks):
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(tasks) - i) / rate if rate > 0 else 0
            print(f"  [{i:3}/{len(tasks)}] elapsed={elapsed:.0f}s rate={rate:.1f}/s eta={eta:.0f}s "
                  f"errors={n_errors}")

    # Add back unmapped claims with empty scores (they're skipped, not failures)
    for c in unmapped:
        c_out = dict(c)
        c_out["credibility_scores"] = {}
        c_out["composite_score"] = None
        c_out["credibility_tier"] = None
        scored.append(c_out)

    # Preserve original order using claim_id where possible
    order_by_id = {c["claim_id"]: i for i, c in enumerate(claims)}
    scored.sort(key=lambda c: order_by_id.get(c["claim_id"], 1e9))

    # Compute summary stats
    tier_counts = {}
    composites = []
    for c in scored:
        t = c.get("credibility_tier")
        if t and t != "error":
            tier_counts[t] = tier_counts.get(t, 0) + 1
        if c.get("composite_score") is not None:
            composites.append(c["composite_score"])
    mean_comp = sum(composites) / len(composites) if composites else None

    out = {
        "metadata": metadata,
        "sections": sections,
        "claims": scored,
        "v7_rerun": {
            "prompt_version": "v7",
            "retrieval": "chunk_aware",
            "scoring_model": PRIMARY_MODEL,
            "scoring_runs": SCORING_RUNS,
            "scoring_temperature": SCORING_TEMPERATURE,
            "n_mapped_scored": len(mapped),
            "n_unmapped_skipped": len(unmapped),
            "n_errors": n_errors,
            "tier_counts": tier_counts,
            "mean_composite": round(mean_comp, 3) if mean_comp is not None else None,
            "elapsed_seconds": round(time.time() - t0, 1),
        },
    }
    with open(output_path, "w") as f:
        json.dump(out, f, indent=2)
    mean_str = f"{mean_comp:.3f}" if mean_comp is not None else "n/a"
    print(f"  Saved {output_path.name}: mean_composite={mean_str}, tiers={tier_counts}, errors={n_errors}")
    return out["v7_rerun"]


async def main_async():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-dir", type=Path, default=OUTPUTS_DIR / "main" / "full")
    parser.add_argument("--chunks-dir", type=Path, default=OUTPUTS_DIR / "main" / "chunks")
    parser.add_argument("--output-dir", type=Path, default=FULL_V7_DIR)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--limit-reports", type=int, default=None,
                        help="Process only the first N reports (for pilot runs).")
    parser.add_argument("--reports", nargs="*", default=None,
                        help="Specific report stems to process, e.g. BDMS-2024-SR-EN.")
    parser.add_argument("--force", action="store_true",
                        help="Re-score even if an output _full_v7.json already exists.")
    args = parser.parse_args()

    if not OPENAI_API_KEY:
        sys.exit("OPENAI_API_KEY not set in .env")

    # Resolve report list
    if args.reports:
        report_paths = []
        for r in args.reports:
            p = args.full_dir / f"{r}_full.json"
            if not p.exists():
                print(f"NOT FOUND: {p}")
                continue
            report_paths.append(p)
    else:
        report_paths = sorted(args.full_dir.glob("*_full.json"))
    if args.limit_reports:
        report_paths = report_paths[: args.limit_reports]

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Filter out reports that already have an output (resume mode)
    todo = []
    skipped = []
    for full_path in report_paths:
        stem = full_path.stem.replace("_full", "")
        out_path = args.output_dir / f"{stem}_full_v7.json"
        chunks_path = args.chunks_dir / f"{stem}_chunks.json"
        if not chunks_path.exists():
            print(f"SKIP (no chunks): {stem}")
            continue
        if out_path.exists() and not args.force:
            skipped.append(stem)
            continue
        todo.append((full_path, chunks_path, out_path))

    print(f"\n{'='*60}")
    print(f"Reports to score: {len(todo)}  (skip {len(skipped)} already done)")
    if skipped:
        print(f"  Already done: {', '.join(skipped[:5])}{' …' if len(skipped) > 5 else ''}")
    total_claims = 0
    for fp, cp, _ in todo:
        with open(fp) as f:
            d = json.load(f)
        n = sum(1 for c in d.get("claims", []) if c.get("sdg_mappings"))
        total_claims += n
    est_cost = total_claims * 3 * (1800 * 2.5/1e6 + 450 * 10/1e6)
    print(f"Mapped claims across these reports: ~{total_claims}")
    print(f"Estimated OpenAI cost: ~${est_cost:.2f}")
    print(f"Concurrency: {args.concurrency}  | Model: {PRIMARY_MODEL}  | Runs/claim: {SCORING_RUNS}")
    print(f"{'='*60}\n")

    if not todo:
        print("Nothing to do.")
        return

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    t_start = time.time()
    summaries = []
    try:
        for i, (full_path, chunks_path, out_path) in enumerate(todo, start=1):
            print(f"\n[{i}/{len(todo)}] {full_path.stem}")
            summary = await score_report(client, full_path, chunks_path,
                                          args.concurrency, out_path)
            summaries.append((full_path.stem, summary))
    finally:
        await client.close()

    # Overall summary
    print(f"\n{'='*60}")
    print(f"DONE. Wall time: {(time.time()-t_start)/60:.1f} min")
    print(f"{'='*60}")
    total_tier = {}
    total_mean = []
    for stem, s in summaries:
        for k, v in s.get("tier_counts", {}).items():
            total_tier[k] = total_tier.get(k, 0) + v
        if s.get("mean_composite") is not None:
            total_mean.append(s["mean_composite"])
    print(f"Tier totals across {len(summaries)} reports: {total_tier}")
    if total_mean:
        print(f"Cross-report mean composite (unweighted avg of per-report means): {sum(total_mean)/len(total_mean):.3f}")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
