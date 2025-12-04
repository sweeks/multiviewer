# For Codex / AI context

- Purpose: quick shared context for Codex tasks in this repo. Keep concise; update when workflows change.
- Project: multiviewer remote-control daemon for J-Tech MV41A + four Apple TVs + LG soundbar/TV. Python asyncio daemon under `src/multiviewer`, remote buttons send HTTP to daemon.
- Start daemon: `bin/start-mvd.sh` (kills prior daemon, logs under `var/mvd.log`).
- Stop daemon: `python -m multiviewer.stop_mvd` (or let start script kill prior instance).
- Tests: `python tests/tests.py all` (end-to-end, but jtech commands disabled in tests via `should_send_commands_to_device = False`; still uses asyncio event loop).
- Config: `src/multiviewer/config.py` holds IP/hostnames; Apple TV pairing lives in external `.pyatv.conf` (not in repo).
- Notes: prefer `rg` for search; files of interest include `mv.py` (state machine), `jtech.py` (device sync), `atv.py` (Apple TV control), `volume.py` (soundbar IR via WF2IR), `http_server.py` (command endpoint).
