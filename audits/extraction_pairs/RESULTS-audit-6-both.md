# Audit 6 (claim / not-claim pairs) — both auditors, before resolution (25 Nov 2026)

Inputs frozen before scoring: Audit6-answers-DNA.csv (a8cea3e6…), Audit6-answers-EE.csv (a1ff0c6d…). Script: score_audit6.py. Rule: PRESPEC addendum 24 Nov 2026. DNA's form was scored on 24 Nov, before EE returned hers; EE worked without the key or DNA's result.

## 1. Agreement on the 90 judgements (reported first, as pre-specified)
| Source | Both: claim | DNA only | EE only | Both: not claim | Agreement | Cohen's κ |
|---|---|---|---|---|---|---|
| E extracted | 21 | 1 | 8 | 0 | 70% | −0.06 |
| N read, not taken | 19 | 1 | 2 | 8 | 90% | 0.77 |
| F beyond the cut | 12 | 3 | 5 | 10 | 73% | 0.47 |
| All | 52 | 5 | 15 | 18 | 78% | 0.49 |
κ for E is not informative: no sentence was rejected by both auditors, so chance agreement is very high. 20 judgements differ; 15 of them are sentences EE accepted and DNA did not.

## 2. Share judged a claim, per auditor (Wilson 95%)
| Source | DNA | EE | Both agree it is a claim |
|---|---|---|---|
| E | 22/30, 73% (56–86) | 29/30, 97% (83–99) | 21/30, 70% (52–83) |
| N | 20/30, 67% (49–81) | 21/30, 70% (52–83) | 19/30, 63% (46–78) |
| F | 15/30, 50% (33–67) | 17/30, 57% (39–73) | 12/30, 40% (25–58) |
The last column is a strict bound, not the resolved result; resolution by discussion is still to be done on the 20 differing judgements (listed in Audit6-disagreements.csv).

## 3. Reading
- Precision of extraction: 73% (DNA) to 97% (EE). Every extracted sentence was accepted by at least one auditor. The auditors differ mainly on recognitions and rankings, statements of intent, and descriptions of an activity, which EE counts and DNA does not.
- Claims passed over in text that was read: 67% and 70%, with high agreement (90%, κ 0.77). This is the most solid result: the extractor takes a subset of the claims in the text it reads.
- Claims beyond the cut: 50% and 57%, lower than in the text that was read for both auditors.
- Rough coverage with the pool sizes (E 6,060; N 6,127; F 13,431): DNA about 29%, EE about 33% of claim-like sentences were extracted. Indicative only (see RESULTS-audit-6-DNA.md for the caveats).
- EE's notes give her reasons for rejection: generic background, a definition, a description of the reporting process, notes to the financial statements.
