"""Step 2 of the extraction re-run: de-duplicate, match to the original claims, recall against the authors' audit judgements.
Run from sdg-credibility-framework/: python3 ../revision/extraction-rerun/rerun_match.py"""
import sys, json, re, csv, collections, statistics
from pathlib import Path
sys.path.insert(0, ".")
from config.settings import OUTPUTS_DIR
H = Path(__file__).resolve().parent; W = H / "work"; AUD = H.parent / "audits"
def words(t): return set(w for w in re.sub(r"[^a-z0-9% ]", " ", str(t).lower().replace("\n", " ")).split() if len(w) > 2)
wins = [json.loads(l) for l in open(W / "windows.jsonl")]
print("windows", len(wins), "finish reasons", collections.Counter(w["finish"] for w in wins), "models", collections.Counter(w["model"] for w in wins))
new = collections.defaultdict(list); seen = set(); raw = 0
for w in sorted(wins, key=lambda w: (w["report"], w["w"])):
    for c in w["claims"]:
        t = str(c.get("claim_text") or "").strip(); raw += 1
        if not t or (w["report"], t) in seen: continue
        seen.add((w["report"], t))
        new[w["report"]].append({"claim_text": t, "claim_type": c.get("claim_type", "unknown"), "page": c.get("page") or w["p0"], "section": c.get("section") or w["section"], "win": w["w"], "p0": w["p0"], "p1": w["p1"], "W": words(t)})
rows = []; allnew = []
for rep in sorted(new):
    full = json.load(open(OUTPUTS_DIR / "main" / "full" / f"{rep}_full.json")); old = [words(c["claim_text"]) for c in full["claims"]]
    k = 0
    for i, c in enumerate(new[rep]):
        a = c["W"]; hit = any(a and o and (len(a & o) / len(a) >= 0.8 or len(a & o) / len(o) >= 0.8) for o in old)
        c["already"] = hit; k += hit; c["rid"] = f"RX-{i+1:05d}"; c["report"] = rep; c["company"] = full["claims"][0]["company"]; c["sector"] = full["claims"][0]["sector"]
    recap = sum(any(o and c["W"] and (len(c["W"] & o) / len(c["W"]) >= 0.8 or len(c["W"] & o) / len(o) >= 0.8) for c in new[rep]) for o in old)
    rows.append((rep, len(old), len(new[rep]), k, len(new[rep]) - k, recap)); allnew += new[rep]
print("raw claims", raw, "after de-duplication", len(allnew))
print("report | original | re-run | already extracted | newly captured | original claims found again")
for r in rows: print(" | ".join(map(str, r)))
to = sum(r[1] for r in rows); tn = sum(r[2] for r in rows); ta = sum(r[3] for r in rows); tr = sum(r[5] for r in rows)
print(f"TOTAL original {to} re-run {tn} already {ta} ({100*ta/tn:.0f}%) newly captured {tn-ta}; original claims found again {tr} ({100*tr/to:.0f}%); ratio re-run/original median {statistics.median(r[2]/r[1] for r in rows):.2f}")
# ---- recall against the pair audit (resolved judgements)
D = {(r["pair"], r["slot"]): r for r in csv.DictReader(open(AUD / "Audit6-scored-DNA.csv"))}; E = {(r["pair"], r["slot"]): r for r in csv.DictReader(open(AUD / "Audit6-scored-EE.csv"))}
R = {(r["pair"], r["slot"]): r["resolved"] for r in csv.DictReader(open(AUD / "Audit6-resolution-DNA-EE.csv", encoding="utf-8-sig")) if r["pair"] != "general"}
def cap(rep, text):
    s = words(text)
    return any(c["W"] and s and len(c["W"] & s) / min(len(c["W"]), len(s)) >= 0.6 for c in new.get(rep, []))
tab = collections.Counter()
for k in D:
    v = R.get(k) or ("claim" if D[k]["judged_claim"] == "1" else "not claim"); tab[(D[k]["source"], v, cap(D[k]["report"], D[k]["sentence"]))] += 1
print("\npair audit: source, resolved judgement -> captured by re-run / total")
for s in "ENF":
    for v in ("claim", "not claim", "not agreed"):
        n = tab[(s, v, True)] + tab[(s, v, False)]
        if n: print(f"  {s} {v}: {tab[(s, v, True)]}/{n}")
for v in ("claim", "not claim"):
    a = sum(tab[(s, v, True)] for s in "ENF"); n = a + sum(tab[(s, v, False)] for s in "ENF"); print(f"  all sources, {v}: {a}/{n} ({100*a/n:.0f}%)")
# ---- recall against Auditor 1's listing (12 pages)
import openpyxl
ws = openpyxl.load_workbook(AUD / "reduced" / "Audit1-Extraction-reduced-DNA.xlsx")["Your claims"]
A = [(r[0], int(r[1]), str(r[2])) for r in ws.iter_rows(min_row=2, values_only=True) if r[0] and r[2] and str(r[2]).strip().lower() != "none"]
hit = 0; ext = set()
for span, page, text in A:
    rep = re.sub(r"-p\d+-\d+$", "", span); s = words(text); ok = False
    for c in new.get(rep, []):
        try: lo, hi = int(c["p0"]), int(c["p1"])
        except Exception: continue
        if lo - 1 <= page <= hi + 1 and c["W"] and len(c["W"] & s) / len(c["W"]) >= 0.6: ok = True; ext.add((rep, c["rid"]))
    hit += ok
print(f"\nAuditor 1 listing: {hit}/{len(A)} listed claims captured by the re-run (original run: 4/30); re-run claims matching a listed claim: {len(ext)}")
for c in allnew: c.pop("W")
json.dump(allnew, open(W / "rerun_claims.json", "w"), ensure_ascii=False)
