from __future__ import annotations

# Standard library
import dataclasses
import re

# Local package
from .base import *
from .ip2sl import Connection
from .json_field import json_dict

class Power(MyStrEnum):
    OFF = auto()
    ON = auto()

    def flip(self):
        match self:
            case Power.ON: return OFF
            case Power.OFF: return ON

OFF, ON = Power.OFF, Power.ON

attach_int(Power, { OFF: 0, ON: 1 })

class Hdmi(MyStrEnum):
    H1 = auto()
    H2 = auto()
    H3 = auto()
    H4 = auto()

H1 = Hdmi.H1
H2 = Hdmi.H2
H3 = Hdmi.H3
H4 = Hdmi.H4

attach_int(Hdmi, { H1: 1, H2: 2, H3: 3, H4: 4})

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
    FULL   = auto()
    PIP    = auto()
    PBP    = auto()
    TRIPLE = auto()
    QUAD   = auto()
    
    def has_submode(self) -> bool:
        match self:
            case Mode.FULL | Mode.PIP: return False
            case Mode.PBP | Mode.TRIPLE | Mode.QUAD: return True

    def num_windows(self) -> int:
        match self:
            case Mode.FULL: return 1
            case Mode.PIP | Mode.PBP: return 2
            case Mode.TRIPLE: return 3
            case Mode.QUAD: return 4
                
    def windows(self) -> list[Window]:
        return [Window.of_int(i) for i in range(1, 1 + self.num_windows())]

    def name_for_submode_command(self) -> str:
        match self:
            case Mode.PBP: return "PBP"
            case Mode.TRIPLE: return "triple"
            case Mode.QUAD: return "quad"
            case _: fail(f"mode {self} has no submode")

    def window_has_border(self, w: Window) -> bool:
        match self:
            case Mode.FULL: return False
            case Mode.PIP: return (w == W2)
            case Mode.PBP | Mode.TRIPLE | Mode.QUAD: return True

FULL, PIP, PBP, TRIPLE, QUAD = Mode.FULL, Mode.PIP, Mode.PBP, Mode.TRIPLE, Mode.QUAD

attach_int(Mode, {FULL: 1, PIP: 2, PBP: 3, TRIPLE: 4, QUAD: 5})

multiview_name_by_mode = {
    FULL: "single screen",
    PIP: "PIP",
    PBP: "PBP",
    TRIPLE: "triple screen",
    QUAD: "quad screen" }

def invert_dict(d: dict) -> dict:
    return {v: k for k, v in d.items()}

multiview_mode_by_name = invert_dict(multiview_name_by_mode)
 
class Submode(MyStrEnum):
    WINDOWS_SAME = auto()
    W1_PROMINENT = auto()

    def flip(self: Submode) -> Submode:
        match self:
            case Submode.WINDOWS_SAME: return W1_PROMINENT
            case Submode.W1_PROMINENT: return WINDOWS_SAME

WINDOWS_SAME = Submode.WINDOWS_SAME
W1_PROMINENT = Submode.W1_PROMINENT

attach_int(Submode, {WINDOWS_SAME: 1, W1_PROMINENT: 2})

class Color(MyStrEnum):
    BLACK   = auto()
    RED     = auto()
    GREEN   = auto()
    BLUE    = auto()
    YELLOW  = auto()
    MAGENTA = auto()
    CYAN    = auto()
    WHITE   = auto()
    GRAY    = auto()

BLACK = Color.BLACK
RED = Color.RED
GREEN = Color.GREEN
BLUE = Color.BLUE
YELLOW = Color.YELLOW
MAGENTA = Color.MAGENTA
CYAN = Color.CYAN
WHITE = Color.WHITE
GRAY = Color.GRAY    

attach_int(Color, {
        BLACK: 1,
        RED: 2,
        GREEN: 3,
        BLUE: 4,
        YELLOW: 5,
        MAGENTA: 6,
        CYAN: 7,
        WHITE: 8,
        GRAY: 9,
    })

def color_letter(c):
    match c:
        case Color.BLACK  : return 'K'
        case Color.RED    : return 'R'
        case Color.GREEN  : return 'G'
        case Color.BLUE   : return 'B'
        case Color.YELLOW : return 'Y'
        case Color.MAGENTA: return 'M'
        case Color.CYAN   : return 'C'
        case Color.WHITE  : return 'W'
        case Color.GRAY   : return 'A'
        case _            : fail("invalid color", c)

class Mute(MyStrEnum):
    UNMUTED = auto()
    MUTED   = auto()
    
MUTED = Mute.MUTED
UNMUTED = Mute.UNMUTED

attach_int(Mute, {UNMUTED: 0, MUTED: 1})

@dataclass_json
@dataclass()
class Window_contents:
    hdmi: Hdmi
    border: Color | None

    def __repr__(self) -> str:
        s = f"{self.hdmi!r}"
        if self.border:
            c = color_letter(self.border)
            s = f"[{s}]{c}"
        return s

@dataclass_json
@dataclass
class Screen:
    mode: Mode
    submode: Submode | None
    audio_from: Hdmi
    windows: dict[Window, Window_contents] = field(
        metadata=json_dict(Window, Window_contents))

    def one_line_description(self) -> str:
        s = self
        sub_str = f"({s.submode.to_int()})" if s.submode is not None else ""
        parts = []
        for w, c in sorted(s.windows.items()):
            h = f"{c.hdmi.value}"
            border = c.border
            if border is not None:
                h = f"[{h}]{color_letter(border)}"
            parts.append(h)
        return f"{s.mode.value}{sub_str} A{s.audio_from.to_int()} " + " ".join(parts)    
    
    def __repr__(self) -> str:
        return self.one_line_description()

class Border(MyStrEnum):
    On = auto()
    Off = auto()

@dataclass_json
@dataclass
class Device_window:
    hdmi: Hdmi | None = None
    border: Border | None = None
    border_color: Color | None = None

    def __repr__(self) -> str:
        if self.hdmi is None:
            s = "H?"
        else:
            s = f"{self.hdmi!r}"
        if self.border == None:
            s = f"?{s}]"
        elif self.border == Border.On:
            s = f"[{s}]"    
        if self.border_color is None:
            c = "?"
        elif self.border_color == BLACK:
            c = ""
        else:
            c = color_letter(self.border_color)
        return f"{s}{c}"
    
@dataclass 
class Mode_screen:
    mode: Mode
    submode: Submode | None = None
    windows: dict[Window, Device_window] = field(
        init=False,
        metadata=json_dict(Window, Device_window))

    def __post_init__(self):
        mode = self.mode
        def device_window(window):
            d = Device_window()
            if not mode.window_has_border(window):
                d.border = Border.Off
                d.border_color = Color.BLACK
            return d
        self.windows = { w: device_window(w) for w in mode.windows() }

    def __repr__(self) -> str:
        if not self.mode.has_submode():
            submode = ""
        elif self.submode is None:
            submode = "(?)"
        else:
            submode = f"({self.submode.to_int()})"
        windows = " ".join([ w.__repr__() for w in self.windows.values() ])
        return f"{self.mode.name}{submode} {windows}"

@dataclass
class Device:
    # These fields represent our belief about the jtech's current state.
    power: Power | None = None
    mode: Mode | None = None
    audio_from: Hdmi | None = None
    audio_mute: Mute | None = None
    mode_screens: Dict[Mode,Mode_screen] = field(init=False)
    """mode_screens[mode] is our belief about the jtech's state for that mode. The
    entries for PIP and PBP are shared, because that's what the J-Tech does."""
    connection: Connection | None = None

    @classmethod
    def field(cls):
        return dataclasses.field(default_factory=Device)

    def __post_init__(self) -> None:
        self.init_mode_screens()

    def init_mode_screens(self):
        self.mode_screens = {
            mode: Mode_screen(mode=mode, submode=None) 
            for mode in [ FULL, PBP, TRIPLE, QUAD ] }
        self.mode_screens[PIP] = self.mode_screens[PBP]
        
    async def reset(self) -> None:
        self.power = None
        self.mode = None
        self.audio_from = None
        self.audio_mute = None
        self.init_mode_screens()
        await self.disconnect()

    def get_submode(self, mode: Mode) -> Submode | None:
        return self.mode_screens[mode].submode
    
    def device_window(self, mode: Mode, w: Window) -> Device_window:
        return self.mode_screens[mode].windows[w]

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

    def record_border(self, m: Mode, w : Window, b: Border | None) -> None:
        self.check_expectation(f"{w} border", self.device_window(m, w).border, b)
        self.device_window(m, w).border = b
            
    def record_border_color(self, m: Mode, w: Window, c) -> None:
        self.check_expectation(f"{w} color", 
                               self.device_window(m, w).border_color, c)
        self.device_window(m, w).border_color = c
    
    def record_window_input(self, m: Mode, w: Window, h: Hdmi | None) -> None:
        self.check_expectation(f"{w} input", self.device_window(m, w).hdmi, h)
        self.device_window(m, w).hdmi = h

    def window_input(self, m: Mode, w: Window) -> Hdmi | None:
        return self.device_window(m, w).hdmi

    def unexpected_response(self, command, response, expected_response=None) -> NoReturn:
        message = f"jtech gave unexpected response '{response}' to command '{command}'"
        if expected_response is not None:
            message=f"{message}, expected '{expected_response}'"
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
        if False: log(f"jtech<<< {command}")
        connection = await self.get_connection()
        response = await connection.send_command(command)
        if response is None:
            log(f"jtech did not respond to: {command}")
            fail("jtech is nonresponsive")
        if expected_response is not None and response != expected_response:
            self.unexpected_response(command, response, expected_response)
        if False: log(f"jtech>>> {response}")       
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
        if False: debug_print(f"set_to={power} was={self.power}")
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
        wi = window.to_int()
        hi = hdmi.to_int()
        self.record_window_input(mode, window, None)
        await self.send_command( f"s window {wi} in {hi}!", 
            expected_response=f"window {wi} select HDMI {hi}")
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
        self.record_border(mode, window, border)
        return border

    async def set_border(self, mode: Mode, window: Window, border: Border) -> None:
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
        self.record_border(mode, window, None)
        await self.send_command( command,
            expected_response=f"window {wi} border {response_b}")
        self.record_border(mode, window, border)

    async def read_border_color(self, mode: Mode, window: Window) -> Color:
        wi = window.to_int()
        command = f"r window {wi} border color!"
        response = await self.send_command(command)
        match = re.fullmatch(rf"window {wi} border color:(?P<c>[A-Za-z_]+)", 
                             response.strip())
        if not match:
            self.unexpected_response(command, response)
        color = Color[match.group("c")]
        self.record_border_color(mode, window, color)
        return color

    async def set_border_color(self, mode: Mode, window: Window, color: Color) -> None:
        wi = window.to_int()
        self.record_border_color(mode, window, None)
        await self.send_command(
            f"s window {wi} border color {color.to_int()}!",
            expected_response=f"window {wi} border color:{color.value}")
        self.record_border_color(mode, window, color)

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
        if False: debug_print(mute)
        match mute:
            case Mute.MUTED:
                z = "on"
            case Mute.UNMUTED:
                z = "off"
        self.record_audio_mute(None)
        await self.send_command(
            f"s output audio mute {mute.to_int()}!",
            expected_response=f"output audio mute: {z}")
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
            expected_response=f"output audio: HDMI {hi} input audio")
        self.record_audio_from(hdmi)

    async def read_mode(self) -> Mode:
        response = await self.send_command("r multiview!")
        mode = multiview_mode_by_name.get(response)
        if mode is None:
            fail("invalid multiview response", response)
        self.record_mode(mode)
        return mode
        
    async def set_mode(self, mode: Mode) -> None:
        self.record_mode(None)
        await self.send_command(f"s multiview {mode.to_int()}!",
            expected_response=multiview_name_by_mode[mode])
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
        if False: debug_print(self)
        n = mode.name_for_submode_command()
        si = submode.to_int()
        command = f"s {n} mode {si}!"
        self.record_submode(mode, None)
        await self.send_command(command, expected_response=f"{n} mode {si}")
        self.record_submode(mode, submode)

    async def read_screen(self, should_abort) -> Screen | None:
        mode = await self.read_mode()
        if should_abort(): return
        submode = await self.read_submode(mode)
        if should_abort(): return
        audio_from = await self.read_audio_from()
        if should_abort(): return
        windows = {}
        for window in mode.windows():
            hdmi = await self.read_window_input(mode, window)
            if should_abort(): return
            if not mode.window_has_border(window):
                border = None
            else:
                border = await self.read_border(mode, window)
                if should_abort(): return
                if border == Border.Off:
                    border = None
                else:
                    border = await self.read_border_color(mode, window) 
                    if should_abort(): return
            windows[window] = Window_contents(hdmi, border)
        return Screen(mode, submode, audio_from, windows)

    async def set_screen(self, desired: Screen, should_abort: Callable[[], bool]) -> bool:
        if False: debug_print(desired, self)
        mode_changed = desired.mode != self.mode
        if mode_changed:
            await self.set_mode(desired.mode)
            if should_abort(): return False
        if (desired.submode is not None
            and (desired.submode != self.get_submode(desired.mode))):
            await self.set_submode(desired.mode, desired.submode)
            if should_abort(): return False
        # Set window inputs and turn on borders.
        for w, d in desired.windows.items():
            current = self.device_window(desired.mode, w)
            if d.hdmi != current.hdmi:
                if desired.mode != FULL and d.hdmi == desired.audio_from:
                    # In multiview modes, there can be audio blips if windows holding
                    # audio_from_hdmi change. Doesn't seem to happen in FULL.
                     await self.mute()
                await self.set_window_input(desired.mode, w, d.hdmi)
                if should_abort(): return False
            if d.border is not None:
                if current.border != Border.On:
                    await self.set_border(desired.mode, w, Border.On)
                    if should_abort(): return False
                if current.border_color != d.border:
                    await self.set_border_color(desired.mode, w, d.border)
                    if should_abort(): return False
        # Turn off borders.  We do this after turning on borders, because the visual
        # effect is nicer. The user sees the new border 100ms sooner.
        for w, d in desired.windows.items():
            current = self.device_window(desired.mode, w)
            if (d.border is None
                and current.border != Border.Off
                and desired.mode.window_has_border(w)):
                await self.set_border(desired.mode, w, Border.Off)
                if should_abort(): return False
        # We do audio last, after visual effects.
        await self.set_audio_from(desired.audio_from)
        await self.unmute()
        return True
