#!/bin/zsh

set -e -u -o pipefail

# Always operate from repo root so relative paths work even when invoked elsewhere.
script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
project_root="$(cd -- "${script_dir}/.." && pwd)"
cd "${project_root}"

if command -v git >/dev/null 2>&1; then
  git config core.hooksPath githooks
fi

rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m ensurepip --upgrade
pip install --upgrade pip
pip install -e .
echo 'RUN: source .venv/bin/activate'
