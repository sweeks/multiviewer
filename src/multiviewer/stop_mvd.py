from . import aio, mvd
from .base import *

RunMode.set(RunMode.Daemon)
aio.run_event_loop(mvd.stop_existing_daemon())
