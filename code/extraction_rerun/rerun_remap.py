"""Check G: repeatability of the mapping step. 300 original claims mapped again with the unchanged Mapper.
Usage (from sdg-credibility-framework/): python3 ../revision/extraction-rerun/rerun_remap.py <seconds> <concurrency>"""
import sys, json, asyncio, time, random
from pathlib import Path
sys.path.insert(0, ".")
from config.settings import OUTPUTS_DIR, OPENAI_API_KEY
from openai import AsyncOpenAI
from agents.mapper import MapperAgent
BUDGET, CONC = float(sys.argv[1]), int(sys.argv[2]); T0 = time.time(); left = lambda: BUDGET - (time.time() - T0)
W = Path(__file__).resolve().parent / "work"; P = W / "remap.json"
allc = []
for p in sorted((OUTPUTS_DIR / "main" / "full_v7").glob("*_full_v7.json")):
    rep = p.name.replace("_full_v7.json", "")
    for c in json.load(open(p))["claims"]: allc.append({"uid": f"{rep}::{c['claim_id']}", "claim_text": c["claim_text"], "orig": sorted({int(m["goal"]) for m in (c.get("sdg_mappings") or []) if m.get("goal")})})
assert len(allc) == 6936, len(allc)
pick = random.Random(20261126).sample(sorted(allc, key=lambda c: c["uid"]), 300)
done = json.load(open(P)) if P.exists() else {}; use = {"in": 0, "out": 0}
client = AsyncOpenAI(api_key=OPENAI_API_KEY); orig = client.chat.completions.create
async def create(*a, **k):
    r = await orig(*a, **k); use["in"] += r.usage.prompt_tokens; use["out"] += r.usage.completion_tokens; return r
client.chat.completions.create = create
agent = MapperAgent(); sem = asyncio.Semaphore(CONC)
async def one(c):
    if c["uid"] in done or left() < 35: return
    r = await agent._async_process_claim(client, {"claim_text": c["claim_text"]}, sem)
    if left() > 3: done[c["uid"]] = {"orig": c["orig"], "again": sorted({int(m["goal"]) for m in r.get("sdg_mappings", []) if m.get("goal")})}
asyncio.run(asyncio.gather(*(one(c) for c in pick)) if False else (lambda: asyncio.gather(*(one(c) for c in pick)))()) if False else None
async def main(): await asyncio.gather(*(one(c) for c in pick))
asyncio.run(main()); json.dump(done, open(P, "w"))
print(f"remapped {len(done)}/300; tokens in {use['in']/1e6:.2f}M out {use['out']/1e6:.2f}M est ${use['in']/1e6*2.5+use['out']/1e6*10:.2f}")
