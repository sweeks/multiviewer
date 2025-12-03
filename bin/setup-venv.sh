#!/bin/zsh

set -e -u -o pipefail
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
echo 'RUN: source .venv/bin/activate'
