# Stricter Evidence reading — sensitivity analysis, pre-specification (10 Nov 2026)

Decision (DNA, 10 Nov 2026, Reviewer 3 point 3, "Option A"): frozen V4 stays the primary instrument. The stricter Evidence reading is a framework-side sensitivity analysis only, announced in FREEZE-V4-30Oct2026.md. Written before any stricter-reading score exists.

**Variant.** `sdg-credibility-framework/prompts/credibility_scoring_v4_E_strict.py` = the V4 prompt with three text replacements in the Evidence section (listed in the file). A standard reference alone, with or without its number, scores E = 1; E = 2 needs the scope of the data or the data's location in the report as well. Nothing else changes (model, temperature 0.3, 3 runs, median).

**Which claims.** Only claims whose primary V4 Evidence score is 2 are rescored (corpus and the 60 Round 1 claims). The stricter reading can only lower a score from 2 to 1; claims at 0, 1 or 3 are unaffected by it and keep their V4 score.

**What is used.** Only the E score of the variant (median of 3 runs). If the variant returns E > 2 for a claim, the claim keeps E = 2 (the reading cannot raise a score). S, M, T, labels and C stay as in V4.

**What is reported.** Number and share of claims whose E changes; mean E, SMTE and tier shares under both readings; the same for firm–goal Rule A and Rule B; rater–framework agreement on E for the 60 Round 1 claims under both readings. Reported as sensitivity, never as the headline.
