# A multi-agent AI framework for assessing the substantiation of corporate SDG claims — code, instrument and data

Companion repository for the manuscript "A multi-agent AI framework for assessing the substantiation of corporate SDG claims in sustainability reports" by Damrongsak Naparat and Erboon Ekasingh (under revision at *Discover Sustainability*).

The framework extracts SDG-related claims from sustainability reports, maps each claim to the 169 SDG targets, and scores how far the report substantiates the claim on **S**pecificity, **M**easurability, **T**emporality and **E**vidence (0–3 each), with a count of **C**orroborating sections elsewhere in the report (SMTEC). It measures what a report discloses, not whether a claim is true or what the company achieved.

Read this first: the held-out evaluation in the paper does **not** validate the instrument (agreement among four trained raters was low), and the authors' audits show that the extraction step captures roughly a third of the claims in a report. The corpus scores are the framework's reading of the rubric, applied uniformly to the claims it extracted.

## Contents

| Folder | What it holds |
|---|---|
| `code/` | The pipeline (Planner → Mapper → Scorer; aggregation scripts), all scoring prompts (`code/prompts/`: V5, V6, V7 = paper Versions 1–3; V4 = the frozen instrument evaluated in the held-out study and used for the corpus results). `code/score_v4.py` applies V4; `code/run_corpus_v4_batched.py` is the corpus run. |
| `code/analysis/` | Scripts behind the corpus findings, figures and the stricter-Evidence sensitivity analysis. |
| `code/round1_analysis/` | Scripts for the held-out evaluation. They read the raters' original workbooks, which are not released; rater nicknames in the scripts are replaced by codes. The released long-form ratings (`data/ratings_round1/`) contain the same scores. |
| `code/audits/` | Scripts that built and scored the authors' audits. |
| `code/rater_forms/` | Scripts that built the rater forms. |
| `instrument/handbook/` | The rater handbook as sent (Thai) and its English version. |
| `instrument/forms/` | The blank Phase 1 and Phase 2 rating forms. |
| `instrument/protocol/` | Sampling and procedure, the record of what was sent and returned (with file hashes), the Version 4 freeze record, the pre-specified rules (firm–goal rules, stricter Evidence reading) and the corpus run record. |
| `data/scores_v4/` | Claim-level Version 4 scores for the 30 reports (the results in the paper). |
| `data/scores_v7/` | Claim-level scores under the earlier prompt (paper Version 3). |
| `data/claims_phase1/` | Claim registry and report sections from the extraction step. |
| `data/samples/` | Claim selections for the pilot, the 50 representative and 10 challenge held-out claims, and the answer keys. |
| `data/ratings_round1/` | Held-out evaluation: the four raters' ratings (codes A–D), the framework's scores for the same 60 claims, the claim key, and aggregate analysis outputs. |
| `data/revision/`, `data/validation/`, `data/experiments/` | Tables behind the analyses in the paper and its Supplementary Information. |
| `audits/` | The authors' audits of the upstream stages (SI §S16): scoring rules fixed in advance, forms, both authors' answers, answer keys, resolution files, results and the audit log. |
| `audits/extraction_rerun/`, `data/extraction_rerun/`, `code/extraction_rerun/` | Re-run of the extraction step on the full text of all 30 reports (SI §S19): plan fixed before the run, results, scripts, every raw extraction response of both passes, the re-extracted claims, and the mappings and scores of the sampled claims. |
| `data/manifest_2024.csv` | The 30 reports (company, sector, file name). |
| `VERSIONS.md` | Model snapshots, library versions and seeds. |

## Not included
- The sustainability reports (copyrighted; available from the companies' websites) and the full extracted report text and embedding caches derived from them. Claim texts and evidence passages in `data/` are short excerpts.
- API keys. Copy `code/.env.example` to `.env` and add your own keys to run the pipeline.
- Peer-review correspondence, the raters' original workbooks, their free-text comments, and anything that identifies a rater.

## Reproducing
```bash
cd code
pip install -r requirements.txt
cp .env.example .env    # add OPENAI_API_KEY (and the LandingAI key for document parsing)
python score_v4.py --form <rater form .xlsx> --out scores.json    # Version 4 on a rating form
python run_corpus_v4_batched.py                                    # corpus run (needs the reports and chunk files)
```
Extraction, mapping and scoring use commercial APIs, and the model was called through an alias (`gpt-4o`; snapshot recorded for the corpus run, see `VERSIONS.md`), so exact numeric replication is not guaranteed. The analysis scripts run on the released claim-level scores without any API.

## Known limitations of the pipeline (see the paper, §6.2)
- The extraction step reads the first 12,000 characters of each report section (`code/agents/planner.py`), so part of each report is not read.
- The location stored with each claim is an internal position number, not a PDF page; `data/revision/` holds a lookup to PDF pages.

## Use of AI tools
An AI assistant was used in this project to write analysis code, to transcribe one handwritten rating form (recorded in `instrument/protocol/RECEIVED-Round1.md`) and to score the authors' audit forms against the keys (recorded in `audits/AUDIT-LOG.md`).

## Maintenance
The files are copied from the authors' working project by `tools/sync_release.py`, which lists what is released and runs safety checks (no keys, no report PDFs, no rater identifiers).

## Citing
All releases are archived on Zenodo (all versions: https://doi.org/10.5281/zenodo.24550438). v1.0.0: https://doi.org/10.5281/zenodo.24550439. v1.1.0 adds the extraction re-run.

## Licence
Code: MIT (see `LICENSE`). Data and instrument: CC BY 4.0.
