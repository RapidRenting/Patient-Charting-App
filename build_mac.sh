#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]:-}" != "$0" ]]; then
  echo "Run this script as './build_mac.sh' (do not use 'source build_mac.sh')."
  return 1 2>/dev/null || exit 1
fi

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found."
  exit 1
fi

if [[ ! -d "venv" ]]; then
  python3 -m venv venv
fi

source "venv/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

rm -rf build dist

pyinstaller \
  --windowed \
  --onedir \
  --name "PatientCharting" \
  --add-data "templates:templates" \
  app.py

echo "Build complete: dist/PatientCharting.app"
