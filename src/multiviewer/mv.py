from __future__ import annotations

# Standard library
from pathlib import Path

# Third-party
from dataclasses_json import dataclass_json

# Local package
from .atv import ATVs
from .tv import TV
from .base import JSON, Jsonable, dataclass, debug_print, fail, log
from .jtech import Power
from .jtech_manager import JtechManager
from .jtech_output import JtechOutput
from .mv_screen import Arrow, MvScreen, RemoteMode
from .volume import Volume


@dataclass_json
@dataclass(slots=True)
class Multiviewer(Jsonable):
    power: Power = Power.ON
    screen: MvScreen = MvScreen.field()
    atvs: ATVs = ATVs.field()
    jtech_manager: JtechManager = JtechManager.field()
    volume: Volume = Volume.field()


def selected_tv(mv: Multiviewer) -> TV:
    return mv.screen.selected_tv()


def validate(mv: Multiviewer) -> None:
    mv.screen.validate()


async def shutdown(mv: Multiviewer) -> None:
    await mv.atvs.shutdown()


def reset(mv: Multiviewer) -> None:
    mv.screen.reset()
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
    mv.screen.power_on()
    mv.volume.power_on()
    # Waking TV1 turns on the LG via CEC.
    for tv in TV.all():
        mv.atvs.atv(tv).wake()
    await mv.atvs.synced()
    log("power is on")


def describe_volume(mv: Multiviewer) -> str:
    return mv.volume.describe_volume()


async def describe_jtech_output(mv: Multiviewer) -> str:
    output = await mv.jtech_manager.current_output()
    return output.one_line_description()


def adjust_volume(mv: Multiviewer, by: int) -> None:
    mv.volume.adjust_volume(mv.screen.selected_tv(), by)


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
    tv = selected_tv(mv)
    atv = mv.atvs.atv(tv)
    match command:
        case "Activate_tv":
            screen.activate_tv()
        case "Back":
            match screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.menu()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed_back()
        case "Deactivate_tv":
            screen.deactivate_tv()
        case "Down" | "S":
            match screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.down()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed_arrow(Arrow.S)
        case "Home":
            match screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.home()
                case RemoteMode.MULTIVIEWER:
                    screen.toggle_submode()
        case "Info":
            return await info(mv)
        case "Launch":
            atv.launch(args[1])
        case "Left" | "W":
            match screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.left()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed_arrow(Arrow.W)
        case "Mute":
            mv.volume.toggle_mute()
        case "Play_pause":
            match screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.play_pause()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed_play_pause()
        case "Power_on":
            if mv.power == Power.OFF:
                await power_on(mv)
        case "Power":
            match mv.power:
                case Power.OFF:
                    await power_on(mv)
                case Power.ON:
                    await power_off(mv)
        case "Remote":
            screen.remote(tv)
            return tv.to_int()
        case "Reset":
            reset(mv)
        case "Right" | "E":
            match screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.right()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed_arrow(Arrow.E)
        case "Screensaver":
            atv.screensaver()
        case "Select":
            match screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.select()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed_select()
        case "Sleep":
            atv.sleep()
        case "Test":
            pass
        case "Up" | "N":
            match screen.remote_mode:
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


async def do_command_and_update_devices(mv: Multiviewer, args: list[str]) -> JSON:
    if False:
        debug_print(args, mv)
    result = await do_command(mv, args)
    validate(mv)
    mv.jtech_manager.set_output(mv.screen.render())
    mv.volume.set_for_tv(selected_tv(mv))
    return result


async def synced(mv: Multiviewer) -> None:
    if False:
        debug_print(mv)
    await mv.atvs.synced()
    await mv.jtech_manager.synced()
    await mv.volume.synced()
