# Software and model versions

## Version 4 runs (held-out claims 30 Oct 2026; corpus 10 Nov 2026)
- Language model: OpenAI alias `gpt-4o`; served snapshot `gpt-4o-2024-08-06` (system fingerprint fp_936db6157f) recorded at the start and end of the corpus run on 10 Nov 2026; not recorded for the 30 Oct run. Temperature 0.3; three runs per claim; JSON-object response mode.
- Embeddings: OpenAI `text-embedding-3-small` (cached from the April–May 2026 runs; no new embeddings in November).
- Python 3.10.12; openai 3.41.0; pandas 2.3.3; numpy 2.2.6; scipy 1.15.3; statsmodels 0.15.0; openpyxl 3.1.5; matplotlib 3.10.9; krippendorff (PyPI, current release on 10 Nov 2026).
- Frozen files and SHA-256 hashes: scorer/FREEZE-V4-30Oct2026.md.

## Extraction and mapping (April 2026)
- Document parsing: LandingAI Agentic Document Extraction, model DPT-2, package `landingai-ade >= 0.2.0`, native semantic chunking (no fixed chunk size or overlap). The exact package version used in April 2026 was not recorded.
- Claim extraction and SDG mapping: OpenAI `gpt-4o` alias, default settings, prompts in SI §S13.1–S13.2; serving snapshot not recorded.
- requirements.txt lists minimum versions only (openai>=1.30.0, pandas>=2.0.0, ...); a lock file was not kept for the April runs.

## Analysis
- Bootstrap: 2,000 replicates, claims resampled within report, seed 20261110.
- Sampling seeds: 20261012 (representative 50), 20261020 (challenge set).
