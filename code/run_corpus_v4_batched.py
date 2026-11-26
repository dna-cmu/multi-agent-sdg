"""Batched driver for the frozen V4 corpus run (10 Nov 2026).

Why: the shell available for this run stops every process after about 3 minutes, and `score_v4.py --corpus`
writes a report only when all its claims are done. This driver calls the SAME frozen functions
(score_v4.items_from_corpus, score_v4.score_items -> same prompt, model, temperature, 3 runs, aggregation) in
time-boxed batches, keeps partial results outside the project, and writes the final per-report file in exactly the
format `score_v4.py --corpus` writes. score_v4.py and the prompt are not modified.
One neutral addition: a claim whose result has fewer than 3 valid runs (API failure, rate limit, or a response the
frozen validator rejects) is scored again in full, up to MAX_ATTEMPTS times in total; the trigger is the number of
valid runs, never the score. After that the result is kept as the frozen scorer returns it (fewer runs, or
"all runs failed") and counted as incomplete in the run log. Each result records `score_attempts`.

Usage (from sdg-credibility-framework/): python3 ../revision/run_corpus_v4_batched.py <seconds> <concurrency>
"""
import sys, os, json, pickle, asyncio, time, hashlib
from pathlib import Path
sys.path.insert(0, ".")
import score_v4 as S
from config.settings import OUTPUTS_DIR, SCORING_RUNS
BUDGET, CONC = float(sys.argv[1]), int(sys.argv[2]); T0 = time.time(); MAX_ATTEMPTS = 3
WORK = Path(os.environ["HOME"]) / "v4work"; WORK.mkdir(exist_ok=True)
outdir = OUTPUTS_DIR / "main" / "full_v4"; outdir.mkdir(parents=True, exist_ok=True)
reports = sorted(p.name.replace("_full_v7.json", "") for p in (OUTPUTS_DIR / "main" / "full_v7").glob("*_full_v7.json"))
left = lambda: BUDGET - (time.time() - T0)
for rep in reports:
    dst = outdir / f"{rep}_full_v4.json"
    if dst.exists(): continue
    ip, pp = WORK / f"{rep}.items.pkl", WORK / f"{rep}.partial.json"
    if ip.exists(): items = pickle.load(open(ip, "rb"))
    else:
        if left() < 60: print("stop before retrieval:", rep); break
        t = time.time(); items = S.items_from_corpus(rep); pickle.dump(items, open(ip, "wb")); print(f"{rep}: retrieval {len(items)} claims in {time.time()-t:.0f}s")
    done = json.load(open(pp)) if pp.exists() else {}
    ok = lambda r: r.get("n_runs") == SCORING_RUNS and "error" not in r
    final = lambda r: ok(r) or r.get("score_attempts", 1) >= MAX_ATTEMPTS
    per_claim = None
    while True:
        todo = [it for it in items if not (it["uid"] in done and final(done[it["uid"]]))]
        if not todo: break
        n = CONC * 2 if per_claim is None else max(CONC, int((left() - 12) / per_claim))
        if left() < 25 or n < 1: break
        batch = todo[:n]; t = time.time()
        res = asyncio.run(S.score_items(batch, CONC, False))
        per_claim = (time.time() - t) / len(batch)
        for it, r in zip(batch, res):
            prev = done.get(it["uid"])
            r["score_attempts"] = (prev.get("score_attempts", 1) + 1) if prev is not None else 1
            done[it["uid"]] = r
        json.dump(done, open(pp, "w"), ensure_ascii=False)
        bad = sum(1 for r in res if not ok(r))
        print(f"{rep}: +{len(batch)} ({bad} incomplete) in {time.time()-t:.0f}s; {sum(1 for it in items if it['uid'] in done and ok(done[it['uid']]))}/{len(items)}")
    if all(it["uid"] in done and final(done[it["uid"]]) for it in items):
        inc = [it["uid"] for it in items if not ok(done[it["uid"]])]
        if inc: print(f"{rep}: INCOMPLETE after {MAX_ATTEMPTS} attempts: {inc}")
        json.dump({"report": rep, "prompt_version": S.PROMPT_VERSION_V4, "prompt_sha256": S.PROMPT_SHA256,
                   "retrieval": "V7 chunk-aware (unchanged)", "mock": False, "claims": [done[it["uid"]] for it in items]},
                  open(dst, "w"), ensure_ascii=False, indent=1)
        print(f"{rep}: {len(items)} claims -> {dst.name}")
    else:
        print("time up in", rep); break
print("reports done:", len(list(outdir.glob("*_full_v4.json"))), "of", len(reports))
