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
