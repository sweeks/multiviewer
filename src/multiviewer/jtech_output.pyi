from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

from .base import *
from .jtech import Color, Hdmi, Jtech, PipLocation, Submode

@dataclass(slots=True)
class WindowContents:
    """Describes one window on the TV screen."""

    hdmi: Hdmi
    border: Color | None

@dataclass(slots=True)
class Full:
    w1: WindowContents

@dataclass(slots=True)
class Pip:
    pip_location: PipLocation
    w1: WindowContents
    w2: WindowContents

@dataclass(slots=True)
class Pbp:
    submode: Submode
    w1: WindowContents
    w2: WindowContents

@dataclass(slots=True)
class Triple:
    submode: Submode
    w1: WindowContents
    w2: WindowContents
    w3: WindowContents

@dataclass(slots=True)
class Quad:
    submode: Submode
    w1: WindowContents
    w2: WindowContents
    w3: WindowContents
    w4: WindowContents

Layout: TypeAlias = Full | Pip | Pbp | Triple | Quad

@dataclass(slots=True)
class JtechOutput:
    layout: Layout
    audio_from: Hdmi

    def one_line_description(self) -> str: ...
    @classmethod
    async def read(
        cls, jtech: Jtech, should_abort: Callable[[], bool]
    ) -> JtechOutput | None: ...
    async def set(self, jtech: Jtech, should_abort: Callable[[], bool]) -> bool: ...
