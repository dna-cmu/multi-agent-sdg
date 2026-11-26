# SDG Credibility Assessment Framework

An agentic AI framework for assessing the credibility of corporate SDG alignment claims in sustainability reports.

## Quick Start

### 1. Install Python dependencies
```bash
pip install landingai-ade openai anthropic langchain langgraph pandas python-dotenv
```

### 2. Set up API keys
```bash
cp .env.example .env
# Edit .env with your actual API keys
```

### 3. Add PDF reports
Place your sustainability report PDFs in the `data/reports/` folder.

### 4. Run Phase 1 (ingestion)
```bash
python run_phase1.py --report data/reports/your_report.pdf
```

### 5. Run full pipeline
```bash
python main.py --reports-dir data/reports/ --output-dir data/outputs/
```

## Project Structure
```
sdg-credibility-framework/
├── config/
│   └── settings.py          # Configuration and API key loading
├── agents/
│   ├── planner.py            # Phase 1: Report ingestion & structuring
│   ├── mapper.py             # Phase 2: SDG target mapping
│   ├── scorer.py             # Phase 3: Credibility scoring
│   └── comparator.py         # Phase 4: Cross-report analysis
├── prompts/
│   ├── claim_extraction.py   # Prompts for claim detection
│   ├── sdg_mapping.py        # Prompts for SDG target mapping
│   └── credibility_scoring.py # Prompts for 5-dimension scoring
├── utils/
│   └── sdg_targets.py        # Official 169 SDG target definitions
├── data/
│   ├── reports/              # Input: PDF sustainability reports
│   └── outputs/              # Output: JSON results per report
├── run_phase1.py             # Run Phase 1 only (for testing)
├── main.py                   # Run full pipeline
├── .env.example              # API key template
└── requirements.txt
```

## Pipeline Phases

- **Phase 1 (Planner):** PDF → structured text → extracted claims with source locations
- **Phase 2 (Mapper):** Claims → mapped to 169 SDG targets with confidence scores
- **Phase 3 (Scorer):** Mapped claims → 5-dimension credibility scores (0-3)
- **Phase 4 (Comparator):** Cross-report patterns, frequency-credibility matrix, feedback loops

## Data availability

This repository contains the framework code only. The corpus of sustainability reports
and the expert validation materials used in the accompanying paper are **not** distributed
with the code. Place your own PDF reports in `data/reports/` to run the pipeline.
The `data/` directory is gitignored; only `DATA_DICTIONARY.md` and `manifest_example.csv`
are tracked as documentation of the expected structure.

## Citation

If you use this framework in academic work, please cite:

```
Naparat, D. (2026). SDG Credibility Assessment Framework (Version 0.1.0) [Software].
https://github.com/<username>/sdg-credibility-framework
```

A peer-reviewed paper describing the SMTEC rubric is in preparation; this section will
be updated with the full citation on acceptance.

## Licence

Released under the [MIT Licence](LICENSE). Copyright (c) 2026 Damrongsak Naparat.

