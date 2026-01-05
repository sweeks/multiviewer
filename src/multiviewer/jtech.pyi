"""
This module has all the classes for describing and controlling the J-Tech device.
"""

# Local package
from .base import *

class Power(MyStrEnum):
    ON = auto()
    OFF = auto()

class Mute(MyStrEnum):
    MUTED = auto()
    UNMUTED = auto()

class Color(MyStrEnum):
    """The names of the border colors."""

    BLACK = auto()
    RED = auto()
    GREEN = auto()
    BLUE = auto()
    YELLOW = auto()
    MAGENTA = auto()
    CYAN = auto()
    WHITE = auto()
    GRAY = auto()

    def letter(self) -> str: ...
    @staticmethod
    def letter_for(color: Color | None) -> str: ...

class Border:
    On: Border
    Off: Border

class Hdmi(MyStrEnum):
    """The names of the HDMI inputs to the J-Tech."""

    H1 = auto()
    H2 = auto()
    H3 = auto()
    H4 = auto()

class Mode(MyStrEnum):
    """The layout of the on-screen windows."""

    FULL = auto()
    PIP = auto()
    PBP = auto()
    TRIPLE = auto()
    QUAD = auto()

    def num_windows(self) -> int: ...
    def windows(self) -> list[Window]: ...
    def window_has_border(self, w: Window) -> bool: ...

class Window(MyStrEnum):
    """The names of the on-screen windwows."""

    W1 = auto()
    W2 = auto()
    W3 = auto()
    W4 = auto()

class Submode(MyStrEnum):
    """
    For QUAD, TRIPLE, and PBP, the submode says whether all windows are the same size,
    or W1 is prominent.
    """

    WINDOWS_SAME = auto()
    W1_PROMINENT = auto()

    def flip(self) -> Submode: ...

class PipLocation(MyStrEnum):
    NW = auto()
    NE = auto()
    SW = auto()
    SE = auto()

class Jtech:
    """
    For controlling the Jtech. It uses an ip2sl.Connnection to send commands, one at a
    time.  It maintains a representation of the internal state of the J-Tech, to avoid
    sending redundant commands.
    """

    @classmethod
    def field(cls) -> Jtech: ...
    async def reset(self) -> None:
        """Reset the internal state and reconnect to the J-Tech."""

    async def read_power(self) -> Power: ...
    async def set_power(self, power: Power) -> None: ...
    async def read_mode(self) -> Mode: ...
    async def set_mode(self, mode: Mode) -> None: ...
    async def read_submode(self, mode: Mode) -> Submode | None: ...
    async def set_submode(self, mode: Mode, submode: Submode) -> None: ...
    async def read_pip_location(self) -> PipLocation | None: ...
    async def set_pip_location(self, pip_location: PipLocation) -> None: ...
    async def read_window_input(self, mode: Mode, window: Window) -> Hdmi: ...
    async def set_window_input(self, mode: Mode, window: Window, hdmi: Hdmi) -> None: ...
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
    async def unmute(self, force: bool = False) -> None: ...
    async def test_aliasing(self) -> None: ...
