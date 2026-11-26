"""
retrieval_comparison.py — three-way retrieval comparison.

For each of the 63 v5 sample claims, run three retrieval pipelines and
record what each one surfaces as the top-5 cross-section / same-section
references. The pipelines:

  A. OPENAI_EMB    OpenAI text-embedding-3-small (closed, cached on disk)
  B. LOCAL_EMB     Nomic-Embed-Text-v1.5 served by LM Studio
  C. LLM_JUDGE     Qwen3-32B-MLX served by LM Studio acting as a relevance
                   judge over a top-50 pre-shortlist (pre-shortlist is
                   computed by averaging A and B's similarity scores so
                   neither method is privileged at the entry stage)

We then compute paired metrics:
  - top-5 set overlap (Jaccard) between each method pair
  - section-diversity agreement (does each method find ≥1 cross-section ref
    above floor for each claim?)
  - similarity score-rank correlation between A and B
  - per-claim disagreement audit (5 claims where pairs disagree most)

Outputs land in data/outputs/experiments/retrieval_comparison/.

Run on the host machine where LM Studio's server is reachable on
http://localhost:1234. Not runnable from a remote sandbox.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from openai import OpenAI

# Reuse the v5 retrieval primitives that already work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import OPENAI_API_KEY, OUTPUTS_DIR
from utils.retrieval import (
    DEFAULT_CROSS_SECTION_TARGET,
    DEFAULT_MIN_SIMILARITY,
    DEFAULT_SAME_SECTION_TARGET,
    cosine_similarity,
    embed_texts as _openai_embed_texts_raw,
    resolve_chunk_section,
)


def openai_embed_texts(texts: list[str], report_key: str) -> np.ndarray:
    """OpenAI embedding wrapper that truncates inputs to fit the 8191-token
    limit, mirroring what we do for the LM Studio embedder. Truncation is
    applied per-text before hashing, so the cache key reflects the actual
    string sent to the API (avoids false hits if the same chunk is later
    embedded under a different truncation policy)."""
    safe = [t[:EMBED_INPUT_MAX_CHARS] if len(t) > EMBED_INPUT_MAX_CHARS else t for t in texts]
    return _openai_embed_texts_raw(safe, report_key=report_key)

EXP_OUT_DIR = OUTPUTS_DIR / "experiments" / "retrieval_comparison"
EXP_OUT_DIR.mkdir(parents=True, exist_ok=True)

# LM Studio endpoint
LMSTUDIO_BASE_URL = "http://localhost:1234/v1"
LOCAL_EMBED_MODEL = "nomic-ai/text-embedding-nomic-embed-text-v1.5"
LOCAL_JUDGE_MODEL = "qwen3-32b-mlx"

# Number of candidates we pass to the LLM judge. 30 keeps the judge prompt
# under ~4K tokens, comfortable for an 8K-context Qwen load. If LM Studio
# is configured with a larger context window (16K+), this can be raised.
JUDGE_SHORTLIST_SIZE = 30

# Hard caps to avoid context-length errors on either endpoint:
EMBED_INPUT_MAX_CHARS = 8000   # nomic-embed max is 8192 tokens; chars / ~3 = tokens, so 8000 chars is safe
JUDGE_CANDIDATE_MAX_CHARS = 350  # 30 candidates × 350 chars × ~0.3 tok/char ≈ 3150 tokens

# LM Studio requires a strict json_schema (not the OpenAI-legacy "json_object"
# shorthand) for structured output. We give it the exact schema we expect.
JUDGE_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "candidate_scores",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "scores": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0, "maximum": 3},
                }
            },
            "required": ["scores"],
            "additionalProperties": False,
        },
    },
}


# ── LM Studio embedding (OpenAI-compatible API) ─────────────────────────────


def lmstudio_client() -> OpenAI:
    """
    LM Studio exposes the OpenAI Chat Completions and Embeddings APIs at
    localhost:1234. We use the official OpenAI Python SDK with a custom
    base_url; no key is needed but the SDK requires a non-empty string.
    """
    return OpenAI(base_url=LMSTUDIO_BASE_URL, api_key="lm-studio")


def _safe_for_embed(text: str) -> str:
    """Truncate to fit nomic-embed's 8192-token input limit with margin."""
    if not text:
        return ""
    if len(text) <= EMBED_INPUT_MAX_CHARS:
        return text
    return text[:EMBED_INPUT_MAX_CHARS]


def lmstudio_embed_texts(client: OpenAI, texts: list[str], batch_size: int = 32) -> np.ndarray:
    """Embed via LM Studio's /v1/embeddings endpoint, returning a (N, D) array."""
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    safe_texts = [_safe_for_embed(t) for t in texts]
    out: list[np.ndarray] = []
    for start in range(0, len(safe_texts), batch_size):
        chunk = safe_texts[start : start + batch_size]
        resp = client.embeddings.create(model=LOCAL_EMBED_MODEL, input=chunk)
        for item in resp.data:
            out.append(np.asarray(item.embedding, dtype=np.float32))
    return np.stack(out, axis=0)


# ── LLM-as-judge prompt ─────────────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """You are an expert sustainability-report analyst evaluating
which passages from a corporate sustainability report best CORROBORATE a specific
claim made elsewhere in the same report.

Corroboration means: the candidate passage provides supporting data, restates the
fact, references the same programme, gives a target the claim reports progress
against, or otherwise grounds the claim in other report content. Mere topical
similarity ("this passage is also about emissions") is NOT corroboration.

Your job: read the claim, then read each candidate passage, and assign each
candidate a relevance score:
  3 = strongly corroborates (data table with the figure, target the claim
      reports progress against, executive summary restating the fact)
  2 = related context that supports the claim's plausibility
  1 = topically similar but doesn't actually corroborate
  0 = unrelated or contradictory

Output strict JSON with one entry per candidate, in the order given:
{"scores": [3, 1, 2, 0, ...]}

Do NOT explain. Return JSON only.
"""


def _truncate(text: str, n: int = JUDGE_CANDIDATE_MAX_CHARS) -> str:
    text = text.strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def judge_rank(client: OpenAI, claim_text: str, candidates: list[dict],
               temperature: float = 0.0) -> list[int]:
    """
    Send claim + candidates to the LLM, get back a list of relevance scores
    (one int per candidate). Returns scores in candidate order.
    """
    cand_block = "\n".join(
        f"[{i+1}] {_truncate(c['text'])}"
        for i, c in enumerate(candidates)
    )
    user_prompt = (
        f"CLAIM:\n{claim_text.strip()}\n\n"
        f"CANDIDATES (return one score per candidate, in this order):\n{cand_block}\n\n"
        f"Return JSON only."
    )

    resp = client.chat.completions.create(
        model=LOCAL_JUDGE_MODEL,
        temperature=temperature,
        response_format=JUDGE_RESPONSE_FORMAT,
        max_tokens=400,  # generous: 50 ints + JSON wrapper fits in <100 tokens
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = resp.choices[0].message.content or "{}"
    try:
        parsed = json.loads(content)
        scores = parsed.get("scores", [])
    except json.JSONDecodeError:
        # If the model returned malformed JSON, fall back to neutral scores
        return [1] * len(candidates)
    # Pad / truncate to match candidate count
    if len(scores) < len(candidates):
        scores = list(scores) + [0] * (len(candidates) - len(scores))
    return [int(s) for s in scores[: len(candidates)]]


# ── Candidate-pool building (matches v5 builder) ────────────────────────────


def build_candidates(claim: dict, claims_pool: list[dict],
                     chunks_pool: list[dict], sections: list[dict]) -> list[dict]:
    """Return a unified candidate list (claims + chunks) for one claim, with section labels."""
    qid = claim["claim_id"]
    cands: list[dict] = []

    for c in claims_pool:
        if c.get("claim_id") == qid:
            continue
        cands.append({
            "source_type": "claim",
            "id": c["claim_id"],
            "text": c["claim_text"],
            "section": c.get("section", ""),
            "page": c.get("page", "?"),
        })

    claim_texts_set = {c["claim_text"].strip() for c in claims_pool}
    for ch in chunks_pool:
        text = (ch.get("text") or "").strip()
        if not text or text in claim_texts_set:
            continue
        cands.append({
            "source_type": "chunk",
            "id": ch.get("chunk_id", ""),
            "text": text,
            "section": resolve_chunk_section(ch.get("page"), sections),
            "page": ch.get("page") if ch.get("page") is not None else "?",
        })

    return cands


def select_top_with_diversity(scored: list[dict], claim_section: str,
                              cross_target: int, same_target: int,
                              min_score: float) -> dict:
    """
    Walk a sorted candidate list and fill cross-section + same-section slots,
    skipping near-duplicates. `scored` should already be in DESC score order.
    """
    cross: list[dict] = []
    same: list[dict] = []
    accepted_texts: list[str] = []

    def is_dup(t: str) -> bool:
        t = t.strip()
        for e in accepted_texts:
            if t == e or t.startswith(e[:60]) or e.startswith(t[:60]):
                if abs(len(t) - len(e)) / max(len(t), len(e), 1) < 0.25:
                    return True
        return False

    for c in scored:
        if c["score"] < min_score:
            break
        if is_dup(c["text"]):
            continue
        is_cross = c["section"] != claim_section
        if is_cross and len(cross) < cross_target:
            cross.append(c)
            accepted_texts.append(c["text"])
        elif (not is_cross) and len(same) < same_target:
            same.append(c)
            accepted_texts.append(c["text"])
        if len(cross) >= cross_target and len(same) >= same_target:
            break
    return {"cross_section": cross, "same_section": same}


# ── Per-method pipelines ────────────────────────────────────────────────────


def run_openai_pipeline(claim: dict, candidates: list[dict],
                        report_key: str) -> dict:
    """OpenAI embeddings + section diversity + relevance floor."""
    if not candidates:
        return {"cross_section": [], "same_section": []}
    texts = [claim["claim_text"]] + [c["text"] for c in candidates]
    embs = openai_embed_texts(texts, report_key=report_key)
    sims = cosine_similarity(embs[0], embs[1:])
    scored = []
    for c, s in zip(candidates, sims):
        scored.append({**c, "score": float(s)})
    scored.sort(key=lambda x: -x["score"])
    return select_top_with_diversity(
        scored, claim.get("section", ""),
        DEFAULT_CROSS_SECTION_TARGET, DEFAULT_SAME_SECTION_TARGET,
        DEFAULT_MIN_SIMILARITY,
    )


def run_local_pipeline(client: OpenAI, claim: dict, candidates: list[dict]) -> dict:
    """Local nomic embeddings + section diversity. Same algorithm as OpenAI pipeline."""
    if not candidates:
        return {"cross_section": [], "same_section": []}
    texts = [claim["claim_text"]] + [c["text"] for c in candidates]
    embs = lmstudio_embed_texts(client, texts)
    sims = cosine_similarity(embs[0], embs[1:])
    scored = []
    for c, s in zip(candidates, sims):
        scored.append({**c, "score": float(s)})
    scored.sort(key=lambda x: -x["score"])
    # The local model produces similarities on a slightly different scale;
    # we use the same 0.35 floor for comparability. Adjust if needed.
    return select_top_with_diversity(
        scored, claim.get("section", ""),
        DEFAULT_CROSS_SECTION_TARGET, DEFAULT_SAME_SECTION_TARGET,
        DEFAULT_MIN_SIMILARITY,
    )


def run_judge_pipeline(client: OpenAI, claim: dict, candidates: list[dict],
                       report_key: str, shortlist_size: int = JUDGE_SHORTLIST_SIZE) -> dict:
    """
    LLM-as-judge over a pre-shortlist. We pre-shortlist by averaging OpenAI
    and nomic similarities so neither embedding method gets to bias the
    judge's input — the judge sees a balanced top-N from both perspectives.
    """
    if not candidates:
        return {"cross_section": [], "same_section": []}

    # OpenAI sims (cached)
    openai_texts = [claim["claim_text"]] + [c["text"] for c in candidates]
    openai_embs = openai_embed_texts(openai_texts, report_key=report_key)
    openai_sims = cosine_similarity(openai_embs[0], openai_embs[1:])

    # Local sims
    local_embs = lmstudio_embed_texts(client, openai_texts)
    local_sims = cosine_similarity(local_embs[0], local_embs[1:])

    # Combine: rank by mean of normalised sims
    def _norm(arr):
        m, s = float(arr.mean()), float(arr.std() + 1e-12)
        return (arr - m) / s
    combined = (_norm(openai_sims) + _norm(local_sims)) / 2.0
    order = np.argsort(-combined)
    shortlist_idx = list(order[:shortlist_size])
    shortlist = [candidates[i] for i in shortlist_idx]

    # Judge
    judge_scores = judge_rank(client, claim["claim_text"], shortlist)
    scored = []
    for c, score in zip(shortlist, judge_scores):
        scored.append({**c, "score": float(score)})
    scored.sort(key=lambda x: -x["score"])

    # Judge uses 0-3. We require score >= 2 (the judge considers it actually
    # supportive, not just topically similar). This is stricter than the
    # embedding floors and is the point — if the judge surfaces fewer items
    # than embeddings, that itself is a finding worth reporting.
    return select_top_with_diversity(
        scored, claim.get("section", ""),
        DEFAULT_CROSS_SECTION_TARGET, DEFAULT_SAME_SECTION_TARGET,
        min_score=2.0,
    )


# ── Metrics ─────────────────────────────────────────────────────────────────


def jaccard(a: list[dict], b: list[dict]) -> float:
    """Jaccard over the (source_type, id) pairs in two top-K lists."""
    sa = {(x["source_type"], x["id"]) for x in a}
    sb = {(x["source_type"], x["id"]) for x in b}
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# ── Main loop ───────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample", type=Path,
        default=OUTPUTS_DIR / "validation" / "expert_validation_sample_v2.json",
    )
    parser.add_argument("--full-dir", type=Path, default=OUTPUTS_DIR / "main" / "full")
    parser.add_argument("--chunks-dir", type=Path, default=OUTPUTS_DIR / "main" / "chunks")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit to first N sample claims (for quick smoke tests).")
    args = parser.parse_args()

    # Load sample
    with open(args.sample) as f:
        sample = json.load(f)
    sample_claims = sample["claims"] if isinstance(sample, dict) else sample
    if args.limit:
        sample_claims = sample_claims[: args.limit]
    print(f"Sample claims: {len(sample_claims)}")

    # Build report index keyed by company → (claims, sections, chunks)
    print("Indexing per-report data...")
    report_data: dict[str, dict] = {}
    for full_path in sorted(args.full_dir.glob("*_full.json")):
        with open(full_path) as f:
            full = json.load(f)
        meta = full.get("metadata", {}) or {}
        company = meta.get("company")
        if not company:
            continue
        stem = full_path.stem.replace("_full", "")
        chunks_path = args.chunks_dir / f"{stem}_chunks.json"
        chunks: list[dict] = []
        if chunks_path.exists():
            with open(chunks_path) as f:
                chunks = json.load(f).get("chunks", [])
        report_data[company] = {
            "claims": full.get("claims", []),
            "sections": full.get("sections", []),
            "chunks": chunks,
            "report_key": f"{stem}_exp",
        }
        print(f"  {company}: {len(full.get('claims', []))} claims, {len(chunks)} chunks")

    # Smoke-test the LM Studio server
    client = lmstudio_client()
    try:
        smoke = lmstudio_embed_texts(client, ["smoke test"])
        print(f"LM Studio embedding endpoint OK (dim={smoke.shape[1]})")
    except Exception as e:
        sys.exit(f"LM Studio embedding endpoint unreachable: {e}")
    try:
        r = client.chat.completions.create(
            model=LOCAL_JUDGE_MODEL,
            temperature=0.0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "smoke",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {"ok": {"type": "integer"}},
                        "required": ["ok"],
                        "additionalProperties": False,
                    },
                },
            },
            messages=[{"role": "user", "content": "Reply with JSON {\"ok\": 1}."}],
            max_tokens=30,
        )
        print(f"LM Studio chat endpoint OK ({len(r.choices[0].message.content or '')} chars)")
    except Exception as e:
        sys.exit(f"LM Studio chat endpoint unreachable: {e}")

    # Run all three pipelines per claim
    results: list[dict] = []
    t0 = time.time()
    for i, sc in enumerate(sample_claims, start=1):
        company = sc.get("company", "")
        claim_id = sc["claim_id"]
        if company not in report_data:
            print(f"  [{i:2}/{len(sample_claims)}] {claim_id}: SKIP (no report data)")
            continue
        d = report_data[company]

        # Enrich sample claim with section/page
        enriched = dict(sc)
        pool_by_id = {c["claim_id"]: c for c in d["claims"]}
        if not enriched.get("section"):
            enriched["section"] = pool_by_id.get(claim_id, {}).get("section", "")
        if "page" not in enriched:
            enriched["page"] = pool_by_id.get(claim_id, {}).get("page", "?")

        cands = build_candidates(enriched, d["claims"], d["chunks"], d["sections"])

        ti = time.time()
        try:
            r_openai = run_openai_pipeline(enriched, cands, d["report_key"])
            r_local = run_local_pipeline(client, enriched, cands)
            r_judge = run_judge_pipeline(client, enriched, cands, d["report_key"])
        except Exception as e:
            print(f"  [{i:2}/{len(sample_claims)}] {claim_id} ({company[:18]}): FAIL {type(e).__name__}: {e}")
            continue

        elapsed = time.time() - ti
        results.append({
            "claim_id": claim_id,
            "company": company,
            "claim_text": enriched["claim_text"],
            "claim_section": enriched.get("section", ""),
            "n_candidates": len(cands),
            "openai_emb": {
                "cross_section": r_openai["cross_section"],
                "same_section": r_openai["same_section"],
            },
            "local_emb": {
                "cross_section": r_local["cross_section"],
                "same_section": r_local["same_section"],
            },
            "llm_judge": {
                "cross_section": r_judge["cross_section"],
                "same_section": r_judge["same_section"],
            },
            "elapsed_seconds": round(elapsed, 1),
        })
        print(
            f"  [{i:2}/{len(sample_claims)}] {claim_id} ({company[:18]}): "
            f"OAI={len(r_openai['cross_section'])}c/{len(r_openai['same_section'])}s "
            f"LOCAL={len(r_local['cross_section'])}c/{len(r_local['same_section'])}s "
            f"JUDGE={len(r_judge['cross_section'])}c/{len(r_judge['same_section'])}s "
            f"({elapsed:.1f}s)"
        )

    print(f"\nProcessed {len(results)} claims in {time.time()-t0:.0f}s total.")

    # Compute paired metrics
    print("\nComputing pairwise metrics...")
    pairs = [("openai_emb", "local_emb"), ("openai_emb", "llm_judge"), ("local_emb", "llm_judge")]
    summary = {p: {"jaccard_top5": [], "section_div_match": 0} for p in pairs}

    for r in results:
        for a, b in pairs:
            top_a = r[a]["cross_section"] + r[a]["same_section"]
            top_b = r[b]["cross_section"] + r[b]["same_section"]
            summary[(a, b)]["jaccard_top5"].append(jaccard(top_a, top_b))
            cross_a = len(r[a]["cross_section"]) > 0
            cross_b = len(r[b]["cross_section"]) > 0
            if cross_a == cross_b:
                summary[(a, b)]["section_div_match"] += 1

    print(f"\n{'Pair':<30} {'Mean Jaccard':>14} {'Section-div agree':>18}")
    for a, b in pairs:
        js = summary[(a, b)]["jaccard_top5"]
        sda = summary[(a, b)]["section_div_match"] / len(js) if js else 0.0
        mean_j = sum(js) / len(js) if js else 0.0
        print(f"  {a} vs {b:<18} {mean_j:>14.3f} {sda:>18.3f}")

    # Top disagreements per pair
    disagreements = {}
    for a, b in pairs:
        scored = []
        for r in results:
            top_a = r[a]["cross_section"] + r[a]["same_section"]
            top_b = r[b]["cross_section"] + r[b]["same_section"]
            j = jaccard(top_a, top_b)
            scored.append({"claim_id": r["claim_id"], "company": r["company"], "jaccard": j})
        scored.sort(key=lambda x: x["jaccard"])
        disagreements[f"{a}_vs_{b}"] = scored[:10]

    # Save
    out_path = EXP_OUT_DIR / "results.json"
    with open(out_path, "w") as f:
        json.dump({
            "n_claims": len(results),
            "elapsed_seconds": round(time.time() - t0, 1),
            "summary": {f"{a}_vs_{b}": {
                "mean_jaccard_top5": round(
                    sum(summary[(a, b)]["jaccard_top5"]) / len(results) if results else 0.0, 4),
                "section_diversity_agreement": round(
                    summary[(a, b)]["section_div_match"] / len(results) if results else 0.0, 4),
            } for a, b in pairs},
            "top_disagreements": disagreements,
            "claim_results": results,
        }, f, indent=2, default=str)
    print(f"\nResults saved: {out_path}")


if __name__ == "__main__":
    main()
