# Standard library
import dataclasses

# Local package
from . import aio
from . import json_field
from .aio import Event, Task
from .base import *
from .jtech import Jtech, Mute, Power
from .jtech_screen import Screen


@dataclass(slots=True)
class Jtech_manager:
    should_send_commands_to_device: bool = True
    desired_power: Power | None = None
    desired_screen: Screen | None = None
    jtech: Jtech = Jtech.field()
    jtech_screen: Screen | None = None
    desynced_event: Event = Event.field()
    synced_event: Event = Event.field()
    # A background task that is constantly trying to make the jtech match desired_power
    # and desired_screen.
    task: Task = Task.field()

    @classmethod
    def field(cls):
        return dataclasses.field(
            default_factory=Jtech_manager, metadata=json_field.omit
        )

    def __post_init__(self) -> None:
        self.task = aio.Task.create(type(self).__name__, self.sync_forever())

    async def synced(self) -> None:
        await self.synced_event.wait()

    def desync(self):
        self.desynced_event.set()
        self.synced_event.clear()

    async def current_power(self) -> Power:
        await self.synced()
        return await self.jtech.read_power()

    async def current_screen(self) -> Screen:
        await self.synced()
        assert self.desired_screen is not None
        return self.desired_screen

    def set_power(self, desired_power: Power) -> None:
        if desired_power != self.desired_power:
            if False:
                debug_print(desired_power)
            self.desired_power = desired_power
            self.desync()

    def set_screen(self, desired_screen: Screen) -> None:
        if desired_screen != self.desired_screen:
            if False:
                debug_print(desired_screen)
            self.desired_screen = desired_screen
            self.desync()

    # sync returns True iff it finished successfully.
    async def sync(self) -> bool:
        if False:
            debug_print(self)

        def should_abort() -> bool:
            return self.desynced_event.is_set()

        jtech = self.jtech
        if self.desired_power is None:
            return True
        await jtech.set_power(self.desired_power)
        if self.desired_power == Power.OFF:
            return True
        await jtech.unmute()
        if should_abort():
            return False
        desired_screen = self.desired_screen
        if desired_screen is None:
            return True
        log(f"setting screen: {desired_screen}")
        set_screen_finished = await desired_screen.set_jtech(jtech, should_abort)
        if set_screen_finished:
            log("set screen finished")
        else:
            log("set screen aborted")
            return False
        # We'd like to check whether device.set_screen worked, so we device.read_screen
        # and compare. But first, we wait a bit, because if we don't, the jtech sometimes
        # lies.
        await aio.wait_for(self.desynced_event.wait(), timeout=1)
        if should_abort():
            return False
        log("reading screen")
        self.jtech_screen = await Screen.read_jtech(jtech, should_abort)
        if self.jtech_screen is None:
            log("read screen aborted")
            return False
        else:
            log(f"read screen: {self.jtech_screen}")
            is_synced = self.jtech_screen == desired_screen
            if not is_synced:
                log(f"screen mismatch")
            return is_synced

    # The call to self.sync in sync_forever is the only code that sends commands to the
    # device.  That ensures sequential communication.
    async def sync_forever(self):
        while True:  # Loop forever
            try:
                self.desynced_event.clear()
                if not self.should_send_commands_to_device:
                    is_synced = True
                else:
                    is_synced = await aio.wait_for(self.sync(), timeout=10)
                    if is_synced is None:
                        fail("sync timeout")
                if is_synced and not self.desynced_event.is_set():
                    self.synced_event.set()
                    await self.desynced_event.wait()
            except Exception as e:
                log_exc(e)
                if RunMode.get() == RunMode.Daemon:
                    debug_print(self)
                await self.jtech.reset()
