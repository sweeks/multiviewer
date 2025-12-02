#!/bin/zsh

set -e -u -o pipefail
root=$(cd -- "$(dirname "$0")"/.. && pwd)
mkdir -p "$root"/var
nohup "$root"/.venv/bin/python -u -m multiviewer.mvd >>"$root"/var/mvd.log 2>&1 &
"$root"/bin/mvd-tail.sh