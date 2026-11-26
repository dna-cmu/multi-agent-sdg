"""
Prompt templates for Phase 1: Claim extraction from sustainability reports.
"""

SECTION_IDENTIFICATION_PROMPT = """You are analysing a sustainability report that has been parsed into structured chunks.
Below is a sequence of text chunks from the report, each with its page number and type.

Your task: Identify the report's structural hierarchy — major sections, subsections, and their boundaries.
Return a JSON array of sections.

Chunks:
{chunks}

Return ONLY valid JSON in this format:
[
  {{
    "section_title": "Environmental Performance",
    "level": 1,
    "start_page": 24,
    "end_page": 38,
    "subsections": [
      {{
        "section_title": "Climate Change and Emissions",
        "level": 2,
        "start_page": 24,
        "end_page": 30
      }}
    ]
  }}
]"""


SECTION_IDENTIFICATION_BY_INDEX_PROMPT = """You are analysing a sustainability report that has been parsed into structured chunks.
Below is a sequence of text chunks from the report. Page numbers are NOT available, so use chunk index ranges instead.

Your task: Identify the report's structural hierarchy — major sections, subsections, and their boundaries using chunk indices.

Chunks:
{chunks}

Return ONLY valid JSON in this format:
[
  {{
    "section_title": "Environmental Performance",
    "level": 1,
    "start_chunk": 45,
    "end_chunk": 95,
    "subsections": [
      {{
        "section_title": "Climate Change and Emissions",
        "level": 2,
        "start_chunk": 45,
        "end_chunk": 70
      }}
    ]
  }}
]

IMPORTANT: You MUST identify sections. Every sustainability report has identifiable sections (e.g., Governance, Social, Environmental, etc.). Use the chunk text content (headings, topic changes) to determine section boundaries. Return at least 3 sections."""


SECTION_IDENTIFICATION_WINDOW_PROMPT = """You are analysing a PORTION of a sustainability report that has been parsed into structured chunks.
This is chunks {window_start} to {window_end} out of {total_chunks} total chunks in the document.
Page numbers are NOT available, so use chunk index ranges.

Your task: Identify any major section boundaries visible in this portion of the report.
Look for heading text, topic changes, or structural markers that indicate a new section.

Chunks:
{chunks}

Return ONLY valid JSON in this format:
{{
  "sections": [
    {{
      "section_title": "Environmental Performance",
      "level": 1,
      "start_chunk": 450,
      "end_chunk": 620
    }}
  ]
}}

Rules:
- Use ABSOLUTE chunk indices (the indices shown in the data), not relative positions.
- Only identify sections you can clearly see starting or continuing in this window.
- If a section clearly started before this window, include it with start_chunk set to {window_start}.
- If a section extends beyond this window, set end_chunk to {window_end}.
- Focus on top-level sections (level 1). Do NOT include subsections in this pass.
- Return at least 1 section for this window."""


SECTION_MERGE_PROMPT = """You are merging section identification results from multiple windows of a sustainability report.
The report has {total_chunks} chunks total. Multiple passes identified the following sections (some may overlap or be duplicates):

{raw_sections}

Your task:
1. Merge overlapping or duplicate sections (same title or clearly the same section)
2. Ensure section boundaries are continuous with no gaps (every chunk should belong to a section)
3. Order sections by start_chunk
4. Add subsections where the section titles suggest a clear parent-child relationship

Return ONLY valid JSON:
{{
  "sections": [
    {{
      "section_title": "Environmental Performance",
      "level": 1,
      "start_chunk": 0,
      "end_chunk": 150,
      "subsections": [
        {{
          "section_title": "Climate Change and Emissions",
          "level": 2,
          "start_chunk": 0,
          "end_chunk": 80
        }}
      ]
    }}
  ]
}}

IMPORTANT: The sections MUST cover the entire document from chunk 0 to chunk {total_chunks}. No gaps allowed."""


CLAIM_EXTRACTION_PROMPT = """You are an expert sustainability analyst extracting claims from a corporate sustainability report.

A "claim" is any statement where the company asserts:
- A contribution to a sustainability goal or target
- An achievement, metric, or outcome related to ESG performance
- A commitment, target, or plan for sustainability improvement
- An alignment with SDGs, GRI standards, or other sustainability frameworks

DO NOT extract:
- Generic background text about global sustainability challenges
- Descriptions of the SDG framework itself
- Boilerplate language (copyright notices, disclaimers, table of contents)
- Procedural descriptions of the reporting process

Report section: "{section_title}"
Page range: {start_page}–{end_page}

Text content:
{text_content}

For each claim found, return a JSON array:
[
  {{
    "claim_text": "The exact text of the claim, quoted verbatim",
    "claim_type": "achievement" | "commitment" | "metric" | "alignment" | "policy",
    "page": 25,
    "section": "Environmental Performance"
  }}
]

If no claims are found in this section, return an empty array: []
Return ONLY valid JSON, no other text."""


CLAIM_DEDUPLICATION_PROMPT = """You are reviewing a list of extracted sustainability claims from a corporate report.
Some claims may be duplicates or near-duplicates (same claim expressed in slightly different words across sections).

Claims:
{claims_json}

Your task:
1. Identify groups of duplicate/near-duplicate claims
2. For each group, select the most complete version (the one with the most detail)
3. Return the deduplicated list

Return ONLY valid JSON — an array of the retained claims (same format as input), with an added field "duplicate_of" set to null for originals, or the index of the original for removed duplicates.
"""
