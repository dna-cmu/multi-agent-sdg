"""Findings reanalysis on the frozen-V4 corpus scores (Reviewer 3 points 1, 2, 5, 6, 7, 8). Run from the project root.
Outputs: revision/findings-v4/Findings-V4.md and CSV tables in sdg-credibility-framework/data/outputs/revision/v4/."""
import itertools, json, warnings
import numpy as np, pandas as pd, krippendorff
import statsmodels.formula.api as smf
from scipy.stats import spearmanr, chi2
warnings.filterwarnings('ignore')
R = 'sdg-credibility-framework/data/outputs/revision/'; OUT = R + 'v4/'
import os; os.makedirs(OUT, exist_ok=True)
A = pd.read_csv(R + 'claims_v4_flat.csv', keep_default_na=False, na_values=[''])  # keep the label 'None' as text
d = A[A.complete == 1].copy()
MAIN = ['commitment', 'achievement', 'metric', 'policy', 'alignment', 'target']
d['ct'] = d.claim_type.where(d.claim_type.isin(MAIN), 'other')
TN = ['unsubstantiated', 'partially_substantiated', 'substantiated']
def tier(x, lo=1.0, hi=2.0): return np.where(x < lo, TN[0], np.where(x < hi, TN[1], TN[2]))
def shares(s): 
    v = pd.Series(s).value_counts(normalize=True).reindex(TN).fillna(0) * 100
    return ' / '.join(f'{x:.1f}' for x in v)
def md(df, floatfmt='.2f'): return df.to_markdown(index=False, floatfmt=floatfmt)
L = ['# Findings on the frozen-V4 corpus scores\n', f'30 reports, {len(A):,} claims; {len(d):,} with a complete score ({len(A)-len(d)} missing, see scorer/CORPUS-V4-RUN.md). Tier shares are given as unsubstantiated / partially / substantiated (%). Headline composite: SMTE (pre-registered rule; raters\' α for C < 0.667).\n']

# 1 overall
L.append('## 1. Overall\n')
t = pd.DataFrame([{'dimension': k, 'mean': d[k].mean(), 'sd': d[k].std(), **{f'% at {v}': (d[k] == v).mean()*100 for v in range(4)}} for k in 'SMTEC'])
L.append(md(t)); t.to_csv(OUT + 'dimension_distributions.csv', index=False)
L.append(f'\nMean SMTE {d.SMTE.mean():.2f} (sd {d.SMTE.std():.2f}); mean SMTEC {d.SMTEC.mean():.2f}.\n\nTiers: SMTE {shares(d.tier_SMTE)}; SMTEC {shares(d.tier_SMTEC)}.\n')

# 2 sensitivity
L.append('## 2. Sensitivity of the tiers (R3.7)\n')
rows = []
for name, x in [('SMTE, cut-points 1.0 / 2.0 (headline)', d.SMTE), ('SMTEC, 1.0 / 2.0', d.SMTEC)]: rows.append((name, shares(tier(x))))
rows.append(('SMTE, cut-points 1.1 / 2.1 (next step up)', shares(tier(d.SMTE, 1.1, 2.1))))
rows.append(('SMTE, cut-points 0.75 / 1.75 (next step down)', shares(tier(d.SMTE, 0.75, 1.75))))
rows.append(('E counted twice: (S+M+T+2E)/5', shares(tier((d['S']+d['M']+d['T']+2*d['E'])/5))))
rows.append(('Non-compensatory: min(S, M, T, E)', shares(tier(d[list('SMTE')].min(axis=1)))))
rows.append(('Non-compensatory on evidence: min(SMTE, E)', shares(tier(np.minimum(d.SMTE, d.E)))))
q = d.SMTE.quantile([1/3, 2/3]).values
rows.append((f'SMTE tertiles ({q[0]:.2f}, {q[1]:.2f})', '—'))
t = pd.DataFrame(rows, columns=['rule', 'unsub / partial / sub (%)']); L.append(md(t)); t.to_csv(OUT + 'tier_sensitivity.csv', index=False)
hi = d[d.tier_SMTE == 'substantiated']
L.append(f'\nCompensation: of the {len(hi):,} claims that reach the substantiated tier on SMTE, {(hi.E <= 1).mean()*100:.1f}% have E ≤ 1 and {(hi.E == 0).mean()*100:.1f}% have E = 0; {(hi.E >= 2).mean()*100:.1f}% have E ≥ 2.\n')

# 3 correlations
L.append('## 3. Relations between dimensions (Spearman)\n')
c = d[list('SMTEC')].corr(method='spearman').round(2); L.append(c.to_markdown()); c.to_csv(OUT + 'dimension_correlations.csv')

# 4 V7 vs V4
L.append('\n## 4. V4 against the earlier V7 scores (development history)\n')
d['v7_SMTE'] = d[['v7_S','v7_M','v7_T','v7_E']].mean(axis=1)
t = pd.DataFrame([{'dimension': k, 'mean V7': d['v7_'+k].mean(), 'mean V4': d[k].mean(), 'same score %': (d['v7_'+k] == d[k]).mean()*100, 'Spearman': spearmanr(d['v7_'+k], d[k]).correlation} for k in 'SMTEC'])
L.append(md(t)); t.to_csv(OUT + 'v7_vs_v4.csv', index=False)
L.append(f'\nSMTE tiers: V7 {shares(tier(d.v7_SMTE))}; V4 {shares(d.tier_SMTE)}. Same SMTE tier under both: {(tier(d.v7_SMTE) == d.tier_SMTE).mean()*100:.1f}%. C = 3: V7 {(d.v7_C==3).mean()*100:.1f}%, V4 {(d.C==3).mean()*100:.1f}%.\n')

# 5 claim type
L.append('## 5. Claim type (R3.6)\n')
g = d.groupby('ct'); t = g.agg(n=('SMTE','size'), S=('S','mean'), M=('M','mean'), T=('T','mean'), E=('E','mean'), C=('C','mean'), SMTE=('SMTE','mean')).reset_index()
t['% substantiated (SMTE)'] = g.apply(lambda x: (x.tier_SMTE == 'substantiated').mean()*100).values
t['% unsubstantiated (SMTE)'] = g.apply(lambda x: (x.tier_SMTE == 'unsubstantiated').mean()*100).values
t = t.sort_values('n', ascending=False); L.append(md(t)); t.to_csv(OUT + 'by_claim_type.csv', index=False)
L.append(f'\n"other" = {int((d.ct=="other").sum())} claims with a type outside the six listed ({", ".join(sorted(set(d.claim_type[d.ct=="other"].astype(str))))}).\n')

# 6 sector
L.append('## 6. Sector (R3.8)\n')
firm = d.groupby(['company','sector']).agg(n=('SMTE','size'), SMTE=('SMTE','mean')).reset_index()
ctmix = d.ct.value_counts(normalize=True)
def std_mean(x):  # direct standardisation to the corpus claim-type mix
    m = x.groupby('ct').SMTE.mean(); w = ctmix.reindex(m.index); return float((m*w).sum()/w.sum())
t = d.groupby('sector').agg(firms=('company','nunique'), claims=('SMTE','size'), claim_mean=('SMTE','mean')).reset_index()
t['mean of firm means'] = t.sector.map(firm.groupby('sector').SMTE.mean())
t['claim-type-standardised'] = t.sector.map(d.groupby('sector').apply(std_mean))
t['% substantiated'] = t.sector.map(d.groupby('sector').apply(lambda x: (x.tier_SMTE=='substantiated').mean()*100))
t = t.sort_values('claim_mean', ascending=False); L.append(md(t)); t.to_csv(OUT + 'by_sector.csv', index=False)
def best_fit(formula, data):
    # ML fit with several optimisers; keep the converged fit with the highest finite log-likelihood
    best = None
    for meth in ('bfgs', 'lbfgs', 'powell', 'cg', 'nm'):
        try:
            f = smf.mixedlm(formula, data, groups=data.company).fit(reml=False, method=[meth])
            if np.isfinite(f.llf) and (best is None or f.llf > best.llf + 1e-6): best = f
        except Exception: pass
    return best
res = {}
dm = d[['SMTE','SMTEC','ct','sector','company']].copy()  # no column named C: it would shadow the formula's C()
for comp in ('SMTE', 'SMTEC'):
    m0 = smf.mixedlm(f'{comp} ~ 1', dm, groups=dm.company).fit(reml=True)
    icc = float(m0.cov_re.iloc[0,0] / (m0.cov_re.iloc[0,0] + m0.scale))
    f1 = best_fit(f'{comp} ~ C(ct, Treatment("commitment"))', dm)
    f2 = best_fit(f'{comp} ~ C(ct, Treatment("commitment")) + C(sector, Treatment("Banking & Finance"))', dm)
    print(comp, 'llf', round(f1.llf, 3), round(f2.llf, 3), 'group var', round(float(f1.cov_re.iloc[0,0]), 5), round(float(f2.cov_re.iloc[0,0]), 5))
    lr = 2*(f2.llf - f1.llf); df = d.sector.nunique()-1; p = float(chi2.sf(lr, df))
    coefs = pd.DataFrame({'term': f2.params.index, 'coef': f2.params.values, 'se': f2.bse.values, 'p': f2.pvalues.values})
    coefs = coefs[coefs.term != 'Group Var']; coefs.to_csv(OUT + f'mixed_model_{comp}.csv', index=False)
    res[comp] = dict(icc=icc, lr=lr, df=df, p=p, coefs=coefs)
r = res['SMTE']
L.append(f'\nMixed model (random intercept for firm, claim type and sector as fixed effects, ML). Firm ICC (null model): SMTE {res["SMTE"]["icc"]:.3f}, SMTEC {res["SMTEC"]["icc"]:.3f}. Likelihood-ratio test for sector, adjusting for claim type: SMTE χ²({r["df"]}) = {r["lr"]:.1f}, p = {r["p"]:.3f}; SMTEC χ²({res["SMTEC"]["df"]}) = {res["SMTEC"]["lr"]:.1f}, p = {res["SMTEC"]["p"]:.3f}.\n')
cc = r['coefs'].copy(); cc['term'] = cc.term.str.replace(r'C\(ct, Treatment\("commitment"\)\)\[T\.(.*)\]', r'claim type: \1', regex=True).str.replace(r'C\(sector, Treatment\("Banking & Finance"\)\)\[T\.(.*)\]', r'sector: \1', regex=True)
L.append('SMTE model coefficients (reference: commitment; Banking & Finance):\n\n' + md(cc, '.3f') + '\n')

# 7 goals
L.append('## 7. SDG goals (R3.8)\n')
ex = d.assign(goal=d.goals.str.split()).explode('goal'); ex['goal'] = ex.goal.astype(int); ex['w'] = 1/ex.n_goals
rows = []
for gno, x in ex.groupby('goal'):
    fm = x.groupby('company').SMTE.mean()
    m = x.groupby('ct').SMTE.mean(); w = ctmix.reindex(m.index)
    rows.append({'SDG': gno, 'claims (full count)': len(x), 'claims (fractional)': x.w.sum(), 'firms': x.company.nunique(), 'mean SMTE (claims)': x.SMTE.mean(), 'mean SMTE (fractional weights)': np.average(x.SMTE, weights=x.w), 'mean of firm means': fm.mean(), 'claim-type-standardised': float((m*w).sum()/w.sum()), '% substantiated': (x.tier_SMTE=='substantiated').mean()*100})
t = pd.DataFrame(rows); L.append(md(t)); t.to_csv(OUT + 'by_goal.csv', index=False)
env, soc = [6,7,11,12,13,14,15], [1,2,3,4,5,8,10,16]
for nm, col in [('claim-level mean', 'mean SMTE (claims)'), ('mean of firm means', 'mean of firm means'), ('claim-type-standardised', 'claim-type-standardised')]:
    e_, s_ = t[t.SDG.isin(env)][col].mean(), t[t.SDG.isin(soc)][col].mean()
    L.append(f'- Environmental goals (6, 7, 11–15) vs social goals (1–5, 8, 10, 16), {nm}: {e_:.2f} vs {s_:.2f} (difference {e_-s_:+.2f}).')
L.append(f'\nClaims mapped to more than one goal: {(d.n_goals>1).mean()*100:.1f}% (mean {d.n_goals.mean():.2f} goals per claim).\n')

# 8 firm-goal, two pre-specified rules
L.append('## 8. Firm–goal cells under the two pre-specified rules (R3.5)\n')
decl = {c: set(map(int, str(v).split())) if isinstance(v, str) else set() for c, v in A.groupby('company').declared_goals.first().items()}
cells = []
for comp in ('SMTE', 'SMTEC'):
    for (co, gno), x in ex.groupby(['company', 'goal']):
        cells.append(dict(composite=comp, company=co, goal=gno, declared=gno in decl[co], n=len(x), mean=x[comp].mean(), n_sub=int((x[comp] >= 2).sum()), share_sub=(x[comp] >= 2).mean(), S=x.S.mean(), M=x.M.mean(), T=x['T'].mean(), E=x.E.mean()))
cells = pd.DataFrame(cells); cells.to_csv(OUT + 'firm_goal_cells.csv', index=False)
ndecl = sum(len(v) for v in decl.values())
rows = []
for comp in ('SMTE', 'SMTEC'):
    for k in (3, 5):
        c = cells[cells.composite == comp]
        for lab, sub in (('declared', c[c.declared]), ('undeclared', c[~c.declared])):
            tot = ndecl if lab == 'declared' else 510 - ndecl
            e = sub[sub.n >= k]
            rows.append({'composite': comp, 'min claims': k, 'cells': lab, 'all cells': tot, 'cells with enough claims': len(e), 'Rule A: mean ≥ 2.0': int((e['mean'] >= 2).sum()), 'Rule B: ≥ 1 substantiated claim': int((e.n_sub >= 1).sum()), 'Rule B (robust): ≥ 3': int((e.n_sub >= 3).sum()), 'median share substantiated %': e.share_sub.median()*100, 'mean cell mean': e['mean'].mean()})
t = pd.DataFrame(rows); L.append(md(t)); t.to_csv(OUT + 'firm_goal_rules.csv', index=False)
c = cells[(cells.composite=='SMTE') & cells.declared & (cells.n>=3)]
L.append(f'\nDeclared cells (SMTE, ≥ 3 claims, n = {len(c)}): highest cell mean {c["mean"].max():.2f}; mean number of substantiated claims per cell {c.n_sub.mean():.1f} of {c.n.mean():.1f}; dimension profile S {c.S.mean():.2f}, M {c.M.mean():.2f}, T {c["T"].mean():.2f}, E {c.E.mean():.2f}. {ndecl - len(cells[(cells.composite=="SMTE") & cells.declared])} declared cells have no mapped claim at all.\n')

# 9 run stability
L.append('## 9. Stability across the three runs\n')
rows = []
for k in 'SMTE':
    runs = np.array([list(map(int, s.split())) for s in d[k + '_runs']])
    rows.append({'dimension': k, 'all three runs equal %': (runs.max(1) == runs.min(1)).mean()*100, 'max spread ≥ 2 %': ((runs.max(1)-runs.min(1)) >= 2).mean()*100, 'Krippendorff α (ordinal, 3 runs)': krippendorff.alpha(reliability_data=runs.T.astype(float), level_of_measurement='ordinal')})
t = pd.DataFrame(rows); L.append(md(t, '.3f')); t.to_csv(OUT + 'run_stability.csv', index=False)

# 10 labels / corroboration
L.append('\n## 10. Passage labels and corroboration (R3.2, R3.4)\n')
lab = pd.concat([d['lab_'+s].rename('label').to_frame().assign(slot=s) for s in ('S1','S2','X1','X2','X3')])
ct = pd.crosstab(lab.slot, lab.label); ct.to_csv(OUT + 'labels_by_slot.csv')
pct = ct.drop(columns=[c for c in ['None'] if c in ct]).pipe(lambda x: x.div(x.sum(1), axis=0)*100).round(1)
pct['empty slots (n)'] = ct['None'] if 'None' in ct else 0
L.append('Share of retrieved passages by label and slot (%; empty slots excluded):\n\n' + pct.reset_index().to_markdown(index=False))
L.append(f'\nC: ' + ', '.join(f'{v} = {(d.C==v).mean()*100:.1f}%' for v in range(4)) + f'. Claims with at least one passage labelled Contradicts: {(d.n_contradicts>0).mean()*100:.1f}% ({int((d.n_contradicts>0).sum()):,}). Claims with no cross-section passage at all: {int(d.nothing_to_check.sum())}. Claims with no Extend passage in any slot: {(d[[f"lab_{s}" for s in ("S1","S2","X1","X2","X3")]].ne("Extend").all(axis=1)).mean()*100:.1f}%.\n')
rep = d.groupby('report').apply(lambda x: pd.Series({'claims': len(x), 'mean SMTE': x.SMTE.mean(), '% Extend passages': (x[[f"lab_{s}" for s in ("S1","S2","X1","X2","X3")]].eq('Extend').values.sum() / x[[f"lab_{s}" for s in ("S1","S2","X1","X2","X3")]].ne('None').values.sum())*100, '% Unrelated passages': (x[[f"lab_{s}" for s in ("S1","S2","X1","X2","X3")]].eq('Unrelated').values.sum() / x[[f"lab_{s}" for s in ("S1","S2","X1","X2","X3")]].ne('None').values.sum())*100})).reset_index()
rep.to_csv(OUT + 'by_report.csv', index=False)
L.append(f'By report: mean SMTE ranges from {rep["mean SMTE"].min():.2f} to {rep["mean SMTE"].max():.2f}; share of passages labelled Unrelated from {rep["% Unrelated passages"].min():.1f}% to {rep["% Unrelated passages"].max():.1f}% (table: by_report.csv).\n')
open('revision/findings-v4/Findings-V4.md', 'w').write('\n'.join(L)); print('\n'.join(L))
