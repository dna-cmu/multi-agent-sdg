# Round 1 holdout rating: sampling and procedure note

*12 Oct 2026. Drafted by CL for DNA and EE. Intended as the basis of the OSF analysis-plan entry. Nothing here has been seen by any rater.*

## 1. What round 1 is

Fifty claims from reports not used in development, rated by four newly recruited raters (NR1 to NR4) who took no part in rubric or prompt development, in two phases: a holistic tier judgement first, with no knowledge of SMTEC, then SMTEC dimension scores on the same 50 claims. Fully crossed: every rater rates every claim in both phases. This is the first part of the held-out validation promised in manuscript §3.4.1 and §6.3 and in the response to R3.3 and R3.4.

## 2. Sampling frame and draw

**Pool.** The six corpus reports not used in the 63-claim development sample: ADVANC (Telecommunications), CPN (Real Estate), IVL and SCC (Construction Materials), PTT and PTTGC (Energy). Scored claims with a mapped SDG target and one of the six regular claim types (commitment, achievement, metric, policy, alignment, target): 822 claims after removing the 20 pilot claims already drawn on 27 Sep (`pilot20_selection.json`). The provisional 89-claim frame of 12 Sep is superseded by this draw; its claims were eligible.

**Design.** Probability sample stratified on report and claim type only. Nothing produced by the framework (dimension scores, tier, flags) entered the draw, as stated in the response to R3.4. Allocation per report was fixed in advance to spread the 50 across reports (ADVANC 9, CPN 7, IVL 9, PTT 8, PTTGC 9, SCC 8); within each report the allocation across claim types is proportional to the report's own claim-type mix (largest-remainder rounding); within each report × type cell the claims were drawn at random. Seed 20261012 (Python `random.Random`, candidates sorted by uid before shuffling, so the draw is reproducible). Stratum weights N_h / n_h are stored in `round1_50_selection.json` and the key file, so corpus-level estimates can be reweighted.

**Result.** 50 claims: commitment 25, achievement 10, metric 6, policy 6, alignment 3, target 0 (only 4 target claims exist in the pool; the challenge set will cover them). Sectors: Construction Materials 17, Energy 17, Telecommunications 9, Real Estate 7. Every claim has at least one cross-section passage; 11 carry the absence-of-evidence retrieval flag. By the framework's own V7 tier, which was *not* used in the draw and is recorded only in the key file, the sample is 39 partially substantiated, 8 substantiated, 3 unsubstantiated. That skew is the population's; it limits what the round can say about agreement on the two outer tiers and attenuates the holistic test. The challenge set (stratified on claim type, reported separately, as promised) is the planned remedy, not a re-draw.

**Not to do.** No re-draw after seeing any score. If a claim proves unusable (fragment, duplicate), replace it with the next random candidate in the same report × type cell under the same seed and log the replacement here.

## 3. Evidence packs

Built with the production V7 chunk-aware retrieval (`retrieve_chunk_aware_refs`, embedding cache `{stem}_corpus_v7`), identical to the pilot: up to two same-section passages (S1, S2) and three cross-section passages (X1 to X3), each tagged with section and page; empty slots show "(no passage retrieved)". 236 passages in total. ADE anchor tags and control characters stripped for display; text otherwise verbatim.

## 4. Procedure

**Phase 1, holistic (file `Round1-Phase1-HOLISTIC-form.xlsx`, one version, DNA tags per rater).** Handbook: Scorer-Handbook-Holistics-10OCT26. Raters have not been told SMTEC exists. Form layout: one claim per page with Passage 1 to 5 (S1, S2, X1, X2, X3 in that order, unlabelled) and, at the foot, `your_judgement` (three levels, D11 wording) and `what_made_you_decide`; a criteria block in the READ ME (handbook 4.2); a closing-notes page; plus a "Judgement" table sheet for typed entry or transcription. Same row order for all raters (random, seed 20261012). Files are collected before anything about phase 2 is said.

**Between phases.** A gap of at least a few days. A single calibration session on four or five practice claims drawn from the pilot-20 set, never from the 50, in which the SMTEC handbook is explained. The session is logged (date, claims used, questions raised, any handbook clarification issued to all raters in writing).

**Phase 2, SMTEC (file `Round1-Phase2-SMTEC-form.xlsx`, one version).** Handbook: Scorer-Handbook-SMTEC-10OCT26. Form layout: one claim per page with its evidence pack and the score boxes at the foot (S, M, T, E, C, contradiction flag pre-set FALSE, passage id, polarity, comment), plus a "Scoring" table sheet for typed entry or transcription. One shuffled row order (seed 20261013), different from phase 1, the same for all raters (DNA decision 12 Oct: one version, tagged per rater at distribution); raters match by `claim_id` (R01 to R50). No access to their phase-1 file.

**Expert 2 (R2).** Not part of the naive series. If he rates, his holistic ratings are reported as an informed series, and his SMTEC scores serve as the bridge to the V3 development-sample scores.

## 5. Analysis plan (to register)

Per dimension and for the composite: Krippendorff's α (ordinal) across NR1 to NR4 with bootstrap CI; human–framework agreement per rater and against the rater median; tier agreement and adjacent agreement. Holistic test: per rater, agreement between the phase-1 tier and the tier implied by her own phase-2 SMTEC composite (weighted κ), and between the phase-1 tier and the framework tier; the comparison that matters for the cut-points is whether the SMTEC-implied tier tracks the holistic tier better at 1.0/2.0 than at neighbouring cut-points. All figures reported unweighted and, for corpus-level statements, reweighted by stratum. Round 1 is powered for calibration and a first validity signal, not for a definitive α: expect intervals of roughly ±0.15.

## 6. Files

`sdg-credibility-framework/data/outputs/revision/round1_50_selection.json` (draw, strata, weights, packs, V7 scores); `scorer/Round1-50-KEY-do-not-send.csv` (claim_id → uid, strata, weights, V7, row orders; DNA/EE only); the two form workbooks above (per-rater variants retired to `_superseded/round1-per-rater/`).

## 7. Addendum, 20 Oct 2026 (before any Phase 2 material reached raters)

*Written while Phase 1 (holistic) was in progress. No rater had seen the SMTEC handbook or the Phase 2 form. Decided by DNA after round-2 reviews (R1 minor, R3 major, 20 Oct).*

**Handbook.** Phase 2 uses `Scorer-Handbook-SMTEC-20OCT26` (replaces 10OCT26-fixed). Changes: (a) Evidence: the two examples that contradicted the ladder were removed ("aligned with GRI 305" at E=2; "ISO 14001 certified" at E=3); anchors otherwise unchanged. 21 Oct: the E=2 anchor now reads "conformity with a standard *stating the scope or location of the data*", and note 1 defines both terms with examples (bare standard name = 1; standard plus scope of the data, e.g. GRI 305-1 / all Thai plants / 2567, or plus where the figure sits in the report, e.g. page, table or GRI content index = 2). This states the existing rule more clearly; it does not change it. (b) Corroboration: raters no longer score C. They label every passage (S1, S2, X1–X3) as match / restatement / related / unrelated / contradicts; `none` is pre-filled for empty slots. C = number of distinct sections among X1–X3 with a passage labelled `match` (0–3). Restatement and related topics are recorded but not counted; contradiction is recorded per passage and never folded into C; a claim with no cross-section passage is C = 0 and flagged "nothing to check". (c) The separate contradiction flag and passage id were removed (a `contradicts` label records the same thing per passage). (d) §9 no longer states the tier cut-points, so Phase 2 scores cannot be steered toward a Phase 1 judgement. (e) Typos fixed (ขอบเขตที่ที่, ท่านที่ว่า, ล็อค, green washing). A marked copy against 10OCT26-fixed, with a change summary, is `scorer/Scorer-Handbook-SMTEC-20OCT26-changes-marked.docx` (for DNA/EE; not for raters).

**Challenge set.** 14 claims drawn purposively by claim wording, not by framework score (`scorer/build_challenge_set.py`, seed 20261020; `round1_challenge_selection.json`): all 4 target claims in the pool; 4 assurance/verification, 3 certification, 3 reporting-standard claims (regexes in the script; priority target > assurance > certification > standard). Pool: the six held-out reports, excluding the 50 and the pilot 20 (772 claims). Evidence packs rebuilt with the production V7 chunk-aware retrieval from the existing embedding cache; the procedure reproduces a stored Round 1 pack exactly. Challenge claims are R51–R64, mixed into the Phase 2 order at random positions (same seed); the 50 keep their 12 Oct relative order and display text. They are scored in Phase 2 only (no holistic judgement) and are reported separately from the representative 50.

**Form and key.** `Round1-Phase2-SMTEC-form-v2.xlsx` (+ `-large` print version, PDFs in `print-pdf/`), built by `build_phase2_form_v2.py`; key `Round1-64-KEY-do-not-send.csv` (adds `set`, `challenge_category`, `empty_slots`; phase2_row updated). The 12 Oct Phase 2 files are in `_superseded/phase2-pre-20Oct/`.

**Analysis plan changes.** C is analysed as derived from labels (human) and from the framework's own passage labels under the frozen V4 prompt, using the same counting code. Passage labels also give the retrieval-relevance audit (R3.4): share of retrieved passages labelled match / restatement / related / unrelated / contradicts, per slot and per report. Challenge-set agreement is reported separately and is not pooled with the representative 50. The framework instrument compared with these ratings must be the V4 prompt written from this handbook and frozen before any Phase 2 workbook is returned.

**Raters and timeline (21 Oct).** Round 1 has five raters, not four: two practitioners from Big Four firms and three academics (DNA confirmed 21 Oct that none took part in developing the rubric, the prompt or the handbooks). Read "NR1 to NR4" in §1, §4 and §5 as NR1 to NR5; the forms and the key are rater-agnostic and unchanged. Analysis (§5): α across NR1–NR5; the Big Four pair and the academic trio may be reported as a descriptive split, but no inference rests on n = 2. Raters agreed to return ratings in two to three weeks. Extension requested from the editor on 21 Oct: 30 days, to 29 Nov 2026.
