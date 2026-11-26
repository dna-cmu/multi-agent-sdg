# Extraction re-run without the 12,000-character cut — PRELIMINARY results (26 Nov 2026)

Plan fixed before the run: PRESPEC-extraction-rerun-26Nov2026.md. Not yet in the paper. Scoring: frozen Version 4. "Original" = the 6,320 scored claims of the paper; "newly captured" = claims the re-run extracted that match no original claim.

## A. Coverage and recall of the re-run extraction
- 2,361 windows over the stored text of the 30 reports (25.4 million characters); every call ended normally; model snapshot gpt-4o-2024-08-06.
- Claims: 16,475 after removing exact duplicates, against 6,936 in the original run (median ratio per report 2.3; two reports, Siam Commercial Bank and Thai Union, gave slightly fewer than before).
- Already extracted: 4,377 of the 16,475 (27%). Newly captured: 12,098.
- Repeatability of extraction: only 4,289 of the 6,936 original claims (62%) were found again. The extraction step does not return the same claims twice, even on text it read both times.
- Pair audit (resolved judgements of the two authors; captured by the re-run / total): sentences judged claims 28 of 61 (46%): previously extracted 18 of 25; previously passed over in text that was read 4 of 20; in text previously not read 6 of 16. Sentences judged not claims: 5 of 24 extracted (21%).
- Auditor 1's listing on 12 pages: 16 of 30 listed claims captured (original run: 4 of 30).
Reading: removing the cut more than doubles the number of claims and raises recall on the 12 audited pages from 13% to 53%. It does not make extraction complete or stable: the model still passes over most claims it passed over before (4 of 20), and it drops about a third of what it took the first time.

## B. Newly captured claims (random sample of 1,000) against the original claims
- Mapped to at least one SDG target: 918 of 1000 (91.8%); original run 6,325 of 6,936 (91.2%). Scored completely: 915.

| SMTE tier | original (n = 6320) | newly captured (n = 915) | 95% interval | difference |
|---|---|---|---|---|
| unsubstantiated | 37.5% | 31.4% | 28.4–34.4 | -6.1 |
| partially | 53.1% | 58.3% | 55.1–61.4 | +5.1 |
| substantiated | 9.4% | 10.4% | 8.5–12.2 | +1.0 |

| mean | original | newly captured | 95% interval | difference |
|---|---|---|---|---|
| S | 1.56 | 1.63 | 1.59–1.68 | +0.08 |
| M | 0.85 | 0.89 | 0.82–0.95 | +0.04 |
| T | 0.84 | 0.95 | 0.89–1.00 | +0.11 |
| E | 1.22 | 1.29 | 1.25–1.33 | +0.07 |
| C | 0.49 | 0.29 | 0.25–0.32 | -0.21 |
| SMTE | 1.12 | 1.19 | 1.16–1.22 | +0.07 |

| claim type | original share | new share | original mean SMTE | new mean SMTE | new n |
|---|---|---|---|---|---|
| commitment | 46.9% | 41.6% | 0.94 | 0.95 | 381 |
| achievement | 19.9% | 20.9% | 1.37 | 1.41 | 191 |
| metric | 16.1% | 23.6% | 1.52 | 1.53 | 216 |
| policy | 10.6% | 8.5% | 0.85 | 0.95 | 78 |
| alignment | 4.5% | 4.7% | 0.88 | 0.95 | 43 |
| target | 1.6% | 0.5% | 1.55 | 1.70 | 5 |

- Environmental minus social goal means, as pre-specified (6, 7, 12–15): original +0.18, newly captured +0.04.
- Environmental minus social goal means, as in the paper (6, 7, 11–15): original +0.17, newly captured +0.02.
  (The pre-specification left goal 11 out of the environmental group by mistake; the paper includes it. Both are shown.)

## C. Combined estimate: tier shares if every newly captured claim had been scored
Newly captured claims: 12,098; estimated mapped and scorable among them: 11,103. Combined with the 6,320 original claims:

| SMTE tier | published | combined estimate | 95% interval | difference |
|---|---|---|---|---|
| unsubstantiated | 37.5% | 33.4% | 31.5–35.4 | -4.1 |
| partially | 53.1% | 56.9% | 54.9–58.9 | +3.8 |
| substantiated | 9.4% | 9.7% | 8.5–10.9 | +0.3 |

## Pre-specified reading
| criterion | met | detail |
|---|---|---|
| (i) each combined tier share within 5 points of the published share | yes | largest difference 4.1 points |
| (ii) Measurability and Temporality the two lowest dimension means among newly captured claims | yes | lowest two: M, T |
| (iii) claim-type ordering: Spearman correlation at least 0.8 (types with at least 30 new claims) | yes | rho = 0.90 over 5 types |
| (iv) environmental minus social difference has the same sign | yes | see above |

## D. Two reports with every newly captured claim scored (illustration, not a test)

**PTT Global Chemical** — declared priorities (authors, resolved): [6, 9, 12, 13, 17]. Original scored claims 143; newly captured 315, mapped 276, scored 276. SMTE tiers (unsub / partial / sub): original 36% / 50% / 15%; newly captured 41% / 48% / 11%.

| cells with ≥ 3 claims | set | cells | Rule A (mean ≥ 2.0) | Rule B (≥ 1 substantiated) | Rule B (≥ 3) | mean of cell means |
|---|---|---|---|---|---|---|
| declared | original claims | 5 | 0 | 5 | 5 | 1.26 |
| undeclared | original claims | 9 | 1 | 5 | 5 | 1.27 |
| declared | original + newly captured | 5 | 0 | 5 | 5 | 1.12 |
| undeclared | original + newly captured | 11 | 0 | 8 | 7 | 1.13 |
Declared goals after adding the new claims: SDG 6: 17 claims, mean 1.21, 4 substantiated; SDG 9: 164 claims, mean 1.03, 11 substantiated; SDG 12: 205 claims, mean 1.10, 24 substantiated; SDG 13: 166 claims, mean 1.12, 14 substantiated; SDG 17: 58 claims, mean 1.13, 9 substantiated

**Siam Cement Group** — declared priorities (authors, resolved): [6, 7, 8, 9, 12, 13, 14, 15, 17]. Original scored claims 122; newly captured 518, mapped 503, scored 500. SMTE tiers (unsub / partial / sub): original 38% / 52% / 11%; newly captured 33% / 58% / 9%.

| cells with ≥ 3 claims | set | cells | Rule A (mean ≥ 2.0) | Rule B (≥ 1 substantiated) | Rule B (≥ 3) | mean of cell means |
|---|---|---|---|---|---|---|
| declared | original claims | 8 | 0 | 6 | 4 | 1.12 |
| undeclared | original claims | 5 | 0 | 1 | 0 | 0.91 |
| declared | original + newly captured | 9 | 0 | 9 | 8 | 1.21 |
| undeclared | original + newly captured | 8 | 0 | 6 | 4 | 1.17 |
Declared goals after adding the new claims: SDG 6: 39 claims, mean 1.27, 6 substantiated; SDG 7: 101 claims, mean 1.38, 20 substantiated; SDG 8: 180 claims, mean 1.12, 13 substantiated; SDG 9: 172 claims, mean 1.12, 9 substantiated; SDG 12: 321 claims, mean 1.18, 33 substantiated; SDG 13: 252 claims, mean 1.24, 34 substantiated; SDG 14: 18 claims, mean 1.50, 3 substantiated; SDG 15: 71 claims, mean 1.18, 6 substantiated; SDG 17: 80 claims, mean 0.91, 1 substantiated

## Notes for interpretation
- Corroboration count C is lower for newly captured claims (0.29 against 0.49). The section labels of re-extracted claims come from the chunk-to-section lookup and not from the original section pass, which changes what counts as "another section"; C is therefore not comparable between the two sets and SMTE (which excludes C) is the comparison to rely on.
- Criterion (iv) is met only in the sense fixed in advance (same sign). Among newly captured claims the environmental minus social difference is +0.02 to +0.04, against +0.17 to +0.18 in the original claims. The paper's statement that environmental goals score somewhat higher is not supported in the newly captured claims.
- Five of 1,635 selected mapped claims could not be scored after three attempts (same rule as the corpus run).
- Cost (token counts recorded per call, priced at US$2.50 / US$10.00 per million input / output tokens, which should be checked against the account): extraction US$31.24 (8.09M in, 1.10M out); mapping US$13.28 (2.06M in, 0.81M out, 5,653 calls); scoring not metered per call, about US$54 at the corpus run's US$33 per 1,000 claims; embeddings under US$1. Total about US$99; ceiling US$150.
- Stored: every raw extraction response (windows.jsonl), the de-duplicated claims with the already/new flag, the selection, mappings and scores, in sdg-credibility-framework/data/outputs/revision/extraction_rerun/ (copy of revision/extraction-rerun/work/). New embedding caches were written under a new key; no existing file was changed.

# Further checks (addendum E to H) — PRELIMINARY

## E. Repeatability of extraction (identical settings and windows, run twice)
- Pass 1: 16,475 claims; pass 2: 16,508 claims.
- Pass-1 claims found again in pass 2: 15,311 (93%); pass-2 claims found in pass 1: 15,302 (93%).
- Union of the two passes: about 17,681 distinct claims (7% more than one pass).
- Original 6,936 claims found again: in pass 1 61%, in pass 2 61%, in either 65%, in both 58%.

| pair-audit sentences (resolved) | n | captured: pass 1 | pass 2 | either pass |
|---|---|---|---|---|
| claims, previously extracted | 25 | 18 | 17 | 18 |
| claims, previously passed over in text that was read | 20 | 4 | 5 | 5 |
| claims, in text previously not read | 16 | 6 | 7 | 7 |
| all claims | 61 | 28 | 29 | 30 |
| all sentences judged not claims | 24 | 5 | 4 | 5 |

- Auditor 1's 30 listed claims captured: pass 1 16, pass 2 16, either 16 (original run 4).

## F. Original claims found again against those not found again (existing Version 4 scores)
| group | n | SMTE tiers unsub / partial / sub (%) | S | M | T | E | SMTE | commitment | achievement | metric | policy | alignment |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| found again (pass 1) | 3940 | 29.4 / 58.9 / 11.7 | 1.64 | 0.99 | 0.98 | 1.23 | 1.21 | 44% | 23% | 18% | 9% | 4% |
| not found again | 2380 | 50.9 / 43.6 / 5.5 | 1.43 | 0.60 | 0.60 | 1.20 | 0.96 | 51% | 16% | 13% | 14% | 5% |
| found in both passes | 3711 | 28.9 / 59.0 / 12.2 | 1.64 | 1.01 | 1.00 | 1.24 | 1.22 | 43% | 23% | 18% | 9% | 4% |
- Share found again by claim type: commitment 59% (n = 2963); achievement 71% (n = 1258); metric 70% (n = 1018); policy 51% (n = 667); alignment 56% (n = 283); target 81% (n = 103).

## G. Repeatability of mapping (300 original claims mapped again)
- Mapped to at least one goal: first time 279, second time 276, both times 276; same mapped / not mapped status for 297 of 300.
- Identical set of goals: 240 of 300 (80%); at least one goal in common among claims mapped both times: 276 of 276.
- Goals per claim: 2.10 and 2.18; goal assignments kept: 603 of 630 (96%). Claim × goal cells: agreement 98.5%, Cohen’s κ 0.93.

## H. Environmental (6, 7, 11–15) against social (1–5, 8, 10, 16) goal means
| | original: env | soc | difference | newly captured: env | soc | difference |
|---|---|---|---|---|---|---|
| unstandardised | 1.19 | 1.02 | +0.17 | 1.18 | 1.16 | +0.02 |
| standardised for claim type | 1.17 | 1.03 | +0.14 | 1.15 | 1.11 | +0.04 |
- Goal means, original → newly captured (n in sample): SDG 1: 0.98 → 1.05 (15); SDG 2: 1.08 → 1.11 (27); SDG 3: 1.07 → 1.28 (123); SDG 4: 1.14 → 1.31 (84); SDG 5: 0.91 → 1.25 (33); SDG 6: 1.17 → 1.26 (41); SDG 7: 1.26 → 1.21 (107); SDG 8: 1.04 → 1.21 (312); SDG 9: 1.08 → 1.10 (233); SDG 10: 0.93 → 0.97 (48); SDG 11: 1.11 → 1.05 (112); SDG 12: 1.12 → 1.19 (364); SDG 13: 1.20 → 1.21 (238); SDG 14: 1.29 → 1.17 (25); SDG 15: 1.17 → 1.13 (76); SDG 16: 1.00 → 1.08 (178); SDG 17: 0.99 → 1.07 (81).
## Corrections and reading after checks E to H
- CORRECTION to part A and to the note above: the 62% of original claims "found again" is not run-to-run instability. With identical settings and windows the extraction step returns 93% of the same claims (check E). The 62% reflects the different way the text was divided: the original run read each section's first 12,000 characters as the section pass defined them; the re-run reads the stored text in consecutive windows. The statement "the extraction step does not return the same claims twice" is withdrawn. The accurate statement is: extraction is repeatable under identical input, and sensitive to how the text is divided.
- A second pass adds little (7% more claims) and does not raise recall on the audited sentences (28, 29, and 30 of 61 for pass 1, pass 2 and either). The claims the extractor passes over are passed over consistently; taking the union of several passes is not a remedy.
- Check F: the original claims that the re-run did not take again (38%) score clearly lower than those it did (mean SMTE 0.96 against 1.21; 50.9% against 29.4% unsubstantiated) and contain more commitments and policies. The claims whose extraction depends on how the text is divided are disproportionately the vague ones.
- Consequence, not pre-specified: the claim set of the re-run alone (already extracted plus newly captured, the original-only claims left out) would give tier shares of about 31 / 58 / 11, against the published 37.5 / 53.1 / 9.4. Criterion (i) was defined on the combined set (original plus newly captured) and is met there (33.4 / 56.9 / 9.7); on the re-run's own claim set the unsubstantiated share is about 7 points lower than published. The direction is the same under both: fuller extraction lowers the unsubstantiated share.
- Check G: the mapping step is repeatable (identical goal sets for 80% of claims, κ 0.93).
- Check H: the environmental minus social difference is +0.02 (unstandardised) and +0.04 (standardised for claim type) among newly captured claims, against +0.17 and +0.14 in the original claims. Social goals score higher among the newly captured claims (SDG 3, 4, 5 and 8 in particular).
- Cost of the further checks: second extraction pass US$31.28, re-mapping US$2.22 (same price assumption). Running total about US$133 of the US$150 ceiling.
