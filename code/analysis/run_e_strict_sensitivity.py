"""Stricter-Evidence sensitivity run (pre-specified in scorer/PRESPEC-E-strict-sensitivity-10Nov2026.md).
Rescores only claims whose frozen-V4 Evidence score is 2, with the prompt variant in
prompts/credibility_scoring_v4_E_strict.py; uses the frozen scorer's own functions for the calls, validation and the
3-run median (the module's prompt constant is swapped in memory for this process only; no file is modified).
Usage (from sdg-credibility-framework/): python3 ../revision/run_e_strict_sensitivity.py <seconds> <concurrency>"""
import sys, os, json, pickle, asyncio, time, glob, hashlib
from pathlib import Path
sys.path.insert(0, ".")
import score_v4 as S
from prompts.credibility_scoring_v4_E_strict import CREDIBILITY_SCORING_PROMPT_V4_E_STRICT as STRICT, PROMPT_VERSION_V4_E_STRICT as VER
from config.settings import OUTPUTS_DIR, SCORING_RUNS
S.CREDIBILITY_SCORING_PROMPT_V4 = STRICT            # in-memory only
BUDGET, CONC = float(sys.argv[1]), int(sys.argv[2]); T0 = time.time(); MAX_ATTEMPTS = 3
WORK = Path(os.environ["HOME"]) / "v4work"; left = lambda: BUDGET - (time.time() - T0)
todo_items = []
for f in sorted(glob.glob(str(OUTPUTS_DIR / "main" / "full_v4" / "*_full_v4.json"))):
    rep = Path(f).name.replace("_full_v4.json", "")
    e2 = {c["uid"] for c in json.load(open(f))["claims"] if c.get("n_runs") == SCORING_RUNS and "error" not in c and c["E"] == 2}
    ip = WORK / f"{rep}.items.pkl"
    items = pickle.load(open(ip, "rb")) if ip.exists() else S.items_from_corpus(rep)
    if not ip.exists(): pickle.dump(items, open(ip, "wb"))
    todo_items += [dict(it, set="corpus") for it in items if it["uid"] in e2]
r1 = json.load(open(OUTPUTS_DIR / "revision" / "v4_round1_EN.json"))["claims"]
e2r = {c["claim_id"] for c in r1 if c["E"] == 2}
for it in S.items_from_form(Path("../scorer/Round1-Phase2-SMTEC-form-v2-EN.xlsx")):
    if it["claim_id"] in e2r: todo_items.append(dict(it, uid="ROUND1::" + it["claim_id"], set="round1"))
pp = WORK / "estrict.partial.json"; done = json.load(open(pp)) if pp.exists() else {}
ok = lambda r: r.get("n_runs") == SCORING_RUNS and "error" not in r
final = lambda r: ok(r) or r.get("score_attempts", 1) >= MAX_ATTEMPTS
per = None
while True:
    todo = [it for it in todo_items if not (it["uid"] in done and final(done[it["uid"]]))]
    if not todo: break
    n = CONC * 2 if per is None else max(CONC, int((left() - 12) / per))
    if left() < 25: break
    batch = todo[:n]; t = time.time(); res = asyncio.run(S.score_items(batch, CONC, False)); per = (time.time() - t) / len(batch)
    for it, r in zip(batch, res):
        prev = done.get(it["uid"])
        done[it["uid"]] = dict(uid=it["uid"], set=it["set"], n_runs=r.get("n_runs"), E_strict_runs=r.get("E_runs"), E_strict_median=r.get("E"),
                               rationale_E=(r.get("rationale") or {}).get("E"), score_attempts=(prev.get("score_attempts", 1) + 1) if prev else 1, **({"error": r["error"]} if "error" in r else {}))
    json.dump(done, open(pp, "w"), ensure_ascii=False)
    print(f"+{len(batch)} in {time.time()-t:.0f}s; {sum(1 for it in todo_items if it['uid'] in done and final(done[it['uid']]))}/{len(todo_items)}")
if all(it["uid"] in done and final(done[it["uid"]]) for it in todo_items):
    out = OUTPUTS_DIR / "revision" / "v4_E_strict_sensitivity.json"
    json.dump({"prompt_version": VER, "prompt_sha256": hashlib.sha256(STRICT.encode()).hexdigest(), "base_prompt_sha256": S.PROMPT_SHA256,
               "rule": "E_sensitivity = min(2, E_strict_median) when 3 valid runs, else the V4 score (2)", "claims": [done[it["uid"]] for it in todo_items]}, open(out, "w"), ensure_ascii=False, indent=1)
    print("DONE ->", out, len(todo_items), "claims; incomplete:", [it["uid"] for it in todo_items if not ok(done[it["uid"]])])
else: print("time up")
