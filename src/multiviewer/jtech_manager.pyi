"""
Manage the jtech device, by continually syncing the desired power and screen.
"""

# Local package
from .base import *
from .jtech import Jtech as DeviceJtech, Power
from .jtech_screen import Screen

class Jtech_manager:
    @classmethod 
    def field(cls) -> Jtech_manager: ...

    should_send_commands_to_device: bool
    """This determines whether we send commands and read responses from the physical jtech
    device. That is what we want in mvd, and sometimes in tests. But sometimes in tests,
    we just want to test our multiviewer logic, in which case, we set
    should_send_commands_to_device=False. In that case, the below functions don't do
    anything, and current_power and current_screen just return the last set value."""

    def set_power(self, desired_power: Power) -> None: ...
    def set_screen(self, desired_screen: Screen) -> None: ...

    def synced(self) -> Awaitable[None]:
        """Wait until the jtech is synced to desired power and screen."""

    async def current_power(self) -> Power: ...
    async def current_screen(self) -> Screen: ...
