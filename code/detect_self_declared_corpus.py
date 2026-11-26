"""
detect_self_declared_corpus.py — run the existing self-declared SDG detector
across all 30 corpus reports in data/outputs/main/full/.

Wraps the detection function from detect_self_declared_sdgs.py but points at
the current corpus location rather than the legacy single-folder structure.

Output: data/outputs/validation/self_declared_sdgs_corpus.json
        (list of 30 detection records, one per report)
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from openai import AsyncOpenAI

from config.settings import OPENAI_API_KEY, OUTPUTS_DIR

# Reuse the detection function and JSON loader from the legacy script
from detect_self_declared_sdgs import (
    detect_sdgs_for_report,
    load_report_data,
)


async def main():
    if not OPENAI_API_KEY:
        sys.exit("OPENAI_API_KEY not set in .env")

    full_dir = OUTPUTS_DIR / "main" / "full"
    full_jsons = sorted(full_dir.glob("*_full.json"))
    if not full_jsons:
        sys.exit(f"No *_full.json files found in {full_dir}")

    print(f"Detecting self-declared SDGs across {len(full_jsons)} reports")
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    tasks = [detect_sdgs_for_report(load_report_data(str(p)), client) for p in full_jsons]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    await client.close()

    clean = []
    for p, r in zip(full_jsons, results):
        if isinstance(r, Exception):
            print(f"  FAIL {p.name}: {r}")
            continue
        clean.append(r)
        sdgs = sorted({s.get("sdg_number") for s in r.get("self_declared_sdgs", []) if s.get("confidence") in ("high", "medium")})
        print(f"  {r.get('company', p.stem):<32} → SDGs {sdgs}")

    out_path = OUTPUTS_DIR / "validation" / "self_declared_sdgs_corpus.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out_path}  ({len(clean)} records)")


if __name__ == "__main__":
    asyncio.run(main())
