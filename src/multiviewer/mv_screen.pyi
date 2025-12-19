from __future__ import annotations

# Local package
from .atv import TV
from .base import JSON
from .jtech_output import JtechOutput

class Arrow:
    N: Arrow
    E: Arrow
    W: Arrow
    S: Arrow

class RemoteMode:
    APPLE_TV: RemoteMode
    MULTIVIEWER: RemoteMode

class Button:
    REMOTE: Button
    SELECT: Button
    BACK: Button
    PLAY_PAUSE: Button
    ACTIVATE_TV: Button
    DEACTIVATE_TV: Button
    TOGGLE_SUBMODE: Button
    ARROW_N: Button
    ARROW_E: Button
    ARROW_W: Button
    ARROW_S: Button

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
