#!/usr/bin/env bash
# Build a standalone Knowledge Base executable (macOS / Linux).
# Output: dist/kb-tool
set -euo pipefail
cd "$(dirname "$0")"

python -m pip install -r requirements.txt

pyinstaller --onefile --noconsole \
    --add-data "templates:templates" \
    --add-data "static:static" \
    --add-data "config.yaml:." \
    --name kb-tool \
    launcher.py

echo "Built: dist/kb-tool"
echo "Note: posts/ and .kb/ live next to the executable (user data, outside the bundle)."
