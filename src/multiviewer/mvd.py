from __future__ import annotations

# Standard library
import os
import signal
import subprocess
import time
from pathlib import Path

from . import aio, http_server, mv

# Local package
from .base import *


async def stop_running_daemon() -> None:
    try:
        out = (
            subprocess.check_output(["lsof", "-ti", f"tcp:{http_server.HTTP_PORT}"])
            .decode()
            .split()
        )
        for pid in out:
            if pid:
                log(f"stopping mvd {pid}")
                os.kill(int(pid), signal.SIGTERM)
                await aio.sleep(1)  # Give the old mvd a second to shutdown
    except subprocess.CalledProcessError:
        pass  # no process using that port


async def become_daemon():
    RunMode.set(RunMode.Daemon)
    log("daemon starting")
    try:
        await stop_running_daemon()
    except Exception as e:
        log_exc(e)
    mvd_state_path = Path("state.json").resolve()
    the_mv = await mv.load(mvd_state_path)
    mv.update_jtech_output(the_mv)

    async def run_command(args):
        if False:
            debug_print(args)
        if True:
            log(f"{args}")
        t0 = time.perf_counter()
        try:
            return await mv.do_command_and_update_jtech_output(the_mv, args)
        except Exception as e:
            log_exc(e)
        finally:
            dt = (time.perf_counter() - t0) * 1000
            log(f"{args} finished in {dt:.1f}ms")

    server = http_server.serve_until_stopped(run_command)
    stop_event = aio.Event()

    def handle_sigterm(signum, frame):
        log("daemon stopping")
        aio.event_loop.call_soon_threadsafe(stop_event.set)

    signal.signal(signal.SIGTERM, handle_sigterm)
    await stop_event.wait()
    http_server.stop(server)
    mv.save(the_mv, mvd_state_path)
    await mv.shutdown(the_mv)
    log("daemon stopped")
