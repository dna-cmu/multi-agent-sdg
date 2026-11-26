"""
score_sample_v6.py — re-score the 63 v5 sample claims using the V6 prompt
that incorporates Expert 1's rubric refinements.

DEPRECATED FOR PRODUCTION USE. V6's mechanical two-DIRECT-refs C rule was
subsequently shown to over-correct (pooled wκ dropped from 0.709 to 0.665).
The production prompt is V7; see score_sample_v7.py. V6 is retained here
solely to reproduce the prompt-sensitivity analysis (Figure 2, §4.1.2 of
Naparat 2026).

V6 changes vs V5 prompt (see prompts/credibility_scoring.CREDIBILITY_SCORING_PROMPT_V6):
  - M=0: explicitly includes "reduce" and "eliminate" as qualitative-only
  - T=1: includes past-tense achievement markers (have completed, achieved, etc.)
  - C: operationalised by counting cross-section references + DIRECT/INDIRECT classification
       (strict two-DIRECT rule; superseded by V7's one-direct-or-two-any rule)
  - Context rendering: cross-section vs same-section refs are explicitly grouped

Output: data/outputs/validation/sample_v6_ai_scores.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
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
from prompts.credibility_scoring import CREDIBILITY_SCORING_PROMPT_V6
from utils.retrieval import (
    DEFAULT_CROSS_SECTION_TARGET,
    DEFAULT_MIN_SIMILARITY,
    DEFAULT_SAME_SECTION_TARGET,
    MixedResult,
    load_chunks_from_chunks_json,
    retrieve_chunk_aware_refs,
)


def render_context_v6(result: MixedResult) -> str:
    """
    Render the chunk-aware retrieval result with cross-section and same-section
    references EXPLICITLY GROUPED. The V6 prompt relies on this grouping to
    apply the operationalised C-dimension rule (count of cross-section refs).
    """
    lines: list[str] = []

    lines.append("=== CROSS-SECTION REFERENCES ===")
    if result.cross_section:
        for ref in result.cross_section:
            kind = "CLAIM" if ref.source_type == "claim" else (ref.chunk_type or "CHUNK")
            section = ref.section or "Unknown"
            page = ref.page if ref.page is not None else "?"
            text = (ref.text or "").strip()
            if len(text) > 600:
                text = text[:597] + "…"
            lines.append(f"- [{kind} | Page {page}, {section}]: {text}")
    else:
        lines.append("(none — no cross-section references above the relevance threshold)")

    lines.append("")
    lines.append("=== SAME-SECTION REFERENCES ===")
    if result.same_section:
        for ref in result.same_section:
            kind = "CLAIM" if ref.source_type == "claim" else (ref.chunk_type or "CHUNK")
            section = ref.section or "Unknown"
            page = ref.page if ref.page is not None else "?"
            text = (ref.text or "").strip()
            if len(text) > 600:
                text = text[:597] + "…"
            lines.append(f"- [{kind} | Page {page}, {section}]: {text}")
    else:
        lines.append("(none)")

    if result.flags:
        lines.append("")
        lines.append("=== RETRIEVAL FLAGS ===")
        for flag in result.flags:
            lines.append(f"- {flag}")

    return "\n".join(lines)


def classify_tier(composite: float) -> str:
    for tier_name, (low, high) in TIER_THRESHOLDS.items():
        if low <= composite < high:
            return tier_name
    if composite >= TIER_THRESHOLDS["substantive"][0]:
        return "substantive"
    return "symbolic"


def compute_median(run_results: list[dict]) -> tuple[dict, str]:
    dimension_scores = {}
    for dim in CREDIBILITY_DIMENSIONS:
        scores: list[int] = []
        rationales: list[str] = []
        for run in run_results:
            dim_data = run.get(dim, {})
            if isinstance(dim_data, dict):
                score = dim_data.get("score")
                rationale = dim_data.get("rationale", "")
            elif isinstance(dim_data, (int, float)):
                score = dim_data
                rationale = ""
            else:
                continue
            if score is not None:
                scores.append(int(score))
                rationales.append(rationale)
        if scores:
            median_score = int(statistics.median(scores))
            closest_idx = min(range(len(scores)), key=lambda i: abs(scores[i] - median_score))
            dimension_scores[dim] = {
                "score": median_score,
                "rationale": rationales[closest_idx] if rationales else "",
                "all_run_scores": scores,
                "agreement": len(set(scores)) == 1,
            }
        else:
            dimension_scores[dim] = {
                "score": 0, "rationale": "Could not score",
                "all_run_scores": [], "agreement": False,
            }
    overall = run_results[0].get("overall_assessment", "") if run_results else ""
    return dimension_scores, overall


async def _async_one_run(client: AsyncOpenAI, claim: dict, context: str,
                         semaphore: asyncio.Semaphore, max_retries: int = 3) -> dict | None:
    for attempt in range(max_retries):
        async with semaphore:
            try:
                response = await client.chat.completions.create(
                    model=PRIMARY_MODEL,
                    temperature=SCORING_TEMPERATURE,
                    response_format={"type": "json_object"},
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert sustainability report analyst. Score claims strictly according to the rubric. Always respond with valid JSON.",
                        },
                        {
                            "role": "user",
                            "content": CREDIBILITY_SCORING_PROMPT_V6.format(
                                claim_text=claim["claim_text"],
                                section=claim.get("section", "Unknown"),
                                page=claim.get("page", "Unknown"),
                                company=claim.get("company", "Unknown"),
                                sector=claim.get("sector", "Unknown"),
                                report_year=claim.get("report_year", "Unknown"),
                                context_passages=context,
                            ),
                        },
                    ],
                )
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                msg = str(e)
                if ("rate_limit" in msg.lower() or "429" in msg) and attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    print(f"    rate-limited, waiting {wait}s")
                    await asyncio.sleep(wait)
                elif attempt == max_retries - 1:
                    print(f"    run failed: {type(e).__name__}: {msg[:160]}")
                    return None
                else:
                    await asyncio.sleep(1)
    return None


async def score_one(client: AsyncOpenAI, claim: dict, claims_pool: list[dict],
                    chunks_pool: list[dict], sections: list[dict],
                    report_key: str, semaphore: asyncio.Semaphore) -> dict:
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
    context = render_context_v6(retrieval)

    run_tasks = [_async_one_run(client, claim, context, semaphore) for _ in range(SCORING_RUNS)]
    run_results_raw = await asyncio.gather(*run_tasks)
    run_results = [r for r in run_results_raw if r is not None]

    if not run_results:
        return {
            "claim_id": claim["claim_id"],
            "company": claim.get("company"),
            "credibility_scores": {},
            "composite_score": None,
            "credibility_tier": "error",
            "overall_assessment": "All scoring runs failed",
            "n_cross_section": len(retrieval.cross_section),
            "n_same_section": len(retrieval.same_section),
            "retrieval_flags": list(retrieval.flags),
        }

    dimension_scores, overall = compute_median(run_results)
    composite = round(
        sum(dimension_scores[d]["score"] for d in CREDIBILITY_DIMENSIONS) / len(CREDIBILITY_DIMENSIONS),
        2,
    )
    tier = classify_tier(composite)

    return {
        "claim_id": claim["claim_id"],
        "company": claim.get("company"),
        "credibility_scores": dimension_scores,
        "composite_score": composite,
        "credibility_tier": tier,
        "overall_assessment": overall,
        "n_cross_section": len(retrieval.cross_section),
        "n_same_section": len(retrieval.same_section),
        "retrieval_flags": list(retrieval.flags),
    }


async def main_async():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample", type=Path,
        default=OUTPUTS_DIR / "validation" / "expert_validation_sample_v2.json",
    )
    parser.add_argument("--full-dir", type=Path, default=OUTPUTS_DIR / "main" / "full")
    parser.add_argument("--chunks-dir", type=Path, default=OUTPUTS_DIR / "main" / "chunks")
    parser.add_argument(
        "--output", type=Path,
        default=OUTPUTS_DIR / "validation" / "sample_v6_ai_scores.json",
    )
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if not OPENAI_API_KEY:
        sys.exit("OPENAI_API_KEY not set in .env")

    print(f"Loading sample: {args.sample}")
    with open(args.sample) as f:
        sample = json.load(f)
    sample_claims = sample["claims"] if isinstance(sample, dict) else sample
    if args.limit:
        sample_claims = sample_claims[: args.limit]
    print(f"  {len(sample_claims)} claims")

    print("Indexing reports...")
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
            continue
        chunks = load_chunks_from_chunks_json(chunks_path)
        by_company[company] = {
            "claims": full.get("claims", []),
            "sections": full.get("sections", []),
            "chunks": chunks,
            # Reuse v5full embedding cache — same texts, same model
            "report_key": f"{stem}_v5full",
        }
    print(f"  {len(by_company)} reports with chunks available")

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    semaphore = asyncio.Semaphore(args.concurrency)

    t0 = time.time()
    tasks = []
    for sc in sample_claims:
        company = sc.get("company", "")
        if company not in by_company:
            continue
        d = by_company[company]
        enriched = dict(sc)
        pool_by_id = {c["claim_id"]: c for c in d["claims"]}
        if not enriched.get("section"):
            enriched["section"] = pool_by_id.get(sc["claim_id"], {}).get("section", "")
        if "page" not in enriched:
            enriched["page"] = pool_by_id.get(sc["claim_id"], {}).get("page", "?")
        tasks.append(score_one(
            client, enriched, d["claims"], d["chunks"], d["sections"],
            d["report_key"], semaphore,
        ))

    print(f"Scoring {len(tasks)} claims with V6 prompt, concurrency {args.concurrency}...")
    results: list[dict] = []
    for i, coro in enumerate(asyncio.as_completed(tasks), start=1):
        r = await coro
        results.append(r)
        s = r["credibility_scores"]
        if s:
            score_str = " ".join(f"{d[0].upper()}={s[d]['score']}" for d in CREDIBILITY_DIMENSIONS)
            print(f"  [{i:2}/{len(tasks)}] {r['claim_id']} ({(r['company'] or '')[:18]}): "
                  f"{score_str} | comp={r['composite_score']} ({r['credibility_tier']})")
        else:
            print(f"  [{i:2}/{len(tasks)}] {r['claim_id']}: ERROR")

    await client.close()
    print(f"\nFinished in {time.time()-t0:.0f}s")

    by_id = {(r["claim_id"], r["company"]): r for r in results}
    ordered = [by_id[(sc["claim_id"], sc.get("company"))] for sc in sample_claims if (sc["claim_id"], sc.get("company")) in by_id]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({
            "n_claims": len(ordered),
            "scoring_model": PRIMARY_MODEL,
            "scoring_runs": SCORING_RUNS,
            "scoring_temperature": SCORING_TEMPERATURE,
            "prompt_version": "v6",
            "prompt_changes": [
                "M=0: reduce/eliminate added as qualitative-only examples",
                "T=1: past-tense achievement markers added",
                "C: operationalised via cross-section ref counts (DIRECT/INDIRECT)",
                "Context rendering: cross-section vs same-section explicitly grouped",
            ],
            "retrieval": "chunk_aware (claims + ADE chunks, section-diverse)",
            "results": ordered,
        }, f, indent=2)
    print(f"Saved: {args.output}")

    tiers: dict[str, int] = {}
    for r in ordered:
        t = r.get("credibility_tier") or "unknown"
        tiers[t] = tiers.get(t, 0) + 1
    print(f"\nTier distribution (V6): {tiers}")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
