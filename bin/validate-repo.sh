#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

if [[ ! -x "$ROOT/.venv/bin/python3" ]]; then
  echo "Missing .venv/. Activate or create it before validating." >&2
  exit 1
fi

# Code formatting (auto-fix)
if ! "$ROOT/.venv/bin/black" src tests; then
  echo "Black formatting failed." >&2
  exit 1
fi

# Docs formatting (auto-fix)
mdformat_bin=""
if command -v mdformat >/dev/null 2>&1; then
  mdformat_bin=$(command -v mdformat)
elif [[ -x "$ROOT/.venv/bin/mdformat" ]]; then
  mdformat_bin="$ROOT/.venv/bin/mdformat"
fi
if [[ -z "$mdformat_bin" ]]; then
  echo "mdformat not found. Install with: .venv/bin/pip install mdformat" >&2
  exit 1
fi
doc_paths=(README.md)
while IFS= read -r -d '' p; do
  doc_paths+=("$p")
done < <(find docs -name '*.md' -print0)
if ! "$mdformat_bin" --wrap 90 "${doc_paths[@]}"; then
  echo "mdformat failed." >&2
  exit 1
fi

# Ruff (configured in pyproject)
if ! "$ROOT/.venv/bin/ruff" check src tests >/dev/null; then
  echo "Ruff reported issues." >&2
  exit 1
fi

# Type checking
if ! pyright_out="$(PYTHONPATH="$PYTHONPATH" "$ROOT/.venv/bin/pyright" 2>&1 >/dev/null)"; then
  echo "Pyright reported type errors." >&2
  echo "$pyright_out" >&2
  exit 1
fi

# Stub/runtime consistency
if ! verify_out="$(PYTHONPATH="$PYTHONPATH" "$ROOT/.venv/bin/pyright" --verifytypes multiviewer --ignoreexternal 2>&1 >/dev/null)"; then
  echo "Pyright verifytypes reported inconsistencies." >&2
  echo "$verify_out" >&2
  exit 1
fi

log="$(mktemp)"
trap 'rm -f "$log"' EXIT

# Run the test suite and fail if any Expect/Actual mismatches appear.
if ! "$ROOT/bin/test-all.sh" >"$log" 2>&1; then
  cat "$log" >&2
  exit 1
fi

if grep -q "EXPECT:" "$log"; then
  cat "$log" >&2
  echo "Expect/Actual mismatches detected. Fix tests before proceeding." >&2
  exit 1
fi

echo "validate-repo: ok"
