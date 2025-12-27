"""
Stuff used throughout the project.  Most other code does:

    from .base import *
"""

# Standard library
from collections.abc import Awaitable, Callable, Coroutine, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import (
    Any,
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

class RunMode:
    Daemon: RunMode
    Testing: RunMode

    @classmethod
    def set(cls, mode: RunMode) -> None: ...
    @classmethod
    def get(cls) -> RunMode: ...

JSON: TypeAlias = dict[str, Any] | list[Any] | str | int | float | bool | None
Dict = dict
List = list
Tuple = tuple

class Jsonable:
    def to_json(self, *args: Any, **kwargs: Any) -> str: ...
    @classmethod
    def from_json(cls, _: str) -> Self: ...

T = TypeVar("T", bound="MyStrEnum")

class MyStrEnum(StrEnum):
    """String-valued enum with an integer bijection, supplied via a subsequent
    call to attach_int.  Attributes:
        all: ordered tuple of all enum members
        to_int:
        of_int:

    Usage looks like:

        class XS(MyStrEnum):
            X1 = auto()
            X2 = auto()
        attach_int(XS, { XS.X1: 1, XS.X2: 2 })
    """

    @classmethod
    def all(cls) -> tuple[Self]:
        """returns a list of all class members"""

    @classmethod
    def of_int(cls, i: int) -> Self:
        """returns the class member corresponding to the int"""

    def to_int(self: Self) -> int:
        """returns the int corresponding to the class member"""

def auto() -> Any:
    """The same as enum.auto.  Use this to initialize MyStrEnum members."""

def attach_int(cls: type[T], table: Mapping[T, int]) -> None:
    "Used with MyStrEnum to specify the bijection between class members and ints."

def fail(*args: object) -> NoReturn:
    """raises an exception containing the supplied arguments"""

def assert_(cond: bool, *args: object) -> None:
    """raises via fail if not cond."""

def assert_equal(a: Any, b: Any, *args: object) -> None:
    """raises via fail if a != b."""

def debug_print(*args: Any) -> None:
    """pretty prints the supplied arguments"""

def log(event: str, **fields: Any) -> None:
    """outputs a timestamped line and the supplied fields"""

def log_exc(e: Exception) -> None: ...

__all__ = [
    "Any",
    "assert_",
    "assert_equal",
    "attach_int",
    "auto",
    "Awaitable",
    "Coroutine",
    "dataclass",
    "dataclass_json",
    "Callable",
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
    "Path",
    "RunMode",
    "Self",
    "Tuple",
    "TypeAlias",
    "TypeVar",
    "Union",
]
