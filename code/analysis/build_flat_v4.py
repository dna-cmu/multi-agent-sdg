"""Flat claim table for the frozen-V4 corpus scores, joined to claim metadata. Run from the project root."""
import json, glob, csv
from pathlib import Path
O = Path('sdg-credibility-framework/data/outputs')
decl = {d['company']: sorted({int(x['sdg_number']) for x in d.get('self_declared_sdgs', [])}) for d in json.load(open(O/'validation/self_declared_sdgs_corpus.json'))}
rows = []
for f in sorted(glob.glob(str(O/'main/full_v4/*_full_v4.json'))):
    rep = Path(f).name.replace('_full_v4.json', '')
    v4 = json.load(open(f)); v7 = json.load(open(O/f'main/full_v7/{rep}_full_v7.json'))
    meta = v7['metadata']; by = {c['claim_id']: c for c in v7['claims']}
    for c in v4['claims']:
        m = by[c['claim_id']]; ok = c.get('n_runs') == 3 and 'error' not in c
        goals = sorted({int(x['goal']) for x in m['sdg_mappings']})
        cs = m.get('credibility_scores') or {}
        g7 = lambda k: (cs.get(k) or {}).get('score') if isinstance(cs.get(k), dict) else cs.get(k)
        r = dict(uid=c['uid'], report=rep, company=meta['company'], sector=meta['sector'], claim_id=c['claim_id'],
                 claim_type=m.get('claim_type'), goals=' '.join(map(str, goals)), n_goals=len(goals),
                 declared_goals=' '.join(map(str, decl.get(meta['company'], []))), complete=int(ok))
        if ok:
            r.update(S=c['S'], M=c['M'], T=c['T'], E=c['E'], C=c['C'], SMTE=c['SMTE'], SMTEC=c['SMTEC'],
                     tier_SMTE=c['tier_SMTE'], tier_SMTEC=c['tier_SMTEC'], nothing_to_check=int(c['nothing_to_check']),
                     n_contradicts=len(c['contradicts_slots']),
                     **{f'lab_{s}': c['labels'][s] for s in ('S1','S2','X1','X2','X3')},
                     **{f'{d}_runs': ' '.join(map(str, c[f'{d}_runs'])) for d in 'SMTE'})
        r.update(v7_S=g7('specificity'), v7_M=g7('measurability'), v7_T=g7('temporality'), v7_E=g7('evidence'), v7_C=g7('consistency'))
        rows.append(r)
keys = []
for r in rows:
    for k in r:
        if k not in keys: keys.append(k)
out = O/'revision/claims_v4_flat.csv'
with open(out, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
print(len(rows), 'claims ->', out, '| complete', sum(r['complete'] for r in rows), '| firms', len({r['company'] for r in rows}), '| firms with declarations', sum(1 for c in {r['company'] for r in rows} if decl.get(c)))
