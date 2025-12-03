from .base import *
from . import aio
from . import mvd

RunMode.set(RunMode.Daemon)
aio.run_event_loop(mvd.stop_running_daemon())
