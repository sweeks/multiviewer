from __future__ import annotations

# Standard library
from dataclasses import dataclass
from typing import Callable, TypeAlias

# Local package
from .base import *
from .jtech import Border, Color, Hdmi, Jtech, Mode, PipLocation, Submode, Window

W1 = Window.W1
W2 = Window.W2
W3 = Window.W3
W4 = Window.W4


@dataclass_json
@dataclass(slots=True)
class WindowContents:
    hdmi: Hdmi
    border: Color | None

    def __repr__(self) -> str:
        s = f"{self.hdmi!r}"
        if self.border:
            s = f"[{s}]{self.border.letter()}"
        return s


@dataclass_json
@dataclass(slots=True)
class Full:
    w1: WindowContents

    def windows(self) -> dict[Window, WindowContents]:
        return {W1: self.w1}


@dataclass_json
@dataclass(slots=True)
class Pip:
    pip_location: PipLocation
    w1: WindowContents
    w2: WindowContents

    def windows(self) -> dict[Window, WindowContents]:
        return {W1: self.w1, W2: self.w2}


@dataclass_json
@dataclass(slots=True)
class Pbp:
    submode: Submode
    w1: WindowContents
    w2: WindowContents

    def windows(self) -> dict[Window, WindowContents]:
        return {W1: self.w1, W2: self.w2}


@dataclass_json
@dataclass(slots=True)
class Triple:
    submode: Submode
    w1: WindowContents
    w2: WindowContents
    w3: WindowContents

    def windows(self) -> dict[Window, WindowContents]:
        return {W1: self.w1, W2: self.w2, W3: self.w3}


@dataclass_json
@dataclass(slots=True)
class Quad:
    submode: Submode
    w1: WindowContents
    w2: WindowContents
    w3: WindowContents
    w4: WindowContents

    def windows(self) -> dict[Window, WindowContents]:
        return {
            W1: self.w1,
            W2: self.w2,
            W3: self.w3,
            W4: self.w4,
        }


Layout: TypeAlias = Full | Pip | Pbp | Triple | Quad


def layout_windows(layout: Layout) -> dict[Window, WindowContents]:
    return layout.windows()


def layout_mode(layout: Layout) -> Mode:
    if isinstance(layout, Full):
        return Mode.FULL
    if isinstance(layout, Pip):
        return Mode.PIP
    if isinstance(layout, Pbp):
        return Mode.PBP
    if isinstance(layout, Triple):
        return Mode.TRIPLE
    return Mode.QUAD


def layout_submode(layout: Layout) -> Submode | None:
    if isinstance(layout, (Pbp, Triple, Quad)):
        return layout.submode
    return None


def layout_pip_location(layout: Layout) -> PipLocation | None:
    if isinstance(layout, Pip):
        return layout.pip_location
    return None


@dataclass_json
@dataclass(slots=True)
class JtechOutput:
    layout: Layout
    audio_from: Hdmi

    def one_line_description(self) -> str:
        mode = layout_mode(self.layout)
        submode = layout_submode(self.layout)
        pip_location = layout_pip_location(self.layout)
        if submode is not None:
            sub_str = f"({submode.to_int()})"
        elif pip_location is not None:
            sub_str = f"({pip_location})"
        else:
            sub_str = ""
        parts = []
        for w, c in sorted(layout_windows(self.layout).items()):
            h = f"{c.hdmi.value}"
            border = c.border
            if border is not None:
                h = f"[{h}]{border.letter()}"
            parts.append(h)
        return f"{mode.value}{sub_str} A{self.audio_from.to_int()} " + " ".join(parts)

    def __repr__(self) -> str:
        return self.one_line_description()

    @classmethod
    async def read(
        cls, jtech: Jtech, should_abort: Callable[[], bool]
    ) -> JtechOutput | None:
        mode = await jtech.read_mode()
        if should_abort():
            return None
        submode = await jtech.read_submode(mode)
        if should_abort():
            return None
        if mode == Mode.PIP:
            pip_location = await jtech.read_pip_location() or PipLocation.NE
        else:
            pip_location = None
        audio_from = await jtech.read_audio_from()
        if should_abort():
            return None
        windows: dict[Window, WindowContents] = {}
        for window in mode.windows():
            hdmi = await jtech.read_window_input(mode, window)
            if should_abort():
                return None
            if not mode.window_has_border(window):
                border = None
            else:
                border = await jtech.read_border(mode, window)
                if should_abort():
                    return None
                if border == Border.Off:
                    border = None
                else:
                    border = await jtech.read_border_color(mode, window)
                    if should_abort():
                        return None
            windows[window] = WindowContents(hdmi, border)
        layout: Layout
        if mode == Mode.FULL:
            layout = Full(w1=windows[W1])
        elif mode == Mode.PIP:
            layout = Pip(
                pip_location=pip_location or PipLocation.NE,
                w1=windows[W1],
                w2=windows[W2],
            )
        elif mode == Mode.PBP:
            assert submode is not None
            layout = Pbp(submode=submode, w1=windows[W1], w2=windows[W2])
        elif mode == Mode.TRIPLE:
            assert submode is not None
            layout = Triple(
                submode=submode,
                w1=windows[W1],
                w2=windows[W2],
                w3=windows[W3],
            )
        else:
            assert submode is not None
            layout = Quad(
                submode=submode,
                w1=windows[W1],
                w2=windows[W2],
                w3=windows[W3],
                w4=windows[W4],
            )
        return cls(layout=layout, audio_from=audio_from)

    async def set(self, jtech: Jtech, should_abort: Callable[[], bool]) -> bool:
        if False:
            debug_print(self, jtech)
        layout = self.layout
        mode = layout_mode(layout)
        submode = layout_submode(layout)
        pip_location = layout_pip_location(layout)
        await jtech.set_mode(mode)
        if should_abort():
            return False
        if mode == Mode.PIP and pip_location is not None:
            await jtech.set_pip_location(pip_location)
            if should_abort():
                return False
        if submode is not None:
            await jtech.set_submode(mode, submode)
            if should_abort():
                return False
        windows = layout_windows(layout)
        for w, d in windows.items():
            await jtech.set_window_input(mode, w, d.hdmi)
            if should_abort():
                return False
            if d.border is not None:
                await jtech.set_border(mode, w, Border.On)
                if should_abort():
                    return False
                await jtech.set_border_color(mode, w, d.border)
                if should_abort():
                    return False
        for w, d in windows.items():
            if d.border is None and mode.window_has_border(w):
                await jtech.set_border(mode, w, Border.Off)
                if should_abort():
                    return False
        await jtech.set_audio_from(self.audio_from)
        await jtech.unmute()
        return True
