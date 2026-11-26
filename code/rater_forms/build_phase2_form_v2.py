"""Round 1 Phase 2 (SMTEC) form, v2 (20 Oct 2026) -- built for handbook Scorer-Handbook-SMTEC-20OCT26.
Changes from the 12 Oct form:
  * 21 Oct: labels renamed to the DNA-edited handbook (Extend / Redundant / Related / Unrelated / Contradicts;
    'None' pre-filled); polarity removed (outside the construct; balance is excluded in manuscript section 2)
  * a label for every passage ('None' pre-filled
    for empty slots); C is no longer scored by raters, it is computed from the X1-X3 labels
  * contradiction_flag / contradicting_passage_id removed (a 'contradicts' label records it per passage)
  * 10-claim challenge set (round1_challenge_selection.json; 14 until 21 Oct) mixed into the shuffled order as R51-R60
  * READ ME corrected (no 'calibration only' line, no stray layout line, no cut-points)
The 50 representative claims keep their 12 Oct relative order and their exact display text.
Usage (repo root): python3 scorer/build_phase2_form_v2.py [en|th]   (en = English-only, default; th = keeps Thai)
"""
import json, csv, random, re
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, Protection
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.pagebreak import Break, RowBreak
from PIL import ImageFont

ROOT = Path(__file__).resolve().parent.parent
SC = ROOT / "scorer"; REV = ROOT / "sdg-credibility-framework/data/outputs/revision"
OLD_FORM = SC / "_superseded/phase2-pre-20Oct/Round1-Phase2-SMTEC-form.xlsx"
OLD_KEY = SC / "Round1-50-KEY-do-not-send.csv"
import sys
LANG = (sys.argv[1] if len(sys.argv) > 1 else "en").lower()   # "en" = English-only display; "th" = keep Thai (21 Oct)
assert LANG in ("en", "th")
SUF = "-EN" if LANG == "en" else "-TH"
PILOT = len(sys.argv) > 2 and sys.argv[2].lower() == "pilot"   # 21 Oct: same form for the 20 pilot claims (EE dry run)
OUT_FORM = SC / (f"Pilot20-SMTEC-form-v4{SUF}.xlsx" if PILOT else f"Round1-Phase2-SMTEC-form-v2{SUF}.xlsx")
OUT_KEY = SC / ("Pilot20-KEY-v4-do-not-send.csv" if PILOT else f"Round1-60-KEY{SUF}-do-not-send.csv")
SEED = 20261020
LABELS = '"Extend,Redundant,Related,Unrelated,Contradicts"'
SLOTS = ["S1", "S2", "X1", "X2", "X3"]
SLOT_NAME = {"S1": "S1 same-section", "S2": "S2 same-section", "X1": "X1 cross-section", "X2": "X2 cross-section", "X3": "X3 cross-section"}
HANDBOOK = "Scorer-Handbook-SMTEC-21OCT26"

GREY = PatternFill("solid", fgColor="FFE7E6E6"); YEL = PatternFill("solid", fgColor="FFFFF2CC")
HEAD = PatternFill("solid", fgColor="FFDDEBF7"); CLAIMF = PatternFill("solid", fgColor="FFFCE4D6")
NONEF = PatternFill("solid", fgColor="FFF2F2F2")
TH = Side(style="thin", color="FF808080"); MD = Side(style="medium", color="FF000000")
BOX = Border(left=TH, right=TH, top=TH, bottom=TH); MBOX = Border(left=MD, right=MD, top=MD, bottom=MD)
F = lambda sz=9, b=False, i=False: Font(name="Calibri", size=sz, bold=b, italic=i)
WRAP_TOP = Alignment(wrap_text=True, vertical="top"); CENTER = Alignment(wrap_text=True, horizontal="center", vertical="center")
LOCK, OPEN = Protection(locked=True), Protection(locked=False)

_f = {}
def n_lines(text, width_px, sz=9, bold=False):
    key = (sz, bold)
    if key not in _f:
        _f[key] = ImageFont.truetype("/usr/share/fonts/truetype/crosextra/Carlito-%s.ttf" % ("Bold" if bold else "Regular"), int(round(sz * 96 / 72)))
    f = _f[key]; total = 0
    for para in str(text).split("\n"):
        line, cnt = "", 1
        for w in para.split(" "):
            cand = w if not line else line + " " + w
            if f.getlength(cand) <= width_px or not line:
                line = cand
                while f.getlength(line) > width_px and len(line) > 1:
                    cnt += 1; line = line[int(len(line) * width_px / f.getlength(line)):]
            else:
                cnt += 1; line = w
        total += cnt
    return total
def h_for(text, ncols, sz=9, bold=False, minh=17):
    w = ncols * 11.5 * 7.0 - 8
    return max(minh, min(409, n_lines(text, w, sz, bold) * 12.2 + 5))

def clean(t):
    t = re.sub(r"<a id='[^']*'></a>\s*", "", t); t = t.replace("**", "")
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", t); t = re.sub(r"\n\s*\n+", "\n", t).strip()
    out = []
    for ln in t.split("\n"):
        if out and len(ln) <= 40 and len(out[-1].split(" | ")[-1]) <= 40: out[-1] += " | " + ln
        else: out.append(ln)
    return "\n".join(out)

if PILOT:
    # ---- the 20 pilot claims, in the pilot key's P01..P20 order (packs as stored in pilot20_selection.json) ----
    pkey = list(csv.DictReader(open(SC / "Pilot20-KEY-do-not-send.csv")))
    psel = {c["uid"]: c for c in json.load(open(REV / "pilot20_selection.json"))}
    text50, key50, items, order = {}, [], {}, []
    for k in pkey:
        c = psel[k["uid"]]; cid = k["pilot_id"]
        t = {"report": c["report"], "CLAIM": f"[Section: {c['section']}, p. {c['page']}]\n{c['claim_text']}", "sdg_targets": c["sdg_targets"]}
        have = {p["pid"]: p for p in c["pack"]}
        for sl in SLOTS:
            t[sl] = f"[Section: {have[sl]['section']}, p. {have[sl]['page']}]\n{clean(have[sl]['text'])}" if sl in have else "(no passage retrieved)"
        items[cid] = (t, c); order.append(cid)
    assert len(order) == 20
else:
    # ---- the 50: exact text and order from the 12 Oct form ----
    old = openpyxl.load_workbook(OLD_FORM); ows = old["Forms"]
    text50, cur = {}, None
    for r in range(1, ows.max_row + 1):
        a = ows.cell(r, 1).value
        if isinstance(a, str) and a.startswith("#"): cur = a.split()[2]; text50[cur] = {"report": a.split()[3]}
        elif cur and isinstance(a, str): text50[cur][a.split()[0]] = ows.cell(r, 2).value
    order50 = [ows.cell(r, 1).value.split()[2] for r in range(1, ows.max_row + 1)
               if isinstance(ows.cell(r, 1).value, str) and ows.cell(r, 1).value.startswith("#")]
    assert len(order50) == 50
    key50 = list(csv.DictReader(open(OLD_KEY)))

    # ---- the 14 challenge claims ----
    ch = json.load(open(REV / ("round1_challenge_selection.json" if LANG == "en" else "round1_challenge_selection_TH.json")))["claims"]
    rng = random.Random(SEED)
    ch_sorted = sorted(ch, key=lambda c: c["uid"]); rng.shuffle(ch_sorted)
    items = {}
    for i, c in enumerate(ch_sorted):
        cid = "R%02d" % (51 + i)
        t = {"report": c["report"], "CLAIM": f"[Section: {c['section']}, p. {c['page']}]\n{c['claim_text']}", "sdg_targets": c["sdg_targets"]}
        have = {p[0]: p for p in c["pack"]}
        for s in SLOTS:
            t[s] = f"[Section: {have[s][2]}, p. {have[s][3]}]\n{clean(have[s][4])}" if s in have else "(no passage retrieved)"
        items[cid] = (t, c)
    order = list(order50)
    for cid in sorted(items):
        order.insert(rng.randint(0, len(order)), cid)
    assert len(order) == 60 and len(set(order)) == 60

THAI_TOK = re.compile(r"[\u0e00-\u0e7f]")
_TH = "\u0e00-\u0e7f"
THAI_RUN = re.compile(r"[(“\"']?[%s](?:[%s \t“”\"'(),.\-/:;0-9]|(?<=[ \t])[A-Za-z0-9(),.&\-]{1,14}(?=[ \t]))*[%s][)”\"']?|[(“]?[%s][)”]?" % (_TH, _TH, _TH, _TH))
def strip_thai(t):
    """English-only display (21 Oct, DNA): the Thai in these packs is the bilingual reports' Thai
    rendering of the adjacent English. Removes each run of Thai script, including spaces, quotes,
    brackets and short Latin words (<= 14 chars) embedded between Thai words; a run never crosses
    a line break, '|' or an HTML tag, so table structure and English text are kept."""
    if not isinstance(t, str) or not THAI_TOK.search(t): return t
    t = THAI_RUN.sub(" ", t)
    t = re.sub(r"\(\s*\)", "", t)                    # brackets emptied by the removal
    t = re.sub(r"[ \t]+([.,;:)])", r"\1", t)          # space left before punctuation
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"\|\s*(?=\|)", "", t)                 # empty '| |' segments
    t = re.sub(r"[ \t]+(</t[dh]>)", r"\1", t)
    t = "\n".join(re.sub(r"^\s*\|\s*|\s*\|\s*$", "", l).strip() for l in t.split("\n"))
    return "\n".join(l for l in t.split("\n") if l)
def disp(cid):
    d = text50[cid] if cid in text50 else items[cid][0]
    return {k: (strip_thai(v) if (k != "report" and LANG == "en") else v) for k, v in d.items()}

# ---- workbook ----
wb = openpyxl.Workbook(); rm = wb.active; rm.title = "READ ME FIRST"
rm.column_dimensions["A"].width = 100
lines = [
 (("SMTEC — PILOT — 20 claims — " if PILOT else "SMTEC — Round 1 — Phase 2 FORM workbook — 60 claims — ") + ("version EN" if LANG == "en" else "version TH"), True),
 (f"Handbook: {HANDBOOK} (DNA/EE, 21 Oct 2569) · form v2 built 21 Oct 2026. The row order differs from Phase 1 and some claims are new; always match by claim_id.", False),
 (("Purpose: pilot of the 21 Oct handbook and this form, and the reference for checking the V4 scoring prompt before Round 1 Phase 2. Not part of the validation. Please note anything unclear in the comment boxes." if PILOT else "Purpose: your scores are part of the held-out validation of the SMTEC instrument. They are used to measure agreement between raters, and between raters and the framework. Score independently; do not discuss individual claims with other raters until all workbooks are returned."), False),
 ("Passages: S1–S2 come from the SAME section as the claim; X1–X3 come from OTHER sections (cross-section). The [Section: …] tag on each passage can be compared with the tag on the claim. '(no passage retrieved)' is information about the report, not an error.", False),
 ("Order for each claim (handbook §4): (1) score S, M, T from the claim text only; do not read the passages yet. (2) Score E reading the claim with all passages S1–S2 and X1–X3 (handbook §5.4). (3) Give EVERY passage one label in the box to its right: Extend / Redundant / Related / Unrelated / Contradicts (handbook §6); empty slots are pre-filled 'None'. (4) comment when unsure, when the passages are unhelpful, or when the claim text looks truncated (§7).", False),
 ("You do not score C. The research team computes C from your X1–X3 labels: the number of different Sections with a passage labelled 'Extend' (handbook §5.5).", False),
 ("Yellow cells are yours; do not edit white or grey cells. Use only the drop-down values. Leave no yellow cell blank except comment. If undecided between two scores, choose the lower and comment; if undecided between Extend and Redundant, choose Redundant and comment.", False),
 ('Layout: sheet "Forms" has one claim per page: claim, SDG targets, passages with a label box beside each, then the score boxes at the foot of the page. Sheet "Scoring" is the same ' + str(len(order)) + ' claims in table form for typing or transcription; if you score on paper, copy everything into "Scoring" before returning the file.', False),
 ("Return this file with your initials in the filename.", False),
]
for i, (t, b) in enumerate(lines, 1):
    c = rm.cell(i, 1, t); c.font = F(11, b); c.alignment = WRAP_TOP
rm.page_setup.orientation = "landscape"; rm.sheet_properties.pageSetUpPr.fitToPage = True; rm.page_setup.fitToHeight = 0
rm.oddFooter.center.text = ("Pilot 20" if PILOT else "Round 1") + " · READ ME FIRST · page &P of &N"; rm.oddFooter.center.size = 9

ws = wb.create_sheet("Forms")
ws.column_dimensions["A"].width = 15
for col in "BCDEFGHIJK": ws.column_dimensions[col].width = 11.5
dvs = {k: DataValidation(type="list", formula1=f, allow_blank=True) for k, f in
       [("score", '"0,1,2,3"'), ("label", LABELS)]}
for dv in dvs.values(): ws.add_data_validation(dv)

def put(r, c, v=None, font=None, fill=None, al=None, border=BOX, prot=LOCK):
    x = ws.cell(r, c, v)
    if font: x.font = font
    if fill: x.fill = fill
    if al: x.alignment = al
    if border: x.border = border
    x.protection = prot
    return x
def merge_box(r, c1, c2, border=BOX, fill=None, prot=LOCK):
    for c in range(c1, c2 + 1):
        x = ws.cell(r, c); x.border = border if c in (c1, c2) else Border(top=border.top, bottom=border.bottom)
        if c == c1: x.border = Border(left=border.left, top=border.top, bottom=border.bottom, right=border.right if c1 == c2 else None)
        if c == c2 and c2 != c1: x.border = Border(right=border.right, top=border.top, bottom=border.bottom)
        if fill: x.fill = fill
        x.protection = prot
    if c2 > c1: ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)

r = 0; breaks = []; label_cells = {}
for n, cid in enumerate(order, 1):
    t = disp(cid)
    r += 1  # header
    put(r, 1, f"# {n}   {cid}   {t['report']}        Rater: ________", F(11, True), HEAD, border=None)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=11); ws.row_dimensions[r].height = 18
    r += 1  # claim
    put(r, 1, "CLAIM", F(9, True), GREY, WRAP_TOP); put(r, 2, t["CLAIM"], F(9, True), CLAIMF, WRAP_TOP)
    merge_box(r, 2, 11, fill=CLAIMF); ws.row_dimensions[r].height = h_for(t["CLAIM"], 10, 9, True)
    r += 1  # targets + label header
    put(r, 1, "sdg_targets", F(9, True), GREY, WRAP_TOP); put(r, 2, t["sdg_targets"], F(9), None, WRAP_TOP)
    merge_box(r, 2, 9)
    put(r, 10, "passage label\nExtend · Redundant · Related · Unrelated · Contradicts", F(8, True), GREY, CENTER); merge_box(r, 10, 11, fill=GREY)
    ws.row_dimensions[r].height = 46
    for s in SLOTS:
        r += 1
        txt = t[s]; empty = txt.strip() == "(no passage retrieved)"
        put(r, 1, SLOT_NAME[s], F(9, True), GREY, WRAP_TOP); put(r, 2, txt, F(9, i=empty), None, WRAP_TOP); merge_box(r, 2, 9)
        if empty:
            put(r, 10, "None", F(10, False, True), NONEF, CENTER, border=BOX); merge_box(r, 10, 11, fill=NONEF)
        else:
            put(r, 10, None, F(12, True), YEL, CENTER, border=MBOX, prot=OPEN); merge_box(r, 10, 11, border=MBOX, fill=YEL, prot=OPEN)
            dvs["label"].add(f"J{r}")
        label_cells[(cid, s)] = None if empty else f"J{r}"
        ws.row_dimensions[r].height = h_for(txt, 8, 9)
    r += 1  # scores title
    put(r, 1, f"SCORES for {cid}  ·  Order: S, M, T from the claim text only → E from claim + all passages (§5.4) → one label for every passage, in the boxes on the right (§6) → comment if needed (§7). C is not scored here; it is computed from your X1–X3 labels.",
        F(9, True), GREY, WRAP_TOP, border=None)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=11); ws.row_dimensions[r].height = 28
    r += 1  # scores
    put(r, 1, "scores", F(9, True), GREY)
    for k, (lab, col) in enumerate([("S (0–3)", 2), ("M (0–3)", 4), ("T (0–3)", 6), ("E (0–3)", 8)]):
        put(r, col, lab, F(10, True), GREY, CENTER); put(r, col + 1, None, F(14, True), YEL, CENTER, MBOX, OPEN)
        dvs["score"].add(ws.cell(r, col + 1).coordinate)
    put(r, 10, "C: computed from labels", F(9, False, True), GREY, CENTER); merge_box(r, 10, 11, fill=GREY)
    ws.row_dimensions[r].height = 30
    r += 1  # comment
    put(r, 1, "comment", F(9, True), GREY, WRAP_TOP); put(r, 2, None, F(11), YEL, WRAP_TOP, MBOX, OPEN); merge_box(r, 2, 11, MBOX, YEL, OPEN)
    ws.row_dimensions[r].height = 70
    r += 1; ws.row_dimensions[r].height = 8   # spacer
    breaks.append(r)
ws.row_breaks = RowBreak()
for b in breaks[:-1]: ws.row_breaks.append(Break(id=b))
ws.page_setup.orientation = "portrait"; ws.page_setup.paperSize = 9
ws.sheet_properties.pageSetUpPr.fitToPage = True; ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 0
ws.page_margins.left = ws.page_margins.right = 0.4; ws.page_margins.top = ws.page_margins.bottom = 0.5
ws.oddFooter.center.text = ("Pilot 20 SMTEC" if PILOT else "Round 1 Phase 2") + " · page &P of &N · initials: ________"; ws.oddFooter.center.size = 9
ws.protection.sheet = True; ws.protection.formatRows = False

# ---- Scoring sheet ----
sc = wb.create_sheet("Scoring")
hdr = ["#", "claim_id", "S", "M", "T", "E", "label_S1", "label_S2", "label_X1", "label_X2", "label_X3", "comment"]
widths = [5, 10, 6, 6, 6, 6, 13, 13, 13, 13, 13, 55]
for j, (h, w) in enumerate(zip(hdr, widths), 1):
    x = sc.cell(1, j, h); x.font = Font(name="Calibri", bold=True); x.fill = GREY; x.alignment = CENTER; x.border = BOX
    sc.column_dimensions[openpyxl.utils.get_column_letter(j)].width = w
sdv = {k: DataValidation(type="list", formula1=f, allow_blank=True) for k, f in
       [("score", '"0,1,2,3"'), ("label", LABELS)]}
for dv in sdv.values(): sc.add_data_validation(dv)
for i, cid in enumerate(order, 1):
    rr = i + 1
    for j in range(1, 13):
        x = sc.cell(rr, j); x.font = F(11); x.alignment = WRAP_TOP; x.border = BOX
    sc.cell(rr, 1, i).protection = LOCK; sc.cell(rr, 2, cid).protection = LOCK
    for j in range(3, 7):
        x = sc.cell(rr, j); x.fill = YEL; x.protection = OPEN; sdv["score"].add(x.coordinate)
    for k, s in enumerate(SLOTS):
        x = sc.cell(rr, 7 + k)
        if label_cells[(cid, s)] is None: x.value = "None"; x.fill = NONEF; x.font = F(11, i=True); x.protection = LOCK
        else: x.fill = YEL; x.protection = OPEN; sdv["label"].add(x.coordinate)
    x = sc.cell(rr, 12); x.fill = YEL; x.protection = OPEN
    sc.row_dimensions[rr].height = 30
sc.freeze_panes = "C2"; sc.protection.sheet = True; sc.print_title_rows = "1:1"
sc.page_setup.orientation = "landscape"; sc.sheet_properties.pageSetUpPr.fitToPage = True; sc.page_setup.fitToHeight = 0
sc.oddFooter.center.text = ("Pilot 20" if PILOT else "Round 1") + " · Scoring · initials: ________ · page &P of &N"; sc.oddFooter.center.size = 9
wb.active = 0
wb.save(OUT_FORM)

# ---- key (do not send) ----
if PILOT:
    with open(OUT_KEY, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["pilot_id", "uid", "selection_reason", "claim_type", "v7_S", "v7_M", "v7_T", "v7_E", "v7_C", "v7_tier", "empty_slots", "form"])
        for cid in order:
            c = items[cid][1]; v = c["v7"]
            w.writerow([cid, c["uid"], c["selection_reason"], c["claim_type"], v["S"], v["M"], v["T"], v["E"], v["C"], v["tier"],
                        " ".join(sl for sl in SLOTS if label_cells[(cid, sl)] is None), OUT_FORM.name])
    print("pilot form:", OUT_FORM.name, "| claims:", len(order), "| key:", OUT_KEY.name); raise SystemExit
fields = ["claim_id", "set", "challenge_category", "uid", "company", "sector", "report", "claim_type", "stratum", "weight",
          "v7_S", "v7_M", "v7_T", "v7_E", "v7_C", "v7_tier", "absence_flag", "phase1_row", "phase2_row", "empty_slots"]
pos = {cid: i + 1 for i, cid in enumerate(order)}
with open(OUT_KEY, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader()
    for k in key50:
        w.writerow({**{f: k.get(f, "") for f in fields}, "set": "representative", "challenge_category": "",
                    "phase2_row": pos[k["claim_id"]],
                    "empty_slots": " ".join(s for s in SLOTS if label_cells[(k["claim_id"], s)] is None)})
    for cid in sorted(items):
        t, c = items[cid]; v = c["v7"]
        w.writerow({"claim_id": cid, "set": "challenge", "challenge_category": c["challenge_category"], "uid": c["uid"],
                    "company": c["company"], "sector": c["sector"], "report": c["report"], "claim_type": c["claim_type"],
                    "stratum": "challenge|" + c["challenge_category"], "weight": "",
                    "v7_S": v["S"], "v7_M": v["M"], "v7_T": v["T"], "v7_E": v["E"], "v7_C": v["C"], "v7_tier": v["tier"],
                    "absence_flag": any("threshold" in f for f in c["flags"]), "phase1_row": "", "phase2_row": pos[cid],
                    "empty_slots": " ".join(s for s in SLOTS if label_cells[(cid, s)] is None)})
print("form:", OUT_FORM.name, "| rows:", ws.max_row, "| claims:", len(order), "| key:", OUT_KEY.name)
print("challenge positions:", {cid: pos[cid] for cid in sorted(items)})
