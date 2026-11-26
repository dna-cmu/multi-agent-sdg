"""
Phase 4: Cross-Report Comparative Analysis (Comparator Agent)

This agent analyses patterns across the full corpus:
- Frequency-credibility matrix
- Self-declared vs AI-assessed alignment comparison
- Sector-level analysis
- Feedback loops (triggers re-assessment when inconsistencies found)
"""

import json
import pandas as pd
from pathlib import Path
from collections import Counter, defaultdict

from config.settings import OUTPUTS_DIR, CREDIBILITY_DIMENSIONS


class ComparatorAgent:
    """Phase 4 agent: cross-report comparative analysis."""

    def __init__(self):
        self.corpus_data = []

    def load_corpus(self, results: list[dict]):
        """Load processed results from all reports."""
        self.corpus_data = results
        print(f"\n{'='*60}")
        print(f"PHASE 4: Cross-Report Analysis ({len(results)} reports)")
        print(f"{'='*60}")

    def build_frequency_credibility_matrix(self) -> pd.DataFrame:
        """
        Build the frequency-credibility matrix:
        For each SDG target, calculate reporting frequency and average credibility.
        This is one of the paper's key diagnostic outputs.
        """
        target_data = defaultdict(lambda: {"count": 0, "scores": []})

        for report in self.corpus_data:
            for claim in report.get("claims", []):
                if claim.get("composite_score") is None:
                    continue
                for mapping in claim.get("sdg_mappings", []):
                    target_id = mapping.get("target")
                    if target_id:
                        target_data[target_id]["count"] += 1
                        target_data[target_id]["scores"].append(claim["composite_score"])

        rows = []
        for target_id, data in sorted(target_data.items()):
            avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
            rows.append({
                "sdg_target": target_id,
                "goal": target_id.split(".")[0],
                "frequency": data["count"],
                "avg_credibility": round(avg_score, 2),
                "n_companies": len(set(
                    r["metadata"]["company"]
                    for r in self.corpus_data
                    for c in r.get("claims", [])
                    if any(m.get("target") == target_id for m in c.get("sdg_mappings", []))
                )),
            })

        df = pd.DataFrame(rows)

        # Classify into quadrants
        if not df.empty:
            freq_median = df["frequency"].median()
            cred_median = df["avg_credibility"].median()
            df["quadrant"] = df.apply(
                lambda r: (
                    "Q1: High freq, High cred" if r["frequency"] >= freq_median and r["avg_credibility"] >= cred_median
                    else "Q2: High freq, Low cred (SDG-washing hotspot)" if r["frequency"] >= freq_median
                    else "Q3: Low freq, High cred (genuine niche)" if r["avg_credibility"] >= cred_median
                    else "Q4: Low freq, Low cred"
                ),
                axis=1,
            )

        print(f"  Frequency-credibility matrix: {len(df)} targets mapped")
        return df

    def sector_analysis(self) -> pd.DataFrame:
        """Compare credibility scores across sectors."""
        sector_data = defaultdict(lambda: {dim: [] for dim in CREDIBILITY_DIMENSIONS + ["composite"]})

        for report in self.corpus_data:
            sector = report["metadata"].get("sector", "Unknown")
            for claim in report.get("claims", []):
                if claim.get("composite_score") is None:
                    continue
                sector_data[sector]["composite"].append(claim["composite_score"])
                for dim in CREDIBILITY_DIMENSIONS:
                    score = claim.get("credibility_scores", {}).get(dim, {})
                    if isinstance(score, dict):
                        score = score.get("score")
                    if score is not None:
                        sector_data[sector][dim].append(score)

        rows = []
        for sector, dims in sector_data.items():
            row = {"sector": sector, "n_claims": len(dims["composite"])}
            for dim in CREDIBILITY_DIMENSIONS + ["composite"]:
                values = dims[dim]
                row[f"{dim}_mean"] = round(sum(values) / len(values), 2) if values else None
            rows.append(row)

        df = pd.DataFrame(rows)
        print(f"  Sector analysis: {len(df)} sectors compared")
        return df

    def overclaiming_analysis(self) -> list[dict]:
        """
        Compare self-declared SDG mappings (from GRI index) against
        AI-assessed mappings. Identifies over-claiming and under-reporting.
        """
        results = []

        for report in self.corpus_data:
            company = report["metadata"].get("company", "Unknown")
            self_declared = set(report["metadata"].get("self_declared_sdgs", []))

            # Collect AI-assessed SDG goals (from target mappings)
            ai_assessed = set()
            for claim in report.get("claims", []):
                for mapping in claim.get("sdg_mappings", []):
                    target = mapping.get("target", "")
                    goal = target.split(".")[0] if "." in target else target
                    ai_assessed.add(goal)

            if self_declared or ai_assessed:
                over_claimed = self_declared - ai_assessed
                under_reported = ai_assessed - self_declared
                results.append({
                    "company": company,
                    "self_declared": sorted(self_declared),
                    "ai_assessed": sorted(ai_assessed),
                    "over_claimed": sorted(over_claimed),
                    "under_reported": sorted(under_reported),
                })

        print(f"  Over-claiming analysis: {len(results)} companies compared")
        return results

    def identify_feedback_targets(self) -> list[dict]:
        """
        Identify claims that should be re-assessed (feedback loop).
        Triggers: statistical outliers, cross-report inconsistencies.
        """
        feedback_targets = []

        for report in self.corpus_data:
            company = report["metadata"]["company"]
            sector = report["metadata"].get("sector", "Unknown")
            scores = [c["composite_score"] for c in report.get("claims", []) if c.get("composite_score") is not None]

            if not scores:
                continue

            mean_score = sum(scores) / len(scores)

            # Flag individual claims that are extreme outliers within a report
            for claim in report.get("claims", []):
                cs = claim.get("composite_score")
                if cs is not None and abs(cs - mean_score) > 1.5:
                    feedback_targets.append({
                        "claim_id": claim["claim_id"],
                        "company": company,
                        "reason": f"Outlier within report (score {cs} vs mean {mean_score:.1f})",
                        "action": "re_score",
                    })

        print(f"  Feedback targets identified: {len(feedback_targets)} claims for re-assessment")
        return feedback_targets

    def generate_summary(self) -> dict:
        """Generate a corpus-level summary of all analyses."""
        fc_matrix = self.build_frequency_credibility_matrix()
        sector_df = self.sector_analysis()
        overclaiming = self.overclaiming_analysis()
        feedback = self.identify_feedback_targets()

        summary = {
            "corpus_size": len(self.corpus_data),
            "total_claims": sum(len(r.get("claims", [])) for r in self.corpus_data),
            "claims_with_mappings": sum(
                1 for r in self.corpus_data
                for c in r.get("claims", [])
                if c.get("sdg_mappings")
            ),
            "frequency_credibility_matrix": fc_matrix.to_dict(orient="records") if not fc_matrix.empty else [],
            "sector_analysis": sector_df.to_dict(orient="records") if not sector_df.empty else [],
            "overclaiming_analysis": overclaiming,
            "feedback_targets": feedback,
        }

        # Save full results
        output_path = OUTPUTS_DIR / "corpus_analysis.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n  Corpus analysis saved to: {output_path}")
        return summary
