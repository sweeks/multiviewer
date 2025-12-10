"""
Manage the jtech device, by continually syncing the desired power and output.
"""

# Local package
from .base import *
from .jtech import Power
from .jtech_output import JtechOutput


class JtechManager:
    @classmethod
    def field(cls) -> JtechManager: ...

    should_send_commands_to_device: bool
    """This determines whether we send commands and read responses from the physical jtech
    device (except for read_power and set_power). mvd uses True. Tests use True or False,
    depending on whether we just want to test our multiviewer logic.  When False, the
    below functions don't do anything, and current_power and current_output just return
    the last set value."""

    def set_power(self, desired_power: Power) -> None: ...
    def set_output(self, desired_output: JtechOutput) -> None: ...

    async def current_power(self) -> Power: ...
    async def current_output(self) -> JtechOutput: ...

    def synced(self) -> Awaitable[None]:
        """Wait until the jtech is synced to desired power and output."""
