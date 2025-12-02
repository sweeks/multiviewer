"""This module sends commands and receives responses to the jtech, via the 
Global Cache iTach IP2SL.  The IP2SL listens to a port on my local network and
forwards commands to the jtech's serial port, and then forwards the replies
back.  Each command is a single line ending in "!", and receives a single line
response."""

# Local package
from .base import *

class Connection:
    def __init__(self) -> NoReturn: ...

    @classmethod
    async def create(cls) -> Connection: ...

    async def read_line(self) -> str: ...

    async def write_line(self, line: str) -> None: ...

    async def send_command(self, command: str) -> str | None: ...

    async def close(self) -> None: ...