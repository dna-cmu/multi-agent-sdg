"""
Run Phase 1 (Report Ingestion) on a single PDF report.
Use this to test the ingestion pipeline before running the full framework.

Usage:
    python run_phase1.py --report data/reports/company_report.pdf --company "PTT PCL" --sector "Energy" --year 2023
"""

import argparse
import json
from config.settings import validate_keys
from agents.planner import PlannerAgent


def main():
    parser = argparse.ArgumentParser(description="Run Phase 1: Report Ingestion")
    parser.add_argument("--report", required=True, help="Path to PDF sustainability report")
    parser.add_argument("--company", default="Unknown", help="Company name")
    parser.add_argument("--sector", default="Unknown", help="Industry sector")
    parser.add_argument("--year", default="Unknown", help="Reporting year")
    parser.add_argument("--extractor", default="pymupdf", choices=["pymupdf", "ade", "pdfplumber"],
                        help="PDF extractor: pymupdf (local), pdfplumber (pdfminer-based, local), or ade (LandingAI API)")
    args = parser.parse_args()

    # Check API keys
    if not validate_keys():
        print("\nPlease set up your .env file first. See README.md for instructions.")
        return

    # Run Phase 1
    agent = PlannerAgent(extractor=args.extractor)
    result = agent.process_report(
        pdf_path=args.report,
        company=args.company,
        sector=args.sector,
        report_year=args.year,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("PHASE 1 SUMMARY")
    print("=" * 60)
    print(f"Company:    {result['metadata']['company']}")
    print(f"Pages:      {result['metadata']['total_pages']}")
    print(f"Sections:   {result['metadata']['sections_found']}")
    print(f"Claims:     {result['metadata']['total_claims']}")
    print()

    # Show first 5 claims as a preview
    print("Sample claims (first 5):")
    print("-" * 40)
    for claim in result["claims"][:5]:
        text = claim["claim_text"][:120] + "..." if len(claim["claim_text"]) > 120 else claim["claim_text"]
        print(f"  [{claim['claim_id']}] ({claim['claim_type']}) p.{claim['page']}")
        print(f"    {text}")
        print()


if __name__ == "__main__":
    main()
