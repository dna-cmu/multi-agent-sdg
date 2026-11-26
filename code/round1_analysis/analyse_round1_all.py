"""Round 1 across raters: Phase 1 inter-rater agreement, Phase 2 inter-rater agreement, each rater vs frozen V4.
Run from project root: python3 revision/round1-analysis/analyse_round1_all.py  -> revision/round1-analysis/Round1-all-raters.md"""
import glob, re, csv, json, itertools, collections, openpyxl, krippendorff, numpy as np
BASE='scorer/Results/Expert Opinion'; V4='sdg-credibility-framework/data/outputs/revision/v4_round1_EN.json'
key={r['claim_id']:r for r in csv.DictReader(open('scorer/Round1-60-KEY-EN-do-not-send.csv'))}
v4={c['claim_id']:c for c in json.load(open(V4))['claims']}
TI=['Unsubstantiated','Partially substantiated','Substantiated']; SL=['S1','S2','X1','X2','X3']; LAB=['Extend','Redundant','Related','Unrelated','Contradicts','None']
def tier(x): return 0 if x<1 else (1 if x<2 else 2)
def p1(f):
    ws=openpyxl.load_workbook(f)['Forms']; j={}; cur=None
    for r in range(1,ws.max_row+1):
        a=str(ws.cell(r,1).value or '').strip(); m=re.match(r'#\s*\d+\s+(R\d+)',a)
        if m: cur=m.group(1); continue
        if cur and a=='your_judgement':
            v=str(ws.cell(r,2).value or '').strip()
            if v in TI: j[cur]=TI.index(v)
    return j
def p2(f):
    ws=openpyxl.load_workbook(f)['Forms']; d={}; cur=None
    for r in range(1,ws.max_row+1):
        a=str(ws.cell(r,1).value or '').strip(); m=re.match(r'#\s*\d+\s+(R\d+)',a)
        if m: cur={'L':{},'sec':{}}; d[m.group(1)]=cur; continue
        if cur is None: continue
        m=re.match(r'(S1|S2|X1|X2|X3) (same|cross)-section$',a)
        if m and m.group(1) not in cur['L']:
            cur['L'][m.group(1)]=str(ws.cell(r,10).value or '').strip()
            s=re.match(r'\[Section:\s*([^,\]]+)',str(ws.cell(r,2).value or '')); cur['sec'][m.group(1)]=s.group(1).strip() if s else None
        if a=='scores':
            for k,c in zip('SMTE',(3,5,7,9)):
                try: cur[k]=int(str(ws.cell(r,c).value).strip())
                except: cur[k]=None
    for i,c in d.items(): c['C']=len({c['sec'][s] for s in ('X1','X2','X3') if c['L'].get(s)=='Extend' and c['sec'].get(s)})
    return d
def C_v4(i,sec): return len({sec[s] for s in ('X1','X2','X3') if v4[i]['labels'][s]=='Extend' and sec.get(s)})
def wk(a,b,k):
    n=len(a); O=np.zeros((k,k))
    for x,y in zip(a,b): O[x][y]+=1
    E=np.outer(O.sum(1),O.sum(0))/n; W=np.array([[(i-j)**2 for j in range(k)] for i in range(k)])
    return 1-(W*O).sum()/(W*E).sum() if (W*E).sum() else float('nan')
def alpha(rows,level):  # rows: list of per-rater lists (None = missing)
    arr=np.array([[np.nan if v is None else v for v in r] for r in rows],dtype=float)
    if np.all(np.isnan(arr)): return float('nan')
    return krippendorff.alpha(reliability_data=arr,level_of_measurement=level)
import sys
BOTH='--both' in sys.argv
P1={}; P2={}
for f in glob.glob(f'{BASE}/*/*Phase1*.xlsx'): P1[f.split('/')[-2]]=p1(f)
for f in glob.glob(f'{BASE}/*/*Phase2*.xlsx'): P2[f.split('/')[-2]]=p2(f)
out=['# Round 1 — '+('raters who completed both phases' if BOTH else 'all returned raters')+' (as of run)\n','RaterB Phase 2 was transcribed from handwriting (scorer/RECEIVED-Round1.md); 2 unreadable cells were confirmed by DNA (R11 S = 2, R44 X3 = Related).\n','V4 frozen 30 Oct 2026. Descriptive; never used to calibrate V4 (FREEZE-V4-30Oct2026.md). RaterD = development Expert 2 (not independent).\n']
out.append('## Returns\n| Rater | Phase 1 judged (of 50) | Phase 2 scored (of 60) |\n|---|---|---|')
for r in sorted(set(P1)|set(P2)|{'RaterB'}):
    out.append(f"| {r} | {len(P1.get(r,{}))} | {sum(1 for c in P2.get(r,{}).values() if all(c.get(k) in (0,1,2,3) for k in 'SMTE')) if r in P2 else ('PDF, handwritten — not yet transcribed' if r=='RaterB' else '—')} |")
use1=[r for r in sorted(P1) if len(P1[r])>=45 and (not BOTH or r in P2)]
ids1=sorted(key, key=lambda x:int(x[1:]))[:50]; ids1=[i for i in ids1 if key[i]['set']=='representative']
out.append(f'\n## Phase 1 — overall judgements (raters with ≥45 of 50: {", ".join(use1)})\n| Rater | Unsub | Partial | Sub |\n|---|---|---|---|')
for r in use1: c=collections.Counter(P1[r].values()); out.append(f'| {r} | {c[0]} | {c[1]} | {c[2]} |')
c=collections.Counter(tier(v4[i]['SMTE']) for i in ids1); out.append(f'| V4 (SMTE tier) | {c[0]} | {c[1]} | {c[2]} |')
a_all=alpha([[P1[r].get(i) for i in ids1] for r in use1],'ordinal')
a_nw=alpha([[P1[r].get(i) for i in ids1] for r in use1 if r!='RaterD'],'ordinal')
out.append(f'\nKrippendorff α (ordinal) among raters: {a_all:.2f} (all {len(use1)}); {a_nw:.2f} (without RaterD).')
out.append('\nPairwise weighted κ (quadratic), and each rater vs V4 tier (SMTE):\n\n| | '+' | '.join(use1)+' | V4 |\n|'+'---|'*(len(use1)+2))
for r in use1:
    row=[]
    for s in use1:
        if s==r: row.append('—'); continue
        ii=[i for i in ids1 if i in P1[r] and i in P1[s]]; row.append(f'{wk([P1[r][i] for i in ii],[P1[s][i] for i in ii],3):.2f}')
    ii=[i for i in ids1 if i in P1[r]]; row.append(f'{wk([P1[r][i] for i in ii],[tier(v4[i]["SMTE"]) for i in ii],3):.2f}')
    out.append(f'| {r} | '+' | '.join(row)+' |')
use2=[r for r in sorted(P2)]
ids2=sorted(key, key=lambda x:int(x[1:]))
out.append(f'\n## Phase 2 — SMTEC (raters: {", ".join(use2)}; n = 60 claims)\n| Dim | α among raters (ordinal) | '+' | '.join(f'κ {r} vs V4' for r in use2)+' | '+' | '.join(f'mean {r}' for r in use2)+' | mean V4 |\n|'+'---|'*(3+2*len(use2)))
for d in 'SMTEC':
    a=alpha([[P2[r][i].get(d) for i in ids2] for r in use2],'ordinal')
    ks=[]; ms=[]
    for r in use2:
        ii=[i for i in ids2 if P2[r][i].get(d) is not None]
        x=[P2[r][i][d] for i in ii]; y=[v4[i][d] if d!='C' else C_v4(i,P2[r][i]['sec']) for i in ii]
        ks.append(f'{wk(x,y,4):.2f}'); ms.append(f'{np.mean(x):.2f}')
    yv=[v4[i][d] if d!='C' else C_v4(i,P2[use2[0]][i]['sec']) for i in ids2]
    out.append(f'| {d} | {a:.2f} | '+' | '.join(ks)+' | '+' | '.join(ms)+f' | {np.mean(yv):.2f} |')
labs=[[LAB.index(P2[r][i]['L'][s]) if P2[r][i]['L'][s] in LAB else None for i in ids2 for s in SL] for r in use2]
out.append(f'\nPassage labels, α among raters (nominal, all slots incl. None): {alpha(labs,"nominal"):.2f}')
for r in use2:
    pr=[(P2[r][i]['L'][s],v4[i]['labels'][s]) for i in ids2 for s in SL if not (P2[r][i]['L'][s]=='None' and v4[i]['labels'][s]=='None')]
    ext=sum(1 for a,_ in pr if a=='Extend')
    out.append(f'- {r}: label agreement with V4 {sum(a==b for a,b in pr)}/{len(pr)}; Extend used {ext}/{len(pr)} ({100*ext/len(pr):.0f}%)')
pr=[(v4[i]['labels'][s]) for i in ids2 for s in SL if v4[i]['labels'][s]!='None']; out.append(f'- V4: Extend {sum(1 for x in pr if x=="Extend")}/{len(pr)} ({100*sum(1 for x in pr if x=="Extend")/len(pr):.0f}%)')
if len(use2)>=2:
    r1,r2=use2[:2]; pr=[(P2[r1][i]['L'][s],P2[r2][i]['L'][s]) for i in ids2 for s in SL if not (P2[r1][i]['L'][s]=='None' and P2[r2][i]['L'][s]=='None')]
    out.append(f'- {r1} vs {r2}: label agreement {sum(a==b for a,b in pr)}/{len(pr)}')
aC=alpha([[P2[r][i]['C'] for i in ids2] for r in use2],'ordinal')
out.append(f'\n**Pre-registered headline rule:** α for C among raters = {aC:.2f} ({"≥" if aC>=0.667 else "<"} 0.667) → headline composite = **{"SMTEC" if aC>=0.667 else "SMTE"}** (provisional: {len(use2)} raters).')
def ok(r,i): return all(P2[r][i].get(d) in (0,1,2,3) for d in 'SMTE')
for comp in ('SMTE','SMTEC'):
    def cr(r,i): s=sum(P2[r][i][d] for d in 'SMTE'); return s/4 if comp=='SMTE' else (s+P2[r][i]['C'])/5
    a=alpha([[tier(cr(r,i)) if ok(r,i) else None for i in ids2] for r in use2],'ordinal')
    ks=[]
    for r in use2:
        ii=[i for i in ids2 if ok(r,i)]
        ks.append(f'{r} vs V4 κ {wk([tier(cr(r,i)) for i in ii],[tier(v4[i][comp]) if comp=="SMTE" else tier((sum(v4[i][d] for d in "SMTE")+C_v4(i,P2[r][i]["sec"]))/5) for i in ii],3):.2f}')
    out.append(f'- Tier from {comp}: α among raters {a:.2f}; '+'; '.join(ks))
out.append('\n## Within each rater: Phase 1 overall judgement vs own Phase 2 tier (50 representative claims)\n| Rater | exact (SMTE) | κ (SMTE) | exact (SMTEC) | κ (SMTEC) | Spearman ρ with own SMTE | holistic Sub / own SMTE Sub |\n|---|---|---|---|---|---|---|')
from scipy.stats import spearmanr
for r in [x for x in use2 if x in P1 and len(P1[x])>=45]:
    ii=[i for i in ids1 if i in P1[r] and ok(r,i)]
    h=[P1[r][i] for i in ii]; sm=[sum(P2[r][i][d] for d in 'SMTE')/4 for i in ii]; sc=[(sum(P2[r][i][d] for d in 'SMTE')+P2[r][i]['C'])/5 for i in ii]
    t1=[tier(x) for x in sm]; t2=[tier(x) for x in sc]
    out.append(f'| {r} | {sum(a==b for a,b in zip(h,t1))}/{len(ii)} | {wk(h,t1,3):.2f} | {sum(a==b for a,b in zip(h,t2))}/{len(ii)} | {wk(h,t2,3):.2f} | {spearmanr(h,sm).correlation:.2f} | {h.count(2)} / {t1.count(2)} |')
open('revision/round1-analysis/Round1-'+('both-phases' if BOTH else 'all-raters')+'.md','w').write('\n'.join(out)); print('\n'.join(out))
