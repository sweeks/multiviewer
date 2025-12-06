"""
HTTP server that receives HTTP requests from button shortcuts and calls run_command with
the supplied command. The server runs in its own thread, and runs calls to run_command in
async via aio.run_coroutine_threadsafe.
"""

# Local package
from .base import *

HTTP_PORT: int

class Server: ...

def serve_until_stopped(run_command: Callable[[list[str]], Awaitable[JSON]]) -> Server: ...

def stop(s: Server) -> None: ...