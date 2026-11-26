#!/usr/bin/env python3
"""
sync_release.py - refresh the public-release folder (release/) from the working project.

Run from the project root (~/Praxis/research/sdg-credibility) whenever work progresses:
    python3 release/tools/sync_release.py            # copy, then check
    python3 release/tools/sync_release.py --check     # check only
then review `git -C release status` and commit.

Design
  * The working folders stay the single source of truth; release/ only receives COPIES.
  * What is released is listed explicitly below (INCLUDE). Anything not listed is not released.
  * Files under release/ that no longer have a source are reported (not deleted) so nothing vanishes silently.
  * Hard safety checks run after every sync and fail loudly: no .env, no API keys, no PDFs, no reviewer
    reports, no named expert workbooks, no rater nicknames (read from a private file that is never
    released), no answer keys or returned ratings while ROUND1_CLOSED is False.

Release rules agreed with DNA (23 Oct 2026)
  IN : framework code and all prompt versions (V5-V7, V4); analysis and form-building scripts; the rater
       handbook as sent and the sampling/procedure note; the V4 freeze record; claim-level scores with page
       references; claim selection files; report list (manifest); validation and revision analysis outputs.
  OUT: .env / keys; report PDFs (copyright); ADE chunk text and embedding caches (full report text);
       reviewer reports and editor letters (confidential); the web app; named expert workbooks.
  LATER (set ROUND1_CLOSED = True after all Phase 2 workbooks are returned): answer keys, Round 1 forms,
       anonymised returned ratings.
"""
from __future__ import annotations
import argparse, filecmp, fnmatch, hashlib, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # project root
REL = ROOT / "release"
FW = "sdg-credibility-framework"
ROUND1_CLOSED = True                                # panel closed 16 Nov 2026 (four raters; see RECEIVED-Round1.md)
import json
_codes = ROOT / "scorer" / "rater-codes-PRIVATE.json"   # private: nickname -> public code; never released
CODES = {k: v for k, v in json.loads(_codes.read_text()).items() if not k.startswith("_")} if _codes.exists() else {}
RECODE_DIRS = ("instrument/protocol", "data/revision", "audits", "data/ratings_round1/analysis", "code/round1_analysis")   # text files here are recoded on copy
def recode(text: str) -> str:
    for k, v in CODES.items(): text = re.sub(r"(?<![A-Za-z])(?:Rater |rater )?" + k + r"(?![A-Za-z])", v, text)
    return text
def recode_code(text: str) -> str:      # scripts: any letter case, code without spaces (nickname -> RaterA)
    for k, v in CODES.items(): text = re.sub(r"(?<![A-Za-z])" + k + r"(?![A-Za-z])", v.split(" (")[0].replace(" ", ""), text, flags=re.I)
    return text

# (source glob relative to project root, destination folder relative to release/)
INCLUDE = [
    # ---- code ----
    (f"{FW}/agents/*.py",                       "code/agents"),
    (f"{FW}/prompts/*.py",                      "code/prompts"),
    (f"{FW}/utils/*.py",                        "code/utils"),
    (f"{FW}/config/*.py",                       "code/config"),
    (f"{FW}/experiments/*.py",                  "code/experiments"),
    (f"{FW}/*.py",                              "code"),
    (f"{FW}/*.sh",                              "code"),
    (f"{FW}/requirements.txt",                  "code"),
    (f"{FW}/pyproject.toml",                    "code"),
    (f"{FW}/.env.example",                      "code"),
    (f"{FW}/README.md",                         "code"),
    (f"{FW}/LICENSE",                           "."),
    ("scorer/build_phase2_form_v2.py",          "code/rater_forms"),
    ("scorer/build_large_forms.py",             "code/rater_forms"),
    ("scorer/build_challenge_set.py",           "code/rater_forms"),
    ("release/tools/sync_release.py",           None),          # lives in release/ already
    # ---- instrument and protocol ----
    ("scorer/Scorer-Handbook-SMTEC-21OCT26-changes-marked-DNA-EE.docx", "instrument/handbook"),
    ("scorer/handbooks-EN/*.docx",                                      "instrument/handbook/english"),
    ("scorer/handbooks-EN/README.md",                                   "instrument/handbook/english"),
    ("scorer/handbooks-EN/translation/*",                               "instrument/handbook/english/translation"),
    ("scorer/Round1-Sampling-and-Procedure-12Oct.md",                   "instrument/protocol"),
    ("scorer/SENT-Round1-Phase2-21Oct.md",                              "instrument/protocol"),
    ("scorer/CORPUS-V4-RUN.md",                                         "instrument/protocol"),
    ("revision/run_corpus_v4_batched.py",                               "code"),
    ("scorer/PRESPEC-E-strict-sensitivity-10Nov2026.md",                "instrument/protocol"),
    ("scorer/PRESPEC-firm-goal-rules-10Nov2026.md",                                    "instrument/protocol"),
    ("scorer/FREEZE-V4-*.md",                                           "instrument/protocol"),
    ("scorer/RECEIVED-Round1.md",                                       "instrument/protocol"),
    # ---- data that may be shared ----
    (f"{FW}/data/DATA_DICTIONARY.md",                       "data"),
    (f"{FW}/data/manifest_2024.csv",                        "data"),
    (f"{FW}/data/outputs/main/full_v7/*.json",              "data/scores_v7"),
    (f"{FW}/data/outputs/main/full_v4/*.json",              "data/scores_v4"),
    (f"{FW}/data/outputs/main/phase1/*.json",               "data/claims_phase1"),
    (f"{FW}/data/outputs/validation/*.json",                "data/validation"),
    (f"{FW}/data/outputs/experiments/retrieval_comparison/results.json", "data/experiments/retrieval_comparison"),
    (f"{FW}/data/outputs/revision/*.csv",                   "data/revision"),
    (f"{FW}/data/outputs/revision/v4/*.csv",                "data/revision/v4"),
    ("revision/findings-v4/*.py",                           "code/analysis"),
    ("revision/findings-v4/*.md",                           "data/revision/v4"),
    (f"{FW}/data/outputs/revision/v4_E_*.json",             "data/revision/v4"),
    ("revision/run_e_*.py",                                 "code/analysis"),
    (f"{FW}/data/outputs/revision/round1_50_selection.json",            "data/samples"),
    (f"{FW}/data/outputs/revision/round1_challenge_selection.json",     "data/samples"),
    (f"{FW}/data/outputs/revision/pilot20_selection.json",              "data/samples"),
    (f"{FW}/data/outputs/revision/v4_pilot20.json",                     "data/pilot"),
]
LATER = [   # released only when ROUND1_CLOSED is True
    ("scorer/Round1-60-KEY-EN-do-not-send.csv",                 "data/samples"),
    ("scorer/Round1-50-KEY-do-not-send.csv",                    "data/samples"),
    ("scorer/Round1-Phase1-HOLISTIC-form-large.xlsx",           "instrument/forms"),
    ("scorer/Round1-Phase2-SMTEC-form-v2-EN-large.xlsx",        "instrument/forms"),
    ("scorer/print-pdf/Round1-Phase2-SMTEC-form-v2-EN-large.pdf", "instrument/forms"),
    ("revision/release-staging/round1/*.csv",                   "data/ratings_round1"),
    ("revision/release-staging/VERSIONS.md",                    "."),
    # ---- author audits of the upstream stages (SI S16): only audits completed by both authors ----
    ("revision/audits/PRESPEC-audit-scoring-16Nov2026.md",      "audits"),
    ("revision/audits/build_audit_workbooks.py",                "code/audits"),
    ("revision/audits/build_audit6_pairs.py",                   "code/audits"),
    ("revision/audits/build_audit6_html.py",                    "code/audits"),
    ("revision/audits/build_audit6_resolution_html.py",         "code/audits"),
    ("revision/audits/score_audit6.py",                         "code/audits"),
    ("revision/audits/score_audit3_both.py",                    "code/audits"),
    ("revision/audits/firm_goal_resolved.py",                   "code/audits"),
    ("revision/audits/Audit6-Claim-or-not.html",                "audits/extraction_pairs"),
    ("revision/audits/Audit6-answers-*.csv",                    "audits/extraction_pairs"),
    ("revision/audits/Audit6-resolution-DNA-EE.csv",            "audits/extraction_pairs"),
    ("revision/audits/_keys-do-not-open/Audit6-Claim-or-not-KEY.csv", "audits/extraction_pairs"),
    ("revision/audits/RESULTS-audit-6-both.md",                 "audits/extraction_pairs"),
    ("revision/audits/RESULTS-audit-6-resolved.md",             "audits/extraction_pairs"),
    ("revision/audits/Audit3-Declared-priorities-DNA.xlsx",     "audits/declared_priorities"),
    ("revision/audits/Audit3-Declared-priorities-EE.xlsx",      "audits/declared_priorities"),
    ("revision/audits/Audit3-resolution-DNA-EE.xlsx",           "audits/declared_priorities"),
    ("revision/audits/Audit3-resolved-matrix.csv",              "audits/declared_priorities"),
    ("revision/audits/_keys-do-not-open/Audit3-Declared-priorities-KEY.csv", "audits/declared_priorities"),
    ("revision/audits/RESULTS-audit-3-both.md",                 "audits/declared_priorities"),
    ("revision/audits/RESULTS-audit-3-resolved.md",             "audits/declared_priorities"),
    ("revision/audits/Audit2-SDG-mapping-DNA.xlsx",             "audits/sdg_mapping"),
    ("revision/audits/Audit2-SDG-mapping-EE.xlsx",              "audits/sdg_mapping"),
    ("revision/audits/_keys-do-not-open/Audit2-SDG-mapping-KEY.csv", "audits/sdg_mapping"),
    ("revision/audits/Audit2-disagreements.csv",                "audits/sdg_mapping"),
    ("revision/audits/RESULTS-audit-2-both.md",                 "audits/sdg_mapping"),
    ("revision/audits/score_audit2.py",                         "code/audits"),
    ("revision/audits/reduced/Audit1-Extraction-reduced-DNA.xlsx", "audits/extraction_listing"),
    ("revision/audits/_keys-do-not-open/Audit1-Extraction-KEY.csv", "audits/extraction_listing"),
    ("revision/audits/RESULTS-audits-1-3-DNA.md",               "audits/extraction_listing"),
    ("revision/audits/score_audits_1_3.py",                     "code/audits"),
    ("revision/audits/build_reduced_plan.py",                   "code/audits"),
    ("revision/audits/build_page_lookup.py",                    "code/audits"),
    ("revision/audits/AUDIT-LOG.md",                            "audits"),
    # ---- held-out evaluation: analysis scripts and aggregate outputs (rater nicknames recoded on copy) ----
    ("revision/round1-analysis/analyse_round1_all.py",          "code/round1_analysis"),
    ("revision/round1-analysis/analyse_round1_ci.py",           "code/round1_analysis"),
    ("revision/round1-analysis/analyse_round1_rater.py",        "code/round1_analysis"),
    ("revision/round1-analysis/analyse_remaining.py",           "code/round1_analysis"),
    ("revision/round1-analysis/analyse_round1_sens_no_*.py",    "code/round1_analysis", "analyse_round1_sens_without_raterC.py"),
    ("revision/round1-analysis/Round1-all-raters.md",           "data/ratings_round1/analysis"),
    ("revision/round1-analysis/Round1-both-phases.md",          "data/ratings_round1/analysis"),
    ("revision/round1-analysis/Round1-agreement-CI.md",         "data/ratings_round1/analysis"),
    ("revision/round1-analysis/Round1-agreement-CI.csv",        "data/ratings_round1/analysis"),
    ("revision/round1-analysis/Remaining-analyses-10Nov.md",    "data/ratings_round1/analysis"),
    ("revision/round1-analysis/Round1-sensitivity-without-*.md",    "data/ratings_round1/analysis", "Round1-sensitivity-without-RaterC.md"),
]
NEVER = ["*.env", "*/scorer/Pilot-Results/*", "*/scorer/handbooks-as-sent/*", ".env", "*.pdf.part", "*/data/reports/*", "*/chunks/*", "*/embeddings/*", "*reviews*", "*Reviewer*",
         "*Editor-Decision*", "*ERBOON*", "*sdg-credibility-web*", "*__pycache__*", "*.pyc", "*.DS_Store",
         "*Assurance-Statements-Corpus*", "*Corpus-Companies-Claims*", "*/scorer/Results/*", "*PRIVATE*"] + [f"*{k}*" for k in CODES]
KEEP_IN_RELEASE = {"README.md", ".gitignore", "tools/sync_release.py", "LICENSE"}
TEXT = {".py", ".md", ".txt", ".toml", ".json", ".csv", ".sh", ".example", ".cfg", ".yml", ".yaml", ".html"}
SECRET = re.compile(r"(sk-[A-Za-z0-9_\-]{20,}|sk-proj-[A-Za-z0-9_\-]{20,}|AKIA[0-9A-Z]{16}|land_sk_[A-Za-z0-9]{10,}|"
                    r"(OPENAI|LANDINGAI|ANTHROPIC|VISION_AGENT)_API_KEY\s*=\s*['\"]?[A-Za-z0-9_\-]{12,})")


def planned():
    rules = INCLUDE + (LATER if ROUND1_CLOSED else [])
    for rule in rules:
        pattern, dest = rule[0], rule[1]; newname = rule[2] if len(rule) > 2 else None
        if dest is None: continue
        for src in sorted(ROOT.glob(pattern)):
            if src.is_file() and (newname or not any(fnmatch.fnmatch(str(src), n) for n in NEVER)):
                yield src, REL / dest / (newname or src.name)


def sync():
    new = upd = same = 0
    expected = set()
    for src, dst in planned():
        expected.add(dst.resolve())
        dst.parent.mkdir(parents=True, exist_ok=True)
        rel = str(dst.relative_to(REL))
        if CODES and src.suffix.lower() in {".md", ".csv", ".txt", ".py"} and rel.startswith(RECODE_DIRS):
            text = src.read_text(encoding="utf-8", errors="strict")
            text = recode_code(text) if rel.startswith("code/round1_analysis") else recode(text)
            if dst.exists() and dst.read_text(encoding="utf-8", errors="ignore") == text: same += 1; continue
            if dst.exists(): upd += 1
            else: new += 1
            dst.write_text(text, encoding="utf-8"); continue
        if dst.exists() and filecmp.cmp(src, dst, shallow=False): same += 1; continue
        if dst.exists(): upd += 1
        else: new += 1
        shutil.copy2(src, dst)
    stale = [p for p in REL.rglob("*") if p.is_file() and ".git" not in p.parts
             and p.resolve() not in expected and str(p.relative_to(REL)) not in KEEP_IN_RELEASE]
    print(f"sync: {new} new, {upd} updated, {same} unchanged")
    if stale:
        print("in release/ but no longer produced by the sync (review, then delete or keep):")
        for p in stale: print("   ", p.relative_to(REL))


def check() -> bool:
    ok = True
    for p in REL.rglob("*"):
        if not p.is_file() or ".git" in p.parts: continue
        rel = str(p.relative_to(REL))
        if any(fnmatch.fnmatch(rel, n) or fnmatch.fnmatch(p.name, n) for n in NEVER) or p.suffix.lower() == ".pdf" and "forms" not in rel:
            print("BLOCKED file in release/:", rel); ok = False
        if not ROUND1_CLOSED and ("KEY" in p.name or "returned" in rel or "ratings_round1" in rel):
            print("BLOCKED (Round 1 still open):", rel); ok = False
        if p.suffix.lower() in TEXT and p.stat().st_size < 50_000_000:
            body = p.read_text(errors="ignore")
            if SECRET.search(body): print("POSSIBLE SECRET in:", rel); ok = False
            fl = re.I if rel.startswith("code/round1_analysis") else 0
            hit = [k for k in CODES if re.search(r"(?<![A-Za-z])" + k + r"(?![A-Za-z])", body, fl)]   # upper-case nicknames (any case in the recoded scripts)
            if hit: print("RATER NICKNAME in:", rel, hit); ok = False
        if any(k.lower() in p.name.lower().replace("float", "") for k in CODES if len(k) > 3): print("RATER NICKNAME in file name:", rel); ok = False
    if not CODES: print("WARNING: scorer/rater-codes-PRIVATE.json not found; nickname check not run"); ok = False
    print("check:", "OK" if ok else "FAILED - do not commit")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not a.check: sync()
    sys.exit(0 if check() else 1)
