"""Score Audit 1 (extraction) and Audit 3 (declared priorities) for one auditor, by the rules in
PRESPEC-audit-scoring-16Nov2026.md and its addenda of 23 and 24 Nov 2026. Run from the project root:
  python3 revision/audits/score_audits_1_3.py DNA revision/audits/reduced/Audit1-Extraction-reduced-DNA.xlsx revision/audits/Audit3-Declared-priorities-DNA.xlsx"""
import sys, re, math, openpyxl, pandas as pd
who, f1, f3 = sys.argv[1:4]; K = 'revision/audits/_keys-do-not-open/'; L = [f'# Audit results — auditor {who} (one auditor; second auditor not yet returned)\n']
def wilson(k, n, z=1.96):
    if n == 0: return (float('nan'),)*2
    p = k/n; d = 1+z*z/n; c = (p+z*z/(2*n))/d; h = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return c-h, c+h
def pct(k, n): lo, hi = wilson(k, n); return f'{k} of {n} ({100*k/n:.0f}%; 95% interval {100*lo:.0f}–{100*hi:.0f}%)'
def words(t): return [w for w in re.sub(r'[^a-z0-9% ]', ' ', str(t).lower().replace('\n', ' ')).split() if len(w) > 2]
# ---------- Audit 1
ws = openpyxl.load_workbook(f1)['Your claims']; A = [dict(span=r[0], page=int(r[1]), text=str(r[2]), typ=r[3]) for r in ws.iter_rows(min_row=2, values_only=True) if r[0] and r[2] and str(r[2]).strip().lower() != 'none']
spans = sorted({a['span'] for a in A} | {r[0] for r in openpyxl.load_workbook(f1)['Spans'].iter_rows(min_row=2, values_only=True) if r[0]})
key = pd.read_csv(K+'Audit1-Extraction-KEY.csv'); key = key[key.span_id.isin(spans)].reset_index(drop=True)
def run(th):
    m_ext = []; hit_rows = set()
    for _, e in key.iterrows():
        we = set(words(e['extracted claim text'])); best = None
        for i, a in enumerate(A):
            if a['span'] != e.span_id or abs(a['page']-int(e.pdf_page)) > 1: continue
            wa = set(words(a['text'])); ov = len(we & wa)/max(1, len(we))
            if ov >= th: hit_rows.add(i); best = i if best is None else best
        m_ext.append(best)
    return m_ext, hit_rows
L += ['## Audit 1 — claim extraction', f'Spans: {len(spans)} ({", ".join(spans)}). Auditor listed {len(A)} claims; the extractor produced {len(key)} claims on the same pages.\n', '| match threshold | recall: auditor claims found by the extractor | precision: extracted claims that match an auditor claim |', '|---|---|---|']
for th in (0.6, 0.5, 0.7):
    m, h = run(th); L.append(f'| {int(th*100)}%{" (main)" if th==0.6 else ""} | {pct(len(h), len(A))} | {pct(sum(x is not None for x in m), len(key))} |')
m, h = run(0.6)
L += ['\nBy span (60% threshold):', '| span | auditor claims | found by extractor | extracted claims | match an auditor claim |', '|---|---|---|---|---|']
for s in spans:
    ia = [i for i, a in enumerate(A) if a['span'] == s]; ie = [j for j in range(len(key)) if key.span_id[j] == s]
    L.append(f'| {s} | {len(ia)} | {sum(i in h for i in ia)} | {len(ie)} | {sum(m[j] is not None for j in ie)} |')
L += ['\nAuditor claims the extractor did not capture:'] + [f'- {a["span"]} p.{a["page"]} [{a["typ"]}]: {a["text"].replace(chr(10)," ")[:170]}' for i, a in enumerate(A) if i not in h]
L += ['\nExtracted claims with no matching auditor claim (to be classified by the auditors):'] + [f'- {key.span_id[j]} p.{key.pdf_page[j]} {key.claim_id[j]} [{key.claim_type[j]}]: {str(key["extracted claim text"][j])[:170]}' for j in range(len(key)) if m[j] is None]
ty = [(A[m[j]]['typ'], key.claim_type[j]) for j in range(len(key)) if m[j] is not None]
L.append(f'\nClaim type, matched pairs: same type {sum(a==b for a,b in ty)} of {len(ty)}.')
# ---------- Audit 3
ws = openpyxl.load_workbook(f3)['Reports']; k3 = pd.read_csv(K+'Audit3-Declared-priorities-KEY.csv').set_index('company')
rows = []
for r in ws.iter_rows(min_row=2, values_only=True):
    if not r[0]: continue
    broad = {int(x) for x in re.findall(r'\d+', str(r[4] or '')) if 1 <= int(x) <= 17}
    note = str(r[6] or ''); mm = re.match(r'\s*([\d,\s]+?)\s*(?:are|is)\s+(?:the\s+)?major', note)
    strict = {int(x) for x in re.findall(r'\d+', mm.group(1))} if mm else set(broad)
    fw = {int(x) for x in str(k3.loc[r[1], 'framework declared SDGs']).split() if x.isdigit()} if r[1] in k3.index and str(k3.loc[r[1], 'framework declared SDGs']) != 'nan' else set()
    rows.append(dict(company=r[1], broad=broad, strict=strict, fw=fw))
L += ['\n## Audit 3 — declared SDG priorities (30 reports × 17 goals = 510 cells)']
for name in ('strict', 'broad'):
    tp = sum(len(x[name] & x['fw']) for x in rows); fn = sum(len(x[name] - x['fw']) for x in rows); fp = sum(len(x['fw'] - x[name]) for x in rows); tn = 510-tp-fn-fp
    po = (tp+tn)/510; pa = (tp+fn)/510; pf = (tp+fp)/510; pe = pa*pf+(1-pa)*(1-pf); kap = (po-pe)/(1-pe)
    L += [f'\n**{name.capitalize()} reading{" (main)" if name=="strict" else " (sensitivity)"}.** Auditor declares {tp+fn} cells; detector declares {tp+fp} cells.', f'- Both declare: {tp}. Auditor only (detector missed): {fn}. Detector only (not declared according to the auditor): {fp}. Neither: {tn}.', f'- Cell agreement {100*po:.1f}%; Cohen’s κ {kap:.2f}. Of the detector’s declared cells, {pct(tp, tp+fp)} are declared according to the auditor; of the auditor’s declared cells, {pct(tp, tp+fn)} were detected.', f'- Reports where the two sets are identical: {sum(x[name]==x["fw"] for x in rows)} of 30.']
L += ['\n| company | auditor (strict) | auditor (broad, n) | detector | detector only | ', '|---|---|---|---|---|']
for x in rows: L.append(f'| {x["company"]} | {" ".join(map(str,sorted(x["strict"]))) or "none"} | {len(x["broad"])} | {" ".join(map(str,sorted(x["fw"]))) or "none"} | {" ".join(map(str,sorted(x["fw"]-x["broad"]))) or "–"} |')
out = f'revision/audits/RESULTS-audits-1-3-{who}.md'; open(out, 'w').write('\n'.join(L)); print('\n'.join(L))
