#!/bin/zsh

set -e -u -o pipefail

root=$(cd -- "$(dirname "$0")"/.. && pwd)

cd "$root"

if [ ! -x ".venv/bin/black" ]; then
  echo "black not found. Run bin/setup-repo.sh or pip install -r requirements." >&2
  exit 1
fi

.venv/bin/black src tests
