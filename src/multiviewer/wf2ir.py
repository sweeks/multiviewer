from __future__ import annotations

# Standard library
import socket
import time

# Local package
from . import aio, config
from .base import *

IR_VOLUME_UP = (
    "sendir,1:3,1,37878,1,1,"  # repeat=1, offset=1 (repeat starts at pair 1)
    "171,170,22,21,22,21,22,63,22,63,22,21,22,63,22,21,22,21,22,21,22,21,"
    "22,63,22,63,22,21,22,63,22,21,22,21,22,63,22,63,22,63,22,21,22,63,22,21,22,21,22,21,22,21,"
    "22,21,22,21,22,63,22,21,22,63,22,63,22,63,22,1779,"  # ← frame 1 (ends with long gap)
    "171,170,22,63,22,3650\r"  # ← single repeat frame
)

IR_VOLUME_DOWN = (
    "sendir,1:3,1,37878,1,1,"
    "171,170,22,21,22,21,22,63,22,63,22,21,22,63,22,21,22,21,22,21,22,21,"
    "22,63,22,63,22,21,22,63,22,21,22,21,22,21,22,63,22,63,22,21,22,63,22,21,22,21,22,21,22,63,"
    "22,21,22,21,22,63,22,21,22,63,22,63,22,63,22,1778,"
    "171,170,22,63,22,3648\r"
)

IR_MUTE = (
    "sendir,1:3,1,37878,1,1,171,170,22,21,22,21,22,63,22,63,22,21,22,63,22,21,22,21,22,21,22,21,"
    "22,63,22,63,22,21,22,63,22,21,22,21,22,63,22,63,22,63,22,63,22,63,22,21,22,21,22,21,22,21,"
    "22,21,22,21,22,21,22,21,22,63,22,63,22,63,22,1779,171,170,22,63,22,3651,171,170,22,63,22,4848\r"
)


def create_connection():
    return socket.create_connection((config.WF2IR_HOST, config.WF2IR_PORT), timeout=5)


def send(s, text):
    s.sendall(text.encode())


def recv(s):
    return s.recv(4096).decode().strip()


def learn():
    with create_connection() as s:
        send(s, "get_IRL,1:1\r")
        print(recv(s))
        print("Aim at top hole, 2–4 inches away. Press key once.")
        time.sleep(10)
        send(s, "stop_IRL,1:1\r")
        print(recv(s))


async def command(text) -> None:
    if RunMode.get() == RunMode.Testing:
        return
    else:
        reader, writer = await aio.open_connection(config.WF2IR_HOST, config.WF2IR_PORT)
        try:
            writer.write(text.encode("ascii"))
            await writer.drain()
            await reader.readuntil(b"\r")
            # data.decode("ascii", errors="strict").strip()
        finally:
            writer.close()
            await writer.wait_closed()
            # We sleep a bit to make the IR more reliable.
            await aio.sleep(0.25)


async def volume_up():
    await command(IR_VOLUME_UP)


async def volume_down():
    await command(IR_VOLUME_DOWN)


async def mute():
    await command(IR_MUTE)
