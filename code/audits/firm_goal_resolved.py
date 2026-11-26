"""Firm–goal rules recomputed with the auditors' resolved declaration matrix (Audit 3). Run from the project root.
Writes sdg-credibility-framework/data/outputs/revision/v4/firm_goal_rules_resolved.csv and declared_resolved.csv; frozen V4 scores are only read."""
import json, numpy as np, pandas as pd
R='sdg-credibility-framework/data/outputs/revision/'; OUT=R+'v4/'
m=pd.read_csv('revision/audits/Audit3-resolved-matrix.csv',encoding='utf-8-sig'); decl={r.company:set(map(int,str(r.iloc[1]).split())) if str(r.iloc[1])!='nan' else set() for _,r in m.iterrows()}
A=pd.read_csv(R+'claims_v4_flat.csv',keep_default_na=False,na_values=['']); det={c:set(map(int,str(v).split())) if isinstance(v,str) else set() for c,v in A.groupby('company').declared_goals.first().items()}
assert set(decl)==set(det),set(decl)^set(det)
pd.DataFrame([dict(company=c,declared_resolved=' '.join(map(str,sorted(decl[c]))),declared_detector=' '.join(map(str,sorted(det[c])))) for c in sorted(decl)]).to_csv(OUT+'declared_resolved.csv',index=False)
cells=pd.read_csv(OUT+'firm_goal_cells.csv'); cells['declared']=[g in decl[c] for c,g in zip(cells.company,cells.goal)]
nd=sum(len(v) for v in decl.values()); rows=[]
for comp in ('SMTE','SMTEC'):
    for k in (3,5):
        c=cells[cells.composite==comp]
        for lab,sub in (('declared',c[c.declared]),('undeclared',c[~c.declared])):
            e=sub[sub.n>=k]; rows.append({'composite':comp,'min claims':k,'cells':lab,'all cells':nd if lab=='declared' else 510-nd,'cells with enough claims':len(e),'Rule A: mean ≥ 2.0':int((e['mean']>=2).sum()),'Rule B: ≥ 1 substantiated claim':int((e.n_sub>=1).sum()),'Rule B (robust): ≥ 3':int((e.n_sub>=3).sum()),'median share substantiated %':e.share_sub.median()*100,'mean cell mean':e['mean'].mean()})
t=pd.DataFrame(rows); t.to_csv(OUT+'firm_goal_rules_resolved.csv',index=False); print(t.to_string())
c=cells[cells.composite=='SMTE']; d3=c[c.declared&(c.n>=3)]; u3=c[~c.declared&(c.n>=3)]
print('declared',nd,'with any mapped claim',int(c.declared.sum()),'fewer than 3: declared',int((c.declared&(c.n<3)).sum())+nd-int(c.declared.sum()),'undeclared',510-nd-len(u3))
print('declared>=3 max mean %.2f; profile S %.2f M %.2f T %.2f E %.2f; undeclared max %.2f'%(d3['mean'].max(),d3.S.mean(),d3.M.mean(),d3['T'].mean(),d3.E.mean(),u3['mean'].max()))
print('B share decl %.1f undecl %.1f ; B3 %.1f %.1f'%(100*(d3.n_sub>=1).mean(),100*(u3.n_sub>=1).mean(),100*(d3.n_sub>=3).mean(),100*(u3.n_sub>=3).mean()))
# detector vs resolved
tp=sum(len(decl[x]&det[x]) for x in decl); print('detector',sum(map(len,det.values())),'both',tp,'resolved only',nd-tp,'detector only',sum(map(len,det.values()))-tp)
# stricter Evidence
d=A[A.complete==1].copy(); st={x['uid']:x for x in json.load(open(R+'v4_E_strict_sensitivity.json'))['claims']}
d['E2']=[min(2,st[u]['E_strict_median']) if (e==2 and u in st and st[u].get('n_runs')==3) else e for u,e in zip(d.uid,d.E)]; d['SMTE2']=(d.S+d.M+d['T']+d.E2)/4
ex=d.assign(goal=d.goals.astype(str).str.split()).explode('goal'); ex['goal']=ex.goal.astype(int)
for col in ('SMTE','SMTE2'):
    g=ex.groupby(['company','goal']).agg(n=(col,'size'),mean=(col,'mean'),nsub=(col,lambda x:(x>=2).sum())).reset_index(); e=g[[gl in decl[c_] for c_,gl in zip(g.company,g.goal)]&(g.n>=3)]
    print(col,len(e),int((e['mean']>=2).sum()),int((e.nsub>=1).sum()),int((e.nsub>=3).sum()))
