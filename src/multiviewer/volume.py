from __future__ import annotations

# Standard library
import dataclasses

# Local package
from . import wf2ir
from .aio import Event, Task
from .base import *
from .json_field import json_dict
from .tv import TV


@dataclass_json
@dataclass(slots=True)
class Volume:
    should_send_commands_to_device: bool = False
    current_mute: bool = False
    desired_mute: bool = False
    current_volume_delta: int = 0
    desired_volume_delta: int = 0
    synced_event: Event = Event.field()
    wake_event: Event = Event.field()
    worker_task: Task[None] = Task.field()
    volume_delta_by_tv: dict[TV, int] = dataclasses.field(
        default_factory=lambda: dict.fromkeys(TV.all(), 0),
        metadata=json_dict(TV, int),
    )

    @classmethod
    def field(cls):
        return dataclasses.field(default_factory=Volume)

    def __post_init__(self) -> None:
        self.worker_task = Task.create(type(self).__name__, self.sync_forever())

    def describe_volume(self) -> str:
        if self.current_mute:
            return "M"
        elif self.current_volume_delta >= 0:
            return f"V+{self.current_volume_delta}"
        else:
            return f"V{self.current_volume_delta}"

    async def synced(self) -> None:
        await self.synced_event.wait()

    def wake_worker(self) -> None:
        self.wake_event.set()
        self.synced_event.clear()

    def set_volume_delta(self, to: int) -> None:
        self.desired_volume_delta = to
        self.wake_worker()

    def toggle_mute(self) -> None:
        self.desired_mute = not self.desired_mute
        self.wake_worker()

    def unmute(self) -> None:
        self.desired_mute = False
        self.wake_worker()

    def is_synced(self) -> bool:
        return self.current_mute == self.desired_mute and (
            self.current_mute or self.desired_volume_delta == self.current_volume_delta
        )

    async def sync(self) -> None:
        if not self.should_send_commands_to_device:
            # In test mode, just mirror desired state locally.
            self.current_mute = self.desired_mute
            self.current_volume_delta = self.desired_volume_delta
            return
        if self.current_mute != self.desired_mute:
            self.current_mute = self.desired_mute
            await wf2ir.mute()
            return
        if self.current_mute:
            return
        diff = self.desired_volume_delta - self.current_volume_delta
        if diff == 0:
            return
        if diff > 0:
            self.current_volume_delta += 1
            await wf2ir.volume_up()
            return
        else:
            self.current_volume_delta -= 1
            await wf2ir.volume_down()
            return

    async def sync_forever(self):
        while True:
            if self.is_synced():
                self.synced_event.set()
                self.wake_event.clear()
                await self.wake_event.wait()
                continue
            try:
                await self.sync()
            except Exception as e:
                log_exc(e)

    def reset(self):
        self.current_mute = False
        self.desired_mute = False
        self.current_volume_delta = 0
        self.desired_volume_delta = 0
        self.volume_delta_by_tv = dict.fromkeys(TV.all(), 0)

    def power_on(self) -> None:
        # We reset all the volume deltas to zero, because this is a new TV session for the
        # user.  This causes the initial update_jtech_output to set the desired
        # volume_delta to zero, which in turn causes the Volume manager to set the actual
        # volume_delta to zero.
        self.reset()

    def set_should_send_commands_to_device(self, b: bool) -> None:
        self.should_send_commands_to_device = b

    def adjust_volume(self, tv: TV, by: int) -> None:
        self.unmute()
        self.volume_delta_by_tv[tv] += by

    def set_for_tv(self, tv: TV) -> None:
        self.set_volume_delta(self.volume_delta_by_tv[tv])

    def volume_delta_for(self, tv: TV) -> int:
        return self.volume_delta_by_tv[tv]
