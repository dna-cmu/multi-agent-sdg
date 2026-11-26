"""Checks E to H of the addendum to PRESPEC-extraction-rerun-26Nov2026.md. Run from the project root."""
import json, re, csv, collections, numpy as np, pandas as pd, openpyxl
H='revision/extraction-rerun/'; W=H+'work/'; FW='sdg-credibility-framework/data/outputs/'; AUD='revision/audits/'
def words(t): return frozenset(w for w in re.sub(r"[^a-z0-9% ]"," ",str(t).lower().replace("\n"," ")).split() if len(w)>2)
def load(fn):
    out=collections.defaultdict(list); seen=set()
    for w in sorted((json.loads(l) for l in open(W+fn)),key=lambda w:(w['report'],w['w'])):
        for c in w['claims']:
            t=str(c.get('claim_text') or '').strip()
            if t and (w['report'],t) not in seen: seen.add((w['report'],t)); out[w['report']].append((words(t),w['w'],w['p0'],w['p1']))
    return out
def same(a,b,th=0.8): return bool(a and b) and (len(a&b)/len(a)>=th or len(a&b)/len(b)>=th)
def found(a,pool,idx):
    """is word set a matched by any claim in pool (list of sets); idx: word -> positions, for speed"""
    cand=collections.Counter()
    for w in a:
        for j in idx.get(w,()): cand[j]+=1
    return any(same(a,pool[j]) for j,_ in cand.most_common(15))
def index(pool):
    idx=collections.defaultdict(list)
    for j,s in enumerate(pool):
        for w in s: idx[w].append(j)
    return idx
P1=load('windows.jsonl'); P2=load('windows_pass2.jsonl'); L=['\n# Further checks (addendum E to H) — PRELIMINARY\n']
n1=n2=f12=f21=0; O_found={}
for rep in sorted(P1):
    a=[x[0] for x in P1[rep]]; b=[x[0] for x in P2[rep]]; ia,ib=index(a),index(b)
    n1+=len(a); n2+=len(b); f12+=sum(found(x,b,ib) for x in a); f21+=sum(found(x,a,ia) for x in b)
    full=json.load(open(FW+f'main/full/{rep}_full.json'))
    for c in full['claims']:
        s=words(c['claim_text']); O_found[f"{rep}::{c['claim_id']}"]=(found(s,a,ia),found(s,b,ib))
L+=['## E. Repeatability of extraction (identical settings and windows, run twice)',f'- Pass 1: {n1:,} claims; pass 2: {n2:,} claims.',f'- Pass-1 claims found again in pass 2: {f12:,} ({100*f12/n1:.0f}%); pass-2 claims found in pass 1: {f21:,} ({100*f21/n2:.0f}%).',f'- Union of the two passes: about {n1+n2-f21:,} distinct claims ({100*(n1+n2-f21)/n1-100:.0f}% more than one pass).']
of=np.array(list(O_found.values())); L.append(f'- Original 6,936 claims found again: in pass 1 {100*of[:,0].mean():.0f}%, in pass 2 {100*of[:,1].mean():.0f}%, in either {100*of.any(1).mean():.0f}%, in both {100*of.all(1).mean():.0f}%.')
# recall of each pass and of the union on the audit sets
D={(r['pair'],r['slot']):r for r in csv.DictReader(open(AUD+'Audit6-scored-DNA.csv'))}
R={(r['pair'],r['slot']):r['resolved'] for r in csv.DictReader(open(AUD+'Audit6-resolution-DNA-EE.csv',encoding='utf-8-sig')) if r['pair']!='general'}
def cap(P,rep,text):
    s=words(text); return any(c[0] and s and len(c[0]&s)/min(len(c[0]),len(s))>=0.6 for c in P.get(rep,[]))
t=collections.Counter()
for k,d in D.items():
    v=R.get(k) or ('claim' if d['judged_claim']=='1' else 'not claim'); c1,c2=cap(P1,d['report'],d['sentence']),cap(P2,d['report'],d['sentence'])
    for nm,c in (('p1',c1),('p2',c2),('union',c1 or c2)): t[(d['source'],v,nm)]+=c
    t[(d['source'],v,'n')]+=1
L+=['\n| pair-audit sentences (resolved) | n | captured: pass 1 | pass 2 | either pass |','|---|---|---|---|---|']
for s,lab in (('E','claims, previously extracted'),('N','claims, previously passed over in text that was read'),('F','claims, in text previously not read')): L.append(f"| {lab} | {t[(s,'claim','n')]} | {t[(s,'claim','p1')]} | {t[(s,'claim','p2')]} | {t[(s,'claim','union')]} |")
tot=lambda v,nm: sum(t[(s,v,nm)] for s in 'ENF')
L.append(f"| all claims | {tot('claim','n')} | {tot('claim','p1')} | {tot('claim','p2')} | {tot('claim','union')} |"); L.append(f"| all sentences judged not claims | {tot('not claim','n')} | {tot('not claim','p1')} | {tot('not claim','p2')} | {tot('not claim','union')} |")
ws=openpyxl.load_workbook(AUD+'reduced/Audit1-Extraction-reduced-DNA.xlsx')['Your claims']; A1=[(r[0],int(r[1]),str(r[2])) for r in ws.iter_rows(min_row=2,values_only=True) if r[0] and r[2] and str(r[2]).strip().lower()!='none']
def a1(P,span,page,text):
    rep=re.sub(r'-p\d+-\d+$','',span); s=words(text)
    for c in P.get(rep,[]):
        try: lo,hi=int(c[2]),int(c[3])
        except Exception: continue
        if lo-1<=page<=hi+1 and c[0] and len(c[0]&s)/len(c[0])>=0.6: return True
    return False
h1=[a1(P1,*x) for x in A1]; h2=[a1(P2,*x) for x in A1]
L.append(f"\n- Auditor 1's 30 listed claims captured: pass 1 {sum(h1)}, pass 2 {sum(h2)}, either {sum(x or y for x,y in zip(h1,h2))} (original run 4).")
# ---- F
A=pd.read_csv(FW+'revision/claims_v4_flat.csv',keep_default_na=False,na_values=['']); O=A[A.complete==1].copy(); O['again']=O.uid.map(lambda u:O_found[u][0]); O['again2']=O.uid.map(lambda u:O_found[u][0] and O_found[u][1])
tier=lambda x: np.where(x<1,0,np.where(x<2,1,2)); sh=lambda d:' / '.join('%.1f'%((tier(d.SMTE)==k).mean()*100) for k in range(3))
L+=['\n## F. Original claims found again against those not found again (existing Version 4 scores)','| group | n | SMTE tiers unsub / partial / sub (%) | S | M | T | E | SMTE | commitment | achievement | metric | policy | alignment |','|---|---|---|---|---|---|---|---|---|---|---|---|---|']
for lab,d in (('found again (pass 1)',O[O.again]),('not found again',O[~O.again]),('found in both passes',O[O.again2])):
    ct=d.claim_type.value_counts(normalize=True)*100
    L.append(f"| {lab} | {len(d)} | {sh(d)} | {d.S.mean():.2f} | {d.M.mean():.2f} | {d['T'].mean():.2f} | {d.E.mean():.2f} | {d.SMTE.mean():.2f} | "+' | '.join('%.0f%%'%ct.get(k,0) for k in ('commitment','achievement','metric','policy','alignment'))+' |')
byt=O.groupby('claim_type').again.agg(['mean','size']); L.append('- Share found again by claim type: '+'; '.join(f"{k} {100*r['mean']:.0f}% (n = {int(r['size'])})" for k,r in byt.sort_values('size',ascending=False).head(6).iterrows())+'.')
# ---- G
rm=json.load(open(W+'remap.json')); v=list(rm.values()); o=[set(x['orig']) for x in v]; g=[set(x['again']) for x in v]; n=len(v)
both=sum(bool(a) and bool(b) for a,b in zip(o,g)); cells=n*17; tp=sum(len(a&b) for a,b in zip(o,g)); na=sum(map(len,o)); nb=sum(map(len,g)); po=(cells-na-nb+2*tp)/cells; pe=(na/cells)*(nb/cells)+(1-na/cells)*(1-nb/cells)
L+=['\n## G. Repeatability of mapping (300 original claims mapped again)',f'- Mapped to at least one goal: first time {sum(map(bool,o))}, second time {sum(map(bool,g))}, both times {both}; same mapped / not mapped status for {sum(bool(a)==bool(b) for a,b in zip(o,g))} of {n}.',f'- Identical set of goals: {sum(a==b for a,b in zip(o,g))} of {n} ({100*sum(a==b for a,b in zip(o,g))/n:.0f}%); at least one goal in common among claims mapped both times: {sum(bool(a&b) for a,b in zip(o,g) if a and b)} of {both}.',f'- Goals per claim: {na/n:.2f} and {nb/n:.2f}; goal assignments kept: {tp} of {na} ({100*tp/na:.0f}%). Claim × goal cells: agreement {100*po:.1f}%, Cohen’s κ {(po-pe)/(1-pe):.2f}.']
# ---- H
N=pd.read_json(W+'rerun_scored_flat.json'); S=N[N.in_sample&N.mapped&N.complete].copy(); O['goals']=O.goals.astype(str).str.split().apply(lambda z:[int(x) for x in z])
ENV=[6,7,11,12,13,14,15]; SOC=[1,2,3,4,5,8,10,16]; wts=O.claim_type.value_counts(normalize=True)
def es(d,std=False):
    e=d[['goals','SMTE','claim_type']].explode('goals').dropna(subset=['goals']); e['goals']=e.goals.astype(int)
    if not std: gm=e.groupby('goals').SMTE.mean()
    else:
        m=e.groupby(['goals','claim_type']).SMTE.mean().unstack(); w=wts.reindex(m.columns).fillna(0); gm=(m*w).sum(1)/((~m.isna())*w).sum(1)
    return gm[gm.index.isin(ENV)].mean(),gm[gm.index.isin(SOC)].mean()
L+=['\n## H. Environmental (6, 7, 11–15) against social (1–5, 8, 10, 16) goal means','| | original: env | soc | difference | newly captured: env | soc | difference |','|---|---|---|---|---|---|---|']
for lab,std in (('unstandardised',False),('standardised for claim type',True)):
    a,b=es(O,std); c,d=es(S,std); L.append(f'| {lab} | {a:.2f} | {b:.2f} | {a-b:+.2f} | {c:.2f} | {d:.2f} | {c-d:+.2f} |')
e=S[['goals','SMTE']].explode('goals').dropna(subset=['goals']); e['goals']=e.goals.astype(int); gs=e.groupby('goals').SMTE.agg(['mean','size']); eo=O[['goals','SMTE']].explode('goals'); eo['goals']=eo.goals.astype(int); go=eo.groupby('goals').SMTE.mean()
L.append('- Goal means, original → newly captured (n in sample): '+'; '.join(f"SDG {k}: {go[k]:.2f} → {gs['mean'].get(k,float('nan')):.2f} ({int(gs['size'].get(k,0))})" for k in range(1,18))+'.')
open(H+'RESULTS-extraction-rerun-PRELIMINARY.md','a').write('\n'.join(L)); print('\n'.join(L))
