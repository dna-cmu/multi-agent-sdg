"""Stricter-Evidence sensitivity: effect on the corpus and on rater agreement. Run from the project root."""
import json, glob, re, csv, numpy as np, pandas as pd, openpyxl
R = 'sdg-credibility-framework/data/outputs/revision/'
A = pd.read_csv(R + 'claims_v4_flat.csv', keep_default_na=False, na_values=['']); d = A[A.complete == 1].copy()
st = {c['uid']: c for c in json.load(open(R + 'v4_E_strict_sensitivity.json'))['claims']}
def e_sens(uid, e):
    c = st.get(uid)
    return min(2, c['E_strict_median']) if (e == 2 and c and c.get('n_runs') == 3) else e
d['E2'] = [e_sens(u, e) for u, e in zip(d.uid, d.E)]; d['SMTE2'] = (d.S + d.M + d['T'] + d.E2) / 4
TN = ['unsub', 'partial', 'sub']; tier = lambda x: np.where(x < 1, 0, np.where(x < 2, 1, 2))
sh = lambda x: ' / '.join(f'{(tier(x) == k).mean()*100:.1f}' for k in range(3))
n2 = int((d.E == 2).sum()); ch = int((d.E2 < d.E).sum())
pl = json.load(open(R + 'v4_E_placebo_rerun.json'))['claims']; plv = [c['E'] for c in pl if c['n_runs'] == 3]; pdrop = sum(1 for v in plv if v < 2) / len(plv)
L = ['# Stricter Evidence reading — sensitivity results\n', 'Pre-specified in scorer/PRESPEC-E-strict-sensitivity-10Nov2026.md. Primary instrument: frozen V4. Tier shares: unsubstantiated / partially / substantiated (%).\n', '## Corpus\n']
L.append(f'- Claims with V4 Evidence = 2: {n2:,} of {len(d):,} ({n2/len(d)*100:.1f}%). Under the stricter reading {ch:,} of them ({ch/n2*100:.1f}%) fall below 2 ({int((d.E2==1).sum()-(d.E==1).sum())} to 1, {int((d.E2==0).sum()-(d.E==0).sum())} to 0); that is {ch/len(d)*100:.1f}% of all claims.')
L.append(f'- Placebo (exploratory, not pre-specified): re-scoring a random 300 of the E = 2 claims with the unchanged V4 prompt moved {pdrop*100:.1f}% below 2 by run-to-run variation alone. Net of that, the stricter reading lowers roughly {max(0, ch/n2 - pdrop)*100:.0f}% of E = 2 claims.')
L.append(f'- Mean Evidence: {d.E.mean():.2f} → {d.E2.mean():.2f}. Mean SMTE: {d.SMTE.mean():.3f} → {d.SMTE2.mean():.3f}.')
L.append(f'- SMTE tiers: V4 {sh(d.SMTE)}; stricter reading {sh(d.SMTE2)}. Claims that change tier: {(tier(d.SMTE) != tier(d.SMTE2)).sum():,} ({(tier(d.SMTE) != tier(d.SMTE2)).mean()*100:.1f}%).')
ex = d.assign(goal=d.goals.astype(str).str.split()).explode('goal'); ex['goal'] = ex.goal.astype(int)
decl = {c: set(map(int, str(v).split())) if isinstance(v, str) else set() for c, v in A.groupby('company').declared_goals.first().items()}
rows = []
for col, nm in (('SMTE', 'V4'), ('SMTE2', 'stricter E')):
    g = ex.groupby(['company', 'goal']).agg(n=(col, 'size'), mean=(col, 'mean'), nsub=(col, lambda x: (x >= 2).sum())).reset_index()
    g['declared'] = [gl in decl[c] for c, gl in zip(g.company, g.goal)]; e = g[g.declared & (g.n >= 3)]
    rows.append({'reading': nm, 'declared cells (≥3 claims)': len(e), 'Rule A: mean ≥ 2.0': int((e['mean'] >= 2).sum()), 'Rule B: ≥ 1 substantiated claim': int((e.nsub >= 1).sum()), 'Rule B robust: ≥ 3': int((e.nsub >= 3).sum())})
L.append('\nFirm–goal rules, declared cells:\n\n' + pd.DataFrame(rows).to_markdown(index=False))
by = d[d.E == 2].groupby('claim_type').apply(lambda x: pd.Series({'E = 2 claims': len(x), 'lowered %': (x.E2 < 2).mean()*100})).reset_index().sort_values('E = 2 claims', ascending=False).head(6)
L.append('\nBy claim type (claims with V4 E = 2):\n\n' + by.to_markdown(index=False, floatfmt='.1f'))
# Round 1
L.append('\n## Round 1 held-out claims (rater agreement on Evidence under both readings)\n')
v4 = {c['claim_id']: c for c in json.load(open(R + 'v4_round1_EN.json'))['claims']}
e1 = {i: c['E'] for i, c in v4.items()}; e2 = {i: e_sens('ROUND1::' + i, c['E']) for i, c in v4.items()}
L.append(f'V4 Evidence = 2 on {sum(1 for v in e1.values() if v == 2)} of 60 claims; the stricter reading lowers {sum(1 for i in e1 if e2[i] < e1[i])} of them.\n')
def wk(a, b, k=4):
    O = np.zeros((k, k))
    for x, y in zip(a, b): O[x][y] += 1
    E = np.outer(O.sum(1), O.sum(0)) / len(a); W = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)]); return 1 - (W * O).sum() / (W * E).sum()
rows = []
for f in sorted(glob.glob('revision/round1-analysis/*-ratings.csv')):
    r = pd.read_csv(f, keep_default_na=False, na_values=['']); nm = f.split('/')[-1].replace('-ratings.csv', '')
    ids = list(r.claim_id); a = [int(x) for x in r.E]
    rows.append({'rater': nm, 'mean rater E': np.mean(a), 'κ vs V4 E': wk(a, [e1[i] for i in ids]), 'κ vs stricter E': wk(a, [e2[i] for i in ids]), 'mean V4 E': np.mean([e1[i] for i in ids]), 'mean stricter E': np.mean([e2[i] for i in ids])})
L.append(pd.DataFrame(rows).to_markdown(index=False, floatfmt='.2f'))
open('revision/findings-v4/E-strict-sensitivity.md', 'w').write('\n'.join(L)); print('\n'.join(L))
d[['uid', 'E', 'E2', 'SMTE', 'SMTE2']].rename(columns={'E2': 'E_strict', 'SMTE2': 'SMTE_strict'}).to_csv(R + 'v4/e_strict_by_claim.csv', index=False)
