# Round 1 Phase 2 (SMTEC) — what was sent to raters

*Recorded 23 Oct 2026; **corrected 28 Oct 2026**: DNA confirmed that **every rater received the EN version** (English only) in **large print** — the 23 Oct entry saying TH was wrong. The returned Phase 2 workbook's READ ME reads "version EN", consistent with this. Nothing below may be edited — any change after this point is a protocol deviation.*

| Item | File | MD5 (copy on disk, 23 Oct) |
|---|---|---|
| Rater handbook | `scorer/Scorer-Handbook-SMTEC-21OCT26-changes-marked-DNA-EE.docx` | e2f6758e0dd2f14bcd99a502a1dd4a76 |
| Form, large print (workbook) | `scorer/Round1-Phase2-SMTEC-form-v2-EN-large.xlsx` | c5dcde268a877930c031ae8e38375379 |
| Form, large print (PDF) | `scorer/print-pdf/Round1-Phase2-SMTEC-form-v2-EN-large.pdf` | a2240e23646235d7ffa6339383706543 |
| Key (DNA/EE only, never sent) | `scorer/Round1-60-KEY-EN-do-not-send.csv` | f62f0fa37434b94815ea708d6bf76701 |
| Challenge selection | `sdg-credibility-framework/data/outputs/revision/round1_challenge_selection.json` (EN: rules a+b+c) | 632bbd5001fb70eefb3f25872f41f67b |

The hashes are of the files on disk; they are assumed identical to the copies sent (built 21 Oct, not modified since). If the copies actually sent differ, record that here.

## What the raters have
- 60 claims: the representative 50 (same claims, text and passages as Phase 1, except that R21 X3 and R35 X3 show English only — Phase 1 showed English + Thai) and 10 challenge claims R51–R60 (match by uid in the EN key).
- Challenge set: target 4, assurance 2, certification 2, standard 2; screened by rules (a) no sentences from assurance statements, (b) no forward-looking commitments, (c) English-only claim text. Certification claims: PTTGC CLM-0050 (ISCC PLUS) and IVL CLM-0189 (ISMS / ISO 27001).
- Raters score S, M, T, E (0–3) and label every passage Extend / Redundant / Related / Unrelated / Contradicts (None pre-filled); C is computed by the team from X1–X3 Extend labels. No polarity, no contradiction flag, no retrieval_note, no Scoring sheet (answers on the Forms pages).
- E rule as in the handbook: standard without number = 1; with number (e.g. GRI 305 / 305-1), scope/period, or data location = 2; named assurer or certifying standard for this data = 3.

## Consequences for the framework side
- The V4 scoring prompt must implement this handbook exactly (including the E rule above) and must receive the EN evidence packs (Thai stripped), i.e. `--form scorer/Round1-Phase2-SMTEC-form-v2-EN.xlsx`, so that framework and raters see the same input.
- Freeze the V4 prompt, retrieval config (V7 chunk-aware, unchanged), C-from-labels rule, composite rule and tier cut-points before any Phase 2 workbook is returned; record the freeze with hashes in this folder.
- The TH variant was not sent; its files are in `scorer/_superseded/phase2-TH-not-sent/` (TH challenge selection: `revision/round1_challenge_selection_TH.json`).
- EE's pilot should therefore be the EN pilot (`Pilot20-SMTEC-form-v4-EN-large.*`), matching what the raters received; it is a dry run only, not part of the validation.
