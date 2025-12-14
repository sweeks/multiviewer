"""
Multiviewer main interface.  This module maintains all the state of the multiviewer and
the objects for controlling the J-Tech, Apple TVs, and Soundbar.  The state includes


  window layouts,
  audio

and
has functions to load and save it from disk, update the jtech output based on changes to
inputs, and do commands from the user.
"""

# Standard library
from pathlib import Path

# Local package
from .base import *
from .jtech_manager import JtechManager

class Power:
    ON: Power
    OFF: Power

class Multiviewer:
    def __init__(self) -> NoReturn:
        """Undefined. Use create()"""
    jtech_manager: JtechManager

async def create() -> Multiviewer: ...
async def shutdown(mv: Multiviewer) -> None: ...
async def load(p: Path) -> Multiviewer: ...
def save(mv: Multiviewer, p: Path) -> None: ...
def update_jtech_output(mv: Multiviewer): ...
def set_should_send_commands_to_device(mv: Multiviewer, b: bool) -> None: ...
async def do_command_and_update_jtech_output(
    mv: Multiviewer, args: list[str]
) -> JSON: ...
async def describe_jtech_output(mv: Multiviewer) -> str: ...
def describe_volume(mv: Multiviewer) -> str: ...
def power(mv: Multiviewer) -> Power: ...
async def power_on(mv: Multiviewer) -> None: ...
async def synced(mv: Multiviewer) -> None: ...
