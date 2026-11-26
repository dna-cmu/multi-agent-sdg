# Where "target" and the other unlisted claim types come from (Reviewer 3 point 6) — 10 Nov 2026

- The extraction prompt (`prompts/claim_extraction.py`) defines its output field as `"claim_type": "achievement" | "commitment" | "metric" | "alignment" | "policy"` — five types.
- The same prompt's description of what counts as a claim uses the words "A commitment, target, or plan for sustainability improvement" and "An achievement, metric, or outcome".
- The code that stores the extracted claims (`agents/planner.py`, line 652) accepts whatever label the model returns (`claim.get("claim_type", "unknown")`); there is no check against the five listed types.
- Result: the extraction model sometimes returned a label outside the list. In the scored corpus: 103 claims labelled "target" (1.6 %; in 19 of 30 reports) and 28 claims with 13 other labels (0.4 %): strategy 6, action_plan 4, outcome 4, opportunity 3, analysis 2, investment 2, and one each of projection, plan, contribution, aspiration, explanation, risk, compliance.
- So "target" was not a designed category and was not assigned afterwards: it is a model-generated label that the pipeline did not validate. No re-extraction was done.
- Reporting: the paper states this, treats "target" as a sixth observed type in the tables (as now), groups the 28 as "other", and notes that a fixed label set should be enforced in the next version.
