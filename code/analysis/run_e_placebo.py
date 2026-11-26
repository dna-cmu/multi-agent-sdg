"""Exploratory placebo for the stricter-Evidence sensitivity (not pre-specified; labelled as such).
Re-scores a seeded random sample of 300 corpus claims with V4 Evidence = 2 using the UNCHANGED frozen V4 prompt, to
measure how often a claim selected at E = 2 falls below 2 on a fresh 3-run median by run-to-run variation alone."""
import sys, os, json, pickle, asyncio, glob, random
from pathlib import Path
sys.path.insert(0, ".")
import score_v4 as S
from config.settings import OUTPUTS_DIR
WORK = Path(os.environ["HOME"]) / "v4work"; items = []
for f in sorted(glob.glob(str(OUTPUTS_DIR / "main" / "full_v4" / "*_full_v4.json"))):
    rep = Path(f).name.replace("_full_v4.json", "")
    e2 = {c["uid"] for c in json.load(open(f))["claims"] if c.get("n_runs") == 3 and "error" not in c and c["E"] == 2}
    items += [it for it in pickle.load(open(WORK / f"{rep}.items.pkl", "rb")) if it["uid"] in e2]
random.Random(20261110).shuffle(items); items = items[:300]
res = asyncio.run(S.score_items(items, 40, False))
out = OUTPUTS_DIR / "revision" / "v4_E_placebo_rerun.json"
json.dump({"note": "exploratory placebo, frozen V4 prompt unchanged, seed 20261110, n=300", "prompt_sha256": S.PROMPT_SHA256,
           "claims": [dict(uid=it["uid"], n_runs=r.get("n_runs"), E_runs=r.get("E_runs"), E=r.get("E")) for it, r in zip(items, res)]}, open(out, "w"), indent=1)
v = [r["E"] for r in res if r.get("n_runs") == 3]
print(len(v), "valid;", {k: v.count(k) for k in sorted(set(v))})
