from __future__ import annotations

# Standard library
import asyncio
import dataclasses
import datetime

# Local package
from . import json_field
from .base import *

gather = asyncio.gather
open_connection = asyncio.open_connection
sleep = asyncio.sleep

event_loop = asyncio.new_event_loop()
def handler(_, context):
    debug_print("loop exception", context)
event_loop.set_exception_handler(handler)
asyncio.set_event_loop(event_loop)

def call_later(seconds, f) -> None:
    event_loop.call_later(seconds, f)

async def wait_for(a, *, timeout):
    start = datetime.datetime.now()
    try:
        return await asyncio.wait_for(a, timeout)
    except asyncio.TimeoutError as e:
        duration = (datetime.datetime.now() - start).total_seconds()
        if False: log(f"wait_for timeout: timeout={timeout}s duration={duration}s")
        return None

class Event(asyncio.Event):
    @classmethod
    def field(cls):
        return dataclasses.field(default_factory=Event, metadata=json_field.omit)

    def __repr__(self) -> str:
        is_set = self.is_set()
        waiters = len(self._waiters)
        return f"{type(self).__name__}(is_set={is_set}, waiters={waiters})"
    
class StreamReader(asyncio.StreamReader):
    def __repr__(self) -> str:
        return f"<StreamReader>"

class StreamWriter(asyncio.StreamWriter):
    def __repr__(self) -> str:
        return f"<StreamWriter>"

class Task(asyncio.Task):
    @classmethod
    def field(cls):
        return dataclasses.field(init=False, metadata=json_field.omit)
    
    def __repr__(self) -> str:
        name = self.get_name()
        return f"Task(name='{name}')"

    def log_done(self) -> None:
        try:
            exc = self.exception()
        except asyncio.CancelledError:
            # Normal during shutdown; ignore.
            return
        if exc is not None:
            debug_print("task raised", exc)

    @classmethod
    def create(cls, name: str, coro) -> Task:
        task = Task(coro)
        task.set_name(name)
        task.add_done_callback(lambda task: task.log_done())
        return task

def run_coroutine_threadsafe(a):
    return asyncio.run_coroutine_threadsafe(a, event_loop).result()

def run_event_loop(main):
    try:
        event_loop.run_until_complete(main)
    finally:
        tasks = asyncio.all_tasks(event_loop)
        for t in tasks:
            t.cancel()
        if tasks:
            event_loop.run_until_complete(gather(*tasks, return_exceptions=True))
        event_loop.close()
