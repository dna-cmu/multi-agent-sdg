"""
Phase 2: SDG Target Mapping (Mapper Agent)

This agent maps each extracted claim to specific SDG targets (169 targets)
using a two-stage approach: goal-level screening → target-level mapping.

Supports both sequential and parallel (async) processing.
"""

import json
import asyncio
from openai import OpenAI, AsyncOpenAI

from config.settings import OPENAI_API_KEY, PRIMARY_MODEL, CONFIDENCE_THRESHOLD
from prompts.sdg_mapping import GOAL_SCREENING_PROMPT, TARGET_MAPPING_PROMPT
from utils.sdg_targets import SDG_GOALS, get_targets_for_goal


class MapperAgent:
    """Phase 2 agent: maps claims to SDG targets."""

    def __init__(self):
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = PRIMARY_MODEL

    def screen_goals(self, claim_text: str) -> list[dict]:
        """Stage 1: Identify candidate SDG goals (1-3) for a claim."""
        response = self.openai_client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are an SDG classification expert. Always respond with valid JSON."},
                {"role": "user", "content": GOAL_SCREENING_PROMPT.format(claim_text=claim_text)},
            ],
        )
        parsed = json.loads(response.choices[0].message.content)
        return parsed.get("candidate_goals", [])

    def map_to_targets(self, claim_text: str, goal_number: int) -> list[dict]:
        """Stage 2: Map claim to specific targets within a goal."""
        goal_info = SDG_GOALS.get(goal_number, {})
        goal_title = goal_info.get("title", f"SDG {goal_number}")
        targets = get_targets_for_goal(goal_number)

        targets_text = "\n".join(
            [f"  Target {t['id']}: {t['description']}" for t in targets]
        )

        response = self.openai_client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are an SDG target-level classification expert. Always respond with valid JSON."},
                {"role": "user", "content": TARGET_MAPPING_PROMPT.format(
                    claim_text=claim_text,
                    goal_number=goal_number,
                    goal_title=goal_title,
                    targets_text=targets_text,
                )},
            ],
        )

        parsed = json.loads(response.choices[0].message.content)
        mappings = parsed.get("mappings", [])

        # Filter to targets above confidence threshold
        return [m for m in mappings if m.get("relevant") and m.get("confidence", 0) >= CONFIDENCE_THRESHOLD]

    def process_claim(self, claim: dict) -> dict:
        """Map a single claim to SDG targets. Returns updated claim dict."""
        claim_text = claim["claim_text"]

        # Stage 1: Goal screening
        candidates = self.screen_goals(claim_text)

        if not candidates:
            claim["sdg_mappings"] = []
            return claim

        # Stage 2: Target mapping for each candidate goal
        all_mappings = []
        for candidate in candidates:
            goal_num = candidate.get("goal")
            if goal_num:
                target_mappings = self.map_to_targets(claim_text, goal_num)
                for tm in target_mappings:
                    all_mappings.append({
                        "goal": goal_num,
                        "target": tm.get("target"),
                        "confidence": tm.get("confidence"),
                        "rationale": tm.get("rationale"),
                    })

        claim["sdg_mappings"] = all_mappings
        return claim

    def process_all_claims(self, claims: list[dict]) -> list[dict]:
        """Map all claims to SDG targets (sequential)."""
        from tqdm import tqdm

        print(f"\n{'='*60}")
        print(f"PHASE 2: SDG Target Mapping ({len(claims)} claims)")
        print(f"{'='*60}")

        mapped_claims = []
        for claim in tqdm(claims, desc="  Mapping claims to SDG targets"):
            mapped = self.process_claim(claim)
            mapped_claims.append(mapped)

        # Summary stats
        claims_with_mappings = sum(1 for c in mapped_claims if c["sdg_mappings"])
        total_mappings = sum(len(c["sdg_mappings"]) for c in mapped_claims)
        print(f"\n  Claims with SDG mappings: {claims_with_mappings}/{len(mapped_claims)}")
        print(f"  Total target-level mappings: {total_mappings}")

        return mapped_claims

    # ── Async (parallel) methods ──────────────────────────────────────────

    async def _async_screen_goals(self, async_client: AsyncOpenAI, claim_text: str,
                                   semaphore: asyncio.Semaphore, max_retries: int = 3) -> list[dict]:
        """Async Stage 1: Identify candidate SDG goals."""
        for attempt in range(max_retries):
            async with semaphore:
                try:
                    response = await async_client.chat.completions.create(
                        model=self.model,
                        temperature=0.1,
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": "You are an SDG classification expert. Always respond with valid JSON."},
                            {"role": "user", "content": GOAL_SCREENING_PROMPT.format(claim_text=claim_text)},
                        ],
                    )
                    parsed = json.loads(response.choices[0].message.content)
                    return parsed.get("candidate_goals", [])
                except Exception as e:
                    if "rate_limit" in str(e).lower() or "429" in str(e):
                        wait = 2 ** attempt
                        await asyncio.sleep(wait)
                    elif attempt == max_retries - 1:
                        print(f"    Goal screening failed: {e}")
                        return []
                    else:
                        await asyncio.sleep(1)
        return []

    async def _async_map_to_targets(self, async_client: AsyncOpenAI, claim_text: str,
                                     goal_number: int, semaphore: asyncio.Semaphore,
                                     max_retries: int = 3) -> list[dict]:
        """Async Stage 2: Map claim to targets within a goal."""
        goal_info = SDG_GOALS.get(goal_number, {})
        goal_title = goal_info.get("title", f"SDG {goal_number}")
        targets = get_targets_for_goal(goal_number)
        targets_text = "\n".join([f"  Target {t['id']}: {t['description']}" for t in targets])

        for attempt in range(max_retries):
            async with semaphore:
                try:
                    response = await async_client.chat.completions.create(
                        model=self.model,
                        temperature=0.1,
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": "You are an SDG target-level classification expert. Always respond with valid JSON."},
                            {"role": "user", "content": TARGET_MAPPING_PROMPT.format(
                                claim_text=claim_text,
                                goal_number=goal_number,
                                goal_title=goal_title,
                                targets_text=targets_text,
                            )},
                        ],
                    )
                    parsed = json.loads(response.choices[0].message.content)
                    mappings = parsed.get("mappings", [])
                    return [m for m in mappings if m.get("relevant") and m.get("confidence", 0) >= CONFIDENCE_THRESHOLD]
                except Exception as e:
                    if "rate_limit" in str(e).lower() or "429" in str(e):
                        wait = 2 ** attempt
                        await asyncio.sleep(wait)
                    elif attempt == max_retries - 1:
                        print(f"    Target mapping failed for goal {goal_number}: {e}")
                        return []
                    else:
                        await asyncio.sleep(1)
        return []

    async def _async_process_claim(self, async_client: AsyncOpenAI, claim: dict,
                                    semaphore: asyncio.Semaphore) -> dict:
        """Map a single claim to SDG targets asynchronously."""
        claim_text = claim["claim_text"]

        candidates = await self._async_screen_goals(async_client, claim_text, semaphore)

        if not candidates:
            claim["sdg_mappings"] = []
            return claim

        # Run target mapping for all candidate goals concurrently
        target_tasks = []
        for candidate in candidates:
            goal_num = candidate.get("goal")
            if goal_num:
                target_tasks.append(
                    self._async_map_to_targets(async_client, claim_text, goal_num, semaphore)
                )

        target_results = await asyncio.gather(*target_tasks)

        all_mappings = []
        for i, candidate in enumerate([c for c in candidates if c.get("goal")]):
            goal_num = candidate["goal"]
            if i < len(target_results):
                for tm in target_results[i]:
                    all_mappings.append({
                        "goal": goal_num,
                        "target": tm.get("target"),
                        "confidence": tm.get("confidence"),
                        "rationale": tm.get("rationale"),
                    })

        claim["sdg_mappings"] = all_mappings
        return claim

    async def process_all_claims_async(self, claims: list[dict], concurrency: int = 5) -> list[dict]:
        """Map all claims to SDG targets (parallel with rate limiting)."""
        from tqdm.asyncio import tqdm as atqdm

        print(f"\n{'='*60}")
        print(f"PHASE 2: SDG Target Mapping ({len(claims)} claims, concurrency={concurrency})")
        print(f"{'='*60}")

        async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        semaphore = asyncio.Semaphore(concurrency)

        try:
            tasks = [self._async_process_claim(async_client, claim, semaphore) for claim in claims]
            mapped_claims = []
            for coro in atqdm(asyncio.as_completed(tasks), total=len(tasks), desc="  Mapping claims to SDG targets"):
                result = await coro
                mapped_claims.append(result)
        finally:
            await async_client.close()

        # Restore original order (as_completed returns in completion order)
        claim_order = {c["claim_id"]: i for i, c in enumerate(claims)}
        mapped_claims.sort(key=lambda c: claim_order.get(c["claim_id"], 0))

        # Summary stats
        claims_with_mappings = sum(1 for c in mapped_claims if c["sdg_mappings"])
        total_mappings = sum(len(c["sdg_mappings"]) for c in mapped_claims)
        print(f"\n  Claims with SDG mappings: {claims_with_mappings}/{len(mapped_claims)}")
        print(f"  Total target-level mappings: {total_mappings}")

        return mapped_claims
