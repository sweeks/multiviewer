from __future__ import annotations

# Standard library
from datetime import datetime
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
    DOUBLE_TAP_MAX_DURATION,
    Arrow,
    E,
    FULL,
    FULLSCREEN,
    N,
    MULTIVIEW,
    PIP,
    APPLE_TV,
    MULTIVIEWER,
    S,
    W,
    W1,
    W1_PROMINENT,
    W2,
    W3,
    W4,
    WINDOWS_SAME,
    FullscreenMode,
    LayoutMode,
    MvScreen,
    RemoteMode,
    max_num_windows,
    min_num_windows,
    RealClock,
    VirtualClock,
)
from .volume import Volume

H1 = Hdmi.H1
H2 = Hdmi.H2
H3 = Hdmi.H3
H4 = Hdmi.H4


def volume_deltas_zero():
    return dict.fromkeys(TV.all(), 0)


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
    screen: MvScreen = field(default_factory=MvScreen)
    volume_delta_by_tv: dict[TV, int] = field(default_factory=volume_deltas_zero)
    volume: Volume = Volume.field()
    last_remote_press: RemotePress | None = field(default=None, metadata=json_field.omit)
    jtech_manager: JtechManager = JtechManager.field()
    atvs: ATVs = ATVs.field()

    @property
    def window_tv(self):
        return self.screen.window_tv

    @window_tv.setter
    def window_tv(self, v):
        self.screen.window_tv = v

    @property
    def layout_mode(self):
        return self.screen.layout_mode

    @layout_mode.setter
    def layout_mode(self, v):
        self.screen.layout_mode = v

    @property
    def num_active_windows(self):
        return self.screen.num_active_windows

    @num_active_windows.setter
    def num_active_windows(self, v):
        self.screen.num_active_windows = v

    @property
    def multiview_submode(self):
        return self.screen.multiview_submode

    @multiview_submode.setter
    def multiview_submode(self, v):
        self.screen.multiview_submode = v

    @property
    def fullscreen_mode(self):
        return self.screen.fullscreen_mode

    @fullscreen_mode.setter
    def fullscreen_mode(self, v):
        self.screen.fullscreen_mode = v

    @property
    def full_window(self):
        return self.screen.full_window

    @full_window.setter
    def full_window(self, v):
        self.screen.full_window = v

    @property
    def pip_window(self):
        return self.screen.pip_window

    @pip_window.setter
    def pip_window(self, v):
        self.screen.pip_window = v

    @property
    def pip_location_by_tv(self):
        return self.screen.pip_location_by_tv

    @pip_location_by_tv.setter
    def pip_location_by_tv(self, v):
        self.screen.pip_location_by_tv = v

    @property
    def selected_window(self):
        return self.screen.selected_window

    @selected_window.setter
    def selected_window(self, v):
        self.screen.selected_window = v

    @property
    def selected_window_has_distinct_border(self):
        return self.screen.selected_window_has_distinct_border

    @selected_window_has_distinct_border.setter
    def selected_window_has_distinct_border(self, v):
        self.screen.selected_window_has_distinct_border = v

    @property
    def remote_mode(self):
        return self.screen.remote_mode

    @remote_mode.setter
    def remote_mode(self, v):
        self.screen.remote_mode = v


def last_active_window(mv: Multiviewer) -> Window:
    return Window.of_int(mv.num_active_windows)


def prev_active_window(mv: Multiviewer, w: Window) -> Window:
    n = mv.num_active_windows
    return Window.of_int(1 + ((w.to_int() + n - 2) % n))


def next_active_window(mv: Multiviewer, w: Window) -> Window:
    return Window.of_int(w.to_int() % mv.num_active_windows + 1)


def window_tv(mv: Multiviewer, w: Window) -> TV:
    return mv.screen.window_tv[w]


def window_input(mv: Multiviewer, w: Window) -> Hdmi:
    return mv.screen.window_input(w)


def pip_location(mv: Multiviewer) -> PipLocation:
    return mv.screen.pip_location()


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
    clock = mv.screen.clock
    mv.screen = MvScreen()
    mv.screen.clock = clock
    mv.last_remote_press = None
    mv.volume_delta_by_tv = volume_deltas_zero()
    mv.volume.reset()


def set_should_send_commands_to_device(mv: Multiviewer, b: bool) -> None:
    mv.jtech_manager.set_should_send_commands_to_device(b)
    mv.atvs.set_should_send_commands_to_device(b)
    mv.volume.set_should_send_commands_to_device(b)


def use_virtual_clock(mv: Multiviewer) -> None:
    mv.screen.clock = VirtualClock()


def advance_clock(mv: Multiviewer, seconds: float) -> None:
    mv.screen.clock.advance(seconds)


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


def remote(mv: Multiviewer, tv: TV) -> JSON:
    this_press = RemotePress(
        at=mv.screen.clock.now(), selected_window=mv.selected_window
    )
    last_press = mv.last_remote_press
    if (
        last_press is not None
        and last_press.selected_window == this_press.selected_window
        and this_press.at - last_press.at <= DOUBLE_TAP_MAX_DURATION
    ):
        # Double tap.  The shortcut will open the Remote app on TV <i>
        mv.last_remote_press = None
        # Flip again to cancel the single-tap mode change.
        mv.screen.toggle_remote_mode()
        return tv.to_int()
    else:
        # Single tap
        mv.last_remote_press = this_press
        mv.screen.toggle_remote_mode()
        return {}


async def do_command(mv: Multiviewer, args: list[str]) -> JSON:
    if False:
        debug_print(args)
    command = args[0]
    if mv.power == Power.OFF and command not in ["Power", "Power_on"]:
        return {}
    tv = selected_tv(mv)
    atv = mv.atvs.atv(tv)
    screen_state = mv.screen
    match command:
        case "Activate_tv":
            screen_state.activate_tv()
        case "Back":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.menu()
                case RemoteMode.MULTIVIEWER:
                    screen_state.pressed_back()
        case "Down" | "S":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.down()
                case RemoteMode.MULTIVIEWER:
                    screen_state.pressed_arrow(S)
        case "Home":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.home()
                case RemoteMode.MULTIVIEWER:
                    screen_state.toggle_submode()
        case "Info":
            return await info(mv)
        case "Launch":
            atv.launch(args[1])
        case "Left" | "W":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.left()
                case RemoteMode.MULTIVIEWER:
                    screen_state.pressed_arrow(W)
        case "Mute":
            toggle_mute(mv)
        case "Play_pause":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.play_pause()
                case RemoteMode.MULTIVIEWER:
                    screen_state.pressed_play_pause()
        case "Power_on":
            if mv.power == Power.OFF:
                mv.selected_window_has_distinct_border = True
                await power_on(mv)
        case "Power":
            await toggle_power(mv)
        case "Remote":
            return remote(mv, tv)
        case "Deactivate_tv":
            screen_state.deactivate_tv()
        case "Reset":
            reset(mv)
        case "Right" | "E":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.right()
                case RemoteMode.MULTIVIEWER:
                    screen_state.pressed_arrow(E)
        case "Screensaver":
            atv.screensaver()
        case "Select":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.select()
                case RemoteMode.MULTIVIEWER:
                    screen_state.pressed_select()
        case "Sleep":
            atv.sleep()
        case "Test":
            pass
        case "Up" | "N":
            match mv.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.up()
                case RemoteMode.MULTIVIEWER:
                    screen_state.pressed_arrow(N)
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
    return mv.screen.render()


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
