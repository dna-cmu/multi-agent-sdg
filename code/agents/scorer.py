"""
Phase 3: Multi-Dimensional Credibility Assessment (Scorer Agent)

This agent evaluates each SDG-mapped claim on 5 dimensions (0-3 scale):
Specificity, Measurability, Temporality, Evidence, Consistency.

Key features:
- 3-run median scoring for reliability
- Context-aware scoring (retrieves related passages from same report)
- Composite score calculation and tier classification
- Parallel (async) processing with rate limiting

Prompt version: as of v0.7.0 (May 2026), the imported CREDIBILITY_SCORING_PROMPT
constant resolves to the V7 prompt — the production version validated against
three raters (Krippendorff α = 0.744). For full reproducibility of earlier
results, see ``prompts/credibility_scoring`` and pin to the explicit V5/V6
constants. The lightweight ``_find_context_passages`` retrieval implemented
below is a keyword-overlap fallback; for the chunk-aware section-diverse
retrieval reported in §4.2–4.3 of the paper, use ``score_corpus_v7.py`` or
``score_sample_v7.py`` which call ``utils/retrieval.retrieve_chunk_aware_refs``.
"""

import json
import asyncio
import statistics
from openai import OpenAI, AsyncOpenAI
from tqdm import tqdm

from config.settings import (
    OPENAI_API_KEY,
    PRIMARY_MODEL,
    SCORING_TEMPERATURE,
    SCORING_RUNS,
    CREDIBILITY_DIMENSIONS,
    TIER_THRESHOLDS,
)
from prompts.credibility_scoring import CREDIBILITY_SCORING_PROMPT, CONSISTENCY_CHECK_PROMPT


class ScorerAgent:
    """Phase 3 agent: scores claim credibility across 5 dimensions."""

    def __init__(self):
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = PRIMARY_MODEL

    def _find_context_passages(self, claim: dict, all_claims: list[dict], max_passages: int = 5) -> str:
        """
        Find related passages from the same report for consistency checking.
        Uses simple keyword overlap — could be upgraded to vector similarity.
        """
        claim_words = set(claim["claim_text"].lower().split())
        scored_claims = []

        for other in all_claims:
            if other["claim_id"] == claim["claim_id"]:
                continue
            other_words = set(other["claim_text"].lower().split())
            overlap = len(claim_words & other_words)
            if overlap > 3:  # Minimum overlap threshold
                scored_claims.append((overlap, other))

        scored_claims.sort(key=lambda x: x[0], reverse=True)
        top_passages = scored_claims[:max_passages]

        if not top_passages:
            return "(No related passages found in report)"

        passages_text = ""
        for _, other in top_passages:
            passages_text += f"\n- [Page {other.get('page', '?')}, {other.get('section', 'Unknown')}]: {other['claim_text'][:300]}"

        return passages_text

    def _score_single_run(self, claim: dict, context_passages: str) -> dict:
        """Perform one scoring run for a claim."""
        response = self.openai_client.chat.completions.create(
            model=self.model,
            temperature=SCORING_TEMPERATURE,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert sustainability report analyst. Score claims strictly according to the rubric. Always respond with valid JSON.",
                },
                {
                    "role": "user",
                    "content": CREDIBILITY_SCORING_PROMPT.format(
                        claim_text=claim["claim_text"],
                        section=claim.get("section", "Unknown"),
                        page=claim.get("page", "Unknown"),
                        company=claim.get("company", "Unknown"),
                        sector=claim.get("sector", "Unknown"),
                        report_year=claim.get("report_year", "Unknown"),
                        context_passages=context_passages,
                    ),
                },
            ],
        )

        return json.loads(response.choices[0].message.content)

    def _compute_median_scores(self, run_results: list[dict]) -> tuple[dict, str]:
        """Compute median scores from multiple runs. Returns (dimension_scores, overall_assessment)."""
        dimension_scores = {}
        for dim in CREDIBILITY_DIMENSIONS:
            scores = []
            rationales = []
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
                dimension_scores[dim] = {"score": 0, "rationale": "Could not score", "all_run_scores": [], "agreement": False}

        overall = run_results[0].get("overall_assessment", "") if run_results else ""
        return dimension_scores, overall

    def _classify_claim(self, claim: dict, dimension_scores: dict, overall: str) -> dict:
        """Compute composite score and assign tier to a claim."""
        dim_values = [dimension_scores[d]["score"] for d in CREDIBILITY_DIMENSIONS if dimension_scores[d]["score"] is not None]
        composite = round(sum(dim_values) / len(dim_values), 2) if dim_values else 0.0

        tier = "symbolic"
        for tier_name, (low, high) in TIER_THRESHOLDS.items():
            if low <= composite < high:
                tier = tier_name
                break
        if composite >= TIER_THRESHOLDS["substantive"][0]:
            tier = "substantive"

        claim["credibility_scores"] = dimension_scores
        claim["composite_score"] = composite
        claim["credibility_tier"] = tier
        claim["overall_assessment"] = overall
        return claim

    def score_claim(self, claim: dict, all_claims: list[dict]) -> dict:
        """
        Score a single claim using 3-run median scoring (synchronous).
        Returns the claim dict with credibility_scores populated.
        """
        if not claim.get("sdg_mappings"):
            claim["credibility_scores"] = {}
            claim["composite_score"] = None
            claim["credibility_tier"] = None
            return claim

        context = self._find_context_passages(claim, all_claims)

        run_results = []
        for _ in range(SCORING_RUNS):
            try:
                result = self._score_single_run(claim, context)
                run_results.append(result)
            except Exception as e:
                print(f"    Scoring run failed for {claim['claim_id']}: {e}")

        if not run_results:
            claim["credibility_scores"] = {}
            claim["composite_score"] = None
            claim["credibility_tier"] = "error"
            return claim

        dimension_scores, overall = self._compute_median_scores(run_results)
        return self._classify_claim(claim, dimension_scores, overall)

    def process_all_claims(self, claims: list[dict]) -> list[dict]:
        """Score all claims that have SDG mappings (sequential)."""
        mapped_claims = [c for c in claims if c.get("sdg_mappings")]
        unmapped_claims = [c for c in claims if not c.get("sdg_mappings")]

        print(f"\n{'='*60}")
        print(f"PHASE 3: Credibility Scoring ({len(mapped_claims)} mapped claims)")
        print(f"{'='*60}")
        print(f"  Skipping {len(unmapped_claims)} unmapped claims")

        scored_claims = []
        for claim in tqdm(mapped_claims, desc="  Scoring credibility"):
            scored = self.score_claim(claim, claims)
            scored_claims.append(scored)

        # Add back unmapped claims (unscored)
        for claim in unmapped_claims:
            claim["credibility_scores"] = {}
            claim["composite_score"] = None
            claim["credibility_tier"] = None
            scored_claims.append(claim)

        self._print_summary(scored_claims)
        return scored_claims

    # ── Async (parallel) methods ──────────────────────────────────────────

    async def _async_score_single_run(self, async_client: AsyncOpenAI, claim: dict,
                                       context_passages: str, semaphore: asyncio.Semaphore,
                                       max_retries: int = 3) -> dict:
        """Perform one async scoring run with retry and rate limiting."""
        for attempt in range(max_retries):
            async with semaphore:
                try:
                    response = await async_client.chat.completions.create(
                        model=self.model,
                        temperature=SCORING_TEMPERATURE,
                        response_format={"type": "json_object"},
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an expert sustainability report analyst. Score claims strictly according to the rubric. Always respond with valid JSON.",
                            },
                            {
                                "role": "user",
                                "content": CREDIBILITY_SCORING_PROMPT.format(
                                    claim_text=claim["claim_text"],
                                    section=claim.get("section", "Unknown"),
                                    page=claim.get("page", "Unknown"),
                                    company=claim.get("company", "Unknown"),
                                    sector=claim.get("sector", "Unknown"),
                                    report_year=claim.get("report_year", "Unknown"),
                                    context_passages=context_passages,
                                ),
                            },
                        ],
                    )
                    return json.loads(response.choices[0].message.content)
                except Exception as e:
                    if "rate_limit" in str(e).lower() or "429" in str(e):
                        wait = 2 ** (attempt + 1)
                        print(f"    Rate limited, waiting {wait}s...")
                        await asyncio.sleep(wait)
                    elif attempt == max_retries - 1:
                        print(f"    Scoring run failed for {claim['claim_id']}: {e}")
                        return None
                    else:
                        await asyncio.sleep(1)
        return None

    async def _async_score_claim(self, async_client: AsyncOpenAI, claim: dict,
                                  all_claims: list[dict], semaphore: asyncio.Semaphore) -> dict:
        """Score a single claim asynchronously with 3-run median."""
        if not claim.get("sdg_mappings"):
            claim["credibility_scores"] = {}
            claim["composite_score"] = None
            claim["credibility_tier"] = None
            return claim

        context = self._find_context_passages(claim, all_claims)

        # Run all scoring runs concurrently for this claim
        run_tasks = [
            self._async_score_single_run(async_client, claim, context, semaphore)
            for _ in range(SCORING_RUNS)
        ]
        run_results_raw = await asyncio.gather(*run_tasks)
        run_results = [r for r in run_results_raw if r is not None]

        if not run_results:
            claim["credibility_scores"] = {}
            claim["composite_score"] = None
            claim["credibility_tier"] = "error"
            return claim

        dimension_scores, overall = self._compute_median_scores(run_results)
        return self._classify_claim(claim, dimension_scores, overall)

    async def process_all_claims_async(self, claims: list[dict], concurrency: int = 5) -> list[dict]:
        """Score all claims with parallel API calls and rate limiting."""
        from tqdm.asyncio import tqdm as atqdm

        mapped_claims = [c for c in claims if c.get("sdg_mappings")]
        unmapped_claims = [c for c in claims if not c.get("sdg_mappings")]

        print(f"\n{'='*60}")
        print(f"PHASE 3: Credibility Scoring ({len(mapped_claims)} mapped claims, concurrency={concurrency})")
        print(f"{'='*60}")
        print(f"  Skipping {len(unmapped_claims)} unmapped claims")
        print(f"  Total API calls: ~{len(mapped_claims) * SCORING_RUNS} ({SCORING_RUNS} runs × {len(mapped_claims)} claims)")

        async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        semaphore = asyncio.Semaphore(concurrency)

        try:
            tasks = [
                self._async_score_claim(async_client, claim, claims, semaphore)
                for claim in mapped_claims
            ]

            scored_claims = []
            for coro in atqdm(asyncio.as_completed(tasks), total=len(tasks), desc="  Scoring credibility"):
                result = await coro
                scored_claims.append(result)
        finally:
            await async_client.close()

        # Restore original order
        claim_order = {c["claim_id"]: i for i, c in enumerate(mapped_claims)}
        scored_claims.sort(key=lambda c: claim_order.get(c["claim_id"], 0))

        # Add back unmapped claims
        for claim in unmapped_claims:
            claim["credibility_scores"] = {}
            claim["composite_score"] = None
            claim["credibility_tier"] = None
            scored_claims.append(claim)

        self._print_summary(scored_claims)
        return scored_claims

    def _print_summary(self, scored_claims: list[dict]):
        """Print scoring summary stats."""
        tiers = [c["credibility_tier"] for c in scored_claims if c["credibility_tier"] and c["credibility_tier"] != "error"]
        if tiers:
            print(f"\n  Credibility distribution:")
            for tier_name in ["symbolic", "partially_substantive", "substantive"]:
                count = tiers.count(tier_name)
                pct = count / len(tiers) * 100
                print(f"    {tier_name}: {count} ({pct:.1f}%)")

            scores = [c["composite_score"] for c in scored_claims if c["composite_score"] is not None]
            print(f"\n  Mean composite score: {sum(scores)/len(scores):.2f}")
