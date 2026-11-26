# Round 1 — returned workbooks log

Each returned workbook is logged on arrival with its hash. **Rule (DNA, 28 Oct 2026): returned workbooks stay unopened — no scores read or analysed — until EE's pilot check is done and V4 is frozen (scorer/FREEZE-V4-*.md).** Only the READ ME title was read to confirm the form version.

| Submitted by rater | File time in Results/ | Rater | Phase | File | MD5 | Opened for analysis |
|---|---|---|---|---|---|---|
| 2026-10-20 | 2026-10-28 01:42 | Rater D | 1 (holistic) | `scorer/Results/Expert Opinion/Rater D/Round1-Phase1-HOLISTIC-form-large-Rater D.xlsx` | 253d5577540818d890534b64f84c4040 | no |
| 2026-10-27 (evening) | 2026-10-28 00:29 | Rater D | 2 (SMTEC, version EN) | `scorer/Results/Expert Opinion/Rater D/Round1-Phase2-SMTEC-form-v2-EN-large-Rater D.xlsx` | 7bad2849bba8a36f427a8f3b437f3c38 | no |

## Notes for the analysis and the paper
- **Rater D is the same person as Expert 2 of the development study** (scored the 63-claim development sample under the earlier rubric; did not develop the rubric, prompt or handbooks). Round 1 claims come from held-out reports and none were in the development sample, but this rater is not naive to the instrument. Report this in the paper; give rater-level results; report α with and without this rater (sensitivity), so that independence cannot be questioned (round-2 reviewer point 1 noted Expert 2's role in development).
- Submission dates as reported by DNA (28 Oct 2026): Phase 1 submitted 20 Oct 2026; Phase 2 submitted the evening of 27 Oct 2026, a week after Phase 1. Phase 1 was completed before the rater saw the Phase 2 (SMTEC) form, so the holistic judgement was not shaped by SMTEC scoring. The "file time" column is when the copies were saved into scorer/Results/, not the submission time.
- The V4 code (prompt, scorer, retrieval, settings) was committed to GitHub on 2026-10-23 15:08 UTC (commit c39c547). This is AFTER the Phase 1 return (20 Oct) and BEFORE the Phase 2 return (27 Oct). The Phase 1 workbook was not opened or used in writing V4; V4 was written from the rater handbook (21OCT26 DNA-EE) only. Phase 1 holds holistic tiers, not SMTEC scores, so it could not have informed the V4 rubric text. Hashes re-verified on 28 Oct.
- Within-rater analysis (Phase 1 holistic tier vs the rater's own SMTEC-implied tier) is deferred to after the freeze, together with all other analyses, so that no rater data is seen before the cut-points, composite rule and E rule are frozen.

## V4 frozen and Round 1 scored (30 Oct 2026)
- V4 frozen 30 Oct 2026 02:14 UTC (scorer/FREEZE-V4-30Oct2026.md); freeze commit 6665e4f pushed to GitHub by DNA before any returned workbook was opened.
- V4 scored the 60 Round 1 claims from `scorer/Round1-Phase2-SMTEC-form-v2-EN.xlsx` (MD5 23b5c161f4c75cbe2aa228474482c83e) on 30 Oct 2026: `sdg-credibility-framework/data/outputs/revision/v4_round1_EN.json`, 60 claims, prompt V4-2026-10-23, prompt-text SHA-256 87533a24ad7c…, output SHA-256 bd3501903787614dc52b58f5ac716eef3151effa0c58cc422ec57f67fe109512.
- Only after this record is committed are the returned workbooks opened for analysis.

## Opened 30 Oct 2026 (after freeze push and V4 Round 1 record) — integrity check
- Both files open cleanly; MD5 unchanged since logging (253d5577…, 7bad2849…).
- Claims and passages: identical to the forms sent (Phase 1: 50 claims; Phase 2: 60 claims, same IDs, same order, same claim and passage text).
- Phase 1: all 50 judgements filled; criteria for the three levels written in READ ME (B17–B19); closing note "use approach as proposed in the beginning session, No change applied."
- **File metadata: both files were last saved by the Office user "EE" (her Office account name)** (Phase 1: 20 Oct 2026 09:55; Phase 2: 27 Oct 2026 16:07). The blank forms carry no such name. To be explained by DNA before analysis (e.g. transcription of paper forms, forwarding, or a shared computer).
- **Phase 2 file is the 20 Oct build of the EN large form**, not the 21 Oct build recorded in SENT-Round1-Phase2-21Oct.md: its READ ME says "Handbook: Scorer-Handbook-SMTEC-20OCT26 (DNA/EE, 20 Oct 2569) · form v2 built 20 Oct 2026". Claims and passages are identical to the 21 Oct build; only the READ ME handbook reference differs. Which handbook Rater D used (20OCT26 or 21OCT26) to be confirmed.
- Phase 2 READ ME has an added note (A14–A15): "Note to researchers: In 5.4 Evidence, awards that an organization achieved should be included in Category 3."
- **Explained by DNA (30 Oct 2026):** Rater D scored on paper; EE typed Rater D's paper answers into the Excel files (hence "EE" (her Office account name) as last saver). The scores are Rater D's. Keep the paper originals as the source record; a transcription check (paper vs Excel) on a sample is advisable. The READ ME note on awards (A14–A15) cannot be attributed with certainty to Rater D or to EE; it is not used as rater data.
- **Handbook (DNA, 30 Oct 2026):** Rater D used the final handbook Scorer-Handbook-SMTEC-21OCT26; only the workbook's READ ME header came from the 20 Oct build.

## Further returns found 10 Nov 2026 (filed by DNA under scorer/Results/Expert Opinion/<rater>/)
Rater D's two files were moved there by DNA (identical MD5); the root copies were moved to _to_delete-10Nov2026/ on 10 Nov. New returns, logged with hashes, not yet opened for analysis:

| File time | Rater | Phase | File | MD5 | Opened for analysis |
|---|---|---|---|---|---|
| 2026-11-09 19:32 | Rater A | 1 (holistic) | `scorer/Results/Expert Opinion/Rater A/Round1-Phase1-HOLISTIC-form_<name>.xlsx` | afd2a653b79ae0c70ee06a5a83bcfee5 | no |
| 2026-11-09 19:32 | Rater A | 2 (SMTEC) | `scorer/Results/Expert Opinion/Rater A/Round1-Phase2-SMTEC-form-v2-EN-scored_<name>.xlsx` | 9527e5e539386e6fa2c9d398d5ce077c | no |
| 2026-11-09 19:33 | Rater E (withdrew) | 1 (holistic) | `scorer/Results/Expert Opinion/Rater E (withdrew)/Round1-Phase1-HOLISTIC-form-Rater E (withdrew).xlsx` | 4f3d96e782166622db8905917590d0cd | no |
| 2026-11-09 19:33 | Rater B | 2 (SMTEC) | `scorer/Results/Expert Opinion/Rater B/Paint-Round1-Phase2-SMTEC-form-v2-EN.pdf` | 0c47c84274ac18013b076c3f2a5edb1d | no |
| 2026-11-09 19:33 | Rater B | 1 (holistic) | `scorer/Results/Expert Opinion/Rater B/Round1-Phase1-HOLISTIC-form_Paint.xlsx` | dc52cad3cc9917d4dbc357f5c47c3881 | no |
| 2026-11-09 19:33 | Rater C | 1 (holistic) | `scorer/Results/Expert Opinion/Rater C/Round1-Phase1-HOLISTIC-form-Rater C.xlsx` | fba7f03ebb2c01c6585150c79fda5c29 | no |

Notes: Rater B's Phase 2 is a PDF (needs transcription or a scan check); Rater E (withdrew) and Rater C have Phase 1 only so far. Real names in file names are shown here as <name>; files are never released.

## Opened 10 Nov 2026 (V4 frozen and pushed 30 Oct; Round 1 V4 output hash recorded 30 Oct)
- Rater A: Phase 1 complete (50/50); Phase 2 complete (60/60); files last saved by the rater's own Office account. Phase 2 is the screen workbook (no Scoring sheet), same layout as the large form; claims parsed by claim_id.
- Rater C: Phase 1 complete (50/50); file last saved by "EE" (Office account) — presumably typed in by EE from paper as for Rater D; to confirm.
- Rater B: Phase 1 complete (50/50; saved by the rater, 18 Oct). Phase 2 returned as a 104-page PDF with handwritten answers (no form fields or annotations; text layer is the blank form) — must be transcribed before analysis. Its READ ME header is the 20 Oct build (as Rater D's); see note below.
- Rater E (withdrew): Phase 1 only 2 of 50 judged (R01, R02); rest blank. Follow up with the rater.
- Note: two returned Phase 2 copies (Rater D, Rater B) carry the 20 Oct build header ("Handbook: Scorer-Handbook-SMTEC-20OCT26 … form v2 built 20 Oct"). Claims and passages are identical to the 21 Oct build. DNA confirmed raters used the 21OCT26 handbook (30 Oct, for Rater D); SENT-Round1-Phase2-21Oct.md should note that the distributed workbook header was the 20 Oct build.
- Analyses: revision/round1-analysis/Round1-all-raters.md (all raters), Rater A-results.md / Rater D-results.md (per rater).

## Rater B Phase 2 transcription (10 Nov 2026)
- Source: handwritten PDF (MD5 0c47c842…). Transcribed by Claude (AI) from page images into the blank EN large form: `scorer/Results/Expert Opinion/Rater B/Round1-Phase2-SMTEC-form-v2-EN-large-Rater B-transcribed.xlsx`; check list `Rater B-transcription-check.csv` (one row per claim with PDF pages and notes).
- Rules used: ditto marks = the label written above; crossed-out values replaced by the value written beside them; pre-filled None slots matched the rater's empty slots in all 60 claims (consistency check).
- Unresolved, left blank: R11 S (looks like '5') — resolved: 2, confirmed by DNA 10 Nov 2026, R44 X3 (both 'Related' and 'Unrelated' written) — resolved: Related, confirmed by DNA 10 Nov 2026. Uncertain readings: R28 S, R09 E, R17 S, R51 E, R08 M (cell notes).
- Comments not transcribed (35+ handwritten, partly Thai; PDF pages listed).
- STATUS: needs a human check against the PDF before Rater B's Phase 2 enters the analysis.

## Analysis of raters with both phases (10 Nov 2026)
- DNA asked to process raters who completed both phases: Rater A, Rater B, Rater D. Rater B's Phase 2 uses the AI transcription (the 2 unreadable cells were later confirmed by DNA: R11 S = 2, R44 X3 = Related; analysis rerun); a human check against the PDF has not been recorded.
- Results: revision/round1-analysis/Round1-both-phases.md (run with `analyse_round1_all.py --both`); per rater: Rater A-, Rater B-, Rater D-results.md.

## Rater roles (DNA, 10 Nov 2026)
EE briefed each rater on their role and asked each rater to judge from that role's point of view (confirmed by DNA, 10 Nov 2026). Roles correspond to the reader groups named in the handbooks (analyst or investor, assurer, regulator, civil society or media, lender).

| Rater | Role |
|---|---|
| Rater A | consultant |
| Rater B | consultant |
| Rater C | analyst |
| Rater D | civil society / media |
| Rater E (withdrew) | not yet recorded |

Clarified by DNA (10 Nov 2026): for Rater A and Rater B the role is their own profession; for Rater C and Rater D the role was an assigned reader perspective, not their occupation (both are university lecturers). Backgrounds and the agreed manuscript wording: revision/manuscript-notes-rater-comments.md (internal).

To report in the paper (methods): raters were assigned reader perspectives, so agreement between raters of different roles mixes perspective and individual differences. Same-role agreement (Rater A vs Rater B, both consultants) is the only comparison free of the role difference. Analyses by role are descriptive only: one or two raters per role.
This instruction is not in the written handbooks (they ask raters to judge as a reader who wants to check the claim, listing the reader groups); it was given in EE's briefing. Record what was said in the briefing, and whether it applied to Phase 1, Phase 2 or both.

## Rater D's status (DNA, 10 Nov 2026)
Rater D is treated as an external rater: he served as an external rater from the outset and did not take part in designing the instrument (rubric, prompt, handbooks). He also rated the development sample, which the paper discloses; agreement is reported with and without him.

## Panel status (DNA, 10 Nov 2026)
Rater E (withdrew) is dropped from the panel (Phase 1 incomplete: 2 of 50 judged; no Phase 2); reported as a withdrawn rater. EE is following up Rater C's Phase 2. EE is writing a short account of the rater briefing.

## Rater C Phase 2 received (16 Nov 2026) — panel closed
- File: `scorer/Results/Expert Opinion/Rater C/Round1-Phase2-SMTEC-form-v2-EN-large-Rater C.xlsx` (MD5 bc106bced353b3c4f827b0cd53210f43), saved 16 Nov 2026 under EE's Office account. DNA confirmed (16 Nov): EE typed Rater C's paper answers in, for both phases.
- Complete: 60/60 claims with S, M, T, E and all five passage labels; no comments.
- DNA (16 Nov 2026): Rater C is the last rater. Final Round 1 panel = Rater A, Rater B, Rater C, Rater D (both phases); Rater E (withdrew) withdrawn (Phase 1: 2 of 50; no Phase 2).
- Rerun 16 Nov with four raters: Rater C-results.md / Rater C-ratings.csv, Round1-all-raters.md, Round1-both-phases.md, Round1-agreement-CI.md/.csv, Remaining-analyses-10Nov.md, findings-v4/E-strict-sensitivity.md (rater table).
- Headline rule with the final panel: α for C among raters = 0.28 (< 0.667) → headline composite stays SMTE.
- Observation (not a correction): Rater C scores much higher than the other raters (means S 2.30, M 2.07, T 1.93; no 0 given on S or M; 90% of passages labelled Extend). Checked whether a one-point shift of the scale explains it: it does not (κ with V4 and with Rater A stays low after subtracting 1). Scores are used as returned. Open point for EE: confirm the typed values against Rater C's paper for a few claims (e.g. R05, R08, R10 Measurability).
- Still not recorded: a human check of the Rater B transcription.
- Data-entry check (16 Nov 2026): DNA compared Rater C's paper forms with the typed file for 10 claims (7 drawn at random, seed 20261116: R14, R22, R26, R33, R41, R55, R60; plus R05, R08, R10 chosen because they differed most from V4): Phase 2 scores S, M, T, E and the five passage labels, and the Phase 1 judgement for the 8 representative claims. Result: the typed values are correct. Rater C's scores are treated as correctly entered; her difference from the other raters is a rating difference, not a typing error.
- From Rater C's paper (DNA, 16 Nov 2026): she wrote no 0 on Specificity or Measurability; passage labels were written out individually (no ditto marks), "EX" for almost every same-section and cross-section passage.
- Decision (DNA, 16 Nov 2026): all four raters are the primary result; a sensitivity analysis without Rater C is reported and labelled as such (decided after seeing her scores, so it is not pre-specified).
