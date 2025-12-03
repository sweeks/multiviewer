from .base import *
from . import aio
from . import mvd

aio.run_event_loop(mvd.become_daemon())
