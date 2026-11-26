"""Audit 6 — blinded claim / not-claim judgement in pairs (DNA's design, 24 Nov 2026).
Three sources, 30 items each, one per report where possible, fixed seed:
  E = extracted claims (as stored);
  N = sentences NOT extracted that lie inside the stretch of text spanned by one section's extracted claims
      (text the extractor certainly read);
  F = sentences NOT extracted that lie more than 12,000 characters from the first extracted claim of every
      section (text the extractor very probably never read, because section text was cut at 12,000 characters).
Excluded: the 12 pages of Audit 1 (BDMS, DELTA reports are excluded altogether). Run from the project root."""
import json, glob, os, re, itertools, random, csv, statistics as st
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
SEED = 20261124; FW = 'sdg-credibility-framework/data/outputs/main/'; OUT = 'revision/audits/'; rng = random.Random(SEED)
def norm(t): return re.sub(r'[^a-z0-9]+', ' ', str(t).lower()).strip()
def words(t): return set(w for w in norm(t).split() if len(w) > 2)
pool = {'E': [], 'N': [], 'F': []}; farshare = []
for f in sorted(glob.glob(FW+'phase1/*_phase1.json')):
    rep = os.path.basename(f).replace('_phase1.json', '')
    d = json.load(open(f)); j = json.load(open(FW+f'chunks/{rep}_chunks.json')); ch = j if isinstance(j, list) else j.get('chunks', [])
    T = norm(' '.join(str(x.get('text') or '') for x in ch)); cl = d['claims']; company = d['metadata'].get('company', rep)
    pos = []
    for c in cl:
        k = norm(c['claim_text'])[:60]; p = T.find(k) if len(k) >= 25 else -1
        if p >= 0 and T.find(k, p+1) >= 0: p = -1
        pos.append(p)
    runs = []
    for sec, g in itertools.groupby(range(len(cl)), key=lambda i: cl[i].get('section')):
        ps = [pos[i] for i in g if pos[i] >= 0]
        if ps: runs.append((min(ps), max(ps)))
    firsts = [a for a, b in runs]
    def zone(p):
        if any(a <= p <= b for a, b in runs if b > a): return 'N'
        if all(abs(p-a) > 12000 for a in firsts): return 'F'
        return None
    # share of text positions that are far from every section's first claim
    step = 500; pts = range(0, len(T), step); farshare.append((rep, sum(zone(p) == 'F' for p in pts)/max(1, len(pts))))
    if rep.startswith(('BDMS', 'DELTA')): continue
    cw = [words(c['claim_text']) for c in cl]
    for c in cl:
        t = ' '.join(str(c['claim_text']).split())
        if 8 <= len(t.split()) <= 70: pool['E'].append((rep, company, t))
    for x in ch:
        if str(x.get('type', '')).lower() not in ('text', 'paragraph', 'title', '') and 'text' not in str(x.get('type', '')).lower(): continue
        raw = ' '.join(str(x.get('text') or '').split())
        raw = re.sub(r'<[^>]+>', ' ', raw)
        for s in re.split(r'(?<=[.!?])\s+(?=[A-Z“"])', raw):
            s = s.strip(' #*-•|')
            if not (10 <= len(s.split()) <= 60) or not s.endswith(('.', '!', '?')): continue
            if sum(ch_.isalpha() for ch_ in s)/max(1, len(s)) < 0.7 or '|' in s: continue
            k = norm(s)[:60]; p = T.find(k)
            if p < 0: continue
            z = zone(p)
            if not z: continue
            ws_ = words(s)
            if any(len(ws_ & w)/max(1, min(len(ws_), len(w))) >= 0.6 for w in cw if w): continue   # overlaps an extracted claim
            pool[z].append((rep, company, s))
types = sorted({str(x.get('type')) for x in ch})
items = []
for src in ('E', 'N', 'F'):
    by = {}
    for r in pool[src]: by.setdefault(r[0], []).append(r)
    reps = sorted(by); rng.shuffle(reps); pick = []
    for r in reps: pick.append(rng.choice(by[r]))
    while len(pick) < 30:                      # 28 reports: top up with second items from random reports
        r = rng.choice(reps); c = rng.choice(by[r])
        if c not in pick: pick.append(c)
    items += [(src,)+p for p in pick[:30]]
rng.shuffle(items)
pairs = [(items[2*i], items[2*i+1]) for i in range(45)]
thin = Side(style='thin', color='BFBFBF'); B = Border(left=thin, right=thin, top=thin, bottom=thin)
DEF = ['Audit 6 — Is it a claim? (45 pairs, 90 sentences)',
 'Each row shows two sentences, A and B, taken from the sustainability reports. For each row, decide which of them is a claim, using the definition below, and choose one answer in the yellow cell: A, B, Both or Neither.',
 'The sentences were drawn at random by a fixed seed and paired at random. A pair may contain two claims, one claim or none. Nothing in the form says where a sentence came from.',
 'DEFINITION (the instruction given to the extraction model, word for word). A "claim" is any statement where the company asserts: (1) a contribution to a sustainability goal or target; (2) an achievement, metric, or outcome related to ESG performance; (3) a commitment, target, or plan for sustainability improvement; (4) an alignment with SDGs, GRI standards, or other sustainability frameworks.',
 'NOT a claim: generic background text about global sustainability challenges; descriptions of the SDG framework itself; boilerplate language (copyright notices, disclaimers, table of contents); procedural descriptions of the reporting process.',
 'Judge each sentence on its own, as written. If you cannot decide for a row, leave it blank and write why in the note column. Work alone; do not discuss with the other auditor until both have finished. Do not open the key.']
for who in ('DNA', 'EE'):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'READ ME'
    for t in DEF: ws.append([t])
    ws.column_dimensions['A'].width = 140
    for r in ws.iter_rows():
        for c in r: c.alignment = Alignment(wrap_text=True, vertical='top')
    ws['A1'].font = Font(bold=True, size=14)
    w2 = wb.create_sheet('Pairs'); w2.append(['pair', 'company A', 'sentence A', 'company B', 'sentence B', 'Which is a claim? (A / B / Both / Neither)', 'note'])
    for i, (a, b) in enumerate(pairs, 1): w2.append([i, a[2], a[3], b[2], b[3], None, None])
    for col, wdt in zip('ABCDEFG', (6, 18, 62, 18, 62, 18, 30)): w2.column_dimensions[col].width = wdt
    dv = DataValidation(type='list', formula1='"A,B,Both,Neither"', allow_blank=True); w2.add_data_validation(dv); dv.add('F2:F46')
    for r in w2.iter_rows():
        for c in r: c.alignment = Alignment(wrap_text=True, vertical='top'); c.border = B
    for c in w2[1]: c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='305496')
    for r in range(2, 47): w2.cell(r, 6).fill = PatternFill('solid', fgColor='FFF2CC')
    w2.freeze_panes = 'A2'; wb.save(OUT+f'Audit6-Claim-or-not-pairs-{who}.xlsx')
with open(OUT+'_keys-do-not-open/Audit6-Claim-or-not-KEY.csv', 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['pair', 'slot', 'source', 'report', 'sentence'])
    for i, (a, b) in enumerate(pairs, 1): w.writerow([i, 'A', a[0], a[1], a[3]]); w.writerow([i, 'B', b[0], b[1], b[3]])
print('pool sizes', {k: len(v) for k, v in pool.items()}, '| chunk types', types[:8])
fs = [v for _, v in farshare]; print('share of report text more than 12,000 chars from every section\'s first extracted claim: min %.2f median %.2f max %.2f' % (min(fs), st.median(fs), max(fs)))
print({r: round(v, 2) for r, v in farshare if r.startswith(('BDMS', 'DELTA'))})
print('items by source in form:', {s: sum(1 for it in items if it[0] == s) for s in 'ENF'}, '| reports represented:', len({it[1] for it in items}))
