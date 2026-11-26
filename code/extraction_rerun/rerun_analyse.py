"""Analysis of the extraction re-run (PRESPEC-extraction-rerun-26Nov2026.md, parts B-D). Run from the project root."""
import json, re, numpy as np, pandas as pd, collections
from scipy.stats import spearmanr
H='revision/extraction-rerun/'; W=H+'work/'; R='sdg-credibility-framework/data/outputs/revision/'
A=pd.read_csv(R+'claims_v4_flat.csv',keep_default_na=False,na_values=['']); O=A[A.complete==1].copy()
sel=json.load(open(W+'selected.json')); mp=json.load(open(W+'mapped.json')); sc=json.load(open(W+'scored.json')); rc=json.load(open(W+'rerun_claims.json'))
Nnew=collections.Counter(c['report'] for c in rc if not c['already'])
rows=[]
for c in sel:
    m=mp.get(c['uid']) or []; r=sc.get(c['uid'],{}); ok=r.get('n_runs')==3 and 'error' not in r
    rows.append(dict(uid=c['uid'],report=c['report'],company=c['company'],claim_type=c['claim_type'],in_sample=c['in_sample'],in_full2=c['in_full2'],mapped=bool(m),goals=sorted({int(x['goal']) for x in m if x.get('goal')}),complete=ok,**({k:r[k] for k in ('S','M','T','E','C','SMTE','SMTEC')} if ok else {})))
N=pd.DataFrame(rows); N.to_json(W+'rerun_scored_flat.json',orient='records',force_ascii=False)
S_=N[N.in_sample]; Sm=S_[S_.mapped&S_.complete].copy()
tier=lambda x: np.where(x<1,0,np.where(x<2,1,2)); TN=['unsubstantiated','partially','substantiated']
L=['# Extraction re-run without the 12,000-character cut — PRELIMINARY results (26 Nov 2026)\n','Plan fixed before the run: PRESPEC-extraction-rerun-26Nov2026.md. Not yet in the paper. Scoring: frozen Version 4. "Original" = the 6,320 scored claims of the paper; "newly captured" = claims the re-run extracted that match no original claim.\n']
L+=['## B. Newly captured claims (random sample of 1,000) against the original claims',f'- Mapped to at least one SDG target: {int(S_.mapped.sum())} of {len(S_)} ({100*S_.mapped.mean():.1f}%); original run 6,325 of 6,936 (91.2%). Scored completely: {len(Sm)}.']
def boot(df,f,B=2000,seed=20261126):
    rng=np.random.default_rng(seed); g=[x for _,x in df.groupby('report')]; v=[]
    for _ in range(B):
        s=pd.concat([x.iloc[rng.integers(0,len(x),len(x))] for x in g]); v.append(f(s))
    return np.percentile(np.array(v),[2.5,97.5],axis=0)
sh=lambda d: np.array([(tier(d.SMTE)==k).mean()*100 for k in range(3)])
ci=boot(Sm,sh); so=sh(O); sn=sh(Sm)
L+=[f'\n| SMTE tier | original (n = {len(O)}) | newly captured (n = {len(Sm)}) | 95% interval | difference |','|---|---|---|---|---|']+[f'| {TN[k]} | {so[k]:.1f}% | {sn[k]:.1f}% | {ci[0][k]:.1f}–{ci[1][k]:.1f} | {sn[k]-so[k]:+.1f} |' for k in range(3)]
dm=lambda d: np.array([d[k].mean() for k in ['S','M','T','E','C','SMTE']]); ci=boot(Sm,dm); mo=dm(O); mn=dm(Sm)
L+=['\n| mean | original | newly captured | 95% interval | difference |','|---|---|---|---|---|']+[f'| {k} | {mo[i]:.2f} | {mn[i]:.2f} | {ci[0][i]:.2f}–{ci[1][i]:.2f} | {mn[i]-mo[i]:+.2f} |' for i,k in enumerate(['S','M','T','E','C','SMTE'])]
ct=pd.DataFrame({'orig share %':O.claim_type.value_counts(normalize=True)*100,'new share %':Sm.claim_type.value_counts(normalize=True)*100,'orig mean SMTE':O.groupby('claim_type').SMTE.mean(),'new mean SMTE':Sm.groupby('claim_type').SMTE.mean(),'new n':Sm.claim_type.value_counts()}).fillna(0).sort_values('orig share %',ascending=False)
L+=['\n| claim type | original share | new share | original mean SMTE | new mean SMTE | new n |','|---|---|---|---|---|---|']+[f'| {i} | {r["orig share %"]:.1f}% | {r["new share %"]:.1f}% | {r["orig mean SMTE"]:.2f} | {r["new mean SMTE"]:.2f} | {int(r["new n"])} |' for i,r in ct.iterrows() if r['orig share %']>=0.3 or r['new n']>=5]
big=ct[(ct['new n']>=30)&(ct['orig share %']>0)]; rho=spearmanr(big['orig mean SMTE'],big['new mean SMTE']).correlation
def envsoc(d,env):
    e=d.assign(g=d.goals).explode('g').dropna(subset=['g']); e['g']=e.g.astype(int); gm=e.groupby('g').SMTE.mean()
    return gm[gm.index.isin(env)].mean()-gm[gm.index.isin([1,2,3,4,5,8,10,16])].mean()
O['goals']=O.goals.astype(str).str.split().apply(lambda v:[int(x) for x in v])
es={nm:(envsoc(O,env),envsoc(Sm,env)) for nm,env in (('as pre-specified (6, 7, 12–15)',[6,7,12,13,14,15]),('as in the paper (6, 7, 11–15)',[6,7,11,12,13,14,15]))}
L+=['']+[f'- Environmental minus social goal means, {nm}: original {a:+.2f}, newly captured {b:+.2f}.' for nm,(a,b) in es.items()]+['  (The pre-specification left goal 11 out of the environmental group by mistake; the paper includes it. Both are shown.)']
# ---- C combined estimate, sample weighted up to newly captured claims per report
ns=S_.groupby('report').size(); Sm['w']=Sm.report.map(lambda r: Nnew[r]/ns[r]); wt=Sm.w.sum()
def comb(d):
    out=[]
    for k in range(3): out.append(100*(((tier(O.SMTE)==k).sum()+(d.w*(tier(d.SMTE)==k)).sum())/(len(O)+d.w.sum())))
    return np.array(out)
cc=comb(Sm); ci=boot(Sm,comb)
L+=['\n## C. Combined estimate: tier shares if every newly captured claim had been scored',f'Newly captured claims: {sum(Nnew.values()):,}; estimated mapped and scorable among them: {wt:,.0f}. Combined with the 6,320 original claims:','\n| SMTE tier | published | combined estimate | 95% interval | difference |','|---|---|---|---|---|']+[f'| {TN[k]} | {so[k]:.1f}% | {cc[k]:.1f}% | {ci[0][k]:.1f}–{ci[1][k]:.1f} | {cc[k]-so[k]:+.1f} |' for k in range(3)]
dims=dict(zip(['S','M','T','E'],mn[:4])); low2=sorted(dims,key=dims.get)[:2]
crit=[('(i) each combined tier share within 5 points of the published share',bool((abs(cc-so)<=5).all()),'largest difference %.1f points'%abs(cc-so).max()),
      ('(ii) Measurability and Temporality the two lowest dimension means among newly captured claims',set(low2)=={'M','T'},'lowest two: '+', '.join(low2)),
      ('(iii) claim-type ordering: Spearman correlation at least 0.8 (types with at least 30 new claims)',bool(rho>=0.8),'rho = %.2f over %d types'%(rho,len(big))),
      ('(iv) environmental minus social difference has the same sign',all((a>0)==(b>0) for a,b in es.values()),'see above')]
L+=['\n## Pre-specified reading','| criterion | met | detail |','|---|---|---|']+[f'| {a} | {"yes" if b else "NO"} | {c} |' for a,b,c in crit]
# ---- D two reports in full
dm_=pd.read_csv('revision/audits/Audit3-resolved-matrix.csv',encoding='utf-8-sig'); decl={r.company:set(map(int,str(r.iloc[1]).split())) for _,r in dm_.iterrows() if str(r.iloc[1])!='nan'}
L+=['\n## D. Two reports with every newly captured claim scored (illustration, not a test)']
for rep in ('PTTGC-2024-IR-EN','SCC-2024-SR-EN'):
    o=O[O.report==rep]; co=o.company.iloc[0]; n=N[(N.report==rep)&N.in_full2]; nm_=n[n.mapped&n.complete]
    L+=[f'\n**{co}** — declared priorities (authors, resolved): {sorted(decl[co])}. Original scored claims {len(o)}; newly captured {len(n)}, mapped {int(n.mapped.sum())}, scored {len(nm_)}. SMTE tiers (unsub / partial / sub): original {" / ".join("%.0f%%"%x for x in sh(o))}; newly captured {" / ".join("%.0f%%"%x for x in sh(nm_))}.','\n| cells with ≥ 3 claims | set | cells | Rule A (mean ≥ 2.0) | Rule B (≥ 1 substantiated) | Rule B (≥ 3) | mean of cell means |','|---|---|---|---|---|---|---|']
    for lab,d in (('original claims',o),('original + newly captured',pd.concat([o[['goals','SMTE']],nm_[['goals','SMTE']]]))):
        e=d.explode('goals').dropna(subset=['goals']); e['goals']=e.goals.astype(int); g=e.groupby('goals').SMTE.agg(n='size',mean='mean',nsub=lambda x:(x>=2).sum())
        for dl,idx in (('declared',g.index.isin(decl[co])),('undeclared',~g.index.isin(decl[co]))):
            q=g[idx&(g.n>=3)]; L.append(f'| {dl} | {lab} | {len(q)} | {int((q["mean"]>=2).sum())} | {int((q.nsub>=1).sum())} | {int((q.nsub>=3).sum())} | {q["mean"].mean():.2f} |')
    e=pd.concat([o[['goals','SMTE']],nm_[['goals','SMTE']]]).explode('goals').dropna(subset=['goals']); e['goals']=e.goals.astype(int); g=e.groupby('goals').SMTE.agg(n='size',mean='mean',nsub=lambda x:(x>=2).sum())
    L.append('Declared goals after adding the new claims: '+'; '.join(f'SDG {k}: {int(g.n.get(k,0))} claims, mean {g["mean"].get(k,float("nan")):.2f}, {int(g.nsub.get(k,0))} substantiated' for k in sorted(decl[co])))
open(H+'RESULTS-extraction-rerun-PRELIMINARY.md','w').write('\n'.join(L)); print('\n'.join(L))
