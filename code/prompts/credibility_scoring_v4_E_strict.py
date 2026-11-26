"""Stricter Evidence reading for the pre-registered SENSITIVITY analysis (Reviewer 3, point 3). NOT the instrument.

Frozen V4 (credibility_scoring_v4.py) stays the primary instrument and is not modified. This file derives a variant
of the V4 prompt by three explicit text replacements in the Evidence section, so the difference is exactly what is
listed in REPLACEMENTS: a standard reference alone, with or without its number (e.g. "aligned with GRI 305"),
scores 1; it scores 2 only when the scope of the data or the location of the data in the report is also given.
Everything else in the prompt is identical. Only the E score from this variant is used.
"""
from prompts.credibility_scoring_v4 import CREDIBILITY_SCORING_PROMPT_V4, SYSTEM_MESSAGE_V4

PROMPT_VERSION_V4_E_STRICT = "V4-E-strict-sensitivity-2026-11-10"
REPLACEMENTS = [
    ("1 = Self-reported with figures, but no method of collection and no source; OR a standard is named without its number, scope or data location.",
     "1 = Self-reported with figures, but no method of collection and no source; OR a standard is named, with or without its number, without the scope of the data or the data location."),
    ("2 = Discloses the method of data collection or analysis, the reporting scope, the source of the data, or conformity with a standard that is identified by its number or scope or by where the data sit in the report. (e.g., sample size, measurement protocol, standard number such as GRI 305 or GRI 305-1, calculation method)",
     "2 = Discloses the method of data collection or analysis, the reporting scope, the source of the data, or conformity with a standard together with the scope of the data or where the data sit in the report. (e.g., sample size, measurement protocol, calculation method)"),
    ("- A standard named without its number (e.g., \"in line with GRI\") = 1. It rises to 2 if at least one of these is given: (a) the scope of the data or the standard's number - what the data cover, e.g. the specific disclosure (GRI 305 or GRI 305-1), the units or areas covered (all plants in Thailand), or the period (2024); or (b) where the data are in the report - page, table, or the GRI content index entry for these data.",
     "- A standard named, with or without its number (e.g., \"in line with GRI\", \"aligned with GRI 305\" or \"GRI 305-1\") = 1: a reference to a standard is not by itself evidence for the claim. It rises to 2 only if at least one of these is also given: (a) the scope of the data - the units or areas covered (all plants in Thailand) or the period (2024); or (b) where the data are in the report - page, table, or the GRI content index entry for these data."),
]
CREDIBILITY_SCORING_PROMPT_V4_E_STRICT = CREDIBILITY_SCORING_PROMPT_V4
for old, new in REPLACEMENTS:
    assert CREDIBILITY_SCORING_PROMPT_V4_E_STRICT.count(old) == 1, old[:60]
    CREDIBILITY_SCORING_PROMPT_V4_E_STRICT = CREDIBILITY_SCORING_PROMPT_V4_E_STRICT.replace(old, new)
__all__ = ["CREDIBILITY_SCORING_PROMPT_V4_E_STRICT", "SYSTEM_MESSAGE_V4", "PROMPT_VERSION_V4_E_STRICT", "REPLACEMENTS"]
