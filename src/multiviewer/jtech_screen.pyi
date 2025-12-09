from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .base import *
from .jtech import Color, Hdmi, Jtech, Mode, PipLocation, Submode, Window

def color_letter(c: Color) -> str: ...

@dataclass(slots=True)
class Window_contents:
    """Describes one window on the TV screen."""
    hdmi: Hdmi
    border: Color | None

@dataclass(slots=True)
class Screen:
    """
    A complete description of the jtech's output observable on the TV, including the
    window layout, borders, and audio.
    """
    mode: Mode
    submode: Submode | None
    pip_location: PipLocation | None
    audio_from: Hdmi
    windows: dict[Window, Window_contents]

    def one_line_description(self) -> str: ...
    @classmethod
    async def read_jtech(
            cls,
            device: Jtech,
            should_abort: Callable[[], bool]) -> Screen | None:
        """
        Send commands to the J-Tech to read its currently displayed screen. After sending
        each command, check should_abort(); if it returns True, abort early and return
        None. Otherwise, return the read Screen.
        """

    async def set_jtech(
            self,
            device: Jtech,
            should_abort: Callable[[], bool]) -> bool:
        """
        Send commands to the J-Tech to make its displayed screen match this Screen.
        After sending each command, check should_abort(); if it returns True, abort early
        and return False. Return True if the entire desired Screen was set.
        """
