# Data Dictionary: SDG Credibility Assessment Framework

**Version:** 1.0  
**Date:** 16 April 2026  
**Authors:** Damrongsak Naparat  
**Corpus:** 30 sustainability reports from SET-listed companies (FY2024)

---

## Overview

This document describes the data structure produced by the SDG Credibility Assessment Framework. The framework processes corporate sustainability reports through four phases, producing structured JSON outputs at each stage. This dictionary covers all fields in the output files and is intended to support reproducibility, future research, and third-party analysis.

---

## File Naming Conventions

| Pattern | Description | Example |
|---------|-------------|---------|
| `{TICKER}-{YEAR}-SR-EN_phase1.json` | Phase 1 output (extraction only) | `BCP-2024-SR-EN_phase1.json` |
| `{TICKER}-{YEAR}-SR-EN_full.json` | Complete output (Phases 1–3) | `BCP-2024-SR-EN_full.json` |
| `manifest_2024.csv` | Input manifest listing all reports | — |

Report type abbreviations: SR = Sustainability Report, OR = One Report (Annual + Sustainability), IR = Integrated Report.

---

## Top-Level Structure

Each JSON output file contains three top-level objects:

```
{
  "metadata": { ... },     // Report-level information
  "sections": [ ... ],     // Identified document sections
  "claims": [ ... ]        // Extracted sustainability claims
}
```

---

## 1. Metadata Object

Report-level descriptive information populated during Phase 1.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `company` | string | Full company name | `"Bangchak Corporation"` |
| `sector` | string | GICS sector classification | `"Energy"` |
| `report_year` | string | Fiscal year of the report | `"2024"` |
| `filename` | string | Source PDF filename | `"BCP-2024-SR-EN.pdf"` |
| `extractor` | string | PDF extraction engine used | `"ade"` (Adobe Document Extract) |
| `total_pages` | integer | Page count as reported by extractor | `1` (see note below) |
| `total_chunks` | integer | Number of text chunks extracted from PDF | `1762` |
| `sections_found` | integer | Number of document sections identified | `32` |
| `total_claims` | integer | Number of sustainability claims extracted | `308` |
| `self_declared_sdgs` | array | SDGs the company claims to address (from manifest) | `["1","2","8","12","13"]` |

**Note on `total_pages`:** When the ADE extractor cannot resolve reliable page numbers (common in complex PDFs), this field defaults to 1 and the framework falls back to chunk-index positioning. The `page` field in individual claims then reflects chunk index rather than PDF page number.

---

## 2. Sections Array

Document structure identified during Phase 1. Each element represents a report section.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `section_title` | string | Section heading as identified in the report | `"Climate Strategy and Energy Management"` |
| `level` | integer | Heading hierarchy level (1 = top-level) | `1` |
| `start_chunk` | integer | First chunk index belonging to this section | `184` |
| `end_chunk` | integer | Last chunk index belonging to this section | `304` |
| `start_page` | integer | Starting page/chunk position | `184` |
| `end_page` | integer | Ending page/chunk position | `304` |

---

## 3. Claims Array

The core analytical unit. Each element represents one sustainability claim extracted from the report. Phase 1 populates the identification fields; Phases 2–3 populate the assessment fields.

### 3.1 Claim Identification (Phase 1)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `claim_id` | string | Unique identifier within the report | `"CLM-0001"` |
| `claim_text` | string | Verbatim text of the extracted claim | `"Total GHG emission (scope 1&2) 0.98 M tCO₂ eq"` |
| `claim_type` | string | Classification of claim nature (see below) | `"metric"` |
| `page` | integer | Page or chunk index where claim was found | `150` |
| `section` | string | Report section containing the claim | `"Bangchak Value Creation"` |
| `company` | string | Company name (denormalised for convenience) | `"Bangchak Corporation"` |
| `sector` | string | Sector (denormalised) | `"Energy"` |
| `report_year` | string | Report year (denormalised) | `"2024"` |
| `source_file` | string | Source PDF filename (denormalised) | `"BCP-2024-SR-EN.pdf"` |

#### Claim Type Values

| Value | Definition | Example |
|-------|-----------|---------|
| `metric` | A quantitative data point or KPI | `"Total water discharge 0.98 million cubic meters"` |
| `target` | A specific, measurable future goal | `"Reduce GHG by 20% by 2030"` |
| `commitment` | A stated intention or pledge without full specificity | `"We are committed to achieving net zero"` |
| `achievement` | A reported accomplishment or milestone | `"Received Thailand Sustainability Investment award for 5th consecutive year"` |
| `policy` | A reference to a policy, framework, or governance mechanism | `"The Board approved the Climate Change Policy in 2023"` |
| `alignment` | A statement linking activities to external frameworks (SDGs, GRI, TCFD) | `"Our operations contribute to SDG 7 and SDG 13"` |

### 3.2 SDG Target Mapping (Phase 2)

| Field | Type | Description |
|-------|------|-------------|
| `sdg_mappings` | array | List of SDG target mappings identified for this claim |

Each mapping object contains:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `goal` | integer | SDG goal number (1–17) | `2` |
| `target` | string | Specific SDG target code | `"2.1"` |
| `confidence` | float | Model confidence in the mapping (0.0–1.0) | `0.9` |
| `rationale` | string | Explanation of why this target was assigned | `"The claim emphasises providing food security..."` |

### 3.3 Credibility Assessment (Phase 3)

| Field | Type | Description |
|-------|------|-------------|
| `credibility_scores` | object | Scores across five SMTEC dimensions |
| `composite_score` | float | Weighted average credibility score (0.0–3.0) |
| `credibility_tier` | string | Overall credibility classification |
| `overall_assessment` | string | Narrative summary of the credibility evaluation |

#### Credibility Dimensions (SMTEC)

Each dimension is scored on a 0–3 ordinal scale. The `credibility_scores` object contains five keys, one per dimension:

| Dimension | Key | What It Measures |
|-----------|-----|-----------------|
| Specificity | `specificity` | How concrete and detailed the claim is |
| Measurability | `measurability` | Whether quantitative metrics or KPIs are provided |
| Temporality | `temporality` | Whether timeframes, deadlines, or baselines are stated |
| Evidence | `evidence` | Whether supporting evidence, verification, or third-party assurance is cited |
| Consistency | `consistency` | Whether the claim aligns with other statements in the same report |

Each dimension object contains:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `score` | integer | Final score (0–3) | `1` |
| `rationale` | string | Explanation for the assigned score | `"The claim is vague and references a generic theme..."` |
| `all_run_scores` | array | Scores from each independent scoring run (typically 3) | `[1, 1, 1]` |
| `agreement` | boolean | Whether all runs produced the same score | `true` |

#### Scoring Scale (per dimension)

| Score | Label | Meaning |
|-------|-------|---------|
| 0 | Absent | Dimension is entirely missing from the claim |
| 1 | Weak | Dimension is present but vague or insufficient |
| 2 | Moderate | Dimension is present with reasonable detail |
| 3 | Strong | Dimension is fully addressed with specific, verifiable detail |

#### Composite Score

The `composite_score` is a weighted average of the five dimension scores, normalised to a 0–3 scale. The default weighting is equal (each dimension contributes 20%).

#### Credibility Tier Values

| Tier | Composite Score Range | Interpretation |
|------|----------------------|----------------|
| `symbolic` | 0.0–1.0 | Claim lacks substance; likely rhetorical or aspirational |
| `partially_substantive` | 1.01–2.0 | Claim has some credible elements but significant gaps |
| `substantive` | 2.01–3.0 | Claim is well-supported with specific, measurable, evidenced content |

A `null` tier indicates the claim could not be scored (e.g., insufficient text for assessment).

---

## 4. Corpus Statistics (2024 Dataset)

| Metric | Value |
|--------|-------|
| Companies | 30 |
| Sectors represented | 10 (Energy, Banking & Finance, Food & Agribusiness, Retail, Real Estate, Transportation, Healthcare, Technology, Telecommunications, Construction Materials) |
| Total claims extracted (Phase 1) | 6,936 |
| Mean claims per report | 231 |
| Min claims | 86 (Central Pattana) |
| Max claims | 596 (WHA Corporation) |
| Report types | SR (19), OR+SR (7), IR (3), OR (1) |

---

## 5. Known Limitations

1. **Page number reliability:** Combined One Reports (OR+SR) with complex layouts may produce unreliable page numbers, defaulting to chunk-index positioning.

2. **Lower extraction yield in combined reports:** OR+SR and OR documents contain substantial non-sustainability content (financial statements, governance sections), resulting in lower claim-to-chunk ratios. Three reports (CPN, KBANK, PTT) are flagged as lower-yield. See `NOTES_lower_yield_reports.md`.

3. **Truncated claims:** Approximately 1–3% of claims may have incomplete sentence endings due to PDF chunking at natural phrase boundaries.

4. **Extractor dependency:** All 2024 reports were processed using the Adobe Document Extract (ADE) engine. Results may differ with alternative extractors (e.g., PyMuPDF).

---

## 6. Reuse Guidelines

This dataset may be reused for:

- Longitudinal analysis (by processing additional reporting years with the same pipeline)
- Cross-country comparisons (by applying the framework to reports from other markets)
- Sector-specific studies (the `sector` field enables filtering)
- NLP model training and benchmarking (claim texts with human-validated scores)
- Regulatory impact assessment (pre/post policy change comparisons)

When reusing, please cite:

> Naparat, D. (2026). Assessing the Credibility of Corporate SDG Claims: An Agentic AI Framework for Sustainability Report Analysis. *Discover Sustainability*.

---

## 7. File Inventory

| Directory | Contents |
|-----------|----------|
| `data/outputs/*_phase1.json` | Phase 1 outputs (30 files, read-only) |
| `data/outputs/*_full.json` | Complete pipeline outputs (Phases 1–3) |
| `data/backups/phase1_2024/` | Backup copy of all Phase 1 outputs with SHA-256 checksums |
| `data/manifest_2024.csv` | Master manifest of all 30 reports |
| `data/reports/2024/` | Source PDF files |
