#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

if [[ ! -x "$ROOT/.venv/bin/python3" ]]; then
  echo "Missing .venv/. Activate or create it before validating." >&2
  exit 1
fi

# Run a command quietly; on failure, show its output and exit.
run_quiet() {
  local log
  log="$(mktemp)"
  trap 'rm -f "$log"' RETURN
  if ! "$@" >"$log" 2>&1; then
    cat "$log" >&2
    exit 1
  fi
  rm -f "$log"
  trap - RETURN
}

# Code formatting (auto-fix)
run_quiet "$ROOT/.venv/bin/black" --quiet src tests

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
run_quiet "$mdformat_bin" --wrap 90 "${doc_paths[@]}"

# Ruff (configured in pyproject)
run_quiet "$ROOT/.venv/bin/ruff" check src tests

# Type checking
run_quiet env PYTHONPATH="$PYTHONPATH" "$ROOT/.venv/bin/pyright"

# Stub/runtime consistency
run_quiet env PYTHONPATH="$PYTHONPATH" "$ROOT/.venv/bin/pyright" --verifytypes multiviewer --ignoreexternal

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
