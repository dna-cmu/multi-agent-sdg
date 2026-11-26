"""Steps 3-5 of the extraction re-run (PRESPEC-extraction-rerun-26Nov2026.md): sample, map, retrieve, score.
Usage (from sdg-credibility-framework/): python3 ../revision/extraction-rerun/rerun_map_score.py sample|map|items|score <seconds> <concurrency>
Unchanged Mapper (agents/mapper.py), frozen retrieval (utils/retrieval.py) and frozen V4 scorer (score_v4.py). Time-boxed and resumable; no existing file is modified."""
import sys, json, asyncio, time, random, pickle
from pathlib import Path
sys.path.insert(0, ".")
from config.settings import OUTPUTS_DIR, OPENAI_API_KEY, SCORING_RUNS
STAGE = sys.argv[1]; BUDGET = float(sys.argv[2]) if len(sys.argv) > 2 else 0; CONC = int(sys.argv[3]) if len(sys.argv) > 3 else 8; T0 = time.time()
W = Path(__file__).resolve().parent / "work"; left = lambda: BUDGET - (time.time() - T0)
FULL2 = ["PTTGC-2024-IR-EN", "SCC-2024-SR-EN"]; SEED = 20261126; NSAMPLE = 1000
def jl(p, default): return json.load(open(p)) if Path(p).exists() else default
if STAGE == "sample":
    assert not (W / "selected.json").exists(), "sample already drawn"
    rc = json.load(open(W / "rerun_claims.json")); new = [c for c in rc if not c["already"]]
    for c in new: c["uid"] = f"{c['report']}::{c['rid']}"
    pick = set(c["uid"] for c in random.Random(SEED).sample(sorted(new, key=lambda c: c["uid"]), NSAMPLE))
    sel = []
    for c in new:
        s = c["uid"] in pick; f = c["report"] in FULL2
        if s or f: c["in_sample"] = s; c["in_full2"] = f; sel.append(c)
    json.dump(sel, open(W / "selected.json", "w"), ensure_ascii=False)
    print("newly captured", len(new), "selected", len(sel), "sample", sum(c["in_sample"] for c in sel), "full2", sum(c["in_full2"] for c in sel), "both", sum(c["in_sample"] and c["in_full2"] for c in sel)); sys.exit()
sel = json.load(open(W / "selected.json"))
if STAGE == "map":
    from openai import AsyncOpenAI
    from agents.mapper import MapperAgent
    mp = jl(W / "mapped.json", {}); use = jl(W / "map_usage.json", {"in": 0, "out": 0, "calls": 0})
    client = AsyncOpenAI(api_key=OPENAI_API_KEY); orig = client.chat.completions.create
    async def create(*a, **k):
        r = await orig(*a, **k); use["in"] += r.usage.prompt_tokens; use["out"] += r.usage.completion_tokens; use["calls"] += 1; return r
    client.chat.completions.create = create
    agent = MapperAgent(); sem = asyncio.Semaphore(CONC); todo = [c for c in sel if c["uid"] not in mp]
    async def one(c):
        if left() < 40: return
        r = await agent._async_process_claim(client, {"claim_text": c["claim_text"]}, sem)
        if left() > 3: mp[c["uid"]] = r.get("sdg_mappings", [])
    async def main():
        for i in range(0, len(todo), CONC * 4):
            if left() < 45: break
            await asyncio.gather(*(one(c) for c in todo[i:i + CONC * 4]))
            json.dump(mp, open(W / "mapped.json", "w"), ensure_ascii=False); json.dump(use, open(W / "map_usage.json", "w"))
    asyncio.run(main())
    m = sum(1 for v in mp.values() if v)
    print(f"mapped {len(mp)}/{len(sel)}; with at least one target {m} ({100*m/max(1,len(mp)):.1f}%); tokens in {use['in']/1e6:.2f}M out {use['out']/1e6:.2f}M calls {use['calls']} est ${use['in']/1e6*2.5+use['out']/1e6*10:.2f}"); sys.exit()
import score_v4 as S
mp = json.load(open(W / "mapped.json")); todo_sel = [c for c in sel if mp.get(c["uid"])]
if STAGE == "items":
    from utils.retrieval import retrieve_chunk_aware_refs, load_chunks_from_chunks_json
    reports = sorted({c["report"] for c in todo_sel}); n = 0
    for rep in reports:
        ip = W / f"items_{rep}.pkl"
        if ip.exists(): n += 1; continue
        if left() < 70: print("stop before", rep); break
        t = time.time(); full = json.load(open(OUTPUTS_DIR / "main" / "full" / f"{rep}_full.json")); chunks = load_chunks_from_chunks_json(OUTPUTS_DIR / "main" / "chunks" / f"{rep}_chunks.json"); items = []
        for c in [c for c in todo_sel if c["report"] == rep]:
            res = retrieve_chunk_aware_refs(sample_claim={"claim_id": c["rid"], "claim_text": c["claim_text"], "section": c["section"], "page": c["page"]}, claims_pool=full["claims"], chunks_pool=chunks, sections=full.get("sections", []), report_key=f"{rep}_rerun26nov")
            slots = {s: S.EMPTY for s in S.SLOTS}
            for i, x in enumerate(res.cross_section[:3]): slots[f"X{i+1}"] = S.tidy(f"[Section: {x.section}, p. {x.page}]\n{S.clean(x.text)}")
            for i, x in enumerate(res.same_section[:2]): slots[f"S{i+1}"] = S.tidy(f"[Section: {x.section}, p. {x.page}]\n{S.clean(x.text)}")
            tg = ", ".join(sorted({str(m.get("target_id") or m.get("target") or m) for m in mp[c["uid"]]}))
            items.append({"claim_id": c["rid"], "uid": c["uid"], "report": rep, "section": c["section"], "page": c["page"], "claim_text": c["claim_text"], "sdg_targets": tg, "slots": slots, "claim_type": c["claim_type"], "retrieval_flags": list(res.flags)})
        pickle.dump(items, open(ip, "wb")); n += 1; print(f"{rep}: {len(items)} items in {time.time()-t:.0f}s")
    print("reports with items:", n, "of", len(reports)); sys.exit()
if STAGE == "score":
    items = [it for p in sorted(W.glob("items_*.pkl")) for it in pickle.load(open(p, "rb"))]; done = jl(W / "scored.json", {}); MAXA = 3
    ok = lambda r: r.get("n_runs") == SCORING_RUNS and "error" not in r; final = lambda r: ok(r) or r.get("score_attempts", 1) >= MAXA; per = None
    while True:
        todo = [it for it in items if not (it["uid"] in done and final(done[it["uid"]]))]
        if not todo: break
        n = CONC * 2 if per is None else max(CONC, int((left() - 15) / per))
        if left() < 30 or n < 1: break
        batch = todo[:n]; t = time.time(); res = asyncio.run(S.score_items(batch, CONC, False)); per = (time.time() - t) / len(batch)
        for it, r in zip(batch, res):
            prev = done.get(it["uid"]); r["score_attempts"] = (prev.get("score_attempts", 1) + 1) if prev is not None else 1; done[it["uid"]] = r
        json.dump(done, open(W / "scored.json", "w"), ensure_ascii=False)
    print(f"scored ok {sum(1 for it in items if it['uid'] in done and ok(done[it['uid']]))}/{len(items)}; incomplete-final {sum(1 for it in items if it['uid'] in done and final(done[it['uid']]) and not ok(done[it['uid']]))}; elapsed {time.time()-T0:.0f}s")
