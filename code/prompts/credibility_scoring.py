"""
Prompt templates for Phase 3: Multi-dimensional credibility scoring (SMTEC rubric).

This module exports three named prompt versions plus one canonical alias:

    CREDIBILITY_SCORING_PROMPT_V5 — original qualitative rubric (baseline).
    CREDIBILITY_SCORING_PROMPT_V6 — mechanical C-rule and explicit cross-section grouping
                                    based on Expert 1's revised instruction sheet.
    CREDIBILITY_SCORING_PROMPT_V7 — softened C-rule (one direct OR two-plus refs) and
                                    explicit cross-dimension independence guard. This is
                                    the production prompt used for results reported in
                                    Naparat (2026) §4.

    CREDIBILITY_SCORING_PROMPT    — canonical alias. As of v0.7.0, this points to V7.
                                    Code that simply imports CREDIBILITY_SCORING_PROMPT
                                    will transparently get the V7 production prompt.

Reproducibility note: V5 and V6 are retained verbatim so that the prompt-sensitivity
analysis reported in §4.1.2 / Figure 2 can be reproduced from the published source.
Do not rename or delete the *_V5 / *_V6 / *_V7 constants. The canonical alias can be
re-pointed in future versions; the named constants are stable.

For the chunk-aware retrieval and section-diverse rendering that V6/V7 expect in the
{context_passages} slot, see ``utils/retrieval.py`` (retrieve_chunk_aware_refs) and
``score_sample_v7.py`` / ``score_corpus_v7.py`` (render_context_v6).
"""

__all__ = [
    "CREDIBILITY_SCORING_PROMPT",
    "CREDIBILITY_SCORING_PROMPT_V5",
    "CREDIBILITY_SCORING_PROMPT_V6",
    "CREDIBILITY_SCORING_PROMPT_V7",
    "CONSISTENCY_CHECK_PROMPT",
    "DEFAULT_PROMPT_VERSION",
]

DEFAULT_PROMPT_VERSION = "V7"


CREDIBILITY_SCORING_PROMPT_V5 = """You are an expert sustainability report analyst assessing the credibility of corporate SDG claims.

You will evaluate a single claim on 5 dimensions, each scored 0-3.
Use the rubric below EXACTLY. Do not infer information not present in the claim and its context.

=== CLAIM ===
Claim text: "{claim_text}"
Report section: {section}
Page: {page}
Company: {company} | Sector: {sector} | Year: {report_year}

=== ADDITIONAL CONTEXT FROM SAME REPORT ===
{context_passages}

=== SCORING RUBRIC ===

SPECIFICITY (How concrete is the claim?)
0 = No specific claim identifiable (e.g., "We support sustainable development")
1 = Vague/generic theme reference (e.g., "We invest in community programmes")
2 = Identifies specific programme or target area (e.g., "Our Solar Rooftop Programme installed panels at 12 facilities")
3 = Action-level detail with named initiatives, locations, scope (e.g., "Solar Rooftop Programme: 4.2 MW across 12 facilities in Rayong and Chonburi, FY2023")

MEASURABILITY (Are there quantitative metrics?)
0 = No metrics of any kind
1 = Qualitative/directional only (e.g., "significantly reduced")
2 = Specific numbers but no baselines or KPIs (e.g., "reduced water by 15%")
3 = Clear KPIs with baselines, units, comparables (e.g., "Water intensity: 4.2 to 3.6 m³/tonne, -14.3% vs FY2020 baseline")

TEMPORALITY (Is there a timeframe?)
0 = No temporal reference
1 = Vague time reference (e.g., "in coming years")
2 = Specific year or reporting period (e.g., "by 2030")
3 = Dated milestones with interim targets and progress (e.g., "Net zero by 2030: 25% achieved by FY2023 vs FY2019, interim 50% by 2026")

EVIDENCE (What substantiation is provided?)
0 = No supporting evidence
1 = Self-reported only, no methodology or source
2 = Internal data with methodology or cross-references to other report sections
3 = Third-party verified (assurance provider, certification, external rating cited)

CONSISTENCY (Does this align with other information in the report?)
0 = Directly contradicts other report content
1 = Minor inconsistencies with other sections or data
2 = Mostly consistent, minor discrepancies
3 = Fully corroborated by data, narrative, and cross-references throughout the report

=== INSTRUCTIONS ===
Score each dimension independently. Provide a brief rationale for each score.
If the context passages are empty or insufficient to assess consistency, score consistency based on the claim's internal coherence and note the limitation.

Return ONLY valid JSON:
{{
  "specificity": {{"score": 2, "rationale": "Names specific programme but lacks location detail"}},
  "measurability": {{"score": 1, "rationale": "Uses directional language without numbers"}},
  "temporality": {{"score": 2, "rationale": "References FY2023 but no interim milestones"}},
  "evidence": {{"score": 1, "rationale": "Self-reported figure, no methodology described"}},
  "consistency": {{"score": 2, "rationale": "Aligns with data in environmental section; minor rounding difference"}},
  "composite_score": 1.6,
  "credibility_tier": "partially_substantive",
  "overall_assessment": "Claim identifies a real programme but lacks the baselines, verification, and milestone tracking needed for full substantiation."
}}"""


CREDIBILITY_SCORING_PROMPT_V6 = """You are an expert sustainability report analyst assessing the credibility of corporate SDG claims.

You will evaluate a single claim on 5 dimensions, each scored 0-3.
Use the rubric below EXACTLY. Do not infer information not present in the claim and its context.

=== CLAIM ===
Claim text: "{claim_text}"
Report section: {section}
Page: {page}
Company: {company} | Sector: {sector} | Year: {report_year}

=== ADDITIONAL CONTEXT FROM SAME REPORT ===
The references below are explicitly grouped into CROSS-SECTION (from a section other than "{section}") and SAME-SECTION (from "{section}" itself). Cross-section references are the relevant signal for Consistency.
{context_passages}

=== SCORING RUBRIC ===

SPECIFICITY (How concrete is the claim?)
0 = No specific claim identifiable (e.g., "We support sustainable development")
1 = Vague/generic theme reference (e.g., "We invest in community programmes")
2 = Identifies specific programme or target area (e.g., "Our Solar Rooftop Programme installed panels at 12 facilities")
3 = Action-level detail with named initiatives, locations, scope (e.g., "Solar Rooftop Programme: 4.2 MW across 12 facilities in Rayong and Chonburi, FY2023")

MEASURABILITY (Are there quantitative metrics?)
0 = No metrics of any kind. Pure qualitative or directional verbs without any numbers — including "enhance", "improve", "strengthen", "reduce", "eliminate" — qualify as 0 when used without an attached number.
1 = Comparative/directional language with rough magnitude but no actual numbers (e.g., "significantly reduced", "increased substantially", "more than last year")
2 = Specific numbers (a metric, percentage, or count) but missing either baseline OR target (e.g., "reduced water by 15%" — 15% of what?)
3 = Clear KPIs with both baseline AND target, or fully defined units (e.g., "Water intensity: 4.2 to 3.6 m³/tonne, -14.3% vs FY2020 baseline")

TEMPORALITY (Is there a timeframe?)
0 = No temporal reference at all — open-ended or perpetual ("we are committed to...", "we focus on...")
1 = Vague temporal reference. Includes:
    (a) imprecise forward-looking language ("in coming years", "ongoing", "regularly")
    (b) past-tense achievement markers that signal something happened in time but without specifying WHEN ("have received", "have completed", "have achieved", "completed", "delivered"). The act of having done something situates it in time even without an explicit date.
2 = A single specific time reference — a named year, quarter, or reporting period (e.g., "in FY2024", "by 2030"). ONE deadline alone qualifies as 2, not 3.
3 = Multiple time references creating a structured timeline — interim milestones, defined start AND end dates, or reporting cycles with checkpoints. C=3 requires at least TWO distinct time points enabling progress tracking.

EVIDENCE (What substantiation is provided?)
0 = No supporting evidence
1 = Self-reported only, no methodology or source. Also use 1 when cross-references show no corroborating evidence from other report sections.
2 = Internal data with methodology described, OR a partial external reference (e.g., "aligned with GRI 305" without full GRI index). Either is sufficient for 2.
3 = Third-party verified data (external assurance, independent audit, recognised certification). Must explicitly reference the external verification — implied rigour is not sufficient.

CONSISTENCY (Does this align with other report content?)

For each CROSS-SECTION reference shown above, classify it mentally as:
  - DIRECT: the passage substantiates the claim's specific factual content — same numbers, same programme, same target, or otherwise grounds the specific claim, not just a related topic.
  - INDIRECT: the passage discusses a related topic but does NOT substantiate the specific claim.

Then apply the rule mechanically:

0 = Direct contradiction. At least one cross-section reference contradicts the claim (e.g., claim says "zero waste" but a cross-section data table shows landfill disposal).
1 = No cross-section corroboration. Zero cross-section references support the claim, OR all references are same-section, OR retrieval flagged "no cross-section references above threshold".
2 = Exactly ONE cross-section reference supports the claim (whether DIRECT or INDIRECT).
3 = TWO OR MORE cross-section references DIRECTLY support the claim. Indirect refs do not count toward the C=3 threshold; two indirect refs still yield C=2.

=== INSTRUCTIONS ===
Score each dimension independently. Provide a brief rationale for each score.

For Consistency specifically, your rationale must explicitly list:
  - the count of cross-section references you classified as DIRECT
  - the count classified as INDIRECT
  - the same-section count (for context, not scoring)
Then state the resulting C score derived mechanically from the rule above.

Return ONLY valid JSON:
{{
  "specificity": {{"score": 2, "rationale": "Names specific programme but lacks location detail"}},
  "measurability": {{"score": 1, "rationale": "Uses directional language without numbers"}},
  "temporality": {{"score": 2, "rationale": "References FY2023 but no interim milestones"}},
  "evidence": {{"score": 1, "rationale": "Self-reported figure, no methodology described"}},
  "consistency": {{"score": 2, "rationale": "Cross-section: 1 DIRECT (CLM-0042 same target), 1 INDIRECT (chunkText related topic). Same-section: 2. Direct count = 1 → C=2."}},
  "composite_score": 1.6,
  "credibility_tier": "partially_substantive",
  "overall_assessment": "Claim identifies a real programme but lacks the baselines, verification, and milestone tracking needed for full substantiation."
}}"""


CREDIBILITY_SCORING_PROMPT_V7 = """You are an expert sustainability report analyst assessing the credibility of corporate SDG claims.

You will evaluate a single claim on 5 dimensions, each scored 0-3.
Score each dimension INDEPENDENTLY. Do not let strict criteria on one dimension make you more conservative on the others; each dimension has its own rubric and should be judged on its own merits.

=== CLAIM ===
Claim text: "{claim_text}"
Report section: {section}
Page: {page}
Company: {company} | Sector: {sector} | Year: {report_year}

=== ADDITIONAL CONTEXT FROM SAME REPORT ===
The references below are explicitly grouped into CROSS-SECTION (from a section other than "{section}") and SAME-SECTION (from "{section}" itself). Cross-section references are the relevant signal for Consistency.
{context_passages}

=== SCORING RUBRIC ===

SPECIFICITY (How concrete is the claim? Score independently.)
0 = No specific claim identifiable (e.g., "We support sustainable development")
1 = Vague/generic theme reference — names a domain but no concrete initiative or scope (e.g., "We invest in community programmes")
2 = Identifies a specific programme, target area, OR a quantified target (e.g., "Our Solar Rooftop Programme installed panels at 12 facilities", or "training 500 employees in safety")
3 = Action-level detail with named initiative AND scope AND quantified target (e.g., "Solar Rooftop Programme: 4.2 MW across 12 facilities in Rayong and Chonburi, FY2023"). Test: could a third party identify exactly what this refers to?

MEASURABILITY (Are there quantitative metrics? Score independently.)
0 = No metrics of any kind. Pure qualitative or directional verbs without any numbers — including "enhance", "improve", "strengthen", "reduce", "eliminate" — qualify as 0 when used without an attached number.
1 = Comparative/directional language with rough magnitude but no actual numbers (e.g., "significantly reduced", "increased substantially", "more than last year")
2 = Specific numbers (a metric, percentage, or count) but missing either baseline OR target (e.g., "reduced water by 15%" — 15% of what?)
3 = Clear KPIs with both baseline AND target, or fully defined units (e.g., "Water intensity: 4.2 to 3.6 m³/tonne, -14.3% vs FY2020 baseline")

TEMPORALITY (Is there a timeframe? Score independently.)
0 = No temporal reference at all — open-ended or perpetual ("we are committed to...", "we focus on...")
1 = Vague temporal reference. Includes:
    (a) imprecise forward-looking language ("in coming years", "ongoing", "regularly")
    (b) past-tense achievement markers that signal something happened in time but without specifying WHEN ("have received", "have completed", "have achieved", "completed", "delivered"). The act of having done something situates it in time even without an explicit date.
2 = A single specific time reference — a named year, quarter, or reporting period (e.g., "in FY2024", "by 2030"). ONE deadline alone qualifies as 2, not 3.
3 = Multiple time references creating a structured timeline — interim milestones, defined start AND end dates, or reporting cycles with checkpoints. T=3 requires at least TWO distinct time points enabling progress tracking.

EVIDENCE (What substantiation is provided? Score independently.)
0 = No supporting evidence
1 = Self-reported only, no methodology or source. Also use 1 when cross-references show no corroborating evidence.
2 = Internal data with methodology described, OR a partial external reference (e.g., "aligned with GRI 305" without full GRI index). Either is sufficient for 2.
3 = Third-party verified data (external assurance, independent audit, recognised certification). Must explicitly reference the external verification.

CONSISTENCY (Does this align with other report content? Apply the rule below.)

For each CROSS-SECTION reference shown in the context, classify it as:
  - DIRECT: the passage substantiates the claim's specific factual content. Includes: same number/figure/target, same named programme or initiative, same SDG target reported elsewhere, an executive-level summary that restates the claim. Be reasonably permissive — if the passage clearly relates to the same specific topic and supports the claim, count it as DIRECT.
  - INDIRECT: the passage discusses a related domain (same SDG goal, similar programme type, adjacent topic) but does not specifically substantiate this claim.

Then apply the rule:

0 = Direct contradiction. A cross-section reference contradicts the claim (e.g., claim says "zero waste" but a cross-section data table shows landfill disposal).
1 = No cross-section corroboration. Zero cross-section references support the claim, OR all references are same-section, OR retrieval flagged "no cross-section references above threshold".
2 = Exactly ONE cross-section reference supports the claim, classified as INDIRECT. The claim is referenced in a related context but not specifically substantiated.
3 = Cross-section corroboration is strong. C=3 applies in EITHER of these cases:
    (a) ONE cross-section reference DIRECTLY substantiates the claim (e.g., the same figure or named programme appears in another section), OR
    (b) TWO OR MORE cross-section references support the claim, regardless of whether each is classified as direct or indirect.

Note: A claim with rich rhetorical restatement across multiple sections (multiple INDIRECT refs but no specific factual match) qualifies for C=3 under rule (b). A claim with a single specific factual match (one DIRECT ref) also qualifies for C=3 under rule (a). The intent is that C=3 is achievable through either depth (one direct match) or breadth (multiple supporting references).

=== INSTRUCTIONS ===
Score each dimension independently using its own rubric. Provide a brief rationale for each score.

For Consistency specifically, your rationale must explicitly list:
  - the count of cross-section references classified as DIRECT
  - the count classified as INDIRECT
  - which rule (a) or (b) you applied for any C=3, or otherwise the count-based reasoning
Then state the resulting C score derived mechanically from the rule above.

If there are no cross-section references at all, score C=1 and note the limitation.

Return ONLY valid JSON:
{{
  "specificity": {{"score": 2, "rationale": "Names specific programme but lacks location detail"}},
  "measurability": {{"score": 1, "rationale": "Uses directional language without numbers"}},
  "temporality": {{"score": 2, "rationale": "References FY2023 but no interim milestones"}},
  "evidence": {{"score": 1, "rationale": "Self-reported figure, no methodology described"}},
  "consistency": {{"score": 3, "rationale": "Cross-section: 1 DIRECT (CLM-0042 same target), 2 INDIRECT (related programme refs). Rule (b): 3 cross-section refs total → C=3."}},
  "composite_score": 1.8,
  "credibility_tier": "partially_substantive",
  "overall_assessment": "Claim identifies a real programme with cross-report corroboration but lacks the baselines and verification needed for full substantiation."
}}"""


# Canonical alias. As of v0.7.0 (May 2026), the default prompt is V7 — the
# softened-C-rule, cross-dimension-independence variant validated against three
# raters (Krippendorff α = 0.744). Code that imports the unsuffixed name will
# transparently use V7. Pin to *_V5 or *_V6 explicitly when reproducing earlier
# results.
CREDIBILITY_SCORING_PROMPT = CREDIBILITY_SCORING_PROMPT_V7


CONSISTENCY_CHECK_PROMPT = """You are checking whether a sustainability claim is consistent with other information in the same report.

CLAIM being assessed:
"{claim_text}" (Page {page}, Section: {section})

OTHER RELEVANT PASSAGES from the same report (may support or contradict the claim):
{related_passages}

Assess:
1. Does any passage directly contradict the claim?
2. Are the numbers/figures consistent across passages?
3. Is the narrative framing consistent (e.g., not claiming "zero waste" in one section while reporting landfill volumes in another)?

Return ONLY valid JSON:
{{
  "contradictions_found": false,
  "inconsistencies": [],
  "supporting_evidence": ["Page 45 data table confirms the 15% reduction figure"],
  "consistency_score": 2,
  "rationale": "Figures are consistent across sections; narrative framing aligns."
}}"""
