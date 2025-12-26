from __future__ import annotations

from pathlib import Path

from .jtech import Submode, Window
from .mv_screen import Button, FullscreenMode, LayoutMode, MvScreen, RemoteMode

class FsmStateRecord:
    layout_mode: LayoutMode
    num_active_windows: int
    multiview_submode: Submode
    fullscreen_mode: FullscreenMode
    full_window: Window
    pip_window: Window
    selected_window: Window
    selected_window_has_distinct_border: bool
    remote_mode: RemoteMode
    last_button: Button | None
    last_selected_window: Window

class FsmState(int):
    @staticmethod
    def create(screen: MvScreen) -> FsmState: ...
    def hydrate(self, screen: MvScreen) -> None: ...
    def to_record(self) -> FsmStateRecord: ...

class FsmStateMachine:
    entries: list[tuple[FsmState, list[FsmState]]]
    buttons: list[Button]
    transitions: int
    complete: bool
    def summary(self) -> dict[str, object]: ...
    def write(self, path: str | Path) -> None: ...
    def write_summary(self, path: str | Path) -> None: ...

MAX_FSM_STATES: int

def decode_fsm_state_fields(state: FsmState) -> FsmStateRecord: ...
def fsm_state_to_screen(state: FsmState) -> MvScreen: ...
def explore_fsm_machine(
    max_states: int = ...,
    validate: bool = ...,
    report_powers_of_two: bool = ...,
) -> FsmStateMachine: ...
def explore_fsm(
    max_states: int = ...,
    validate: bool = ...,
    report_powers_of_two: bool = ...,
    save_json_to: str | Path | None = ...,
) -> tuple[int, int, bool]: ...
def explore_fsm_cli(
    *,
    max_states: int = ...,
    report_powers_of_two: bool = ...,
    validate: bool = ...,
) -> tuple[int, int, bool]: ...
