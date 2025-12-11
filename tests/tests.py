# This file should only be run from the command line, via:
#    python tests.py all
#    python tests.py LINE
# The line numbers correspond to @test annotations.

from __future__ import annotations

import inspect
import json
import sys
import time
import traceback

from multiviewer import aio, mv
from multiviewer.base import *
from multiviewer.mv import Multiviewer

RunMode.set(RunMode.Testing)

_the_mv: None | Multiviewer = None


def the_mv() -> Multiviewer:
    if _the_mv is None:
        fail("did not set the_mv")
    return _the_mv


def expect(actual, expected, frame_index=2):
    if actual != expected:
        frame = inspect.stack()[frame_index]
        lineno = frame.lineno
        print(f"State mismatch at line {lineno}:\n EXPECT: {expected}\n ACTUAL: {actual}")


async def tv_do(s, e=None):
    if False:
        debug_print(s)
    commands = [part.split() for part in s.split(";") if part.strip()]
    last = None
    for c in commands:
        if False:
            debug_print(c)
        j = await mv.do_command_and_update_jtech_output(the_mv(), c)
        last = json.dumps(j)
    if e is not None:
        expect(last, e)


async def tv_is(expected):
    await mv.synced(the_mv())
    expect(await mv.describe_jtech_output(the_mv()), expected)


async def vol_is(expected):
    await mv.synced(the_mv())
    expect(mv.describe_volume(the_mv()), expected)


tests = []


def test(label=None):
    """Decorator to register test functions with optional label."""

    def decorator(fn):
        tests.append((fn.__code__.co_firstlineno, label, fn))
        return fn

    if callable(label):  # bare @test
        fn = label
        tests.append((fn.__code__.co_firstlineno, None, fn))
        return fn
    return decorator


def parse_selection(arg):
    if not arg or arg == "all":
        return None
    sel = set()
    for part in arg.split(","):
        if "-" in part:
            a, b = map(int, part.split("-", 1))
            sel.update(range(a, b + 1))
        else:
            sel.add(int(part))
    return sel


async def run(selected):
    total = passed = 0
    for line, label, fn in sorted(tests):
        if selected and line not in selected:
            continue
        total += 1
        heading = f"L{line}:" + (f" {label}" if label else "") + " ..."
        __builtins__.print(heading, end="", flush=True)
        start = time.perf_counter()
        try:
            await fn()
            elapsed = time.perf_counter() - start
            print(f" {elapsed:.1f}s")
            passed += 1
        except Exception:
            elapsed = time.perf_counter() - start
            print(f"  FAILED ({elapsed:.1f}s)")
            traceback.print_exc()
    print(f"{passed}/{total} passed")


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


@test("Test")
async def _():
    await tv_do("Test")


@test("Reset")
async def _():
    await tv_do("Reset")
    await tv_is("QUAD(2) A1 [H1]G [H2]A [H3]A [H4]A")


@test("Play_pause toggles border")
async def _():
    await tv_do("Reset; Play_pause")
    await tv_is("QUAD(2) A1 [H1]A [H2]A [H3]A [H4]A")


@test("Select+Back toggle fullscreen")
async def _():
    await tv_do("Reset; Select")
    await tv_is("FULL A1 H1")
    await tv_do("Back")
    await tv_is("QUAD(2) A1 [H1]G [H2]A [H3]A [H4]A")


@test("Select+Back preserves submode")
async def _():
    await tv_do("Reset; Play_pause; Play_pause; Select; Back")
    await tv_is("QUAD(1) A1 [H1]G [H2]A [H3]A [H4]A")


@test("Select+Back preserves audio")
async def _():
    await tv_do("Reset; Select; E; Back")
    await tv_is("QUAD(2) A2 [H1]A [H2]G [H3]A [H4]A")


@test("NEWS in QUAD(2)")
async def _():
    await tv_do("Reset")
    await tv_do("N")
    await tv_is("QUAD(2) A2 [H1]A [H2]G [H3]A [H4]A")
    await tv_do("W")
    await tv_is("QUAD(2) A1 [H1]G [H2]A [H3]A [H4]A")
    await tv_do("E")
    await tv_is("QUAD(2) A3 [H1]A [H2]A [H3]G [H4]A")
    await tv_do("S")
    await tv_is("QUAD(2) A4 [H1]A [H2]A [H3]A [H4]G")


@test("NEWS in QUAD(1)")
async def _():
    await tv_do("Reset; Play_pause; Play_pause; E")
    await tv_is("QUAD(1) A2 [H1]A [H2]G [H3]A [H4]A")
    await tv_do("W; S")
    await tv_is("QUAD(1) A3 [H1]A [H2]A [H3]G [H4]A")
    await tv_do("E")
    await tv_is("QUAD(1) A4 [H1]A [H2]A [H3]A [H4]G")
    await tv_do("W; N")
    await tv_is("QUAD(1) A1 [H1]G [H2]A [H3]A [H4]A")


@test("NEWS in FULL")
async def _():
    await tv_do("Reset; Select")
    await tv_is("FULL A1 H1")
    await tv_do("E")
    await tv_is("FULL A2 H2")
    await tv_do("E")
    await tv_is("FULL A3 H3")
    await tv_do("E")
    await tv_is("FULL A4 H4")
    await tv_do("E")
    await tv_is("FULL A1 H1")
    await tv_do("W")
    await tv_is("FULL A4 H4")
    await tv_do("W")
    await tv_is("FULL A3 H3")
    await tv_do("W")
    await tv_is("FULL A2 H2")
    await tv_do("W")
    await tv_is("FULL A1 H1")


@test("PIP and Back from W1")
async def _():
    await tv_do("Reset; Select; Home")
    await tv_is("PIP(NE) A1 H1 [H2]A")
    await tv_do("Back")
    await tv_is("QUAD(2) A1 [H1]G [H2]A [H3]A [H4]A")


@test("PIP and Back from W3")
async def _():
    await tv_do("Reset; E; Select; Home")
    await tv_is("PIP(NE) A3 H3 [H4]A")
    await tv_do("Back")
    await tv_is("QUAD(2) A3 [H1]A [H2]A [H3]G [H4]A")


@test("PIP from FULL after rotating")
async def _():
    await tv_do("Reset; Select; E; Home")
    await tv_is("PIP(NE) A2 H2 [H3]A")


@test("Select PIP window and go Back")
async def _():
    await tv_do("Reset; Select; Home; N")
    await tv_is("PIP(NE) A2 H1 [H2]G")
    await tv_do("Back")
    await tv_is("PIP(NE) A1 H1 [H2]A")


@test("Swap full and PIP windows")
async def _():
    await tv_do("Reset; Select; Home; Select")
    await tv_is("PIP(NE) A2 H2 [H1]A")
    await tv_do("Select")
    await tv_is("PIP(NE) A1 H1 [H2]A")


@test("Swap full and PIP windows from PIP window")
async def _():
    await tv_do("Reset; Select; Home; N; Select")
    await tv_is("PIP(NE) A2 H2 [H1]A")


@test("Change PIP location")
async def _():
    await tv_do("Reset; Select; Home; N")
    await tv_do("W")
    await tv_is("PIP(NW) A2 H1 [H2]G")
    await tv_do("S")
    await tv_is("PIP(SW) A2 H1 [H2]G")
    await tv_do("E")
    await tv_is("PIP(SE) A2 H1 [H2]G")
    await tv_do("N")
    await tv_is("PIP(NE) A2 H1 [H2]G")
    await tv_do("S")
    await tv_is("PIP(SE) A2 H1 [H2]G")
    await tv_do("W")
    await tv_is("PIP(SW) A2 H1 [H2]G")
    await tv_do("N")
    await tv_is("PIP(NW) A2 H1 [H2]G")
    await tv_do("E")
    await tv_is("PIP(NE) A2 H1 [H2]G")


@test("Rotate PIP window")
async def _():
    await tv_do("Reset; Select; Home; E")
    await tv_is("PIP(NE) A1 H1 [H3]A")
    await tv_do("E")
    await tv_is("PIP(NE) A1 H1 [H4]A")
    await tv_do("E")
    await tv_is("PIP(NE) A1 H1 [H2]A")
    await tv_do("W")
    await tv_is("PIP(NE) A1 H1 [H4]A")
    await tv_do("W")
    await tv_is("PIP(NE) A1 H1 [H3]A")
    await tv_do("W")
    await tv_is("PIP(NE) A1 H1 [H2]A")


@test("Back exits fullscreen PIP")
async def _():
    await tv_do("Reset; Select; Home; Back")
    await tv_is("QUAD(2) A1 [H1]G [H2]A [H3]A [H4]A")


@test("Home toggles PIP off")
async def _():
    await tv_do("Reset; Select; Home; Home")
    await tv_is("FULL A1 H1")


@test("Remove_window")
async def _():
    await tv_do("Reset; S; Back")
    await tv_is("TRIPLE(2) A1 [H1]G [H2]A [H3]A")
    await tv_do("Wait 0.4; S; Back")
    await tv_is("PBP(2) A1 [H1]G [H2]A")
    await tv_do("Wait 0.4; Back")
    await tv_is("FULL A2 H2")


@test("Remove_window preserves submode")
async def _():
    await tv_do("Reset; Play_pause; Play_pause; S; Back")
    await tv_is("TRIPLE(1) A4 [H1]A [H2]A [H4]G")


@test("Remove_window switches audio to visible window")
async def _():
    await tv_do("Reset; S; Back")
    await tv_is("TRIPLE(2) A1 [H1]G [H2]A [H3]A")


@test("Add_window")
async def _():
    await tv_do("Reset; S; Back; Wait 0.4; S; Back")
    await tv_is("PBP(2) A1 [H1]G [H2]A")
    await tv_do("Home")
    await tv_is("TRIPLE(2) A1 [H1]G [H2]A [H3]A")
    await tv_do("Home")
    await tv_is("QUAD(2) A1 [H1]G [H2]A [H3]A [H4]A")


@test("Add_window and Remove_window preserve submode")
async def _():
    await tv_do("Reset; Play_pause; Play_pause; S; Back")
    await tv_is("TRIPLE(1) A4 [H1]A [H2]A [H4]G")
    await tv_do("Play_pause; Play_pause; Home; Home")
    await tv_is("QUAD(2) A4 [H1]A [H2]A [H4]G [H3]A")


@test("Demote_window")
async def _():
    await tv_do("Reset; Back")
    await tv_is("TRIPLE(2) A2 [H2]G [H3]A [H4]A")


@test("Back adds window when only one active")
async def _():
    await tv_do("Reset; S; Back; Wait 0.4; S; Back; Wait 0.4; Back")
    await tv_is("FULL A2 H2")
    await tv_do("Wait 0.4; Back")
    await tv_is("PBP(2) A2 [H2]G [H1]A")


@test("Home shows PIP when only one active")
async def _():
    await tv_do("Reset; S; Back; Wait 0.4; S; Back; Wait 0.4; Back")
    await tv_is("FULL A2 H2")
    await tv_do("Home")
    await tv_is("PIP(NE) A2 H2 [H1]A")


@test("Home")
async def _():
    await tv_do("Reset; Remote; Wait 0.3; Home; Wait 1")


@test("Home Right Down Left Up")
async def _():
    await tv_do("Reset; Remote; Wait 0.3")
    await tv_do(
        "Home; Wait 1; Home; Wait 1; Right; Wait 1; Down; Wait 1; Left; Wait 1; "
        "Up; Wait 1"
    )


@test("Play_pause")
async def _():
    await tv_do("Reset; Remote; Wait 0.3; Play_pause; Wait 2; Play_pause")


@test("Screensaver")
async def _():
    await tv_do("Reset; Screensaver")
    await tv_is("QUAD(2) A1 [H1]G [H2]A [H3]A [H4]A")


@test("Volume")
async def _():
    await tv_do("Reset")
    await vol_is("V+0")
    await tv_do("Volume_up")
    await vol_is("V+1")
    await tv_do("Volume_down")
    await vol_is("V+0")
    await tv_do("Volume_down")
    await vol_is("V-1")


@test("Mute")
async def _():
    await tv_do("Reset; Mute")
    await vol_is("M")
    await tv_do("Mute")
    await vol_is("V+0")


@test("Mute + Volume_up")
async def _():
    await tv_do("Reset; Volume_up; Mute; Volume_up")
    await vol_is("V+2")


@test("Volume is adjusted when switching TVs")
async def _():
    await tv_do("Reset; Volume_up; N")
    await vol_is("V+0")
    await tv_do("W")
    await vol_is("V+1")


@test("Volume is adjusted when switching TVs")
async def _():
    await tv_do("Reset; Volume_up; E; Volume_down")
    await vol_is("V-1")


@test("Mute is preserved when switching TVs")
async def _():
    await tv_do("Reset; Volume_up; Mute; N")
    await vol_is("M")
    await tv_do("Mute")
    await vol_is("V+0")
    await tv_do("W")
    await vol_is("V+1")


@test("Remote double tap")
async def _():
    await tv_do("Reset; Remote; Remote", "1")
    await tv_do("E; Remote; Remote", "3")


@test("Info")
async def _():
    await tv_do("Reset; Info", '"QUAD(2) A1 [H1]G [H2]A [H3]A [H4]A V+0"')


@test("Power")
async def _():
    # We do a state change before turning off to make sure it is preserved.
    # We do a state change after turning on to make sure that we can.
    await tv_do("Reset; E; Power; Wait 10; Power; S")
    await tv_is("QUAD(2) A4 [H1]A [H2]A [H3]A [H4]G")


async def main():
    global _the_mv
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    the_mv = await mv.create()
    _the_mv = the_mv
    # mv.save(mv, Path("TEST_MV.json").resolve())
    the_mv.jtech_manager.should_send_commands_to_device = False
    await mv.power_on(the_mv)
    await run(parse_selection(arg))
    await mv.shutdown(the_mv)


aio.run_event_loop(main())
