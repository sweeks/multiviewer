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

## Using `base`

`base.py` re-exports the common types/utilities (e.g., `Any`, `Task`, `Callable`,
`fail/assert_/debug_print`, `MyStrEnum`, etc.). When adding annotations elsewhere, prefer
to import from `base` rather than re-importing from `typing`/`asyncio`, so types stay
consistent and centralized. If a type is already in `base`/`base.pyi`, don’t duplicate the
import from `typing`—just pull it from `base`.

## Naming conventions

We avoid leading underscores on helper functions; to keep interfaces clean, hide internal
details in the `.pyi` stubs instead of prefixing names. This keeps the runtime code more
readable while still controlling what’s exported.
