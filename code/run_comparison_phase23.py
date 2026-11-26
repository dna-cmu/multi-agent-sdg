"""
Run Phases 2-3 on extractor comparison Phase 1 outputs.

Loads Phase 1 JSON directly (no file copying needed), runs SDG mapping
and credibility scoring, and saves results to the comparison directory.

Usage:
    python run_comparison_phase23.py                    # Run all
    python run_comparison_phase23.py --extractor pymupdf  # One extractor only
    python run_comparison_phase23.py --report BCP        # One report only
"""

import argparse
import asyncio
import json
from pathlib import Path

from config.settings import validate_keys, OUTPUTS_DIR
from agents.mapper import MapperAgent
from agents.scorer import ScorerAgent

COMP_DIR = OUTPUTS_DIR / "extractor_comparison"

REPORTS = [
    ("BCP-2024-SR-EN", "Bangchak Corporation", "Energy", "2024"),
    ("AOT-2024-OR+SR-EN", "Airports of Thailand", "Transportation", "2024"),
    ("MINT-2024-SR-EN", "Minor International", "Real Estate", "2024"),
    ("SCB-2024-SR-EN", "Siam Commercial Bank", "Banking & Finance", "2024"),
    ("CPN-2024-OR+SR-EN", "Central Pattana", "Real Estate", "2024"),
]

EXTRACTORS = ["pymupdf", "pdfplumber"]


def run_phases23(phase1_path: Path, output_path: Path, concurrency: int = 5):
    """Run Phases 2-3 on a single Phase 1 JSON file."""

    # Load Phase 1 result
    with open(phase1_path, "r", encoding="utf-8") as f:
        result = json.load(f)

    company = result.get("metadata", {}).get("company", "Unknown")
    n_claims = len(result.get("claims", []))
    print(f"  Loaded: {phase1_path.name}")
    print(f"  Company: {company} | Claims: {n_claims}")

    # Phase 2: SDG Mapping
    mapper = MapperAgent()
    if concurrency > 0:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result["claims"] = loop.run_until_complete(
                mapper.process_all_claims_async(result["claims"], concurrency)
            )
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
            loop.close()
    else:
        result["claims"] = mapper.process_all_claims(result["claims"])

    # Phase 3: Credibility Scoring
    scorer = ScorerAgent()
    if concurrency > 0:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result["claims"] = loop.run_until_complete(
                scorer.process_all_claims_async(result["claims"], concurrency)
            )
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
            loop.close()
    else:
        result["claims"] = scorer.process_all_claims(result["claims"])

    # Save
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"  Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Run Phases 2-3 on comparison Phase 1 outputs")
    parser.add_argument("--extractor", choices=["pymupdf", "pdfplumber"],
                        help="Run only this extractor (default: both)")
    parser.add_argument("--report", help="Run only reports matching this substring (e.g., 'BCP')")
    parser.add_argument("--concurrency", type=int, default=5,
                        help="Parallel API calls (default: 5)")
    args = parser.parse_args()

    if not validate_keys():
        print("Please set up your .env file first.")
        return

    extractors = [args.extractor] if args.extractor else EXTRACTORS

    for extractor in extractors:
        print(f"\n{'='*60}")
        print(f"Extractor: {extractor}")
        print(f"{'='*60}")

        for stem, company, sector, year in REPORTS:
            if args.report and args.report.upper() not in stem.upper():
                continue

            phase1_file = COMP_DIR / f"{extractor}_{stem}_phase1.json"
            full_file = COMP_DIR / f"{extractor}_{stem}_full.json"

            if full_file.exists():
                print(f"\n  SKIP: {full_file.name} already exists")
                continue

            if not phase1_file.exists():
                print(f"\n  WARNING: {phase1_file.name} not found. Run phase1 first.")
                continue

            print(f"\n  Processing: {stem} ({extractor})")

            try:
                run_phases23(phase1_file, full_file, args.concurrency)
            except Exception as e:
                print(f"  ERROR: {e}")
                continue

    print(f"\n{'='*60}")
    print("COMPLETE")
    print(f"{'='*60}")
    print(f"Results in: {COMP_DIR}")


if __name__ == "__main__":
    main()
