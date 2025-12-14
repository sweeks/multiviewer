#!/bin/zsh

set -e -u -o pipefail

root=$(cd -- "$(dirname "$0")"/.. && pwd)

mdformat_bin=""

if command -v mdformat >/dev/null 2>&1; then
  mdformat_bin=$(command -v mdformat)
elif [ -x "$root/.venv/bin/mdformat" ]; then
  mdformat_bin="$root/.venv/bin/mdformat"
fi

if [ -z "$mdformat_bin" ]; then
  echo "mdformat not found. Install with: .venv/bin/pip install mdformat" >&2
  exit 1
fi

cd "$root"

# Format README plus all docs/*.md
zsh -c 'mdformat --wrap 90 README.md docs/**/*.md' mdformat="$mdformat_bin"
