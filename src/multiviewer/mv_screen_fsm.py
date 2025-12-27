from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import deque

from .base import *
from .jtech import Submode, Window
from .mv_screen import (
    Button,
    FullscreenMode,
    LayoutMode,
    MvScreen,
    RemoteMode,
    initial_pip_location_by_tv,
    initial_window_tv,
)

APPLE_TV = RemoteMode.APPLE_TV
MULTIVIEWER = RemoteMode.MULTIVIEWER

FULL = FullscreenMode.FULL
PIP = FullscreenMode.PIP
FULLSCREEN = LayoutMode.FULLSCREEN
MULTIVIEW = LayoutMode.MULTIVIEW
WINDOWS_SAME = Submode.WINDOWS_SAME
W1_PROMINENT = Submode.W1_PROMINENT
W1 = Window.W1
W2 = Window.W2
W3 = Window.W3
W4 = Window.W4


@dataclass_json
@dataclass(frozen=True)
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
    def create(screen: MvScreen) -> FsmState:
        state = 0
        state |= (screen.num_active_windows - 1) << _NUM_ACTIVE_POS
        state |= (1 if screen.layout_mode == LayoutMode.FULLSCREEN else 0) << _LAYOUT_POS
        state |= (
            1 if screen.multiview_submode == W1_PROMINENT else 0
        ) << _MULTIVIEW_SUBMODE_POS
        state |= (
            1 if screen.fullscreen_mode == FullscreenMode.PIP else 0
        ) << _FULLSCREEN_MODE_POS
        state |= window_code(screen.full_window) << _FULL_WINDOW_POS
        state |= window_code(screen.pip_window) << _PIP_WINDOW_POS
        state |= window_code(screen.selected_window) << _SELECTED_WINDOW_POS
        state |= (
            1 if screen.selected_window_has_distinct_border else 0
        ) << _SELECTED_BORDER_POS
        state |= (
            1 if screen.remote_mode == RemoteMode.APPLE_TV else 0
        ) << _REMOTE_MODE_POS
        state |= _BUTTON_TO_CODE[screen.last_button] << _LAST_BUTTON_POS
        state |= window_code(screen.last_selected_window) << _LAST_SELECTED_WINDOW_POS
        return FsmState(state)

    def hydrate(self, screen: MvScreen) -> None:
        state = int(self)
        wt = screen.window_tv
        wt.clear()
        wt.update(initial_window_tv())
        pl = screen.pip_location_by_tv
        pl.clear()
        pl.update(initial_pip_location_by_tv())

        def get(bits: int, pos: int) -> int:
            mask = (1 << bits) - 1
            return (state >> pos) & mask

        screen.num_active_windows = get(_NUM_ACTIVE_BITS, _NUM_ACTIVE_POS) + 1
        screen.layout_mode = FULLSCREEN if get(1, _LAYOUT_POS) else MULTIVIEW
        screen.multiview_submode = (
            W1_PROMINENT if get(1, _MULTIVIEW_SUBMODE_POS) else WINDOWS_SAME
        )
        screen.fullscreen_mode = PIP if get(1, _FULLSCREEN_MODE_POS) else FULL
        screen.full_window = window_from_code(get(_WINDOW_BITS, _FULL_WINDOW_POS))
        screen.pip_window = window_from_code(get(_WINDOW_BITS, _PIP_WINDOW_POS))
        screen.selected_window = window_from_code(get(_WINDOW_BITS, _SELECTED_WINDOW_POS))
        screen.selected_window_has_distinct_border = bool(get(1, _SELECTED_BORDER_POS))
        screen.remote_mode = APPLE_TV if get(1, _REMOTE_MODE_POS) else MULTIVIEWER
        screen.last_button = _CODE_TO_BUTTON[get(_LAST_BUTTON_BITS, _LAST_BUTTON_POS)]
        screen.last_selected_window = window_from_code(
            get(_WINDOW_BITS, _LAST_SELECTED_WINDOW_POS)
        )

    def to_record(self) -> FsmStateRecord:
        screen = MvScreen()
        self.hydrate(screen)
        return FsmStateRecord(
            layout_mode=screen.layout_mode,
            num_active_windows=screen.num_active_windows,
            multiview_submode=screen.multiview_submode,
            fullscreen_mode=screen.fullscreen_mode,
            full_window=screen.full_window,
            pip_window=screen.pip_window,
            selected_window=screen.selected_window,
            selected_window_has_distinct_border=screen.selected_window_has_distinct_border,
            remote_mode=screen.remote_mode,
            last_button=screen.last_button,
            last_selected_window=screen.last_selected_window,
        )


@dataclass_json
@dataclass(frozen=True)
class FsmStateMachine:
    entries: list[tuple[FsmState, list[FsmState]]]
    buttons: list[Button]
    transitions: int
    complete: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "buttons": [b.name for b in self.buttons],
            "complete": self.complete,
            "states": len(self.entries),
            "transitions": self.transitions,
            "entries": [
                [int(state), [int(t) for t in transitions]]
                for state, transitions in self.entries
            ],
        }

    def to_pretty_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def write(self, path: str | Path) -> None:
        p = Path(path)
        p.write_text(self.to_pretty_json())

    def summary(self) -> dict[str, object]:
        digest = hashlib.sha256(
            json.dumps(self.to_dict(), separators=(",", ":")).encode()
        ).hexdigest()
        return {
            "states": len(self.entries),
            "transitions": self.transitions,
            "complete": self.complete,
            "sha256": digest,
        }

    def write_summary(self, path: str | Path) -> None:
        p = Path(path)
        p.write_text(json.dumps(self.summary(), indent=2))


MAX_FSM_STATES = 1 << 19

# Bit packing helpers for FSM state -> int
_BUTTONS = list(Button)
_BUTTON_TO_CODE: dict[Button | None, int] = {None: 0} | {
    b: i + 1 for i, b in enumerate(_BUTTONS)
}
_CODE_TO_BUTTON: list[Button | None] = [None] + _BUTTONS

_NUM_ACTIVE_POS = 0
_NUM_ACTIVE_BITS = 2
_LAYOUT_POS = 2
_MULTIVIEW_SUBMODE_POS = 3
_FULLSCREEN_MODE_POS = 4
_FULL_WINDOW_POS = 5
_WINDOW_BITS = 2
_PIP_WINDOW_POS = 7
_SELECTED_WINDOW_POS = 9
_SELECTED_BORDER_POS = 11
_REMOTE_MODE_POS = 12
_LAST_BUTTON_POS = 13
_LAST_BUTTON_BITS = 4
_LAST_SELECTED_WINDOW_POS = 17


def window_code(w: Window) -> int:
    return w.to_int() - 1


def window_from_code(code: int) -> Window:
    return Window.of_int(code + 1)


def decode_fsm_state_fields(state: FsmState) -> FsmStateRecord:
    return state.to_record()


def fsm_state_to_screen(state: FsmState) -> MvScreen:
    screen = MvScreen()
    state.hydrate(screen)
    return screen


def explore_fsm_machine(
    max_states: int = 500_000,
    validate: bool = True,
    report_powers_of_two: bool = False,
) -> FsmStateMachine:
    """Breadth-first exploration of reachable FSM states."""
    base = MvScreen()
    start_state = FsmState.create(base)
    queue: deque[FsmState] = deque([start_state])
    visited: list[list[FsmState] | None] = [None] * MAX_FSM_STATES
    visited[int(start_state)] = []
    seen = 1
    transitions = 0
    next_report = 1

    buttons = _BUTTONS
    transitions_per_state = len(buttons) * 2
    entries: list[tuple[FsmState, list[FsmState]]] = []

    while queue:
        state = queue.popleft()
        assert visited[int(state)] == []
        transitions_for_state: list[FsmState] = [FsmState(0)] * transitions_per_state
        for b_idx, button in enumerate(buttons):
            for d_idx, maybe_double_tap in enumerate((False, True)):
                state.hydrate(base)
                base.pressed(button, maybe_double_tap=maybe_double_tap)
                if validate:
                    try:
                        base.validate()
                    except Exception:
                        print(
                            "validate failed",
                            {
                                "from": decode_fsm_state_fields(state),
                                "button": button,
                                "double": maybe_double_tap,
                                "after": decode_fsm_state_fields(FsmState.create(base)),
                                "window_tv": base.window_tv,
                                "pip_location_by_tv": base.pip_location_by_tv,
                            },
                            flush=True,
                        )
                        raise
                key = FsmState.create(base)
                transitions += 1
                idx = b_idx * 2 + d_idx
                transitions_for_state[idx] = key
                if visited[int(key)] is None:
                    visited[int(key)] = []
                    seen += 1
                    if report_powers_of_two and seen >= next_report:
                        while next_report <= seen:
                            print(f"states={seen} transitions={transitions}", flush=True)
                            next_report *= 2
                    if seen >= max_states:
                        return FsmStateMachine(
                            entries=entries,
                            buttons=buttons,
                            transitions=transitions,
                            complete=False,
                        )
                    queue.append(key)
        visited[int(state)] = transitions_for_state
        entries.append((state, transitions_for_state))

    return FsmStateMachine(
        entries=entries, buttons=buttons, transitions=transitions, complete=True
    )


def explore_fsm(
    max_states: int = 500_000,
    validate: bool = True,
    report_powers_of_two: bool = False,
    save_json_to: str | Path | None = None,
) -> tuple[int, int, bool]:
    """Breadth-first exploration of reachable FSM states.

    Returns (num_states, num_transitions, complete) where complete=False if the
    search hit max_states and stopped early.
    """
    machine = explore_fsm_machine(
        max_states=max_states,
        validate=validate,
        report_powers_of_two=report_powers_of_two,
    )
    if save_json_to is not None:
        save_path = Path(save_json_to)
        machine.write(save_path)
        summary_path = save_path.with_name(f"{save_path.stem}-summary.json")
        machine.write_summary(summary_path)
    return (len(machine.entries), machine.transitions, machine.complete)


def explore_fsm_cli(
    *,
    max_states: int = 10_000_000,
    report_powers_of_two: bool = True,
    validate: bool = True,
    save_json_to: str | Path | None = None,
) -> tuple[int, int, bool]:
    if save_json_to is None:
        save_json_to = Path(__file__).resolve().parent / "mv_screen_fsm.json"
    states, transitions, complete = explore_fsm(
        max_states=max_states,
        report_powers_of_two=report_powers_of_two,
        validate=validate,
        save_json_to=save_json_to,
    )
    print(f"done: states={states} transitions={transitions} complete={complete}")
    return states, transitions, complete


DEFAULT_SAVE_PATH = Path(__file__).resolve().parent / "mv_screen_fsm.json"
DEFAULT_SUMMARY_PATH = DEFAULT_SAVE_PATH.with_name("mv_screen_fsm-summary.json")


def generate(
    *,
    max_states: int = 10_000_000,
    report_powers_of_two: bool = True,
    validate: bool = True,
    save_path: Path = DEFAULT_SAVE_PATH,
) -> tuple[int, int, bool]:
    return explore_fsm_cli(
        max_states=max_states,
        report_powers_of_two=report_powers_of_two,
        validate=validate,
        save_json_to=save_path,
    )


def validate_against_summary(summary_path: Path | None = None) -> None:
    if summary_path is None:
        summary_path = DEFAULT_SUMMARY_PATH
    if not summary_path.exists():
        print(f"FSM summary file missing: {summary_path}")
        raise SystemExit(1)
    expected = json.loads(summary_path.read_text())
    current = explore_fsm_machine().summary()
    if current != expected:
        print("FSM summary mismatch; run bin/generate-mv-screen-fsm.sh to regenerate")
        print("expected:", expected)
        print("current :", current)
        raise SystemExit(1)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Explore mv_screen FSM")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--generate", action="store_true", help="Generate FSM JSON and summary"
    )
    group.add_argument(
        "--validate", action="store_true", help="Validate current FSM against summary"
    )
    args = parser.parse_args(argv)

    if args.generate:
        generate()
    else:
        validate_against_summary()


if __name__ == "__main__":
    main(sys.argv[1:])
