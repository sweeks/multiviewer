from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from dataclasses_json import dataclass_json

from . import json_field
from .base import *
from .json_field import json_dict
from .jtech import Color, Hdmi, Mode, PipLocation, Submode, Window
from .jtech_output import Full, JtechOutput, Pbp, Pip, Quad, Triple, WindowContents
from .tv import TV

DOUBLE_TAP_MAX_DURATION = timedelta(seconds=0.3)


class Arrow(MyStrEnum):
    N = auto()
    E = auto()
    W = auto()
    S = auto()


N = Arrow.N
E = Arrow.E
W = Arrow.W
S = Arrow.S


class LayoutMode(MyStrEnum):
    MULTIVIEW = auto()
    FULLSCREEN = auto()


MULTIVIEW = LayoutMode.MULTIVIEW
FULLSCREEN = LayoutMode.FULLSCREEN


class FullscreenMode(MyStrEnum):
    FULL = auto()
    PIP = auto()


FULL = FullscreenMode.FULL
PIP = FullscreenMode.PIP


class RemoteMode(MyStrEnum):
    APPLE_TV = auto()
    MULTIVIEWER = auto()

    def flip(self) -> RemoteMode:
        match self:
            case RemoteMode.APPLE_TV:
                return MULTIVIEWER
            case RemoteMode.MULTIVIEWER:
                return APPLE_TV


APPLE_TV = RemoteMode.APPLE_TV
MULTIVIEWER = RemoteMode.MULTIVIEWER


class Button(MyStrEnum):
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
        wt[W1] = TV.TV1
        wt[W2] = TV.TV2
        wt[W3] = TV.TV3
        wt[W4] = TV.TV4
        pl = screen.pip_location_by_tv
        pl.clear()
        for tv in TV.all():
            pl[tv] = PipLocation.NE

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


H1 = Hdmi.H1
H2 = Hdmi.H2
H3 = Hdmi.H3
H4 = Hdmi.H4
W1 = Window.W1
W2 = Window.W2
W3 = Window.W3
W4 = Window.W4
WINDOWS_SAME = Submode.WINDOWS_SAME
W1_PROMINENT = Submode.W1_PROMINENT

max_num_windows = 4
min_num_windows = 1

_arrow_points_to = {
    2: {W1: {E: W2}, W2: {W: W1}},
    3: {
        W1: {N: W2, E: W2, S: W3},
        W2: {W: W1, S: W3},
        W3: {
            N: W2,
            W: W1,
        },
    },
    (4, WINDOWS_SAME): {
        W1: {E: W2, W: W4, S: W3},
        W2: {E: W3, W: W1, S: W4},
        W3: {N: W1, E: W4, W: W2},
        W4: {
            N: W2,
            E: W1,
            W: W3,
        },
    },
    (4, W1_PROMINENT): {
        W1: {N: W2, E: W3, S: W4},
        W2: {W: W1, S: W3},
        W3: {N: W2, W: W1, S: W4},
        W4: {N: W3, W: W1},
    },
}


def initial_pip_location_by_tv():
    return dict.fromkeys(TV.all(), PipLocation.NE)


def initial_window_tv():
    return {W1: TV.TV1, W2: TV.TV2, W3: TV.TV3, W4: TV.TV4}


def tv2hdmi(tv: TV) -> Hdmi:
    match tv:
        case TV.TV1:
            return Hdmi.H1
        case TV.TV2:
            return Hdmi.H2
        case TV.TV3:
            return Hdmi.H3
        case TV.TV4:
            return Hdmi.H4
    raise AssertionError


@dataclass_json
@dataclass(slots=True)
class MvScreen(Jsonable):
    window_tv: dict[Window, TV] = field(
        default_factory=initial_window_tv, metadata=json_dict(Window, TV)
    )
    layout_mode: LayoutMode = MULTIVIEW
    num_active_windows: int = max_num_windows
    multiview_submode: Submode = W1_PROMINENT
    fullscreen_mode: FullscreenMode = FULL
    full_window: Window = W1
    pip_window: Window = W2
    pip_location_by_tv: dict[TV, PipLocation] = field(
        default_factory=initial_pip_location_by_tv, metadata=json_dict(TV, PipLocation)
    )
    selected_window: Window = W1
    selected_window_has_distinct_border: bool = True
    remote_mode: RemoteMode = MULTIVIEWER
    last_button: Button | None = field(default=None, metadata=json_field.omit)
    last_selected_window: Window = field(default=W1, metadata=json_field.omit)

    @classmethod
    def field(cls) -> MvScreen:
        return field(default_factory=MvScreen)

    def tv_window(self, tv: TV) -> Window:
        for w, tv2 in self.window_tv.items():
            if tv2 == tv:
                return w
        raise AssertionError(f"tv_window: TV {tv} not found")

    def power_on(self) -> None:
        self.remote_mode = MULTIVIEWER
        self.selected_window_has_distinct_border = True

    def activate_tv(self) -> None:
        if self.num_active_windows < max_num_windows:
            self.num_active_windows += 1

    def last_active_window(self) -> Window:
        return Window.of_int(self.num_active_windows)

    def active_windows(self) -> list[Window]:
        return [Window.of_int(i) for i in range(1, 1 + self.num_active_windows)]

    def next_active_window(self, w: Window) -> Window:
        return Window.of_int(w.to_int() % self.num_active_windows + 1)

    def prev_active_window(self, w: Window) -> Window:
        n = self.num_active_windows
        return Window.of_int(1 + ((w.to_int() + n - 2) % n))

    def set_pip_window(self) -> None:
        self.pip_window = self.next_active_window(self.full_window)

    def enter_fullscreen(self) -> None:
        self.layout_mode = FULLSCREEN
        self.full_window = self.selected_window
        if self.fullscreen_mode == FullscreenMode.PIP:
            self.set_pip_window()

    def swap_full_and_pip_windows(self) -> None:
        old_full = self.full_window
        self.full_window = self.pip_window
        self.pip_window = old_full
        self.selected_window = self.full_window

    def demote_tv(self, w1: Window) -> None:
        last = self.last_active_window()
        while w1 != last:
            w2 = self.next_active_window(w1)
            self.swap_window_tvs(w1, w2)
            w1 = w2

    def swap_window_tvs(self, w1: Window, w2: Window) -> None:
        tv1 = self.window_tv[w1]
        tv2 = self.window_tv[w2]
        self.window_tv[w1] = tv2
        self.window_tv[w2] = tv1

    def window_is_prominent(self, w: Window) -> bool:
        if w != W1:
            return False
        match self.layout_mode:
            case LayoutMode.FULLSCREEN:
                return True
            case LayoutMode.MULTIVIEW:
                return self.multiview_submode == W1_PROMINENT

    def deactivate_tv(self, *, place_first_in_inactive: bool = True) -> None:
        if self.num_active_windows == 1:
            return
        windows = Window.all()
        selected_tv = self.window_tv[self.selected_window]
        full_tv = self.window_tv[self.full_window]
        pip_tv = self.window_tv[self.pip_window]
        full_is_selected = full_tv == selected_tv
        if place_first_in_inactive:
            insert_at = self.num_active_windows - 1
        else:
            insert_at = len(windows) - 1
        i = windows.index(self.selected_window)
        while i < insert_at:
            self.window_tv[windows[i]] = self.window_tv[windows[i + 1]]
            i += 1
        self.window_tv[windows[insert_at]] = selected_tv
        self.num_active_windows -= 1
        self.selected_window_has_distinct_border = True
        if self.selected_window.to_int() > self.num_active_windows:
            self.selected_window = Window.of_int(self.num_active_windows)
        if self.num_active_windows == 1:
            self.layout_mode = FULLSCREEN
            self.fullscreen_mode = FULL
        if self.layout_mode == LayoutMode.FULLSCREEN:
            match self.fullscreen_mode:
                case FullscreenMode.FULL:
                    self.full_window = self.selected_window
                case FullscreenMode.PIP:
                    if full_is_selected:
                        self.pip_window = self.tv_window(pip_tv)
                        self.full_window = self.next_active_window(self.pip_window)
                        self.selected_window = self.full_window
                    else:
                        self.full_window = self.tv_window(full_tv)
                        self.pip_window = self.next_active_window(self.full_window)
                        self.selected_window = self.pip_window

    def entered_w1_prominent(self) -> None:
        if self.multiview_submode == W1_PROMINENT and self.selected_window != W1:
            self.swap_window_tvs(W1, self.selected_window)
            self.selected_window = W1

    def toggle_submode(self) -> None:
        match self.layout_mode:
            case LayoutMode.MULTIVIEW:
                self.multiview_submode = self.multiview_submode.flip()
                self.entered_w1_prominent()
            case LayoutMode.FULLSCREEN:
                if self.num_active_windows >= 2:
                    match self.fullscreen_mode:
                        case FullscreenMode.FULL:
                            self.fullscreen_mode = PIP
                            self.set_pip_window()
                        case FullscreenMode.PIP:
                            self.fullscreen_mode = FULL
                            self.selected_window = self.full_window

    def pressed_back(self) -> None:
        if self.layout_mode == LayoutMode.FULLSCREEN:
            if self.num_active_windows == 1:
                self.activate_tv()
            self.layout_mode = MULTIVIEW
            self.entered_w1_prominent()

    def pressed_play_pause(self) -> None:
        self.selected_window_has_distinct_border = (
            not self.selected_window_has_distinct_border
        )

    def toggle_remote_mode(self) -> None:
        self.remote_mode = self.remote_mode.flip()

    def pressed_select(self) -> None:
        match self.layout_mode:
            case LayoutMode.MULTIVIEW:
                self.enter_fullscreen()
            case LayoutMode.FULLSCREEN:
                match self.fullscreen_mode:
                    case FullscreenMode.FULL:
                        pass
                    case FullscreenMode.PIP:
                        self.swap_full_and_pip_windows()

    def window_input(self, w: Window) -> Hdmi:
        return tv2hdmi(self.window_tv[w])

    def pip_location(self) -> PipLocation:
        return self.pip_location_by_tv[self.window_tv[self.full_window]]

    def selected_tv(self) -> TV:
        return self.window_tv[self.selected_window]

    def remote(self, *, double_tap: bool = False) -> JSON:
        if double_tap:
            # Double tap.  The shortcut will open the Remote app on TV <i>
            self.last_button = None
            # Flip again to cancel the single-tap mode change.
            self.toggle_remote_mode()
            return self.selected_tv().to_int()
        else:
            # Single tap
            self.last_button = Button.REMOTE
            self.last_selected_window = self.selected_window
            self.toggle_remote_mode()
            return {}

    def validate(self) -> None:
        assert_equal(set(self.window_tv.keys()), set(Mode.QUAD.windows()))
        assert_equal(len(set(self.window_tv.values())), len(self.window_tv))
        assert_(min_num_windows <= self.num_active_windows <= max_num_windows)
        if self.num_active_windows == 1:
            assert_(self.layout_mode == FULLSCREEN)
            assert_(self.fullscreen_mode == FULL)
        active_windows = self.active_windows()
        assert_(self.selected_window in active_windows)
        match self.layout_mode:
            case LayoutMode.FULLSCREEN:
                assert_(self.full_window in active_windows)
                if self.fullscreen_mode == FullscreenMode.PIP:
                    assert_(self.pip_window in active_windows)
            case LayoutMode.MULTIVIEW:
                assert_(self.num_active_windows >= 2)

    def reset(self) -> None:
        new = MvScreen()
        self.window_tv = new.window_tv
        self.layout_mode = new.layout_mode
        self.num_active_windows = new.num_active_windows
        self.multiview_submode = new.multiview_submode
        self.fullscreen_mode = new.fullscreen_mode
        self.full_window = new.full_window
        self.pip_window = new.pip_window
        self.pip_location_by_tv = new.pip_location_by_tv
        self.selected_window = new.selected_window
        self.selected_window_has_distinct_border = new.selected_window_has_distinct_border
        self.remote_mode = new.remote_mode
        self.last_button = None
        self.last_selected_window = new.selected_window

    def arrow_points_to(self, arrow: Arrow) -> Window | None:
        match self.num_active_windows:
            case 2 | 3:
                key = self.num_active_windows
            case 4:
                key = (self.num_active_windows, self.multiview_submode)
            case _:
                fail(
                    "arrow_points_to invalid num_active_windows", self.num_active_windows
                )
        table = _arrow_points_to.get(key)
        if table is None:
            return None
        return table.get(self.selected_window, {}).get(arrow)

    def rotate_pip_window(self, direction: Arrow) -> None:
        if direction == Arrow.E:
            w = self.next_active_window(self.pip_window)
            if w == self.full_window:
                w = self.next_active_window(w)
        elif direction == Arrow.W:
            w = self.prev_active_window(self.pip_window)
            if w == self.full_window:
                w = self.prev_active_window(w)
        else:
            fail("invalid rotate direction", direction)
        self.pip_window = w

    def from_pip_arrow_points_to(self, arrow: Arrow) -> PipLocation | None:
        assert self.layout_mode == FULLSCREEN and self.fullscreen_mode == PIP
        match (self.pip_location(), arrow):
            case (PipLocation.NW, Arrow.E):
                return PipLocation.NE
            case (PipLocation.NW, Arrow.S):
                return PipLocation.SW
            case (PipLocation.NE, Arrow.W):
                return PipLocation.NW
            case (PipLocation.NE, Arrow.S):
                return PipLocation.SE
            case (PipLocation.SW, Arrow.N):
                return PipLocation.NW
            case (PipLocation.SW, Arrow.E):
                return PipLocation.SE
            case (PipLocation.SE, Arrow.N):
                return PipLocation.NE
            case (PipLocation.SE, Arrow.W):
                return PipLocation.SW
            case _:
                return None

    def arrow_points_from_full_to_pip(self, arrow: Arrow) -> bool:
        if arrow not in (Arrow.N, Arrow.S):
            return False
        loc = self.pip_location()
        return (loc in (PipLocation.NW, PipLocation.NE) and arrow == Arrow.N) or (
            loc in (PipLocation.SW, PipLocation.SE) and arrow == Arrow.S
        )

    def arrow_points_from_pip_to_full(self, arrow: Arrow) -> bool:
        return arrow in (Arrow.N, Arrow.S) and not self.arrow_points_from_full_to_pip(
            arrow
        )

    def pressed_arrow_in_full(self, arrow: Arrow) -> None:
        match arrow:
            case Arrow.N | Arrow.S:
                pass
            case Arrow.E:
                self.full_window = self.next_active_window(self.selected_window)
                self.selected_window = self.full_window
            case Arrow.W:
                self.full_window = self.prev_active_window(self.selected_window)
                self.selected_window = self.full_window

    def pressed_arrow_in_pip(self, arrow: Arrow, *, double_tap: bool) -> None:
        snapshot_selected_window = self.selected_window
        if double_tap:
            # Double tap -- undo single-tap effect and change PIP location.
            self.selected_window = self.last_selected_window
            match arrow:
                case Arrow.E:
                    self.rotate_pip_window(Arrow.W)
                case Arrow.W:
                    self.rotate_pip_window(Arrow.E)
                case Arrow.N | Arrow.S:
                    pass
            pip_loc = self.from_pip_arrow_points_to(arrow)
            if pip_loc is not None:
                self.pip_location_by_tv[self.window_tv[self.full_window]] = pip_loc
            self.last_button = None
            return
        # Single tap
        pip_is_selected = self.selected_window == self.pip_window
        match arrow:
            case Arrow.E:
                self.rotate_pip_window(Arrow.E)
                if pip_is_selected:
                    self.selected_window = self.pip_window
            case Arrow.W:
                self.rotate_pip_window(Arrow.W)
                if pip_is_selected:
                    self.selected_window = self.pip_window
            case Arrow.N | Arrow.S:
                if pip_is_selected:
                    if self.arrow_points_from_pip_to_full(arrow):
                        self.selected_window = self.full_window
                else:
                    if self.arrow_points_from_full_to_pip(arrow):
                        self.selected_window = self.pip_window
        self.last_button = Button(f"ARROW_{arrow.name}")
        self.last_selected_window = snapshot_selected_window

    def pressed_arrow_in_multiview(self, arrow: Arrow, *, double_tap: bool) -> None:
        # If single tap, change the selected window to the pointed-to window. If double
        # tap, swap the previously selected window with the previously pointed-to window.
        self.selected_window_has_distinct_border = True
        if double_tap:
            # Double tap
            points_to = self.selected_window
            self.swap_window_tvs(self.last_selected_window, points_to)
            if self.window_is_prominent(self.last_selected_window):
                self.selected_window = self.last_selected_window
            else:
                self.selected_window = points_to
            self.last_button = None
        else:
            points_to = self.arrow_points_to(arrow)
            if points_to is not None:
                # Single tap
                self.last_button = Button(f"ARROW_{arrow.name}")
                self.last_selected_window = self.selected_window
                self.selected_window = points_to

    def pressed_arrow(self, arrow: Arrow, *, double_tap: bool) -> None:
        match self.layout_mode:
            case LayoutMode.MULTIVIEW:
                self.pressed_arrow_in_multiview(arrow, double_tap=double_tap)
            case LayoutMode.FULLSCREEN:
                match self.fullscreen_mode:
                    case FullscreenMode.FULL:
                        self.pressed_arrow_in_full(arrow)
                    case FullscreenMode.PIP:
                        self.pressed_arrow_in_pip(arrow, double_tap=double_tap)

    def pressed(self, button: Button, *, maybe_double_tap: bool = False) -> JSON:
        double_tap = maybe_double_tap and self.last_button == button
        self.last_button = None
        result: JSON = {}
        match button:
            case Button.ARROW_N:
                self.pressed_arrow(Arrow.N, double_tap=double_tap)
            case Button.ARROW_E:
                self.pressed_arrow(Arrow.E, double_tap=double_tap)
            case Button.ARROW_W:
                self.pressed_arrow(Arrow.W, double_tap=double_tap)
            case Button.ARROW_S:
                self.pressed_arrow(Arrow.S, double_tap=double_tap)
            case Button.REMOTE:
                result = self.remote(double_tap=double_tap)
            case Button.SELECT:
                self.pressed_select()
            case Button.BACK:
                self.pressed_back()
            case Button.PLAY_PAUSE:
                self.pressed_play_pause()
            case Button.ACTIVATE_TV:
                self.activate_tv()
            case Button.DEACTIVATE_TV_FIRST:
                self.deactivate_tv(place_first_in_inactive=True)
            case Button.DEACTIVATE_TV_LAST:
                self.deactivate_tv(place_first_in_inactive=False)
            case Button.TOGGLE_SUBMODE:
                self.toggle_submode()
            case _:
                fail("invalid button", button)
        return result

    def fsm_key(self) -> int:
        return int(FsmState.create(self))

    def explore_fsm_machine(
        self,
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
                                    "after": decode_fsm_state_fields(
                                        FsmState.create(base)
                                    ),
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
                                print(
                                    f"states={seen} transitions={transitions}",
                                    flush=True,
                                )
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
        self,
        max_states: int = 500_000,
        validate: bool = True,
        report_powers_of_two: bool = False,
        save_json_to: str | Path | None = None,
    ) -> tuple[int, int, bool]:
        """Breadth-first exploration of reachable FSM states.

        Returns (num_states, num_transitions, complete) where complete=False if the
        search hit max_states and stopped early.
        """
        machine = self.explore_fsm_machine(
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

    def render(self) -> JtechOutput:
        def window(
            mode: Mode, layout_window: Window, mv_window: Window | None = None
        ) -> WindowContents:
            if mv_window is None:
                mv_window = layout_window
            if not mode.window_has_border(layout_window):
                border = None
            elif mv_window == self.selected_window:
                match self.remote_mode:
                    case RemoteMode.APPLE_TV:
                        border = Color.RED
                    case RemoteMode.MULTIVIEWER:
                        if self.selected_window_has_distinct_border:
                            border = Color.GREEN
                        else:
                            border = Color.GRAY
            else:
                border = Color.GRAY
            return WindowContents(hdmi=self.window_input(mv_window), border=border)

        match self.layout_mode:
            case LayoutMode.FULLSCREEN:
                match self.fullscreen_mode:
                    case FullscreenMode.FULL:
                        layout = Full(w1=window(Mode.FULL, W1, self.full_window))
                    case FullscreenMode.PIP:
                        layout = Pip(
                            pip_location=self.pip_location(),
                            w1=window(Mode.PIP, W1, self.full_window),
                            w2=window(Mode.PIP, W2, self.pip_window),
                        )
            case LayoutMode.MULTIVIEW:
                assert_(self.num_active_windows >= 2)
                match self.num_active_windows:
                    case 2:
                        mode = Mode.PBP
                    case 3:
                        mode = Mode.TRIPLE
                    case 4:
                        mode = Mode.QUAD
                    case _:
                        fail(f"invalid num_active_windows={self.num_active_windows}")
                submode = self.multiview_submode
                if mode == Mode.PBP:
                    layout = Pbp(
                        submode=submode,
                        w1=window(mode, W1),
                        w2=window(mode, W2),
                    )
                elif mode == Mode.TRIPLE:
                    layout = Triple(
                        submode=submode,
                        w1=window(mode, W1),
                        w2=window(mode, W2),
                        w3=window(mode, W3),
                    )
                else:
                    layout = Quad(
                        submode=submode,
                        w1=window(mode, W1),
                        w2=window(mode, W2),
                        w3=window(mode, W3),
                        w4=window(mode, W4),
                    )
            case _:
                fail("invalid layout_mode", self.layout_mode)
        return JtechOutput(
            layout=layout, audio_from=self.window_input(self.selected_window)
        )


def explore_fsm_cli(
    *,
    max_states: int = 10_000_000,
    report_powers_of_two: bool = True,
    validate: bool = True,
) -> tuple[int, int, bool]:
    mv = MvScreen()
    states, transitions, complete = mv.explore_fsm(
        max_states=max_states,
        report_powers_of_two=report_powers_of_two,
        validate=validate,
        save_json_to=Path(__file__).resolve().parent / "mv_screen_fsm.json",
    )
    print(f"done: states={states} transitions={transitions} complete={complete}")
    return states, transitions, complete
