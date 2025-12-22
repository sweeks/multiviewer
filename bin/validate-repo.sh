#!/usr/bin/env bash
set -euo pipefail

# validate-repo should exit nonzero if any formatter/type checker/test fails or if
# formatting changes files.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

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
run_quiet mdformat "$ROOT/.venv/bin/mdformat" --wrap 90 README.md docs

# Fail if formatting changed files
if ! git diff --quiet --exit-code; then
  echo "validate-repo: formatting changed files; review/stage and re-run" >&2
  exit 1
fi

# Ruff (configured in pyproject)
run_quiet ruff "$ROOT/.venv/bin/ruff" check src tests

# Type checking
run_quiet pyright env PYTHONPATH="$PYTHONPATH" "$ROOT/.venv/bin/pyright"

# Stub/runtime consistency
run_quiet pyright-verify env PYTHONPATH="$PYTHONPATH" "$ROOT/.venv/bin/pyright" --verifytypes multiviewer --ignoreexternal

run_quiet tests "$ROOT/bin/test-all.sh"

echo "validate-repo: ok"
