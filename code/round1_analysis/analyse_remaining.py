"""Remaining analyses before drafting: (1) tier cut-points and compensation in the raters' own data (R3.7),
(2) retrieval relevance from the raters' passage labels (R3.4), (3) header-only passages in the corpus evidence,
(4) volume, runtime and cost inputs by stage (R3.9). Run from the project root."""
import glob, json, os, pickle, re, subprocess, collections, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
O = Path('sdg-credibility-framework/data/outputs'); L = ['# Remaining analyses (10 Nov 2026)\n']
R = sorted(f.split('/')[-1].replace('-ratings.csv', '') for f in glob.glob('revision/round1-analysis/*-ratings.csv'))
D = {r: pd.read_csv(f'revision/round1-analysis/{r}-ratings.csv', keep_default_na=False, na_values=['']) for r in R}
key = pd.read_csv('scorer/Round1-60-KEY-EN-do-not-send.csv').set_index('claim_id')
TI = ['Unsubstantiated', 'Partially substantiated', 'Substantiated']
def wk(a, b, k=3):
    O_ = np.zeros((k, k)); np.add.at(O_, (np.asarray(a), np.asarray(b)), 1); E = np.outer(O_.sum(1), O_.sum(0)) / len(a); W = np.subtract.outer(np.arange(k), np.arange(k)) ** 2
    den = (W * E).sum(); return 1 - (W * O_).sum() / den if den else float('nan')
tier = lambda x, lo, hi: np.where(x < lo, 0, np.where(x < hi, 1, 2))

# ---- 1. cut-points and compensation
L.append('## 1. Tier cut-points and compensation in the raters\' own data (R3.7)\n')
L.append('Each rater\'s overall judgement (Phase 1) against the tier implied by the same rater\'s SMTE (Phase 2), 50 representative claims, at the registered cut-points and at neighbouring ones. Cells: claims in the same tier (of 50) / weighted κ.\n')
grid = [(0.5, 1.5), (0.5, 2.0), (0.75, 1.5), (0.75, 1.75), (0.75, 2.0), (1.0, 1.5), (1.0, 1.75), (1.0, 2.0), (1.0, 2.25), (1.25, 2.0), (1.25, 2.25)]
rows = []; P = {}
for r in R:
    d = D[r][D[r].phase1_judgement.isin(TI)].copy(); d['h'] = d.phase1_judgement.map(TI.index); d['smte'] = d[list('SMTE')].astype(int).mean(axis=1); P[r] = d
for lo, hi in grid:
    row = {'cut-points (partial from / substantiated from)': f'{lo} / {hi}' + ('  (registered)' if (lo, hi) == (1.0, 2.0) else '')}
    for r in R:
        t = tier(P[r].smte.values, lo, hi); row[r] = f'{int((t == P[r].h.values).sum())} / {wk(P[r].h.values, t):.2f}'
    allh = np.concatenate([P[r].h.values for r in R]); allt = np.concatenate([tier(P[r].smte.values, lo, hi) for r in R]); row['pooled (all raters)'] = f'{int((allh == allt).sum())} of {len(allh)} / {wk(allh, allt):.2f}'
    rows.append(row)
L.append(pd.DataFrame(rows).to_markdown(index=False))
L.append('\nMean own-SMTE of the claims a rater placed at each overall level:\n')
L.append(pd.DataFrame([{'rater': r, **{TI[k]: (f"{P[r][P[r].h == k].smte.mean():.2f} (n={int((P[r].h == k).sum())})" if (P[r].h == k).any() else '—') for k in range(3)}} for r in R]).to_markdown(index=False))
L.append('\nWhich dimension the overall judgement follows (Spearman ρ between the overall level and the rater\'s own score):\n')
L.append(pd.DataFrame([{'rater': r, **{k: round(spearmanr(P[r].h, P[r][k].astype(int)).correlation, 2) for k in 'SMTE'}, 'C (from labels)': round(spearmanr(P[r].h, P[r].C_rater.astype(int)).correlation, 2)} for r in R]).to_markdown(index=False))
rows = []
for r in R:
    d = P[r]; e = d.E.astype(int); hi_no_e = d[(d.smte >= 2) & (e <= 1)]; lo_e = d[e <= 1]; hi_e = d[e >= 2]
    rows.append({'rater': r, 'claims with own E ≤ 1': len(lo_e), '…judged Substantiated overall %': (lo_e.h == 2).mean() * 100, 'claims with own E ≥ 2': len(hi_e), '…judged Substantiated overall % ': (hi_e.h == 2).mean() * 100, 'own SMTE ≥ 2 with own E ≤ 1 (n)': len(hi_no_e)})
L.append('\nCompensation (does weak Evidence stop a rater calling a claim Substantiated overall?):\n\n' + pd.DataFrame(rows).to_markdown(index=False, floatfmt='.0f'))

# ---- 2. retrieval relevance from rater labels
L.append('\n## 2. Retrieval relevance from the raters\' passage labels (R3.4)\n')
SL = ['S1', 'S2', 'X1', 'X2', 'X3']; LAB = ['Extend', 'Redundant', 'Related', 'Unrelated', 'Contradicts']
long = []
for r in R:
    for _, x in D[r].iterrows():
        for s in SL:
            if x['label_' + s] != 'None': long.append(dict(rater=r, claim=x.claim_id, slot=s, label=x['label_' + s], report=key.loc[x.claim_id, 'report']))
d0 = D[R[0]]
for _, x in d0.iterrows():
    for s in SL:
        if x['V4_label_' + s] != 'None': long.append(dict(rater='V4', claim=x.claim_id, slot=s, label=x['V4_label_' + s], report=key.loc[x.claim_id, 'report']))
G = pd.DataFrame(long)
t = (pd.crosstab(G.rater, G.label, normalize='index') * 100).reindex(columns=LAB).round(1).reset_index(); L.append('Share of the 282 retrieved passages by label (%):\n\n' + t.to_markdown(index=False))
hum = G[G.rater != 'V4']
maj = hum.groupby(['claim', 'slot']).label.agg(lambda s: s.value_counts().index[0] if s.value_counts().iloc[0] >= 2 else 'no majority').reset_index()
maj['report'] = maj.claim.map(key.report)
L.append(f'\nMajority label of the {len(R)} raters per passage: ' + ', '.join(f'{k} {v/len(maj)*100:.1f}%' for k, v in maj.label.value_counts().items()) + f'. Passages all raters call Unrelated: {int((hum.groupby(["claim","slot"]).label.agg(lambda s: (s == "Unrelated").all())).sum())}; passages at least one rater calls Unrelated: {int((hum.groupby(["claim","slot"]).label.agg(lambda s: (s == "Unrelated").any())).sum())}; passages no rater calls Unrelated or Related (all Extend/Redundant/Contradicts): {int((hum.groupby(["claim","slot"]).label.agg(lambda s: (~s.isin(["Unrelated","Related"])).all())).sum())}.\n')
t = (pd.crosstab(maj.slot, maj.label, normalize='index') * 100).round(1).reset_index(); L.append('Raters\' majority label by slot (%):\n\n' + t.to_markdown(index=False))
t = (pd.crosstab(maj.report, maj.label, normalize='index') * 100).round(1); t.insert(0, 'passages', maj.groupby('report').size()); L.append('\nRaters\' majority label by report (%):\n\n' + t.reset_index().to_markdown(index=False))

# ---- 3. header-only passages in the corpus
L.append('\n## 3. Header- or heading-only passages in the corpus evidence\n')
W = Path(os.environ['HOME']) / 'v4work'; v4 = {}
for f in glob.glob(str(O / 'main/full_v4/*_full_v4.json')):
    for c in json.load(open(f))['claims']: v4[c['uid']] = c
EMPTY = '(no passage retrieved)'; body = lambda t: t.split('\n', 1)[1].strip() if '\n' in t else ''
recs = []; ptoks = 0; nitems = 0
for ip in sorted(W.glob('*.items.pkl')):
    items = pickle.load(open(ip, 'rb')); freq = collections.Counter(body(it['slots'][s]) for it in items for s in SL if it['slots'][s] != EMPTY)
    for it in items:
        nitems += 1; ptoks += sum(len(it['slots'][s]) for s in SL) + len(it['claim_text'])
        c = v4.get(it['uid'])
        for s in SL:
            t = it['slots'][s]
            if t == EMPTY: continue
            b = body(t); recs.append(dict(slot=s, n=len(b), words=len(b.split()), repeats=freq[b], label=(c['labels'][s] if c and c.get('n_runs') == 3 else 'unscored')))
H = pd.DataFrame(recs); H['short'] = H.words <= 12; H['boiler'] = H.short & (H.repeats >= 5)
L.append(f'Working definition (text after the section tag): "short" = 12 words or fewer; "repeated short" = short and the identical text retrieved for 5 or more claims in the same report (typical of page headers and footers).\n')
L.append(f'- Passages retrieved in the corpus: {len(H):,}. Short: {int(H.short.sum()):,} ({H.short.mean()*100:.1f}%). Repeated short: {int(H.boiler.sum()):,} ({H.boiler.mean()*100:.1f}%).')
L.append('- By slot (short %): ' + ', '.join(f'{s} {H[H.slot == s].short.mean()*100:.1f}' for s in SL) + '.')
L.append('- How V4 labelled the short passages: ' + ', '.join(f'{k} {v/int(H.short.sum())*100:.1f}%' for k, v in H[H.short].label.value_counts().items()) + '.')
claims_with = len({(r['slot']) for r in recs})  # placeholder not used
L.append(f'- Median passage length: {int(H.words.median())} words.\n')

# ---- 4. volumes and runtime
L.append('## 4. Volume and runtime by stage (inputs for the end-to-end account, R3.9)\n')
pages = 0; nrep = 0
for p in glob.glob('sdg-credibility-framework/data/reports/2024/*.pdf'):
    rep = Path(p).stem
    if not (O / f'main/full_v7/{rep}_full_v7.json').exists() and not rep.startswith('WHA'): continue
    try: pages += int([l for l in subprocess.run(['pdfinfo', p], capture_output=True, text=True).stdout.splitlines() if l.startswith('Pages')][0].split()[1]); nrep += 1
    except Exception: pass
chunks = raw = chars = 0; v7sec = 0; ncl = nmap = 0
for f in glob.glob(str(O / 'main/chunks/*_chunks.json')):
    c = json.load(open(f)); chunks += c['n_chunks_kept']; raw += c['n_chunks_raw']; chars += sum(len(x.get('text') or '') for x in c['chunks'])
for f in glob.glob(str(O / 'main/full_v7/*_full_v7.json')):
    d = json.load(open(f)); v7sec += d.get('v7_rerun', {}).get('elapsed_seconds', 0); ncl += len(d['claims']); nmap += sum(1 for x in d['claims'] if x.get('sdg_mappings'))
sys.path.insert(0, 'sdg-credibility-framework'); cwd = os.getcwd(); os.chdir('sdg-credibility-framework'); sys.path.insert(0, os.getcwd())
from prompts.credibility_scoring_v4 import CREDIBILITY_SCORING_PROMPT_V4 as PV4
import prompts.sdg_mapping as PM, prompts.claim_extraction as PE
os.chdir(cwd)
mp = max((len(v) for v in vars(PM).values() if isinstance(v, str)), default=0); ep = max((len(v) for v in vars(PE).values() if isinstance(v, str)), default=0)
out_chars = np.mean([len(json.dumps({'r': c.get('rationale'), 'l': c.get('label_reason')})) for c in list(v4.values())[:2000] if c.get('n_runs') == 3])
tk = lambda ch: ch / 4  # rough: 4 characters per token
rows = [
 {'stage': '1. Document parsing (ADE)', 'volume': f'{nrep} PDF files, {pages:,} pages → {raw:,} chunks ({chunks:,} kept)', 'model calls': f'{pages:,} pages parsed', 'approx. tokens': '—', 'runtime recorded': 'not logged'},
 {'stage': '2. Claim extraction (gpt-4o)', 'volume': f'{chars/1e6:.1f} million characters of report text → {ncl:,} claims', 'model calls': 'not logged', 'approx. tokens': f'≥ {tk(chars)/1e6:.1f} M input (report text only; prompt overhead and output not logged)', 'runtime recorded': 'not logged'},
 {'stage': '3. SDG mapping (gpt-4o)', 'volume': f'{ncl:,} claims → {nmap:,} mapped, {ncl-nmap} unmapped', 'model calls': f'≥ {ncl:,}', 'approx. tokens': f'≈ {tk(mp)*ncl/1e6:.1f} M input (prompt of ~{tk(mp):,.0f} tokens per claim)', 'runtime recorded': 'not logged'},
 {'stage': '4. Retrieval (text-embedding-3-small, cached)', 'volume': f'{chunks:,} chunks and {ncl:,} claims embedded once; reused afterwards', 'model calls': 'embedding calls not logged', 'approx. tokens': f'≈ {tk(chars)/1e6:.1f} M embedded', 'runtime recorded': 'about 4–5 s per report with the cache'},
 {'stage': '5. Scoring, V7 production run (13–14 May 2026)', 'volume': f'{nmap:,} claims × 3 runs', 'model calls': f'{nmap*3:,}', 'approx. tokens': 'not recomputed', 'runtime recorded': f'{v7sec/60:.0f} min summed over reports'},
 {'stage': '5. Scoring, frozen V4 (10 Nov 2026)', 'volume': f'{nitems:,} claims × 3 runs, full passages', 'model calls': f'{nitems*3:,} (+ about 20 repeats)', 'approx. tokens': f'≈ {(tk(len(PV4)) * nitems + tk(ptoks)) * 3 / 1e6:.0f} M input, ≈ {tk(out_chars) * nitems * 3 / 1e6:.1f} M output', 'runtime recorded': 'about 50 min wall-clock at 12–40 parallel calls'},
 {'stage': 'Human review', 'volume': 'none in the production pipeline; author audits and rater validation are separate', 'model calls': '—', 'approx. tokens': '—', 'runtime recorded': '—'},
]
L.append(pd.DataFrame(rows).to_markdown(index=False))
L.append('\nNotes. Token figures are estimates from stored inputs at about 4 characters per token; they are not billing records. Extraction, mapping and embedding calls were not logged at the time, so their runtime, retries and cost cannot be reconstructed from the files; the actual cost per stage should be taken from the OpenAI and LandingAI usage records for the run dates. The paper should label the reported cost and runtime as scoring-stage figures and give the stage volumes above for the rest.')
open('revision/round1-analysis/Remaining-analyses-10Nov.md', 'w').write('\n'.join(L)); print('\n'.join(L))
