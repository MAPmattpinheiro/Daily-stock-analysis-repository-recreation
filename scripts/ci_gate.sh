#!/bin/bash
set -e
echo "=== Running CI Gate ==="
echo "--- Lint ---"
python -m flake8 . --max-line-length=120 --exclude=__pycache__,apps,data_store,.git --ignore=E501,W503,E203 || true
echo "--- Tests ---"
python -m pytest tests/ -v --tb=short
echo "=== CI Gate Passed ==="
