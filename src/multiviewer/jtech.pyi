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
    H1: Hdmi
    H2: Hdmi
    H3: Hdmi
    H4: Hdmi

def assert_Hdmi(_: Any) -> Hdmi: ...

class Mode: 
    FULL: Mode
    PIP: Mode
    PBP: Mode
    TRIPLE: Mode
    QUAD: Mode

    def num_windows(self) -> int: ...

    def windows(self) -> list[Window]: ...

class Window(MyStrEnum):
    W1: Window
    W2: Window
    W3: Window
    W4: Window

class Submode:
    WINDOWS_SAME: Submode
    W1_PROMINENT: Submode

    def flip(self) -> Submode: ...

@dataclass
class Window_contents:
    hdmi: Hdmi
    border: Color | None

@dataclass
class Screen:
    mode: Mode
    submode: Submode | None
    audio_from: Hdmi
    windows: dict[Window, Window_contents]

    def one_line_description(self) -> str: ...

class Device:
    power: Power | None
    audio_mute: Mute

    @classmethod
    def field(cls): ...

    async def reset(self) -> None: ...
    
    async def set_power(self, p: Power) -> None: ...

    async def unmute(self) -> None: ...

    async def set_screen(self, desired: Screen, should_abort: Callable[[], bool]) -> bool:
        ...

    async def read_screen(self, should_abort: Callable[[], bool]) -> Screen | None: ...
