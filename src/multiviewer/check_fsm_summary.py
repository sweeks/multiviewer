from __future__ import annotations

import json
from pathlib import Path

from .mv_screen import MvScreen


def compute_summary() -> dict[str, object]:
    machine = MvScreen().explore_fsm_machine()
    return machine.summary()


def main() -> None:
    summary_path = Path(__file__).resolve().parent / "mv_screen_fsm-summary.json"
    if not summary_path.exists():
        print(f"FSM summary file missing: {summary_path}")
        raise SystemExit(1)
    expected = json.loads(summary_path.read_text())
    current = compute_summary()
    if current != expected:
        print("FSM summary mismatch; run bin/explore-fsm.sh to regenerate")
        print("expected:", expected)
        print("current :", current)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
