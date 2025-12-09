from __future__ import annotations

# Standard library
import dataclasses

# Local package
from . import wf2ir
from .aio import Event, Task
from .base import *


@dataclass_json
@dataclass(slots=True)
class Volume:
    current_mute: bool = False
    desired_mute: bool = False
    current_volume_delta: int = 0
    desired_volume_delta: int = 0
    synced_event: Event = Event.field()
    wake_event: Event = Event.field()
    worker_task: Task = Task.field()

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
