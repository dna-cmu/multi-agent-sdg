# How the author audits will be scored — fixed before any audit workbook is opened (16 Nov 2026)

Written while the audit workbooks are still with the two auditors (DNA, EE) and the keys in `_keys-do-not-open/` are unopened. The purpose is that the measures below are not chosen after seeing results (Reviewer 3, point 4).

For every audit: the two auditors' answers are compared first (agreement: percentage and Cohen's κ for categorical answers), disagreements are listed and resolved by discussion, and results are reported both per auditor and after resolution. Blank answers are reported as missing, never filled in. 95% intervals are Wilson intervals for proportions.

1. **Extraction (Audit 1).** Precision = share of sampled extracted claims judged a valid SDG-related claim unit. Recall = share of auditor-marked claims on the sampled spans that the extractor captured. Boundary errors and the error types named in the workbook are tabulated. Reported by report where n allows.
2. **SDG mapping (Audit 2).** Precision = share of sampled claim–target pairs judged correct, at target level and at goal level. Missed goals = share of sampled claims for which the auditor names a goal the mapper did not assign (reported separately for claims with one, two and three assigned goals).
3. **Declared priorities (Audit 3).** For each of the 30 reports: agreement between the detector's 17-goal vector and the auditor's reading; cells in error are counted in both directions (declared but not detected; detected but not declared). The firm–goal results (§4.7) are recomputed with the corrected matrix and both versions are reported.
4. **Excluded claims (Audit 4).** Share of the sampled unmapped claims judged (a) correctly excluded, (b) mappable to a goal. If (b) exceeds 10%, the corpus distribution is re-estimated under the assumption that the same share of all 611 excluded claims is mappable, and the range is reported.
5. **End-to-end trace (Audit 5).** For each traced claim: whether extraction, mapping, retrieval and the page location are each correct; the share of claims with no error at any stage; and where the first error occurs.

Nothing in the instrument (prompt, retrieval, aggregation, thresholds) is changed in response to audit results. Corrections to the declaration matrix are data corrections and are reported with before/after results.

## Addendum, 23 Nov 2026 — matching rule for Audit 1 (written before any key or extractor output for the audited spans was opened)
Auditor rows are not always one sentence, and copied text can carry small errors (a missing first letter, a typo). Matching is therefore by wording, not exact string:
- Text is lower-cased, punctuation and line breaks removed, and split into words.
- An extracted claim **matches** an auditor row when at least 60% of the extracted claim's words (ignoring words of one or two letters) occur in that row, on the same PDF page or the page before or after it.
- One auditor row may match several extracted claims (a row that holds several sentences); one extracted claim counts once even if it matches several rows.
- Recall = auditor rows matched by at least one extracted claim ÷ all auditor rows. Precision = extracted claims on the span that match an auditor row ÷ all extracted claims on the span. Extracted claims with no match are listed and classified by the two auditors after the keys are opened (not a claim / claim the auditor missed / text inside an image / boundary error); that classification is reported separately from the matching result.
- Sensitivity: the same figures at thresholds of 50% and 70%.

## Addendum, 24 Nov 2026 — Audit 3 scored two ways (agreed by DNA before the key was opened)
Some reports present all or most SDGs and mark a few as the main focus (wording such as "major" and "minor", or larger icons). The auditor's list can therefore be read in two ways, and both are scored:
- **Broad:** every goal the auditor listed for the report.
- **Strict:** only the goals the auditor marks in the note column as the report's top level ("major", "main focus" or the larger icons). Where the auditor notes no distinction, the strict set equals the full list.
For each reading: agreement between the detector's 17-goal vector and the auditor's, cells in error in both directions, and the firm–goal results (§4.7) recomputed with the auditor's matrix. Repeated goal numbers count once. A report the auditor states declares none is scored as an empty set, not as missing. Which reading is reported as the main one is not chosen after the key is opened: the strict reading is the main one, because the task asks for goals presented as priorities; the broad reading is the sensitivity.

## Addendum, 24 Nov 2026 — Audit 6: blinded claim / not-claim judgement in pairs (written before the form was opened by either auditor)
Why added. Audit 1 (exhaustive listing on 12 pages) was scored for DNA on 24 Nov and found 4 of 30 auditor claims captured. DNA considers that an exhaustive listing depends heavily on one reader who is not an SDG specialist, and proposed a judgement test. Audit 1 is still reported. Audit 6 is an additional audit, designed after Audit 1's result was known; the paper says so.
Design. 90 sentences, 30 from each of three sources, drawn with seed 20261124 from 28 reports (BDMS and DELTA, the Audit 1 reports, are excluded), one per report per source and two more at random:
- E: claims the extractor produced.
- N: sentences the extractor did not take that lie inside the stretch of text spanned by one section's extracted claims (text it certainly read).
- F: sentences it did not take that lie more than 12,000 characters from the first extracted claim of every section (text it very probably never read).
Sentences are shuffled and shown in 45 random pairs with no indication of source. The auditor answers A, B, Both or Neither using the definition in the extraction prompt, quoted word for word in the form. Builder: build_audit6_pairs.py. The key (source of each sentence) is in _keys-do-not-open/ and is not opened by anyone, Claude included, until an auditor's form is final and frozen.
Scoring. Each answer gives two judgements (claim / not claim). Reported with Wilson 95% intervals:
- Precision of extraction = share of E sentences judged a claim.
- Claims passed over in text that was read = share of N sentences judged a claim.
- Claims in text that was not read = share of F sentences judged a claim.
- Blank rows are missing, not imputed. With two auditors: agreement (percentage and κ) on the 90 judgements first, then results per auditor and after resolution.
- No estimate of overall recall is computed from these three shares unless the number of candidate sentences per source in the corpus is also reported with it (pool sizes at build time: E 6,060; N 6,127; F 13,431, after the filters in the builder).
Interpretation fixed in advance: if the share judged a claim in F is close to that in E, the cut at 12,000 characters removed material of the same kind as what was kept; if it is close to that in N, the unread text is mostly not claims.
