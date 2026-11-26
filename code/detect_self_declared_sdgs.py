"""
SDG Self-Declaration Detector

Scans sustainability report claim data (from Phase 1 outputs) and uses GPT-4o
to identify which SDGs each company explicitly declares as priorities vs. merely
mentions in passing.

Output: JSON with detected self-declared SDGs per company + supporting evidence,
        ready for human verification before updating the manifest.

Usage:
    # Detect from all *_full.json files:
    python detect_self_declared_sdgs.py

    # Review-only mode (re-display previous results):
    python detect_self_declared_sdgs.py --results-only

    # Specify output path:
    python detect_self_declared_sdgs.py --output data/outputs/self_declared_sdgs.json
"""

import argparse
import asyncio
import json
import re
from pathlib import Path

from openai import AsyncOpenAI
from config.settings import OPENAI_API_KEY, OUTPUTS_DIR, PRIMARY_MODEL


SDG_NAMES = {
    1: "No Poverty",
    2: "Zero Hunger",
    3: "Good Health and Well-Being",
    4: "Quality Education",
    5: "Gender Equality",
    6: "Clean Water and Sanitation",
    7: "Affordable and Clean Energy",
    8: "Decent Work and Economic Growth",
    9: "Industry, Innovation and Infrastructure",
    10: "Reduced Inequalities",
    11: "Sustainable Cities and Communities",
    12: "Responsible Consumption and Production",
    13: "Climate Action",
    14: "Life Below Water",
    15: "Life on Land",
    16: "Peace, Justice and Strong Institutions",
    17: "Partnerships for the Goals",
}

DETECTION_PROMPT = """You are an expert analyst reviewing a corporate sustainability report. Your task is to identify which UN Sustainable Development Goals (SDGs) the company EXPLICITLY DECLARES as priorities, commitments, or focus areas.

IMPORTANT DISTINCTIONS:
- "Self-declared" = The company explicitly states it prioritizes, commits to, or aligns with specific SDGs. Look for:
  * Dedicated SDG sections or pages listing their priority goals
  * Statements like "We focus on SDG X", "Our key SDGs include...", "We are committed to..."
  * SDG mapping tables, materiality matrices referencing specific SDGs
  * Strategy sections that name specific SDGs as priorities

- "Mentioned in passing" = SDGs referenced contextually without being claimed as a priority. These should NOT be included.

COMPANY: {company}
SECTOR: {sector}
REPORT YEAR: {report_year}

Below are the sustainability claims extracted from this company's report, organized by section. Use these to identify self-declared SDGs.

{claims_by_section}

RESPOND IN THIS EXACT JSON FORMAT:
{{
    "company": "{company}",
    "self_declared_sdgs": [
        {{
            "sdg_number": <int>,
            "sdg_name": "<name>",
            "confidence": "<high|medium|low>",
            "evidence": "<exact quote or paraphrase from the report that supports this declaration>",
            "section": "<section where evidence was found>"
        }}
    ],
    "sdg_summary": "<1-2 sentence summary of how the company positions its SDG commitments>",
    "detection_notes": "<any caveats about the detection, e.g. if SDG icons were likely present but not captured as text>"
}}

Only include SDGs where you have at least medium confidence. Return the JSON and nothing else."""


def load_report_data(json_path: str) -> dict:
    """Load a full or phase1 JSON output file."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_claims_by_section(report_data: dict) -> str:
    """
    Organize claims by section for the detection prompt.
    Prioritize sections most likely to contain SDG declarations.
    """
    claims = report_data.get("claims", [])

    # Group by section
    sections = {}
    for claim in claims:
        section = claim.get("section", "Unknown")
        if section not in sections:
            sections[section] = []
        sections[section].append(claim["claim_text"])

    # Priority sections that are most likely to contain SDG declarations
    priority_keywords = [
        "sdg", "sustainable development", "sustainability strategy",
        "sustainability", "strategy", "materiality", "framework",
        "commitment", "goal", "target", "priority", "highlight",
        "overview", "message", "chairman", "ceo", "executive",
        "about", "esg", "reporting", "gri"
    ]

    def section_priority(section_name: str) -> int:
        name_lower = section_name.lower()
        score = 0
        for kw in priority_keywords:
            if kw in name_lower:
                score += 1
        return -score  # Negative for ascending sort (highest priority first)

    sorted_sections = sorted(sections.keys(), key=section_priority)

    # Build text, keeping within token limits (~6000 tokens of context)
    lines = []
    total_chars = 0
    max_chars = 20000  # ~5000 tokens

    for section in sorted_sections:
        section_claims = sections[section]
        section_text = f"\n=== {section} ===\n"
        for claim in section_claims:
            section_text += f"- {claim}\n"

        if total_chars + len(section_text) > max_chars:
            # Still add section header with truncation note
            remaining = max_chars - total_chars
            if remaining > 200:
                lines.append(section_text[:remaining] + "\n[... truncated ...]")
            break

        lines.append(section_text)
        total_chars += len(section_text)

    return "\n".join(lines)


async def detect_sdgs_for_report(report_data: dict, client: AsyncOpenAI) -> dict:
    """
    Use GPT-4o to detect self-declared SDGs from a single report's claims.
    """
    metadata = report_data.get("metadata", {})
    company = metadata.get("company", "Unknown")
    sector = metadata.get("sector", "Unknown")
    report_year = metadata.get("report_year", "Unknown")

    claims_text = build_claims_by_section(report_data)

    prompt = DETECTION_PROMPT.format(
        company=company,
        sector=sector,
        report_year=report_year,
        claims_by_section=claims_text,
    )

    print(f"\n  Analyzing {company} ({len(report_data.get('claims', []))} claims)...")

    response = await client.chat.completions.create(
        model=PRIMARY_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,  # Low temp for factual extraction
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        text = response.choices[0].message.content
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            result = {
                "company": company,
                "self_declared_sdgs": [],
                "sdg_summary": "ERROR: Could not parse response",
                "detection_notes": text[:500],
            }

    # Add metadata
    result["filename"] = metadata.get("filename", "")
    result["sector"] = sector
    result["report_year"] = report_year
    result["total_claims_analyzed"] = len(report_data.get("claims", []))

    return result


def display_results(results: list[dict]):
    """Pretty-print the detection results for human review."""
    print(f"\n{'='*70}")
    print("SELF-DECLARED SDG DETECTION RESULTS")
    print(f"{'='*70}")

    for r in results:
        company = r.get("company", "Unknown")
        sdgs = r.get("self_declared_sdgs", [])
        summary = r.get("sdg_summary", "")
        notes = r.get("detection_notes", "")

        print(f"\n{'─'*70}")
        print(f"  {company} ({r.get('sector', '')}, {r.get('report_year', '')})")
        print(f"  Claims analyzed: {r.get('total_claims_analyzed', '?')}")
        print(f"{'─'*70}")

        if summary:
            print(f"\n  Summary: {summary}")

        if sdgs:
            print(f"\n  Self-declared SDGs ({len(sdgs)}):")
            for sdg in sorted(sdgs, key=lambda x: x.get("sdg_number", 0)):
                num = sdg.get("sdg_number", "?")
                name = sdg.get("sdg_name", SDG_NAMES.get(num, "Unknown"))
                conf = sdg.get("confidence", "?")
                evidence = sdg.get("evidence", "")
                section = sdg.get("section", "")

                conf_icon = {"high": "●", "medium": "◐", "low": "○"}.get(conf, "?")
                print(f"    {conf_icon} SDG {num}: {name} [{conf}]")
                if evidence:
                    # Wrap long evidence text
                    ev_short = evidence[:120] + "..." if len(evidence) > 120 else evidence
                    print(f"      Evidence: \"{ev_short}\"")
                if section:
                    print(f"      Section: {section}")
        else:
            print("\n  No explicit SDG declarations detected.")

        if notes:
            print(f"\n  Notes: {notes}")

    # Generate manifest-ready output
    print(f"\n{'='*70}")
    print("MANIFEST-READY FORMAT (for manifest.csv)")
    print(f"{'='*70}")
    print("\nfilename,company,sector,report_year,self_declared_sdgs")
    for r in results:
        filename = r.get("filename", "")
        company = r.get("company", "")
        sector = r.get("sector", "")
        year = r.get("report_year", "")
        sdg_nums = sorted([
            s.get("sdg_number", 0)
            for s in r.get("self_declared_sdgs", [])
            if s.get("confidence", "") in ("high", "medium")
        ])
        sdg_str = ";".join(str(n) for n in sdg_nums)
        print(f'{filename},{company},{sector},{year},"{sdg_str}"')

    print(f"\n{'='*70}")
    print("ACTION REQUIRED: Please review the above results.")
    print("If accurate, the manifest.csv self_declared_sdgs column can be updated.")
    print(f"{'='*70}")


async def main_async(args):
    """Run detection on all reports."""
    # Find all full JSON files
    full_jsons = sorted(OUTPUTS_DIR.glob("*_full.json"))
    if not full_jsons:
        print("ERROR: No *_full.json files found in", OUTPUTS_DIR)
        return

    print(f"Found {len(full_jsons)} report outputs to analyze:")
    for j in full_jsons:
        print(f"  - {j.name}")

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    results = []

    # Process all reports concurrently
    tasks = []
    report_data_list = []
    for jpath in full_jsons:
        report_data = load_report_data(str(jpath))
        report_data_list.append(report_data)
        tasks.append(detect_sdgs_for_report(report_data, client))

    results = await asyncio.gather(*tasks)

    # Save results
    output_path = Path(args.output) if args.output else OUTPUTS_DIR / "self_declared_sdgs.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(list(results), f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {output_path}")

    # Display for human review
    display_results(list(results))

    return results


def main():
    parser = argparse.ArgumentParser(description="Detect self-declared SDGs from sustainability reports")
    parser.add_argument("--output", help="Output JSON path", default=None)
    parser.add_argument("--results-only", action="store_true",
                        help="Display previous results without re-running detection")
    args = parser.parse_args()

    if args.results_only:
        output_path = Path(args.output) if args.output else OUTPUTS_DIR / "self_declared_sdgs.json"
        if not output_path.exists():
            print(f"ERROR: No results found at {output_path}. Run detection first.")
            return
        with open(output_path, "r", encoding="utf-8") as f:
            results = json.load(f)
        display_results(results)
        return

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
