from __future__ import annotations

# Local package
from .base import *
from . import aio
from . import config

TERM = b"\r"

@dataclass
class Connection:
    reader: aio.StreamReader
    writer: aio.StreamWriter
    read_line_timeout: float = 1

    def __repr__(self):
        return "<connection>"

    @classmethod
    async def create(cls) -> Connection:
        reader, writer = await aio.open_connection(config.ITACH_HOST, config.ITACH_PORT)
        return Connection(reader=reader, writer=writer)

    async def read_line(self) -> str | None:
        line = await aio.wait_for(
            self.reader.readuntil(b"\n"), 
            timeout=self.read_line_timeout)
        if line is None:
            return None
        response = line.decode("ascii", errors="strict").strip()
        if False: log(f"jtech--> {response}")
        return response

    async def write_line(self, line: str) -> None:
        if False: log(f"jtech<-- {line}")
        self.writer.write(line.encode("ascii") + TERM)
        await self.writer.drain()

    async def send_command(self, command: str) -> str | None:
        await self.write_line(command)
        return await self.read_line()

    async def close(self) -> None:
        self.writer.close()
        try:
            await self.writer.wait_closed()
        except Exception:
            pass
