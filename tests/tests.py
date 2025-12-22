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
_mismatch_count = 0


def the_mv() -> Multiviewer:
    if _the_mv is None:
        fail("did not set the_mv")
    return _the_mv


def expect(actual, expected, frame_index=2):
    global _mismatch_count
    if actual != expected:
        _mismatch_count += 1
        frame = inspect.stack()[frame_index]
        lineno = frame.lineno
        print(f"State mismatch at line {lineno}:\n EXPECT: {expected}\n ACTUAL: {actual}")


async def tv_do(s, e=None):
    if False:
        debug_print(s)
    commands = [part.split() for part in s.split(";") if part.strip()]
    last = None
    for parts in commands:
        mv_obj = the_mv()
        if False:
            debug_print(parts)
        if parts[0] == "Double":
            if len(parts) < 2:
                fail("Double command requires an inner command")
            result = None
            for _ in range(2):
                result = await mv.do_command_and_update_devices(mv_obj, parts[1:])
            last = json.dumps(result)
            mv.advance_clock(mv_obj, 1.0)
        else:
            j = await mv.do_command_and_update_devices(mv_obj, parts)
            last = json.dumps(j)
            mv.advance_clock(mv_obj, 1.0)
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
    global _mismatch_count
    total = passed = 0
    _mismatch_count = 0
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
    print(f"{_mismatch_count} expectation mismatches")


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
    await tv_do("Reset; Home; Select; Back")
    await tv_is("QUAD(1) A1 [H1]G [H2]A [H3]A [H4]A")


@test("Select+Back preserves audio")
async def _():
    await tv_do("Reset; Select; E; Back")
    await tv_is("QUAD(2) A2 [H2]G [H1]A [H3]A [H4]A")


@test("Back to prominent swaps selected TV into W1")
async def _():
    await tv_do("Reset; Select; E; Back")
    await tv_is("QUAD(2) A2 [H2]G [H1]A [H3]A [H4]A")


@test("Home to W1 prominent swaps selected TV into W1")
async def _():
    await tv_do("Reset; Home")
    await tv_do("E")
    await tv_do("Home")
    await tv_is("QUAD(2) A2 [H2]G [H1]A [H3]A [H4]A")


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
    await tv_do("Reset; Home; E")
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
    await tv_is("QUAD(2) A3 [H3]G [H2]A [H1]A [H4]A")


@test("PIP from FULL after rotating")
async def _():
    await tv_do("Reset; Select; E; Home")
    await tv_is("PIP(NE) A2 H2 [H3]A")


@test("Select PIP window and go Back")
async def _():
    await tv_do("Reset; Select; Home; N")
    await tv_is("PIP(NE) A2 H1 [H2]G")
    await tv_do("Back")
    await tv_is("QUAD(2) A2 [H2]G [H1]A [H3]A [H4]A")


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


@test("Change PIP location from full")
async def _():
    await tv_do("Reset; Select; Home")
    await tv_is("PIP(NE) A1 H1 [H2]A")
    await tv_do("Double W")
    await tv_is("PIP(NW) A1 H1 [H2]A")
    await tv_do("Double S")
    await tv_is("PIP(SW) A1 H1 [H2]A")
    await tv_do("Double E")
    await tv_is("PIP(SE) A1 H1 [H2]A")
    await tv_do("Double N")
    await tv_is("PIP(NE) A1 H1 [H2]A")


@test("Change PIP location from PIP")
async def _():
    await tv_do("Reset; Select; Home; N")
    await tv_do("Double W")
    await tv_is("PIP(NW) A2 H1 [H2]G")
    await tv_do("Double S")
    await tv_is("PIP(SW) A2 H1 [H2]G")
    await tv_do("Double E")
    await tv_is("PIP(SE) A2 H1 [H2]G")
    await tv_do("Double N")
    await tv_is("PIP(NE) A2 H1 [H2]G")
    await tv_do("Double S")
    await tv_is("PIP(SE) A2 H1 [H2]G")
    await tv_do("Double W")
    await tv_is("PIP(SW) A2 H1 [H2]G")
    await tv_do("Double N")
    await tv_is("PIP(NW) A2 H1 [H2]G")
    await tv_do("Double E")
    await tv_is("PIP(NE) A2 H1 [H2]G")


@test("PIP location follows TV")
async def _():
    await tv_do("Reset; Select; Home; Double W")
    await tv_is("PIP(NW) A1 H1 [H2]A")
    await tv_do("Select")
    await tv_is("PIP(NE) A2 H2 [H1]A")
    await tv_do("Double S")
    await tv_is("PIP(SE) A2 H2 [H1]A")
    await tv_do("Select")
    await tv_is("PIP(NW) A1 H1 [H2]A")


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


@test("Rotate PIP window when PIP selected")
async def _():
    await tv_do("Reset; Select; Home; N")
    await tv_is("PIP(NE) A2 H1 [H2]G")
    await tv_do("E")
    await tv_is("PIP(NE) A3 H1 [H3]G")
    await tv_do("W")
    await tv_is("PIP(NE) A2 H1 [H2]G")


@test("Back exits fullscreen PIP")
async def _():
    await tv_do("Reset; Select; Home; Back")
    await tv_is("QUAD(2) A1 [H1]G [H2]A [H3]A [H4]A")


@test("Home toggles PIP off")
async def _():
    await tv_do("Reset; Select; Home; Home")
    await tv_is("FULL A1 H1")


@test("Home selects full window when leaving PIP")
async def _():
    await tv_do("Reset; Select; Home")
    await tv_is("PIP(NE) A1 H1 [H2]A")
    await tv_do("N")
    await tv_is("PIP(NE) A2 H1 [H2]G")
    await tv_do("Home")
    await tv_is("FULL A1 H1")


@test("Home does nothing when only one active")
async def _():
    await tv_do("Reset; S; Deactivate_tv; S; Deactivate_tv; Deactivate_tv")
    await tv_is("FULL A2 H2")
    await tv_do("Home")
    await tv_is("FULL A2 H2")


@test("Deactivate_tv removes window")
async def _():
    await tv_do("Reset; S; Deactivate_tv")
    await tv_is("TRIPLE(2) A1 [H1]G [H2]A [H3]A")
    await tv_do("S; Deactivate_tv")
    await tv_is("PBP(2) A1 [H1]G [H2]A")
    await tv_do("Deactivate_tv")
    await tv_is("FULL A2 H2")


@test("Deactivate_tv keeps selected window visible in FULL")
async def _():
    await tv_do("Reset; S; Select")
    await tv_is("FULL A4 H4")
    await tv_do("Deactivate_tv")
    await tv_is("FULL A1 H1")


@test("Deactivate_tv preserves submode")
async def _():
    await tv_do("Reset; Home; S; Deactivate_tv")
    await tv_is("TRIPLE(1) A1 [H1]G [H2]A [H4]A")


@test("Deactivate_tv switches selected window to W1")
async def _():
    await tv_do("Reset; S; Deactivate_tv")
    await tv_is("TRIPLE(2) A1 [H1]G [H2]A [H3]A")


@test("Triple Right points to W2")
async def _():
    await tv_do("Reset; S; Deactivate_tv; E")
    await tv_is("TRIPLE(2) A2 [H1]A [H2]G [H3]A")


@test("Activate_tv adds window")
async def _():
    await tv_do("Reset; S; Deactivate_tv; S; Deactivate_tv")
    await tv_is("PBP(2) A1 [H1]G [H2]A")
    await tv_do("Activate_tv")
    await tv_is("TRIPLE(2) A1 [H1]G [H2]A [H3]A")
    await tv_do("Activate_tv")
    await tv_is("QUAD(2) A1 [H1]G [H2]A [H3]A [H4]A")


@test("Activate_tv in FULL enables cycling")
async def _():
    await tv_do("Reset; Deactivate_tv; Deactivate_tv; Deactivate_tv")
    await tv_is("FULL A4 H4")
    await tv_do("Activate_tv")
    await tv_is("FULL A4 H4")
    await tv_do("E")
    await tv_is("FULL A3 H3")


@test("Activate_tv in PIP enables cycling")
async def _():
    await tv_do("Reset; Deactivate_tv; Deactivate_tv")
    await tv_is("PBP(2) A3 [H3]G [H4]A")
    await tv_do("Select; Home")
    await tv_is("PIP(NE) A3 H3 [H4]A")
    await tv_do("Activate_tv")
    await tv_is("PIP(NE) A3 H3 [H4]A")
    await tv_do("E")
    await tv_is("PIP(NE) A3 H3 [H2]A")


@test("Adding and removing windows preserve submode")
async def _():
    await tv_do("Reset; Home; S; Deactivate_tv")
    await tv_is("TRIPLE(1) A1 [H1]G [H2]A [H4]A")
    await tv_do("Home; Activate_tv; Activate_tv")
    await tv_is("QUAD(2) A1 [H1]G [H2]A [H4]A [H3]A")


@test("Deactivate_tv demotes window")
async def _():
    await tv_do("Reset; Deactivate_tv")
    await tv_is("TRIPLE(2) A2 [H2]G [H3]A [H4]A")


@test("Deactivate_tv places next inactive first when not in screensaver")
async def _():
    await tv_do("Reset; Deactivate_tv; Deactivate_tv; Activate_tv")
    await tv_is("TRIPLE(2) A3 [H3]G [H4]A [H2]A")


@test("Deactivate_tv places next inactive last when in screensaver")
async def _():
    await tv_do("Reset; Deactivate_tv; Remote; Screensaver; Deactivate_tv; Activate_tv")
    await tv_is("TRIPLE(2) A3 [H3]G [H4]A [H1]A")


@test("Back activates a TV when only one active")
async def _():
    await tv_do("Reset; S; Deactivate_tv; S; Deactivate_tv; Deactivate_tv")
    await tv_is("FULL A2 H2")
    await tv_do("Back")
    await tv_is("PBP(2) A2 [H2]G [H1]A")


@test("Home")
async def _():
    await tv_do("Reset; Remote; Home")


@test("Home Right Down Left Up")
async def _():
    await tv_do("Reset; Remote")
    await tv_do("Home; Home; Right; Down; Left; Up")


@test("Play_pause")
async def _():
    await tv_do("Reset; Remote; Play_pause; Play_pause")


@test("Screensaver")
async def _():
    await tv_do("Reset; Screensaver")
    await tv_is("QUAD(2) A1 [H1]G [H2]A [H3]A [H4]A")
    await tv_do("Remote")
    await tv_do("Screensaver")
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
    await tv_do("Reset; Double Remote", "1")
    await tv_do("E; Double Remote", "3")


@test("Remote single tap returns nothing")
async def _():
    await tv_do("Reset; Remote", "{}")


@test("Info")
async def _():
    await tv_do("Reset; Info", '"QUAD(2) A1 [H1]G [H2]A [H3]A [H4]A V+0"')


@test("Power")
async def _():
    # We do a state change before turning off to make sure it is preserved.
    # We do a state change after turning on to make sure that we can.
    await tv_do("Reset; E; Power; Power; S")
    await tv_is("QUAD(2) A4 [H1]A [H2]A [H3]A [H4]G")


async def main():
    global _the_mv
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    the_mv = await mv.create()
    _the_mv = the_mv
    mv.use_virtual_clock(the_mv)
    # mv.save(mv, Path("TEST_MV.json").resolve())
    mv.set_should_send_commands_to_device(the_mv, False)
    await mv.power_on(the_mv)
    await run(parse_selection(arg))
    await mv.shutdown(the_mv)


aio.run_event_loop(main())
