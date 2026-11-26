"""Audit 3, both auditors: agreement DNA vs EE, each vs detector, and firm-goal rules under each matrix.
Run from project root: python3 revision/audits/score_audit3_both.py"""
import re, openpyxl, pandas as pd
AD='revision/audits/'; k3=pd.read_csv(AD+'_keys-do-not-open/Audit3-Declared-priorities-KEY.csv').set_index('company')
def load(f):
    out={}
    for r in openpyxl.load_workbook(f)['Reports'].iter_rows(min_row=2,values_only=True):
        if not r[1]: continue
        broad={int(x) for x in re.findall(r'\d+',str(r[4] or '')) if 1<=int(x)<=17}
        mm=re.match(r'\s*([\d,\s]+?)\s*(?:are|is)\s+(?:the\s+)?major',str(r[6] or ''))
        out[r[1]]=dict(broad=broad,strict={int(x) for x in re.findall(r'\d+',mm.group(1))} if mm else set(broad))
    return out
D=load(AD+'Audit3-Declared-priorities-DNA.xlsx'); E=load(AD+'Audit3-Declared-priorities-EE.xlsx'); assert set(D)==set(E) and len(D)==30
FW={c:({int(x) for x in str(k3.loc[c,'framework declared SDGs']).split() if x.isdigit()} if str(k3.loc[c,'framework declared SDGs'])!='nan' else set()) for c in D}
def cmp(a,b,la,lb):
    tp=sum(len(a[c]&b[c]) for c in a); fn=sum(len(a[c]-b[c]) for c in a); fp=sum(len(b[c]-a[c]) for c in a); tn=510-tp-fn-fp
    po=(tp+tn)/510; pa=(tp+fn)/510; pb=(tp+fp)/510; pe=pa*pb+(1-pa)*(1-pb)
    return f'| {la} vs {lb} | {tp+fn} | {tp+fp} | {tp} | {fn} | {fp} | {100*po:.1f}% | {(po-pe)/(1-pe):.2f} | {sum(a[c]==b[c] for c in a)} |'
M={'DNA strict':{c:D[c]['strict'] for c in D},'DNA broad':{c:D[c]['broad'] for c in D},'EE':{c:E[c]['strict'] for c in E},'detector':FW}
M['both auditors']={c:M['DNA strict'][c]&M['EE'][c] for c in D}; M['either auditor']={c:M['DNA strict'][c]|M['EE'][c] for c in D}
L=['# Audit 3 — declared SDG priorities, both auditors, before resolution\n','510 cells (30 reports × 17 goals). EE marks no major/minor levels, so her strict and broad sets are the same.\n','| comparison (first vs second) | first declares | second declares | both | first only | second only | cell agreement | κ | identical reports of 30 |','|---|---|---|---|---|---|---|---|---|']
for a,b in (('DNA strict','EE'),('DNA broad','EE'),('DNA strict','detector'),('EE','detector'),('both auditors','detector'),('either auditor','detector')): L.append(cmp(M[a],M[b],a,b))
cells=pd.read_csv('release/data/revision/v4/firm_goal_cells.csv'); cells=cells[cells.composite=='SMTE']
L+=['\n## Firm–goal rules (SMTE, cells with at least 3 claims) under each declaration matrix','| declared according to | declared cells | with ≥3 claims | Rule A (mean ≥ 2.0) | Rule B (≥1 substantiated) | Rule B (≥3) | median share substantiated | undeclared ≥3 claims: n / Rule B / ≥3 |','|---|---|---|---|---|---|---|---|']
for n in ('detector','DNA strict','EE','both auditors','either auditor'):
    d=cells.apply(lambda r:int(r.goal) in M[n][r.company],axis=1); e=cells[d&(cells.n>=3)]; u=cells[~d&(cells.n>=3)]
    L.append(f'| {n} | {sum(len(v) for v in M[n].values())} | {len(e)} | {int((e["mean"]>=2).sum())} | {int((e.n_sub>=1).sum())} ({100*(e.n_sub>=1).mean():.0f}%) | {int((e.n_sub>=3).sum())} ({100*(e.n_sub>=3).mean():.0f}%) | {100*e.share_sub.median():.1f}% | {len(u)} / {int((u.n_sub>=1).sum())} ({100*(u.n_sub>=1).mean():.0f}%) / {int((u.n_sub>=3).sum())} ({100*(u.n_sub>=3).mean():.0f}%) |')
L+=['\n## Reports where the two auditors differ','| company | DNA only | EE only | n DNA | n EE |','|---|---|---|---|---|']
for c in D:
    a,b=M['DNA strict'][c],M['EE'][c]
    if a!=b: L.append(f'| {c} | {" ".join(map(str,sorted(a-b))) or "–"} | {" ".join(map(str,sorted(b-a))) or "–"} | {len(a)} | {len(b)} |')
open(AD+'RESULTS-audit-3-both.md','w').write('\n'.join(L)); print('\n'.join(L))
