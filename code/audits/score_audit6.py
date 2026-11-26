"""Score Audit 6 (claim / not-claim pairs) for one auditor. Rule: PRESPEC addendum 24 Nov 2026.
usage: python3 score_audit6.py Audit6-answers-DNA.csv"""
import csv, sys, math, collections
def wilson(k, n, z=1.96):
    if n == 0: return (float('nan'),)*2
    p = k/n; d = 1+z*z/n
    c = (p+z*z/(2*n))/d; h = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return c-h, c+h
key = {(int(r['pair']), r['slot']): r for r in csv.DictReader(open('_keys-do-not-open/Audit6-Claim-or-not-KEY.csv', encoding='utf-8-sig'))}
ans = {int(r['pair']): r['answer'].strip() for r in csv.DictReader(open(sys.argv[1], encoding='utf-8-sig'))}
tot = collections.Counter(); yes = collections.Counter(); rows = []
pairtab = collections.Counter()
for (p, s), k in sorted(key.items()):
    a = ans.get(p, '')
    if a not in ('A', 'B', 'Both', 'Neither'): continue
    j = a == 'Both' or a == s
    tot[k['source']] += 1; yes[k['source']] += j
    rows.append((p, s, k['source'], int(j), k['report'], k['sentence']))
for p in sorted(ans):
    srcs = tuple(key[(p, s)]['source'] for s in 'AB'); pairtab[(srcs, ans[p])] += 1
print('source  n  judged_claim  share  wilson95')
for s in 'ENF':
    lo, hi = wilson(yes[s], tot[s])
    print(f'{s}      {tot[s]:2d}  {yes[s]:2d}           {yes[s]/tot[s]:.0%}   {lo:.0%}-{hi:.0%}')
print('\nmixed pairs (one answer picks one sentence):')
for (srcs, a), n in sorted(pairtab.items()): print(' ', srcs, a, n)
w = csv.writer(open(sys.argv[1].replace('answers', 'scored'), 'w', newline='', encoding='utf-8'))
w.writerow(['pair', 'slot', 'source', 'judged_claim', 'report', 'sentence']); w.writerows(rows)
