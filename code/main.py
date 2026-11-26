"""
SDG Credibility Assessment Framework — Main Pipeline

Runs all 4 phases sequentially:
  Phase 1: Report Ingestion (Planner Agent)
  Phase 2: SDG Target Mapping (Mapper Agent)
  Phase 3: Credibility Scoring (Scorer Agent)
  Phase 4: Cross-Report Comparative Analysis (Comparator Agent)

Usage:
    # Full pipeline (all phases):
    python main.py --reports-dir data/reports/ --manifest data/manifest.csv

    # Single report:
    python main.py --report data/reports/ptt_2023.pdf --company "PTT PCL" --sector "Energy" --year 2023

    # Skip Phase 1 (reuse existing Phase 1 JSON outputs):
    python main.py --skip-phase1 --manifest data/manifest.csv

    # Run only Phase 1:
    python main.py --reports-dir data/reports/ --manifest data/manifest.csv --only-phase1

    # Auto-discover all PDFs in a folder (no manifest needed):
    python main.py --reports-dir data/reports/ --only-phase1

    # Auto-discover with full pipeline:
    python main.py --reports-dir data/reports/
"""

import argparse
import asyncio
import json
import csv
from pathlib import Path

from config.settings import validate_keys, OUTPUTS_DIR
from agents.planner import PlannerAgent
from agents.mapper import MapperAgent
from agents.scorer import ScorerAgent
from agents.comparator import ComparatorAgent
from utils.dashboard import generate_report_dashboard, generate_comparison_dashboard


def discover_pdfs(reports_dir: str) -> list[dict]:
    """
    Auto-discover all PDF files in a directory and create manifest entries
    with metadata derived from filenames.

    Filename convention: COMPANY-YEAR-SR-LANG.pdf
    e.g., CPF-2023-SR-EN.pdf → company="CPF", year="2023"
    """
    reports_path = Path(reports_dir)
    if not reports_path.exists():
        print(f"ERROR: Reports directory not found: {reports_dir}")
        return []

    pdf_files = sorted(reports_path.glob("*.pdf"))
    if not pdf_files:
        print(f"WARNING: No PDF files found in {reports_dir}")
        return []

    entries = []
    for pdf in pdf_files:
        # Try to parse metadata from filename
        stem = pdf.stem  # e.g., "CPF-2023-SR-EN"
        parts = stem.split("-")

        company = parts[0] if len(parts) >= 1 else "Unknown"
        year = "Unknown"
        for part in parts:
            if part.isdigit() and len(part) == 4:
                year = part
                break

        entries.append({
            "filename": pdf.name,
            "company": company,
            "sector": "Unknown",
            "report_year": year,
            "self_declared_sdgs": [],
        })

    return entries


def load_manifest(manifest_path: str) -> list[dict]:
    """
    Load a CSV manifest describing the reports to process.
    Expected columns: filename, company, sector, report_year, self_declared_sdgs
    """
    reports = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sdgs = row.get("self_declared_sdgs", "")
            row["self_declared_sdgs"] = [s.strip() for s in sdgs.split(",") if s.strip()]
            reports.append(row)
    return reports


def load_phase1_result(filename: str) -> dict:
    """Load an existing Phase 1 JSON result from the outputs directory."""
    stem = Path(filename).stem
    phase1_path = OUTPUTS_DIR / f"{stem}_phase1.json"
    full_path = OUTPUTS_DIR / f"{stem}_full.json"

    # Prefer phase1 file, fall back to full file
    for path in [phase1_path, full_path]:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                result = json.load(f)
            print(f"  Loaded existing Phase 1 from: {path.name}")
            print(f"  Claims: {len(result.get('claims', []))} | Sections: {result.get('metadata', {}).get('sections_found', '?')}")
            return result

    return None


def process_single_report(
    pdf_path: str,
    company: str,
    sector: str,
    report_year: str,
    self_declared_sdgs: list = None,
    extractor: str = "ade",
    skip_phase1: bool = False,
    only_phase1: bool = False,
    no_dashboard: bool = False,
    concurrency: int = 0,
) -> dict:
    """Run pipeline phases on a single report."""

    filename = Path(pdf_path).name if pdf_path else "unknown"

    # --- Phase 1: Ingestion ---
    if skip_phase1:
        result = load_phase1_result(filename)
        if result is None:
            print(f"\n  ERROR: No Phase 1 output found for {filename}. Run Phase 1 first.")
            return None
    else:
        planner = PlannerAgent(extractor=extractor)
        result = planner.process_report(pdf_path, company, sector, report_year)

    if self_declared_sdgs:
        result["metadata"]["self_declared_sdgs"] = self_declared_sdgs

    # If only running Phase 1, save and return
    if only_phase1:
        output_path = OUTPUTS_DIR / f"{Path(filename).stem}_phase1.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n  Phase 1 saved to: {output_path}")
        return result

    # --- Phase 2: SDG Mapping ---
    mapper = MapperAgent()
    if concurrency > 0:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result["claims"] = loop.run_until_complete(mapper.process_all_claims_async(result["claims"], concurrency))
        finally:
            # Shut down pending async generators and tasks before closing
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
            loop.close()
    else:
        result["claims"] = mapper.process_all_claims(result["claims"])

    # --- Phase 3: Credibility Scoring ---
    scorer = ScorerAgent()
    if concurrency > 0:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result["claims"] = loop.run_until_complete(scorer.process_all_claims_async(result["claims"], concurrency))
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
            loop.close()
    else:
        result["claims"] = scorer.process_all_claims(result["claims"])

    # Save per-report results
    output_path = OUTPUTS_DIR / f"{Path(filename).stem}_full.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n  Full results saved to: {output_path}")

    # Generate per-report dashboard
    if not no_dashboard:
        try:
            generate_report_dashboard(result)
        except Exception as e:
            print(f"  WARNING: Dashboard generation failed: {e}")

    return result


def main():
    parser = argparse.ArgumentParser(description="SDG Credibility Assessment Framework")
    parser.add_argument("--report", help="Path to a single PDF report")
    parser.add_argument("--reports-dir", help="Directory containing PDF reports")
    parser.add_argument("--manifest", help="CSV manifest with report metadata")
    parser.add_argument("--company", default="Unknown", help="Company name (single report mode)")
    parser.add_argument("--sector", default="Unknown", help="Sector (single report mode)")
    parser.add_argument("--year", default="Unknown", help="Report year (single report mode)")
    parser.add_argument("--skip-phase4", action="store_true", help="Skip cross-report analysis")
    parser.add_argument("--skip-phase1", action="store_true",
                        help="Skip Phase 1; load existing Phase 1 JSON outputs from data/outputs/")
    parser.add_argument("--only-phase1", action="store_true",
                        help="Run only Phase 1 (extraction + claim identification), then stop")
    parser.add_argument("--extractor", default="ade", choices=["pymupdf", "ade", "pdfplumber"],
                        help="PDF extractor: pymupdf (local), pdfplumber (pdfminer-based, local), or ade (LandingAI API)")
    parser.add_argument("--no-dashboard", action="store_true",
                        help="Skip HTML dashboard generation")
    parser.add_argument("--dashboard-only", action="store_true",
                        help="Regenerate dashboards from existing *_full.json outputs (no pipeline run)")
    parser.add_argument("--concurrency", type=int, default=0,
                        help="Enable parallel API calls with N concurrent requests (0=sequential, recommended: 5-10)")
    args = parser.parse_args()

    if not validate_keys():
        print("\nPlease set up your .env file first. See README.md.")
        return

    # --- Dashboard-only mode: regenerate from existing JSONs ---
    if args.dashboard_only:
        print(f"\nRegenerating dashboards from existing outputs in {OUTPUTS_DIR}")
        full_jsons = sorted(OUTPUTS_DIR.glob("*_full.json"))
        if not full_jsons:
            print("  No *_full.json files found. Run the pipeline first.")
            return
        all_results = []
        for jpath in full_jsons:
            with open(jpath, "r", encoding="utf-8") as f:
                result = json.load(f)
            company = result.get("metadata", {}).get("company", jpath.stem)
            print(f"  Loading: {jpath.name} ({company})")
            generate_report_dashboard(result)
            all_results.append(result)
        if len(all_results) > 1:
            generate_comparison_dashboard(all_results)
        print(f"\n  Dashboards generated for {len(all_results)} reports.")
        return

    all_results = []

    # --- Single report mode ---
    if args.report:
        result = process_single_report(
            args.report, args.company, args.sector, args.year,
            extractor=args.extractor,
            skip_phase1=args.skip_phase1,
            only_phase1=args.only_phase1,
            no_dashboard=args.no_dashboard,
            concurrency=args.concurrency,
        )
        if result:
            all_results.append(result)

    # --- Batch mode with manifest or auto-discovery ---
    elif args.manifest or args.reports_dir:
        if args.manifest:
            manifest = load_manifest(args.manifest)
            print(f"\nLoaded manifest with {len(manifest)} reports")
        else:
            manifest = discover_pdfs(args.reports_dir)
            print(f"\nAuto-discovered {len(manifest)} PDF files in {args.reports_dir}")

        reports_dir = Path(args.reports_dir) if args.reports_dir else None

        if args.skip_phase1:
            print("  (Skipping Phase 1 — loading existing outputs)")

        for entry in manifest:
            filename = entry["filename"]

            if args.skip_phase1:
                pdf_path = filename  # Pass filename so load_phase1_result can find the JSON
            else:
                if not reports_dir:
                    print("\n  ERROR: --reports-dir required when running Phase 1.")
                    return
                pdf_path = str(reports_dir / filename)
                if not Path(pdf_path).exists():
                    print(f"\n  WARNING: File not found: {pdf_path}, skipping.")
                    continue

            result = process_single_report(
                pdf_path,
                entry.get("company", "Unknown"),
                entry.get("sector", "Unknown"),
                entry.get("report_year", "Unknown"),
                entry.get("self_declared_sdgs", []),
                extractor=args.extractor,
                skip_phase1=args.skip_phase1,
                only_phase1=args.only_phase1,
                no_dashboard=args.no_dashboard,
                concurrency=args.concurrency,
            )
            if result:
                all_results.append(result)

    else:
        parser.print_help()
        print("\nProvide either --report (single), --manifest (batch), or --reports-dir (auto-discover).")
        return

    # --- Phase 4: Cross-report analysis ---
    if args.only_phase1:
        print(f"\n{'='*60}")
        print("PHASE 1 COMPLETE")
        print(f"{'='*60}")
        print(f"Reports processed: {len(all_results)}")
        print(f"Results saved to: {OUTPUTS_DIR}")
    elif not args.skip_phase4 and len(all_results) > 1:
        comparator = ComparatorAgent()
        comparator.load_corpus(all_results)
        summary = comparator.generate_summary()

        # Generate comparison dashboard
        if not args.no_dashboard:
            try:
                generate_comparison_dashboard(all_results)
            except Exception as e:
                print(f"  WARNING: Comparison dashboard failed: {e}")

        print(f"\n{'='*60}")
        print("PIPELINE COMPLETE")
        print(f"{'='*60}")
        print(f"Reports processed: {len(all_results)}")
        print(f"Total claims: {summary['total_claims']}")
        print(f"Claims with SDG mappings: {summary['claims_with_mappings']}")
        print(f"Results saved to: {OUTPUTS_DIR}")
    else:
        print(f"\n{'='*60}")
        print("PIPELINE COMPLETE (Phases 1-3)")
        print(f"{'='*60}")
        print(f"Reports processed: {len(all_results)}")
        print(f"Results saved to: {OUTPUTS_DIR}")


if __name__ == "__main__":
    main()
