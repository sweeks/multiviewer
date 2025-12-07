"""
This module has all the classes for describing and controlling the J-Tech device. The
Screen class describes the screen layout, and the Device class has functions to read and
set the screen.
"""

# Local package
from . import aio
from .base import *

class Power:
    ON: Power
    OFF: Power

class Mute:
    MUTED: Mute
    UNMUTED: Mute

class Color:
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

class Hdmi:
    """The names of the HDMI inputs to the J-Tech."""
    H1: Hdmi
    H2: Hdmi
    H3: Hdmi
    H4: Hdmi

class Mode:
    """The layout of the on-screen windows."""
    FULL: Mode
    PIP: Mode
    PBP: Mode
    TRIPLE: Mode
    QUAD: Mode

    def num_windows(self) -> int: ...

    def windows(self) -> list[Window]: ...

class Window(MyStrEnum):
    """The names of the on-screen windwows."""
    W1: Window
    W2: Window
    W3: Window
    W4: Window

class Submode:
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

@dataclass
class Window_contents:
    """Describes one window on the TV screen"""
    hdmi: Hdmi
    border: Color | None

@dataclass
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

class Device:
    """
    For controlling the Jtech. It uses an ip2sl.Connnection to send commands, one at a
    time.  It maintains a representation of the internal state of the J-Tech, to avoid
    sending redundant commands.
    """

    @classmethod
    def field(cls): ...

    power: Power | None
    """The J-Tech's power state, as last read from the device."""

    audio_mute: Mute
    """The J-Tech's audio mute state, as last read from the device."""

    async def reset(self) -> None:
        """Reset the internal state and reconnect to the J-Tech."""
    
    async def unmute(self) -> None: ...

    async def set_power(self, desired_power: Power) -> None:
        """Send a command to the J-Tech to make its power match desired_power."""

    async def set_screen(self, 
                        desired_screen: Screen, 
                        should_abort: Callable[[], bool]) -> bool:
        """
        Send commands to the J-Tech to make its displayed screen match desired_screen.
        After sending each command, check should_abort(); if it returns True, abort early
        and return False.  Return True if the entire desired_screen was set.
        """

    async def read_screen(self, should_abort: Callable[[], bool]) -> Screen | None: 
        """
        Send commands to the J-Tech to read its currently displayed screen. After sending
        each command, check should_abort(); if it returns True, abort early and return
        None. Otherwise, return the read Screen.
        """