# V4 framework instrument — freeze record (FROZEN 30 Oct 2026)

**Frozen by DNA on 30 Oct 2026 (02:14 UTC), unchanged from the 23 Oct draft. All hashes below re-verified at freeze; they are identical to GitHub commit c39c547 (23 Oct 2026 15:08 UTC). Any later change to these files is a new version (V4.1), never an edit of V4.**

*History: drafted 23 Oct 2026. 28 Oct: the first returned workbooks (one rater; Phase 1 submitted 20 Oct, Phase 2 submitted 27 Oct) arrived before the freeze; DNA decided to keep them UNOPENED until EE's pilot check and the freeze are done (see scorer/RECEIVED-Round1.md). The code files are byte-identical to the 23 Oct GitHub commit c39c547 (verified 28 Oct). Becomes FREEZE-V4-<date>.md when DNA freezes it. Must be frozen before ANY Round 1 Phase 2 workbook is returned (reviewer R2 point 1: frozen rubric, prompt, retrieval configuration, aggregation rule and thresholds).*

## What is frozen
| Component | File | SHA-256 (23 Oct, re-verified at freeze 30 Oct) |
|---|---|---|
| V4 scoring prompt + system message | `sdg-credibility-framework/prompts/credibility_scoring_v4.py` (PROMPT_VERSION_V4 = V4-2026-10-23) | file 61395e0f6b9cd92d55f7dc940a70ae2d434d33884f8505a43c1c01cde1834917 · prompt text 87533a24ad7c3c535fd052eab20b34af4d202eea8ba2b9536ad7bf6e94066f90 |
| Scorer, aggregation, C rule, composites, tiers | `sdg-credibility-framework/score_v4.py` | c49c01ceca2b592dea97205e5633c1cfbae34c6cd87fd87fad5531ece2b32a74 |
| Retrieval (V7 chunk-aware, unchanged) | `sdg-credibility-framework/utils/retrieval.py` | 673b8c600fa43521d4192c36ca910fb8661976ab0a16f15ab1505b9bc4ca5f7c |
| Model, temperature, runs, thresholds | `sdg-credibility-framework/config/settings.py` (gpt-4o, T = 0.3, 3 runs) | 42ffe0a0c2a2045b30de29e475462abca281451f06ff3c8b0498dce65e5190ed |
| Rubric source | `scorer/Scorer-Handbook-SMTEC-21OCT26-changes-marked-DNA-EE.docx` (as sent; see SENT-Round1-Phase2-21Oct.md) | e2f6758e… (MD5) |

## Fixed rules (implemented in score_v4.py)
- Model scores S, M, T, E (0–3) and labels each passage Extend / Redundant / Related / Unrelated / Contradicts; empty slots = None (set in code).
- 3 runs per claim; S, M, T, E = median; passage label = label given by ≥ 2 of 3 runs, otherwise Related (non-counting).
- C = number of distinct sections among X1–X3 labelled Extend (0–3); S1–S2 never count; Contradicts recorded, never deducted; all X empty → C = 0 and nothing_to_check = True.
- SMTEC = mean(S, M, T, E, C); SMTE = mean(S, M, T, E); equal weights.
- Tiers: unsubstantiated < 1.0 ≤ partially substantiated < 2.0 ≤ substantiated.
- Headline composite (pre-registered): SMTEC if the raters' Krippendorff ordinal α for C ≥ 0.667, else SMTE; both always reported.
- Evidence rule exactly as the handbook sent: standard without number = 1; with number / scope / period / data location = 2; unnamed independent third party = 2; named assurer or certification standard tied to this data = 3.
- Pre-registered sensitivity (framework side only): E rescored with a numbered standard counted as 1 unless scope or location is also given; reported as sensitivity, never as the headline.

## Inputs
- Round 1 comparison: `python score_v4.py --form ../scorer/Round1-Phase2-SMTEC-form-v2-EN.xlsx` — the model reads the passages from the EN form the raters received (Thai stripped; corrected 28 Oct), with the large-print display tidy (figure markers as [Figure: …], markdown marks removed); tables as HTML (raters saw the same cells as a grid). Passages are given in full (V7 truncated at 600 characters).
- Corpus: `python score_v4.py --corpus` → `data/outputs/main/full_v4/` (production retrieval; same cleaning; may additionally show "[Figure: visual content]" markers that the 12 Oct form builder dropped — content otherwise identical; checked on 18 of 19 Round 1 claims from SCC and CPN).

## Checks before freezing
1. [~] Translation fidelity. EE did not run a separate anchor-by-anchor check of the prompt. Instead, both handbooks were translated into English (scorer/handbooks-EN/, 30 Oct) and the SMTEC translation was compared with the prompt; no difference that would change a score was found. The English translation has not yet been reviewed by a Thai speaker.
2. [x] Dry run on the 20 pilot claims, 30 Oct 2026 (`--form ../scorer/Pilot20-SMTEC-form-v4-EN.xlsx` → data/outputs/revision/v4_pilot20.json, SHA-256 5cade08d…c1ab4). 20/20 claims parsed, no format or translation errors. Compared with EE's pilot (updated return 30 Oct): wκ S 0.28, M 0.71, T 0.76, E 0.44; label agreement 26/93 (EE Extend 77, V4 Extend 16); V4 marked 7 passages Contradicts, several not contradictions under the handbook; tier agreement 11/20 (SMTE). Details: revision/pilot-calibration/Pilot20-EE-vs-V4.md.
   **Decision (DNA, 30 Oct): freeze V4 unchanged.** The gaps are interpretive, not format or translation errors; changing the prompt towards one pilot rater (development Expert 1 and handbook co-author) would move V4 away from the written definitions the Round 1 raters used. The gaps are reported as calibration findings; Round 1 rater labels will show whether V4's strict reading of Extend and its Contradicts flags differ from independent raters.
3. [x] Mock run passes on both forms (23 Oct: 20 and 60 claims parse; C and composites computed).
4. [x] Final hashes recorded (unchanged), file renamed FREEZE-V4-30Oct2026.md, FILE-MAP.md updated.

## After the freeze
- Push release/ so the freeze commit is public BEFORE any Round 1 workbook is opened.
- Then: score the 60 Round 1 claims with V4 (`--form ../scorer/Round1-Phase2-SMTEC-form-v2-EN.xlsx`) and open the returned workbooks (scorer/RECEIVED-Round1.md).

## Use of Round 1 results (DNA, 30 Oct 2026)
Round 1 is the held-out validation set. Its results are NEVER used to calibrate, tune or edit V4 (prompt, retrieval, aggregation, C rule, thresholds), whatever they show.
- V4 is reported as frozen. Weak areas found in Round 1 (e.g. S, E, passage labels, C) are reported as findings; the pre-registered headline rule (SMTEC if raters' α for C ≥ 0.667, else SMTE) applies unchanged.
- Round 1 results may inform the Discussion, Limitations and future work.
- Any later improvement is a new version (V4.1 or later), labelled as developed after seeing Round 1. V4 remains the primary result. A new version is validated only on new held-out claims (not the 60 Round 1 claims), with its own freeze record before that validation.
