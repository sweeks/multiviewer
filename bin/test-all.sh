#!/bin/zsh

set -e -u -o pipefail
root=$(cd -- "$(dirname "$0")"/.. && pwd)
log="$root/var/tests.log"
mkdir -p "$root/var"
{
  echo "===== $(date): bin/test-all.sh"
  "$root"/.venv/bin/python tests/tests.py all
} 2>&1 | tee "$log"

if grep -q "EXPECT:" "$log"; then
  echo "Expect/Actual mismatches (see ${log})" >&2
  exit 1
fi
