"""
See ../../docs/multiviewer-specification.md for the spec of this module.
"""

from __future__ import annotations

from enum import StrEnum

# Local package
from .atv import TV
from .base import *
from .jtech import PipLocation, Submode, Window
from .jtech_output import JtechOutput

class Arrow(StrEnum):
    N = auto()
    E = auto()
    W = auto()
    S = auto()

class RemoteMode(StrEnum):
    APPLE_TV = auto()
    MULTIVIEWER = auto()

class LayoutMode(StrEnum):
    MULTIVIEW = auto()
    FULLSCREEN = auto()

class FullscreenMode(StrEnum):
    FULL = auto()
    PIP = auto()

class Button(StrEnum):
    REMOTE = auto()
    SELECT = auto()
    BACK = auto()
    PLAY_PAUSE = auto()
    ACTIVATE_TV = auto()
    DEACTIVATE_TV_FIRST = auto()
    DEACTIVATE_TV_LAST = auto()
    TOGGLE_SUBMODE = auto()
    ARROW_N = auto()
    ARROW_E = auto()
    ARROW_W = auto()
    ARROW_S = auto()

class MvScreen:
    layout_mode: LayoutMode
    num_active_windows: int
    window_tv: dict[Window, TV]
    multiview_submode: Submode
    fullscreen_mode: FullscreenMode
    full_window: Window
    pip_window: Window
    pip_location_by_tv: dict[TV, PipLocation]
    selected_window: Window
    selected_window_has_distinct_border: bool
    remote_mode: RemoteMode
    last_button: Button | None
    last_selected_window: Window

    @classmethod
    def field(cls) -> MvScreen: ...
    def pressed(self, button: Button, *, maybe_double_tap: bool = False) -> JSON: ...
    def validate(self) -> None: ...
    def reset(self) -> None: ...
    def render(self) -> JtechOutput: ...
    def power_on(self) -> None: ...
    def selected_tv(self) -> TV: ...

def initial_pip_location_by_tv() -> dict[TV, PipLocation]: ...
def initial_window_tv() -> dict[Window, TV]: ...
