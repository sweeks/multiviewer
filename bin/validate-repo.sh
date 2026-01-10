#!/usr/bin/env bash
set -euo pipefail

# validate-repo should exit nonzero if any formatter/type checker/test fails or if
# formatting changes files.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

mkdir -p "$ROOT/var"
VALIDATE_LOG="$ROOT/var/validate-repo.log"
: >"$VALIDATE_LOG"
validate_start_seconds=$SECONDS
validate_start_time=$(date +"%Y-%m-%dT%H:%M:%S%z")
echo "validate-repo start ${validate_start_time}" >>"$VALIDATE_LOG"

# Run a command quietly; on failure, point to its log.
run_quiet() {
  local name="$1"
  shift
  local log="$ROOT/var/${name##*/}.log"
  local start_seconds=$SECONDS
  local start_time
  start_time=$(date +"%Y-%m-%dT%H:%M:%S%z")

  {
    echo "==> ${name}: start ${start_time}"
    "$@"
  } >"$log" 2>&1
  local status=$?

  local end_time
  end_time=$(date +"%Y-%m-%dT%H:%M:%S%z")
  local duration=$((SECONDS - start_seconds))
  printf '==> %s: end %s (duration: %ss, exit=%s)\n' \
    "$name" "$end_time" "$duration" "$status" >>"$log"
  printf '%-16s duration=%ss exit=%s\n' \
    "$name" "$duration" "$status" >>"$VALIDATE_LOG"

  if (( status != 0 )); then
    echo "validate-repo: ${name} failed (see ${log})" >&2
    exit 1
  fi
}

# Code formatting (auto-fix)
run_quiet black "$ROOT/.venv/bin/black" --quiet src tests

# Docs formatting (auto-fix)
run_quiet mdformat "$ROOT/.venv/bin/mdformat" --wrap 90 README.md docs

# Apple TV credentials formatting (auto-fix)
run_quiet pyatv-conf "$ROOT/bin/format-json.sh" "$ROOT/src/multiviewer/pyatv.conf"

# Ruff (configured in pyproject)
run_quiet ruff "$ROOT/.venv/bin/ruff" check --fix src tests

# Type checking
run_quiet pyright env PYTHONPATH="$PYTHONPATH" "$ROOT/.venv/bin/pyright"

run_quiet tests "$ROOT/bin/test-all.sh"
run_quiet fsm-summary "$ROOT/.venv/bin/python" -m multiviewer.mv_screen_fsm --validate

validate_end_time=$(date +"%Y-%m-%dT%H:%M:%S%z")
validate_duration=$((SECONDS - validate_start_seconds))
echo "validate-repo end ${validate_end_time} (duration: ${validate_duration}s)" >>"$VALIDATE_LOG"

echo "validate-repo: ok"
