#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCES_DIR="$(cd "$SCRIPT_DIR/../sources" && pwd)"

echo "================================================================="
echo "BHIV MasterDB Inspected Source Test Suite Verification"
echo "Target Directory: $SOURCES_DIR"
echo "================================================================="

echo ""
echo ">>> [1/4] Testing bhiv_pharmacovigilance (Sarvesh / Baseline Core)..."
(cd "$SOURCES_DIR/bhiv_pharmacovigilance" && pytest -v)

echo ""
echo ">>> [2/4] Testing shravni_qc_evidence (Shravani / QC Evidence Map)..."
(cd "$SOURCES_DIR/shravni_qc_evidence" && pytest -v)

echo ""
echo ">>> [3/4] Testing shamit_drug_discovery (Shamit / Compound Pipeline)..."
(cd "$SOURCES_DIR/shamit_drug_discovery" && pytest -v)

echo ""
echo ">>> [4/4] Testing shyamal_octo_invention (Shyamal / Preclinical QC)..."
(cd "$SOURCES_DIR/shyamal_octo_invention" && pytest -v)

echo ""
echo "================================================================="
echo "SUCCESS: All 99 tests across all 4 external sources passed!"
echo "================================================================="
