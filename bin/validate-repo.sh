#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

if [[ ! -x "$ROOT/.venv/bin/python3" ]]; then
  echo "Missing .venv/. Activate or create it before validating." >&2
  exit 1
fi

mkdir -p "$ROOT/var"

# Run a command quietly; on failure, point to its log.
run_quiet() {
  local name="$1"
  shift
  local log="$ROOT/var/${name##*/}.log"
  if ! "$@" >"$log" 2>&1; then
    echo "validate-repo: ${name} failed (see ${log})" >&2
    exit 1
  fi
}

# Code formatting (auto-fix)
run_quiet black "$ROOT/.venv/bin/black" --quiet src tests

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
run_quiet mdformat "$mdformat_bin" --wrap 90 "${doc_paths[@]}"

# Ruff (configured in pyproject)
run_quiet ruff "$ROOT/.venv/bin/ruff" check src tests

# Type checking
run_quiet pyright env PYTHONPATH="$PYTHONPATH" "$ROOT/.venv/bin/pyright"

# Stub/runtime consistency
run_quiet pyright-verify env PYTHONPATH="$PYTHONPATH" "$ROOT/.venv/bin/pyright" --verifytypes multiviewer --ignoreexternal

tests_log="$ROOT/var/tests.log"
if ! "$ROOT/bin/test-all.sh" >"$tests_log" 2>&1; then
  echo "validate-repo: tests failed (see ${tests_log})" >&2
  exit 1
fi

if grep -q "EXPECT:" "$tests_log"; then
  echo "validate-repo: Expect/Actual mismatches (see ${tests_log})" >&2
  exit 1
fi

echo "validate-repo: ok"
