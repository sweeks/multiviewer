# For Codex / AI context

- Purpose: quick shared context for Codex tasks in this repo. Keep concise; update when
  workflows change.
- Reminder: you are a developer—read and follow `docs/developer-guide.md` before working.
- Rule: never change code unless explicitly instructed to do so; discuss designs and agree
  on them before writing any code; only start coding after I explicitly say "code it".
- Rule: keep changes minimal and focused on the current goal; avoid unrelated rewrites.
- Rationale: off-scope edits make diffs noisy, slow reviews, and hide the intent of the
  requested change; only touch code needed for the current task or to fix the resulting
  errors.
- Rule: make only narrow, task-relevant edits; don't “improve” nearby code unless it is
  part of the requested task or needed to fix a resulting error.
- Rule: keep this doc lean—avoid duplicating `docs/developer-guide.md`; prefer linking or
  deferring to it instead of restating details here.
- Rule: when cleaning unused imports, use the static analyzer (Pyright/Pylance) or a quick
  AST-based check (e.g., `.venv/bin/python - <<'PY' ...`) to identify and remove only what
  is truly unused; keep it fast and automated rather than guessing.
- Rule: always run `pyright` after code changes (in addition to tests) to catch type
  errors early; mention any pyright findings in your response.
- Rule: use repo tools from the `.venv`: e.g., run pyright via `.venv/bin/pyright` (or
  `bin/validate-repo.sh`), and prefer helper scripts over ad-hoc commands.
- Reading note: when asked to "read for-codex", do not summarize—it's just to refresh your
  context.
- Project: multiviewer remote-control daemon for J-Tech MV41A + four Apple TVs + LG
  soundbar/TV. Python asyncio daemon under `src/multiviewer`, remote buttons send HTTP to
  daemon.
- Notes: prefer `rg` for search; files of interest include `mv.py` (state machine),
  `jtech.py` (device sync), `atv.py` (Apple TV control), `volume.py` (soundbar IR via
  WF2IR), `http_server.py` (command endpoint).
- VS Code: `.vscode/settings.json` is tracked; team is macOS and uses a repo-root `.venv`
  (settings point Python/terminal to `.venv/bin/python` and add `src` to
  `python.analysis.extraPaths`). `.vscode` folder is not gitignored; add new files
  intentionally.
- Editor: VS Code on macOS; in inline git diffs use the editor title bar “…” menu → “Open
  File” to jump to the real file at the same line.
- Formatting: run `bin/validate-repo.sh` (Black, mdformat, Ruff, Pyright, tests); the old
  `bin/format-code.sh` has been subsumed.
