#!/bin/bash
# =============================================================
# 3-Way Extractor Comparison: ADE vs PyMuPDF vs pdfplumber
# =============================================================
#
# Runs Phase 1 extraction with PyMuPDF and pdfplumber on 5 reports,
# then Phases 2-3 on each set. ADE Phase 1 outputs already exist.
#
# Usage:
#   ./run_extractor_comparison.sh              # Run everything
#   ./run_extractor_comparison.sh phase1       # Phase 1 only (extraction)
#   ./run_extractor_comparison.sh phase23      # Phases 2-3 only (reuse Phase 1)
#
# Selected reports (5, stratified by type/length/sector):
#   1. BCP-2024-SR-EN     (Energy, SR, 107pp, 308 ADE claims)
#   2. AOT-2024-OR+SR-EN  (Transport, OR+SR, 360pp, 162 ADE claims)
#   3. MINT-2024-SR-EN    (Real Estate, SR, 75pp, 128 ADE claims)
#   4. SCB-2024-SR-EN     (Banking, SR, 132pp, 385 ADE claims)
#   5. CPN-2024-OR+SR-EN  (Real Estate, OR+SR, 258pp, 86 ADE claims)
# =============================================================

cd "$(dirname "$0")"

REPORTS_DIR="data/reports/2024"
COMP_DIR="data/outputs/extractor_comparison"
mkdir -p "$COMP_DIR"

# The 5 selected reports
REPORTS=(
    "BCP-2024-SR-EN.pdf|Bangchak Corporation|Energy|2024"
    "AOT-2024-OR+SR-EN.pdf|Airports of Thailand|Transportation|2024"
    "MINT-2024-SR-EN.pdf|Minor International|Real Estate|2024"
    "SCB-2024-SR-EN.pdf|Siam Commercial Bank|Banking & Finance|2024"
    "CPN-2024-OR+SR-EN.pdf|Central Pattana|Real Estate|2024"
)

EXTRACTORS=("pymupdf" "pdfplumber")
MODE=${1:-"all"}

# =============================================================
# PHASE 1: Extract with PyMuPDF and pdfplumber
# =============================================================
if [[ "$MODE" == "all" || "$MODE" == "phase1" ]]; then
    echo ""
    echo "============================================"
    echo "PHASE 1: PDF Extraction (PyMuPDF + pdfplumber)"
    echo "============================================"

    for extractor in "${EXTRACTORS[@]}"; do
        echo ""
        echo "--- Extractor: $extractor ---"

        for entry in "${REPORTS[@]}"; do
            IFS='|' read -r filename company sector year <<< "$entry"
            stem="${filename%.pdf}"
            outfile="$COMP_DIR/${extractor}_${stem}_phase1.json"

            # Skip if already exists
            if [ -f "$outfile" ]; then
                echo "  SKIP: $outfile already exists"
                continue
            fi

            echo ""
            echo "  Processing: $filename ($extractor)"

            python run_phase1.py \
                --report "$REPORTS_DIR/$filename" \
                --company "$company" \
                --sector "$sector" \
                --year "$year" \
                --extractor "$extractor"

            # Planner now saves with extractor prefix automatically
            # Move from outputs/ to comparison directory
            prefixed_out="data/outputs/${extractor}_${stem}_phase1.json"
            if [ -f "$prefixed_out" ]; then
                mv "$prefixed_out" "$outfile"
                echo "  Saved: $outfile"
            else
                echo "  WARNING: Expected output not found: $prefixed_out"
            fi
        done
    done

    # Copy ADE Phase 1 outputs to comparison directory for completeness
    echo ""
    echo "--- Copying existing ADE Phase 1 outputs ---"
    for entry in "${REPORTS[@]}"; do
        IFS='|' read -r filename company sector year <<< "$entry"
        stem="${filename%.pdf}"
        ade_src="data/outputs/${stem}_phase1.json"
        ade_dst="$COMP_DIR/ade_${stem}_phase1.json"

        if [ -f "$ade_src" ] && [ ! -f "$ade_dst" ]; then
            cp "$ade_src" "$ade_dst"
            echo "  Copied: $ade_dst"
        elif [ -f "$ade_dst" ]; then
            echo "  SKIP: $ade_dst already exists"
        else
            echo "  WARNING: ADE output not found: $ade_src"
        fi
    done

    echo ""
    echo "Phase 1 extraction complete."
    echo "Files saved to: $COMP_DIR"
fi

# =============================================================
# PHASES 2-3: SDG Mapping + Credibility Scoring
# =============================================================
if [[ "$MODE" == "all" || "$MODE" == "phase23" ]]; then
    echo ""
    echo "============================================"
    echo "PHASES 2-3: SDG Mapping + Credibility Scoring"
    echo "============================================"

    CONCURRENCY=5

    for extractor in "${EXTRACTORS[@]}"; do
        echo ""
        echo "--- Extractor: $extractor ---"

        for entry in "${REPORTS[@]}"; do
            IFS='|' read -r filename company sector year <<< "$entry"
            stem="${filename%.pdf}"
            phase1_file="$COMP_DIR/${extractor}_${stem}_phase1.json"
            full_file="$COMP_DIR/${extractor}_${stem}_full.json"

            # Skip if full output already exists
            if [ -f "$full_file" ]; then
                echo "  SKIP: $full_file already exists"
                continue
            fi

            if [ ! -f "$phase1_file" ]; then
                echo "  WARNING: Phase 1 not found: $phase1_file. Run phase1 first."
                continue
            fi

            echo ""
            echo "  Processing: $stem ($extractor) — Phases 2-3"

            # Create a temporary single-entry manifest for this report
            tmp_manifest=$(mktemp)
            echo "filename,company,sector,report_year,self_declared_sdgs" > "$tmp_manifest"
            echo "$filename,$company,$sector,$year," >> "$tmp_manifest"

            # We need to temporarily copy the phase1 file to the main outputs dir
            # so the pipeline can find it via --skip-phase1
            cp "$phase1_file" "data/outputs/${stem}_phase1.json.bak" 2>/dev/null
            cp "$phase1_file" "data/outputs/${stem}_phase1.json"

            python main.py \
                --manifest "$tmp_manifest" \
                --skip-phase1 \
                --skip-phase4 \
                --concurrency $CONCURRENCY \
                --no-dashboard

            # Move full output to comparison directory
            default_full="data/outputs/${stem}_full.json"
            if [ -f "$default_full" ]; then
                mv "$default_full" "$full_file"
                echo "  Saved: $full_file"
            fi

            # Restore original phase1 file if we backed it up
            if [ -f "data/outputs/${stem}_phase1.json.bak" ]; then
                mv "data/outputs/${stem}_phase1.json.bak" "data/outputs/${stem}_phase1.json"
            fi

            rm -f "$tmp_manifest"
        done
    done

    echo ""
    echo "Phases 2-3 complete for all extractors."
fi

echo ""
echo "============================================"
echo "COMPARISON COMPLETE"
echo "============================================"
echo "Output directory: $COMP_DIR"
echo ""
echo "Next step: Run the analysis script:"
echo "  python analyze_extractor_comparison.py"
