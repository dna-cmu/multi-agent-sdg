"""Author-audit workbooks for Reviewer 3 point 4 (extraction, SDG mapping, declared priorities, excluded claims,
end-to-end trace). Samples are drawn with fixed seeds; the framework's answers are kept in separate key files that
the auditors do not open until both have finished. Run from the project root."""
import json, glob, csv, random, re, collections
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
SEED = 20261110; O = Path('sdg-credibility-framework/data/outputs'); OUT = Path('revision/audits'); KEY = OUT / '_keys-do-not-open'; KEY.mkdir(parents=True, exist_ok=True)
AUDITORS = ['DNA', 'EE']
SDG = {1:'No poverty',2:'Zero hunger',3:'Good health and well-being',4:'Quality education',5:'Gender equality',6:'Clean water and sanitation',7:'Affordable and clean energy',8:'Decent work and economic growth',9:'Industry, innovation and infrastructure',10:'Reduced inequalities',11:'Sustainable cities and communities',12:'Responsible consumption and production',13:'Climate action',14:'Life below water',15:'Life on land',16:'Peace, justice and strong institutions',17:'Partnerships for the goals'}
look = {r['uid']: r for r in csv.DictReader(open(O / 'revision/claim_pdf_page_lookup.csv'))}
claims = []; meta = {}
for f in sorted(glob.glob(str(O / 'main/full_v7/*_full_v7.json'))):
    rep = Path(f).name.replace('_full_v7.json', ''); d = json.load(open(f)); meta[rep] = d['metadata']
    for c in d['claims']:
        uid = f"{rep}::{c['claim_id']}"; p = look[uid]['pdf_page']
        claims.append(dict(uid=uid, report=rep, company=d['metadata']['company'], sector=d['metadata']['sector'], claim_id=c['claim_id'], text=c['claim_text'], type=c.get('claim_type'), section=c.get('section'), pdf_page=int(p) if p else None, goals=sorted({int(m['goal']) for m in (c.get('sdg_mappings') or [])}), targets=sorted({str(m.get('target')) for m in (c.get('sdg_mappings') or [])})))
v4 = {}
for f in glob.glob(str(O / 'main/full_v4/*_full_v4.json')):
    for c in json.load(open(f))['claims']: v4[c['uid']] = c
H = Font(bold=True, color='FFFFFF'); HF = PatternFill('solid', fgColor='305496'); YF = PatternFill('solid', fgColor='FFF2CC'); thin = Side(style='thin', color='BFBFBF'); B = Border(left=thin, right=thin, top=thin, bottom=thin)
def sheet(wb, title, headers, widths, rows, yellow=()):
    ws = wb.create_sheet(title); ws.append(headers)
    for i, (h, w) in enumerate(zip(headers, widths), 1):
        c = ws.cell(1, i); c.font = H; c.fill = HF; c.alignment = Alignment(wrap_text=True, vertical='center'); ws.column_dimensions[c.column_letter].width = w
    for r in rows: ws.append(r)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical='top'); c.border = B
            if headers[c.column - 1] in yellow: c.fill = YF
    ws.freeze_panes = 'A2'; return ws
def readme(wb, title, lines):
    ws = wb.active; ws.title = 'READ ME'; ws.column_dimensions['A'].width = 120
    ws['A1'] = title; ws['A1'].font = Font(bold=True, size=14)
    for i, l in enumerate(lines, 3): ws.cell(i, 1, l).alignment = Alignment(wrap_text=True, vertical='top')
def dv(ws, col, opts, n):
    v = DataValidation(type='list', formula1='"' + ','.join(opts) + '"', allow_blank=True); ws.add_data_validation(v); v.add(f'{col}2:{col}{n+1}')
def save(wb, name):
    for a in AUDITORS: wb.save(OUT / f'{name}-{a}.xlsx')
COMMON = ['Work alone. Do not discuss with the other auditor, and do not open the key files or the framework outputs, until both of you have finished. Yellow cells are yours.', 'This is an author audit (DNA and EE); the paper will say so and report agreement between the two auditors.']
rng = random.Random(SEED)

# ---------- A1 extraction audit
by_rep = collections.defaultdict(list)
for c in claims:
    if c['pdf_page']: by_rep[c['report']].append(c)
sectors = collections.defaultdict(list)
for rep, m in meta.items(): sectors[m['sector']].append(rep)
reps = [rng.choice(sorted(sectors[s])) for s in rng.sample(sorted(sectors), 3)]
spans = []; keyrows = []
for rep in reps:
    import subprocess
    npages = int([l for l in subprocess.run(['pdfinfo', f'sdg-credibility-framework/data/reports/2024/{rep}.pdf'], capture_output=True, text=True).stdout.splitlines() if l.startswith('Pages')][0].split()[1])
    cnt = collections.Counter(c['pdf_page'] for c in by_rep[rep])
    starts = list(range(1, npages - 1)); dense = [s for s in starts if sum(cnt[s + k] for k in range(3)) >= 3]; empty = [s for s in starts if sum(cnt[s + k] for k in range(3)) == 0]
    chosen = []
    for pool, k in ((dense, 2), (empty, 1)):
        rng.shuffle(pool)
        for s in pool:
            if len([x for x in chosen if x[1] == pool]) >= k: break
            if all(abs(s - t[0]) >= 3 for t in chosen): chosen.append((s, pool))
    for s, _ in sorted(chosen):
        sid = f'{rep}-p{s}-{s+2}'; spans.append([sid, meta[rep]['company'], f'{rep}.pdf', s, s + 2])
        for c in by_rep[rep]:
            if s <= c['pdf_page'] <= s + 2: keyrows.append([sid, c['pdf_page'], c['claim_id'], c['type'], c['text']])
wb = openpyxl.Workbook(); readme(wb, 'Audit 1 — Claim extraction', COMMON + ['Task: for each page span in the sheet "Spans", open the PDF (sdg-credibility-framework/data/reports/2024/) at the printed PDF page numbers (page 1 = first page of the file) and list EVERY SDG-related claim you find on those pages in the sheet "Your claims": one row per claim, copied word for word.', 'A claim = one sentence or bullet that states an action, target, result or status related to sustainability / the SDGs (the definition in the rater handbooks). Ignore headings, pure descriptions with no action or result, and financial statements.', 'Some spans may contain no claim; then write "none" once for that span.', 'Claim type: commitment, achievement, metric, policy, alignment, target (choose the closest).'])
sheet(wb, 'Spans', ['span_id', 'company', 'PDF file', 'from PDF page', 'to PDF page'], [30, 30, 30, 14, 14], spans)
ws = sheet(wb, 'Your claims', ['span_id', 'PDF page', 'claim text (word for word)', 'claim type', 'note'], [30, 10, 100, 16, 30], [[''] * 5 for _ in range(250)], yellow=('span_id', 'PDF page', 'claim text (word for word)', 'claim type', 'note'))
dv(ws, 'A', [s[0] for s in spans], 250); dv(ws, 'D', ['commitment', 'achievement', 'metric', 'policy', 'alignment', 'target'], 250)
save(wb, 'Audit1-Extraction')
csv.writer(open(KEY / 'Audit1-Extraction-KEY.csv', 'w', newline='', encoding='utf-8-sig')).writerows([['span_id', 'pdf_page', 'claim_id', 'claim_type', 'extracted claim text']] + keyrows)

# ---------- A2 mapping audit (100 mapped + 20 unmapped, mixed)
mapped = [c for c in claims if c['goals']]; unm = [c for c in claims if not c['goals']]
samp = rng.sample(mapped, 100) + rng.sample(unm, 20); rng.shuffle(samp)
wb = openpyxl.Workbook(); readme(wb, 'Audit 2 — SDG mapping', COMMON + ['Task: for each claim, write the SDG goal numbers (1–17) that the claim addresses, most relevant first, up to three, in the three yellow columns. If the claim addresses no SDG, write 0 in the first column.', 'Judge from the claim text and its section title only (that is what the framework sees). The sheet "SDG list" gives the 17 goals.'])
ws = sheet(wb, 'Claims', ['#', 'company', 'section', 'claim text', 'goal 1', 'goal 2', 'goal 3', 'note'], [5, 24, 30, 90, 8, 8, 8, 30], [[i + 1, c['company'], c['section'], c['text'], '', '', '', ''] for i, c in enumerate(samp)], yellow=('goal 1', 'goal 2', 'goal 3', 'note'))
sheet(wb, 'SDG list', ['goal', 'name'], [8, 50], [[k, v] for k, v in SDG.items()])
save(wb, 'Audit2-SDG-mapping')
csv.writer(open(KEY / 'Audit2-SDG-mapping-KEY.csv', 'w', newline='', encoding='utf-8-sig')).writerows([['#', 'uid', 'in scored corpus', 'framework goals', 'framework targets']] + [[i + 1, c['uid'], int(bool(c['goals'])), ' '.join(map(str, c['goals'])), ' '.join(c['targets'])] for i, c in enumerate(samp)])

# ---------- A3 declared priorities
decl = {d['company']: d for d in json.load(open(O / 'validation/self_declared_sdgs_corpus.json'))}
rows = [[i + 1, m['company'], m['sector'], f'{rep}.pdf', '', '', ''] for i, (rep, m) in enumerate(sorted(meta.items(), key=lambda x: x[1]['company']))]
wb = openpyxl.Workbook(); readme(wb, 'Audit 3 — Declared SDG priorities', COMMON + ['Task: for each of the 30 reports, find where the company states which SDGs it prioritises or commits to (e.g. a materiality/SDG mapping page, strategy page, SDG icons with a statement of priority). Write the goal numbers, separated by commas, and the PDF page(s) where you found them.', 'Record only goals the report presents as its own priorities or commitments, not every SDG icon that appears beside a topic. If the report declares none, write 0. If you are unsure whether a goal is presented as a priority, add it to the note column instead.'])
sheet(wb, 'Reports', ['#', 'company', 'sector', 'PDF file', 'declared priority SDGs (e.g. 7, 12, 13)', 'PDF page(s)', 'note'], [5, 30, 22, 30, 34, 16, 50], rows, yellow=('declared priority SDGs (e.g. 7, 12, 13)', 'PDF page(s)', 'note'))
save(wb, 'Audit3-Declared-priorities')
csv.writer(open(KEY / 'Audit3-Declared-priorities-KEY.csv', 'w', newline='', encoding='utf-8-sig')).writerows([['company', 'framework declared SDGs', 'framework evidence']] + [[c, ' '.join(str(x['sdg_number']) for x in d.get('self_declared_sdgs', [])), ' || '.join(f"{x['sdg_number']}: {x.get('evidence','')[:200]}" for x in d.get('self_declared_sdgs', []))] for c, d in sorted(decl.items())])

# ---------- A4 excluded claims
samp = rng.sample(unm, 100)
REAS = ['Not SDG-related', 'SDG-related: should have been mapped', 'Not a claim (fragment/heading/table text)', 'Duplicate of another claim', 'Unclear']
wb = openpyxl.Workbook(); readme(wb, 'Audit 4 — Claims excluded from scoring', COMMON + ['Background: 611 extracted claims received no SDG mapping and were therefore not scored. This is a random sample of 100 of them.', 'Task: for each, choose the one description that fits best. If you choose "SDG-related: should have been mapped", write the goal number(s) it should have received.'])
ws = sheet(wb, 'Claims', ['#', 'company', 'section', 'claim type', 'claim text', 'your assessment', 'goal(s) if it should have been mapped', 'note'], [5, 24, 30, 14, 90, 36, 20, 30], [[i + 1, c['company'], c['section'], c['type'], c['text'], '', '', ''] for i, c in enumerate(samp)], yellow=('your assessment', 'goal(s) if it should have been mapped', 'note'))
dv(ws, 'F', REAS, 100); save(wb, 'Audit4-Excluded-claims')
csv.writer(open(KEY / 'Audit4-Excluded-claims-KEY.csv', 'w', newline='', encoding='utf-8-sig')).writerows([['#', 'uid', 'pdf_page']] + [[i + 1, c['uid'], c['pdf_page']] for i, c in enumerate(samp)])

# ---------- A5 end-to-end trace (20 claims, by SMTE tier)
import pickle, os
ok = [c for c in mapped if c['uid'] in v4 and v4[c['uid']].get('n_runs') == 3 and c['pdf_page']]
pick = []
for t, k in (('unsubstantiated', 7), ('partially_substantiated', 8), ('substantiated', 5)): pick += rng.sample([c for c in ok if v4[c['uid']]['tier_SMTE'] == t], k)
rng.shuffle(pick)
os.chdir('sdg-credibility-framework'); __import__('sys').path.insert(0, os.getcwd()); import score_v4 as S
items = {}
for rep in {c['report'] for c in pick}:
    for it in S.items_from_corpus(rep): items[it['uid']] = it
os.chdir('..')
crow, prow = [], []
YN = ['Yes', 'Partly', 'No']
for i, c in enumerate(pick, 1):
    v = v4[c['uid']]
    crow.append([i, c['company'], f"{c['report']}.pdf", c['pdf_page'], c['section'], c['text'], c['type'], ', '.join(c['targets']), v['S'], v['M'], v['T'], v['E'], v['C'], v['SMTE'], '', '', '', '', '', '', '', '', ''])
    for s in ('S1', 'S2', 'X1', 'X2', 'X3'):
        txt = items[c['uid']]['slots'][s]
        prow.append([i, s, txt if txt != S.EMPTY else '(no passage retrieved)', v['labels'][s], v['label_reason'][s], '', ''])
wb = openpyxl.Workbook(); readme(wb, 'Audit 5 — End-to-end trace of 20 claims', COMMON + ['Unlike audits 1–4, this audit shows the framework\'s output, because the task is to check each stage for the same claim and see how an error at one stage carries into the next.', 'Sheet "Claims": (a) find the claim in the PDF at the page given and say whether the extracted text is faithful; (b) say whether the claim type is right; (c) say whether the SDG targets are right; (d) give your own S, M, T, E (0–3) using the SMTEC handbook of 21 Oct.', 'Sheet "Passages": for each retrieved passage give your own label (Extend / Redundant / Related / Unrelated / Contradicts) and say whether the passage is real report content or only a header, footer or heading.', 'Note: the "p." numbers printed inside passage tags are internal position numbers, not PDF pages; use the PDF page column in the Claims sheet to find the claim.'])
hd = ['#', 'company', 'PDF file', 'PDF page', 'section', 'extracted claim text', 'framework claim type', 'framework SDG targets', 'fw S', 'fw M', 'fw T', 'fw E', 'fw C', 'fw SMTE', 'found on that page?', 'text faithful?', 'claim type right?', 'SDG targets right?', 'your S', 'your M', 'your T', 'your E', 'note']
ws = sheet(wb, 'Claims', hd, [4, 20, 24, 8, 24, 70, 14, 22, 6, 6, 6, 6, 6, 8, 12, 12, 12, 12, 7, 7, 7, 7, 40], crow, yellow=tuple(hd[14:]))
for col in 'OPQR': dv(ws, col, YN, 20)
ws = sheet(wb, 'Passages', ['claim #', 'slot', 'passage', 'framework label', 'framework reason', 'your label', 'content or header/heading only?'], [8, 6, 100, 14, 50, 16, 24], prow, yellow=('your label', 'content or header/heading only?'))
dv(ws, 'F', ['Extend', 'Redundant', 'Related', 'Unrelated', 'Contradicts'], len(prow)); dv(ws, 'G', ['Content', 'Header/heading only'], len(prow))
save(wb, 'Audit5-End-to-end-trace')
csv.writer(open(KEY / 'Audit5-End-to-end-KEY.csv', 'w', newline='', encoding='utf-8-sig')).writerows([['#', 'uid']] + [[i, c['uid']] for i, c in enumerate(pick, 1)])
print('extraction spans:', [(s[0]) for s in spans], '| key claims', len(keyrows))
print('built:', sorted(p.name for p in OUT.glob('Audit*.xlsx')))
