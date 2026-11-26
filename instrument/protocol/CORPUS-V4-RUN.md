# V4 corpus run — log

Frozen V4 (FREEZE-V4-30Oct2026.md) applied to the 30-report corpus: `python3 score_v4.py --corpus` → `sdg-credibility-framework/data/outputs/main/full_v4/`. Firm–goal rules were pre-specified and pushed first (PRESPEC-firm-goal-rules-10Nov2026.md, commit 8d1fb9d).

## Model snapshot
The frozen setting is the alias `gpt-4o` (config/settings.py), temperature 0.3, 3 runs. The scorer does not record which dated snapshot serves a call, so a separate one-line API call records it (V4 files untouched).
- Before the run: 2026-11-10 04:07:25 UTC | requested gpt-4o | served: gpt-4o-2024-08-06 | system_fingerprint: fp_936db6157f | openai lib 3.41.0 | python 3.10.12
- Round 1 (30 Oct 2026) and the pilot used the same alias; the snapshot was not recorded then.

## Run
- Started: 2026-11-10 04:07 UTC, code hashes as in the freeze record (re-verified 10 Nov).
- Method: the shell used for the run stops every process after about 3 minutes, so `score_v4.py --corpus` could not run to completion in one go. The run used `revision/run_corpus_v4_batched.py`, which calls the same frozen functions (items_from_corpus, score_items) in time-boxed batches and writes the same per-report format. score_v4.py, the prompt, retrieval and settings were not modified (hashes re-verified after the run). API concurrency 12–40 (does not affect scores).
- Finished: 2026-11-10 04:57 UTC. 30 reports, 6,325 claims.
- After the run: 2026-11-10 04:57:09 UTC | requested gpt-4o | served: gpt-4o-2024-08-06 | system_fingerprint: fp_936db6157f | openai lib 3.41.0 | python 3.10.12  → same snapshot before and after.

## Completeness
- 6,320 claims scored with 3 valid runs; 6,319 on the first attempt, 1 after re-scoring.
- 5 claims incomplete after 3 attempts (kept as the frozen scorer returns them; to be reported as missing):
  BDMS-2024-SR-EN::CLM-0027, BEM-2024-SR-EN::CLM-0015, KTB-2024-SR-EN::CLM-0055, PTTEP-2024-OR+SR-EN::CLM-0021 ("all runs failed"); IVL-2024-SR-EN::CLM-0009 (2 valid runs only).
  Cause checked on BDMS CLM-0027: the model labelled a non-empty passage "None", which the frozen validator rejects (None is reserved for empty slots).
- Re-scoring rule in the driver: a claim with fewer than 3 valid runs is scored again in full, at most 3 attempts in total; the trigger is the number of valid runs, never the score. Each result carries `score_attempts`.

## Output
- `sdg-credibility-framework/data/outputs/main/full_v4/<report>_full_v4.json` (30 files). SHA-256 of the 30 files concatenated in sorted order: 5b5f92612a8bdb102eb5d5a0d41c08d663d898c0e1096fc1efd05e18df2979b0
- Run log: `revision/corpus_v4_run.log` is empty (the first direct attempt was stopped by the shell before any report finished; nothing was written).

## First descriptive figures (6,320 scored claims; not yet the paper's tables)
- Means: S 1.56, M 0.85, T 0.84, E 1.22, C 0.49.
- SMTE tiers: unsubstantiated 37.5 %, partially substantiated 53.1 %, substantiated 9.4 %.
- SMTEC tiers: unsubstantiated 45.3 %, partially substantiated 51.7 %, substantiated 3.0 %.
- Passage labels (non-empty slots): Related 53.0 %, Redundant 15.4 %, Extend 15.1 %, Unrelated 14.3 %, Contradicts 2.2 %.
- C: 0 for 3,556 claims, 1 for 2,423, 2 for 327, 3 for 14.
- 33.9 % of claims have at least one of S, M, T, E differing across the three runs.

## Why the five claims are incomplete (checked 10 Nov 2026, 3 diagnostic calls per claim)
Same cause in all five: one or more retrieved "passages" contain no content, only a page header, footer or heading (e.g. "Bangkok Expressway and Metro Public Company Limited / Sustainability Report 2024", "Krungthai Bank PCL", "Key Sustainability Recognitions and Awards in 2024"). The model labels such a passage "None". The frozen validator accepts "None" only for slots where retrieval returned nothing, so it rejects the whole run; when this happens in every run, the claim has no score.
- BDMS CLM-0027: S2 is the company name only. BEM CLM-0015: S1, S2, X3 are page headers. KTB CLM-0055: S1, S2 are page headers. PTTEP CLM-0021: X3 is a table label. IVL CLM-0009: X1–X3 are a repeated heading (one run of three labelled them validly).
- This is a retrieval-quality finding (header and heading chunks can be retrieved as passages), relevant to Reviewer 3 point 4. V4 is not changed; the five claims (0.08 % of 6,325) are reported as missing, with this explanation.

## Stricter-Evidence sensitivity run (10 Nov 2026)
Pre-specification pushed first (commit 8b8e104). Runner: `revision/run_e_strict_sensitivity.py` (frozen scorer functions; prompt variant swapped in memory only).
- Snapshot before: 2026-11-10 05:35:11 UTC | requested gpt-4o | served: gpt-4o-2024-08-06 | system_fingerprint: fp_936db6157f | openai lib 3.41.0 | python 3.10.12
- Snapshot after: 2026-11-10 05:43:19 UTC | requested gpt-4o | served: gpt-4o-2024-08-06 | system_fingerprint: fp_936db6157f | openai lib 3.41.0 | python 3.10.12
- 1,560 claims rescored (1,542 corpus claims with V4 E = 2, and 18 of the 60 Round 1 claims); all with 3 valid runs. Output: `data/outputs/revision/v4_E_strict_sensitivity.json`.
- Exploratory placebo (not pre-specified): 300 random E = 2 corpus claims re-scored with the unchanged V4 prompt (seed 20261110), `revision/run_e_placebo.py` → `v4_E_placebo_rerun.json`: 19 of 300 (6.3 %) fell to 1 by run-to-run variation.
- Results: `revision/findings-v4/E-strict-sensitivity.md`.

## Cost of the run (read from the OpenAI usage page, 16 Nov 2026)
- 10 Nov 2026, whole day (UTC): US$272.46, 82,232,622 tokens, 24,831 requests. This day holds the corpus run, the stricter-Evidence run, the repeat (placebo) run and diagnostics.
- 04:00 UTC hour (the corpus run, 04:07–04:57): 62,852,548 tokens, 19,234 requests = 76.4% of the day's tokens → about US$208 for the V4 corpus scoring (about US$33 per 1,000 claims). The page gives spend per day only, so the hourly cost is an estimate from the token share.
- For reference: May 2026 total US$119.93 (19,393 requests, 44.0M tokens; the Version 3 corpus run, reported earlier as about US$116). Account total 1 Jan–16 Nov 2026: US$647.06 (all uses of the account).
- Not available: LandingAI extraction cost; separate cost of extraction-stage LLM calls, mapping and embeddings (dates of those runs needed).
- Note: the account shows spend above its configured limits (organisation US$100, project US$50 for the month).

## Cost of the other stages (read from provider pages, 16 Nov 2026)
- LandingAI ADE: usage log shows Parse jobs (DPT-2) at 3 credits per page (e.g. 36 pages = 108 credits); invoices show US$0.01 per credit → US$0.03 per page → one parse of the 5,952-page corpus ≈ 17,856 credits ≈ US$179. The account's usage history starts in May 2026 (May 4,242 credits / 200 requests; June 7,403.6 credits / 145 requests, Playground jobs), so the corpus parse of 24–25 April 2026 (dates of data/outputs/main/chunks) is not itemised. Invoices: US$616.38 of credits bought 14–25 April 2026 (plus US$50 in Aug 2025); balance on 16 Nov 2026: 8,297.4 credits. Credits consumed to date ≈ 58,341 (≈ US$583), which includes development, extractor trials and repeated parses.
- OpenAI, April 2026: US$248.82, 65,865,935 tokens, 63,868 requests. File dates show extraction (phase1), mapping and Version 1 scoring (main/full), and the first embeddings were all made in April; chunk embeddings were added in May. So US$249 is an upper bound for extraction + mapping + embedding.
- OpenAI totals: April 248.82 + May 119.93 + November 272.46 = 641.21 of the 647.06 for 1 Jan–16 Nov 2026.
- Paper (§3.3.4): one end-to-end pass ≤ about US$640 (179 + 249 + 208), about US$21 per report.
