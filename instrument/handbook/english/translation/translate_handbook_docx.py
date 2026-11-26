"""Replace Thai paragraphs in a docx with English (same order as keys file); drop change-marking; switch Thai Latin font to Calibri."""
import sys, json, re, zipfile, shutil, os, docx
from docx.shared import Pt
src, keys_f, en_f, dst, note = sys.argv[1:6]
TH = re.compile('[\u0E00-\u0E7F]')
keys = json.load(open(keys_f)); en = json.load(open(en_f))
assert len(keys) == len(en), (len(keys), len(en))
M = dict(zip(keys, en))
d = docx.Document(src)
def paras(d):
    for p in d.paragraphs: yield p
    for t in d.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs: yield p
done = set(); todo = []
for p in paras(d):
    if id(p._p) in done: continue
    done.add(id(p._p)); todo.append(p)
miss = []
for p in todo:
    t = p.text
    for r in p.runs:  # drop change-marking
        rp = r._r.rPr
        if rp is not None:
            for tag in ('highlight', 'color'):
                for el in rp.findall('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}' + tag): rp.remove(el)
    if not TH.search(t): continue
    if t not in M: miss.append(t); continue
    runs = p.runs
    runs[0].text = M[t]
    for r in runs[1:]: r._r.getparent().remove(r._r)
assert not miss, miss
# translator's note after the "For raters/experts" line (3rd paragraph)
anchor = d.paragraphs[2]
newp = anchor.insert_paragraph_before('') if False else None
from copy import deepcopy
np_ = deepcopy(d.paragraphs[3]._p); anchor._p.addnext(np_)
from docx.text.paragraph import Paragraph
P = Paragraph(np_, anchor._parent)
for r in P.runs[1:]: r._r.getparent().remove(r._r)
P.runs[0].text = note; P.runs[0].italic = True; P.runs[0].bold = False
from docx.enum.text import WD_ALIGN_PARAGRAPH
for t in d.tables:
    for row in t.rows:
        for c in row.cells:
            for q in c.paragraphs:
                if q.alignment != WD_ALIGN_PARAGRAPH.CENTER: q.alignment = WD_ALIGN_PARAGRAPH.LEFT
d.save(dst)
# font swap and size scaling at XML level
tmp = dst + '.tmp'; shutil.copy(dst, tmp)
with zipfile.ZipFile(tmp) as zi, zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zo:
    for it in zi.infolist():
        b = zi.read(it.filename)
        if it.filename in ('word/document.xml', 'word/styles.xml') or it.filename.startswith('word/footer'):
            s = b.decode('utf8')
            s = re.sub(r'w:(ascii|hAnsi|eastAsia)="TH SarabunPSK"', r'w:\1="Calibri"', s)
            s = re.sub(r'<w:sz w:val="(\d+)"/>', lambda m: '<w:sz w:val="%d"/>' % max(18, round(int(m.group(1)) * 0.72)), s)
            b = s.encode('utf8')
        zo.writestr(it, b)
os.remove(tmp)
left = [p.text for p in paras(docx.Document(dst)) if TH.search(p.text)]
print('remaining Thai paragraphs:', len(left))
