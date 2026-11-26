"""Round 1 analysis for one returned rater (Phase 1 holistic + Phase 2 SMTEC) against frozen V4.
Usage: python3 revision/round1-analysis/analyse_round1_rater.py <RATER_CODE> <phase1.xlsx> <phase2.xlsx>
Outputs: revision/round1-analysis/<RATER>-results.md and <RATER>-ratings.csv (rater data; never released while Round 1 is open)."""
import sys, re, csv, json, collections, openpyxl
R, P1, P2 = sys.argv[1:4]
V4 = 'sdg-credibility-framework/data/outputs/revision/v4_round1_EN.json'
KEY = 'scorer/Round1-60-KEY-EN-do-not-send.csv'
SL = ['S1','S2','X1','X2','X3']; LABS = ['Extend','Redundant','Related','Unrelated','Contradicts','None']
TIERS = ['Unsubstantiated','Partially substantiated','Substantiated']
key = {r['claim_id']: r for r in csv.DictReader(open(KEY))}
v4 = {c['claim_id']: c for c in json.load(open(V4))['claims']}
def tier(x): return 0 if x < 1 else (1 if x < 2 else 2)
def wk(a, b, k):
    n=len(a); O=[[0]*k for _ in range(k)]
    for x,y in zip(a,b): O[x][y]+=1
    ra=[sum(r) for r in O]; cb=[sum(O[i][j] for i in range(k)) for j in range(k)]
    num=sum(((i-j)**2)*O[i][j] for i in range(k) for j in range(k)); den=sum(((i-j)**2)*ra[i]*cb[j]/n for i in range(k) for j in range(k))
    return (1-num/den if den else float('nan')), O
def mat(O, lab): return '| | ' + ' | '.join(lab) + ' |\n|' + '---|'*(len(lab)+1) + '\n' + '\n'.join(f'| {lab[i]} | ' + ' | '.join(str(v) for v in O[i]) + ' |' for i in range(len(O)))
# ---- Phase 1
ws=openpyxl.load_workbook(P1)['Forms']; p1={}; cur=None
for r in range(1,ws.max_row+1):
    a=str(ws.cell(r,1).value or '').strip(); m=re.match(r'#\s*\d+\s+(R\d+)',a)
    if m: cur=m.group(1); p1[cur]={}; continue
    if cur and a=='your_judgement': p1[cur]['j']=str(ws.cell(r,2).value or '').strip()
    if cur and a=='what_made_you_decide': p1[cur]['why']=str(ws.cell(r,2).value or '').strip()
crit=[str(openpyxl.load_workbook(P1)['READ ME FIRST'].cell(r,2).value or '') for r in (17,18,19)]
# ---- Phase 2
ws=openpyxl.load_workbook(P2)['Forms']; p2={}; cur=None
for r in range(1,ws.max_row+1):
    a=str(ws.cell(r,1).value or '').strip(); m=re.match(r'#\s*\d+\s+(R\d+)',a)
    if m: cur={'L':{},'sec':{}}; p2[m.group(1)]=cur; continue
    if cur is None: continue
    m=re.match(r'(S1|S2|X1|X2|X3) (same|cross)-section$',a)
    if m and m.group(1) not in cur['L']:
        cur['L'][m.group(1)]=str(ws.cell(r,10).value or '').strip() or 'MISSING'
        s=re.match(r'\[Section:\s*([^,\]]+)',str(ws.cell(r,2).value or '')); cur['sec'][m.group(1)]=s.group(1).strip() if s else None
    if a=='scores':
        for k,c in zip('SMTE',(3,5,7,9)):
            v=ws.cell(r,c).value
            try: cur[k]=int(str(v).strip())
            except: cur[k]=None
    if a=='comment': cur['comment']=str(ws.cell(r,2).value or '').strip()
def C(L,sec): return len({sec[s] for s in ('X1','X2','X3') if L.get(s)=='Extend' and sec.get(s)})
out=[f'# Round 1 — rater {R} vs frozen V4\n','Source and transcription notes: scorer/RECEIVED-Round1.md. V4 = frozen 30 Oct 2026, run on the EN form.\n']
# completeness
bad=[(i,k) for i in p2 for k in 'SMTE' if p2[i].get(k) not in (0,1,2,3)]+[(i,s,p2[i]['L'][s]) for i in p2 for s in SL if p2[i]['L'][s] not in LABS]
badp1=[i for i in p1 if p1[i].get('j') not in TIERS]
out.append(f'## Completeness\nPhase 1: {len(p1)} claims, invalid/missing judgements: {badp1 or "none"}. Phase 2: {len(p2)} claims, invalid/missing: {bad or "none"}.\n')
rep=[i for i in sorted(p2) if key[i]['set']=='representative']; chal=[i for i in sorted(p2) if key[i]['set']!='representative']
ok2=[i for i in sorted(p2) if all(p2[i].get(k) in (0,1,2,3) for k in 'SMTE')]
# ---- A. Phase 1 vs V4 tier
for comp in ('SMTE','SMTEC'):
    ids=[i for i in sorted(p1) if p1[i].get('j') in TIERS and i in v4]
    a=[TIERS.index(p1[i]['j']) for i in ids]; b=[tier(v4[i][comp]) for i in ids]
    k,O=wk(a,b,3)
    out.append(f'## A. Phase 1 holistic judgement vs V4 tier ({comp}), {len(ids)} representative claims\nExact {sum(x==y for x,y in zip(a,b))}/{len(ids)}; weighted κ {k:.2f}. Rows = rater, columns = V4.\n\n'+mat(O,['Unsub','Partial','Sub'])+'\n')
# ---- B. Phase 1 vs rater's own SMTEC-implied tier
for comp in ('SMTE','SMTEC'):
    ids=[i for i in sorted(p1) if p1[i].get('j') in TIERS and i in ok2]
    def comp_r(i): s=sum(p2[i][d] for d in 'SMTE'); return s/4 if comp=='SMTE' else (s+C(p2[i]['L'],p2[i]['sec']))/5
    a=[TIERS.index(p1[i]['j']) for i in ids]; b=[tier(comp_r(i)) for i in ids]
    k,O=wk(a,b,3)
    out.append(f'## B. Phase 1 holistic vs the rater\'s own Phase 2 tier ({comp}), {len(ids)} claims\nExact {sum(x==y for x,y in zip(a,b))}/{len(ids)}; weighted κ {k:.2f}. Rows = holistic, columns = own SMTEC-implied tier.\n\n'+mat(O,['Unsub','Partial','Sub'])+'\n')
# ---- C. Phase 2 per dimension vs V4
for name,ids in (('all 60',ok2),('representative 50',[i for i in ok2 if i in rep]),('challenge 10',[i for i in ok2 if i in chal])):
    out.append(f'## C. Phase 2 dimensions, rater vs V4 — {name} (n={len(ids)})\n| Dim | exact | within 1 | weighted κ | mean rater | mean V4 |\n|---|---|---|---|---|---|')
    for d in 'SMTE':
        a=[p2[i][d] for i in ids]; b=[v4[i][d] for i in ids]; k,_=wk(a,b,4)
        out.append(f'| {d} | {sum(x==y for x,y in zip(a,b))}/{len(ids)} | {sum(abs(x-y)<=1 for x,y in zip(a,b))}/{len(ids)} | {k:.2f} | {sum(a)/len(a):.2f} | {sum(b)/len(b):.2f} |')
    out.append('')
out.append('### Confusion matrices, all 60 (rows rater 0–3, columns V4 0–3)')
for d in 'SMTE':
    _,O=wk([p2[i][d] for i in ok2],[v4[i][d] for i in ok2],4); out.append(f'\n{d}\n\n'+mat(O,['0','1','2','3']))
# ---- D. labels and C
pairs=[(p2[i]['L'][s], v4[i]['labels'][s]) for i in ok2 for s in SL if not (p2[i]['L'][s]=='None' and v4[i]['labels'][s]=='None')]
cm=collections.Counter(pairs)
out.append(f'\n## D. Passage labels ({len(pairs)} passages)\nExact agreement {sum(a==b for a,b in pairs)}/{len(pairs)}. Rows = rater, columns = V4.\n\n| | '+' | '.join(LABS)+' |\n|'+'---|'*(len(LABS)+1))
for x in LABS: out.append(f'| {x} | '+' | '.join(str(cm[(x,y)]) for y in LABS)+' |')
tot_r=collections.Counter(a for a,_ in pairs); tot_v=collections.Counter(b for _,b in pairs)
out.append(f'\nTotals — rater: {dict(tot_r)}; V4: {dict(tot_v)}')
ca=[C(p2[i]['L'],p2[i]['sec']) for i in ok2]; cb=[C(v4[i]['labels'],p2[i]['sec']) for i in ok2]; k,O=wk(ca,cb,4)
out.append(f'\nC (computed from labels, same section rule): exact {sum(x==y for x,y in zip(ca,cb))}/{len(ok2)}, weighted κ {k:.2f}, mean rater {sum(ca)/len(ca):.2f}, mean V4 {sum(cb)/len(cb):.2f}.\n\n'+mat(O,['0','1','2','3']))
# ---- E. composite tiers rater vs V4
for comp in ('SMTE','SMTEC'):
    def cr(i): s=sum(p2[i][d] for d in 'SMTE'); return s/4 if comp=='SMTE' else (s+C(p2[i]['L'],p2[i]['sec']))/5
    a=[tier(cr(i)) for i in ok2]; b=[tier(v4[i][comp]) for i in ok2]; k,O=wk(a,b,3)
    out.append(f'\n## E. Composite tier, rater SMTEC scores vs V4 ({comp}), n={len(ok2)}\nExact {sum(x==y for x,y in zip(a,b))}/{len(ok2)}; weighted κ {k:.2f}.\n\n'+mat(O,['Unsub','Partial','Sub']))
out.append(f'\n## Rater criteria for the three levels (Phase 1, READ ME)\n- Substantiated: {crit[2] if False else crit[0]}\n- Partially substantiated: {crit[1]}\n- Unsubstantiated: {crit[2]}')
open(f'revision/round1-analysis/{R}-results.md','w').write('\n'.join(out))
with open(f'revision/round1-analysis/{R}-ratings.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['claim_id','set','claim_type','phase1_judgement','phase1_why','S','M','T','E']+[f'label_{s}' for s in SL]+['C_rater','comment','V4_S','V4_M','V4_T','V4_E']+[f'V4_label_{s}' for s in SL]+['V4_C','V4_SMTE','V4_SMTEC','theme'])
    for i in sorted(p2):
        p=p2[i]; v=v4[i]
        w.writerow([i,key[i]['set'],key[i]['claim_type'],p1.get(i,{}).get('j',''),p1.get(i,{}).get('why',''),p.get('S'),p.get('M'),p.get('T'),p.get('E')]+[p['L'][s] for s in SL]+[C(p['L'],p['sec']),p.get('comment','')]+[v[d] for d in 'SMTE']+[v['labels'][s] for s in SL]+[C(v['labels'],p['sec']),v['SMTE'],v['SMTEC'],''])
print('\n'.join(out))
