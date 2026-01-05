# Standard library
import dataclasses

# Local package
from . import aio, json_field
from .aio import Event, Task
from .base import *
from .jtech import Jtech, Power
from .jtech_output import JtechOutput


@dataclass(slots=True)
class JtechManager:
    should_send_commands_to_device: bool = False
    desired_power: Power | None = None
    desired_output: JtechOutput | None = None
    jtech: Jtech = Jtech.field()
    jtech_output: JtechOutput | None = None
    desynced_event: Event = Event.field()
    synced_event: Event = Event.field()
    # A background task that is constantly trying to make the jtech match desired_power
    # and desired_output.
    task: Task[None] = Task.field()

    @classmethod
    def field(cls):
        return dataclasses.field(default_factory=JtechManager, metadata=json_field.omit)

    def __post_init__(self) -> None:
        self.task = Task[None].create(type(self).__name__, self.sync_forever())

    async def synced(self) -> None:
        await self.synced_event.wait()

    def desync(self):
        self.desynced_event.set()
        self.synced_event.clear()

    async def current_power(self) -> Power:
        await self.synced()
        assert self.desired_power is not None
        return self.desired_power

    async def current_output(self) -> JtechOutput:
        await self.synced()
        assert self.desired_output is not None
        return self.desired_output

    def set_power(self, desired_power: Power) -> None:
        if desired_power != self.desired_power:
            self.desired_power = desired_power
            self.desync()

    def set_output(self, desired_output: JtechOutput) -> None:
        if desired_output != self.desired_output:
            self.desired_output = desired_output
            self.desync()

    def power_on(self) -> None:
        self.set_power(Power.ON)

    def power_off(self) -> None:
        self.set_power(Power.OFF)

    def set_should_send_commands_to_device(self, b: bool) -> None:
        if self.should_send_commands_to_device != b:
            self.should_send_commands_to_device = b
            self.desync()

    def should_abort(self) -> bool:
        return self.desynced_event.is_set()

    # sync returns True iff it finished successfully.
    async def sync(self) -> bool:
        if False:
            debug_print(self)
        if not self.should_send_commands_to_device or self.desired_power is None:
            return True
        jtech = self.jtech
        await jtech.set_power(self.desired_power)
        if self.desired_power == Power.OFF:
            return True
        if self.should_abort():
            return False
        desired_output = self.desired_output
        if desired_output is None:
            return True
        log(f"setting jtech output: {desired_output}")
        if await desired_output.set(jtech, self.should_abort):
            log("set jtech output finished")
        else:
            log("set jtech output aborted")
            return False
        # We'd like to check whether desired_output.set worked, so we JtechOutput.read
        # and compare. But first, we wait a bit, because if we don't, the jtech sometimes
        # lies.
        await aio.wait_for(self.desynced_event.wait(), timeout=1)
        if self.should_abort():
            return False
        log("reading jtech output")
        self.jtech_output = await JtechOutput.read(jtech, self.should_abort)
        if self.jtech_output is None:
            log("read jtech output aborted")
            return False
        else:
            log(f"read jtech output: {self.jtech_output}")
            is_synced = self.jtech_output == desired_output
            if not is_synced:
                log("jtech output mismatch")
            if is_synced:
                await jtech.unmute(force=True)
            return is_synced

    # The call to self.sync in sync_forever is the only code that sends commands to the
    # device.  That ensures sequential communication.
    async def sync_forever(self) -> NoReturn:
        while True:  # Loop forever
            try:
                self.desynced_event.clear()
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
