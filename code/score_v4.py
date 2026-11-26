"""
score_v4.py - score claims with the V4 instrument (handbook Scorer-Handbook-SMTEC-21OCT26, as sent to raters).

The model scores S, M, T, E and labels every passage; C, the composites and the tiers are computed here,
by fixed rules, so that the framework and the human raters are compared on exactly the same footing.

Modes
  --form PATH      score the claims exactly as displayed in a rater form workbook (Forms sheet):
                   the Round 1 Phase 2 TH form (validation) or the Pilot 20 form (dry run).
                   Passage text is read from the workbook, so the model sees what the raters saw.
  --corpus         score every SDG-mapped claim of the corpus reports (or --reports ...) with the
                   production retrieval (V7 chunk-aware, unchanged) -> data/outputs/main/full_v4/
  --mock           no API calls; a fixed fake response, to test parsing and aggregation.

Fixed rules (see scorer/FREEZE-V4-*.md once frozen)
  * 3 runs per claim (SCORING_RUNS), temperature SCORING_TEMPERATURE, model PRIMARY_MODEL (config/settings.py).
  * S, M, T, E: median of the runs (integer).
  * Passage label: the label given by at least 2 of 3 runs; if no majority, "Related" (a non-counting label);
    empty slots are always "None".
  * C = number of DISTINCT sections among X1-X3 passages labelled Extend (0-3). S1, S2 never count.
    Contradicts is recorded (contradicts_slots), never deducted. All X slots empty -> C = 0 and
    flag nothing_to_check = True.
  * Composites (equal weights): SMTEC = mean(S, M, T, E, C); SMTE = mean(S, M, T, E).
  * Tiers: unsubstantiated < 1.0 <= partially_substantiated < 2.0 <= substantiated.
  * Headline composite (pre-registered): SMTEC if the raters' Krippendorff ordinal alpha for C >= 0.667,
    otherwise SMTE. Both are always stored.

Run from sdg-credibility-framework/:
  python score_v4.py --form ../scorer/Pilot20-SMTEC-form-v4-EN.xlsx --out data/outputs/revision/v4_pilot20.json
  python score_v4.py --form ../scorer/Round1-Phase2-SMTEC-form-v2-TH.xlsx --out data/outputs/revision/v4_round1_TH.json
  python score_v4.py --corpus
"""
from __future__ import annotations

import argparse, asyncio, hashlib, html, json, re, statistics, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from prompts.credibility_scoring_v4 import (CREDIBILITY_SCORING_PROMPT_V4, SYSTEM_MESSAGE_V4,
                                           LABELS_V4, PROMPT_VERSION_V4)

SLOTS = ["S1", "S2", "X1", "X2", "X3"]
X_SLOTS = ["X1", "X2", "X3"]
DIMS = ["S", "M", "T", "E"]
EMPTY = "(no passage retrieved)"
TIERS = [("unsubstantiated", 0.0, 1.0), ("partially_substantiated", 1.0, 2.0), ("substantiated", 2.0, 3.01)]
PROMPT_SHA256 = hashlib.sha256((SYSTEM_MESSAGE_V4 + "\n" + CREDIBILITY_SCORING_PROMPT_V4).encode()).hexdigest()
TAG = re.compile(r"^\[Section:\s*(.*?),\s*p\.\s*([^\]]*)\]\s*\n?(.*)$", re.S)


# ---------------------------------------------------------------- display text (same as the rater forms)
def clean(t: str) -> str:
    """Identical to scorer/build_phase2_form_v2.py clean(): strip ADE anchors and bold marks, drop control
    characters and blank lines, and join very short layout fragments with ' | '."""
    t = re.sub(r"<a id='[^']*'></a>\s*", "", t); t = t.replace("**", "")
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", t); t = re.sub(r"\n\s*\n+", "\n", t).strip()
    out = []
    for ln in t.split("\n"):
        if out and len(ln) <= 40 and len(out[-1].split(" | ")[-1]) <= 40: out[-1] += " | " + ln
        else: out.append(ln)
    return "\n".join(out)

def tidy(t: str) -> str:
    """Identical in effect to scorer/build_large_forms.py tidy(): the large-print forms the raters received
    show figure markers as [Figure: ...], drop markdown '#' marks and '**', and decode HTML entities outside
    tables. Tables are kept as HTML here (raters saw them as a grid; same cells, same text)."""
    t = t.replace("<::", "[Figure: ").replace("::>", "]")
    t = re.sub(r"(^|\n|\| )#{1,6} ", r"\1", t).replace("**", "")
    if "<table" not in t: return html.unescape(t)
    m = re.search(r"<table.*?(</table>|$)", t, re.S)
    return html.unescape(t[:m.start()]) + m.group(0) + html.unescape(t[m.end():])

def split_tag(text: str):
    m = TAG.match(text or "")
    return (m.group(1).strip(), m.group(2).strip(), m.group(3).strip()) if m else (None, None, (text or "").strip())


# ---------------------------------------------------------------- inputs
def items_from_form(path: Path) -> list[dict]:
    """Read claims and passages exactly as shown on a rater form's Forms sheet."""
    import openpyxl
    ws = openpyxl.load_workbook(path, read_only=True)["Forms"]
    items, cur = [], None
    for row in ws.iter_rows(min_col=1, max_col=2, values_only=True):
        a, b = row
        if isinstance(a, str) and a.startswith("#"):
            parts = a.split()
            cur = {"claim_id": parts[2], "report": parts[3], "slots": {}}
            items.append(cur); continue
        if cur is None or not isinstance(a, str): continue
        key = a.split()[0]
        if key == "CLAIM":
            sec, page, txt = split_tag(b); cur.update(section=sec, page=page, claim_text=txt)
        elif key == "sdg_targets":
            cur["sdg_targets"] = b or ""
        elif key in SLOTS:
            cur["slots"][key] = tidy(b) if isinstance(b, str) else EMPTY
    for it in items:
        for s in SLOTS: it["slots"].setdefault(s, EMPTY)
    return items

def items_from_corpus(report: str) -> list[dict]:
    """Production retrieval (V7 chunk-aware, unchanged) -> the same pack layout the raters saw."""
    from utils.retrieval import retrieve_chunk_aware_refs, load_chunks_from_chunks_json
    from config.settings import OUTPUTS_DIR
    full = json.load(open(OUTPUTS_DIR / "main" / "full" / f"{report}_full.json"))
    v7 = json.load(open(OUTPUTS_DIR / "main" / "full_v7" / f"{report}_full_v7.json"))
    chunks = load_chunks_from_chunks_json(OUTPUTS_DIR / "main" / "chunks" / f"{report}_chunks.json")
    by_id = {c["claim_id"]: c for c in full["claims"]}
    items = []
    for c in v7["claims"]:
        if not c.get("sdg_mappings"): continue
        res = retrieve_chunk_aware_refs(sample_claim=by_id[c["claim_id"]], claims_pool=full["claims"],
                                        chunks_pool=chunks, sections=full.get("sections", []),
                                        report_key=f"{report}_corpus_v7")
        slots = {s: EMPTY for s in SLOTS}
        for i, x in enumerate(res.cross_section[:3]): slots[f"X{i+1}"] = tidy(f"[Section: {x.section}, p. {x.page}]\n{clean(x.text)}")
        for i, x in enumerate(res.same_section[:2]):  slots[f"S{i+1}"] = tidy(f"[Section: {x.section}, p. {x.page}]\n{clean(x.text)}")
        tg = ", ".join(sorted({m.get("target_id") or m.get("target") or str(m) for m in c["sdg_mappings"]}))
        items.append({"claim_id": c["claim_id"], "uid": f"{report}::{c['claim_id']}", "report": report,
                      "section": c.get("section"), "page": c.get("page"), "claim_text": c["claim_text"],
                      "sdg_targets": tg, "slots": slots, "claim_type": c.get("claim_type"),
                      "retrieval_flags": list(res.flags)})
    return items


# ---------------------------------------------------------------- prompt + one run
def build_prompt(it: dict) -> str:
    return CREDIBILITY_SCORING_PROMPT_V4.format(
        claim_text=it["claim_text"], section=it.get("section") or "Unknown", page=it.get("page") or "?",
        sdg_targets=it.get("sdg_targets") or "", **{s: it["slots"][s] for s in SLOTS})

def parse_run(raw: dict, it: dict) -> dict | None:
    """Validate one model response; returns None if unusable."""
    try:
        out = {d: int(raw[d]["score"]) for d in DIMS}
        if any(not 0 <= v <= 3 for v in out.values()): return None
        out["rationale"] = {d: str(raw[d].get("rationale", "")) for d in DIMS}
        labs = raw.get("labels", {})
        out["labels"] = {}
        for s in SLOTS:
            if it["slots"][s] == EMPTY: out["labels"][s] = "None"; continue
            lab = str((labs.get(s) or {}).get("label", "")).strip().capitalize()
            if lab not in LABELS_V4: return None
            out["labels"][s] = lab
        out["label_reason"] = {s: str((labs.get(s) or {}).get("reason", "")) for s in SLOTS}
        out["comment"] = str(raw.get("comment", ""))
        return out
    except (KeyError, TypeError, ValueError):
        return None

MOCK = {"S": {"score": 2, "rationale": "mock"}, "M": {"score": 2, "rationale": "mock"},
        "T": {"score": 1, "rationale": "mock"}, "E": {"score": 1, "rationale": "mock"},
        "labels": {"S1": {"label": "Redundant", "reason": "mock"}, "S2": {"label": "Related", "reason": "mock"},
                   "X1": {"label": "Extend", "reason": "mock"}, "X2": {"label": "Extend", "reason": "mock"},
                   "X3": {"label": "Contradicts", "reason": "mock"}}, "comment": ""}

async def one_run(client, it, sem, mock=False, retries=3):
    if mock: return parse_run(json.loads(json.dumps(MOCK)), it)
    from config.settings import PRIMARY_MODEL, SCORING_TEMPERATURE
    for attempt in range(retries):
        async with sem:
            try:
                r = await client.chat.completions.create(
                    model=PRIMARY_MODEL, temperature=SCORING_TEMPERATURE,
                    response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": SYSTEM_MESSAGE_V4},
                              {"role": "user", "content": build_prompt(it)}])
                parsed = parse_run(json.loads(r.choices[0].message.content), it)
                if parsed is not None: return parsed
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower(): await asyncio.sleep(2 ** (attempt + 1))
                elif attempt == retries - 1: print("   run failed:", type(e).__name__, str(e)[:120])
        await asyncio.sleep(0.5)
    return None


# ---------------------------------------------------------------- fixed aggregation rules
def majority_label(labels: list[str]) -> tuple[str, bool]:
    for lab in set(labels):
        if labels.count(lab) >= 2: return lab, len(set(labels)) == 1
    return "Related", False

def section_of(text: str) -> str | None:
    return split_tag(text)[0]

def compute_c(labels: dict, slots: dict) -> tuple[int, bool]:
    if all(slots[s] == EMPTY for s in X_SLOTS): return 0, True
    secs = {(section_of(slots[s]) or s).strip().lower() for s in X_SLOTS if labels.get(s) == "Extend"}
    return min(3, len(secs)), False

def tier_of(x: float) -> str:
    for name, lo, hi in TIERS:
        if lo <= x < hi: return name
    return "substantiated"

def aggregate(it: dict, runs: list[dict]) -> dict:
    res = {k: it.get(k) for k in ("claim_id", "uid", "report", "section", "page", "claim_type", "sdg_targets", "retrieval_flags") if k in it}
    res.update(prompt_version=PROMPT_VERSION_V4, prompt_sha256=PROMPT_SHA256, n_runs=len(runs))
    if not runs:
        res["error"] = "all runs failed"; return res
    for d in DIMS:
        vals = [r[d] for r in runs]
        res[d] = int(statistics.median(vals)); res[f"{d}_runs"] = vals
    res["labels"], res["label_agreement"] = {}, {}
    for s in SLOTS:
        lab, agree = majority_label([r["labels"][s] for r in runs])
        res["labels"][s] = lab; res["label_agreement"][s] = agree
    res["C"], res["nothing_to_check"] = compute_c(res["labels"], it["slots"])
    res["contradicts_slots"] = [s for s in SLOTS if res["labels"][s] == "Contradicts"]
    res["SMTEC"] = round(sum(res[d] for d in DIMS + ["C"]) / 5, 2)
    res["SMTE"] = round(sum(res[d] for d in DIMS) / 4, 2)
    res["tier_SMTEC"], res["tier_SMTE"] = tier_of(res["SMTEC"]), tier_of(res["SMTE"])
    mid = min(range(len(runs)), key=lambda i: sum(abs(runs[i][d] - res[d]) for d in DIMS))
    res["rationale"], res["label_reason"], res["comment"] = runs[mid]["rationale"], runs[mid]["label_reason"], runs[mid]["comment"]
    return res


# ---------------------------------------------------------------- driver
async def score_items(items, concurrency=5, mock=False):
    from config.settings import SCORING_RUNS
    client = None
    if not mock:
        from openai import AsyncOpenAI
        from config.settings import OPENAI_API_KEY
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    sem = asyncio.Semaphore(concurrency)
    async def one(it):
        runs = await asyncio.gather(*[one_run(client, it, sem, mock) for _ in range(SCORING_RUNS)])
        return aggregate(it, [r for r in runs if r])
    return await asyncio.gather(*[one(it) for it in items])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--form"); ap.add_argument("--out"); ap.add_argument("--corpus", action="store_true")
    ap.add_argument("--reports", nargs="*"); ap.add_argument("--concurrency", type=int, default=5)
    ap.add_argument("--mock", action="store_true"); ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    if a.form:
        items = items_from_form(Path(a.form))[: a.limit or None]
        t0 = time.time(); results = asyncio.run(score_items(items, a.concurrency, a.mock))
        out = Path(a.out or f"v4_scores_{Path(a.form).stem}.json")
        json.dump({"source_form": str(a.form), "prompt_version": PROMPT_VERSION_V4, "prompt_sha256": PROMPT_SHA256,
                   "mock": a.mock, "claims": results}, open(out, "w"), ensure_ascii=False, indent=1)
        print(f"scored {len(results)} claims in {time.time()-t0:.0f}s -> {out}")
    elif a.corpus:
        from config.settings import OUTPUTS_DIR
        outdir = OUTPUTS_DIR / "main" / "full_v4"; outdir.mkdir(parents=True, exist_ok=True)
        reports = a.reports or sorted(p.name.replace("_full_v7.json", "") for p in (OUTPUTS_DIR / "main" / "full_v7").glob("*_full_v7.json"))
        for rep in reports:
            dst = outdir / f"{rep}_full_v4.json"
            if dst.exists(): print("skip (exists):", rep); continue
            items = items_from_corpus(rep)[: a.limit or None]
            results = asyncio.run(score_items(items, a.concurrency, a.mock))
            json.dump({"report": rep, "prompt_version": PROMPT_VERSION_V4, "prompt_sha256": PROMPT_SHA256,
                       "retrieval": "V7 chunk-aware (unchanged)", "mock": a.mock, "claims": results},
                      open(dst, "w"), ensure_ascii=False, indent=1)
            print(f"{rep}: {len(results)} claims -> {dst.name}")
    else:
        ap.error("choose --form PATH or --corpus")

if __name__ == "__main__":
    main()
