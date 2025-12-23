from __future__ import annotations

# Local package
from .base import *

class TV(MyStrEnum):
    TV1 = auto()
    TV2 = auto()
    TV3 = auto()
    TV4 = auto()

def validate_tv(x: TV) -> None: ...
