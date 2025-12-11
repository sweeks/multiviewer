#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

"$ROOT/.venv/bin/python3" -m ruff check src tests --fix
"$ROOT/.venv/bin/python3" -m black src tests
