"""Round 1 challenge set: purposive draw by claim WORDING (not by framework scores),
from the six held-out reports, excluding the representative 50 and the pilot 20.
Categories (priority order when a claim matches several):
  target       claim_type == 'target' (all)
  assurance    assurance / verification wording
  certification ISO-type or other certification wording
  standard     reporting-standard reference (GRI, IFRS S1/S2, TCFD, SBTi, ...)
Evidence packs rebuilt with the production V7 chunk-aware retrieval and the
existing embedding cache (no new embeddings are fetched; a cache miss aborts).
Usage (from repo root):  python3 scorer/build_challenge_set.py
"""
import sys, json, re, random, types, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
FW = ROOT / "sdg-credibility-framework"
sys.path.insert(0, str(FW))
# stub the OpenAI client: any cache miss must fail loudly, never call the API
if "openai" not in sys.modules:
    m = types.ModuleType("openai")
    class OpenAI:
        def __init__(self, *a, **k): raise RuntimeError("embedding cache miss: refusing to call OpenAI")
    m.OpenAI = OpenAI; sys.modules["openai"] = m
from utils.retrieval import retrieve_chunk_aware_refs, load_chunks_from_chunks_json

SEED = 20261020
QUOTA = {"target": 4, "assurance": 2, "certification": 2, "standard": 2}   # 21 Oct: was 4/4/3/3 (14 claims)
REPORTS = ["advanc-2024-SR-en", "CPN-2024-OR+SR-EN", "IVL-2024-SR-EN",
           "PTT-2024-OR+SR-EN", "PTTGC-2024-IR-EN", "SCC-2024-SR-EN"]
TYPES = {"commitment", "achievement", "metric", "policy", "alignment", "target"}
PAT = {
    "assurance": r"assur|verif|audited|third[- ]party|independent(ly)? (audit|assess|review|verif)",
    "certification": r"\bISO\s?\d{4,5}|certif|accredit",
    "standard": r"\bGRI\b|\bSASB\b|\bTCFD\b|\bISSB\b|IFRS S\d|GHG Protocol|\bTNFD\b|\bSBTi\b|Science[- ]Based Target",
}
OUT = FW / "data/outputs/revision"
# Eligibility for the assurance / certification / standard categories (added 21 Oct 2026):
# the claim must be the firm's own statement about its EXISTING data or practice, so that the
# reference can be tested as evidence for that claim. Excluded: (a) sentences extracted from the
# assurance provider's statement (section title contains "Assurance Statement"/"Assurance Report"),
# which are not company claims; (b) forward-looking commitments, which carry no existing data for an
# assurance, certification or standard reference to cover.
ASSURER_SECTION = re.compile(r"assurance (statement|report)", re.I)
THAI = re.compile(r"[\u0e00-\u0e7f]")
def eligible(c):
    return (not ASSURER_SECTION.search(str(c.get("section") or "")) and c.get("claim_type") != "commitment"
            and not THAI.search(c.get("claim_text") or ""))   # (c) English-only claim text (21 Oct, DNA: avoid language bias)

def main(check_uid=None):
    r1 = json.load(open(OUT / "round1_50_selection.json"))["claims"]
    p20 = json.load(open(OUT / "pilot20_selection.json"))
    excl = {c["uid"] for c in r1} | {c["uid"] for c in p20}
    reports = {}
    for r in REPORTS:
        v7 = json.load(open(FW / f"data/outputs/main/full_v7/{r}_full_v7.json"))
        full = json.load(open(FW / f"data/outputs/main/full/{r}_full.json"))
        chunks = load_chunks_from_chunks_json(FW / f"data/outputs/main/chunks/{r}_chunks.json")
        reports[r] = (v7, full, chunks)

    def pack_for(r, claim):
        v7, full, chunks = reports[r]
        res = retrieve_chunk_aware_refs(sample_claim=claim, claims_pool=full["claims"],
                                        chunks_pool=chunks, sections=full.get("sections", []),
                                        report_key=f"{r}_corpus_v7")
        pk = [[f"X{i+1}", "cross-section", x.section, x.page, x.text] for i, x in enumerate(res.cross_section)]
        pk += [[f"S{i+1}", "same-section", x.section, x.page, x.text] for i, x in enumerate(res.same_section)]
        return pk, list(res.flags)

    if check_uid:   # reproduce a stored round-1 pack to prove the procedure matches
        c0 = next(c for c in r1 if c["uid"] == check_uid); r, cid = check_uid.split("::")
        claim = next(c for c in reports[r][1]["claims"] if c["claim_id"] == cid)
        pk, fl = pack_for(r, claim)
        same = [p[:4] + [p[4].strip()] for p in pk] == [p[:4] + [p[4].strip()] for p in c0["pack"]]
        print("reproduces stored pack:", same); return

    pool = []
    for r in REPORTS:
        for c in reports[r][0]["claims"]:
            uid = f"{r}::{c['claim_id']}"
            if c.get("sdg_mappings") and c.get("claim_type") in TYPES and uid not in excl:
                pool.append((uid, r, c))
    pool.sort(key=lambda t: t[0])
    cat_of = {}
    for uid, r, c in pool:
        if c["claim_type"] == "target": cat_of[uid] = "target"; continue
        for k in ("assurance", "certification", "standard"):
            if re.search(PAT[k], c["claim_text"], re.I): cat_of[uid] = k; break
    rng = random.Random(SEED); chosen = []
    for k in ("target", "assurance", "certification", "standard"):
        cands = [t for t in pool if cat_of.get(t[0]) == k]
        rng.shuffle(cands)
        if k != "target":   # eligibility rule (21 Oct, before any rater saw Phase 2), applied after the shuffle so order is kept
            cands = [t for t in cands if eligible(t[2])]
        chosen += [(k, t) for t in cands[:QUOTA[k]]]
        print(k, "eligible", len(cands), "drawn", min(len(cands), QUOTA[k]))
    out = []
    for k, (uid, r, c) in chosen:
        full_claim = next(fc for fc in reports[r][1]["claims"] if fc["claim_id"] == c["claim_id"])
        pk, fl = pack_for(r, full_claim)
        sc = c.get("credibility_scores", {})
        g = lambda d: (sc.get(d) or {}).get("score") if isinstance(sc.get(d), dict) else sc.get(d)
        out.append({"uid": uid, "challenge_category": k, "company": c.get("company"), "sector": c.get("sector"),
                    "report": r, "page": c.get("page"), "section": c.get("section"), "claim_type": c["claim_type"],
                    "claim_text": c["claim_text"],
                    "sdg_targets": ", ".join(sorted({m.get("target_id") or m.get("target") or str(m) for m in c["sdg_mappings"]})),
                    "pack": pk, "flags": fl,
                    "v7": {d[0].upper(): g(d) for d in ["specificity","measurability","temporality","evidence","consistency"]} | {"tier": c.get("credibility_tier")}})
    json.dump({"seed": SEED, "design": "purposive challenge set by claim wording; categories and regexes in build_challenge_set.py; "
               "framework scores not used in the draw; eligibility rule eligible() applied to non-target categories after the shuffle (21 Oct); reported separately from the representative 50",
               "quota": QUOTA, "pool_size": len(pool), "claims": out},
              open(OUT / "round1_challenge_selection.json", "w"), ensure_ascii=False, indent=1)
    for o in out: print(o["challenge_category"], o["uid"], o["claim_type"], "|", o["claim_text"][:110], "| packs:", [p[0] for p in o["pack"]], o["flags"])

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
