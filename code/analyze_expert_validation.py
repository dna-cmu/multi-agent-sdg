"""
Expert Validation Analysis

Ingests completed expert scoring workbooks and compares them against the
pipeline's scores. Computes inter-rater reliability (Cohen's kappa,
Krippendorff's alpha), identifies systematic disagreements, and generates
a summary report.

Usage:
    # Analyze two expert workbooks:
    python analyze_expert_validation.py \
        --expert-a data/expert_scores/expert_a.xlsx \
        --expert-b data/expert_scores/expert_b.xlsx

    # Re-display previous results:
    python analyze_expert_validation.py --results-only
"""

import argparse
import json
import numpy as np
from pathlib import Path

try:
    import krippendorff
    HAS_KRIPPENDORFF = True
except ImportError:
    HAS_KRIPPENDORFF = False

from openpyxl import load_workbook
from config.settings import OUTPUTS_DIR

DIMS = ["specificity", "measurability", "temporality", "evidence", "consistency"]

# Header-label → internal dimension key. We look up columns by header text so
# the analyzer works across workbook versions (v3 scoring columns are at I-M,
# v4 shifts them to J-N after the new "Cross-References v4" column is inserted).
DIM_HEADER_PREFIXES = {
    "specificity": ("S (", "Specificity"),
    "measurability": ("M (", "Measurability"),
    "temporality": ("T (", "Temporality"),
    "evidence": ("E (", "Evidence"),
    "consistency": ("C (", "Consistency"),
}


def _resolve_dim_columns(ws) -> dict:
    """
    Find the column index of each SMTEC dimension by scanning the header row.
    Raises if any dimension column cannot be located — this is a correctness
    requirement, not a warning.
    """
    found: dict = {}
    for col in range(1, ws.max_column + 1):
        header = ws.cell(row=1, column=col).value
        if not header:
            continue
        header_str = str(header).strip()
        for dim, prefixes in DIM_HEADER_PREFIXES.items():
            if any(header_str.startswith(p) for p in prefixes):
                found.setdefault(dim, col)

    missing = [d for d in DIMS if d not in found]
    if missing:
        raise RuntimeError(
            f"Could not locate columns for dimensions: {missing}. "
            f"Header row was: "
            f"{[ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]}"
        )
    return found


def load_expert_scores(xlsx_path: str) -> dict:
    """
    Load expert scores from a completed validation workbook.
    Returns: {claim_id: {dim: score, ...}, ...}
    """
    wb = load_workbook(xlsx_path, data_only=True)
    ws = wb["Scoring"]
    dim_cols = _resolve_dim_columns(ws)

    scores = {}
    for row in range(2, ws.max_row + 1):
        claim_id = ws.cell(row=row, column=2).value
        if not claim_id:
            continue

        claim_scores = {}
        all_filled = True
        for dim, col in dim_cols.items():
            val = ws.cell(row=row, column=col).value
            if val is None:
                all_filled = False
                break
            claim_scores[dim] = int(val)

        if all_filled:
            claim_scores["composite"] = round(np.mean([claim_scores[d] for d in DIMS]), 2)
            claim_scores["tier"] = classify_tier(claim_scores["composite"])
            scores[claim_id] = claim_scores

    return scores


def load_pipeline_scores(xlsx_path: str) -> dict:
    """Load pipeline scores from the hidden sheet in any expert workbook."""
    wb = load_workbook(xlsx_path, data_only=True)
    ws = wb["Pipeline_Scores"]

    scores = {}
    for row in range(2, ws.max_row + 1):
        unique_id = ws.cell(row=row, column=1).value  # Column A: Unique ID (e.g., CPF-CLM-0001)
        if not unique_id:
            continue
        scores[unique_id] = {
            "specificity": ws.cell(row=row, column=4).value,
            "measurability": ws.cell(row=row, column=5).value,
            "temporality": ws.cell(row=row, column=6).value,
            "evidence": ws.cell(row=row, column=7).value,
            "consistency": ws.cell(row=row, column=8).value,
            "composite": ws.cell(row=row, column=9).value,
            "tier": ws.cell(row=row, column=10).value,
        }
    return scores


def classify_tier(composite: float) -> str:
    if composite >= 2.0:
        return "substantive"
    elif composite >= 1.0:
        return "partially_substantive"
    return "symbolic"


def cohens_kappa(rater1: list, rater2: list) -> float:
    """Compute Cohen's kappa for two raters (ordinal treated as nominal)."""
    categories = sorted(set(rater1 + rater2))
    n = len(rater1)
    if n == 0:
        return 0.0

    # Confusion matrix
    matrix = {}
    for cat in categories:
        matrix[cat] = {c: 0 for c in categories}
    for a, b in zip(rater1, rater2):
        matrix[a][b] += 1

    # Observed agreement
    po = sum(matrix[c][c] for c in categories) / n

    # Expected agreement
    pe = 0
    for c in categories:
        row_sum = sum(matrix[c].values()) / n
        col_sum = sum(matrix[r][c] for r in categories) / n
        pe += row_sum * col_sum

    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def weighted_kappa(rater1: list, rater2: list, weights="quadratic") -> float:
    """Compute weighted Cohen's kappa (linear or quadratic weights)."""
    categories = sorted(set(rater1 + rater2))
    n = len(rater1)
    k = len(categories)
    if n == 0 or k <= 1:
        return 0.0

    cat_idx = {c: i for i, c in enumerate(categories)}

    # Weight matrix
    w = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            if weights == "quadratic":
                w[i][j] = 1 - ((i - j) ** 2) / ((k - 1) ** 2)
            else:  # linear
                w[i][j] = 1 - abs(i - j) / (k - 1)

    # Observed and expected matrices
    observed = np.zeros((k, k))
    for a, b in zip(rater1, rater2):
        observed[cat_idx[a]][cat_idx[b]] += 1
    observed /= n

    row_marginals = observed.sum(axis=1)
    col_marginals = observed.sum(axis=0)
    expected = np.outer(row_marginals, col_marginals)

    po_w = np.sum(w * observed)
    pe_w = np.sum(w * expected)

    if pe_w == 1.0:
        return 1.0
    return (po_w - pe_w) / (1 - pe_w)


def compute_krippendorff_alpha(raters_data: list[list], level="ordinal") -> float:
    """Compute Krippendorff's alpha for multiple raters."""
    if not HAS_KRIPPENDORFF:
        return float("nan")
    matrix = np.array(raters_data)
    return krippendorff.alpha(reliability_data=matrix, level_of_measurement=level)


def analyze(expert_a: dict, expert_b: dict, pipeline: dict):
    """Run the full analysis and return results dict."""
    # Find common claims scored by both experts and pipeline
    common_ids = sorted(set(expert_a.keys()) & set(expert_b.keys()) & set(pipeline.keys()))
    n = len(common_ids)

    print(f"\nClaims scored by Expert A: {len(expert_a)}")
    print(f"Claims scored by Expert B: {len(expert_b)}")
    print(f"Claims in common (all 3 raters): {n}")

    if n == 0:
        print("ERROR: No common claims found. Check that claim IDs match.")
        return None

    results = {"n_claims": n, "dimensions": {}, "pairwise": {}, "three_rater": {}}

    # ── Per-dimension analysis ───────────────────────────────────────
    print(f"\n{'='*75}")
    print("PER-DIMENSION INTER-RATER RELIABILITY")
    print(f"{'='*75}")
    print(f"{'Dimension':15s} {'K_AB':>8s} {'K_AP':>8s} {'K_BP':>8s} {'Wk_AB':>8s} {'Wk_AP':>8s} {'Wk_BP':>8s} {'Alpha':>8s}")
    print("-"*75)

    for dim in DIMS:
        a_scores = [expert_a[cid][dim] for cid in common_ids]
        b_scores = [expert_b[cid][dim] for cid in common_ids]
        p_scores = [pipeline[cid][dim] for cid in common_ids]

        # Pairwise Cohen's kappa
        k_ab = cohens_kappa(a_scores, b_scores)
        k_ap = cohens_kappa(a_scores, p_scores)
        k_bp = cohens_kappa(b_scores, p_scores)

        # Weighted kappa (quadratic)
        wk_ab = weighted_kappa(a_scores, b_scores)
        wk_ap = weighted_kappa(a_scores, p_scores)
        wk_bp = weighted_kappa(b_scores, p_scores)

        # 3-rater Krippendorff's alpha
        alpha = compute_krippendorff_alpha([a_scores, b_scores, p_scores], "ordinal")

        results["dimensions"][dim] = {
            "kappa_AB": round(k_ab, 4),
            "kappa_AP": round(k_ap, 4),
            "kappa_BP": round(k_bp, 4),
            "weighted_kappa_AB": round(wk_ab, 4),
            "weighted_kappa_AP": round(wk_ap, 4),
            "weighted_kappa_BP": round(wk_bp, 4),
            "krippendorff_alpha": round(alpha, 4) if not np.isnan(alpha) else None,
            "mean_A": round(np.mean(a_scores), 3),
            "mean_B": round(np.mean(b_scores), 3),
            "mean_pipeline": round(np.mean(p_scores), 3),
        }

        print(f"{dim:15s} {k_ab:8.3f} {k_ap:8.3f} {k_bp:8.3f} {wk_ab:8.3f} {wk_ap:8.3f} {wk_bp:8.3f} {alpha:8.3f}")

    # ── Overall (pooled across dimensions) ───────────────────────────
    all_a = [expert_a[cid][dim] for cid in common_ids for dim in DIMS]
    all_b = [expert_b[cid][dim] for cid in common_ids for dim in DIMS]
    all_p = [pipeline[cid][dim] for cid in common_ids for dim in DIMS]

    k_ab_all = cohens_kappa(all_a, all_b)
    k_ap_all = cohens_kappa(all_a, all_p)
    k_bp_all = cohens_kappa(all_b, all_p)
    wk_ab_all = weighted_kappa(all_a, all_b)
    wk_ap_all = weighted_kappa(all_a, all_p)
    wk_bp_all = weighted_kappa(all_b, all_p)
    alpha_all = compute_krippendorff_alpha([all_a, all_b, all_p], "ordinal")

    results["overall"] = {
        "kappa_AB": round(k_ab_all, 4),
        "kappa_AP": round(k_ap_all, 4),
        "kappa_BP": round(k_bp_all, 4),
        "weighted_kappa_AB": round(wk_ab_all, 4),
        "weighted_kappa_AP": round(wk_ap_all, 4),
        "weighted_kappa_BP": round(wk_bp_all, 4),
        "krippendorff_alpha": round(alpha_all, 4) if not np.isnan(alpha_all) else None,
    }

    print("-"*75)
    print(f"{'OVERALL':15s} {k_ab_all:8.3f} {k_ap_all:8.3f} {k_bp_all:8.3f} {wk_ab_all:8.3f} {wk_ap_all:8.3f} {wk_bp_all:8.3f} {alpha_all:8.3f}")

    # ── Tier agreement ───────────────────────────────────────────────
    print(f"\n{'='*75}")
    print("TIER CLASSIFICATION AGREEMENT")
    print(f"{'='*75}")

    a_tiers = [expert_a[cid]["tier"] for cid in common_ids]
    b_tiers = [expert_b[cid]["tier"] for cid in common_ids]
    p_tiers = [pipeline[cid]["tier"] for cid in common_ids]

    agree_ab = sum(1 for a, b in zip(a_tiers, b_tiers) if a == b)
    agree_ap = sum(1 for a, p in zip(a_tiers, p_tiers) if a == p)
    agree_bp = sum(1 for b, p in zip(b_tiers, p_tiers) if b == p)
    agree_all = sum(1 for a, b, p in zip(a_tiers, b_tiers, p_tiers) if a == b == p)

    results["tier_agreement"] = {
        "expert_AB": round(agree_ab / n, 4),
        "expert_A_pipeline": round(agree_ap / n, 4),
        "expert_B_pipeline": round(agree_bp / n, 4),
        "all_three": round(agree_all / n, 4),
    }

    print(f"  Expert A vs Expert B:   {agree_ab}/{n} ({100*agree_ab/n:.1f}%)")
    print(f"  Expert A vs Pipeline:   {agree_ap}/{n} ({100*agree_ap/n:.1f}%)")
    print(f"  Expert B vs Pipeline:   {agree_bp}/{n} ({100*agree_bp/n:.1f}%)")
    print(f"  All three agree:        {agree_all}/{n} ({100*agree_all/n:.1f}%)")

    # ── Bias analysis ────────────────────────────────────────────────
    print(f"\n{'='*75}")
    print("SCORING BIAS (mean difference)")
    print(f"{'='*75}")
    print(f"{'Dimension':15s} {'A-Pipeline':>12s} {'B-Pipeline':>12s} {'A-B':>12s}")
    print("-"*55)

    results["bias"] = {}
    for dim in DIMS:
        a_scores = [expert_a[cid][dim] for cid in common_ids]
        b_scores = [expert_b[cid][dim] for cid in common_ids]
        p_scores = [pipeline[cid][dim] for cid in common_ids]

        bias_ap = np.mean([a - p for a, p in zip(a_scores, p_scores)])
        bias_bp = np.mean([b - p for b, p in zip(b_scores, p_scores)])
        bias_ab = np.mean([a - b for a, b in zip(a_scores, b_scores)])

        results["bias"][dim] = {
            "A_minus_pipeline": round(bias_ap, 3),
            "B_minus_pipeline": round(bias_bp, 3),
            "A_minus_B": round(bias_ab, 3),
        }

        print(f"{dim:15s} {bias_ap:+12.3f} {bias_bp:+12.3f} {bias_ab:+12.3f}")

    # ── Disagreement hotspots ────────────────────────────────────────
    print(f"\n{'='*75}")
    print("LARGEST DISAGREEMENTS (Expert consensus vs Pipeline)")
    print(f"{'='*75}")

    disagreements = []
    for cid in common_ids:
        expert_avg_comp = (expert_a[cid]["composite"] + expert_b[cid]["composite"]) / 2
        pipe_comp = pipeline[cid]["composite"]
        diff = abs(expert_avg_comp - pipe_comp)
        disagreements.append({
            "claim_id": cid,
            "expert_avg_composite": round(expert_avg_comp, 2),
            "pipeline_composite": pipe_comp,
            "difference": round(diff, 2),
            "expert_a_tier": expert_a[cid]["tier"],
            "expert_b_tier": expert_b[cid]["tier"],
            "pipeline_tier": pipeline[cid]["tier"],
        })

    disagreements.sort(key=lambda x: -x["difference"])
    results["top_disagreements"] = disagreements[:10]

    for d in disagreements[:10]:
        direction = "Pipeline higher" if d["pipeline_composite"] > d["expert_avg_composite"] else "Pipeline lower"
        print(f"  {d['claim_id']}: experts={d['expert_avg_composite']:.2f} vs pipeline={d['pipeline_composite']} (Δ={d['difference']:.2f}, {direction})")

    # ── Interpretation ───────────────────────────────────────────────
    print(f"\n{'='*75}")
    print("INTERPRETATION")
    print(f"{'='*75}")

    alpha_val = results["overall"]["krippendorff_alpha"]
    if alpha_val and alpha_val >= 0.8:
        print(f"  Overall Krippendorff's alpha: {alpha_val:.3f} — STRONG agreement")
    elif alpha_val and alpha_val >= 0.667:
        print(f"  Overall Krippendorff's alpha: {alpha_val:.3f} — ACCEPTABLE agreement")
    elif alpha_val:
        print(f"  Overall Krippendorff's alpha: {alpha_val:.3f} — BELOW threshold")
    else:
        print("  Krippendorff's alpha: not computed (install krippendorff package)")

    wk_avg = (results["overall"]["weighted_kappa_AP"] + results["overall"]["weighted_kappa_BP"]) / 2
    print(f"  Mean weighted kappa (experts vs pipeline): {wk_avg:.3f}")
    if wk_avg >= 0.8:
        print("  → Almost perfect agreement (Landis & Koch)")
    elif wk_avg >= 0.6:
        print("  → Substantial agreement (Landis & Koch)")
    elif wk_avg >= 0.4:
        print("  → Moderate agreement (Landis & Koch)")
    else:
        print("  → Fair or lower agreement")

    return results


def main():
    parser = argparse.ArgumentParser(description="Analyze expert validation results")
    parser.add_argument("--expert-a", required=False, help="Path to Expert A's completed workbook")
    parser.add_argument("--expert-b", required=False, help="Path to Expert B's completed workbook")
    parser.add_argument("--output", default=None, help="Output JSON path")
    parser.add_argument("--results-only", action="store_true", help="Display previous results")
    args = parser.parse_args()

    output_path = Path(args.output) if args.output else OUTPUTS_DIR / "expert_validation_analysis.json"

    if args.results_only:
        if not output_path.exists():
            print(f"ERROR: No results at {output_path}. Run analysis first.")
            return
        with open(output_path) as f:
            results = json.load(f)
        print(json.dumps(results, indent=2))
        return

    if not args.expert_a or not args.expert_b:
        print("Usage: python analyze_expert_validation.py --expert-a <path> --expert-b <path>")
        print("\nProvide completed expert workbooks (.xlsx files).")
        return

    print("Loading expert scores...")
    expert_a = load_expert_scores(args.expert_a)
    expert_b = load_expert_scores(args.expert_b)
    pipeline = load_pipeline_scores(args.expert_a)  # Pipeline scores from hidden sheet

    results = analyze(expert_a, expert_b, pipeline)

    if results:
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
