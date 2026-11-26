"""
Phase 1: Report Ingestion & Structuring (Planner Agent)

This agent:
1. Extracts text from PDF sustainability reports (PyMuPDF or LandingAI ADE)
2. Identifies report structure (sections, subsections)
3. Extracts discrete sustainability claims with source metadata
4. Outputs a structured claim registry (JSON)
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from openai import OpenAI
from tqdm import tqdm

from config.settings import (
    LANDINGAI_API_KEY,
    OPENAI_API_KEY,
    PRIMARY_MODEL,
    OUTPUTS_DIR,
)
from prompts.claim_extraction import (
    SECTION_IDENTIFICATION_PROMPT,
    SECTION_IDENTIFICATION_BY_INDEX_PROMPT,
    SECTION_IDENTIFICATION_WINDOW_PROMPT,
    SECTION_MERGE_PROMPT,
    CLAIM_EXTRACTION_PROMPT,
)


# --- Unified chunk format used by both extractors ---

@dataclass
class Chunk:
    """A single text chunk extracted from a PDF page."""
    text: str
    page: int
    chunk_type: str = "text"


@dataclass
class ExtractedDocument:
    """Unified extraction result, compatible with both PyMuPDF and ADE."""
    chunks: list
    num_pages: int
    source: str = "pymupdf"  # "pymupdf" or "landingai_ade"


class PlannerAgent:
    """Phase 1 agent: ingests PDF reports and extracts structured claims."""

    def __init__(self, extractor: str = "pymupdf"):
        """
        Args:
            extractor: "pymupdf" (local, no API needed) or "ade" (LandingAI ADE)
        """
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = PRIMARY_MODEL
        self.extractor = extractor

    # -----------------------------------------------------------------
    # Step 1a: PDF Extraction via PyMuPDF (default fallback)
    # -----------------------------------------------------------------
    def extract_pdf_pymupdf(self, pdf_path: str) -> ExtractedDocument:
        """
        Parse a PDF using PyMuPDF (local, no API key needed).
        Extracts text page-by-page and creates chunks.
        """
        import pymupdf

        print(f"  Extracting PDF via PyMuPDF: {Path(pdf_path).name}")
        doc = pymupdf.open(pdf_path)
        num_pages = len(doc)
        chunks = []

        for page_num in range(num_pages):
            page = doc[page_num]

            # Extract text blocks (preserves reading order better than get_text())
            blocks = page.get_text("blocks")
            for block in blocks:
                # block format: (x0, y0, x1, y1, text, block_no, block_type)
                text = block[4].strip()
                block_type = block[6]  # 0 = text, 1 = image

                if block_type == 0 and text and len(text) > 10:
                    chunks.append(Chunk(
                        text=text,
                        page=page_num + 1,  # 1-indexed
                        chunk_type="text",
                    ))

            # Also extract tables if present
            try:
                tables = page.find_tables()
                for table in tables:
                    table_data = table.extract()
                    if table_data:
                        # Convert table to readable text
                        rows = []
                        for row in table_data:
                            row_text = " | ".join(
                                str(cell) if cell else "" for cell in row
                            )
                            rows.append(row_text)
                        table_text = "\n".join(rows)
                        if table_text.strip():
                            chunks.append(Chunk(
                                text=table_text,
                                page=page_num + 1,
                                chunk_type="table",
                            ))
            except Exception:
                pass  # Table extraction not critical

        doc.close()
        print(f"  Extracted {len(chunks)} chunks across {num_pages} pages")

        return ExtractedDocument(
            chunks=chunks,
            num_pages=num_pages,
            source="pymupdf",
        )

    # -----------------------------------------------------------------
    # Step 1b: PDF Extraction via pdfplumber (pdfminer.six-based)
    # -----------------------------------------------------------------
    def extract_pdf_pdfplumber(self, pdf_path: str) -> ExtractedDocument:
        """
        Parse a PDF using pdfplumber (built on pdfminer.six).
        pdfminer.six is the most widely used Python PDF extraction library
        in academic NLP research. pdfplumber adds table detection on top.
        """
        import pdfplumber

        print(f"  Extracting PDF via pdfplumber (pdfminer.six): {Path(pdf_path).name}")
        chunks = []

        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)

            for page_num, page in enumerate(pdf.pages):
                # Extract main text
                text = page.extract_text()
                if text and text.strip() and len(text.strip()) > 10:
                    # Split into paragraphs (pdfplumber returns one big text block)
                    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
                    for para in paragraphs:
                        if len(para) > 10:
                            chunks.append(Chunk(
                                text=para,
                                page=page_num + 1,  # 1-indexed
                                chunk_type="text",
                            ))

                # Extract tables separately
                try:
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            rows = []
                            for row in table:
                                row_text = " | ".join(
                                    str(cell) if cell else "" for cell in row
                                )
                                rows.append(row_text)
                            table_text = "\n".join(rows)
                            if table_text.strip() and len(table_text.strip()) > 10:
                                chunks.append(Chunk(
                                    text=table_text,
                                    page=page_num + 1,
                                    chunk_type="table",
                                ))
                except Exception:
                    pass  # Table extraction not critical

        print(f"  Extracted {len(chunks)} chunks across {num_pages} pages")

        return ExtractedDocument(
            chunks=chunks,
            num_pages=num_pages,
            source="pdfplumber",
        )

    # -----------------------------------------------------------------
    # Step 1c: PDF Extraction via LandingAI ADE (optional, API-based)
    # -----------------------------------------------------------------
    def extract_pdf_ade(self, pdf_path: str) -> ExtractedDocument:
        """
        Parse a PDF using LandingAI Agentic Document Extraction.
        Better for complex layouts (infographics, nested tables, charts).
        Requires LANDINGAI_API_KEY.
        """
        from agentic_doc.parse import parse_documents

        print(f"  Extracting PDF via LandingAI ADE: {Path(pdf_path).name}")
        results = parse_documents([pdf_path])

        if not results:
            raise ValueError(f"ADE returned no results for {pdf_path}")

        result = results[0]

        # Check for extraction errors before proceeding
        if hasattr(result, "errors") and result.errors:
            error_count = len(result.errors)
            sample_error = str(result.errors[0])[:200]
            print(f"  WARNING: ADE reported {error_count} page errors.")
            print(f"  Sample error: {sample_error}")
            # If every page errored, fail fast to PyMuPDF fallback
            total_pages = 0
            if hasattr(result, "end_page_idx") and hasattr(result, "start_page_idx"):
                total_pages = result.end_page_idx - result.start_page_idx + 1
            if total_pages > 0 and error_count >= total_pages:
                print(f"  ERROR: All {total_pages} pages failed ADE extraction. Falling back to PyMuPDF.")
                return self.extract_pdf_pymupdf(pdf_path)

        # Debug: inspect the result object structure
        print(f"  ADE result type: {type(result).__name__}")
        if hasattr(result, "chunks"):
            print(f"  ADE chunks count: {len(result.chunks)}")
        elif hasattr(result, "segments"):
            print(f"  ADE segments count: {len(result.segments)}")
        elif hasattr(result, "markdown"):
            print(f"  ADE markdown length: {len(result.markdown)}")

        # Convert ADE chunks to our unified format
        chunks = []
        max_page = 0

        # Try multiple possible structures from different agentic-doc versions
        raw_chunks = []
        if hasattr(result, "chunks") and result.chunks:
            raw_chunks = result.chunks
        elif hasattr(result, "segments") and result.segments:
            raw_chunks = result.segments

        for chunk in raw_chunks:
            # Try various attribute names for page number
            page = 0
            for attr in ["page", "page_number", "page_num", "page_idx"]:
                if hasattr(chunk, attr):
                    val = getattr(chunk, attr)
                    if val is not None:
                        page = int(val) if not isinstance(val, int) else val
                        break

            # Try various attribute names for text content
            text = ""
            for attr in ["text", "content", "markdown", "raw_text"]:
                if hasattr(chunk, attr):
                    val = getattr(chunk, attr)
                    if val:
                        text = str(val)
                        break

            # If chunk is a dict instead of object
            if not text and isinstance(chunk, dict):
                text = chunk.get("text", chunk.get("content", chunk.get("markdown", "")))
                page = chunk.get("page", chunk.get("page_number", 0))

            if text:
                max_page = max(max_page, page)
                chunk_type_val = "text"
                for attr in ["chunk_type", "type", "segment_type", "category"]:
                    if hasattr(chunk, attr):
                        chunk_type_val = str(getattr(chunk, attr)) or "text"
                        break
                chunks.append(Chunk(text=text, page=page, chunk_type=chunk_type_val))

        # Fallback: if no chunks but markdown is available, split by pages
        if not chunks and hasattr(result, "markdown") and result.markdown and result.markdown.strip():
            print("  Falling back to markdown extraction...")
            md = result.markdown.strip()
            # Simple page split if markdown contains page markers
            chunks.append(Chunk(text=md, page=1, chunk_type="markdown"))
            max_page = 1

        num_pages = max_page if max_page > 0 else len(set(c.page for c in chunks)) if chunks else 0
        print(f"  Extracted {len(chunks)} chunks across {num_pages} pages")

        if not chunks:
            print("  WARNING: ADE extraction produced 0 chunks. Falling back to PyMuPDF.")
            return self.extract_pdf_pymupdf(pdf_path)

        return ExtractedDocument(
            chunks=chunks,
            num_pages=num_pages,
            source="landingai_ade",
        )

    # -----------------------------------------------------------------
    # Step 1: Unified extraction entry point
    # -----------------------------------------------------------------
    def extract_pdf(self, pdf_path: str) -> ExtractedDocument:
        """Route to the configured extractor."""
        if self.extractor == "ade":
            return self.extract_pdf_ade(pdf_path)
        elif self.extractor == "pdfplumber":
            return self.extract_pdf_pdfplumber(pdf_path)
        else:
            return self.extract_pdf_pymupdf(pdf_path)

    # -----------------------------------------------------------------
    # Step 2: Structure the extracted content into sections
    # -----------------------------------------------------------------
    def identify_sections(self, extracted: ExtractedDocument) -> list[dict]:
        """
        Identify the report's structural hierarchy from extracted chunks.
        Uses multi-window scanning to cover the full document.
        """
        total_chunks = len(extracted.chunks)

        # Check if page numbers are reliable
        unique_pages = set(c.page for c in extracted.chunks)
        self._pages_reliable = len(unique_pages) > 2
        if not self._pages_reliable:
            print(f"  NOTE: Page numbers unreliable (only values: {unique_pages}). Using chunk-index strategy.")

        # For small documents (≤200 chunks), use single-pass identification
        if total_chunks <= 200:
            return self._identify_sections_single_pass(extracted)

        # For larger documents, use multi-window scanning
        return self._identify_sections_multi_window(extracted)

    def _identify_sections_single_pass(self, extracted: ExtractedDocument) -> list[dict]:
        """Single-pass section identification for small documents."""
        chunk_summaries = []
        for i, chunk in enumerate(extracted.chunks):
            summary = {"index": i, "type": chunk.chunk_type, "text": chunk.text[:200] if chunk.text else ""}
            if self._pages_reliable:
                summary["page"] = chunk.page
            chunk_summaries.append(summary)

        if self._pages_reliable:
            prompt = SECTION_IDENTIFICATION_PROMPT.format(chunks=json.dumps(chunk_summaries, indent=2))
        else:
            prompt = SECTION_IDENTIFICATION_BY_INDEX_PROMPT.format(chunks=json.dumps(chunk_summaries, indent=2))

        print(f"  Identifying sections (single pass, {len(chunk_summaries)} chunks)...")
        sections = self._call_section_llm(prompt)

        if not sections:
            sections = self._fallback_uniform_sections(len(extracted.chunks))

        sections = self._normalize_sections(sections)
        print(f"  Found {len(sections)} top-level sections")
        return sections

    def _identify_sections_multi_window(self, extracted: ExtractedDocument) -> list[dict]:
        """
        Multi-window section identification for large documents.
        Scans the full document in overlapping windows, then merges results.
        """
        total_chunks = len(extracted.chunks)
        window_size = 150  # chunks per window
        stride = 120       # overlap of 30 chunks between windows
        windows = []

        start = 0
        while start < total_chunks:
            end = min(start + window_size, total_chunks)
            windows.append((start, end))
            if end >= total_chunks:
                break
            start += stride

        print(f"  Identifying sections (multi-window: {len(windows)} windows across {total_chunks} chunks)...")

        # Pass 1: Scan each window for section boundaries
        all_raw_sections = []
        for w_idx, (w_start, w_end) in enumerate(windows):
            chunk_summaries = []
            for i, chunk in enumerate(extracted.chunks[w_start:w_end]):
                summary = {
                    "index": w_start + i,
                    "type": chunk.chunk_type,
                    "text": chunk.text[:150] if chunk.text else "",
                }
                chunk_summaries.append(summary)

            prompt = SECTION_IDENTIFICATION_WINDOW_PROMPT.format(
                window_start=w_start,
                window_end=w_end,
                total_chunks=total_chunks,
                chunks=json.dumps(chunk_summaries, indent=2),
            )

            response = self.openai_client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are an expert at analysing the structure of corporate sustainability reports. Always respond with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
            )

            raw = json.loads(response.choices[0].message.content)
            window_sections = raw.get("sections", []) if isinstance(raw, dict) else raw
            if isinstance(window_sections, list):
                for s in window_sections:
                    if isinstance(s, dict):
                        all_raw_sections.append(s)

            print(f"    Window {w_idx + 1}/{len(windows)} (chunks {w_start}-{w_end}): {len(window_sections) if isinstance(window_sections, list) else 0} sections found")

        if not all_raw_sections:
            print("  WARNING: No sections found in any window. Using fallback.")
            sections = self._fallback_uniform_sections(total_chunks)
            sections = self._normalize_sections(sections)
            print(f"  Found {len(sections)} top-level sections (fallback)")
            return sections

        # Pass 2: Merge overlapping sections into a unified list
        print(f"  Merging {len(all_raw_sections)} raw sections from {len(windows)} windows...")

        raw_sections_text = json.dumps(all_raw_sections, indent=2)
        merge_prompt = SECTION_MERGE_PROMPT.format(
            total_chunks=total_chunks,
            raw_sections=raw_sections_text,
        )

        response = self.openai_client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are an expert at analysing the structure of corporate sustainability reports. Always respond with valid JSON."},
                {"role": "user", "content": merge_prompt},
            ],
        )

        merged = json.loads(response.choices[0].message.content)
        sections = merged.get("sections", []) if isinstance(merged, dict) else merged
        if not isinstance(sections, list):
            sections = []
        sections = [s for s in sections if isinstance(s, dict)]

        if not sections:
            print("  WARNING: Merge returned 0 sections. Using fallback.")
            sections = self._fallback_uniform_sections(total_chunks)

        sections = self._normalize_sections(sections)
        print(f"  Found {len(sections)} top-level sections (covering chunks 0-{total_chunks})")
        return sections

    def _call_section_llm(self, prompt: str) -> list[dict]:
        """Call the LLM for section identification with retry logic."""
        for attempt in range(2):
            response = self.openai_client.chat.completions.create(
                model=self.model,
                temperature=0.1 + (attempt * 0.2),
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are an expert at analysing the structure of corporate sustainability reports. Always respond with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
            )
            raw = json.loads(response.choices[0].message.content)
            if isinstance(raw, dict):
                sections = raw.get("sections", list(raw.values())[0])
            else:
                sections = raw
            if isinstance(sections, list):
                sections = [s for s in sections if isinstance(s, dict)]
                if sections:
                    return sections
            print(f"  WARNING: Attempt {attempt + 1} returned 0 sections. {'Retrying...' if attempt == 0 else ''}")
        return []

    def _fallback_uniform_sections(self, total_chunks: int) -> list[dict]:
        """Create uniform sections as a last resort."""
        n_sections = min(10, max(3, total_chunks // 100))
        chunk_per = total_chunks // n_sections
        print(f"  FALLBACK: Creating {n_sections} uniform sections from {total_chunks} chunks.")
        sections = []
        for i in range(n_sections):
            sections.append({
                "section_title": f"Report Section {i + 1}",
                "level": 1,
                "start_chunk": i * chunk_per,
                "end_chunk": min((i + 1) * chunk_per, total_chunks) if i < n_sections - 1 else total_chunks,
                "subsections": [],
            })
        return sections

    def _normalize_sections(self, sections: list[dict]) -> list[dict]:
        """Normalize section format: ensure start_chunk/end_chunk and start_page/end_page exist."""
        for section in sections:
            if isinstance(section, str):
                section = {"section_title": section, "start_chunk": 0, "end_chunk": 100}
            if "start_chunk" in section and "start_page" not in section:
                section["start_page"] = section["start_chunk"]
                section["end_page"] = section["end_chunk"]
            if "start_page" in section and "start_chunk" not in section:
                section["start_chunk"] = section.get("start_page", 0)
                section["end_chunk"] = section.get("end_page", 0)
            for sub in section.get("subsections", []):
                if isinstance(sub, dict):
                    if "start_chunk" in sub and "start_page" not in sub:
                        sub["start_page"] = sub["start_chunk"]
                        sub["end_page"] = sub["end_chunk"]
                    if "start_page" in sub and "start_chunk" not in sub:
                        sub["start_chunk"] = sub.get("start_page", 0)
                        sub["end_chunk"] = sub.get("end_page", 0)
        return sections

    # -----------------------------------------------------------------
    # Step 3: Extract claims from each section
    # -----------------------------------------------------------------
    def extract_claims_from_section(
        self, extracted: ExtractedDocument, section: dict, chunk_range: tuple = None
    ) -> list[dict]:
        """
        Extract sustainability claims from a single report section.

        Args:
            extracted: The full extracted document
            section: Section metadata dict
            chunk_range: Optional (start_idx, end_idx) for direct chunk slicing
                         Used when page numbers are unreliable.
        """
        section_title = section.get("section_title", "Unknown")
        section_text_parts = []

        if chunk_range:
            # Direct chunk index range (used when pages are unreliable)
            start_idx, end_idx = chunk_range
            for chunk in extracted.chunks[start_idx:end_idx]:
                if chunk.text:
                    section_text_parts.append(chunk.text)
        else:
            # Page-based filtering
            start_page = section.get("start_page", 0)
            end_page = section.get("end_page", start_page + 10)
            for chunk in extracted.chunks:
                if start_page <= chunk.page <= end_page:
                    if chunk.text:
                        section_text_parts.append(chunk.text)

        section_text = "\n".join(section_text_parts)

        if not section_text.strip():
            return []

        # Truncate to ~12,000 chars to fit in context window
        if len(section_text) > 12000:
            section_text = section_text[:12000] + "\n[... truncated]"

        response = self.openai_client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert sustainability analyst. Extract claims accurately. Always respond with valid JSON containing a 'claims' array.",
                },
                {
                    "role": "user",
                    "content": CLAIM_EXTRACTION_PROMPT.format(
                        section_title=section_title,
                        start_page=chunk_range[0] if chunk_range else section.get("start_page", "?"),
                        end_page=chunk_range[1] if chunk_range else section.get("end_page", "?"),
                        text_content=section_text,
                    ),
                },
            ],
        )

        raw = response.choices[0].message.content
        parsed = json.loads(raw)

        # Handle various JSON wrapper formats
        if isinstance(parsed, dict):
            claims = parsed.get("claims", list(parsed.values())[0] if parsed else [])
        elif isinstance(parsed, list):
            claims = parsed
        else:
            claims = []

        return claims

    # -----------------------------------------------------------------
    # Step 4: Build the full claim registry
    # -----------------------------------------------------------------
    def build_claim_registry(
        self, extracted: ExtractedDocument, sections: list[dict], report_metadata: dict
    ) -> list[dict]:
        """
        Process all sections and build the complete claim registry.
        Each claim gets a unique ID and full metadata.
        """
        all_claims = []
        claim_id = 0

        # Process top-level sections and their subsections
        # Handle cases where LLM returns strings instead of dicts
        sections_to_process = []
        for section in sections:
            if isinstance(section, str):
                section = {"section_title": section, "start_page": 1, "end_page": 10}
            sections_to_process.append(section)
            for sub in section.get("subsections", []):
                if isinstance(sub, str):
                    sub = {"section_title": sub, "start_page": section.get("start_page", 1), "end_page": section.get("end_page", 10)}
                sections_to_process.append(sub)

        print(f"  Extracting claims from {len(sections_to_process)} sections...")

        # Determine if we need chunk-index strategy
        pages_reliable = getattr(self, "_pages_reliable", True)

        # Build chunk ranges for each section
        chunk_ranges = {}
        if not pages_reliable:
            for i, sec in enumerate(sections_to_process):
                # Use start_chunk/end_chunk if the LLM provided them
                if "start_chunk" in sec:
                    chunk_ranges[i] = (sec["start_chunk"], sec["end_chunk"])
                elif "start_page" in sec:
                    # start_page/end_page were mapped from start_chunk/end_chunk in identify_sections
                    chunk_ranges[i] = (sec["start_page"], sec["end_page"])

            # If no chunk ranges were set (shouldn't happen), fall back to uniform
            if not chunk_ranges:
                total_chunks = len(extracted.chunks)
                chunk_per_section = max(1, total_chunks // len(sections_to_process))
                for i in range(len(sections_to_process)):
                    start_idx = i * chunk_per_section
                    end_idx = min((i + 1) * chunk_per_section, total_chunks)
                    if i == len(sections_to_process) - 1:
                        end_idx = total_chunks
                    chunk_ranges[i] = (start_idx, end_idx)

            print(f"  Using chunk-index strategy for {len(chunk_ranges)} sections")

        for i, section in enumerate(tqdm(sections_to_process, desc="  Processing sections")):
            cr = chunk_ranges.get(i) if not pages_reliable else None
            claims = self.extract_claims_from_section(extracted, section, chunk_range=cr)

            for claim in claims:
                claim_id += 1
                all_claims.append({
                    "claim_id": f"CLM-{claim_id:04d}",
                    "claim_text": claim.get("claim_text", ""),
                    "claim_type": claim.get("claim_type", "unknown"),
                    "page": claim.get("page"),
                    "section": claim.get("section", section.get("section_title")),
                    "company": report_metadata.get("company", "Unknown"),
                    "sector": report_metadata.get("sector", "Unknown"),
                    "report_year": report_metadata.get("report_year", "Unknown"),
                    "source_file": report_metadata.get("filename", "Unknown"),
                    # Phases 2-3 will populate these:
                    "sdg_mappings": [],
                    "credibility_scores": {},
                    "composite_score": None,
                    "credibility_tier": None,
                })

        print(f"  Total claims extracted: {len(all_claims)}")
        return all_claims

    # -----------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------
    def process_report(
        self,
        pdf_path: str,
        company: str = "Unknown",
        sector: str = "Unknown",
        report_year: str = "Unknown",
    ) -> dict:
        """
        Full Phase 1 pipeline: PDF → structured claims.

        Args:
            pdf_path: Path to the PDF sustainability report
            company: Company name
            sector: Industry sector
            report_year: Reporting year

        Returns:
            dict with 'metadata' and 'claims' (the claim registry)
        """
        pdf_path = str(pdf_path)
        filename = Path(pdf_path).name

        print(f"\n{'='*60}")
        print(f"PHASE 1: Processing {filename}")
        print(f"  Extractor: {self.extractor}")
        print(f"{'='*60}")

        report_metadata = {
            "company": company,
            "sector": sector,
            "report_year": report_year,
            "filename": filename,
            "extractor": self.extractor,
        }

        # Step 1: Extract PDF
        extracted = self.extract_pdf(pdf_path)
        report_metadata["total_pages"] = extracted.num_pages
        report_metadata["total_chunks"] = len(extracted.chunks)

        # Step 2: Identify sections
        sections = self.identify_sections(extracted)
        report_metadata["sections_found"] = len(sections)

        # Step 3-4: Extract claims and build registry
        claims = self.build_claim_registry(extracted, sections, report_metadata)
        report_metadata["total_claims"] = len(claims)

        result = {
            "metadata": report_metadata,
            "sections": sections,
            "claims": claims,
        }

        # Save output (use extractor prefix for non-ADE to avoid overwriting protected ADE files)
        if self.extractor in ("pymupdf", "pdfplumber"):
            output_path = OUTPUTS_DIR / f"{self.extractor}_{Path(pdf_path).stem}_phase1.json"
        else:
            output_path = OUTPUTS_DIR / f"{Path(pdf_path).stem}_phase1.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n  Phase 1 complete. Output saved to: {output_path}")
        print(f"  Extractor: {self.extractor} | Pages: {extracted.num_pages} | Sections: {len(sections)} | Claims: {len(claims)}")

        return result
