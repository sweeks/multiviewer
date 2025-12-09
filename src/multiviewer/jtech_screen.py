from __future__ import annotations

# Standard library
from .base import *
from .json_field import json_dict
from .jtech import (
    Border,
    Color,
    Hdmi,
    Jtech,
    Mode,
    PipLocation,
    Submode,
    Window,
)


def color_letter(c: Color) -> str:
    match c:
        case Color.BLACK:
            return "K"
        case Color.RED:
            return "R"
        case Color.GREEN:
            return "G"
        case Color.BLUE:
            return "B"
        case Color.YELLOW:
            return "Y"
        case Color.MAGENTA:
            return "M"
        case Color.CYAN:
            return "C"
        case Color.WHITE:
            return "W"
        case Color.GRAY:
            return "A"
        case _:
            fail("invalid color", c)


@dataclass_json
@dataclass(slots=True)
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
@dataclass(slots=True)
class Screen:
    mode: Mode
    submode: Submode | None
    pip_location: PipLocation | None
    audio_from: Hdmi
    windows: dict[Window, Window_contents] = field(
        metadata=json_dict(Window, Window_contents)
    )

    def one_line_description(self) -> str:
        s = self
        if s.submode is not None:
            sub_str = f"({s.submode.to_int()})"
        elif s.pip_location is not None:
            sub_str = f"({s.pip_location})"
        else:
            sub_str = ""
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

    @classmethod
    async def read_jtech(
        cls, device: Jtech, should_abort: Callable[[], bool]
    ) -> Screen | None:
        """
        Send commands to the J-Tech to read its currently displayed screen. After sending
        each command, check should_abort(); if it returns True, abort early and return
        None. Otherwise, return the read Screen.
        """
        mode = await device.read_mode()
        if should_abort():
            return None
        submode = await device.read_submode(mode)
        if should_abort():
            return None
        if mode == Mode.PIP:
            pip_location = device.pip_location
        else:
            pip_location = None
        audio_from = await device.read_audio_from()
        if should_abort():
            return None
        windows = {}
        for window in mode.windows():
            hdmi = await device.read_window_input(mode, window)
            if should_abort():
                return None
            if not mode.window_has_border(window):
                border = None
            else:
                border = await device.read_border(mode, window)
                if should_abort():
                    return None
                if border == Border.Off:
                    border = None
                else:
                    border = await device.read_border_color(mode, window)
                    if should_abort():
                        return None
            windows[window] = Window_contents(hdmi, border)
        return cls(mode, submode, pip_location, audio_from, windows)

    async def set_jtech(self, device: Jtech, should_abort: Callable[[], bool]) -> bool:
        """
        Send commands to the J-Tech to make its displayed screen match this Screen.
        After sending each command, check should_abort(); if it returns True, abort early
        and return False. Return True if the entire desired Screen was set.
        """
        desired = self
        if False:
            debug_print(desired, device)
        mode_changed = desired.mode != device.mode
        if mode_changed:
            await device.set_mode(desired.mode)
            if should_abort():
                return False
        if desired.mode == Mode.PIP:
            if desired.pip_location is None:
                pip_location = PipLocation.NE
            else:
                pip_location = desired.pip_location
            await device.set_pip(pip_location)
            if should_abort():
                return False
        if desired.submode is not None and (
            desired.submode != device.get_submode(desired.mode)
        ):
            await device.set_submode(desired.mode, desired.submode)
            if should_abort():
                return False
        # Set window inputs and turn on borders.
        for w, d in desired.windows.items():
            current = device.window_input(desired.mode, w)
            if d.hdmi != current.hdmi:
                if desired.mode != Mode.FULL and d.hdmi == desired.audio_from:
                    # In multiview modes, there can be audio blips if windows holding
                    # audio_from_hdmi change. Doesn't seem to happen in FULL.
                    await device.mute()
                await device.set_window_input(desired.mode, w, d.hdmi)
                if should_abort():
                    return False
            current = device.window_border(desired.mode, w)
            if d.border is not None:
                if current.border != Border.On:
                    await device.set_border(desired.mode, w, Border.On)
                    if should_abort():
                        return False
                if current.border_color != d.border:
                    await device.set_border_color(desired.mode, w, d.border)
                    if should_abort():
                        return False
        # Turn off borders.  We do this after turning on borders, because the visual
        # effect is nicer. The user sees the new border 100ms sooner.
        for w, d in desired.windows.items():
            current = device.window_border(desired.mode, w)
            if (
                d.border is None
                and current.border != Border.Off
                and desired.mode.window_has_border(w)
            ):
                await device.set_border(desired.mode, w, Border.Off)
                if should_abort():
                    return False
        # We do audio last, after visual effects.
        await device.set_audio_from(desired.audio_from)
        await device.unmute()
        return True
