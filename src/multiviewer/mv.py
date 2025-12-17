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
from .volume import Volume

DOUBLE_TAP_MAX_DURATION = timedelta(seconds=0.3)

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


def hdmi2tv(h: Hdmi) -> TV:
    match h:
        case Hdmi.H1:
            return TV.TV1
        case Hdmi.H2:
            return TV.TV2
        case Hdmi.H3:
            return TV.TV3
        case Hdmi.H4:
            return TV.TV4
    raise AssertionError


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


max_num_windows = 4
min_num_windows = 1


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


@dataclass(slots=True)
class BackPress:
    at: datetime
    selected_window: Window
    tv: TV


@dataclass(slots=True)
class PlayPausePress:
    at: datetime
    selected_window: Window
    previous_border_state: bool


@dataclass_json
@dataclass(slots=True)
class Multiviewer(Jsonable):
    # power is the state of the virtual multiviewer.  During initialization, we ensure
    # that the physical devices match it.
    power: Power = Power.ON
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
    selected_window_border_is_on: bool = True
    control_apple_tv: bool = False
    volume_delta_by_tv: dict[TV, int] = field(default_factory=volume_deltas_zero)
    volume: Volume = Volume.field()
    last_arrow_press: ArrowPress | None = field(default=None, metadata=json_field.omit)
    last_remote_press: RemotePress | None = field(default=None, metadata=json_field.omit)
    last_back_press: BackPress | None = field(default=None, metadata=json_field.omit)
    last_play_pause_press: PlayPausePress | None = field(
        default=None, metadata=json_field.omit
    )
    jtech_manager: JtechManager = JtechManager.field()
    atvs: ATVs = ATVs.field()
    most_recent_command_at: datetime = field(
        default=datetime.now(), metadata=json_field.omit
    )
    task: Task = Task.field()


def num_windows(mv: Multiviewer) -> int:
    return mv.num_active_windows


def last_window(mv: Multiviewer) -> Window:
    return Window.of_int(num_windows(mv))


def prev_window(mv: Multiviewer, w: Window) -> Window:
    n = num_windows(mv)
    return Window.of_int(1 + ((w.to_int() + n - 2) % n))


def next_window(mv: Multiviewer, w: Window) -> Window:
    return Window.of_int(w.to_int() % num_windows(mv) + 1)


def window_tv(mv: Multiviewer, w: Window) -> TV:
    return mv.window_tv[w]


def window_input(mv: Multiviewer, w: Window) -> Hdmi:
    return tv2hdmi(window_tv(mv, w))


def pip_location(mv: Multiviewer) -> PipLocation:
    return mv.pip_location_by_tv[window_tv(mv, mv.full_window)]


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
    if mv.num_active_windows == min_num_windows:
        assert_(mv.layout_mode == FULLSCREEN)
        assert_(mv.fullscreen_mode == FULL)
    v = visible(mv)
    if mv.layout_mode == MULTIVIEW:
        assert_(mv.num_active_windows >= 2)
        assert_(mv.selected_window in v)


async def shutdown(mv: Multiviewer) -> None:
    await mv.atvs.shutdown()


def reset(mv: Multiviewer) -> None:
    mv.num_active_windows = max_num_windows
    mv.multiview_submode = W1_PROMINENT
    mv.layout_mode = MULTIVIEW
    mv.fullscreen_mode = FULL
    mv.full_window = W1
    mv.pip_window = W2
    mv.pip_location_by_tv = initial_pip_location_by_tv()
    mv.selected_window = W1
    mv.selected_window_border_is_on = True
    mv.control_apple_tv = False
    mv.last_arrow_press = None
    mv.last_remote_press = None
    mv.last_back_press = None
    mv.last_play_pause_press = None
    mv.volume_delta_by_tv = volume_deltas_zero()
    mv.volume.reset()
    mv.window_tv = initial_window_tv()


def set_should_send_commands_to_device(mv: Multiviewer, b: bool) -> None:
    mv.jtech_manager.set_should_send_commands_to_device(b)
    mv.atvs.set_should_send_commands_to_device(b)
    mv.volume.set_should_send_commands_to_device(b)


async def update_jtech_output_forever(mv: Multiviewer):
    if False:
        while True:
            await aio.sleep(1)
            update_jtech_output(mv)


async def initialize(mv: Multiviewer):
    if False:
        debug_print()
    mv.task = Task.create(type(mv).__name__, update_jtech_output_forever(mv))
    desired_power = mv.power
    mv.power = await mv.jtech_manager.current_power()
    if mv.power != desired_power:
        if mv.power == Power.ON:
            await power_on(mv)
        else:
            await power_off(mv)
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


def power(mv: Multiviewer) -> Power:
    return mv.power


def set_power(mv: Multiviewer, p: Power) -> None:
    if False:
        debug_print(p)
    mv.power = p
    mv.jtech_manager.set_power(p)


async def power_off(mv: Multiviewer) -> None:
    if False:
        debug_print(mv)
    if mv.power == Power.OFF:
        return
    log("turning off power")
    for tv in TV.all():
        mv.atvs.atv(tv).sleep()
    await mv.atvs.synced()
    set_power(mv, Power.OFF)
    log("power is off")


async def power_on(mv: Multiviewer) -> None:
    if False:
        debug_print(mv)
    if mv.power == Power.ON:
        return
    log("turning on power")
    set_power(mv, Power.ON)
    # We reset all the volume deltas to zero, because this is a new TV session for the
    # user.  This causes the initial update_jtech_output to set the desired volume_delta
    # to zero, which in turn causes the Volume manager to set the actual volume_delta
    # to zero.
    mv.volume_delta_by_tv = volume_deltas_zero()
    mv.control_apple_tv = False
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


def set_selected_window(mv: Multiviewer, w: Window) -> None:
    if False:
        debug_print(mv)
    mv.selected_window = w


def window_is_prominent(mv: Multiviewer, w: Window) -> bool:
    if w != W1:
        return False
    if mv.layout_mode == FULLSCREEN:
        return True
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
            mv.full_window = next_window(mv, mv.selected_window)
            mv.selected_window = mv.full_window
        case Arrow.W:
            mv.full_window = prev_window(mv, mv.selected_window)
            mv.selected_window = mv.full_window


def rotate_pip_window(mv: Multiviewer, direction: Arrow) -> None:
    if direction == Arrow.E:
        w = next_window(mv, mv.pip_window)
        if w == mv.full_window:
            w = next_window(mv, w)
    elif direction == Arrow.W:
        w = prev_window(mv, mv.pip_window)
        if w == mv.full_window:
            w = prev_window(mv, w)
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
    at = datetime.now()
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
    mv.selected_window_border_is_on = True
    last_press = mv.last_arrow_press
    at = datetime.now()
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


def add_window(mv: Multiviewer) -> None:
    if mv.layout_mode == FULLSCREEN:
        mv.layout_mode = MULTIVIEW
        mv.num_active_windows = max(2, mv.num_active_windows)
        swap_window_tvs(mv, W1, mv.full_window)
        mv.selected_window = W1
        if mv.fullscreen_mode == PIP and mv.num_active_windows >= 2:
            if mv.pip_window == W1:
                swap_window_tvs(mv, W2, mv.full_window)
            else:
                swap_window_tvs(mv, W2, mv.pip_window)
    else:
        if mv.num_active_windows < max_num_windows:
            mv.num_active_windows += 1


def demote_window(mv: Multiviewer, w1: Window) -> None:
    if mv.layout_mode == MULTIVIEW:
        last = last_window(mv)
        while w1 != last:
            w2 = next_window(mv, w1)
            swap_window_tvs(mv, w1, w2)
            w1 = w2


def remove_window(mv: Multiviewer) -> None:
    if mv.layout_mode == MULTIVIEW:
        if mv.num_active_windows == min_num_windows:
            return
        if mv.num_active_windows == 2:
            mv.layout_mode = FULLSCREEN
            mv.full_window = mv.selected_window
            mv.fullscreen_mode = FULL
        mv.num_active_windows -= 1
        if not is_visible(mv, mv.selected_window):
            mv.selected_window_border_is_on = True
            mv.selected_window = W1


def maybe_entered_pip(mv: Multiviewer) -> None:
    if mv.fullscreen_mode == PIP and mv.num_active_windows >= 2:
        mv.pip_window = next_window(mv, mv.full_window)
    elif mv.num_active_windows < 2:
        mv.fullscreen_mode = FULL


def toggle_fullscreen(mv: Multiviewer) -> None:
    if mv.layout_mode == FULLSCREEN:
        if mv.num_active_windows >= 2:
            mv.layout_mode = MULTIVIEW
            mv.selected_window_border_is_on = True
            if not is_visible(mv, mv.selected_window):
                swap_window_tvs(mv, W1, mv.selected_window)
                mv.selected_window = W1
    else:
        mv.layout_mode = FULLSCREEN
        mv.full_window = mv.selected_window
        maybe_entered_pip(mv)


def toggle_submode(mv: Multiviewer) -> None:
    if mv.layout_mode == FULLSCREEN:
        if mv.num_active_windows == 1:
            mv.num_active_windows = 2
            mv.fullscreen_mode = PIP
            maybe_entered_pip(mv)
        elif mv.num_active_windows >= 2:
            if mv.fullscreen_mode == FULL:
                mv.fullscreen_mode = PIP
            else:
                mv.fullscreen_mode = FULL
            maybe_entered_pip(mv)
    else:
        mv.multiview_submode = mv.multiview_submode.flip()


def pressed_arrow(mv: Multiviewer, arrow: Arrow) -> None:
    if False:
        debug_print(arrow)
    if mv.layout_mode == FULLSCREEN:
        if mv.fullscreen_mode == PIP:
            pressed_arrow_in_pip(mv, arrow)
        else:
            pressed_arrow_in_full(mv, arrow)
    else:
        pressed_arrow_in_multiview(mv, arrow)


def pressed_back(mv: Multiviewer, tv: TV) -> None:
    at = datetime.now()
    last_press = mv.last_back_press
    if last_press is not None and at - last_press.at <= DOUBLE_TAP_MAX_DURATION:
        log_double_tap_duration(at - last_press.at)
        mv.last_back_press = None
        mv.atvs.atv(last_press.tv).screensaver()
        return
    if mv.layout_mode == FULLSCREEN and mv.num_active_windows == 1:
        mv.last_back_press = None
        add_window(mv)
        return
    if mv.layout_mode == FULLSCREEN:
        mv.last_back_press = None
        if mv.fullscreen_mode == PIP and mv.selected_window == mv.pip_window:
            mv.selected_window = mv.full_window
        else:
            toggle_fullscreen(mv)
        return
    if mv.num_active_windows == min_num_windows:
        mv.last_back_press = None
        return
    mv.last_back_press = BackPress(at=at, selected_window=mv.selected_window, tv=tv)
    demote_window(mv, mv.selected_window)
    remove_window(mv)


def pressed_play_pause(mv: Multiviewer) -> None:
    if mv.layout_mode == FULLSCREEN:
        mv.last_play_pause_press = None
        mv.selected_window_border_is_on = not mv.selected_window_border_is_on
        return
    at = datetime.now()
    last_press = mv.last_play_pause_press
    if (
        last_press is not None
        and last_press.selected_window == mv.selected_window
        and at - last_press.at <= DOUBLE_TAP_MAX_DURATION
    ):
        log_double_tap_duration(at - last_press.at)
        mv.last_play_pause_press = None
        mv.selected_window_border_is_on = last_press.previous_border_state
        toggle_submode(mv)
    else:
        previous_state = mv.selected_window_border_is_on
        mv.selected_window_border_is_on = not mv.selected_window_border_is_on
        mv.last_play_pause_press = PlayPausePress(
            at=at,
            selected_window=mv.selected_window,
            previous_border_state=previous_state,
        )


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
    this_press = RemotePress(at=datetime.now(), selected_window=mv.selected_window)
    last_press = mv.last_remote_press
    if (
        last_press is not None
        and last_press.selected_window == this_press.selected_window
        and this_press.at - last_press.at <= DOUBLE_TAP_MAX_DURATION
    ):
        # Double tap.  The shortcut will open the Remote app on TV <i>
        mv.last_remote_press = None
        mv.control_apple_tv = not mv.control_apple_tv
        return tv.to_int()
    else:
        # Single tap
        mv.last_remote_press = this_press
        mv.control_apple_tv = not mv.control_apple_tv
        return {}


def swap_full_and_pip_windows(mv: Multiviewer) -> None:
    old_full = mv.full_window
    mv.full_window = mv.pip_window
    mv.pip_window = old_full
    mv.selected_window = mv.full_window


async def do_command(mv: Multiviewer, args: list[str]) -> JSON:
    if False:
        debug_print(args)
    mv.most_recent_command_at = datetime.now()
    command = args[0]
    if mv.power == Power.OFF and (command not in ["Power", "Power_on", "Wait"]):
        return {}
    tv = selected_tv(mv)
    atv = mv.atvs.atv(tv)
    match command:
        case "Back":
            if mv.control_apple_tv:
                atv.menu()
            else:
                pressed_back(mv, tv)
        case "Down" | "S":
            if mv.control_apple_tv:
                atv.down()
            else:
                pressed_arrow(mv, S)
        case "Home":
            if mv.control_apple_tv:
                atv.home()
            else:
                if mv.layout_mode == FULLSCREEN:
                    toggle_submode(mv)
                else:
                    add_window(mv)
        case "Info":
            return await info(mv)
        case "Launch":
            atv.launch(args[1])
        case "Left" | "W":
            if mv.control_apple_tv:
                atv.left()
            else:
                pressed_arrow(mv, W)
        case "Mute":
            toggle_mute(mv)
        case "Play_pause":
            if mv.control_apple_tv:
                atv.play_pause()
            else:
                pressed_play_pause(mv)
        case "Power_on":
            mv.selected_window_border_is_on = True
            await power_on(mv)
        case "Power":
            await toggle_power(mv)
        case "Remote":
            return remote(mv, tv)
        case "Reset":
            reset(mv)
        case "Right" | "E":
            if mv.control_apple_tv:
                atv.right()
            else:
                pressed_arrow(mv, E)
        case "Screensaver":
            atv.screensaver()
        case "Select":
            if mv.control_apple_tv:
                atv.select()
            elif mv.layout_mode == FULLSCREEN:
                if mv.fullscreen_mode == PIP:
                    swap_full_and_pip_windows(mv)
                else:
                    pass
            else:
                toggle_fullscreen(mv)
        case "Sleep":
            atv.sleep()
        case "Test":
            pass
        case "Toggle_submode":
            toggle_submode(mv)
        case "Up" | "N":
            if mv.control_apple_tv:
                atv.up()
            else:
                pressed_arrow(mv, N)
        case "Volume_down":
            adjust_volume(mv, -1)
        case "Volume_up":
            adjust_volume(mv, 1)
        case "Wait":
            await aio.sleep(float(args[1]))
        case "Wake":
            atv.wake()
        case _:
            fail("invalid command", command)
    return {}


def render(mv: Multiviewer) -> JtechOutput:
    if False:
        debug_print()

    def window(
        mode: Mode, layout_window: Window, mv_window: Window | None = None
    ) -> WindowContents:
        if mv_window is None:
            mv_window = layout_window
        if not mode.window_has_border(layout_window):
            border = None
        elif mv.control_apple_tv and mv_window == mv.selected_window:
            border = Color.RED
        elif mv.selected_window_border_is_on and mv_window == mv.selected_window:
            border = Color.GREEN
        else:
            border = Color.GRAY
        return WindowContents(hdmi=window_input(mv, mv_window), border=border)

    if mv.layout_mode == FULLSCREEN:
        if mv.fullscreen_mode == FULL:
            layout = Full(w1=window(Mode.FULL, W1, mv.full_window))
        else:
            layout = Pip(
                pip_location=pip_location(mv),
                w1=window(Mode.PIP, W1, mv.full_window),
                w2=window(Mode.PIP, W2, mv.pip_window),
            )
    else:
        assert_(mv.num_active_windows >= 2)
        match mv.num_active_windows:
            case 2:
                mode = Mode.PBP
            case 3:
                mode = Mode.TRIPLE
            case 4:
                mode = Mode.QUAD
            case _:
                fail(f"invalid num_active_windows={mv.num_active_windows}")
        submode = mv.multiview_submode
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
    return JtechOutput(layout=layout, audio_from=window_input(mv, mv.selected_window))


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
