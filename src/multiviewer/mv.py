from __future__ import annotations

# Standard library
from datetime import datetime, timedelta
from pathlib import Path

# Third-party
from dataclasses_json import dataclass_json

# Local package
from . import aio
from . import json_field
from .aio import Task
from .atv import ATVs, TV
from .base import *
from .json_field import json_dict
from .jtech import Color, Hdmi, Mode, PipLocation, Power, Submode, Window
from .jtech_manager import Jtech_manager
from .jtech_screen import Full, Pip, Pbp, Quad, Screen, Triple, Window_contents
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
    assert False


max_num_windows = 4


def volume_deltas_zero():
    return {tv: 0 for tv in TV.all()}


def initial_window_input():
    return {W1: H1, W2: H2, W3: H3, W4: H4}


class Multimode(MyStrEnum):
    PBP = auto()
    TRIPLE = auto()
    QUAD = auto()

    def to_mode(self) -> Mode:
        match self:
            case Multimode.PBP:
                return Mode.PBP
            case Multimode.TRIPLE:
                return Mode.TRIPLE
            case Multimode.QUAD:
                return Mode.QUAD


PBP = Multimode.PBP
TRIPLE = Multimode.TRIPLE
QUAD = Multimode.QUAD


@dataclass(slots=True)
class ArrowPress:
    at: datetime
    arrow: Arrow
    points_to: Window
    selected_window: Window


@dataclass(slots=True)
class RemotePress:
    at: datetime
    selected_window: Window


@dataclass_json
@dataclass(slots=True)
class Multiviewer(Jsonable):
    power: Power = Power.ON
    multimode: Multimode = Multimode.QUAD
    submode: Submode = W1_PROMINENT
    is_fullscreen: bool = False
    fullscreen_shows_pip: bool = False
    pip_location: PipLocation = PipLocation.NE
    selected_window: Window = W1
    full_window: Window = W1
    pip_window: Window = W2
    selected_window_border_is_on: bool = True
    control_apple_tv: bool = False
    most_recent_command_at: datetime = field(
        default=datetime.now(), metadata=json_field.omit
    )
    last_arrow_press: ArrowPress | None = field(default=None, metadata=json_field.omit)
    last_remote_press: RemotePress | None = field(
        default=None, metadata=json_field.omit
    )
    jtech_manager: Jtech_manager = Jtech_manager.field()
    # We maintain a volume delta for each TV, which we use to automatically adjust
    # volume_delta when unmuting or when the selected TV changes.
    volume_delta_by_tv: dict[TV, int] = field(default_factory=volume_deltas_zero)
    volume: Volume = Volume.field()
    atvs: ATVs = ATVs.field()
    window_input: dict[Window, Hdmi] = field(
        default_factory=initial_window_input, metadata=json_dict(Window, Hdmi)
    )
    task: Task = Task.field()


def num_windows(mv: Multiviewer) -> int:
    return mv.multimode.to_mode().num_windows()


def last_window(mv: Multiviewer) -> Window:
    return Window.of_int(num_windows(mv))


def prev_window(mv: Multiviewer, w: Window) -> Window:
    n = num_windows(mv)
    return Window.of_int(1 + ((w.to_int() + n - 2) % n))


def next_window(mv: Multiviewer, w: Window) -> Window:
    return Window.of_int(w.to_int() % num_windows(mv) + 1)


def window_input(mv: Multiviewer, w: Window) -> Hdmi:
    return mv.window_input[w]


def window_tv(mv: Multiviewer, w: Window) -> TV:
    return hdmi2tv(window_input(mv, w))


def selected_tv(mv: Multiviewer) -> TV:
    return window_tv(mv, mv.selected_window)


def visible(mv: Multiviewer) -> list[Window]:
    return mv.multimode.to_mode().windows()


def is_visible(mv: Multiviewer, w: Window) -> bool:
    return w in visible(mv)


def validate(mv: Multiviewer) -> None:
    assert_equal(set(mv.window_input.keys()), set(Mode.QUAD.windows()))
    assert_equal(len(set(mv.window_input.values())), len(mv.window_input))
    v = visible(mv)
    if not mv.is_fullscreen:
        assert_(mv.selected_window in v)


async def shutdown(mv: Multiviewer) -> None:
    await mv.atvs.shutdown()


def reset(mv: Multiviewer) -> None:
    mv.multimode = QUAD
    mv.submode = W1_PROMINENT
    mv.is_fullscreen = False
    mv.fullscreen_shows_pip = False
    mv.full_window = W1
    mv.pip_window = W2
    mv.pip_location = PipLocation.NE
    mv.selected_window = W1
    mv.selected_window_border_is_on = True
    mv.control_apple_tv = False
    mv.last_arrow_press = None
    mv.last_remote_press = None
    mv.volume_delta_by_tv = volume_deltas_zero()
    mv.volume.reset()
    mv.window_input = initial_window_input()


async def update_screen_forever(mv: Multiviewer):
    if False:
        while True:
            await aio.sleep(1)
            update_screen(mv)


async def initialize(mv: Multiviewer):
    mv.task = Task.create(type(mv).__name__, update_screen_forever(mv))
    set_power(mv, mv.power)


async def create() -> Multiviewer:
    mv = Multiviewer()
    await initialize(mv)
    validate(mv)
    return mv


async def load(path: Path) -> Multiviewer:
    if False:
        debug_print()
    try:
        mv = Multiviewer.from_json(path.read_text())
        await initialize(mv)
        validate(mv)
        return mv
    except Exception:
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
    # user.  This causes the initial update_screen to set the desired volume_delta
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
    if mv.is_fullscreen:
        return True
    match mv.multimode:
        case Multimode.PBP | Multimode.TRIPLE | Multimode.QUAD:
            return mv.submode == W1_PROMINENT
    assert False


def swap_window_inputs(mv: Multiviewer, w1: Window, w2: Window) -> None:
    if False:
        debug_print(f"{w1} <-> {w2}")
    window_input = mv.window_input
    h1 = window_input[w1]
    h2 = window_input[w2]
    window_input[w1] = h2
    window_input[w2] = h1


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
    PBP: {W1: {E: W2}, W2: {W: W1}},
    TRIPLE: {
        W1: {N: W2, S: W3},
        W2: {W: W1, S: W3},
        W3: {
            N: W2,
            W: W1,
        },
    },
    (QUAD, WINDOWS_SAME): {
        W1: {E: W2, W: W4, S: W3},
        W2: {E: W3, W: W1, S: W4},
        W3: {N: W1, E: W4, W: W2},
        W4: {
            N: W2,
            E: W1,
            W: W3,
        },
    },
    (QUAD, W1_PROMINENT): {
        W1: {N: W2, E: W3, S: W4},
        W2: {W: W1, S: W3},
        W3: {N: W2, W: W1, S: W4},
        W4: {N: W3, W: W1},
    },
}


def arrow_points_to(mv: Multiviewer, arrow: Arrow) -> Window | None:
    if False:
        debug_print(arrow)
    match mv.multimode:
        case Multimode.PBP | Multimode.TRIPLE:
            key = mv.multimode
        case Multimode.QUAD:
            key = (mv.multimode, mv.submode)
    return _arrow_points_to[key][mv.selected_window].get(arrow)


def add_window(mv: Multiviewer) -> None:
    if mv.is_fullscreen:
        mv.multimode = PBP
        mv.is_fullscreen = False
        swap_window_inputs(mv, W1, mv.full_window)
        mv.selected_window = W1
        if mv.fullscreen_shows_pip:
            if mv.pip_window == W1:
                swap_window_inputs(mv, W2, mv.full_window)
            else:
                swap_window_inputs(mv, W2, mv.pip_window)
    else:
        match mv.multimode:
            case Multimode.PBP:
                mv.multimode = TRIPLE
            case Multimode.TRIPLE:
                mv.multimode = QUAD


def demote_window(mv: Multiviewer, w1: Window) -> None:
    if not mv.is_fullscreen:
        last = last_window(mv)
        while w1 != last:
            w2 = next_window(mv, w1)
            swap_window_inputs(mv, w1, w2)
            w1 = w2


def remove_window(mv: Multiviewer) -> None:
    if not mv.is_fullscreen:
        match mv.multimode:
            case Multimode.PBP:
                mv.is_fullscreen = True
                mv.full_window = mv.selected_window
                mv.fullscreen_shows_pip = False
            case Multimode.TRIPLE:
                mv.multimode = PBP
            case Multimode.QUAD:
                mv.multimode = TRIPLE
        if not is_visible(mv, mv.selected_window):
            mv.selected_window_border_is_on = True
            mv.selected_window = W1


def maybe_entered_pip(mv: Multiviewer) -> None:
    if mv.fullscreen_shows_pip:
        mv.pip_window = next_window(mv, mv.full_window)


def toggle_fullscreen(mv: Multiviewer) -> None:
    mv.is_fullscreen = not mv.is_fullscreen
    if mv.is_fullscreen:
        mv.full_window = mv.selected_window
        maybe_entered_pip(mv)
    else:
        mv.selected_window_border_is_on = True
        if not is_visible(mv, mv.selected_window):
            swap_window_inputs(mv, W1, mv.selected_window)
            mv.selected_window = W1


def toggle_submode(mv: Multiviewer) -> None:
    if mv.is_fullscreen:
        mv.fullscreen_shows_pip = not mv.fullscreen_shows_pip
        maybe_entered_pip(mv)
    else:
        mv.submode = mv.submode.flip()


def from_pip_arrow_points_to(mv: Multiviewer, arrow: Arrow) -> PipLocation | None:
    assert mv.is_fullscreen and mv.fullscreen_shows_pip
    match (mv.pip_location, arrow):
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


def pressed_arrow(mv: Multiviewer, arrow: Arrow) -> None:
    if False:
        debug_print(arrow)
    if mv.is_fullscreen:
        if mv.fullscreen_shows_pip:
            if mv.pip_window == mv.selected_window:
                # Move the PIP on screen
                pip_location = from_pip_arrow_points_to(mv, arrow)
                if pip_location is not None:
                    mv.pip_location = pip_location
            else:
                # Rotate PIP (E, W) or select PIP (N, S)
                match (arrow, mv.pip_location):
                    case (Arrow.E, _):
                        w = next_window(mv, mv.pip_window)
                        if w == mv.full_window:
                            w = next_window(mv, w)
                        mv.pip_window = w
                    case (Arrow.W, _):
                        w = prev_window(mv, mv.pip_window)
                        if w == mv.full_window:
                            w = prev_window(mv, w)
                        mv.pip_window = w
                    case (Arrow.N, PipLocation.NE | PipLocation.NW) | (
                        Arrow.S,
                        PipLocation.SE | PipLocation.SW,
                    ):
                        mv.selected_window = mv.pip_window
                    case _:
                        pass
        else:  # FULL
            match arrow:
                case Arrow.N | Arrow.S:
                    pass
                case Arrow.E:
                    mv.full_window = next_window(mv, mv.selected_window)
                    mv.selected_window = mv.full_window
                case Arrow.W:
                    mv.full_window = prev_window(mv, mv.selected_window)
                    mv.selected_window = mv.full_window

    else:
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
            log_double_tap_duration(at - last_press.at)
            mv.last_arrow_press = None
            swap_window_inputs(mv, last_press.selected_window, last_press.points_to)
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


def toggle_mute(mv: Multiviewer) -> None:
    mv.volume.toggle_mute()


def adjust_volume(mv: Multiviewer, by: int) -> None:
    mv.volume.unmute()
    mv.volume_delta_by_tv[selected_tv(mv)] += by


def describe_volume(mv: Multiviewer) -> str:
    return mv.volume.describe_volume()


async def describe_screen(mv: Multiviewer) -> str:
    screen = await mv.jtech_manager.current_screen()
    return screen.one_line_description()


async def info(mv: Multiviewer) -> str:
    screen = await describe_screen(mv)
    volume = describe_volume(mv)
    return f"{screen} {volume}"


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
        case "Add_window":
            add_window(mv)
        case "Back":
            if mv.control_apple_tv:
                atv.menu()
            elif mv.is_fullscreen:
                if mv.fullscreen_shows_pip and mv.selected_window == mv.pip_window:
                    mv.selected_window = mv.full_window
                else:
                    toggle_fullscreen(mv)
        case "Demote_window":
            demote_window(mv, mv.selected_window)
        case "Down" | "S":
            if mv.control_apple_tv:
                atv.down()
            else:
                pressed_arrow(mv, S)
        case "Home":
            if mv.control_apple_tv:
                atv.home()
            else:
                toggle_submode(mv)
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
                mv.selected_window_border_is_on = not mv.selected_window_border_is_on
        case "Power_on":
            mv.selected_window_border_is_on = True
            await power_on(mv)
        case "Power":
            await toggle_power(mv)
        case "Remote":
            return remote(mv, tv)
        case "Remove_window":
            remove_window(mv)
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
            elif mv.is_fullscreen:
                if mv.fullscreen_shows_pip:
                    swap_full_and_pip_windows(mv)
                else:
                    pass
            else:
                toggle_fullscreen(mv)
        case "Sleep":
            atv.sleep()
        case "Test":
            pass
        case "Toggle_fullscreen":
            toggle_fullscreen(mv)
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


def render(mv: Multiviewer) -> Screen:
    if False:
        debug_print()

    def window(
        mode: Mode, screen_window: Window, mv_window: Window | None = None
    ) -> Window_contents:
        if mv_window is None:
            mv_window = screen_window
        if not mode.window_has_border(screen_window):
            border = None
        elif mv.control_apple_tv and mv_window == mv.selected_window:
            border = Color.RED
        elif mv.selected_window_border_is_on and mv_window == mv.selected_window:
            border = Color.GREEN
        else:
            border = Color.GRAY
        return Window_contents(hdmi=mv.window_input[mv_window], border=border)

    if mv.is_fullscreen:
        if not mv.fullscreen_shows_pip:
            layout = Full(w1=window(Mode.FULL, W1, mv.full_window))
        else:
            layout = Pip(
                pip_location=mv.pip_location,
                w1=window(Mode.PIP, W1, mv.full_window),
                w2=window(Mode.PIP, W2, mv.pip_window),
            )
    else:
        mode = mv.multimode.to_mode()
        submode = mv.submode
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
    return Screen(layout=layout, audio_from=mv.window_input[mv.selected_window])


def update_screen(mv: Multiviewer) -> None:
    mv.jtech_manager.set_screen(render(mv))
    mv.volume.set_volume_delta(mv.volume_delta_by_tv[selected_tv(mv)])


async def do_command_and_update_screen(mv: Multiviewer, args: list[str]) -> JSON:
    if False:
        debug_print(args, mv)
    result = await do_command(mv, args)
    validate(mv)
    update_screen(mv)
    return result


async def synced(mv: Multiviewer) -> None:
    if False:
        debug_print(mv)
    await mv.atvs.synced()
    await mv.jtech_manager.synced()
    await mv.volume.synced()
