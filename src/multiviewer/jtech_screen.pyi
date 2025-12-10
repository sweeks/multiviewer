from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeAlias

from .base import *
from .jtech import Color, Hdmi, Jtech, PipLocation, Submode, Window


def color_letter(c: Color) -> str: ...


@dataclass(slots=True)
class Window_contents:
    """Describes one window on the TV screen."""

    hdmi: Hdmi
    border: Color | None


@dataclass(slots=True)
class Full:
    w1: Window_contents


@dataclass(slots=True)
class Pip:
    pip_location: PipLocation
    w1: Window_contents
    w2: Window_contents


@dataclass(slots=True)
class Pbp:
    submode: Submode
    w1: Window_contents
    w2: Window_contents


@dataclass(slots=True)
class Triple:
    submode: Submode
    w1: Window_contents
    w2: Window_contents
    w3: Window_contents


@dataclass(slots=True)
class Quad:
    submode: Submode
    w1: Window_contents
    w2: Window_contents
    w3: Window_contents
    w4: Window_contents


Layout: TypeAlias = Full | Pip | Pbp | Triple | Quad


@dataclass(slots=True)
class Screen:
    layout: Layout
    audio_from: Hdmi

    def one_line_description(self) -> str: ...

    @classmethod
    async def read_jtech(
        cls, device: Jtech, should_abort: Callable[[], bool]
    ) -> Screen | None: ...

    async def set_jtech(self, device: Jtech, should_abort: Callable[[], bool]) -> bool: ...
