# Local package
from .base import *

HTTP_PORT: int

class Server: ...

def serve_until_stopped(run_command: Callable[[list[str]], Awaitable[JSON]]) -> Server: ...

def stop(s: Server) -> None: ...