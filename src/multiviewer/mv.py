from __future__ import annotations

# Standard library
from pathlib import Path

# Third-party
from dataclasses_json import dataclass_json

# Local package
from .atv import ATVs
from .tv import TV
from .base import JSON, Jsonable, dataclass, debug_print, fail, field, log
from .jtech import Power
from .jtech_manager import JtechManager
from .jtech_output import JtechOutput
from .mv_screen import Arrow, MULTIVIEWER, MvScreen, RemoteMode
from .volume import Volume


def volume_deltas_zero():
    return dict.fromkeys(TV.all(), 0)


@dataclass_json
@dataclass(slots=True)
class Multiviewer(Jsonable):
    # power is the state of the virtual multiviewer.  During initialization, we ensure
    # that the physical devices match it.
    power: Power = Power.ON
    screen: MvScreen = field(default_factory=MvScreen)
    volume_delta_by_tv: dict[TV, int] = field(default_factory=volume_deltas_zero)
    volume: Volume = Volume.field()
    jtech_manager: JtechManager = JtechManager.field()
    atvs: ATVs = ATVs.field()


def selected_tv(mv: Multiviewer) -> TV:
    return mv.screen.selected_tv()


def validate(mv: Multiviewer) -> None:
    mv.screen.validate()


async def shutdown(mv: Multiviewer) -> None:
    await mv.atvs.shutdown()


def reset(mv: Multiviewer) -> None:
    mv.screen = mv.screen.reset()
    mv.volume_delta_by_tv = volume_deltas_zero()
    mv.volume.reset()


def set_should_send_commands_to_device(mv: Multiviewer, b: bool) -> None:
    mv.jtech_manager.set_should_send_commands_to_device(b)
    mv.atvs.set_should_send_commands_to_device(b)
    mv.volume.set_should_send_commands_to_device(b)


def use_virtual_clock(mv: Multiviewer) -> None:
    mv.screen.use_virtual_clock()


def advance_clock(mv: Multiviewer, seconds: float) -> None:
    mv.screen.advance_clock(seconds)


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
    mv.screen.remote_mode = MULTIVIEWER
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
    mv.volume_delta_by_tv[mv.screen.selected_tv()] += by


def describe_volume(mv: Multiviewer) -> str:
    return mv.volume.describe_volume()


async def describe_jtech_output(mv: Multiviewer) -> str:
    output = await mv.jtech_manager.current_output()
    return output.one_line_description()


async def info(mv: Multiviewer) -> str:
    output = await describe_jtech_output(mv)
    volume = describe_volume(mv)
    return f"{output} {volume}"


async def do_command(mv: Multiviewer, args: list[str]) -> JSON:
    if False:
        debug_print(args)
    command = args[0]
    if mv.power == Power.OFF and command not in ["Power", "Power_on"]:
        return {}
    screen = mv.screen
    tv = screen.selected_tv()
    atv = mv.atvs.atv(tv)
    match command:
        case "Activate_tv":
            screen.activate_tv()
        case "Back":
            match mv.screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.menu()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed_back()
        case "Down" | "S":
            match mv.screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.down()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed_arrow(Arrow.S)
        case "Home":
            match mv.screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.home()
                case RemoteMode.MULTIVIEWER:
                    screen.toggle_submode()
        case "Info":
            return await info(mv)
        case "Launch":
            atv.launch(args[1])
        case "Left" | "W":
            match mv.screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.left()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed_arrow(Arrow.W)
        case "Mute":
            toggle_mute(mv)
        case "Play_pause":
            match mv.screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.play_pause()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed_play_pause()
        case "Power_on":
            if mv.power == Power.OFF:
                mv.screen.selected_window_has_distinct_border = True
                await power_on(mv)
        case "Power":
            await toggle_power(mv)
        case "Remote":
            return mv.screen.remote(tv) or tv.to_int()
        case "Deactivate_tv":
            screen.deactivate_tv()
        case "Reset":
            reset(mv)
        case "Right" | "E":
            match mv.screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.right()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed_arrow(Arrow.E)
        case "Screensaver":
            atv.screensaver()
        case "Select":
            match mv.screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.select()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed_select()
        case "Sleep":
            atv.sleep()
        case "Test":
            pass
        case "Up" | "N":
            match mv.screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.up()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed_arrow(Arrow.N)
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
