"""Audit 2 (SDG mapping), both auditors. Rule: PRESPEC-audit-scoring-16Nov2026.md item 2. Run in revision/audits."""
import openpyxl, csv, re, math, collections
def wil(k,n,z=1.96):
    if n==0: return float('nan'),float('nan')
    p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return 100*(c-h),100*(c+h)
pc=lambda k,n:f'{k} of {n} ({100*k/n:.0f}%; {wil(k,n)[0]:.0f}–{wil(k,n)[1]:.0f}%)' if n else 'n/a'
K={int(r['#']):r for r in csv.DictReader(open('_keys-do-not-open/Audit2-SDG-mapping-KEY.csv',encoding='utf-8-sig'))}
F={i:[int(x) for x in r['framework goals'].split()] for i,r in K.items()}; FT={i:set(r['framework targets'].split()) for i,r in K.items()}
def load(w):
    G={};T={}
    for r in openpyxl.load_workbook(f'Audit2-SDG-mapping-{w}.xlsx')['Claims'].iter_rows(min_row=2,values_only=True):
        if r[0] is None: continue
        g=[];t=set()
        for v in r[4:7]:
            if v in (None,''): continue
            s=str(v).strip(); n=int(re.match(r'\d+',s).group())
            if 1<=n<=17 and n not in g: g.append(n)
            if '.' in s and not isinstance(v,float): t.add(s)
        G[int(r[0])]=g; T[int(r[0])]=t
    return G,T
A={w:load(w) for w in ('DNA','EE')}; ids=sorted(K); M=[i for i in ids if F[i]]; U=[i for i in ids if not F[i]]
L=['# Audit 2 — SDG mapping, both auditors, before resolution\n',f'120 claims: {len(M)} that the framework mapped to at least one goal and {len(U)} that it left unmapped (excluded from the corpus scores). Each auditor listed up to three goals per claim, or 0 for none, from the claim text and section title. EE gave targets; her goal is the number before the point. Intervals are Wilson 95%.\n']
# agreement between auditors
d,e=A['DNA'][0],A['EE'][0]
g1=sum((d[i][:1]==e[i][:1]) for i in ids); ov=sum(bool(set(d[i])&set(e[i])) or (not d[i] and not e[i]) for i in ids)
tp=sum(len(set(d[i])&set(e[i])) for i in ids); a=sum(len(d[i]) for i in ids); b=sum(len(e[i]) for i in ids); n=120*17; po=(n-a-b+2*tp)/n; pe=(a/n)*(b/n)+(1-a/n)*(1-b/n)
z=sum((not d[i])==(not e[i]) for i in ids)
L+=['## 1. Agreement between the two auditors',f'- Same first goal (or both none): {pc(g1,120)}.',f'- At least one goal in common (or both none): {pc(ov,120)}.',f'- Claim × goal cells (120 × 17 = 2,040): DNA lists {a}, EE lists {b}, both {tp}; agreement {100*po:.1f}%, Cohen’s κ {(po-pe)/(1-pe):.2f}.',f'- Whether the claim addresses any SDG: same answer for {pc(z,120)}; DNA says none for {sum(not d[i] for i in ids)}, EE for {sum(not e[i] for i in ids)}.\n']
def block(name,G):
    pairs=sum(len(F[i]) for i in M); ok=sum(len(set(F[i])&set(G[i])) for i in M)
    out=[f'### {name}',f'- Framework goal assignments confirmed by the auditor (goal-level precision): {pc(ok,pairs)}.',
     f'- Claims with at least one framework goal confirmed: {pc(sum(bool(set(F[i])&set(G[i])) for i in M),len(M))}.',
     f'- Framework’s first-listed goal confirmed: {pc(sum(F[i][0] in G[i] for i in M),len(M))}; auditor’s first goal is among the framework’s goals: {pc(sum(bool(G[i]) and G[i][0] in F[i] for i in M),len(M))}.',
     f'- Mapped claims the auditor says address no SDG: {pc(sum(not G[i] for i in M),len(M))}.',
     '- Missed goals (auditor names a goal the framework did not assign): '+'; '.join(f'{k} framework goal{"s" if k>1 else ""}: {pc(sum(bool(set(G[i])-set(F[i])) for i in M if len(F[i])==k),sum(len(F[i])==k for i in M))}' for k in (1,2,3))+f'; all: {pc(sum(bool(set(G[i])-set(F[i])) for i in M),len(M))}.',
     f'- Unmapped claims: auditor says no SDG (correctly excluded) {pc(sum(not G[i] for i in U),len(U))}; auditor names a goal (mappable) {pc(sum(bool(G[i]) for i in U),len(U))}.']
    return out
L+=['## 2. Framework mapping against each auditor']+block('Auditor DNA',d)+block('Auditor EE',e)
both={i:[g for g in d[i] if g in e[i]] for i in ids}; either={i:list(dict.fromkeys(d[i]+e[i])) for i in ids}
L+=block('Goals both auditors list (strict bound; not the resolved result)',both)+block('Goals either auditor lists (lenient bound)',either)
et=A['EE'][1]; tp_=sum(len(FT[i]) for i in M); tok=sum(len(FT[i]&et[i]) for i in M)
L+=['\n## 3. Target level (EE only; DNA gave goals)',f'- Framework target assignments that EE also lists: {pc(tok,tp_)}; claims with at least one target in common: {pc(sum(bool(FT[i]&et[i]) for i in M),len(M))}. EE could list at most three targets and the framework lists {tp_/len(M):.1f} per claim on average, so this is a lower bound on target-level precision.']
L+=['\n## Notes','- The auditors could list at most three goals; the framework assigns one to three goals to these claims, so the limit does not by itself lower precision.','- Goal-level precision here means the auditor independently named the same goal, which is stricter than judging a shown claim–goal pair as acceptable (the wording of the pre-specified measure). The form asked for independent listing so that missed goals could be measured.']
open('RESULTS-audit-2-both.md','w').write('\n'.join(L)); print('\n'.join(L))
w=csv.writer(open('Audit2-disagreements.csv','w',newline='',encoding='utf-8-sig')); w.writerow(['#','company','claim text','DNA goals','EE goals','EE note','AGREED goals (numbers, or 0)','reason'])
ws=openpyxl.load_workbook('Audit2-SDG-mapping-EE.xlsx')['Claims']; n=0
for r in ws.iter_rows(min_row=2,values_only=True):
    i=int(r[0])
    if set(d[i])!=set(e[i]): w.writerow([i,r[1],r[3],' '.join(map(str,d[i])) or '0',' '.join(map(str,e[i])) or '0',r[7],'','']); n+=1
print('claims with differing goal sets:',n)
