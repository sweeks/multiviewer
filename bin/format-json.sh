#!/usr/bin/env bash
set -euo pipefail

# Format one or more JSON files using python -m json.tool with stable sorting.

if [[ "$#" -lt 1 ]]; then
  echo "usage: $0 <file> [file...]" >&2
  exit 1
fi

python_bin="${PYTHON_BIN:-$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.venv/bin/python}"

for file in "$@"; do
  if [[ ! -f "$file" ]]; then
    echo "format-json: missing file: $file" >&2
    exit 1
  fi
  tmp="${file}.tmp"
  "$python_bin" -m json.tool --sort-keys --indent 2 "$file" >"$tmp"
  mv "$tmp" "$file"
done
