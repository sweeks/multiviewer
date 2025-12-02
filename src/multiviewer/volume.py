from __future__ import annotations

# Standard library
import dataclasses

# Local package
from . import wf2ir
from .aio import Event, Task
from .base import *

@dataclass_json
@dataclass
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
        self.worker_task = Task.create(type(self).__name__, self.worker())

    def is_synced(self) -> bool:
        if self.current_mute != self.desired_mute:
            return False
        if self.current_mute:
            return True
        return self.current_volume_delta == self.desired_volume_delta

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
        
    async def worker(self):
        while True:
            # We loop, breaking out iff we are synced, and at each iteration making one
            # (async) wf2ir call and then immediately looping, so that we reconsider
            # the latest desired state, which may have changed during the wf2ir call.
            while True: 
                if self.current_mute != self.desired_mute:
                    self.current_mute = self.desired_mute
                    await wf2ir.mute()
                    continue
                if self.current_mute:
                    break
                diff = self.desired_volume_delta - self.current_volume_delta
                if diff == 0:
                    break
                if diff > 0:
                    self.current_volume_delta += 1
                    await wf2ir.volume_up()
                    continue
                else:
                    self.current_volume_delta -= 1
                    await wf2ir.volume_down()
                    continue
            assert(self.is_synced())
            self.synced_event.set()
            await self.wake_event.wait()
            self.wake_event.clear()

    def reset(self):
        self.current_mute = False
        self.desired_mute = False
        self.current_volume_delta = 0
        self.desired_volume_delta = 0