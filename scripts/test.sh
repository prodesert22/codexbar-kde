#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 -m unittest discover -s "$ROOT_DIR/tests" -p 'test_*.py'

if command -v qmllint >/dev/null 2>&1; then
    qmllint "$ROOT_DIR/package/contents/ui/main.qml" "$ROOT_DIR/package/contents/ui/UsageBar.qml"
else
    echo "qmllint not found; skipped QML lint."
fi
