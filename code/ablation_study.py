"""
Ablation Study: Comparing the full agentic pipeline against simpler baselines.

Three conditions:
  A) Zero-shot: Single LLM call, no context, no multi-run, no two-stage mapping
  B) RAG-only: Context retrieval + single LLM call, but no multi-run or agent orchestration
  C) Full pipeline: The existing agentic framework (two-stage mapping, context retrieval, 3-run median)

We sample N claims from the existing scored corpus, re-score them under conditions A and B,
then compare against the existing condition C scores.

Usage:
    python ablation_study.py --sample-size 50 --concurrency 5
    python ablation_study.py --sample-size 50 --concurrency 0   # sequential
    python ablation_study.py --results-only                     # just analyze existing results
"""

import argparse
import asyncio
import json
import random
import statistics
from pathlib import Path
from collections import defaultdict

from openai import OpenAI, AsyncOpenAI
from tqdm import tqdm

from config.settings import (
    OPENAI_API_KEY,
    PRIMARY_MODEL,
    SCORING_TEMPERATURE,
    CREDIBILITY_DIMENSIONS,
    TIER_THRESHOLDS,
    OUTPUTS_DIR,
)
from prompts.credibility_scoring import CREDIBILITY_SCORING_PROMPT

# ── Prompts ───────────────────────────────────────────────────────────────

ZERO_SHOT_PROMPT = """You are an expert sustainability report analyst assessing the credibility of corporate SDG claims.

Evaluate this claim on 5 dimensions, each scored 0-3.

Claim: "{claim_text}"
Company: {company} | Sector: {sector} | Year: {report_year}

Score each dimension:
- SPECIFICITY (0=vague, 1=generic theme, 2=specific programme, 3=action-level detail with names/locations/scope)
- MEASURABILITY (0=no metrics, 1=qualitative only, 2=numbers but no baselines, 3=KPIs with baselines and units)
- TEMPORALITY (0=no timeframe, 1=vague time, 2=specific year, 3=dated milestones with interim targets)
- EVIDENCE (0=no evidence, 1=self-reported only, 2=internal data with methodology, 3=third-party verified)
- CONSISTENCY (0=contradicts itself, 1=minor inconsistencies, 2=mostly consistent, 3=fully corroborated)

Return ONLY valid JSON:
{{
  "specificity": {{"score": 2, "rationale": "..."}},
  "measurability": {{"score": 1, "rationale": "..."}},
  "temporality": {{"score": 2, "rationale": "..."}},
  "evidence": {{"score": 1, "rationale": "..."}},
  "consistency": {{"score": 2, "rationale": "..."}}
}}"""


# ── Sampling ──────────────────────────────────────────────────────────────

def load_all_scored_claims() -> list[dict]:
    """Load all scored claims from the 5 processed reports."""
    reports = ['CPF-2023-SR-EN', 'BDMS-2023-SR-EN', 'SCC-2023-SR-EN', 'SCB-2023-SR-EN', 'True-2023-SR-EN']
    all_claims = []
    all_claims_by_company = defaultdict(list)

    for name in reports:
        path = OUTPUTS_DIR / f"{name}_full.json"
        if not path.exists():
            continue
        with open(path, "r") as f:
            r = json.load(f)
        company = r["metadata"]["company"]
        sector = r["metadata"]["sector"]
        for c in r["claims"]:
            if c.get("composite_score") is not None:
                c["_company"] = company
                c["_sector"] = sector
                all_claims.append(c)
                all_claims_by_company[company].append(c)

    return all_claims, all_claims_by_company


def stratified_sample(all_claims_by_company: dict, sample_size: int = 50, seed: int = 42) -> list[dict]:
    """
    Stratified sampling: equal claims per company, proportional by tier within each company.
    """
    random.seed(seed)
    companies = sorted(all_claims_by_company.keys())
    per_company = sample_size // len(companies)
    remainder = sample_size % len(companies)

    sample = []
    for i, company in enumerate(companies):
        claims = all_claims_by_company[company]
        n = per_company + (1 if i < remainder else 0)

        # Stratify by tier within company
        by_tier = defaultdict(list)
        for c in claims:
            by_tier[c["credibility_tier"]].append(c)

        company_sample = []
        tiers = ["symbolic", "partially_substantive", "substantive"]
        tier_counts = {t: len(by_tier[t]) for t in tiers}
        total = sum(tier_counts.values())

        for tier in tiers:
            tier_n = max(1, round(n * tier_counts[tier] / total)) if total > 0 else 0
            tier_n = min(tier_n, len(by_tier[tier]))
            company_sample.extend(random.sample(by_tier[tier], tier_n))

        # Trim or pad to exact count
        if len(company_sample) > n:
            company_sample = random.sample(company_sample, n)
        elif len(company_sample) < n:
            remaining = [c for c in claims if c not in company_sample]
            extra = min(n - len(company_sample), len(remaining))
            company_sample.extend(random.sample(remaining, extra))

        sample.extend(company_sample)

    print(f"  Sampled {len(sample)} claims from {len(companies)} companies")
    tier_dist = defaultdict(int)
    for c in sample:
        tier_dist[c["credibility_tier"]] += 1
    for t, count in sorted(tier_dist.items()):
        print(f"    {t}: {count}")

    return sample


# ── Baseline A: Zero-shot ─────────────────────────────────────────────────

def zero_shot_score(client: OpenAI, claim: dict) -> dict:
    """Score a claim with zero-shot: no context, no multi-run, minimal prompt."""
    try:
        response = client.chat.completions.create(
            model=PRIMARY_MODEL,
            temperature=SCORING_TEMPERATURE,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a sustainability report analyst. Always respond with valid JSON."},
                {"role": "user", "content": ZERO_SHOT_PROMPT.format(
                    claim_text=claim["claim_text"],
                    company=claim.get("_company", claim.get("company", "Unknown")),
                    sector=claim.get("_sector", claim.get("sector", "Unknown")),
                    report_year=claim.get("report_year", "2023"),
                )},
            ],
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"    Zero-shot failed for {claim['claim_id']}: {e}")
        return None


async def async_zero_shot_score(client: AsyncOpenAI, claim: dict,
                                 semaphore: asyncio.Semaphore, max_retries: int = 3) -> dict:
    """Async zero-shot scoring with retry."""
    for attempt in range(max_retries):
        async with semaphore:
            try:
                response = await client.chat.completions.create(
                    model=PRIMARY_MODEL,
                    temperature=SCORING_TEMPERATURE,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": "You are a sustainability report analyst. Always respond with valid JSON."},
                        {"role": "user", "content": ZERO_SHOT_PROMPT.format(
                            claim_text=claim["claim_text"],
                            company=claim.get("_company", claim.get("company", "Unknown")),
                            sector=claim.get("_sector", claim.get("sector", "Unknown")),
                            report_year=claim.get("report_year", "2023"),
                        )},
                    ],
                )
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    await asyncio.sleep(2 ** attempt)
                elif attempt == max_retries - 1:
                    print(f"    Zero-shot failed for {claim['claim_id']}: {e}")
                    return None
                else:
                    await asyncio.sleep(1)
    return None


# ── Baseline B: RAG-only (context + single pass) ─────────────────────────

def find_context_passages(claim: dict, all_claims: list[dict], max_passages: int = 5) -> str:
    """Find related passages (same as full pipeline)."""
    claim_words = set(claim["claim_text"].lower().split())
    scored = []
    for other in all_claims:
        if other["claim_id"] == claim["claim_id"]:
            continue
        other_words = set(other["claim_text"].lower().split())
        overlap = len(claim_words & other_words)
        if overlap > 3:
            scored.append((overlap, other))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:max_passages]
    if not top:
        return "(No related passages found in report)"
    text = ""
    for _, other in top:
        text += f"\n- [{other.get('section', 'Unknown')}]: {other['claim_text'][:300]}"
    return text


def rag_only_score(client: OpenAI, claim: dict, context_passages: str) -> dict:
    """Score with context retrieval but single pass (no 3-run median)."""
    try:
        response = client.chat.completions.create(
            model=PRIMARY_MODEL,
            temperature=SCORING_TEMPERATURE,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are an expert sustainability report analyst. Score claims strictly according to the rubric. Always respond with valid JSON."},
                {"role": "user", "content": CREDIBILITY_SCORING_PROMPT.format(
                    claim_text=claim["claim_text"],
                    section=claim.get("section", "Unknown"),
                    page=claim.get("page", "Unknown"),
                    company=claim.get("_company", claim.get("company", "Unknown")),
                    sector=claim.get("_sector", claim.get("sector", "Unknown")),
                    report_year=claim.get("report_year", "2023"),
                    context_passages=context_passages,
                )},
            ],
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"    RAG-only failed for {claim['claim_id']}: {e}")
        return None


async def async_rag_only_score(client: AsyncOpenAI, claim: dict, context_passages: str,
                                semaphore: asyncio.Semaphore, max_retries: int = 3) -> dict:
    """Async RAG-only scoring with retry."""
    for attempt in range(max_retries):
        async with semaphore:
            try:
                response = await client.chat.completions.create(
                    model=PRIMARY_MODEL,
                    temperature=SCORING_TEMPERATURE,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": "You are an expert sustainability report analyst. Score claims strictly according to the rubric. Always respond with valid JSON."},
                        {"role": "user", "content": CREDIBILITY_SCORING_PROMPT.format(
                            claim_text=claim["claim_text"],
                            section=claim.get("section", "Unknown"),
                            page=claim.get("page", "Unknown"),
                            company=claim.get("_company", claim.get("company", "Unknown")),
                            sector=claim.get("_sector", claim.get("sector", "Unknown")),
                            report_year=claim.get("report_year", "2023"),
                            context_passages=context_passages,
                        )},
                    ],
                )
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    await asyncio.sleep(2 ** attempt)
                elif attempt == max_retries - 1:
                    print(f"    RAG-only failed for {claim['claim_id']}: {e}")
                    return None
                else:
                    await asyncio.sleep(1)
    return None


# ── Score extraction helpers ──────────────────────────────────────────────

def extract_scores(result: dict) -> dict:
    """Extract dimension scores from an LLM response."""
    scores = {}
    for dim in CREDIBILITY_DIMENSIONS:
        dim_data = result.get(dim, {})
        if isinstance(dim_data, dict):
            scores[dim] = dim_data.get("score", 0)
        elif isinstance(dim_data, (int, float)):
            scores[dim] = int(dim_data)
        else:
            scores[dim] = 0
    scores["composite"] = round(sum(scores[d] for d in CREDIBILITY_DIMENSIONS) / len(CREDIBILITY_DIMENSIONS), 2)
    return scores


def classify_tier(composite: float) -> str:
    """Classify composite score into tier."""
    if composite >= TIER_THRESHOLDS["substantive"][0]:
        return "substantive"
    elif composite >= TIER_THRESHOLDS["partially_substantive"][0]:
        return "partially_substantive"
    return "symbolic"


# ── Run ablation ──────────────────────────────────────────────────────────

def run_ablation_sequential(sample: list[dict], all_claims: list[dict]) -> dict:
    """Run both baselines sequentially."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    results = []

    print(f"\n{'='*60}")
    print(f"ABLATION STUDY: {len(sample)} claims (sequential)")
    print(f"{'='*60}")

    for claim in tqdm(sample, desc="  Scoring baselines"):
        # Get context for RAG baseline
        same_company_claims = [c for c in all_claims if c.get("_company") == claim.get("_company")]
        context = find_context_passages(claim, same_company_claims)

        # Baseline A: Zero-shot
        zs_result = zero_shot_score(client, claim)
        zs_scores = extract_scores(zs_result) if zs_result else None

        # Baseline B: RAG-only
        rag_result = rag_only_score(client, claim, context)
        rag_scores = extract_scores(rag_result) if rag_result else None

        # Condition C: Full pipeline (from existing data)
        full_scores = {}
        for dim in CREDIBILITY_DIMENSIONS:
            dim_data = claim.get("credibility_scores", {}).get(dim, {})
            full_scores[dim] = dim_data.get("score", 0) if isinstance(dim_data, dict) else 0
        full_scores["composite"] = claim["composite_score"]

        results.append({
            "claim_id": claim["claim_id"],
            "company": claim.get("_company", "Unknown"),
            "claim_text": claim["claim_text"][:200],
            "full_pipeline": full_scores,
            "zero_shot": zs_scores,
            "rag_only": rag_scores,
            "full_tier": claim["credibility_tier"],
            "zero_shot_tier": classify_tier(zs_scores["composite"]) if zs_scores else None,
            "rag_only_tier": classify_tier(rag_scores["composite"]) if rag_scores else None,
        })

    return results


async def run_ablation_async(sample: list[dict], all_claims: list[dict], concurrency: int = 5) -> list:
    """Run both baselines with parallel API calls."""
    from tqdm.asyncio import tqdm as atqdm

    async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    semaphore = asyncio.Semaphore(concurrency)

    print(f"\n{'='*60}")
    print(f"ABLATION STUDY: {len(sample)} claims (concurrency={concurrency})")
    print(f"  API calls: ~{len(sample) * 2} (1 zero-shot + 1 RAG per claim)")
    print(f"{'='*60}")

    # Pre-compute contexts
    contexts = {}
    for claim in sample:
        same_company_claims = [c for c in all_claims if c.get("_company") == claim.get("_company")]
        contexts[claim["claim_id"]] = find_context_passages(claim, same_company_claims)

    async def process_one(claim):
        context = contexts[claim["claim_id"]]
        zs_result = await async_zero_shot_score(async_client, claim, semaphore)
        rag_result = await async_rag_only_score(async_client, claim, context, semaphore)

        zs_scores = extract_scores(zs_result) if zs_result else None
        rag_scores = extract_scores(rag_result) if rag_result else None

        full_scores = {}
        for dim in CREDIBILITY_DIMENSIONS:
            dim_data = claim.get("credibility_scores", {}).get(dim, {})
            full_scores[dim] = dim_data.get("score", 0) if isinstance(dim_data, dict) else 0
        full_scores["composite"] = claim["composite_score"]

        return {
            "claim_id": claim["claim_id"],
            "company": claim.get("_company", "Unknown"),
            "claim_text": claim["claim_text"][:200],
            "full_pipeline": full_scores,
            "zero_shot": zs_scores,
            "rag_only": rag_scores,
            "full_tier": claim["credibility_tier"],
            "zero_shot_tier": classify_tier(zs_scores["composite"]) if zs_scores else None,
            "rag_only_tier": classify_tier(rag_scores["composite"]) if rag_scores else None,
        }

    tasks = [process_one(claim) for claim in sample]
    results = []
    for coro in atqdm(asyncio.as_completed(tasks), total=len(tasks), desc="  Scoring baselines"):
        result = await coro
        results.append(result)

    # Restore order
    claim_order = {c["claim_id"]: i for i, c in enumerate(sample)}
    results.sort(key=lambda r: claim_order.get(r["claim_id"], 0))

    return results


# ── Analysis ──────────────────────────────────────────────────────────────

def analyze_results(results: list[dict]):
    """Analyze and print ablation study results."""
    print(f"\n{'='*60}")
    print("ABLATION RESULTS")
    print(f"{'='*60}")
    print(f"Sample size: {len(results)}")

    # Filter to claims where all 3 conditions succeeded
    valid = [r for r in results if r["zero_shot"] and r["rag_only"] and r["full_pipeline"]]
    print(f"Valid (all 3 conditions scored): {len(valid)}")

    if not valid:
        print("  No valid results to analyze.")
        return

    # --- Composite score comparison ---
    print(f"\n--- COMPOSITE SCORE COMPARISON ---")
    for condition in ["zero_shot", "rag_only", "full_pipeline"]:
        scores = [r[condition]["composite"] for r in valid]
        mean = round(sum(scores) / len(scores), 3)
        std = round(statistics.stdev(scores), 3) if len(scores) > 1 else 0
        print(f"  {condition:<20} mean={mean:.3f}  std={std:.3f}  min={min(scores)}  max={max(scores)}")

    # --- Per-dimension comparison ---
    print(f"\n--- PER-DIMENSION MEAN SCORES ---")
    print(f"  {'Dimension':<20} {'Zero-shot':>10} {'RAG-only':>10} {'Full pipe':>10} {'ZS→Full Δ':>10}")
    for dim in CREDIBILITY_DIMENSIONS:
        zs_scores = [r["zero_shot"][dim] for r in valid]
        rag_scores = [r["rag_only"][dim] for r in valid]
        full_scores = [r["full_pipeline"][dim] for r in valid]
        zs_mean = sum(zs_scores) / len(zs_scores)
        rag_mean = sum(rag_scores) / len(rag_scores)
        full_mean = sum(full_scores) / len(full_scores)
        delta = full_mean - zs_mean
        print(f"  {dim:<20} {zs_mean:>10.2f} {rag_mean:>10.2f} {full_mean:>10.2f} {delta:>+10.2f}")

    # --- Tier classification accuracy ---
    print(f"\n--- TIER CLASSIFICATION AGREEMENT ---")
    for condition, tier_key in [("zero_shot", "zero_shot_tier"), ("rag_only", "rag_only_tier")]:
        matches = sum(1 for r in valid if r[tier_key] == r["full_tier"])
        pct = round(matches / len(valid) * 100, 1)
        print(f"  {condition:<20} agrees with full pipeline: {matches}/{len(valid)} ({pct}%)")

    # --- Score deviation analysis ---
    print(f"\n--- MEAN ABSOLUTE DEVIATION FROM FULL PIPELINE ---")
    for condition in ["zero_shot", "rag_only"]:
        deviations = [abs(r[condition]["composite"] - r["full_pipeline"]["composite"]) for r in valid]
        mad = round(sum(deviations) / len(deviations), 3)
        print(f"  {condition:<20} MAD={mad:.3f}")

    # --- Per-dimension deviation ---
    print(f"\n--- PER-DIMENSION MEAN ABSOLUTE DEVIATION ---")
    print(f"  {'Dimension':<20} {'ZS MAD':>10} {'RAG MAD':>10}")
    for dim in CREDIBILITY_DIMENSIONS:
        zs_devs = [abs(r["zero_shot"][dim] - r["full_pipeline"][dim]) for r in valid]
        rag_devs = [abs(r["rag_only"][dim] - r["full_pipeline"][dim]) for r in valid]
        zs_mad = sum(zs_devs) / len(zs_devs)
        rag_mad = sum(rag_devs) / len(rag_devs)
        print(f"  {dim:<20} {zs_mad:>10.3f} {rag_mad:>10.3f}")

    # --- Scoring inflation/deflation ---
    print(f"\n--- SCORING BIAS (positive = inflates, negative = deflates vs full pipeline) ---")
    for condition in ["zero_shot", "rag_only"]:
        biases = [r[condition]["composite"] - r["full_pipeline"]["composite"] for r in valid]
        mean_bias = round(sum(biases) / len(biases), 3)
        inflated = sum(1 for b in biases if b > 0.2)
        deflated = sum(1 for b in biases if b < -0.2)
        print(f"  {condition:<20} mean_bias={mean_bias:+.3f}  inflated={inflated}  deflated={deflated}")

    return valid


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ablation Study for SDG Credibility Framework")
    parser.add_argument("--sample-size", type=int, default=50, help="Number of claims to sample (default: 50)")
    parser.add_argument("--concurrency", type=int, default=0, help="Parallel API calls (0=sequential)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--results-only", action="store_true", help="Only analyze existing results (no API calls)")
    args = parser.parse_args()

    results_path = OUTPUTS_DIR / "ablation_results.json"

    if args.results_only:
        if not results_path.exists():
            print("No existing ablation results found. Run the study first.")
            return
        with open(results_path, "r") as f:
            results = json.load(f)
        analyze_results(results)
        return

    # Load and sample
    all_claims, by_company = load_all_scored_claims()
    sample = stratified_sample(by_company, args.sample_size, args.seed)

    # Run baselines
    if args.concurrency > 0:
        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(run_ablation_async(sample, all_claims, args.concurrency))
        finally:
            loop.close()
    else:
        results = run_ablation_sequential(sample, all_claims)

    # Save results
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved to: {results_path}")

    # Analyze
    analyze_results(results)


if __name__ == "__main__":
    main()
