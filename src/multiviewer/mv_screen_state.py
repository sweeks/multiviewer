from __future__ import annotations

# Standard library
from dataclasses import dataclass, field

# Third-party
from dataclasses_json import dataclass_json

# Local package
from .base import *
from .atv import TV
from .json_field import json_dict
from .jtech import Color, Hdmi, Mode, PipLocation, Submode, Window
from .jtech_output import Full, JtechOutput, Pbp, Pip, Quad, Triple, WindowContents


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
class MvScreenState(Jsonable):
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

    def activate_tv(self) -> None:
        if self.num_active_windows < max_num_windows:
            self.num_active_windows += 1

    def last_active_window(self) -> Window:
        return Window.of_int(self.num_active_windows)

    def next_active_window(self, w: Window) -> Window:
        return Window.of_int(w.to_int() % self.num_active_windows + 1)

    def set_pip_window(self) -> None:
        self.pip_window = self.next_active_window(self.full_window)

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

    def toggle_submode(self) -> None:
        match self.layout_mode:
            case LayoutMode.MULTIVIEW:
                self.multiview_submode = self.multiview_submode.flip()
            case LayoutMode.FULLSCREEN:
                if self.num_active_windows >= 2:
                    match self.fullscreen_mode:
                        case FullscreenMode.FULL:
                            self.fullscreen_mode = PIP
                            self.set_pip_window()
                        case FullscreenMode.PIP:
                            self.fullscreen_mode = FULL
                            self.selected_window = self.full_window

    def window_input(self, w: Window) -> Hdmi:
        return tv2hdmi(self.window_tv[w])

    def pip_location(self) -> PipLocation:
        return self.pip_location_by_tv[self.window_tv[self.full_window]]

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
