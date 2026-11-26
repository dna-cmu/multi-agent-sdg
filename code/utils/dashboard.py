"""
Dashboard Generator for SDG Credibility Assessment Framework.

Generates HTML dashboards from pipeline outputs:
  - Per-report dashboard: claim stats, tier distribution, SDG frequency,
    dimension scores, section heatmap, top/bottom claims
  - Cross-report dashboard: comparative analysis across all reports
"""

import json
from pathlib import Path
from collections import Counter, defaultdict
from config.settings import OUTPUTS_DIR, CREDIBILITY_DIMENSIONS

# Official SDG colors
SDG_COLORS = {
    1: "#e5243b", 2: "#dda63a", 3: "#4c9f38", 4: "#c5192d", 5: "#ff3a21",
    6: "#26bde2", 7: "#fcc30b", 8: "#a21942", 9: "#fd6925", 10: "#dd1367",
    11: "#fd9d24", 12: "#bf8b2e", 13: "#3f7e44", 14: "#0a97d9", 15: "#56c02b",
    16: "#00689d", 17: "#19486a",
}

SDG_NAMES = {
    1: "No Poverty", 2: "Zero Hunger", 3: "Good Health", 4: "Quality Education",
    5: "Gender Equality", 6: "Clean Water", 7: "Affordable Energy", 8: "Decent Work",
    9: "Industry & Innovation", 10: "Reduced Inequalities", 11: "Sustainable Cities",
    12: "Responsible Consumption", 13: "Climate Action", 14: "Life Below Water",
    15: "Life on Land", 16: "Peace & Justice", 17: "Partnerships",
}


def _extract_report_stats(result: dict) -> dict:
    """Extract all statistics needed for a single-report dashboard."""
    claims = result.get("claims", [])
    metadata = result.get("metadata", {})
    sections = result.get("sections", [])

    scored_claims = [c for c in claims if c.get("composite_score") is not None]
    mapped_claims = [c for c in claims if c.get("sdg_mappings")]

    # Tier distribution
    tiers = Counter(c.get("credibility_tier") for c in claims)
    tier_dist = {
        "substantive": tiers.get("substantive", 0),
        "partially_substantive": tiers.get("partially_substantive", 0),
        "symbolic": tiers.get("symbolic", 0),
        "unscored": sum(1 for c in claims if c.get("composite_score") is None),
    }
    total_scored = tier_dist["substantive"] + tier_dist["partially_substantive"] + tier_dist["symbolic"]

    # Claim type distribution
    type_dist = Counter(c.get("claim_type", "unknown") for c in claims)

    # SDG frequency
    sdg_freq = Counter()
    for c in claims:
        goals_seen = set()
        for m in c.get("sdg_mappings", []):
            target = m.get("target", "")
            goal = int(target.split(".")[0]) if "." in target else None
            if goal and goal not in goals_seen:
                sdg_freq[goal] += 1
                goals_seen.add(goal)

    # Dimension averages
    dim_avgs = {}
    for dim in CREDIBILITY_DIMENSIONS:
        scores = []
        for c in scored_claims:
            dim_data = c.get("credibility_scores", {}).get(dim, {})
            if isinstance(dim_data, dict) and dim_data.get("score") is not None:
                scores.append(dim_data["score"])
        dim_avgs[dim] = round(sum(scores) / len(scores), 2) if scores else 0

    # Agreement stats
    total_dims = 0
    agreed_dims = 0
    for c in scored_claims:
        for dim in CREDIBILITY_DIMENSIONS:
            dim_data = c.get("credibility_scores", {}).get(dim, {})
            if isinstance(dim_data, dict) and "agreement" in dim_data:
                total_dims += 1
                if dim_data["agreement"]:
                    agreed_dims += 1
    agreement_pct = round(agreed_dims / total_dims * 100, 1) if total_dims else 0

    # Section scores
    section_claims = defaultdict(list)
    for c in scored_claims:
        sec = c.get("section", "Unknown")
        section_claims[sec].append(c["composite_score"])
    section_scores = []
    for sec, scores in section_claims.items():
        section_scores.append({
            "section": sec,
            "num_claims": len(scores),
            "avg_score": round(sum(scores) / len(scores), 2),
        })
    section_scores.sort(key=lambda x: x["avg_score"], reverse=True)

    # Top/bottom claims
    sorted_claims = sorted(scored_claims, key=lambda c: c["composite_score"], reverse=True)
    top_5 = sorted_claims[:5]
    bottom_5 = sorted(scored_claims, key=lambda c: c["composite_score"])[:5]

    # Mean composite
    mean_composite = round(sum(c["composite_score"] for c in scored_claims) / len(scored_claims), 2) if scored_claims else 0

    return {
        "metadata": metadata,
        "total_claims": len(claims),
        "mapped_claims": len(mapped_claims),
        "scored_claims": len(scored_claims),
        "mean_composite": mean_composite,
        "tier_dist": tier_dist,
        "total_scored": total_scored,
        "type_dist": dict(type_dist.most_common()),
        "sdg_freq": dict(sdg_freq.most_common()),
        "dim_avgs": dim_avgs,
        "agreement_pct": agreement_pct,
        "section_scores": section_scores,
        "top_claims": top_5,
        "bottom_claims": bottom_5,
    }


def _bar_html(label, value, max_value, color, show_count=True):
    """Generate HTML for a single horizontal bar."""
    pct = (value / max_value * 100) if max_value else 0
    pct_display = max(pct, 3)  # minimum visible width
    count_html = f'<div class="bar-count">{value}</div>' if show_count else ""
    return f'''<div class="bar-row">
      <div class="bar-label">{label}</div>
      <div class="bar-track"><div class="bar-fill" style="width:{pct_display:.1f}%;background:{color};">{value}</div></div>
      {count_html}
    </div>'''


def _claim_row_html(claim, badge_class):
    """Generate a table row for a claim."""
    text = claim["claim_text"][:150].replace('"', '').replace("'", "")
    score = claim["composite_score"]
    section = claim.get("section", "Unknown")[:40]
    return f'''<tr>
          <td><span class="score-badge {badge_class}">{score}</span></td>
          <td class="claim-text">{text}</td>
          <td style="font-size:0.78rem;color:#6c757d;">{section}</td>
        </tr>'''


def _section_row_html(sec):
    """Generate a section heatmap row."""
    score = sec["avg_score"]
    if score >= 1.6:
        heat = "heat-high"
    elif score >= 1.2:
        heat = "heat-mid"
    else:
        heat = "heat-low"
    name = sec["section"][:45]
    return f'''<div class="section-row">
        <span class="section-name">{name}</span>
        <span class="section-claims">{sec["num_claims"]}</span>
        <span class="section-score {heat}">{score}</span>
      </div>'''


# ── CSS shared by all dashboards ─────────────────────────────────────────

DASHBOARD_CSS = """
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #f8f9fa; color: #1a1a2e; line-height: 1.6; padding: 2rem; }
  .container { max-width: 1100px; margin: 0 auto; }
  h1 { font-size: 1.8rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0.3rem; }
  .subtitle { color: #6c757d; font-size: 0.95rem; margin-bottom: 2rem; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }
  .card { background: #fff; border-radius: 12px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  .card h2 { font-size: 0.85rem; font-weight: 600; color: #495057; margin-bottom: 1rem; text-transform: uppercase; letter-spacing: 0.03em; }
  .big-number { font-size: 2.4rem; font-weight: 700; color: #1a1a2e; }
  .big-label { font-size: 0.85rem; color: #6c757d; margin-top: 0.2rem; }
  .bar-row { display: flex; align-items: center; margin-bottom: 0.6rem; }
  .bar-label { width: 140px; font-size: 0.82rem; color: #495057; flex-shrink: 0; text-align: right; padding-right: 12px; }
  .bar-track { flex: 1; background: #f0f0f0; border-radius: 4px; height: 22px; position: relative; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 4px; display: flex; align-items: center; padding-left: 8px; font-size: 0.75rem; color: #fff; font-weight: 600; min-width: 30px; }
  .bar-count { margin-left: 8px; font-size: 0.8rem; color: #6c757d; flex-shrink: 0; width: 50px; }
  .dim-row { display: flex; align-items: center; margin-bottom: 0.7rem; }
  .dim-label { width: 120px; font-size: 0.85rem; font-weight: 500; }
  .dim-track { flex: 1; background: #e9ecef; border-radius: 6px; height: 28px; position: relative; }
  .dim-fill { height: 100%; border-radius: 6px; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; font-size: 0.8rem; font-weight: 700; color: #fff; }
  .dim-max { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); font-size: 0.7rem; color: #adb5bd; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th { text-align: left; padding: 0.6rem 0.8rem; border-bottom: 2px solid #dee2e6; color: #495057; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.03em; }
  td { padding: 0.6rem 0.8rem; border-bottom: 1px solid #f0f0f0; vertical-align: top; }
  tr:last-child td { border-bottom: none; }
  .claim-text { font-size: 0.82rem; color: #343a40; line-height: 1.4; max-width: 500px; }
  .score-badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 10px; font-weight: 700; font-size: 0.8rem; }
  .badge-green { background: #d4edda; color: #155724; }
  .badge-yellow { background: #fff3cd; color: #856404; }
  .badge-red { background: #f8d7da; color: #721c24; }
  .section-row { display: flex; align-items: center; padding: 0.35rem 0; border-bottom: 1px solid #f8f9fa; font-size: 0.82rem; }
  .section-name { flex: 1; color: #495057; }
  .section-claims { width: 50px; text-align: center; color: #6c757d; }
  .section-score { width: 70px; text-align: center; font-weight: 700; padding: 0.15rem 0.4rem; border-radius: 4px; }
  .heat-high { background: #d4edda; color: #155724; }
  .heat-mid { background: #fff3cd; color: #856404; }
  .heat-low { background: #f8d7da; color: #721c24; }
  .stat-row { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid #f0f0f0; }
  .stat-row:last-child { border-bottom: none; }
  .footnote { margin-top: 2rem; font-size: 0.78rem; color: #adb5bd; text-align: center; }
"""


# ── Single-report dashboard ──────────────────────────────────────────────

def generate_report_dashboard(result: dict, output_path: Path = None) -> Path:
    """
    Generate an HTML dashboard for a single report's results.

    Args:
        result: Full pipeline output dict for one report.
        output_path: Where to save. Defaults to outputs/<stem>_dashboard.html.

    Returns:
        Path to the generated HTML file.
    """
    s = _extract_report_stats(result)
    meta = s["metadata"]
    company = meta.get("company", "Unknown")
    sector = meta.get("sector", "Unknown")
    year = meta.get("report_year", "Unknown")
    filename = meta.get("filename", "report")

    if output_path is None:
        stem = Path(filename).stem
        output_path = OUTPUTS_DIR / f"{stem}_dashboard.html"

    # --- Tier bars ---
    td = s["tier_dist"]
    ts = s["total_scored"] or 1
    tier_bars = ""
    for tier_name, color, label in [
        ("substantive", "#2d9a2d", "Substantive"),
        ("partially_substantive", "#e6a817", "Partially Substantive"),
        ("symbolic", "#dc3545", "Symbolic"),
        ("unscored", "#adb5bd", "Unscored"),
    ]:
        count = td[tier_name]
        pct = count / len([c for c in result.get("claims", [])]) * 100 if result.get("claims") else 0
        tier_bars += _bar_html(label, count, max(td.values()) or 1, color)

    # --- Claim type bars ---
    type_bars = ""
    type_colors = ["#6366f1", "#8b5cf6", "#a78bfa", "#c4b5fd", "#ddd6fe", "#ede9fe"]
    for i, (ctype, count) in enumerate(s["type_dist"].items()):
        color = type_colors[min(i, len(type_colors) - 1)]
        type_bars += _bar_html(ctype.capitalize(), count, max(s["type_dist"].values()) or 1, color)

    # --- SDG frequency bars ---
    sdg_bars = ""
    max_sdg = max(s["sdg_freq"].values()) if s["sdg_freq"] else 1
    for goal, count in sorted(s["sdg_freq"].items(), key=lambda x: x[1], reverse=True):
        goal_int = int(goal)
        color = SDG_COLORS.get(goal_int, "#6c757d")
        label = f"SDG {goal_int}"
        sdg_bars += _bar_html(label, count, max_sdg, color, show_count=False)

    # --- Dimension bars ---
    dim_bars = ""
    dim_colors = {"consistency": "#2d9a2d", "specificity": "#59a14f", "evidence": "#e6a817",
                  "measurability": "#dc3545", "temporality": "#dc3545"}
    dim_order = sorted(s["dim_avgs"].items(), key=lambda x: x[1], reverse=True)
    for dim, avg in dim_order:
        pct = avg / 3 * 100
        color = dim_colors.get(dim, "#6c757d")
        if avg >= 1.5:
            color = "#2d9a2d"
        elif avg >= 1.0:
            color = "#e6a817"
        else:
            color = "#dc3545"
        dim_bars += f'''<div class="dim-row">
      <div class="dim-label">{dim.capitalize()}</div>
      <div class="dim-track">
        <div class="dim-fill" style="width:{pct:.1f}%;background:{color};">{avg}</div>
        <span class="dim-max">/3</span>
      </div>
    </div>'''

    # --- Top/bottom claims ---
    top_rows = ""
    for c in s["top_claims"]:
        badge = "badge-green" if c["composite_score"] >= 2.0 else "badge-yellow"
        top_rows += _claim_row_html(c, badge)

    bottom_rows = ""
    for c in s["bottom_claims"]:
        badge = "badge-red" if c["composite_score"] < 1.0 else "badge-yellow"
        bottom_rows += _claim_row_html(c, badge)

    # --- Section heatmap ---
    top_sections = ""
    for sec in s["section_scores"][:8]:
        top_sections += _section_row_html(sec)
    bottom_sections = ""
    for sec in s["section_scores"][-8:]:
        bottom_sections += _section_row_html(sec)

    # --- Insights ---
    weakest_dim = min(s["dim_avgs"].items(), key=lambda x: x[1])
    strongest_dim = max(s["dim_avgs"].items(), key=lambda x: x[1])
    commit_count = s["type_dist"].get("commitment", 0)
    commit_pct = round(commit_count / s["total_claims"] * 100, 1) if s["total_claims"] else 0
    sub_pct = round(td["substantive"] / ts * 100, 1) if ts else 0
    top_sdg = list(s["sdg_freq"].keys())[0] if s["sdg_freq"] else "N/A"
    top_sdg_count = list(s["sdg_freq"].values())[0] if s["sdg_freq"] else 0
    top_sdg_pct = round(top_sdg_count / sum(s["sdg_freq"].values()) * 100, 1) if s["sdg_freq"] else 0
    mapped_pct = round(s["mapped_claims"] / s["total_claims"] * 100, 1) if s["total_claims"] else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{company} — SDG Credibility Assessment</title>
<style>{DASHBOARD_CSS}</style>
</head>
<body>
<div class="container">

<h1>{company} — SDG Credibility Assessment</h1>
<p class="subtitle">Sustainability Report {year} · {sector} · Assessed via 4-Phase Agentic AI Framework</p>

<!-- Key metrics -->
<div class="grid-3">
  <div class="card" style="text-align:center;">
    <div class="big-number">{s["total_claims"]}</div>
    <div class="big-label">Total Claims Extracted</div>
  </div>
  <div class="card" style="text-align:center;">
    <div class="big-number">{s["mapped_claims"]}</div>
    <div class="big-label">Claims with SDG Mappings ({mapped_pct}%)</div>
  </div>
  <div class="card" style="text-align:center;">
    <div class="big-number">{s["mean_composite"]}</div>
    <div class="big-label">Mean Composite Score (0–3)</div>
  </div>
</div>

<!-- Tier distribution + Claim types -->
<div class="grid-2">
  <div class="card">
    <h2>Credibility Tier Distribution</h2>
    {tier_bars}
    <div style="margin-top:1rem;padding-top:0.8rem;border-top:1px solid #f0f0f0;">
      <div class="stat-row">
        <span style="color:#495057;font-size:0.9rem;">3-Run Scoring Agreement</span>
        <span style="font-weight:700;">{s["agreement_pct"]}%</span>
      </div>
    </div>
  </div>
  <div class="card">
    <h2>Claim Type Breakdown</h2>
    {type_bars}
  </div>
</div>

<!-- Dimensions + SDG frequency -->
<div class="grid-2">
  <div class="card">
    <h2>Credibility Dimension Scores (avg, 0–3)</h2>
    {dim_bars}
    <p style="margin-top:1rem;font-size:0.8rem;color:#6c757d;">
      <strong>Strongest:</strong> {strongest_dim[0].capitalize()} ({strongest_dim[1]}) · <strong>Weakest:</strong> {weakest_dim[0].capitalize()} ({weakest_dim[1]})
    </p>
  </div>
  <div class="card">
    <h2>SDG Goal Mapping Frequency</h2>
    {sdg_bars}
  </div>
</div>

<!-- Top & Bottom claims -->
<div class="grid-2">
  <div class="card">
    <h2>Top 5 Most Credible Claims</h2>
    <table>
      <thead><tr><th>Score</th><th>Claim</th><th>Section</th></tr></thead>
      <tbody>{top_rows}</tbody>
    </table>
  </div>
  <div class="card">
    <h2>Bottom 5 Least Credible Claims</h2>
    <table>
      <thead><tr><th>Score</th><th>Claim</th><th>Section</th></tr></thead>
      <tbody>{bottom_rows}</tbody>
    </table>
  </div>
</div>

<!-- Section heatmap -->
<div class="card" style="margin-bottom:1.5rem;">
  <h2>Section Credibility Heatmap</h2>
  <div class="grid-2">
    <div>
      <p style="font-size:0.78rem;color:#6c757d;margin-bottom:0.5rem;font-weight:600;">HIGHEST CREDIBILITY</p>
      {top_sections}
    </div>
    <div>
      <p style="font-size:0.78rem;color:#6c757d;margin-bottom:0.5rem;font-weight:600;">LOWEST CREDIBILITY</p>
      {bottom_sections}
    </div>
  </div>
</div>

<!-- Key findings -->
<div class="card" style="margin-bottom:1.5rem;">
  <h2>Key Findings</h2>
  <table>
    <tbody>
      <tr>
        <td style="width:180px;font-weight:600;color:#495057;">Weakest Dimension</td>
        <td>{weakest_dim[0].capitalize()} scores only <strong>{weakest_dim[1]}/3</strong> on average — the most significant credibility gap in this report.</td>
      </tr>
      <tr>
        <td style="font-weight:600;color:#495057;">Commitment Gap</td>
        <td><strong>{commit_pct}%</strong> of claims are forward-looking commitments, yet only <strong>{sub_pct}%</strong> of scored claims achieve substantive credibility.</td>
      </tr>
      <tr>
        <td style="font-weight:600;color:#495057;">SDG Concentration</td>
        <td>SDG {top_sdg} ({SDG_NAMES.get(int(top_sdg), '')}) accounts for <strong>{top_sdg_pct}%</strong> of all mappings — the most frequently claimed goal.</td>
      </tr>
      <tr>
        <td style="font-weight:600;color:#495057;">Scoring Reliability</td>
        <td><strong>{s["agreement_pct"]}%</strong> of dimension scores showed perfect 3-run agreement, indicating high reproducibility.</td>
      </tr>
    </tbody>
  </table>
</div>

<p class="footnote">Generated by SDG Credibility Assessment Framework · 4-Phase Agentic AI Pipeline · {year}</p>

</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Dashboard saved to: {output_path}")
    return output_path


# ── Cross-report comparison dashboard ─────────────────────────────────────

def generate_comparison_dashboard(results: list[dict], output_path: Path = None) -> Path:
    """
    Generate an HTML dashboard comparing multiple reports.

    Args:
        results: List of full pipeline output dicts.
        output_path: Where to save. Defaults to outputs/comparison_dashboard.html.

    Returns:
        Path to the generated HTML file.
    """
    if output_path is None:
        output_path = OUTPUTS_DIR / "comparison_dashboard.html"

    all_stats = [_extract_report_stats(r) for r in results]

    # --- Company comparison table ---
    company_rows = ""
    for s in sorted(all_stats, key=lambda x: x["mean_composite"], reverse=True):
        meta = s["metadata"]
        td = s["tier_dist"]
        ts = s["total_scored"] or 1
        sub_pct = round(td["substantive"] / ts * 100, 1) if ts else 0
        sym_pct = round(td["symbolic"] / ts * 100, 1) if ts else 0

        score = s["mean_composite"]
        if score >= 1.5:
            badge = "badge-green"
        elif score >= 1.0:
            badge = "badge-yellow"
        else:
            badge = "badge-red"

        company_rows += f"""<tr>
          <td style="font-weight:600;">{meta.get("company", "Unknown")}</td>
          <td>{meta.get("sector", "Unknown")}</td>
          <td style="text-align:center;">{s["total_claims"]}</td>
          <td style="text-align:center;">{s["mapped_claims"]}</td>
          <td style="text-align:center;"><span class="score-badge {badge}">{score}</span></td>
          <td style="text-align:center;color:#2d9a2d;">{sub_pct}%</td>
          <td style="text-align:center;color:#dc3545;">{sym_pct}%</td>
        </tr>"""

    # --- Dimension comparison ---
    dim_comparison_rows = ""
    for dim in CREDIBILITY_DIMENSIONS:
        cells = ""
        for s in all_stats:
            val = s["dim_avgs"].get(dim, 0)
            if val >= 1.5:
                color = "#2d9a2d"
            elif val >= 1.0:
                color = "#e6a817"
            else:
                color = "#dc3545"
            cells += f'<td style="text-align:center;color:{color};font-weight:700;">{val}</td>'
        dim_comparison_rows += f"""<tr>
          <td style="font-weight:600;">{dim.capitalize()}</td>
          {cells}
        </tr>"""

    # Company headers for dimension table
    company_headers = ""
    for s in all_stats:
        name = s["metadata"].get("company", "Unknown")
        short_name = name.split()[0] if name != "Unknown" else "Unknown"
        company_headers += f'<th style="text-align:center;">{short_name}</th>'

    # --- SDG frequency heatmap across companies ---
    all_sdgs = set()
    for s in all_stats:
        all_sdgs.update(int(g) for g in s["sdg_freq"].keys())

    sdg_heatmap_rows = ""
    for goal in sorted(all_sdgs):
        cells = ""
        for s in all_stats:
            count = s["sdg_freq"].get(goal, 0)
            if count == 0:
                cells += '<td style="text-align:center;color:#dee2e6;">—</td>'
            else:
                cells += f'<td style="text-align:center;font-weight:600;">{count}</td>'
        color = SDG_COLORS.get(goal, "#6c757d")
        sdg_heatmap_rows += f"""<tr>
          <td><span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:{color};margin-right:6px;vertical-align:middle;"></span>SDG {goal}: {SDG_NAMES.get(goal, '')}</td>
          {cells}
        </tr>"""

    # --- Corpus-level aggregates ---
    total_claims = sum(s["total_claims"] for s in all_stats)
    total_mapped = sum(s["mapped_claims"] for s in all_stats)
    overall_mean = round(sum(s["mean_composite"] * s["scored_claims"] for s in all_stats) / max(sum(s["scored_claims"] for s in all_stats), 1), 2)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SDG Credibility — Cross-Report Comparison</title>
<style>{DASHBOARD_CSS}
  .compare-table th {{ font-size: 0.78rem; }}
  .compare-table td {{ font-size: 0.83rem; }}
</style>
</head>
<body>
<div class="container">

<h1>SDG Credibility — Cross-Report Comparison</h1>
<p class="subtitle">{len(all_stats)} Reports · All 2023 Sustainability Reports · Thai SET-Listed Companies</p>

<!-- Corpus metrics -->
<div class="grid-3">
  <div class="card" style="text-align:center;">
    <div class="big-number">{len(all_stats)}</div>
    <div class="big-label">Reports Analysed</div>
  </div>
  <div class="card" style="text-align:center;">
    <div class="big-number">{total_claims}</div>
    <div class="big-label">Total Claims ({total_mapped} mapped)</div>
  </div>
  <div class="card" style="text-align:center;">
    <div class="big-number">{overall_mean}</div>
    <div class="big-label">Corpus Mean Score (0–3)</div>
  </div>
</div>

<!-- Company comparison table -->
<div class="card" style="margin-bottom:1.5rem;">
  <h2>Company Comparison</h2>
  <table class="compare-table">
    <thead>
      <tr>
        <th>Company</th>
        <th>Sector</th>
        <th style="text-align:center;">Claims</th>
        <th style="text-align:center;">Mapped</th>
        <th style="text-align:center;">Mean Score</th>
        <th style="text-align:center;">Substantive</th>
        <th style="text-align:center;">Symbolic</th>
      </tr>
    </thead>
    <tbody>{company_rows}</tbody>
  </table>
</div>

<!-- Dimension comparison -->
<div class="card" style="margin-bottom:1.5rem;">
  <h2>Credibility Dimensions by Company (avg score, 0–3)</h2>
  <table class="compare-table">
    <thead>
      <tr>
        <th>Dimension</th>
        {company_headers}
      </tr>
    </thead>
    <tbody>{dim_comparison_rows}</tbody>
  </table>
</div>

<!-- SDG frequency heatmap -->
<div class="card" style="margin-bottom:1.5rem;">
  <h2>SDG Goal Frequency by Company</h2>
  <table class="compare-table">
    <thead>
      <tr>
        <th>SDG Goal</th>
        {company_headers}
      </tr>
    </thead>
    <tbody>{sdg_heatmap_rows}</tbody>
  </table>
</div>

<p class="footnote">Generated by SDG Credibility Assessment Framework · Cross-Report Analysis · 2023 Corpus</p>

</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Comparison dashboard saved to: {output_path}")
    return output_path
