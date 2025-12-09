"""
This module has all the classes for describing and controlling the J-Tech device.
"""

# Local package
from . import aio
from .base import *
from .jtech_screen import Screen, Window_contents

class Power(MyStrEnum):
    ON: Power
    OFF: Power

class Mute(MyStrEnum):
    MUTED: Mute
    UNMUTED: Mute

class Color(MyStrEnum):
    """The names of the border colors."""

    BLACK: Color
    RED: Color
    GREEN: Color
    BLUE: Color
    YELLOW: Color
    MAGENTA: Color
    CYAN: Color
    WHITE: Color
    GRAY: Color

class Border:
    On: Border
    Off: Border

class Hdmi(MyStrEnum):
    """The names of the HDMI inputs to the J-Tech."""

    H1: Hdmi
    H2: Hdmi
    H3: Hdmi
    H4: Hdmi

class Mode(MyStrEnum):
    """The layout of the on-screen windows."""

    FULL: Mode
    PIP: Mode
    PBP: Mode
    TRIPLE: Mode
    QUAD: Mode

    def num_windows(self) -> int: ...
    def windows(self) -> list[Window]: ...
    def window_has_border(self, w: Window) -> bool: ...

class Window(MyStrEnum):
    """The names of the on-screen windwows."""

    W1: Window
    W2: Window
    W3: Window
    W4: Window

class Submode(MyStrEnum):
    """
    For QUAD, TRIPLE, and PBP, the submode says whether all windows are the same size,
    or W1 is prominent.
    """

    WINDOWS_SAME: Submode
    W1_PROMINENT: Submode

    def flip(self) -> Submode: ...

class PipLocation(MyStrEnum):
    NW: PipLocation
    NE: PipLocation
    SW: PipLocation
    SE: PipLocation

class Jtech:
    """
    For controlling the Jtech. It uses an ip2sl.Connnection to send commands, one at a
    time.  It maintains a representation of the internal state of the J-Tech, to avoid
    sending redundant commands.
    """

    @classmethod
    def field(cls): ...

    async def reset(self) -> None:
        """Reset the internal state and reconnect to the J-Tech."""

    pip_location: PipLocation

    async def read_power(self) -> Power: ...
    async def set_power(self, power: Power) -> None: ...

    async def read_mode(self) -> Mode: ...
    async def set_mode(self, mode: Mode) -> None: ...

    async def read_submode(self, mode: Mode) -> Submode | None: ...
    async def set_submode(self, mode: Mode, submode: Submode) -> None: ...

    async def set_pip(self, pip_location: PipLocation) -> None: ...

    async def read_window_input(self, mode: Mode, window: Window) -> Hdmi: ...
    async def set_window_input(
        self, mode: Mode, window: Window, hdmi: Hdmi
    ) -> None: ...

    async def read_border(self, mode: Mode, window: Window) -> Border: ...
    async def set_border(self, mode: Mode, window: Window, border: Border) -> None: ...

    async def read_border_color(self, mode: Mode, window: Window) -> Color: ...
    async def set_border_color(
        self, mode: Mode, window: Window, color: Color
    ) -> None: ...

    async def read_audio_from(self) -> Hdmi: ...
    async def set_audio_from(self, hdmi: Hdmi) -> None: ...

    async def read_audio_mute(self) -> Mute: ...
    async def mute(self) -> None: ...
    async def unmute(self) -> None: ...

    async def test_aliasing(self) -> None: ...
