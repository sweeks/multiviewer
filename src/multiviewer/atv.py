# atv.py — persistent Apple TV control with synchronous API

# Standard library
import asyncio
import dataclasses
import time
from asyncio import Queue
from typing import cast

# Third-party
import pyatv
from pyatv.interface import AppleTV
from pyatv.storage.file_storage import FileStorage

from . import aio, config, json_field
from .aio import Task

# Local package
from .base import *
from .tv import TV

tv_ips = {
    TV.TV1: config.TV1_IP,
    TV.TV2: config.TV2_IP,
    TV.TV3: config.TV3_IP,
    TV.TV4: config.TV4_IP,
}


@dataclass(slots=True)
class AtvConnection:
    tv: TV
    should_send_commands_to_device: bool = False
    apple_tv: AppleTV | None = None

    async def connect(self) -> AppleTV:
        tv = self.tv
        if False:
            debug_print(tv)
        if not self.should_send_commands_to_device:
            fail("connect should not be called when commands are disabled")
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
        if not self.should_send_commands_to_device:
            self.apple_tv = None
            return
        if self.apple_tv is not None:
            apple_tv = self.apple_tv
            self.apple_tv = None
            tasks = cast(
                set[asyncio.Task[Any]],
                apple_tv.close(),  # pyright: ignore[reportUnknownMemberType]
            )
            await aio.gather(*tasks)

    async def do_command(self, command: str, args: list[str]):
        if not self.should_send_commands_to_device:
            return
        apple_tv = await self.get_apple_tv()
        await getattr(apple_tv.remote_control, command)(*args)

    async def home(self):
        await self.do_command("home", [])

    async def down(self):
        await self.do_command("down", [])

    async def launch_url(self, url: str):
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
        if not self.should_send_commands_to_device:
            return
        await self.home()
        await aio.sleep(2)
        await self.home()
        await aio.sleep(2)
        await self.menu()

    async def sleep(self) -> None:
        if not self.should_send_commands_to_device:
            return
        apple_tv = await self.get_apple_tv()
        await apple_tv.power.turn_off()

    async def wake(self) -> None:
        if not self.should_send_commands_to_device:
            return
        apple_tv = await self.get_apple_tv()
        await apple_tv.power.turn_on()
        await aio.sleep(8)
        await self.screensaver()

    async def launch(self, url: str) -> None:
        if not self.should_send_commands_to_device:
            return
        apple_tv = await self.get_apple_tv()
        await apple_tv.apps.launch_app(url)
        await aio.sleep(2)
        await apple_tv.remote_control.select()
        await apple_tv.remote_control.select()


Job: TypeAlias = Callable[[], Awaitable[None]]


@dataclass(slots=True)
class ATV:
    atv: AtvConnection
    queue: Queue[Job] = field(default_factory=lambda: Queue[Job](), repr=False)
    task: Task[NoReturn] = field(init=False, repr=False)
    in_screensaver: bool = False

    def __post_init__(self) -> None:
        self.task = Task[NoReturn].create(
            type(self).__name__, self.process_queue_forever()
        )

    async def process_queue_forever(self) -> NoReturn:
        while True:
            job = await self.queue.get()
            if False:
                debug_print("dequeue", job)
            try:
                await self.run_job_with_retry(job)
            finally:
                self.queue.task_done()

    async def run_job_with_retry(self, job: Job) -> None:
        attempts = 0
        while attempts < 2:
            attempts += 1
            try:
                await job()
                return
            except Exception as e:
                log_exc(e)
                debug_print(self)
                await self.close()
                if attempts == 2:
                    return

    async def synced(self) -> None:
        await self.queue.join()

    async def close(self) -> None:
        await self.atv.close()

    def enqueue(self, job: Job, *, mark_screensaver: bool = False) -> None:
        self.in_screensaver = mark_screensaver
        if False:
            debug_print("enqueue")
        self.queue.put_nowait(job)

    def is_in_screensaver(self) -> bool:
        return self.in_screensaver

    def down(self):
        self.enqueue(self.atv.down)

    def home(self):
        self.enqueue(self.atv.home)

    def launch(self, url: str):
        self.enqueue(lambda: self.atv.launch(url))

    def left(self):
        self.enqueue(self.atv.left)

    def menu(self):
        self.enqueue(self.atv.menu)

    def next(self):
        self.enqueue(self.atv.next)

    def play_pause(self):
        self.enqueue(self.atv.play_pause)

    def previous(self):
        self.enqueue(self.atv.previous)

    def right(self):
        self.enqueue(self.atv.right)

    def screensaver(self):
        self.enqueue(self.atv.screensaver, mark_screensaver=True)

    def select(self):
        self.enqueue(self.atv.select)

    def sleep(self):
        self.enqueue(self.atv.sleep)

    def stop(self):
        self.enqueue(self.atv.stop)

    def top_menu(self):
        self.enqueue(self.atv.top_menu)

    def up(self):
        self.enqueue(self.atv.up)

    def volume_down(self):
        self.enqueue(self.atv.volume_down)

    def volume_up(self):
        self.enqueue(self.atv.volume_up)

    def wake(self):
        self.enqueue(self.atv.wake)


@dataclass(slots=True)
class ATVs:
    by_tv: Dict[TV, ATV] = field(
        default_factory=lambda: {tv: ATV(AtvConnection(tv)) for tv in TV.all()}
    )

    @classmethod
    def field(cls):
        return dataclasses.field(default_factory=ATVs, metadata=json_field.omit)

    def set_should_send_commands_to_device(self, b: bool) -> None:
        for atv in self.by_tv.values():
            atv.atv.should_send_commands_to_device = b

    async def power_on(self) -> None:
        # Waking TV1 turns on the LG via CEC.
        for tv in TV.all():
            self.atv(tv).wake()
        await self.synced()

    async def power_off(self) -> None:
        for tv in TV.all():
            self.atv(tv).sleep()
        await self.synced()

    async def shutdown(self):
        await self.synced()
        await aio.gather(*(atv.close() for atv in self.by_tv.values()))

    def atv(self, tv: TV) -> ATV:
        return self.by_tv[tv]

    async def synced(self) -> None:
        await aio.gather(*(atv.synced() for atv in self.by_tv.values()))
