"""
Section-diverse retrieval utilities.

Used by the expert validation workbook builder to surface cross-references
that genuinely span different sections of a report — addressing the
methodological limitation identified in v3 (Column H clustered within
the same section as the source claim, making the Consistency dimension
effectively impossible to score).

Design principles:
- Candidates are ranked by embedding cosine similarity (OpenAI
  text-embedding-3-small), not bag-of-words overlap.
- Retrieval has explicit targets (default: 3 cross-section + 2 same-section)
  but NEVER pads below a relevance floor. When the floor cannot be met,
  fewer references are returned and a flag explains the absence.
- Embeddings are cached to disk per report so reruns are free.
"""

from __future__ import annotations

import hashlib
import json
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np
from openai import OpenAI

from config.settings import OPENAI_API_KEY, OUTPUTS_DIR

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# OpenAI's text-embedding-3-small has a hard 8191-token input limit per text.
# Truncate before sending so a single oversized ADE chunk (e.g. a giant table
# or figure caption) doesn't fail the whole batch. ~8000 chars stays safely
# under the token limit for English text.
MAX_INPUT_CHARS = 8000

# Relevance floor — cosine similarities below this are treated as "not related".
# For text-embedding-3-small, random business-English pairs sit around 0.2-0.3;
# vaguely related topics are ~0.35-0.45; closely related ~0.5+.
DEFAULT_MIN_SIMILARITY = 0.35

# Retrieval targets: we *aim* for this many, but do not pad.
DEFAULT_CROSS_SECTION_TARGET = 3
DEFAULT_SAME_SECTION_TARGET = 2

EMBED_CACHE_DIR = OUTPUTS_DIR / "embeddings"
EMBED_CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class RetrievedRef:
    """A single retrieved reference claim with its similarity score."""

    claim_id: str
    claim_text: str
    section: str
    page: int | str
    similarity: float
    is_cross_section: bool
    sdg_mappings: list = field(default_factory=list)


@dataclass
class RetrievalResult:
    """Output of retrieve_section_diverse_refs for a single sample claim."""

    cross_section: list[RetrievedRef]
    same_section: list[RetrievedRef]
    flags: list[str]

    @property
    def all_refs(self) -> list[RetrievedRef]:
        """Both lists concatenated (cross-section first, then same-section)."""
        return list(self.cross_section) + list(self.same_section)


# ── Unified "chunk-aware" retrieval (v5) ────────────────────────────────────


@dataclass
class MixedRef:
    """
    A single retrieved reference, which may be either a claim (from the
    extracted claims pool) or a raw text chunk (from the ADE chunks pool).
    """

    source_type: str            # "claim" or "chunk"
    id: str                     # claim_id or chunk_id
    text: str                   # claim_text or chunk markdown
    section: str                # resolved section (chunks are looked up by page)
    page: int | str
    similarity: float
    is_cross_section: bool
    chunk_type: str | None = None  # "chunkText" / "chunkTable" / ... for chunks
    sdg_mappings: list = field(default_factory=list)  # claims only


@dataclass
class MixedResult:
    """Result bundle for chunk-aware retrieval."""

    cross_section: list[MixedRef]
    same_section: list[MixedRef]
    flags: list[str]

    @property
    def all_refs(self) -> list[MixedRef]:
        return list(self.cross_section) + list(self.same_section)


# ── Embeddings with per-report caching ──────────────────────────────────────

_client: OpenAI | None = None


def _openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def _cache_key(report_key: str) -> Path:
    """Cache filename for a given report. Returns the pickle path."""
    safe = hashlib.sha1(report_key.encode()).hexdigest()[:16]
    return EMBED_CACHE_DIR / f"{safe}.pkl"


def _load_cache(report_key: str) -> dict[str, np.ndarray]:
    path = _cache_key(report_key)
    if not path.exists():
        return {}
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return {}


def _save_cache(report_key: str, cache: dict[str, np.ndarray]) -> None:
    path = _cache_key(report_key)
    with open(path, "wb") as f:
        pickle.dump(cache, f)


def _text_hash(text: str) -> str:
    """Stable per-text hash, used as the cache key inside a report."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def embed_texts(
    texts: list[str],
    report_key: str,
    batch_size: int = 256,
) -> np.ndarray:
    """
    Embed a list of texts using OpenAI text-embedding-3-small.
    Results are cached on disk keyed by (report_key, text hash). Repeat calls
    with the same text under the same report_key hit the cache.

    Returns a (len(texts), EMBEDDING_DIM) numpy array, row-aligned with `texts`.
    """
    if not texts:
        return np.zeros((0, EMBEDDING_DIM), dtype=np.float32)

    cache = _load_cache(report_key)
    hashes = [_text_hash(t) for t in texts]

    # Which texts are already cached?
    to_fetch_idx = [i for i, h in enumerate(hashes) if h not in cache]
    to_fetch_texts = [texts[i] for i in to_fetch_idx]

    # Batch-call OpenAI for the ones we don't have. Truncate each text to stay
    # under the 8191-token input limit; the cache key is on the *original*
    # untruncated text so future hits on shorter variants still work.
    if to_fetch_texts:
        client = _openai_client()
        safe_to_fetch = [
            t if len(t) <= MAX_INPUT_CHARS else t[:MAX_INPUT_CHARS]
            for t in to_fetch_texts
        ]
        for start in range(0, len(safe_to_fetch), batch_size):
            chunk = safe_to_fetch[start : start + batch_size]
            chunk_idx = to_fetch_idx[start : start + batch_size]
            response = client.embeddings.create(model=EMBEDDING_MODEL, input=chunk)
            for offset, item in enumerate(response.data):
                original_i = chunk_idx[offset]
                cache[hashes[original_i]] = np.asarray(item.embedding, dtype=np.float32)
        _save_cache(report_key, cache)

    # Assemble result in original order
    out = np.stack([cache[h] for h in hashes], axis=0)
    return out


# ── Similarity and retrieval ────────────────────────────────────────────────


def cosine_similarity(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Cosine similarity between a 1-D query and rows of a 2-D matrix."""
    q = query / (np.linalg.norm(query) + 1e-12)
    m_norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-12
    m = matrix / m_norms
    return (m @ q).astype(np.float32)


def retrieve_section_diverse_refs(
    sample_claim: dict,
    pool: Iterable[dict],
    report_key: str,
    cross_section_target: int = DEFAULT_CROSS_SECTION_TARGET,
    same_section_target: int = DEFAULT_SAME_SECTION_TARGET,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> RetrievalResult:
    """
    Find cross-references for `sample_claim` in a pool of candidate claims
    (all other claims from the same report).

    Retrieval policy:
    1. Embed the sample claim and all candidates (with caching).
    2. Rank candidates by cosine similarity, DESC.
    3. Drop any candidate below `min_similarity` (the relevance floor).
    4. Fill the cross-section slots first (up to `cross_section_target`).
       Then fill the same-section slots (up to `same_section_target`).
    5. If either slot can't be filled to its target, return fewer and add
       a flag explaining what was absent — do NOT lower the threshold.

    Parameters
    ----------
    sample_claim : dict
        The claim being scored. Must contain at least ``claim_id``, ``claim_text``,
        and ``section``. Any other fields are ignored.
    pool : iterable of dict
        Candidate claims from the same source report. Each must contain
        ``claim_id``, ``claim_text``, ``section``, and ``page``.
    report_key : str
        A stable identifier for this report (e.g. the ``source_file`` value).
        Used to namespace the embedding cache so multiple reports can be
        embedded without keys colliding.

    Returns
    -------
    RetrievalResult
        Structured result with cross-section refs, same-section refs, and a
        list of human-readable flags describing what was or wasn't found.
    """
    claim_section = sample_claim.get("section", "")
    query_text = sample_claim["claim_text"]
    query_id = sample_claim["claim_id"]

    # Exclude the claim itself from the pool
    candidates = [c for c in pool if c.get("claim_id") != query_id]

    if not candidates:
        return RetrievalResult(
            cross_section=[],
            same_section=[],
            flags=["Source report contains no other claims to compare against."],
        )

    # Embed the query + all candidates in one cache-aware batch
    all_texts = [query_text] + [c["claim_text"] for c in candidates]
    all_embs = embed_texts(all_texts, report_key=report_key)
    query_emb = all_embs[0]
    candidate_embs = all_embs[1:]

    # Rank by similarity
    sims = cosine_similarity(query_emb, candidate_embs)
    order = np.argsort(-sims)  # descending

    # Walk the ranking and fill slots according to section
    cross_section: list[RetrievedRef] = []
    same_section: list[RetrievedRef] = []

    for idx in order:
        sim = float(sims[idx])
        if sim < min_similarity:
            break  # sorted, so everything beyond this is also below the floor

        cand = candidates[idx]
        cand_section = cand.get("section", "")
        is_cross = cand_section != claim_section

        ref = RetrievedRef(
            claim_id=cand["claim_id"],
            claim_text=cand["claim_text"],
            section=cand_section,
            page=cand.get("page", "?"),
            similarity=sim,
            is_cross_section=is_cross,
            sdg_mappings=cand.get("sdg_mappings", []),
        )

        if is_cross and len(cross_section) < cross_section_target:
            cross_section.append(ref)
        elif (not is_cross) and len(same_section) < same_section_target:
            same_section.append(ref)

        if (len(cross_section) >= cross_section_target
                and len(same_section) >= same_section_target):
            break

    # Build flags — we want absence of evidence to be visible, not swept up
    flags: list[str] = []

    if len(cross_section) == 0:
        flags.append(
            f"No cross-section references above similarity {min_similarity:.2f}. "
            f"This topic appears only in section '{claim_section}' within this report."
        )
    elif len(cross_section) < cross_section_target:
        flags.append(
            f"Only {len(cross_section)} of {cross_section_target} target cross-section references "
            f"met the similarity threshold ({min_similarity:.2f})."
        )

    if len(same_section) == 0:
        flags.append(
            f"No other claims in section '{claim_section}' met the similarity "
            f"threshold ({min_similarity:.2f})."
        )
    elif len(same_section) < same_section_target:
        flags.append(
            f"Only {len(same_section)} of {same_section_target} target same-section references "
            f"met the similarity threshold ({min_similarity:.2f})."
        )

    return RetrievalResult(cross_section=cross_section, same_section=same_section, flags=flags)


# ── Convenience: load a report's claim pool from its phase1 / full JSON ─────


def load_pool_from_full_json(path: str | Path) -> list[dict]:
    """Load the claims list from a `..._full.json` or `..._phase1.json`."""
    with open(path) as f:
        data = json.load(f)
    return data.get("claims", [])


# ── Chunk-aware retrieval (v5) ──────────────────────────────────────────────


def resolve_chunk_section(page: int | None, sections: list[dict]) -> str:
    """
    Given a page number and a report's sections list (from the phase1 / full
    JSON: [{"section_title": ..., "start_page": ..., "end_page": ...}, ...]),
    return the section title that contains that page.

    If multiple sections contain the page (ranges overlap in the raw metadata),
    prefer the smallest / most specific range. If none match, return "Unmapped".
    """
    if page is None:
        return "Unmapped"
    candidates = [
        s for s in sections
        if s.get("start_page") is not None
        and s.get("end_page") is not None
        and s["start_page"] <= page <= s["end_page"]
    ]
    if not candidates:
        return "Unmapped"
    # Prefer the smallest (most specific) range
    candidates.sort(key=lambda s: (s["end_page"] - s["start_page"], s.get("level", 99)))
    return candidates[0].get("section_title", "Unmapped")


def retrieve_chunk_aware_refs(
    sample_claim: dict,
    claims_pool: list[dict],
    chunks_pool: list[dict],
    sections: list[dict],
    report_key: str,
    cross_section_target: int = DEFAULT_CROSS_SECTION_TARGET,
    same_section_target: int = DEFAULT_SAME_SECTION_TARGET,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> MixedResult:
    """
    Chunk-aware retrieval. Pools BOTH extracted claims AND ADE text chunks,
    ranks them together by cosine similarity, and enforces the usual
    cross-section targets without padding.

    Parameters
    ----------
    sample_claim : dict
        The claim being scored. Needs ``claim_id``, ``claim_text``, ``section``.
    claims_pool : list of dict
        All other claims in the same report (same shape as the sample claim).
    chunks_pool : list of dict
        ADE chunks from the same report. Each must have ``chunk_id``, ``text``,
        ``page``, and ``type`` (from extract_chunks.py output format).
    sections : list of dict
        The report's sections list — used to map each chunk's page to a
        section title for the cross-section determination.
    report_key : str
        Stable per-report identifier for the embedding cache.

    Returns
    -------
    MixedResult with cross_section / same_section lists of MixedRef, plus flags.
    """
    claim_section = sample_claim.get("section", "")
    query_text = sample_claim["claim_text"]
    query_id = sample_claim["claim_id"]

    # ── Build the unified candidate list ──────────────────────────────────
    # Each entry: (text, metadata-dict). We track metadata so we can rebuild
    # the MixedRef after ranking.
    cand_texts: list[str] = []
    cand_meta: list[dict] = []

    for c in claims_pool:
        if c.get("claim_id") == query_id:
            continue
        cand_texts.append(c["claim_text"])
        cand_meta.append({
            "source_type": "claim",
            "id": c["claim_id"],
            "text": c["claim_text"],
            "section": c.get("section", ""),
            "page": c.get("page", "?"),
            "sdg_mappings": c.get("sdg_mappings", []),
            "chunk_type": None,
        })

    # Drop chunks that literally restate a claim's text — they carry no new
    # signal and would dominate the top ranks. A cheap equality check is fine;
    # we don't need perfect dedup.
    claim_texts_set = {c["claim_text"].strip() for c in claims_pool}
    for ch in chunks_pool:
        text = (ch.get("text") or "").strip()
        if not text or text in claim_texts_set:
            continue
        page = ch.get("page")
        cand_texts.append(text)
        cand_meta.append({
            "source_type": "chunk",
            "id": ch.get("chunk_id", ""),
            "text": text,
            "section": resolve_chunk_section(page, sections),
            "page": page if page is not None else "?",
            "sdg_mappings": [],
            "chunk_type": ch.get("type"),
        })

    if not cand_texts:
        return MixedResult(
            cross_section=[], same_section=[],
            flags=["Source report has no claims or chunks to compare against."],
        )

    # ── Embed query + all candidates (cached) ─────────────────────────────
    all_texts = [query_text] + cand_texts
    all_embs = embed_texts(all_texts, report_key=report_key)
    query_emb = all_embs[0]
    cand_embs = all_embs[1:]

    sims = cosine_similarity(query_emb, cand_embs)
    order = np.argsort(-sims)

    # ── Fill slots by section, same policy as claim-only retrieval ────────
    cross_refs: list[MixedRef] = []
    same_refs: list[MixedRef] = []
    # To avoid near-duplicates (two chunks with almost identical text from the
    # same page bleeding into the result), also skip any candidate whose text
    # is already represented at very high similarity to an accepted ref.
    accepted_texts: list[str] = []

    def is_near_duplicate(text: str) -> bool:
        t = text.strip()
        for existing in accepted_texts:
            if t == existing:
                return True
            # cheap approximate dedup: one is a prefix of the other and lengths
            # differ by less than 25%
            if t.startswith(existing[:60]) or existing.startswith(t[:60]):
                if abs(len(t) - len(existing)) / max(len(t), len(existing), 1) < 0.25:
                    return True
        return False

    for idx in order:
        sim = float(sims[idx])
        if sim < min_similarity:
            break

        meta = cand_meta[idx]
        if is_near_duplicate(meta["text"]):
            continue

        is_cross = meta["section"] != claim_section

        ref = MixedRef(
            source_type=meta["source_type"],
            id=meta["id"],
            text=meta["text"],
            section=meta["section"],
            page=meta["page"],
            similarity=sim,
            is_cross_section=is_cross,
            chunk_type=meta["chunk_type"],
            sdg_mappings=meta["sdg_mappings"],
        )

        if is_cross and len(cross_refs) < cross_section_target:
            cross_refs.append(ref)
            accepted_texts.append(meta["text"])
        elif (not is_cross) and len(same_refs) < same_section_target:
            same_refs.append(ref)
            accepted_texts.append(meta["text"])

        if len(cross_refs) >= cross_section_target and len(same_refs) >= same_section_target:
            break

    # ── Flags ─────────────────────────────────────────────────────────────
    flags: list[str] = []
    if len(cross_refs) == 0:
        flags.append(
            f"No cross-section references above similarity {min_similarity:.2f}. "
            f"This topic appears only in section '{claim_section}' within this report."
        )
    elif len(cross_refs) < cross_section_target:
        flags.append(
            f"Only {len(cross_refs)} of {cross_section_target} target cross-section references "
            f"met the similarity threshold ({min_similarity:.2f})."
        )

    if len(same_refs) == 0:
        flags.append(
            f"No other material in section '{claim_section}' met the similarity threshold "
            f"({min_similarity:.2f})."
        )
    elif len(same_refs) < same_section_target:
        flags.append(
            f"Only {len(same_refs)} of {same_section_target} target same-section references "
            f"met the similarity threshold ({min_similarity:.2f})."
        )

    return MixedResult(cross_section=cross_refs, same_section=same_refs, flags=flags)


def load_chunks_from_chunks_json(path: str | Path) -> list[dict]:
    """Load the chunks list from a `..._chunks.json` produced by extract_chunks.py."""
    with open(path) as f:
        data = json.load(f)
    return data.get("chunks", [])
