"""Round 1 agreement with bootstrap confidence intervals (Reviewer 3 point 8). Run from the project root.
Bootstrap: claims are resampled with replacement WITHIN each report (6 held-out reports), 2,000 replicates, seed
20261110; a resampled claim brings all raters' scores and the framework's scores with it, so observations belonging
to the same claim stay together and each report keeps its number of claims. Percentile 95% intervals."""
import glob, sys, numpy as np, pandas as pd, krippendorff
R = sorted(f.split('/')[-1].replace('-ratings.csv', '') for f in glob.glob('revision/round1-analysis/*-ratings.csv'))
D = {r: pd.read_csv(f'revision/round1-analysis/{r}-ratings.csv', keep_default_na=False, na_values=['']).set_index('claim_id') for r in R}
key = pd.read_csv('scorer/Round1-60-KEY-EN-do-not-send.csv').set_index('claim_id')
ids = sorted(D[R[0]].index, key=lambda x: int(x[1:])); rep = key.loc[ids, 'report'].values; st = key.loc[ids, 'set'].values
NEW = [r for r in R if r != 'RaterD']
def wk(a, b, k):
    O = np.zeros((k, k)); np.add.at(O, (a, b), 1); E = np.outer(O.sum(1), O.sum(0)) / len(a); W = np.subtract.outer(np.arange(k), np.arange(k)) ** 2
    den = (W * E).sum(); return 1 - (W * O).sum() / den if den else np.nan
def alpha(M):
    try: return krippendorff.alpha(reliability_data=M.astype(float), level_of_measurement='ordinal')
    except Exception: return np.nan
tier = lambda x: np.where(x < 1, 0, np.where(x < 2, 1, 2))
X = {}
for r in R:
    d = D[r].loc[ids]
    X[r] = {k: d[k].astype(int).values for k in 'SMTE'}; X[r]['C'] = d.C_rater.astype(int).values
    X[r]['tier'] = tier((d.S.astype(int) + d.M.astype(int) + d['T'].astype(int) + d.E.astype(int)).values / 4)
d0 = D[R[0]].loc[ids]
V = {k: d0['V4_' + k].astype(int).values for k in 'SMTE'}; V['C'] = d0.V4_C.astype(int).values; V['tier'] = tier(d0.V4_SMTE.astype(float).values)
def stats(ix):
    out = {}
    for k in ['S', 'M', 'T', 'E', 'C', 'tier']:
        K = 3 if k == 'tier' else 4
        out[f'{k}|α all raters'] = alpha(np.array([X[r][k][ix] for r in R]))
        if len(NEW) >= 2: out[f'{k}|α without RaterD'] = alpha(np.array([X[r][k][ix] for r in NEW]))
        for r in R: out[f'{k}|κ {r} vs V4'] = wk(X[r][k][ix], V[k][ix], K)
    return out
rng = np.random.default_rng(20261110); Bn = 2000
def run(mask, name):
    base = np.where(mask)[0]; pt = stats(base); groups = [base[rep[base] == g] for g in sorted(set(rep[base]))]
    bs = {k: [] for k in pt}
    for _ in range(Bn):
        ix = np.concatenate([rng.choice(g, len(g), replace=True) for g in groups]); s = stats(ix)
        for k in pt: bs[k].append(s[k])
    rows = []
    for k in pt:
        dim, what = k.split('|'); v = np.array(bs[k], float); v = v[~np.isnan(v)]
        rows.append({'set': name, 'n claims': len(base), 'measure': 'SMTE tier' if dim == 'tier' else dim, 'statistic': what, 'estimate': pt[k], 'CI low': np.percentile(v, 2.5), 'CI high': np.percentile(v, 97.5)})
    return rows
rows = run(np.ones(len(ids), bool), 'all 60') + run(st == 'representative', 'representative 50') + run(st != 'representative', 'challenge 10')
T = pd.DataFrame(rows); T.to_csv('revision/round1-analysis/Round1-agreement-CI.csv', index=False)
L = ['# Round 1 — agreement with 95% bootstrap intervals\n', f'Raters with both phases: {", ".join(R)}. Bootstrap: 2,000 replicates, claims resampled within report (all raters\' and the framework\'s scores for a claim stay together), percentile intervals, seed 20261110. α = Krippendorff ordinal; κ = quadratic weighted kappa against frozen V4. "Without RaterD" = raters new to the study.\n']
for name in ('all 60', 'representative 50', 'challenge 10'):
    t = T[T['set'] == name].copy(); t['value'] = t.apply(lambda r: f"{r['estimate']:.2f} [{r['CI low']:.2f}, {r['CI high']:.2f}]", axis=1)
    p = t.pivot(index='measure', columns='statistic', values='value').reindex(['S', 'M', 'T', 'E', 'C', 'SMTE tier']).reset_index()
    L.append(f'## {name}\n\n' + p.to_markdown(index=False) + '\n')
L.append('Intervals for the challenge set (10 claims) are very wide and are shown for completeness only.')
open('revision/round1-analysis/Round1-agreement-CI.md', 'w').write('\n'.join(L)); print('\n'.join(L))
