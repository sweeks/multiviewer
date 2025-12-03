#!/bin/zsh

set -e -u -o pipefail
root=$(cd -- "$(dirname "$0")"/.. && pwd)
"$root"/.venv/bin/python tests/tests.py all