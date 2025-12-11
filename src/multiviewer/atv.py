# atv.py — persistent Apple TV control with synchronous API

# Standard library
import dataclasses
import time
from asyncio import Queue, Task

# Third-party
import pyatv
from pyatv.interface import AppleTV
from pyatv.storage.file_storage import FileStorage

from . import aio, config, json_field

# Local package
from .base import *


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
class AtvConnection:
    tv: TV
    apple_tv: AppleTV | None = None

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
        apple_tv = await pyatv.connect(devices[0], aio.event_loop, storage=storage)
        apple_tv.push_updater.stop()
        self.apple_tv = apple_tv
        ms = int((time.perf_counter() - t0) * 1000)
        log(f"connected to {tv} ({ms}ms)")
        return apple_tv

    async def get_apple_tv(self) -> AppleTV:
        if self.apple_tv is not None:
            return self.apple_tv
        self.apple_tv = await self.connect()
        return self.apple_tv

    async def close(self) -> None:
        if self.apple_tv is not None:
            apple_tv = self.apple_tv
            self.apple_tv = None
            await aio.gather(*(apple_tv.close()))

    async def do_command(self, command: str, args: list[str]):
        apple_tv = await self.get_apple_tv()
        await getattr(apple_tv.remote_control, command)(*args)

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
        apple_tv = await self.get_apple_tv()
        await apple_tv.power.turn_off()

    async def wake(self) -> None:
        apple_tv = await self.get_apple_tv()
        await apple_tv.power.turn_on()
        await aio.sleep(8)
        await self.screensaver()

    async def launch(self, url: str) -> None:
        apple_tv = await self.get_apple_tv()
        await apple_tv.apps.launch_app(url)
        await aio.sleep(2)
        await apple_tv.remote_control.select()
        await apple_tv.remote_control.select()


@dataclass(slots=True)
class ATV:
    atv: AtvConnection
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
        default_factory=lambda: {tv: ATV(AtvConnection(tv)) for tv in TV.all()}
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
