#!/bin/zsh

set -e -u -o pipefail
root=$(cd -- "$(dirname "$0")"/.. && pwd)
tail -n 100 -F "$root"/var/mvd.log
