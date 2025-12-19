from __future__ import annotations

# Standard library
from datetime import datetime, timedelta
from pathlib import Path

# Third-party
from dataclasses_json import dataclass_json

# Local package
from . import json_field
from .atv import ATVs
from .tv import TV
from .base import JSON, Jsonable, dataclass, debug_print, fail, log, field
from .jtech import Power
from .jtech_manager import JtechManager
from .jtech_output import JtechOutput
from .mv_screen import Arrow, Button, MvScreen, RemoteMode
from .volume import Volume


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


@dataclass(slots=True)
class ArrowPressInfo:
    arrow: Arrow
    at: datetime


@dataclass(slots=True)
class RemotePressInfo:
    at: datetime


DOUBLE_TAP_MAX_DURATION = timedelta(seconds=0.3)

@dataclass_json
@dataclass(slots=True)
class Multiviewer(Jsonable):
    power: Power = Power.ON
    screen: MvScreen = MvScreen.field()
    atvs: ATVs = ATVs.field()
    jtech_manager: JtechManager = JtechManager.field()
    volume: Volume = Volume.field()
    clock: RealClock | VirtualClock = field(
        default_factory=RealClock, metadata=json_field.omit
    )
    last_arrow_press: ArrowPressInfo | None = field(default=None, metadata=json_field.omit)
    last_remote_press: RemotePressInfo | None = field(
        default=None, metadata=json_field.omit
    )


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
    mv.clock = VirtualClock()


def advance_clock(mv: Multiviewer, seconds: float) -> None:
    mv.clock.advance(seconds)


def now(mv: Multiviewer) -> datetime:
    return mv.clock.now()


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


async def power_off(mv: Multiviewer) -> None:
    if False:
        debug_print(mv)
    log("turning off power")
    mv.power = Power.OFF
    mv.jtech_manager.power_off()
    await mv.atvs.power_off()
    log("power is off")


async def power_on(mv: Multiviewer) -> None:
    if False:
        debug_print(mv)
    log("turning on power")
    mv.power = Power.ON
    mv.jtech_manager.power_on()
    await mv.atvs.power_on()
    mv.screen.power_on()
    mv.volume.power_on()
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
            screen.pressed(Button.ACTIVATE_TV, double_tap=False)
        case "Back":
            match screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.menu()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed(Button.BACK, double_tap=False)
        case "Deactivate_tv":
            screen.pressed(Button.DEACTIVATE_TV, double_tap=False)
        case "Down" | "S":
            match screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.down()
                case RemoteMode.MULTIVIEWER:
                    at = now(mv)
                    double_tap = (
                        mv.last_arrow_press is not None
                        and mv.last_arrow_press.arrow == Arrow.S
                        and at - mv.last_arrow_press.at <= DOUBLE_TAP_MAX_DURATION
                    )
                    screen.pressed(Button.ARROW_S, double_tap=double_tap)
                    mv.last_arrow_press = None if double_tap else ArrowPressInfo(Arrow.S, at)
        case "Home":
            match screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.home()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed(Button.TOGGLE_SUBMODE, double_tap=False)
        case "Info":
            return await info(mv)
        case "Launch":
            atv.launch(args[1])
        case "Left" | "W":
            match screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.left()
                case RemoteMode.MULTIVIEWER:
                    at = now(mv)
                    double_tap = (
                        mv.last_arrow_press is not None
                        and mv.last_arrow_press.arrow == Arrow.W
                        and at - mv.last_arrow_press.at <= DOUBLE_TAP_MAX_DURATION
                    )
                    screen.pressed(Button.ARROW_W, double_tap=double_tap)
                    mv.last_arrow_press = None if double_tap else ArrowPressInfo(Arrow.W, at)
        case "Mute":
            mv.volume.toggle_mute()
        case "Play_pause":
            match screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.play_pause()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed(Button.PLAY_PAUSE, double_tap=False)
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
            at = now(mv)
            double_tap = (
                mv.last_remote_press is not None
                and at - mv.last_remote_press.at <= DOUBLE_TAP_MAX_DURATION
            )
            screen.pressed(Button.REMOTE, double_tap=double_tap)
            mv.last_remote_press = None if double_tap else RemotePressInfo(at)
            return tv.to_int()
        case "Reset":
            reset(mv)
        case "Right" | "E":
            match screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.right()
                case RemoteMode.MULTIVIEWER:
                    at = now(mv)
                    double_tap = (
                        mv.last_arrow_press is not None
                        and mv.last_arrow_press.arrow == Arrow.E
                        and at - mv.last_arrow_press.at <= DOUBLE_TAP_MAX_DURATION
                    )
                    screen.pressed(Button.ARROW_E, double_tap=double_tap)
                    mv.last_arrow_press = None if double_tap else ArrowPressInfo(Arrow.E, at)
        case "Screensaver":
            atv.screensaver()
        case "Select":
            match screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.select()
                case RemoteMode.MULTIVIEWER:
                    screen.pressed(Button.SELECT, double_tap=False)
        case "Test":
            pass
        case "Up" | "N":
            match screen.remote_mode:
                case RemoteMode.APPLE_TV:
                    atv.up()
                case RemoteMode.MULTIVIEWER:
                    at = now(mv)
                    double_tap = (
                        mv.last_arrow_press is not None
                        and mv.last_arrow_press.arrow == Arrow.N
                        and at - mv.last_arrow_press.at <= DOUBLE_TAP_MAX_DURATION
                    )
                    screen.pressed(Button.ARROW_N, double_tap=double_tap)
                    mv.last_arrow_press = None if double_tap else ArrowPressInfo(Arrow.N, at)
        case "Volume_down":
            adjust_volume(mv, -1)
        case "Volume_up":
            adjust_volume(mv, 1)
        case _:
            fail("invalid command", command)
    return {}


def update_devices(mv: Multiviewer):
    mv.jtech_manager.set_output(mv.screen.render())
    mv.volume.set_for_tv(selected_tv(mv))


async def do_command_and_update_devices(mv: Multiviewer, args: list[str]) -> JSON:
    if False:
        debug_print(args, mv)
    result = await do_command(mv, args)
    validate(mv)
    update_devices(mv)
    return result


async def synced(mv: Multiviewer) -> None:
    if False:
        debug_print(mv)
    await mv.atvs.synced()
    await mv.jtech_manager.synced()
    await mv.volume.synced()
