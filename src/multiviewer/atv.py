# atv.py — persistent Apple TV control with synchronous API

# Standard library
from asyncio import Queue, Task

import dataclasses
import time

# Third-party
import pyatv

from pyatv.interface import AppleTV
from pyatv.storage.file_storage import FileStorage

# Local package
from .base import *
from . import aio
from . import config
from . import json_field


class TV(MyStrEnum):
    TV1 = auto()
    TV2 = auto()
    TV3 = auto()
    TV4 = auto()


TV1 = TV.TV1
TV2 = TV.TV2
TV3 = TV.TV3
TV4 = TV.TV4

attach_int(TV, {TV1: 1, TV2: 2, TV3: 3, TV4: 4})


def validate_tv(x) -> None:
    if not (isinstance(x, TV)):
        fail("not a TV", x)


tv_ips = {
    TV1: config.TV1_IP,
    TV2: config.TV2_IP,
    TV3: config.TV3_IP,
    TV4: config.TV4_IP,
}


@dataclass(slots=True)
class _ATV:
    tv: TV
    appleTV: AppleTV | None = None

    async def connect(self) -> AppleTV:
        tv = self.tv
        if False:
            debug_print(tv)
        t0 = time.perf_counter()
        storage = FileStorage.default_storage(aio.event_loop)
        await storage.load()
        devices = await pyatv.scan(aio.event_loop, hosts=[tv_ips[tv]], storage=storage)
        if not devices:
            fail(f"could not connect to {tv}")
        appleTV = await pyatv.connect(devices[0], aio.event_loop, storage=storage)
        appleTV.push_updater.stop()
        self.appleTV = appleTV
        ms = int((time.perf_counter() - t0) * 1000)
        log(f"connected to {tv} ({ms}ms)")
        return appleTV

    async def get_appleTV(self) -> AppleTV:
        if self.appleTV is not None:
            return self.appleTV
        return await self.connect()

    async def close(self) -> None:
        if self.appleTV is not None:
            appleTV = self.appleTV
            self.appleTV = None
            await aio.gather(*(appleTV.close()))

    async def do_command(self, command: str, args: list[str]):
        appleTV = await self.get_appleTV()
        await getattr(appleTV.remote_control, command)(*args)

    async def home(self):
        await self.do_command("home", [])

    async def down(self):
        await self.do_command("down", [])

    async def launch_url(self, url):
        await self.do_command("launch_url", [url])

    async def left(self):
        await self.do_command("left", [])

    async def menu(self):
        await self.do_command("menu", [])

    async def next(self):
        await self.do_command("next", [])

    async def play_pause(self):
        await self.do_command("play_pause", [])

    async def previous(self):
        await self.do_command("previous", [])

    async def right(self):
        await self.do_command("right", [])

    async def select(self):
        await self.do_command("select", [])

    async def stop(self):
        await self.do_command("stop", [])

    async def top_menu(self):
        await self.do_command("top_menu", [])

    async def up(self):
        await self.do_command("up", [])

    async def volume_down(self):
        await self.do_command("volume_down", [])

    async def volume_up(self):
        await self.do_command("volume_up", [])

    async def screensaver(self) -> None:
        await self.home()
        await aio.sleep(2)
        await self.home()
        await aio.sleep(2)
        await self.menu()

    async def sleep(self) -> None:
        appleTV = await self.get_appleTV()
        await appleTV.power.turn_off()

    async def wake(self) -> None:
        appleTV = await self.get_appleTV()
        await appleTV.power.turn_on()
        await aio.sleep(8)
        await self.screensaver()

    async def launch(self, url: str) -> None:
        appleTV = await self.get_appleTV()
        await appleTV.apps.launch_app(url)
        await aio.sleep(2)
        await appleTV.remote_control.select()
        await appleTV.remote_control.select()


@dataclass(slots=True)
class ATV:
    atv: _ATV
    queue: Queue[Awaitable[None]] = field(default_factory=Queue, repr=False)
    task: Task = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.task = aio.Task.create(type(self).__name__, self.process_queue_forever())

    async def process_queue_forever(self) -> NoReturn:
        while True:
            job = await self.queue.get()
            if False:
                debug_print("dequeue", job)
            try:
                await job
            except Exception as e:
                log_exc(e)
                debug_print(self)
                await self.close()
            finally:
                self.queue.task_done()

    async def synced(self) -> None:
        await self.queue.join()

    async def close(self) -> None:
        await self.atv.close()

    def enqueue(self, a: Awaitable[None]) -> None:
        if False:
            debug_print("enqueue")
        self.queue.put_nowait(a)

    def down(self):
        self.enqueue(self.atv.down())

    def home(self):
        self.enqueue(self.atv.home())

    def launch(self, url):
        self.enqueue(self.atv.launch(url))

    def left(self):
        self.enqueue(self.atv.left())

    def menu(self):
        self.enqueue(self.atv.menu())

    def next(self):
        self.enqueue(self.atv.next())

    def play_pause(self):
        self.enqueue(self.atv.play_pause())

    def previous(self):
        self.enqueue(self.atv.previous())

    def right(self):
        self.enqueue(self.atv.right())

    def screensaver(self):
        self.enqueue(self.atv.screensaver())

    def select(self):
        self.enqueue(self.atv.select())

    def sleep(self):
        self.enqueue(self.atv.sleep())

    def stop(self):
        self.enqueue(self.atv.stop())

    def top_menu(self):
        self.enqueue(self.atv.top_menu())

    def up(self):
        self.enqueue(self.atv.up())

    def volume_down(self):
        self.enqueue(self.atv.volume_down())

    def volume_up(self):
        self.enqueue(self.atv.volume_up())

    def wake(self):
        self.enqueue(self.atv.wake())


@dataclass(slots=True)
class ATVs:
    by_tv: Dict[TV, ATV] = field(
        default_factory=lambda: {tv: ATV(_ATV(tv)) for tv in TV.all()}
    )

    @classmethod
    def field(cls):
        return dataclasses.field(default_factory=ATVs, metadata=json_field.omit)

    async def shutdown(self):
        await self.synced()
        await aio.gather(*(atv.close() for atv in self.by_tv.values()))

    def atv(self, tv):
        return self.by_tv[tv]

    async def synced(self) -> None:
        await aio.gather(*(atv.synced() for atv in self.by_tv.values()))
