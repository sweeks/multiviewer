from __future__ import annotations

# Local package
from .base import *

class TV(MyStrEnum):
    TV1: TV
    TV2: TV
    TV3: TV
    TV4: TV

def validate_tv(x: TV) -> None: ...
