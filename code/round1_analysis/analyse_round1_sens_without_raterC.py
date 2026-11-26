"""Sensitivity: agreement among raters without RaterC (decided 16 Nov 2026 AFTER seeing her scores, so NOT pre-specified).
Same bootstrap as analyse_round1_ci.py (claims resampled within report, 2,000 replicates, seed 20261110). Run from project root."""
import numpy as np, pandas as pd, krippendorff
R=['RaterA','RaterB','RaterC','RaterD']
D={r:pd.read_csv(f'revision/round1-analysis/{r}-ratings.csv',keep_default_na=False,na_values=['']).set_index('claim_id') for r in R}
key=pd.read_csv('scorer/Round1-60-KEY-EN-do-not-send.csv').set_index('claim_id')
ids=sorted(D[R[0]].index,key=lambda x:int(x[1:])); rep=key.loc[ids,'report'].values; st=key.loc[ids,'set'].values
def tier(x): return np.where(x<1,0,np.where(x<2,1,2))
M={}
for r in R:
    d=D[r].loc[ids]; M[r]={k:d[k].values.astype(float) for k in 'SMTE'}; M[r]['C']=d['C_rater'].values.astype(float)
    M[r]['SMTE tier']=tier(sum(M[r][k] for k in 'SMTE')/4).astype(float)
def alpha(rs,m,idx): 
    a=np.array([M[r][m][idx] for r in rs])
    try: return krippendorff.alpha(reliability_data=a,level_of_measurement='ordinal')
    except Exception: return np.nan
rng=np.random.default_rng(20261110)
def boot(mask):
    base=np.where(mask)[0]; out=[]
    for _ in range(2000):
        out.append(np.concatenate([rng.choice(base[rep[base]==g],size=(rep[base]==g).sum(),replace=True) for g in np.unique(rep[base])]))
    return base,out
L=['# Round 1 — sensitivity without RaterC (not pre-specified; decided 16 Nov 2026 after her scores were seen)\n','Krippendorff ordinal α among raters, 95% bootstrap intervals (claims resampled within report, 2,000 replicates).\n']
for name,mask in [('all 60',np.ones(len(ids),bool)),('representative 50',st=='representative')]:
    base,bs=boot(mask); L+=[f'\n## {name}\n','| measure | all four raters | without RaterC (3 raters) | without RaterC and RaterD (the two consultants) |','|---|---|---|---|']
    for m in ['S','M','T','E','C','SMTE tier']:
        row=[]
        for rs in (R,['RaterA','RaterB','RaterD'],['RaterA','RaterB']):
            v=alpha(rs,m,base); b=[alpha(rs,m,i) for i in bs]; lo,hi=np.nanpercentile(b,[2.5,97.5]); row.append(f'{v:.2f} [{lo:.2f}, {hi:.2f}]')
        L.append(f'| {m} | '+' | '.join(row)+' |')
# Phase 1
J={'Unsubstantiated':0,'Partially substantiated':1,'Substantiated':2}
p=np.array([[J.get(x,np.nan) for x in D[r].loc[ids,'phase1_judgement']] for r in R]); rm=st=='representative'
L+=['\n## Phase 1 holistic judgement (50 claims)\n',f"α all four: {krippendorff.alpha(reliability_data=p[:,rm],level_of_measurement='ordinal'):.2f}; without RaterC: {krippendorff.alpha(reliability_data=p[[0,1,3]][:,rm],level_of_measurement='ordinal'):.2f}; without RaterB: {krippendorff.alpha(reliability_data=p[[0,2,3]][:,rm],level_of_measurement='ordinal'):.2f}."]
open('revision/round1-analysis/Round1-sensitivity-without-RaterC.md','w').write('\n'.join(L)); print('\n'.join(L))
