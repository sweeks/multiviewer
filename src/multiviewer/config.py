"""Hosts and ports for devices used by multiviewer."""

from .tv import TV

ITACH_HOST = "iTach0741E6"
ITACH_PORT = 4999

TV_HOSTS = {
    TV.TV1: "TV-1",
    TV.TV2: "TV-2",
    TV.TV3: "TV-3",
    TV.TV4: "TV-4",
}

WF2IR_HOST = "iTach071EC8"
WF2IR_PORT = 4998
