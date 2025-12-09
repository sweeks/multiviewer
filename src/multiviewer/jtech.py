from __future__ import annotations

# Standard library
import dataclasses
import re
from unittest import result

# Local package
from . import aio
from .base import *
from .ip2sl import Connection
from .json_field import json_dict


class Power(MyStrEnum):
    OFF = auto()
    ON = auto()

    def flip(self):
        match self:
            case Power.ON:
                return OFF
            case Power.OFF:
                return ON


OFF, ON = Power.OFF, Power.ON

attach_int(Power, {OFF: 0, ON: 1})


class Hdmi(MyStrEnum):
    H1 = auto()
    H2 = auto()
    H3 = auto()
    H4 = auto()


H1 = Hdmi.H1
H2 = Hdmi.H2
H3 = Hdmi.H3
H4 = Hdmi.H4

attach_int(Hdmi, {H1: 1, H2: 2, H3: 3, H4: 4})


class Window(MyStrEnum):
    W1 = auto()
    W2 = auto()
    W3 = auto()
    W4 = auto()


W1 = Window.W1
W2 = Window.W2
W3 = Window.W3
W4 = Window.W4


def window_dict(f):
    return {w: f(w) for w in Window.all()}


attach_int(Window, {W1: 1, W2: 2, W3: 3, W4: 4})


class Mode(MyStrEnum):
    FULL = auto()
    PIP = auto()
    PBP = auto()
    TRIPLE = auto()
    QUAD = auto()

    def has_submode(self) -> bool:
        match self:
            case Mode.FULL | Mode.PIP:
                return False
            case Mode.PBP | Mode.TRIPLE | Mode.QUAD:
                return True

    def num_windows(self) -> int:
        match self:
            case Mode.FULL:
                return 1
            case Mode.PIP | Mode.PBP:
                return 2
            case Mode.TRIPLE:
                return 3
            case Mode.QUAD:
                return 4

    def windows(self) -> list[Window]:
        return [Window.of_int(i) for i in range(1, 1 + self.num_windows())]

    def name_for_submode_command(self) -> str:
        match self:
            case Mode.PBP:
                return "PBP"
            case Mode.TRIPLE:
                return "triple"
            case Mode.QUAD:
                return "quad"
            case _:
                fail(f"mode {self} has no submode")

    def window_has_border(self, w: Window) -> bool:
        match self:
            case Mode.FULL:
                return False
            case Mode.PIP:
                return w == W2
            case Mode.PBP | Mode.TRIPLE | Mode.QUAD:
                return True


FULL, PIP, PBP, TRIPLE, QUAD = Mode.FULL, Mode.PIP, Mode.PBP, Mode.TRIPLE, Mode.QUAD

attach_int(Mode, {FULL: 1, PIP: 2, PBP: 3, TRIPLE: 4, QUAD: 5})

multiview_name_by_mode = {
    FULL: "single screen",
    PIP: "PIP",
    PBP: "PBP",
    TRIPLE: "triple screen",
    QUAD: "quad screen",
}


def invert_dict(d: dict) -> dict:
    return {v: k for k, v in d.items()}


multiview_mode_by_name = invert_dict(multiview_name_by_mode)


class Submode(MyStrEnum):
    WINDOWS_SAME = auto()
    W1_PROMINENT = auto()

    def flip(self: Submode) -> Submode:
        match self:
            case Submode.WINDOWS_SAME:
                return W1_PROMINENT
            case Submode.W1_PROMINENT:
                return WINDOWS_SAME


WINDOWS_SAME = Submode.WINDOWS_SAME
W1_PROMINENT = Submode.W1_PROMINENT

attach_int(Submode, {WINDOWS_SAME: 1, W1_PROMINENT: 2})


class PipLocation(MyStrEnum):
    NW = auto()
    NE = auto()
    SW = auto()
    SE = auto()


class Color(MyStrEnum):
    BLACK = auto()
    RED = auto()
    GREEN = auto()
    BLUE = auto()
    YELLOW = auto()
    MAGENTA = auto()
    CYAN = auto()
    WHITE = auto()
    GRAY = auto()


BLACK = Color.BLACK
RED = Color.RED
GREEN = Color.GREEN
BLUE = Color.BLUE
YELLOW = Color.YELLOW
MAGENTA = Color.MAGENTA
CYAN = Color.CYAN
WHITE = Color.WHITE
GRAY = Color.GRAY

attach_int(
    Color,
    {
        BLACK: 1,
        RED: 2,
        GREEN: 3,
        BLUE: 4,
        YELLOW: 5,
        MAGENTA: 6,
        CYAN: 7,
        WHITE: 8,
        GRAY: 9,
    },
)


class Mute(MyStrEnum):
    UNMUTED = auto()
    MUTED = auto()


MUTED = Mute.MUTED
UNMUTED = Mute.UNMUTED

attach_int(Mute, {UNMUTED: 0, MUTED: 1})


class Border(MyStrEnum):
    On = auto()
    Off = auto()


@dataclass_json
@dataclass(slots=True)
class Window_input:
    hdmi: Hdmi | None = None

    def __repr__(self) -> str:
        if self.hdmi is None:
            return "?"
        else:
            return f"{self.hdmi!r}"


@dataclass_json
@dataclass(slots=True)
class Window_border:
    border: Border | None = None
    border_color: Color | None = None


@dataclass(slots=True)
class Mode_screen:
    mode: Mode
    submode: Submode | None = None
    window_inputs: dict[Window, Window_input] = field(
        init=False, metadata=json_dict(Window, Window_input)
    )

    def __post_init__(self):
        mode = self.mode
        self.window_inputs = {w: Window_input() for w in mode.windows()}

        def window_border(window):
            d = Window_border()
            if not mode.window_has_border(window):
                d.border = Border.Off
                d.border_color = Color.BLACK
            return d

    def __repr__(self) -> str:
        if not self.mode.has_submode():
            submode = ""
        elif self.submode is None:
            submode = "(?)"
        else:
            submode = f"({self.submode.to_int()})"
        windows = " ".join(
            [self.window_inputs[w].__repr__() for w in self.mode.windows()]
        )
        return f"{self.mode.name}{submode} {windows}"


@dataclass(slots=True)
class Jtech:
    # These fields represent our belief about the jtech's current state.
    power: Power | None = None
    mode: Mode | None = None
    pip_location: PipLocation | None = None
    audio_from: Hdmi | None = None
    audio_mute: Mute | None = None
    mode_screens: Dict[Mode, Mode_screen] = field(init=False)
    window_borders: dict[Window, Window_border] = field(
        init=False, metadata=json_dict(Window, Window_border)
    )
    connection: Connection | None = None

    @classmethod
    def field(cls):
        return dataclasses.field(default_factory=Jtech)

    def __post_init__(self) -> None:
        self.init_mode_screens()
        self.window_borders = {w: Window_border() for w in Window.all()}

    def init_mode_screens(self):
        self.mode_screens = {
            mode: Mode_screen(mode=mode, submode=None) for mode in Mode.all()
        }

    async def reset(self) -> None:
        self.power = None
        self.mode = None
        self.audio_from = None
        self.audio_mute = None
        self.init_mode_screens()
        await self.disconnect()

    def get_submode(self, mode: Mode) -> Submode | None:
        return self.mode_screens[mode].submode

    def window_border(self, w: Window) -> Window_border:
        return self.window_borders[w]

    def window_input(self, mode: Mode, w: Window) -> Window_input:
        return self.mode_screens[mode].window_inputs[w]

    def check_expectation(self, description, x, y) -> None:
        if x is not None and y is not None and x != y:
            log(f"jtech mismatch for {description}: expected {x} but got {y}")

    def record_mode(self, m) -> None:
        self.check_expectation("mode", self.mode, m)
        self.mode = m

    def record_submode(self, mode: Mode, submode: Submode | None) -> None:
        self.check_expectation("submode", self.mode_screens[mode].submode, submode)
        self.mode_screens[mode].submode = submode

    def record_audio_from(self, h) -> None:
        self.check_expectation("audio from", self.audio_from, h)
        self.audio_from = h

    def record_audio_mute(self, m: Mute | None) -> None:
        self.check_expectation("audio mute", self.audio_mute, m)
        self.audio_mute = m

    def record_border(self, w: Window, b: Border | None) -> None:
        wb = self.window_border(w)
        self.check_expectation(f"{w} border", wb.border, b)
        wb.border = b

    def record_border_color(self, w: Window, c) -> None:
        wb = self.window_border(w)
        self.check_expectation(f"{w} color", wb.border_color, c)
        wb.border_color = c

    def record_window_input(self, m: Mode, w: Window, h: Hdmi | None) -> None:
        wi = self.window_input(m, w)
        self.check_expectation(f"{w} input", wi.hdmi, h)
        wi.hdmi = h

    def unexpected_response(
        self, command, response, expected_response=None
    ) -> NoReturn:
        message = f"jtech gave unexpected response '{response}' to command '{command}'"
        if expected_response is not None:
            message = f"{message}, expected '{expected_response}'"
        log(message)
        fail(message)

    async def get_connection(self) -> Connection:
        if self.connection is None:
            connection = await Connection.create()
            log("connected to jtech")
            self.connection = connection
            await self.sync_connection(connection)
        else:
            connection = self.connection
        return connection

    async def sync_connection(self, connection) -> None:
        # To sync the connection, we send "r power!" to request the power state.  We
        # ignore any existing unconsumed output by reading unti we see the jtech's
        # response: "power on" or "power off".
        log("syncing jtech connection")
        await connection.write_line("r power!")
        while True:
            line = await connection.read_line()
            if line == "power on" or line == "power off":
                break
        log("synced jtech connection")

    async def disconnect(self) -> None:
        if self.connection is not None:
            await self.connection.close()
            log("disconnected from jtech")
            self.connection = None

    async def send_command(self, command: str, *, expected_response=None) -> str:
        if False:
            log(f"jtech<<< {command}")
        connection = await self.get_connection()
        response = await connection.send_command(command)
        if response is None:
            log(f"jtech did not respond to: {command}")
            fail("jtech is nonresponsive")
        if expected_response is not None and response != expected_response:
            self.unexpected_response(command, response, expected_response)
        if False:
            log(f"jtech>>> {response}")
        return response

    async def read_power(self) -> Power:
        command = "r power!"
        response = await self.send_command(command)
        if response == "power on":
            power = ON
        elif response == "power off":
            power = OFF
        else:
            self.unexpected_response(command, response)
        self.power = power
        return power

    async def set_power(self, power: Power) -> None:
        if False:
            debug_print(f"set_to={power} was={self.power}")
        self.power = None
        await self.read_power()
        if self.power == power:
            return
        await self.send_command(f"power {power.to_int()}!")
        if power == ON:
            # After the jtech powers on, it outputs a bunch of cruft that we need to
            # consume.  It also is silent for a few seconds.  So, we read until we see
            # "Initialization Finished!".  Some of those reads timeout while the jtech is
            # silent, but we keep trying.  Then we sync the connection, which ignores the
            # cruft that the jtech outputs after "Initialization Finished!".
            connection = self.connection
            assert connection is not None
            await connection.read_until_line("Initialization Finished!")
            await self.sync_connection(connection)
        await self.read_power()
        assert_equal(self.power, power)

    async def read_window_input(self, mode: Mode, window: Window) -> Hdmi:
        wi = window.to_int()
        command = f"r window {wi} in!"
        response = await self.send_command(command)
        match = re.fullmatch(rf"window {wi} select HDMI (?P<h>\d+)", response)
        if not match:
            self.unexpected_response(command, response)
        hdmi = Hdmi.of_int(int(match.group("h")))
        self.record_window_input(mode, window, hdmi)
        return hdmi

    async def set_window_input(self, mode: Mode, window: Window, hdmi: Hdmi) -> None:
        current = self.window_input(mode, window).hdmi
        if current == hdmi:
            return
        if mode != Mode.FULL and hdmi == self.audio_from:
            # In multiview modes, there can be audio blips if windows holding
            # audio_from_hdmi change. Doesn't seem to happen in FULL.
            await self.mute()
        wi = window.to_int()
        hi = hdmi.to_int()
        self.record_window_input(mode, window, None)
        await self.send_command(
            f"s window {wi} in {hi}!", expected_response=f"window {wi} select HDMI {hi}"
        )
        self.record_window_input(mode, window, hdmi)

    async def read_border(self, mode: Mode, window: Window) -> Border:
        wi = window.to_int()
        command = f"r window {wi} border!"
        response = await self.send_command(command)
        if response == f"window {wi} border on":
            border = Border.On
        elif response == f"window {wi} border off":
            border = Border.Off
        else:
            self.unexpected_response(command, response)
        self.record_border(window, border)
        return border

    async def set_border(self, mode: Mode, window: Window, border: Border) -> None:
        if border == self.window_border(window).border:
            return
        wi = window.to_int()
        if border == Border.On:
            command_b = "1"
            response_b = "on"
        elif border == Border.Off:
            command_b = "0"
            response_b = "off"
        else:
            fail("invalid border")
        command = f"s window {wi} border {command_b}!"
        self.record_border(window, None)
        await self.send_command(
            command, expected_response=f"window {wi} border {response_b}"
        )
        self.record_border(window, border)

    async def read_border_color(self, mode: Mode, window: Window) -> Color:
        wi = window.to_int()
        command = f"r window {wi} border color!"
        response = await self.send_command(command)
        match = re.fullmatch(
            rf"window {wi} border color:(?P<c>[A-Za-z_]+)", response.strip()
        )
        if not match:
            self.unexpected_response(command, response)
        color = Color[match.group("c")]
        self.record_border_color(window, color)
        return color

    async def set_border_color(self, mode: Mode, window: Window, color: Color) -> None:
        if color == self.window_border(window).border_color:
            return
        wi = window.to_int()
        self.record_border_color(window, None)
        await self.send_command(
            f"s window {wi} border color {color.to_int()}!",
            expected_response=f"window {wi} border color:{color.value}",
        )
        self.record_border_color(window, color)

    async def read_audio_mute(self) -> Mute:
        command = "r output audio mute!"
        response = await self.send_command(command)
        if response == "output audio mute: on":
            mute = MUTED
        elif response == "output audio mute: off":
            mute = UNMUTED
        else:
            self.unexpected_response(command, response)
        self.record_audio_mute(mute)
        return mute

    async def set_audio_mute(self, mute: Mute) -> None:
        if self.audio_mute == mute:
            return
        if False:
            debug_print(mute)
        match mute:
            case Mute.MUTED:
                z = "on"
            case Mute.UNMUTED:
                z = "off"
        self.record_audio_mute(None)
        await self.send_command(
            f"s output audio mute {mute.to_int()}!",
            expected_response=f"output audio mute: {z}",
        )
        self.record_audio_mute(mute)

    async def mute(self) -> None:
        return await self.set_audio_mute(MUTED)

    async def unmute(self) -> None:
        return await self.set_audio_mute(UNMUTED)

    async def read_audio_from(self) -> Hdmi:
        command = "r output audio!"
        response = await self.send_command(command)
        match = re.search(r"HDMI (\d+)", response, re.I)
        if not match:
            self.unexpected_response(command, response)
        hdmi = Hdmi.of_int(int(match.group(1)))
        self.record_audio_from(hdmi)
        return hdmi

    async def set_audio_from(self, hdmi: Hdmi) -> None:
        if self.audio_from == hdmi:
            return
        hi = hdmi.to_int()
        self.record_audio_from(None)
        await self.send_command(
            f"s output audio {hi}!",
            expected_response=f"output audio: HDMI {hi} input audio",
        )
        self.record_audio_from(hdmi)

    async def read_mode(self) -> Mode:
        response = await self.send_command("r multiview!")
        mode = multiview_mode_by_name.get(response)
        if mode is None:
            fail("invalid multiview response", response)
        self.record_mode(mode)
        return mode

    async def set_mode(self, mode: Mode) -> None:
        if mode == self.mode:
            return
        self.record_mode(None)
        await self.send_command(
            f"s multiview {mode.to_int()}!",
            expected_response=multiview_name_by_mode[mode],
        )
        self.record_mode(mode)

    async def read_submode(self, mode: Mode) -> Submode | None:
        if mode == Mode.FULL or mode == Mode.PIP:
            return None
        n = mode.name_for_submode_command()
        command = f"r {n} mode!"
        response = await self.send_command(command)
        if response == f"{n} mode 1":
            submode = WINDOWS_SAME
        elif response == f"{n} mode 2":
            submode = W1_PROMINENT
        else:
            self.unexpected_response(command, response)
        self.record_submode(mode, submode)
        return submode

    async def set_submode(self, mode: Mode, submode: Submode) -> None:
        if False:
            debug_print(self)
        if submode == self.get_submode(mode):
            return
        n = mode.name_for_submode_command()
        si = submode.to_int()
        command = f"s {n} mode {si}!"
        self.record_submode(mode, None)
        await self.send_command(command, expected_response=f"{n} mode {si}")
        self.record_submode(mode, submode)

    async def set_pip(self, pip_location: PipLocation) -> None:
        if self.pip_location == pip_location:
            return
        hsize = vsize = 19
        left = 3
        top = 3
        right = 99 - hsize
        bottom = 99 - vsize
        match pip_location:
            case PipLocation.NW:
                hstart, vstart = left, top
            case PipLocation.NE:
                hstart, vstart = right, top
            case PipLocation.SW:
                hstart, vstart = left, bottom
            case PipLocation.SE:
                hstart, vstart = right, bottom
        command = f"s PIP {hstart} {vstart} {hsize} {vsize}!"
        expected_response = f"PIP {hstart} {vstart} {hsize} {vsize}"
        self.pip_location = None
        await self.send_command(command, expected_response=expected_response)
        self.pip_location = pip_location

    async def test_aliasing_of_window_input(
        self, mode1: Mode, mode2: Mode, window: Window
    ) -> None:
        if not window in mode1.windows() or not window in mode2.windows():
            return
        await self.set_mode(mode1)
        await aio.sleep(1)
        await self.set_window_input(mode1, window, H1)
        await aio.sleep(1)
        await self.set_mode(mode2)
        await aio.sleep(1)
        await self.set_window_input(mode2, window, H2)
        await aio.sleep(1)
        await self.set_mode(mode1)
        await aio.sleep(1)
        h = await self.read_window_input(mode1, window)
        if h == H1:
            pass
        elif h == H2:
            print(f"{mode1} {mode2} {window}")
        else:
            fail(f"{mode1} {mode2} {window} {h}")

    async def test_aliasing_of_border(
        self, mode1: Mode, mode2: Mode, window: Window
    ) -> None:
        if not window in mode1.windows() or not window in mode2.windows():
            return
        await self.set_mode(mode1)
        await aio.sleep(1)
        await self.set_border(mode1, window, Border.On)
        await aio.sleep(1)
        await self.set_mode(mode2)
        await aio.sleep(1)
        await self.set_border(mode2, window, Border.Off)
        await aio.sleep(1)
        await self.set_mode(mode1)
        await aio.sleep(1)
        b = await self.read_border(mode1, window)
        if b == Border.Off:
            print(f"{mode1} {mode2} {window}")

    async def test_aliasing(self) -> None:
        print()
        for mode1 in Mode.all():
            for mode2 in Mode.all():
                if mode1 == mode2:
                    continue
                for window in mode1.windows():
                    if window in mode2.windows():
                        # await self.test_aliasing_of_window_input(mode1, mode2, window)
                        await self.test_aliasing_of_border(mode1, mode2, window)
