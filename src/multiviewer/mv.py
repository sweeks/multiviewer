from __future__ import annotations

# Standard library
from datetime import datetime, timedelta
from pathlib import Path

# Third-party
from dataclasses_json import dataclass_json

# Local package
from . import aio, json_field
from .aio import Task
from .atv import TV, ATVs
from .base import *
from .json_field import json_dict
from .jtech import Color, Hdmi, Mode, PipLocation, Power, Submode, Window
from .jtech_manager import JtechManager
from .jtech_output import Full, JtechOutput, Pbp, Pip, Quad, Triple, WindowContents
from .mv_screen_state import (
    FULL,
    FULLSCREEN,
    MULTIVIEW,
    PIP,
    APPLE_TV,
    MULTIVIEWER,
    W1,
    W1_PROMINENT,
    W2,
    W3,
    W4,
    WINDOWS_SAME,
    FullscreenMode,
    LayoutMode,
    MvScreenState,
    RemoteMode,
    initial_pip_location_by_tv,
    initial_window_tv,
    max_num_windows,
    min_num_windows,
)
from .volume import Volume

DOUBLE_TAP_MAX_DURATION = timedelta(seconds=0.3)


class RealClock:
    def now(self) -> datetime:
        return datetime.now()

    def advance(self, _: float) -> None:
        pass


class VirtualClock:
    def __init__(self) -> None:
        self._now = datetime.now()

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


H1 = Hdmi.H1
H2 = Hdmi.H2
H3 = Hdmi.H3
H4 = Hdmi.H4


def volume_deltas_zero():
    return dict.fromkeys(TV.all(), 0)


def initial_pip_location_by_tv():
    return dict.fromkeys(TV.all(), PipLocation.NE)


def initial_window_tv():
    return {W1: TV.TV1, W2: TV.TV2, W3: TV.TV3, W4: TV.TV4}


@dataclass(slots=True)
class ArrowPress:
    at: datetime
    arrow: Arrow
    points_to: Window | None
    selected_window: Window


@dataclass(slots=True)
class RemotePress:
    at: datetime
    selected_window: Window


@dataclass_json
@dataclass(slots=True)
class Multiviewer(Jsonable):
    # power is the state of the virtual multiviewer.  During initialization, we ensure
    # that the physical devices match it.
    power: Power = Power.ON
    screen_state: MvScreenState = field(default_factory=MvScreenState)
    volume_delta_by_tv: dict[TV, int] = field(default_factory=volume_deltas_zero)
    volume: Volume = Volume.field()
    last_arrow_press: ArrowPress | None = field(default=None, metadata=json_field.omit)
    last_remote_press: RemotePress | None = field(default=None, metadata=json_field.omit)
    clock: RealClock | VirtualClock = field(
        default_factory=RealClock, metadata=json_field.omit
    )
    jtech_manager: JtechManager = JtechManager.field()
    atvs: ATVs = ATVs.field()

    @property
    def window_tv(self):
        return self.screen_state.window_tv

    @window_tv.setter
    def window_tv(self, v):
        self.screen_state.window_tv = v

    @property
    def layout_mode(self):
        return self.screen_state.layout_mode

    @layout_mode.setter
    def layout_mode(self, v):
        self.screen_state.layout_mode = v

    @property
    def num_active_windows(self):
        return self.screen_state.num_active_windows

    @num_active_windows.setter
    def num_active_windows(self, v):
        self.screen_state.num_active_windows = v

    @property
    def multiview_submode(self):
        return self.screen_state.multiview_submode

    @multiview_submode.setter
    def multiview_submode(self, v):
        self.screen_state.multiview_submode = v

    @property
    def fullscreen_mode(self):
        return self.screen_state.fullscreen_mode

    @fullscreen_mode.setter
    def fullscreen_mode(self, v):
        self.screen_state.fullscreen_mode = v

    @property
    def full_window(self):
        return self.screen_state.full_window

    @full_window.setter
    def full_window(self, v):
        self.screen_state.full_window = v

    @property
    def pip_window(self):
        return self.screen_state.pip_window

    @pip_window.setter
    def pip_window(self, v):
        self.screen_state.pip_window = v

    @property
    def pip_location_by_tv(self):
        return self.screen_state.pip_location_by_tv

    @pip_location_by_tv.setter
    def pip_location_by_tv(self, v):
        self.screen_state.pip_location_by_tv = v

    @property
    def selected_window(self):
        return self.screen_state.selected_window

    @selected_window.setter
    def selected_window(self, v):
        self.screen_state.selected_window = v

    @property
    def selected_window_has_distinct_border(self):
        return self.screen_state.selected_window_has_distinct_border

    @selected_window_has_distinct_border.setter
    def selected_window_has_distinct_border(self, v):
        self.screen_state.selected_window_has_distinct_border = v

    @property
    def remote_mode(self):
        return self.screen_state.remote_mode

    @remote_mode.setter
    def remote_mode(self, v):
        self.screen_state.remote_mode = v


def last_active_window(mv: Multiviewer) -> Window:
    return Window.of_int(mv.num_active_windows)


def prev_active_window(mv: Multiviewer, w: Window) -> Window:
    n = mv.num_active_windows
    return Window.of_int(1 + ((w.to_int() + n - 2) % n))


def next_active_window(mv: Multiviewer, w: Window) -> Window:
    return Window.of_int(w.to_int() % mv.num_active_windows + 1)


def window_tv(mv: Multiviewer, w: Window) -> TV:
    return mv.screen_state.window_tv[w]


def window_input(mv: Multiviewer, w: Window) -> Hdmi:
    return mv.screen_state.window_input(w)


def pip_location(mv: Multiviewer) -> PipLocation:
    return mv.screen_state.pip_location()


def selected_tv(mv: Multiviewer) -> TV:
    return window_tv(mv, mv.selected_window)


def visible(mv: Multiviewer) -> list[Window]:
    return [Window.of_int(i) for i in range(1, 1 + mv.num_active_windows)]


def is_visible(mv: Multiviewer, w: Window) -> bool:
    return w in visible(mv)


def validate(mv: Multiviewer) -> None:
    assert_equal(set(mv.window_tv.keys()), set(Mode.QUAD.windows()))
    assert_equal(len(set(mv.window_tv.values())), len(mv.window_tv))
    assert_(min_num_windows <= mv.num_active_windows <= max_num_windows)
    if mv.num_active_windows == 1:
        assert_(mv.layout_mode == FULLSCREEN)
        assert_(mv.fullscreen_mode == FULL)
    v = visible(mv)
    match mv.layout_mode:
        case LayoutMode.FULLSCREEN:
            pass
        case LayoutMode.MULTIVIEW:
            assert_(mv.num_active_windows >= 2)
            assert_(mv.selected_window in v)


async def shutdown(mv: Multiviewer) -> None:
    await mv.atvs.shutdown()


def reset(mv: Multiviewer) -> None:
    mv.screen_state = MvScreenState()
    mv.last_arrow_press = None
    mv.last_remote_press = None
    mv.volume_delta_by_tv = volume_deltas_zero()
    mv.volume.reset()


def set_should_send_commands_to_device(mv: Multiviewer, b: bool) -> None:
    mv.jtech_manager.set_should_send_commands_to_device(b)
    mv.atvs.set_should_send_commands_to_device(b)
    mv.volume.set_should_send_commands_to_device(b)


def use_virtual_clock(mv: Multiviewer) -> None:
    mv.clock = VirtualClock()


def advance_clock(mv: Multiviewer, seconds: float) -> None:
    mv.clock.advance(seconds)


async def initialize(mv: Multiviewer):
    if False:
        debug_print(mv)
    match mv.power:
        case Power.OFF:
            await power_off(mv)
        case Power.ON:
            await power_on(mv)
    validate(mv)


async def create() -> Multiviewer:
    mv = Multiviewer()
    await initialize(mv)
    return mv


async def load(path: Path) -> Multiviewer:
    log(f"loading multiviewer state from {path}")
    try:
        mv = Multiviewer.from_json(path.read_text())
        await initialize(mv)
        return mv
    except Exception:
        log("failed to load, creating new multiviewer")
        return await create()


def save(mv: Multiviewer, path: Path) -> None:
    if False:
        debug_print(mv)
    validate(mv)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(mv.to_json(indent=2))
    tmp.replace(path)


def set_power(mv: Multiviewer, p: Power) -> None:
    if False:
        debug_print(p)
    mv.power = p
    mv.jtech_manager.set_power(p)


async def power_off(mv: Multiviewer) -> None:
    if False:
        debug_print(mv)
    log("turning off power")
    set_power(mv, Power.OFF)
    for tv in TV.all():
        mv.atvs.atv(tv).sleep()
    await mv.atvs.synced()
    log("power is off")


async def power_on(mv: Multiviewer) -> None:
    if False:
        debug_print(mv)
    log("turning on power")
    set_power(mv, Power.ON)
    # We reset all the volume deltas to zero, because this is a new TV session for the
    # user.  This causes the initial update_jtech_output to set the desired volume_delta
    # to zero, which in turn causes the Volume manager to set the actual volume_delta
    # to zero.
    mv.volume_delta_by_tv = volume_deltas_zero()
    mv.remote_mode = MULTIVIEWER
    # Waking TV1 turns on the LG via CEC.
    for tv in TV.all():
        mv.atvs.atv(tv).wake()
    await mv.atvs.synced()
    log("power is on")


async def toggle_power(mv: Multiviewer) -> None:
    match mv.power:
        case Power.OFF:
            await power_on(mv)
        case Power.ON:
            await power_off(mv)


def window_is_prominent(mv: Multiviewer, w: Window) -> bool:
    if w != W1:
        return False
    match mv.layout_mode:
        case LayoutMode.FULLSCREEN:
            return True
        case LayoutMode.MULTIVIEW:
            return mv.multiview_submode == W1_PROMINENT


def swap_window_tvs(mv: Multiviewer, w1: Window, w2: Window) -> None:
    if False:
        debug_print(f"{w1} <-> {w2}")
    window_tv = mv.window_tv
    tv1 = window_tv[w1]
    tv2 = window_tv[w2]
    window_tv[w1] = tv2
    window_tv[w2] = tv1


class Arrow(MyStrEnum):
    N = auto()
    E = auto()
    W = auto()
    S = auto()


N = Arrow.N
E = Arrow.E
W = Arrow.W
S = Arrow.S

_arrow_points_to = {
    2: {W1: {E: W2}, W2: {W: W1}},
    3: {
        W1: {N: W2, S: W3},
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


def arrow_points_to(mv: Multiviewer, arrow: Arrow) -> Window | None:
    if False:
        debug_print(arrow)
    match mv.num_active_windows:
        case 2 | 3:
            key = mv.num_active_windows
        case 4:
            key = (mv.num_active_windows, mv.multiview_submode)
        case _:
            fail("arrow_points_to invalid num_active_windows", mv.num_active_windows)
    return _arrow_points_to[key][mv.selected_window].get(arrow)


def pressed_arrow_in_full(mv: Multiviewer, arrow: Arrow) -> None:
    match arrow:
        case Arrow.N | Arrow.S:
            pass
        case Arrow.E:
            mv.full_window = next_active_window(mv, mv.selected_window)
            mv.selected_window = mv.full_window
        case Arrow.W:
            mv.full_window = prev_active_window(mv, mv.selected_window)
            mv.selected_window = mv.full_window


def rotate_pip_window(mv: Multiviewer, direction: Arrow) -> None:
    if direction == Arrow.E:
        w = next_active_window(mv, mv.pip_window)
        if w == mv.full_window:
            w = next_active_window(mv, w)
    elif direction == Arrow.W:
        w = prev_active_window(mv, mv.pip_window)
        if w == mv.full_window:
            w = prev_active_window(mv, w)
    else:
        fail("invalid rotate direction", direction)
    mv.pip_window = w


def from_pip_arrow_points_to(mv: Multiviewer, arrow: Arrow) -> PipLocation | None:
    assert mv.layout_mode == FULLSCREEN and mv.fullscreen_mode == PIP
    match (pip_location(mv), arrow):
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


def arrow_points_from_full_to_pip(mv: Multiviewer, arrow: Arrow) -> bool:
    if arrow not in (Arrow.N, Arrow.S):
        return False
    loc = pip_location(mv)
    return (loc in (PipLocation.NW, PipLocation.NE) and arrow == Arrow.N) or (
        loc in (PipLocation.SW, PipLocation.SE) and arrow == Arrow.S
    )


def arrow_points_from_pip_to_full(mv: Multiviewer, arrow: Arrow) -> bool:
    return arrow in (Arrow.N, Arrow.S) and not arrow_points_from_full_to_pip(mv, arrow)


def pressed_arrow_in_pip(mv: Multiviewer, arrow: Arrow) -> None:
    snapshot_selected_window = mv.selected_window
    at = mv.clock.now()
    last_press = mv.last_arrow_press
    if (
        last_press is not None
        and arrow == last_press.arrow
        and at - last_press.at <= DOUBLE_TAP_MAX_DURATION
    ):
        # Double tap -- undo single-tap effect and change PIP location.
        mv.selected_window = last_press.selected_window
        match arrow:
            case Arrow.E:
                rotate_pip_window(mv, Arrow.W)
            case Arrow.W:
                rotate_pip_window(mv, Arrow.E)
            case Arrow.N | Arrow.S:
                pass
        pip_loc = from_pip_arrow_points_to(mv, arrow)
        if pip_loc is not None:
            mv.pip_location_by_tv[window_tv(mv, mv.full_window)] = pip_loc
        mv.last_arrow_press = None
        return
    # Single tap
    pip_is_selected = mv.selected_window == mv.pip_window
    match arrow:
        case Arrow.E:
            rotate_pip_window(mv, Arrow.E)
            if pip_is_selected:
                mv.selected_window = mv.pip_window
        case Arrow.W:
            rotate_pip_window(mv, Arrow.W)
            if pip_is_selected:
                mv.selected_window = mv.pip_window
        case Arrow.N | Arrow.S:
            if pip_is_selected:
                if arrow_points_from_pip_to_full(mv, arrow):
                    mv.selected_window = mv.full_window
            else:
                if arrow_points_from_full_to_pip(mv, arrow):
                    mv.selected_window = mv.pip_window
    mv.last_arrow_press = ArrowPress(
        arrow=arrow,
        points_to=None,
        at=at,
        selected_window=snapshot_selected_window,
    )


def pressed_arrow_in_multiview(mv: Multiviewer, arrow: Arrow) -> None:
    # If single tap, change the selected window to the pointed-to window. If double
    # tap, swap the previously selected window with the previously pointed-to window.
    mv.selected_window_has_distinct_border = True
    last_press = mv.last_arrow_press
    at = mv.clock.now()
    if (
        last_press is not None
        and arrow == last_press.arrow
        and at - last_press.at <= DOUBLE_TAP_MAX_DURATION
    ):
        # Double tap
        assert last_press.points_to is not None
        log_double_tap_duration(at - last_press.at)
        mv.last_arrow_press = None
        swap_window_tvs(mv, last_press.selected_window, last_press.points_to)
        if window_is_prominent(mv, last_press.selected_window):
            mv.selected_window = last_press.selected_window
        else:
            mv.selected_window = last_press.points_to
    else:
        points_to = arrow_points_to(mv, arrow)
        if points_to is not None:
            # Single tap
            mv.last_arrow_press = ArrowPress(
                arrow=arrow,
                points_to=points_to,
                at=at,
                selected_window=mv.selected_window,
            )
            mv.selected_window = points_to


def activate_tv(mv: Multiviewer) -> None:
    if mv.num_active_windows < max_num_windows:
        mv.num_active_windows += 1


def demote_tv(mv: Multiviewer, w1: Window) -> None:
    last = last_active_window(mv)
    while w1 != last:
        w2 = next_active_window(mv, w1)
        swap_window_tvs(mv, w1, w2)
        w1 = w2


def deactivate_tv(mv: Multiviewer) -> None:
    if mv.num_active_windows == 1:
        return
    demote_tv(mv, mv.selected_window)
    mv.num_active_windows -= 1
    mv.selected_window = W1
    mv.selected_window_has_distinct_border = True
    if mv.layout_mode == FULLSCREEN:
        mv.full_window = W1
        if mv.fullscreen_mode == FullscreenMode.PIP:
            set_pip_window(mv)
    if mv.num_active_windows == 1:
        mv.layout_mode = FULLSCREEN
        mv.fullscreen_mode = FULL
        mv.full_window = W1


def set_pip_window(mv: Multiviewer) -> None:
    mv.pip_window = next_active_window(mv, mv.full_window)


def enter_multiview(mv: Multiviewer) -> None:
    if mv.num_active_windows >= 2:
        mv.layout_mode = MULTIVIEW
        mv.selected_window_has_distinct_border = True
        if not is_visible(mv, mv.selected_window):
            swap_window_tvs(mv, W1, mv.selected_window)
            mv.selected_window = W1


def enter_fullscreen(mv: Multiviewer) -> None:
    mv.layout_mode = FULLSCREEN
    mv.full_window = mv.selected_window
    if mv.fullscreen_mode == FullscreenMode.PIP:
        set_pip_window(mv)


def toggle_submode(mv: Multiviewer) -> None:
    match mv.layout_mode:
        case LayoutMode.MULTIVIEW:
            mv.multiview_submode = mv.multiview_submode.flip()
        case LayoutMode.FULLSCREEN:
            if mv.num_active_windows >= 2:
                match mv.fullscreen_mode:
                    case FullscreenMode.FULL:
                        mv.fullscreen_mode = PIP
                        set_pip_window(mv)
                    case FullscreenMode.PIP:
                        mv.fullscreen_mode = FULL
                        mv.selected_window = mv.full_window


def pressed_arrow(mv: Multiviewer, arrow: Arrow) -> None:
    if False:
        debug_print(arrow)
    match mv.layout_mode:
        case LayoutMode.MULTIVIEW:
            pressed_arrow_in_multiview(mv, arrow)
        case LayoutMode.FULLSCREEN:
            match mv.fullscreen_mode:
                case FullscreenMode.FULL:
                    pressed_arrow_in_full(mv, arrow)
                case FullscreenMode.PIP:
                    pressed_arrow_in_pip(mv, arrow)


def pressed_back(mv: Multiviewer, tv: TV) -> None:
    if mv.layout_mode == LayoutMode.FULLSCREEN and mv.num_active_windows > 1:
        enter_multiview(mv)


def pressed_play_pause(mv: Multiviewer) -> None:
    mv.selected_window_has_distinct_border = not mv.selected_window_has_distinct_border


def toggle_mute(mv: Multiviewer) -> None:
    mv.volume.toggle_mute()


def adjust_volume(mv: Multiviewer, by: int) -> None:
    mv.volume.unmute()
    mv.volume_delta_by_tv[selected_tv(mv)] += by


def describe_volume(mv: Multiviewer) -> str:
    return mv.volume.describe_volume()


async def describe_jtech_output(mv: Multiviewer) -> str:
    output = await mv.jtech_manager.current_output()
    return output.one_line_description()


async def info(mv: Multiviewer) -> str:
    output = await describe_jtech_output(mv)
    volume = describe_volume(mv)
    return f"{output} {volume}"


def log_double_tap_duration(d: timedelta) -> None:
    ms = int(d.total_seconds() * 1000)
    log(f"double-tap duration: {ms}ms")


def remote(mv: Multiviewer, tv: TV) -> JSON:
    this_press = RemotePress(at=mv.clock.now(), selected_window=mv.selected_window)
    last_press = mv.last_remote_press
    if (
        last_press is not None
        and last_press.selected_window == this_press.selected_window
        and this_press.at - last_press.at <= DOUBLE_TAP_MAX_DURATION
    ):
        # Double tap.  The shortcut will open the Remote app on TV <i>
        mv.last_remote_press = None
        # Flip again to cancel the single-tap mode change.
        mv.remote_mode = mv.remote_mode.flip()
        return tv.to_int()
    else:
        # Single tap
        mv.last_remote_press = this_press
        mv.remote_mode = mv.remote_mode.flip()
        return {}


def swap_full_and_pip_windows(mv: Multiviewer) -> None:
    old_full = mv.full_window
    mv.full_window = mv.pip_window
    mv.pip_window = old_full
    mv.selected_window = mv.full_window


async def do_command(mv: Multiviewer, args: list[str]) -> JSON:
    if False:
        debug_print(args)
    command = args[0]
    if mv.power == Power.OFF and command not in ["Power", "Power_on"]:
        return {}
    tv = selected_tv(mv)
    atv = mv.atvs.atv(tv)
    match command:
        case "Activate_tv":
            activate_tv(mv)
        case "Back":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.menu()
                case RemoteMode.MULTIVIEWER:
                    pressed_back(mv, tv)
        case "Down" | "S":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.down()
                case RemoteMode.MULTIVIEWER:
                    pressed_arrow(mv, S)
        case "Home":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.home()
                case RemoteMode.MULTIVIEWER:
                    toggle_submode(mv)
        case "Info":
            return await info(mv)
        case "Launch":
            atv.launch(args[1])
        case "Left" | "W":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.left()
                case RemoteMode.MULTIVIEWER:
                    pressed_arrow(mv, W)
        case "Mute":
            toggle_mute(mv)
        case "Play_pause":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.play_pause()
                case RemoteMode.MULTIVIEWER:
                    pressed_play_pause(mv)
        case "Power_on":
            if mv.power == Power.OFF:
                mv.selected_window_has_distinct_border = True
                await power_on(mv)
        case "Power":
            await toggle_power(mv)
        case "Remote":
            return remote(mv, tv)
        case "Deactivate_tv":
            deactivate_tv(mv)
        case "Reset":
            reset(mv)
        case "Right" | "E":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.right()
                case RemoteMode.MULTIVIEWER:
                    pressed_arrow(mv, E)
        case "Screensaver":
            atv.screensaver()
        case "Select":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.select()
                case RemoteMode.MULTIVIEWER:
                    match mv.layout_mode:
                        case LayoutMode.MULTIVIEW:
                            enter_fullscreen(mv)
                        case LayoutMode.FULLSCREEN:
                            match mv.fullscreen_mode:
                                case FullscreenMode.FULL:
                                    pass
                                case FullscreenMode.PIP:
                                    swap_full_and_pip_windows(mv)
        case "Sleep":
            atv.sleep()
        case "Test":
            pass
        case "Up" | "N":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.up()
                case RemoteMode.MULTIVIEWER:
                    pressed_arrow(mv, N)
        case "Volume_down":
            adjust_volume(mv, -1)
        case "Volume_up":
            adjust_volume(mv, 1)
        case "Wake":
            atv.wake()
        case _:
            fail("invalid command", command)
    return {}


def render(mv: Multiviewer) -> JtechOutput:
    return mv.screen_state.render()


def update_jtech_output(mv: Multiviewer) -> None:
    mv.jtech_manager.set_output(render(mv))
    mv.volume.set_volume_delta(mv.volume_delta_by_tv[selected_tv(mv)])


async def do_command_and_update_jtech_output(mv: Multiviewer, args: list[str]) -> JSON:
    if False:
        debug_print(args, mv)
    result = await do_command(mv, args)
    validate(mv)
    update_jtech_output(mv)
    return result


async def synced(mv: Multiviewer) -> None:
    if False:
        debug_print(mv)
    await mv.atvs.synced()
    await mv.jtech_manager.synced()
    await mv.volume.synced()
