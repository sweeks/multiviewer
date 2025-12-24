from __future__ import annotations

# Standard library
import datetime
import inspect
import os
import pprint
import sys
import time
import traceback
from collections.abc import Awaitable, Callable, Coroutine, Mapping
from dataclasses import dataclass, field
from enum import StrEnum as _StrEnum
from enum import auto
from typing import (
    Any,
    ClassVar,
    Generic,
    NoReturn,
    Optional,
    Self,
    TypeAlias,
    TypeVar,
    Union,
)

# Third-party
from dataclasses_json import dataclass_json

JSON: TypeAlias = dict[str, Any] | list[Any] | str | int | float | bool | None
Dict = dict
List = list
Tuple = tuple


class Jsonable:
    pass


class RunMode(_StrEnum):
    Daemon = auto()
    Testing = auto()

    current: ClassVar[RunMode | None]

    @classmethod
    def set(cls, mode: RunMode) -> None:
        cls.current = mode

    @classmethod
    def get(cls) -> RunMode:
        mode = cls.current
        if mode is None:
            fail("Must call RunMode.set before RunMode.get")
        return mode


RunMode.current = None

SELF_BASENAME = os.path.basename(__file__)
SELF_MODNAME = __name__


def file_and_line(max_steps: int = 50) -> str:
    f = inspect.currentframe()
    steps = 0
    try:
        while f and steps < max_steps:
            co = f.f_code
            filename = co.co_filename or ""
            base = os.path.basename(filename) if filename else ""
            modname = f.f_globals.get("__name__", "")
            is_self = (base == SELF_BASENAME) or (modname == SELF_MODNAME)
            is_synthetic = base in ("", "<string>", "<stdin>")
            if not is_self and not is_synthetic:
                line = f.f_lineno or "?"
                return f"{base}:{line}:{co.co_name}"
            f = f.f_back
            steps += 1
        return "?:?"
    finally:
        # avoid reference cycles
        del f


def log(event: str, **fields: object) -> None:
    if RunMode.get() != RunMode.Daemon:
        return
    now = datetime.datetime.now()
    ts = f"{now.strftime('%Y-%m-%d %H:%M:%S')}.{now.microsecond // 1000:03d}"
    pid = os.getpid()
    parts = [f"{ts} [mvd {pid}]", event]
    for k, v in fields.items():
        parts.append(f"{k}={v}")
    print(" ".join(parts))


def log_exc(e: Exception) -> None:
    if RunMode.get() != RunMode.Daemon:
        return
    fl = file_and_line()
    log(f"{fl} exception")
    traceback.print_exc()
    debug_print(e)


indent = 2
width = 80
depth = None

last_ts = time.monotonic()


def debug_print(*args: Any) -> None:
    global last_ts
    now = time.monotonic()
    dt = int((now - last_ts) * 1000)
    last_ts = now
    pid = os.getpid()
    fl = file_and_line()
    pprint.pprint(
        (f"[mvd {pid}] ({dt}ms) {fl}", *args),
        indent=indent,
        width=width,
        depth=depth,
        sort_dicts=False,
    )
    sys.stdout.flush()


def fail(*args: object) -> NoReturn:
    raise RuntimeError((file_and_line(), *args))


def assert_(condition: bool, *args: object) -> None:
    if not condition:
        fail(*args)


def assert_equal(a: Any, b: Any, *args: object) -> None:
    assert_(a == b, "unexpectedly unequal", a, b, *args)


T = TypeVar("T", bound="MyStrEnum")


class MyStrEnum(_StrEnum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name

    def __repr__(self) -> str:
        return self.name

    @classmethod
    def missing_attach_int(cls) -> NoReturn:
        fail(f"{cls.__name__} not initialized by attach_int()")

    @classmethod
    def all(cls):
        cls.missing_attach_int()

    @classmethod
    def of_int(cls: type[T], i: int) -> T:
        cls.missing_attach_int()

    def to_int(self) -> int:
        type(self).missing_attach_int()


def attach_int(cls: type[T], table: dict[T, int]) -> None:
    # 1) Validate bijection
    members = tuple(cls)
    keyset = set(table.keys())
    if keyset != set(members):
        missing = [m for m in members if m not in keyset]
        extra = [k for k in keyset if k not in members]
        fail("attach_int table mismatch", {"missing": missing, "extra": extra})
    vals: list[Any] = list(table.values())
    if any(not isinstance(v, int) for v in vals):
        fail("attach_int values must be int")
    if len(vals) != len(set(vals)):
        fail("attach_int ints must be unique per member")
    # 2) Freeze maps
    fwd = {m: int(table[m]) for m in members}
    rev = {v: m for m, v in fwd.items()}

    # 3) Rebind methods with named callables
    def all(_cls: type[T]) -> tuple[T, ...]:
        return members

    def of_int(_cls: type[T], i: int) -> T:
        return rev[i]

    def to_int(self: T) -> int:
        return fwd[self]

    cls.all = classmethod(all)  # type: ignore[assignment]
    cls.of_int = classmethod(of_int)  # type: ignore[assignment]
    cls.to_int = to_int  # type: ignore[assignment]


# __all__ is necessary in base.py because other code uses "from .base import *",
# and the meaning of that is determined solely by base.py's __all__.
__all__ = [
    "Any",
    "assert_",
    "assert_equal",
    "attach_int",
    "auto",
    "Awaitable",
    "dataclass",
    "dataclass_json",
    "Callable",
    "Coroutine",
    "debug_print",
    "Dict",
    "fail",
    "field",
    "Generic",
    "JSON",
    "Jsonable",
    "List",
    "log",
    "log_exc",
    "Mapping",
    "MyStrEnum",
    "NoReturn",
    "Optional",
    "RunMode",
    "Self",
    "Tuple",
    "TypeVar",
    "Union",
]
