from __future__ import annotations

from enum import StrEnum, auto

# Local package
from .atv import TV
from .base import JSON
from .jtech_output import JtechOutput

class Arrow(StrEnum):
    N = auto()
    E = auto()
    W = auto()
    S = auto()

class RemoteMode(StrEnum):
    APPLE_TV = auto()
    MULTIVIEWER = auto()

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
    @classmethod
    def field(cls) -> MvScreen: ...
    remote_mode: RemoteMode
    def pressed(self, button: Button, *, maybe_double_tap: bool = False) -> JSON: ...
    def explore_fsm(
        self,
        max_states: int = ...,
        validate: bool = ...,
        report_powers_of_two: bool = ...,
    ) -> tuple[int, int, bool]: ...
    def validate(self) -> None: ...
    def reset(self) -> None: ...
    def render(self) -> JtechOutput: ...
    def power_on(self) -> None: ...
    def selected_tv(self) -> TV: ...
