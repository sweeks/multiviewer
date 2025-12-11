from . import aio, mvd
from .base import *

aio.run_event_loop(mvd.become_daemon())
