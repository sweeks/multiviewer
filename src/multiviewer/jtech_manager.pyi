from .base import *
from .jtech import Power, Screen

class Jtech:
    @classmethod 
    def field(cls) -> Jtech: ...

    should_send_commands_to_device: bool
    # This determines whether we send commands and read responses from the physical jtech
    # device.  That is what we want in mvd, and sometimes in tests. But sometimes in
    # tests, we just want to test our multiviewer logic, in which case, we set
    # should_send_commands_to_device=False. In that case, the below functions don't do
    # anything, and current_power and current_screen just return the last set value.

    async def current_power(self) -> Power: ...
    def set_power(self, p: Power) -> None: ...

    async def current_screen(self) -> Screen: ...
    def set_screen(self, s: Screen) -> None: ...

    def synced(self) -> Awaitable[None]: ...
