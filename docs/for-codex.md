# For Codex / AI context

- Purpose: quick shared context for Codex tasks in this repo. Keep concise; update when
  workflows change.
- Rule: never change code unless explicitly instructed to do so; discuss designs and agree
  on them before writing any code; only start coding after I explicitly say "code it".
- Reading note: when asked to "read for-codex", do not summarize—it's just to refresh your
  context.
- Project: multiviewer remote-control daemon for J-Tech MV41A + four Apple TVs + LG
  soundbar/TV. Python asyncio daemon under `src/multiviewer`, remote buttons send HTTP to
  daemon.
- Start daemon: `bin/start-mvd.sh` (kills prior daemon, logs under `var/mvd.log`).
- Stop daemon: `python -m multiviewer.stop_mvd` (or let start script kill prior instance).
- Tests: `PYTHONPATH=src .venv/bin/python tests/tests.py` (end-to-end, but jtech commands
  disabled in tests via `should_send_commands_to_device = False`; still uses asyncio event
  loop). Make sure the repo `.venv` is active or referenced explicitly.
- Workflow note: user runs tests (see `bin/test-all.sh`) and provides the log; Codex
  should run `bin/test-all.sh` after changes (device I/O disabled by default) and include
  the results in the response.
- Config: `src/multiviewer/config.py` holds IP/hostnames; Apple TV pairing lives in
  external `.pyatv.conf` (not in repo).
- Notes: prefer `rg` for search; files of interest include `mv.py` (state machine),
  `jtech.py` (device sync), `atv.py` (Apple TV control), `volume.py` (soundbar IR via
  WF2IR), `http_server.py` (command endpoint).
- Default workflow: after changes, run `bin/test-all.sh` to exercise the end-to-end tests
  (they now disable device I/O by default), and share the log.
- Docs: use `bin/format-docs.sh` (mdformat, wrap 90) after editing markdown files.
- Pyright: `pyrightconfig.json` points the CLI at the repo `.venv` and adds `src` to
  `extraPaths`; Pylance already picks this up via VS Code settings.
- VS Code: `.vscode/settings.json` is tracked; team is macOS and uses a repo-root `.venv`
  (settings point Python/terminal to `.venv/bin/python` and add `src` to
  `python.analysis.extraPaths`). `.vscode` folder is not gitignored; add new files
  intentionally.
- Editor: VS Code on macOS; in inline git diffs use the editor title bar “…” menu → “Open
  File” to jump to the real file at the same line.
- Formatting: run `bin/format-code.sh` to apply Black across `src` and `tests`, and
  `bin/format-docs.sh` for markdown.
