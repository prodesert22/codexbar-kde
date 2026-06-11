#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Prefer pytest + xdist for parallel runs (see requirements-dev.txt).
# Fall back to stdlib unittest when pytest is not installed — the test
# suite is plain unittest.TestCase, so both runners work unchanged.
if python3 -m pytest --version >/dev/null 2>&1; then
    python3 -m pytest "$ROOT_DIR/tests" -n auto -q
else
    echo "pytest not found; running serial unittest (pip install -r requirements-dev.txt for parallel)."
    python3 -m unittest discover -s "$ROOT_DIR/tests" -p 'test_*.py'
fi

if command -v qmllint >/dev/null 2>&1; then
    qmllint "$ROOT_DIR/package/contents/ui/main.qml" "$ROOT_DIR/package/contents/ui/UsageBar.qml"
else
    echo "qmllint not found; skipped QML lint."
fi
