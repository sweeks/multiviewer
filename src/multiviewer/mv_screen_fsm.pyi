"""
CLI wrapper that exhaustively explores the MvScreen state space and writes two artifacts:
the full FSM (gitignored) and a small summary with a SHA-256 digest (committed).

We rerun this in CI (validate-repo) to detect unintentional changes to the FSM, and run it
manually when we intentionally regenerate the reference summary.
"""
