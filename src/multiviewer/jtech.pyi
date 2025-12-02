# Local package
from .base import *

class Power:
    ON: Power
    OFF: Power

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

class Jtech:
    @classmethod 
    def field(cls) -> Jtech: ...

    should_send_commands_to_device: bool
    # This determines whether we send commands and read responses from the physical jtech
    # device.  That is what we want in mvd, and sometimes in tests. But sometimes in
    # tests, we just want to test our multiviewer logic, in which case, we set
    # should_send_commands_to_device=False. In that case, the below functions don't do
    # anything, and current_power and current_screen just return the last set value.

    async def current_power(self) -> Power: ...
    def set_power(self, p: Power) -> None: ...

    async def current_screen(self) -> Screen: ...
    def set_screen(self, s: Screen) -> None: ...

    def synced(self) -> Awaitable[None]: ...
