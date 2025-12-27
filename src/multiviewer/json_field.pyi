"""
Used to specify json serialization in fields of class declarations that look like:

    @dataclass_json
    @dataclass
    class SomeClass:
        some_field: dict[X, Y] = field(metadata=...)
"""

# Local package
from .base import *

Metadata = dict[str, dict[str, Any]]

omit: Metadata
"""
Elide the field from json.  Usage:
    some_field: X = field(metadata=json_field.omit)
"""

def json_dict(domain: type, range: type) -> Metadata:
    """
    Usage:
        some_field: dict[X, Y] = field(metadata=json_dict(X, Y))
    """
