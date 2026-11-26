"""Reduced audit plan: subsets of the full audit workbooks (same seed, same keys), so either plan can be used.
Run from the project root after build_audit_workbooks.py."""
import csv, random, collections, openpyxl
from pathlib import Path
from openpyxl.worksheet.datavalidation import DataValidation
A = Path('revision/audits'); R = A / 'reduced'; R.mkdir(exist_ok=True); rng = random.Random(20261110)
def keep_rows(ws, keep):  # keep = predicate on the row's values (data rows only)
    for r in range(ws.max_row, 1, -1):
        if not keep([c.value for c in ws[r]]): ws.delete_rows(r)
note = lambda wb, t: wb['READ ME'].cell(wb['READ ME'].max_row + 2, 1, t)
# Audit 1: 4 spans in 2 reports (per report: the span with most extracted claims and the span with fewest)
key = list(csv.DictReader(open(A / '_keys-do-not-open/Audit1-Extraction-KEY.csv', encoding='utf-8-sig')))
wb0 = openpyxl.load_workbook(A / 'Audit1-Extraction-DNA.xlsx'); spans = [r[0] for r in wb0['Spans'].iter_rows(min_row=2, values_only=True)]
cnt = collections.Counter(k['span_id'] for k in key); by = collections.defaultdict(list)
for s in spans: by[s.rsplit('-p', 1)[0]].append(s)
chosen = []
for rep in rng.sample(sorted(by), 2):
    ss = sorted(by[rep], key=lambda s: cnt[s]); chosen += [ss[-1], ss[0]]
for a in ('DNA', 'EE'):
    wb = openpyxl.load_workbook(A / f'Audit1-Extraction-{a}.xlsx'); keep_rows(wb['Spans'], lambda v: v[0] in chosen)
    ws = wb['Your claims']; ws.delete_rows(122, ws.max_row); ws.data_validations.dataValidation = []
    for col, opts in (('A', chosen), ('D', ['commitment', 'achievement', 'metric', 'policy', 'alignment', 'target'])):
        v = DataValidation(type='list', formula1='"' + ','.join(opts) + '"', allow_blank=True); ws.add_data_validation(v); v.add(f'{col}2:{col}121')
    note(wb, 'REDUCED PLAN: 4 page spans in 2 reports (a subset of the full plan\'s 9 spans).'); wb.save(R / f'Audit1-Extraction-reduced-{a}.xlsx')
# Audit 2: unchanged (120 claims) -> copy
for a in ('DNA', 'EE'):
    wb = openpyxl.load_workbook(A / f'Audit2-SDG-mapping-{a}.xlsx'); note(wb, 'REDUCED PLAN: same as the full plan (120 claims).'); wb.save(R / f'Audit2-SDG-mapping-{a}.xlsx')
# Audit 3: one auditor does all 30 (the full workbook); the other checks a seeded sample of 10
wb0 = openpyxl.load_workbook(A / 'Audit3-Declared-priorities-DNA.xlsx'); comps = [r[1] for r in wb0['Reports'].iter_rows(min_row=2, values_only=True)]
ten = set(rng.sample(sorted(comps), 10))
wb = openpyxl.load_workbook(A / 'Audit3-Declared-priorities-DNA.xlsx'); note(wb, 'REDUCED PLAN: this copy is for the auditor who does all 30 reports.'); wb.save(R / 'Audit3-Declared-priorities-all30.xlsx')
wb = openpyxl.load_workbook(A / 'Audit3-Declared-priorities-DNA.xlsx'); keep_rows(wb['Reports'], lambda v: v[1] in ten); note(wb, 'REDUCED PLAN: this copy is for the second auditor, who checks 10 of the 30 reports (seeded sample) so that agreement can be reported.'); wb.save(R / 'Audit3-Declared-priorities-check10.xlsx')
# Audit 4: first 50 of the 100 (the sample is already in random order)
for a in ('DNA', 'EE'):
    wb = openpyxl.load_workbook(A / f'Audit4-Excluded-claims-{a}.xlsx'); keep_rows(wb['Claims'], lambda v: isinstance(v[0], int) and v[0] <= 50); note(wb, 'REDUCED PLAN: the first 50 of the full plan\'s 100 claims.'); wb.save(R / f'Audit4-Excluded-claims-reduced-{a}.xlsx')
open(R / 'READ-ME-reduced-plan.md', 'w').write(f"""# Reduced audit plan (10 Nov 2026)

Subsets of the full plan in `revision/audits/` (same seed 20261110, same key files), so results from either plan can be scored with the same keys.

| Audit | Full plan | Reduced plan | Who |
|---|---|---|---|
| 1. Extraction | 9 page spans, 3 reports | 4 page spans, 2 reports: {', '.join(chosen)} | DNA and EE, separately |
| 2. SDG mapping | 120 claims | 120 claims (unchanged) | DNA and EE, separately |
| 3. Declared priorities | 30 reports, both auditors | one auditor all 30 (`…-all30.xlsx`); the other 10 reports (`…-check10.xlsx`): {', '.join(sorted(ten))} | decide who takes which |
| 4. Excluded claims | 100 claims | first 50 | DNA and EE, separately |
| 5. End-to-end trace | 20 claims | not done | — |

Retrieval relevance needs no author audit: three raters labelled the retrieved passages of the 60 Round 1 claims.
If Audit 5 is skipped, the response letter says the stage-by-stage audits were prioritised over the combined trace.
Work separately; do not open `_keys-do-not-open/` until both have finished.
""")
print('chosen spans:', chosen); print('check-10 reports:', sorted(ten)); print(sorted(p.name for p in R.iterdir()))
