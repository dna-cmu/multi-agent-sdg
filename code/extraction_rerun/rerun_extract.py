"""Extraction re-run without the 12,000-character cut (PRESPEC-extraction-rerun-26Nov2026.md).
Usage (from sdg-credibility-framework/): python3 ../revision/extraction-rerun/rerun_extract.py <seconds> <concurrency> [--dry]
Time-boxed and resumable: one JSON line per finished window in work/windows.jsonl. No existing file is modified."""
import sys, os, json, asyncio, time, re
from pathlib import Path
sys.path.insert(0, ".")
from config.settings import OUTPUTS_DIR, OPENAI_API_KEY, PRIMARY_MODEL
from utils.retrieval import resolve_chunk_section, load_chunks_from_chunks_json
from prompts.claim_extraction import CLAIM_EXTRACTION_PROMPT
BUDGET, CONC = float(sys.argv[1]), int(sys.argv[2]); DRY = "--dry" in sys.argv; T0 = time.time(); MAXC = 12000
WORK = Path(__file__).resolve().parent / "work"; WORK.mkdir(exist_ok=True); OUT = WORK / ("windows_pass2.jsonl" if "--pass2" in sys.argv else "windows.jsonl")
SYSTEM = "You are an expert sustainability analyst. Extract claims accurately. Always respond with valid JSON containing a 'claims' array."
reports = sorted(p.name.replace("_full_v7.json", "") for p in (OUTPUTS_DIR / "main" / "full_v7").glob("*_full_v7.json"))
def windows(rep):
    full = json.load(open(OUTPUTS_DIR / "main" / "full" / f"{rep}_full.json")); secs = full.get("sections", [])
    out = []; cur = None
    for ch in load_chunks_from_chunks_json(OUTPUTS_DIR / "main" / "chunks" / f"{rep}_chunks.json"):
        t = ch.get("text") or ""
        if not t.strip(): continue
        lab = resolve_chunk_section(ch.get("page"), secs); pieces = [t[i:i + MAXC] for i in range(0, len(t), MAXC)]
        for pc in pieces:
            if cur is None or cur["section"] != lab or cur["n"] + len(pc) + 1 > MAXC:
                cur = {"report": rep, "w": len(out), "section": lab, "p0": ch.get("page"), "p1": ch.get("page"), "parts": [], "n": 0}; out.append(cur)
            cur["parts"].append(pc); cur["n"] += len(pc) + 1; cur["p1"] = ch.get("page")
    return out
ALL = [w for r in reports for w in windows(r)]
done = {}
if OUT.exists():
    for l in open(OUT):
        d = json.loads(l); done[(d["report"], d["w"])] = d
todo = [w for w in ALL if (w["report"], w["w"]) not in done]
print(f"reports {len(reports)} windows {len(ALL)} chars {sum(w['n'] for w in ALL)/1e6:.1f}M done {len(done)} todo {len(todo)}")
if DRY:
    import collections; c = collections.Counter(w["report"] for w in ALL); print("windows per report: min %d median %d max %d" % (min(c.values()), sorted(c.values())[len(c)//2], max(c.values())))
    print("section labels 'Unmapped':", sum(w["section"] == "Unmapped" for w in ALL)); sys.exit()
from openai import AsyncOpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY); sem = asyncio.Semaphore(CONC); fh = open(OUT, "a")
async def one(w):
    if BUDGET - (time.time() - T0) < 45: return
    async with sem:
        if BUDGET - (time.time() - T0) < 40: return
        text = "\n".join(w["parts"]); err = None
        for attempt in range(3):
            try:
                r = await asyncio.wait_for(client.chat.completions.create(model=PRIMARY_MODEL, temperature=0.1, response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": CLAIM_EXTRACTION_PROMPT.format(section_title=w["section"], start_page=w["p0"], end_page=w["p1"], text_content=text)}]), timeout=max(20, BUDGET - (time.time() - T0) - 5))
                raw = r.choices[0].message.content; parsed = json.loads(raw)
                claims = parsed.get("claims", parsed.get("data", [])) if isinstance(parsed, dict) else parsed
                if not isinstance(claims, list): claims = []
                rec = {"report": w["report"], "w": w["w"], "section": w["section"], "p0": w["p0"], "p1": w["p1"], "chars": w["n"], "claims": [c for c in claims if isinstance(c, dict)],
                       "in_tok": r.usage.prompt_tokens, "out_tok": r.usage.completion_tokens, "finish": r.choices[0].finish_reason, "fingerprint": r.system_fingerprint, "model": r.model}
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush(); return
            except asyncio.TimeoutError: return
            except Exception as e:
                err = repr(e)[:200]; await asyncio.sleep(2 * (attempt + 1))
        print("FAILED", w["report"], w["w"], err)
async def main(): await asyncio.gather(*(one(w) for w in todo))
asyncio.run(main()); fh.close()
n = i = o = c = 0
for l in open(OUT):
    d = json.loads(l); n += 1; i += d["in_tok"]; o += d["out_tok"]; c += len(d["claims"])
print(f"windows done {n}/{len(ALL)} claims {c} in_tok {i/1e6:.2f}M out_tok {o/1e6:.2f}M  est cost at $2.50/$10 per M: ${i/1e6*2.5+o/1e6*10:.2f}  elapsed {time.time()-T0:.0f}s")
