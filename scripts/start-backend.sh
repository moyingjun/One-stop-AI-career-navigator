#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_EXE="$PROJECT_ROOT/.venv/Scripts/python.exe"
CHECK_SCRIPT="$PROJECT_ROOT/scripts/check-python-env.py"

if [[ ! -x "$PYTHON_EXE" ]]; then
  echo "Project Python not found or not executable: $PYTHON_EXE" >&2
  exit 1
fi

unset PYTHONPATH
unset PYTHONHOME

cd "$PROJECT_ROOT"
"$PYTHON_EXE" "$CHECK_SCRIPT"
"$PYTHON_EXE" -m uvicorn main:app --reload
