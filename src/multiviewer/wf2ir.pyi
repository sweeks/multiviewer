"""
The Global Cache WF2IR is connected to the WiFi network, and can send IR sequences to the
soundbar.  The volume module uses it for controlling volume (+, -, mute).
"""

# Local package
from .base import *

def learn() -> None:
    """Enter IR learn mode briefly and print prompts/results."""

async def volume_up() -> None: ...
async def volume_down() -> None: ...
async def mute() -> None: ...
