
from __future__ import annotations

# Standard library
import inspect

from dataclasses_json import config
from enum import Enum

# Local package
from .base import *

K = TypeVar("K")
V = TypeVar("V")

Codec = Tuple[Callable[[Any], Any], Callable[[Any], Any]]

omit = config(
    encoder=lambda _: None,
    exclude=lambda _: True)

def _identity_codec() -> Codec:
    return (lambda x: x, lambda x: x)

def _resolve_codec(t_or_codec: Any) -> Codec:
    """
    Resolve either:
      - a (encode, decode) pair directly, or
      - a class/type into an appropriate codec:
          * dataclasses_json classes → (to_dict, schema.load)
          * Enum subclasses         → (e.name, T[ name ])
          * primitives/other        → identity
    """
    # Already a codec pair
    if isinstance(t_or_codec, tuple) and len(t_or_codec) == 2:
        return t_or_codec  # type: ignore[return-value]

    # Class-based resolution
    if inspect.isclass(t_or_codec):
        T = t_or_codec

        # dataclasses_json classes expose class-level schema() and instance to_dict()
        has_schema = hasattr(T, "schema") and callable(getattr(T, "schema"))
        has_to_dict = hasattr(T, "to_dict")
        if has_schema and has_to_dict:
            return (lambda o: o.to_dict(), lambda d: T.schema().load(d))  # type: ignore[attr-defined]

        # Enums: centralized name-based codec
        if issubclass(T, Enum):
            return (lambda e: e.name, lambda s: T[s])  # type: ignore[index]

    # Fallback: numbers, strings, bools, None, plain dict/list, etc.
    return _identity_codec()

def json_dict(key_t_or_codec: Any, val_t_or_codec: Any):
    """
    Create a dataclasses_json field that encodes a Python dict[K,V] as
    a JSON list of [key_json, value_json] pairs.

    key_t_or_codec, val_t_or_codec:
      - a type (Enum subclass, @dataclass_json class, or primitive), OR
      - an explicit (encode, decode) callable pair.

    Example:
        submode: dict[Mode, Submode] = dict(Mode, Submode)
    """
    k_enc, k_dec = _resolve_codec(key_t_or_codec)
    v_enc, v_dec = _resolve_codec(val_t_or_codec)

    def encoder(d: dict[K, V]) -> list[list[Any]]:
        return [[k_enc(k), v_enc(v)] for k, v in d.items()]

    def decoder(pairs: Any) -> dict[object, object]:
        # Accept both the intended list-of-pairs and a legacy JSON object for resilience.
        if isinstance(pairs, dict):
            it = pairs.items()
        else:
            it = pairs  # expect iterable of [k, v]
        return {k_dec(k): v_dec(v) for k, v in it}

    return config(encoder=encoder, decoder=decoder)
