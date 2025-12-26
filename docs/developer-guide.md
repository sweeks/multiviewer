# Repo setup

After checking out the repo, run [setup-repo.sh](../bin/setup-repo.sh) to create `.venv`,
install tools, and setup git hooks.

In [pyproject.toml](../pyproject.toml), we specify dependencies, including the tools:
(`black`, `mdformat`, `pyright`, `ruff`) and their configuration. We configure `pyright`
with [pyrightconfig.json](../pyrightconfig.json).

Run [validate-repo.sh](../bin/validate-repo.sh) to run all those tools over the entire
codebase, as well as [test-all.sh](../bin/test-all.sh), which runs the
[regression tests](../tests/).

The [pre-commit hook](../githooks/pre-commit) runs `validate-repo.sh`, and fails if any
validation fails or reformats code.

# Setting up the Remote Control Home Screen

Each remote-control button has a `.shortcut` and `.jpg` in
[remote-control/](../remote-control/). In iOS Shortcuts, use `Add to Home Screen` and pick
the matching icon; the main shortcut just needs to be added and pointed at the daemon
hostname.

# Scripts layout

Small shell wrappers live in [bin/](../bin), and they should do as little Python as
possible. The corresponding Python entry points live under
[src/multiviewer/](../src/multiviewer/) and are invoked with `python -m` from the shell
scripts (e.g., [explore-fsm.sh](../bin/explore-fsm.sh) runs
`python -m multiviewer.explore_fsm`).

# Configuring and Running the Daemon

The daemon is configured in [config.py](../src/multiviewer/config.py), which holds host
names, IPs, and ports. The daemon also uses a `.pyatv.conf` outside this repo with pairing
info for the Apple TVs (needed for `pyatv` to connect).

Start the daemon with [start-mvd.sh](../bin/start-mvd.sh); it stops any prior instance,
then launches the HTTP server.

# Coding Conventions

## `base.py`

[base.pyi](../src/multiviewer/base.pyi) exports functions and types used throughout the
project. All other files should do:

```
from .base import *
```

If something is available in `base`, don't re-import it from somewhere else. E.g. don't do
`from typing import Any`, because `base` already exports `Any`.

## Naming conventions

We avoid leading underscores on helper functions; to keep interfaces clean, hide internal
details in the `.pyi` stubs instead of prefixing names. This keeps the runtime code more
readable while still controlling what’s exported.

# Pyright

We configure pyright using [pyrightconfig.json](../pyrightconfig.json), so that CLI,
Codex, and VS Code all experience the same behavior. We use `strict` type checking, and
enable some additional checks.

## Pyright exhaustiveness and enums

Pyright treats an enum as “closed” only when the stub enumerates all members with
assignments. For enums that use `MyStrEnum` at runtime, keep the `.py` as-is and make the
`.pyi` subclass `StrEnum` (or `MyStrEnum`) with explicit `auto()` members, e.g.:

```python
from enum import StrEnum, auto

class RemoteMode(StrEnum):
    APPLE_TV = auto()
    MULTIVIEWER = auto()
```

Annotations without assignments are not enough for Pyright to know the set is closed, and
mixing annotations with `= auto()` in stubs is invalid. Use this pattern to satisfy
`reportMatchNotExhaustive` without touching runtime code.

## Pyright ignores vs casts

When only the type checker needs help (e.g., upstream stubs are incomplete), prefer a
targeted `# pyright: ignore[...]` over adding runtime casts. This keeps runtime behavior
unchanged and makes the intent explicit to readers.
