"""Claim -> true PDF page lookup. The `page` stored with each claim (and printed as "p." in the rater forms and the
prompt) is a position index from the extraction stage, not a PDF page. The ADE chunk files carry the real page, so
each claim is located by text in those chunks. Run from the project root."""
import json, glob, re, csv
from pathlib import Path
O = Path('sdg-credibility-framework/data/outputs')
norm = lambda s: re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()
rows = []
for f in sorted(glob.glob(str(O / 'main/full_v7/*_full_v7.json'))):
    rep = Path(f).name.replace('_full_v7.json', '')
    ch = json.load(open(O / f'main/chunks/{rep}_chunks.json'))['chunks']
    txt = [norm(c.get('text') or '') for c in ch]; toks = [set(t.split()) for t in txt]
    for c in json.load(open(f))['claims']:
        k = norm(c['claim_text']); how, idx = 'none', []
        if len(k) >= 20:
            idx = [i for i, t in enumerate(txt) if k in t]; how = 'exact'
            if not idx: idx = [i for i, t in enumerate(txt) if k[:60] in t]; how = 'prefix'
        if not idx:
            kt = set(k.split()); best = max(range(len(ch)), key=lambda i: len(kt & toks[i]) / max(1, len(kt))) if kt else None
            cov = len(kt & toks[best]) / max(1, len(kt)) if best is not None else 0
            idx, how = ([best], f'fuzzy') if cov >= 0.8 else ([], 'none')
        pages = sorted({ch[i]['page'] + 1 for i in idx})
        rows.append(dict(uid=f"{rep}::{c['claim_id']}", report=rep, claim_id=c['claim_id'], index_shown_as_page=c.get('page'),
                         pdf_page=pages[0] if pages else '', other_candidate_pages=' '.join(map(str, pages[1:6])), match=how if idx else 'none',
                         mapped=int(bool(c.get('sdg_mappings')))))
out = O / 'revision/claim_pdf_page_lookup.csv'
with open(out, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
import collections
n = len(rows); m = collections.Counter(r['match'] for r in rows)
print(n, 'claims ->', out); print({k: f'{v} ({v/n*100:.1f}%)' for k, v in m.items()})
print('one candidate page only:', sum(1 for r in rows if r['pdf_page'] != '' and not r['other_candidate_pages']), '| index equals true page:', sum(1 for r in rows if str(r['index_shown_as_page']) == str(r['pdf_page'])))
