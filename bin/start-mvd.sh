#!/bin/zsh

set -e -u -o pipefail
root=$(cd -- "$(dirname "$0")"/.. && pwd)
mkdir -p "$root"/var
cd "$root"/var
nohup "$root"/.venv/bin/python -u -m multiviewer.mvd >>mvd.log 2>&1 &
"$root"/bin/tail-mvd.sh