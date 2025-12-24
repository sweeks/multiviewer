from __future__ import annotations

# Local package
from .base import *


class TV(MyStrEnum):
    TV1 = auto()
    TV2 = auto()
    TV3 = auto()
    TV4 = auto()


TV1 = TV.TV1
TV2 = TV.TV2
TV3 = TV.TV3
TV4 = TV.TV4

attach_int(TV, {TV1: 1, TV2: 2, TV3: 3, TV4: 4})


def validate_tv(x: object) -> None:
    if not (isinstance(x, TV)):
        fail("not a TV", x)
