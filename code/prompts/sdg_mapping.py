"""
Prompt templates for Phase 2: SDG target mapping.
"""

GOAL_SCREENING_PROMPT = """You are an SDG classification expert. Given a sustainability claim from a corporate report, identify which of the 17 UN Sustainable Development Goals this claim is most relevant to.

Claim: "{claim_text}"

Return a JSON object with the top 1-3 most relevant SDG goals (by number), with a brief rationale for each:
{{
  "candidate_goals": [
    {{"goal": 7, "rationale": "Claim relates to renewable energy investment"}},
    {{"goal": 13, "rationale": "Claim addresses climate change mitigation"}}
  ]
}}

If the claim is not relevant to any SDG, return: {{"candidate_goals": []}}
Return ONLY valid JSON."""


TARGET_MAPPING_PROMPT = """You are an SDG target-level classification expert. Given a sustainability claim and a specific SDG goal, determine which specific targets within that goal the claim addresses.

Claim: "{claim_text}"

SDG Goal {goal_number}: {goal_title}

Targets for this goal:
{targets_text}

For each target, assess whether the claim is relevant. Return a JSON object:
{{
  "mappings": [
    {{
      "target": "7.2",
      "target_text": "Increase substantially the share of renewable energy...",
      "relevant": true,
      "confidence": 0.85,
      "rationale": "Claim directly describes solar energy capacity installation"
    }},
    {{
      "target": "7.3",
      "target_text": "Double the global rate of improvement in energy efficiency...",
      "relevant": false,
      "confidence": 0.2,
      "rationale": "Claim is about energy generation, not efficiency"
    }}
  ]
}}

Only include targets where relevance is plausible. Skip clearly irrelevant targets.
Return ONLY valid JSON."""
