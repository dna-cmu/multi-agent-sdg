"""Enlarge the Forms sheet of the Round 1 rating forms for print.
- fonts 9->11, 10->12, 11->13 (Forms sheet only)
- column widths retuned so A4 portrait prints at ~100% instead of being shrunk
- row heights recomputed from measured text wrap (Carlito = Calibri metrics)
- passages too long for Excel's 409pt row cap are split into "(cont.)" rows
  (previously such passages were silently cut off in print)
- merges, data validation, page breaks (one claim per page), protection, footer kept
"""
import sys, math, re
from copy import copy
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.pagebreak import Break, RowBreak
from PIL import ImageFont

SRC, DST = sys.argv[1], sys.argv[2]
MODE = sys.argv[3] if len(sys.argv) > 3 else 'print'   # 'print' = blank TRUE/FALSE box for paper; 'screen' = FALSE pre-filled for Excel use
FONT_MAP = {9.0: 12.0, 10.0: 12.0, 11.0: 13.0}
COL_A, COL_REST = 14.5, 8.0
PX = lambda w: w * 7.0               # Excel col width -> px (approx, Calibri 11 default)
LINE_PT = {11.0: 14.8, 12.0: 15.6, 13.0: 17.2}
PAD_PT = 3
MAX_ROW_PT = 400                     # Excel hard cap is 409

_fonts = {}
def font(sz, bold):
    key = (sz, bold)
    if key not in _fonts:
        f = '/usr/share/fonts/truetype/crosextra/Carlito-%s.ttf' % ('Bold' if bold else 'Regular')
        _fonts[key] = ImageFont.truetype(f, int(round(sz * 96 / 72)))
    return _fonts[key]

def n_lines(text, width_px, sz, bold):
    f = font(sz, bold); total = 0
    for para in str(text).split('\n'):
        words = para.split(' '); line = ''; cnt = 1
        for w in words:
            cand = w if not line else line + ' ' + w
            if f.getlength(cand) <= width_px or not line:
                line = cand
                while f.getlength(line) > width_px and len(line) > 1:   # hard-break very long tokens
                    cnt += 1; line = line[int(len(line) * width_px / f.getlength(line)):]
            else:
                cnt += 1; line = w
        total += cnt
    return total

def split_text(text, width_px, sz, bold, max_lines):
    """split into chunks of <= max_lines at paragraph, then sentence, then word boundaries"""
    units = []
    for para in str(text).split('\n'):
        if n_lines(para, width_px, sz, bold) <= max_lines:
            units.append((para, '\n'))
        else:
            sents = re.split(r'(?<=[.;:!?])\s+', para)
            for s in sents:
                if n_lines(s, width_px, sz, bold) <= max_lines:
                    units.append((s, ' '))
                else:
                    ws_ = s.split(' '); cur = ''
                    for w in ws_:
                        c = (cur + ' ' + w).strip()
                        if n_lines(c, width_px, sz, bold) > max_lines:
                            units.append((cur, ' ')); cur = w
                        else:
                            cur = c
                    units.append((cur, ' '))
            units[-1] = (units[-1][0], '\n')
    chunks, cur = [], ''
    for u, sep in units:
        cand = cur + u
        if cur and n_lines(cand, width_px, sz, bold) > max_lines:
            chunks.append(cur.rstrip()); cur = u + sep
        else:
            cur = cand + sep
    if cur.strip(): chunks.append(cur.rstrip())
    return chunks

KEEP_BREAK = re.compile(r'^\s*(\*|-|•|#|\[|\(?\d+[.)]|\(?[a-z][.)]\s)')
import html as _h
def tidy(text):
    """display-only cleanup of extraction artefacts (content unchanged):
    ADE figure markers <::...::> -> [Figure: ...]; markdown heading marks and ** removed;
    HTML entities outside tables decoded (&gt; -> >)."""
    t = text.replace('<::', '[Figure: ').replace('::>', ']')
    t = re.sub(r'(^|\n|\| )#{1,6} ', r'\1', t)
    t = t.replace('**', '')
    if '<table' not in t: t = _h.unescape(t)
    else:
        m = re.search(r'<table.*?(</table>|$)', t, re.S)
        t = _h.unescape(t[:m.start()]) + m.group(0) + _h.unescape(t[m.end():])
    return t

def reflow(text):
    """join PDF hard line-breaks inside a paragraph; keep breaks before bullets,
    numbered items, headings, [Section] tags, and after lines ending in ':'"""
    lines = text.split('\n'); out = [lines[0]]
    for ln in lines[1:]:
        prev = out[-1]
        if (not ln.strip() or not prev.strip() or KEEP_BREAK.match(ln)
                or prev.rstrip().endswith(':') or prev.lstrip().startswith(('[', '#'))):
            out.append(ln)
        else:
            out[-1] = prev.rstrip() + ' ' + ln.lstrip()
    return '\n'.join(out)


from html.parser import HTMLParser
import html as _html
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

class _TP(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.cell=None
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='tr': self.rows.append([])
        elif tag in ('td','th'):
            if not self.rows: self.rows.append([])
            self.cell={'t':'','cs':int(a.get('colspan') or 1),'rs':int(a.get('rowspan') or 1),'th':tag=='th'}
            self.rows[-1].append(self.cell)
        elif tag=='br' and self.cell is not None: self.cell['t']+='\n'
    def handle_endtag(self, tag):
        if tag in ('td','th'): self.cell=None
    def handle_data(self, d):
        if self.cell is not None: self.cell['t']+=d

def parse_table(t):
    p=_TP(); p.feed(t); p.close()
    rows=[[dict(c, t=_html.unescape(c['t']).strip()) for c in r] for r in p.rows if r]
    # place on a grid honouring spans
    grid={}; placed=[]
    for i,r in enumerate(rows):
        j=0
        for c in r:
            while (i,j) in grid: j+=1
            for di in range(c['rs']):
                for dj in range(c['cs']): grid[(i+di,j+dj)]=True
            placed.append((i,j,c)); j+=c['cs']
    ncol=max(j for _,j in grid)+1 if grid else 0
    nrow=len(rows)
    return nrow,ncol,placed

THIN=Side(style='thin', color='FF808080')
BOX=Border(left=THIN,right=THIN,top=THIN,bottom=THIN)
HEAD_FILL=PatternFill('solid', fgColor='FFDDEBF7')
SUB_FILL=PatternFill('solid', fgColor='FFF2F2F2')
TFONT=11.0

def alloc_cols(ncol, placed, total=10):
    """map table columns onto sheet columns B..K, wider where text is longer"""
    if ncol>total: return None
    need=[1]*ncol; mx=[1]*ncol
    for i,j,c in placed:
        if c['cs']==1 and i>0:
            need[j]+=len(c['t']); mx[j]=max(mx[j],len(c['t']))
    # weight by total text, but numeric-only columns just need their widest value
    need=[min(n, m*3) for n,m in zip(need,mx)]
    for i,j,c in placed:
        if i==0 and c['cs']==1: need[j]=max(need[j], len(c['t'])*1.5)
    alloc=[1]*ncol; spare=total-ncol
    for _ in range(spare):
        k=max(range(ncol), key=lambda x: need[x]/alloc[x]); alloc[k]+=1
    starts=[]; s=2
    for a in alloc: starts.append(s); s+=a
    return [(starts[k], starts[k]+alloc[k]-1) for k in range(ncol)]

def styled_copy(src, dst, enlarge=True):
    if src.has_style:
        f = copy(src.font)
        if enlarge and f.sz in FONT_MAP:
            f = copy(f); f.sz = FONT_MAP[f.sz]
        if not f.name:                      # unnamed fonts render as a serif fallback; force Calibri
            f = copy(f); f.name = 'Calibri'
        dst.font = f
        dst.fill = copy(src.fill); dst.border = copy(src.border)
        dst.alignment = copy(src.alignment); dst.number_format = src.number_format
        dst.protection = copy(src.protection)

wb = openpyxl.load_workbook(SRC)
old = wb['Forms']; idx = wb.sheetnames.index('Forms')
new = wb.create_sheet('Forms_new', idx)

# sheet-level settings
new.column_dimensions['A'].width = COL_A
for c in range(2, 12):
    new.column_dimensions[get_column_letter(c)].width = COL_REST
col_px = {1: PX(COL_A), **{c: PX(COL_REST) for c in range(2, 12)}}
new.page_setup.orientation = 'portrait'
new.page_setup.paperSize = 9   # A4
new.page_setup.fitToWidth = 1; new.page_setup.fitToHeight = 0
new.sheet_properties.pageSetUpPr = copy(old.sheet_properties.pageSetUpPr)
new.page_margins = copy(old.page_margins)
new.print_options = copy(old.print_options)
new.oddFooter.center.text = old.oddFooter.center.text
new.oddFooter.center.size = 9
new.sheet_view.zoomScale = 100
new.protection = copy(old.protection)

merges = {}
for m in old.merged_cells.ranges:
    merges.setdefault(m.min_row, []).append((m.min_col, m.max_col))

breaks_old = {b.id for b in old.row_breaks.brk}
row_map = {}          # old row -> list of new rows
out = 0
split_report = []
tables_done = []
for r in range(1, old.max_row + 1):
    mrow = merges.get(r, [])
    def span_px(c):
        for a, b in mrow:
            if a == c: return sum(col_px[x] for x in range(a, b + 1)) - 8
        return col_px[c] - 8
    # form v2 (20 Oct): passage rows carry a label box merged J:K beside text merged B:I
    lab_v = old.cell(r, 1).value
    has_lab = (10, 11) in mrow and isinstance(lab_v, str) and lab_v[:2] in ('S1', 'S2', 'X1', 'X2', 'X3')
    TXT_END = 9 if has_lab else 11
    # long text in B (merged B:K) may need splitting
    b = old.cell(r, 2)
    if isinstance(b.value, str) and b.value.startswith('[Section'):
        b.value = tidy(b.value)
    if isinstance(b.value, str) and '<table' in b.value and any(a == 2 for a, _ in mrow):
        m = re.search(r'<table.*?(</table>|$)', b.value, re.S)
        pre = b.value[:m.start()].rstrip().rstrip('|').rstrip()
        post = b.value[m.end():].strip().lstrip('|').strip()
        nrow, ncol, placed = parse_table(m.group(0))
        cmap = alloc_cols(ncol, placed, total=TXT_END - 1)
        WIDE = False
        if cmap is None and has_lab and ncol <= 10:   # too many columns for B:I -> table uses B:K, label box sits beside the intro row
            cmap = alloc_cols(ncol, placed, total=10); WIDE = True
        if cmap and nrow:
            row_map[r] = []; first = out + 1
            def text_row(txt, src_r=r):
                global out
                out += 1; row_map[r].append(out)
                for c in range(1, 12):
                    styled_copy(old.cell(src_r, c), new.cell(out, c))
                new.cell(out, 2).value = txt
                new.merge_cells(start_row=out, start_column=2, end_row=out, end_column=TXT_END)
                d = new.cell(out, 2)
                new.row_dimensions[out].height = min(409, n_lines(txt, span_px(2), d.font.sz or 11, bool(d.font.b)) * LINE_PT.get(d.font.sz or 11, 15) + PAD_PT)
            text_row(pre)
            t0 = out + 1
            heights = [0.0] * nrow
            lab = old.cell(r, 1)
            for i in range(nrow):
                out += 1; row_map[r].append(out)
                styled_copy(lab, new.cell(out, 1))
                for c in range(2, (11 if WIDE else TXT_END) + 1):
                    new.cell(out, c).border = BOX
            spans_v = []
            for i, j, cdef in placed:
                c1 = cmap[j][0]; c2 = cmap[min(j + cdef['cs'] - 1, ncol - 1)][1]
                rr = t0 + i; rs = min(cdef['rs'], nrow - i)
                d = new.cell(rr, c1)
                d.value = cdef['t'] if cdef['t'] != '' else None
                header = (i == 0)
                fullwidth = (cdef['cs'] >= ncol and ncol > 1)
                d.font = Font(name='Calibri', size=TFONT, bold=header or fullwidth)
                if header: fill = HEAD_FILL
                elif fullwidth: fill = SUB_FILL
                else: fill = None
                numeric = bool(re.fullmatch(r'[-+]?[\d,.]+%?|N/A|-', cdef['t']))
                d.alignment = Alignment(wrap_text=True, vertical='top',
                                        horizontal=('center' if header and j > 0 else 'right' if (numeric and j > 0) else 'left'))
                for x in range(c1, c2 + 1):
                    for y in range(rr, rr + rs):
                        cc = new.cell(y, x); cc.border = BOX
                        if fill: cc.fill = fill
                if c2 > c1 or rs > 1:
                    new.merge_cells(start_row=rr, start_column=c1, end_row=rr + rs - 1, end_column=c2)
                w = sum(col_px[x] for x in range(c1, c2 + 1)) - 8
                h = (n_lines(cdef['t'], w, TFONT, header or fullwidth) if cdef['t'] else 1) * 15.0 + 4
                if rs == 1: heights[i] = max(heights[i], h)
                else: spans_v.append((i, rs, h))
            for i, rs, h in spans_v:
                have = sum(max(x, 17.5) for x in heights[i:i + rs])
                if h > have: heights[i + rs - 1] = max(heights[i + rs - 1], 17.5) + (h - have)
            for i in range(nrow):
                new.row_dimensions[t0 + i].height = min(409, round(max(heights[i], 17.5), 1))
            if post: text_row(post)
            # one label cell down the left for the whole block
            new.cell(first, 1).value = lab.value
            new.merge_cells(start_row=first, start_column=1, end_row=out, end_column=1)
            if has_lab:   # one label box down the right of the whole table block (intro row only for wide tables)
                for y in range(first, (first if WIDE else out) + 1):
                    for c in (10, 11):
                        styled_copy(old.cell(r, c), new.cell(y, c))
                new.cell(first, 10).value = old.cell(r, 10).value
                new.merge_cells(start_row=first, start_column=10, end_row=(first if WIDE else out), end_column=11)
                if WIDE: new.row_dimensions[first].height = max(new.row_dimensions[first].height or 0, 34)
            tables_done.append((lab.value, nrow, ncol))
            continue
    if isinstance(b.value, str) and any(a == 2 for a, _ in mrow) and b.value.startswith('[Section'):
        b.value = reflow(b.value)
    chunks = [b.value]
    if isinstance(b.value, str) and any(a == 2 for a, _ in mrow):
        sz = FONT_MAP.get(b.font.sz, b.font.sz or 11)
        maxl = int((MAX_ROW_PT - PAD_PT) // LINE_PT.get(sz, 15))
        if n_lines(b.value, span_px(2), sz, bool(b.font.b)) > maxl:
            chunks = split_text(b.value, span_px(2), sz, bool(b.font.b), maxl)
            split_report.append((old.cell(r, 1).value, old.cell(1 if r < 2 else r, 1).row, len(chunks)))
    row_map[r] = []
    for k, chunk in enumerate(chunks):
        out += 1; row_map[r].append(out)
        for c in range(1, 12):
            s = old.cell(r, c); d = new.cell(out, c)
            styled_copy(s, d)
            span = next((bb - a + 1 for a, bb in mrow if a == c), 1)
            if isinstance(s.value, str) and d.font.sz and d.font.sz > 11 and (
                    (c == 1 and not s.value.startswith('#')) or s.value.lstrip().startswith('\u2610')):
                f = copy(d.font); f.sz = 11.0; d.font = f   # row labels and tick-box lines stay 11 pt
            if c > 1 and span <= 3 and isinstance(s.value, str) and d.font.sz and d.font.sz > 10 and s.value not in ('TRUE','FALSE'):
                f = copy(d.font); f.sz = 10.0; d.font = f
            v = s.value
            if c == 2 and len(chunks) > 1: v = chunk
            if c == 1 and k > 0 and v: v = '%s (cont.)' % v
            d.value = v
        for a, bb in mrow:
            if has_lab and a == 10: continue
            new.merge_cells(start_row=out, start_column=a, end_row=out, end_column=bb)
        if has_lab and k > 0:
            for c in (10, 11): new.cell(out, c).value = None
        # height
        need = 0; has_text = False
        for c in range(1, 12):
            d = new.cell(out, c)
            if d.value is None or str(d.value).strip() == '': continue
            has_text = True
            sz = d.font.sz or 11.0
            wrap = d.alignment.wrap_text
            width = span_px(c)
            lines = n_lines(d.value, width, sz, bool(d.font.b)) if wrap else 1
            if not wrap and font(sz, bool(d.font.b)).getlength(str(d.value)) > width:
                d.alignment = d.alignment.copy(wrap_text=True)
                lines = n_lines(d.value, width, sz, bool(d.font.b))
            need = max(need, lines * LINE_PT.get(sz, sz * 1.36) + PAD_PT)
        oh = old.row_dimensions[r].height
        if has_text and old.cell(r, 2).value not in (None, ''):
            h = need                                   # content row: fit to text
        else:
            h = max(need, (oh or 15) * 0.75)           # label/writing rows: compact input boxes
        new.row_dimensions[out].height = min(409, round(h, 1))
    if has_lab:
        rows_ = row_map[r]
        new.merge_cells(start_row=rows_[0], start_column=10, end_row=rows_[-1], end_column=11)

# data validation remap
for dv in old.data_validations.dataValidation:
    nd = DataValidation(type=dv.type, formula1=dv.formula1, formula2=dv.formula2,
                        allow_blank=dv.allow_blank, showDropDown=dv.showDropDown,
                        showErrorMessage=dv.showErrorMessage, showInputMessage=dv.showInputMessage,
                        errorTitle=dv.errorTitle, error=dv.error, promptTitle=dv.promptTitle,
                        prompt=dv.prompt, errorStyle=dv.errorStyle, operator=dv.operator)
    for rng in dv.sqref.ranges:
        for rr in range(rng.min_row, rng.max_row + 1):
            for cc in range(rng.min_col, rng.max_col + 1):
                for nr in row_map[rr][:1]:
                    nd.add('%s%d' % (get_column_letter(cc), nr))
    new.add_data_validation(nd)

# page breaks: one claim per page, as before
new.row_breaks = RowBreak()
for r in sorted(breaks_old):
    if r in row_map: new.row_breaks.append(Break(id=row_map[r][-1]))


# ---- paper tweaks for the SMTEC form (14/19 Oct): blank flag box, larger passage-id box ----
from openpyxl.styles import Protection
MED = Side(style='medium', color='FF000000')
def _box(ws_, r_, c1, c2, src):
    for c in range(c1, c2 + 1):
        d = ws_.cell(r_, c)
        d.fill = copy(src.fill); d.protection = copy(src.protection)
        d.border = Border(top=MED, bottom=MED, left=MED if c == c1 else None, right=MED if c == c2 else None)
    d0 = ws_.cell(r_, c1); d0.font = copy(src.font); d0.alignment = copy(src.alignment)
n_flag = 0
for r_ in range(1, new.max_row + 1):
    if new.cell(r_, 1).value != 'contradiction': continue
    n_flag += 1
    if MODE == 'print':
        new.cell(r_, 2).value = 'contradiction_flag\n(write TRUE or FALSE)'
        new.cell(r_, 4).value = None
    else:
        new.cell(r_, 2).value = 'contradiction_flag\n(default FALSE)'
        new.cell(r_, 4).value = 'FALSE'
    new.cell(r_, 6).value = 'contradicting_\npassage_id\n(S1 S2 X1 X2 X3,\nonly if TRUE)'
    lab = copy(new.cell(r_, 6)); inp_src = new.cell(r_, 9)
    inp = {'fill': copy(inp_src.fill), 'prot': copy(inp_src.protection), 'font': copy(inp_src.font), 'al': copy(inp_src.alignment)}
    lab_style = (copy(new.cell(r_, 6).fill), copy(new.cell(r_, 6).font), copy(new.cell(r_, 6).alignment), copy(new.cell(r_, 6).border), copy(new.cell(r_, 6).protection))
    for rng in list(new.merged_cells.ranges):
        if rng.min_row == r_ and rng.min_col in (6, 9): new.unmerge_cells(str(rng))
    # label F:G
    for c in (6, 7):
        d = new.cell(r_, c); d.fill, d.font, d.alignment, d.border, d.protection = [copy(x) for x in lab_style]
    new.merge_cells(start_row=r_, start_column=6, end_row=r_, end_column=7)
    # input H:K
    class _S: pass
    src = _S(); src.fill, src.protection, src.font, src.alignment = inp['fill'], inp['prot'], inp['font'], inp['al']
    new.cell(r_, 8).value = None
    _box(new, r_, 8, 11, src)
    new.merge_cells(start_row=r_, start_column=8, end_row=r_, end_column=11)
    new.row_dimensions[r_].height = max(new.row_dimensions[r_].height or 0, 52)
if n_flag:
    for dv in new.data_validations.dataValidation:
        if dv.formula1 == '"S1,S2,X1,X2,X3"':
            from openpyxl.worksheet.cell_range import MultiCellRange
            dv.sqref = MultiCellRange(' '.join('H%d' % rng.min_row for rng in dv.sqref.ranges))
    rm = wb['READ ME FIRST']
    for row_ in rm.iter_rows():
        for c in row_:
            if MODE == 'print' and isinstance(c.value, str) and 'contradiction_flag is pre-set to FALSE: change to TRUE only if' in c.value:
                c.value = c.value.replace('contradiction_flag is pre-set to FALSE: change to TRUE only if a passage contradicts the claim',
                    'contradiction_flag: write TRUE or FALSE in the box (it is blank on the printed form); write TRUE only if a passage contradicts the claim')
    print('paper tweaks applied to', n_flag, 'claims')

for ws_ in wb:                          # same Calibri fix on the other sheets
    if ws_ is old or ws_ is new: continue
    for row_ in ws_.iter_rows():
        for c in row_:
            if c.has_style and not c.font.name:
                f = copy(c.font); f.name = 'Calibri'; c.font = f
wb.remove(old); new.title = 'Forms'
# print version (21 Oct): raters answer on the Forms pages, so the Scoring table is not printed or shipped
if MODE == 'print' and 'Scoring' in wb.sheetnames:
    wb.remove(wb['Scoring'])
    rm_ = wb['READ ME FIRST']
    for row_ in rm_.iter_rows():
        for c in row_:
            v = c.value
            if not isinstance(v, str): continue
            if v.startswith('Layout:'):
                c.value = ('Layout: one claim per page: the claim, its SDG targets, the passages with a label box beside each, '
                           'then the score boxes and the comment box at the foot. Write all your answers on these pages.')
            elif v.startswith('Yellow cells are yours'):
                c.value = v.replace('Use only the drop-down values.', 'Use only the listed values.')
            elif v.startswith('Return this file'):
                c.value = 'Write your initials in the footer of every page and return all pages.'
# page number, large, top-right of every Forms page (plus existing footer)
new.page_margins.top = 0.75; new.page_margins.header = 0.3
new.oddHeader.right.text = 'Page &P of &N'
new.oddHeader.right.size = 12
new.oddHeader.right.font = 'Calibri,Bold'
new.oddHeader.left.text = new.oddFooter.center.text.split(' · ')[0]
new.oddHeader.left.size = 9
# page numbers on the other sheets too
for ws_ in wb:
    if ws_.title == 'Forms': continue
    base = ws_.oddFooter.center.text or ('Round 1 · ' + ws_.title)
    if '&P' not in base:
        ws_.oddFooter.center.text = base + ' · page &P of &N'
        ws_.oddFooter.center.size = 9
wb.active = idx
wb.save(DST)
print('rows', old.max_row, '->', out, '| split passages:', len(split_report), '| tables:', tables_done)
