#!/bin/bash
# Run Phases 2-3 (SDG Mapping + Credibility Scoring) in batches of 6
# Uses existing Phase 1 outputs (--skip-phase1)
#
# Usage:
#   ./run_phase23_batches.sh          # Run all 5 batches sequentially
#   ./run_phase23_batches.sh 1        # Run only batch 1
#   ./run_phase23_batches.sh 3 5      # Run batches 3 through 5
#
# Each batch processes 6 reports through Phases 2-3.
# Concurrency is set to 5 parallel API calls per report.
# Phase 4 (cross-report comparison) is skipped per-batch and should be
# run separately after all batches complete.

cd "$(dirname "$0")"

CONCURRENCY=5
START_BATCH=${1:-1}
END_BATCH=${2:-5}

echo "============================================"
echo "SDG Credibility Framework — Phases 2-3"
echo "Running batches $START_BATCH through $END_BATCH"
echo "Concurrency: $CONCURRENCY parallel API calls"
echo "============================================"

for i in $(seq $START_BATCH $END_BATCH); do
    MANIFEST="data/manifest_2024_batch${i}.csv"

    if [ ! -f "$MANIFEST" ]; then
        echo "ERROR: $MANIFEST not found, skipping batch $i"
        continue
    fi

    echo ""
    echo "──────────────────────────────────────────"
    echo "BATCH $i of 5 — Starting at $(date '+%H:%M:%S')"
    echo "──────────────────────────────────────────"

    python main.py \
        --manifest "$MANIFEST" \
        --skip-phase1 \
        --skip-phase4 \
        --concurrency $CONCURRENCY \
        --no-dashboard

    EXIT_CODE=$?

    if [ $EXIT_CODE -ne 0 ]; then
        echo "WARNING: Batch $i exited with code $EXIT_CODE"
        echo "You can resume from batch $i by running:"
        echo "  ./run_phase23_batches.sh $i $END_BATCH"
        read -p "Continue to next batch? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Stopped at batch $i."
            exit 1
        fi
    else
        echo "Batch $i complete at $(date '+%H:%M:%S')"
    fi
done

echo ""
echo "============================================"
echo "ALL BATCHES COMPLETE"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Run Phase 4 (cross-report comparison):"
echo "     python main.py --manifest data/manifest_2024.csv --skip-phase1 --concurrency 5"
echo ""
echo "  2. Or regenerate dashboards only:"
echo "     python main.py --dashboard-only"
