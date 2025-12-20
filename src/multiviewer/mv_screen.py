from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import timedelta

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
    DEACTIVATE_TV = auto()
    TOGGLE_SUBMODE = auto()
    ARROW_N = auto()
    ARROW_E = auto()
    ARROW_W = auto()
    ARROW_S = auto()


@dataclass(frozen=True)
class FsmState:
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

    @classmethod
    def from_screen(cls, screen: MvScreen) -> FsmState:
        return cls(
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

    def power_on(self) -> None:
        self.remote_mode = MULTIVIEWER
        self.selected_window_has_distinct_border = True

    def activate_tv(self) -> None:
        if self.num_active_windows < max_num_windows:
            self.num_active_windows += 1

    def last_active_window(self) -> Window:
        return Window.of_int(self.num_active_windows)

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

    def deactivate_tv(self) -> None:
        if self.num_active_windows == 1:
            return
        self.demote_tv(self.selected_window)
        self.num_active_windows -= 1
        self.selected_window = W1
        self.selected_window_has_distinct_border = True
        if self.layout_mode == FULLSCREEN:
            self.full_window = W1
            if self.fullscreen_mode == FullscreenMode.PIP:
                self.set_pip_window()
        if self.num_active_windows == 1:
            self.layout_mode = FULLSCREEN
            self.fullscreen_mode = FULL
            self.full_window = W1

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
        if self.layout_mode == LayoutMode.FULLSCREEN and self.num_active_windows > 1:
            self.entered_w1_prominent()
            self.layout_mode = MULTIVIEW

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
        v = [Window.of_int(i) for i in range(1, 1 + self.num_active_windows)]
        match self.layout_mode:
            case LayoutMode.FULLSCREEN:
                pass
            case LayoutMode.MULTIVIEW:
                assert_(self.num_active_windows >= 2)
                assert_(self.selected_window in v)

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
        return _arrow_points_to[key][self.selected_window].get(arrow)

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
            case Button.DEACTIVATE_TV:
                self.deactivate_tv()
            case Button.TOGGLE_SUBMODE:
                self.toggle_submode()
            case _:
                fail("invalid button", button)
        return result

    def fsm_key(self) -> FsmState:
        return FsmState.from_screen(self)

    def explore_fsm(
        self,
        max_states: int = 500_000,
        validate: bool = True,
        report_powers_of_two: bool = False,
    ) -> tuple[int, int, bool]:
        """Breadth-first exploration of reachable FSM states.

        Returns (num_states, num_transitions, complete) where complete=False if the
        search hit max_states and stopped early.
        """
        base = MvScreen()
        queue: deque[FsmState] = deque([FsmState.from_screen(base)])
        seen: set[FsmState] = set(queue)
        transitions = 0
        next_report = 1

        buttons = list(Button)

        def hydrate(state: FsmState) -> None:
            # Fields not tracked in FSM state: reset to defaults.
            wt = base.window_tv
            wt.clear()
            wt[W1] = TV.TV1
            wt[W2] = TV.TV2
            wt[W3] = TV.TV3
            wt[W4] = TV.TV4
            pl = base.pip_location_by_tv
            pl.clear()
            for tv in TV.all():
                pl[tv] = PipLocation.NE
            # Overwrite tracked fields from FSM state.
            base.layout_mode = state.layout_mode
            base.num_active_windows = state.num_active_windows
            base.multiview_submode = state.multiview_submode
            base.fullscreen_mode = state.fullscreen_mode
            base.full_window = state.full_window
            base.pip_window = state.pip_window
            base.selected_window = state.selected_window
            base.selected_window_has_distinct_border = (
                state.selected_window_has_distinct_border
            )
            base.remote_mode = state.remote_mode
            base.last_button = state.last_button
            base.last_selected_window = state.last_selected_window

        while queue:
            state = queue.popleft()
            for button in buttons:
                for maybe_double_tap in (False, True):
                    hydrate(state)
                    base.pressed(button, maybe_double_tap=maybe_double_tap)
                    if validate:
                        base.validate()
                    key = FsmState.from_screen(base)
                    transitions += 1
                    if key not in seen:
                        seen.add(key)
                        if report_powers_of_two and len(seen) >= next_report:
                            while next_report <= len(seen):
                                print(
                                    f"states={len(seen)} transitions={transitions}",
                                    flush=True,
                                )
                                next_report *= 2
                        if len(seen) >= max_states:
                            return (len(seen), transitions, False)
                        queue.append(key)

        return (len(seen), transitions, True)

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
