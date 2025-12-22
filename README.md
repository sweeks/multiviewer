# Overview

This project implements a multiviewer remote control for my home TV. It uses a J-Tech
multiviewer to display four Apple TVs on a single TV, arranged in windows of varying
layouts. The Apple TVs can run a mix of streaming apps, which allows multiview within
streamers and across streamers, always with the same user interface and control.

Here is an example multiviewer layout:

![multiview example](docs/images/1+3.jpg)

The selected window is indicated with a green border. Audio comes from the selected TV,
i.e. the TV currently displayed in the selected window.

# Remote Control

The remote control is an iPhone 13 Mini, which has a home screen with buttons that control
the J-Tech, the Apple TVs, and the volume:

<img src="remote-control/home-screen.png" width="300">

The heart of the remote control is nine buttons arranged like a keypad on an Apple TV
remote: **Up**, **Down**, **Left**, **Right**, **Select**, **Back**, **TV**,
**Play/Pause**, plus a **Remote** button, which toggles the other eight so that they act
as an Apple TV remote or as a multiviewer remote. In `Apple TV` mode, the eight buttons
send the corresponding command to the selected Apple TV. Double tapping **Remote** brings
up the iOS Remote app for the selected TV. In `Multiviewer` mode, the arrow buttons change
the selected window, and double tap moves the selected TV, swapping it with the TV the
arrow points to. **Select** makes the selected TV fullscreen; from there, **Back** returns
to multiview. **Deactivate TV** hides the selected TV offscreen.  **Activate TV** button
adds a window displaying the most recently deactivated TV. 

The lesser-used buttons are at the top. **Power** toggles on/off the power of all the
hardware in the system, including Apple TVs, Jtech, soundbar, and TV. The **Sports** and
**TV** apps are the ordinary iOS apps, and are handy for choosing what to watch. From the
**TV** app, you can share a show to start it playing on the selected TV -- unfortunately,
this only works reliably for shows, and not for most sports streams, so far. The bottom
row of buttons (**Mute**, **Volume Up**, **Volume Down**) control the volume. The
multiviewer has a different volume setting for each TV, and automatically adjusts volume
when switching TVs. Mute is shared across all TVs.

# Implementation

The system consists of the remote control, a daemon running on a MacBook, and software and
devices that allow the daemon to communicate with the J-Tech, Apple TVs, and soundbar.
Here is all the hardware in the system:

- iPhone Mini 13
- MacBook
- 4 Apple TVs
- J-Tech MV41A Multiviewer
- LG S95QR soundbar
- LG TV
- iTach IP2SL
- iTach WF2IR

There are manuals for the J-Tech and iTach devices [here](docs/manuals/).

The remote-control buttons are iOS shortcuts. Each button invokes a shared
[main shortcut](remote-control/MV-Do-Command.shortcut) with the button's name ("Home",
"Up", "Play_pause", etc). The main shortcut sends a simple HTTP request to the daemon with
the button name -- all of the multiviewer logic happens in the daemon.

The daemon is a few thousand lines of Python, and uses the `asyncio` and `pyatv`
libraries. The [src/multiviewer/](src/multiviewer) directory has all of the code except
for tests. The daemon runs an HTTP server that receives commands from the remote-control
shortcuts, updates its virtual multiviewer state and responds to the request, and then in
the background sends commands via WiFi to the J-Tech, Apple TVs, and soundbar.

The IP2SL connects the J-Tech's serial port to ethernet, and has a bidirectional
connection so that the daemon can send commands and receive responses. The WF2IR is
connected to the daemon via WiFi, and sends IR to the soundbar in response to daemon
commands. The Apple TVs are connected to ethernet, and receive commands from the daemon
using the `pyatv` library.

# Configuration

[config.py](src/multiviewer/config.py) has host names, IP addresses, and ports.

Currently, the daemon uses a `.pyatv.conf` that lives outside this repo. That file has
pairing info for the Apple TVs that is required in order for `pyatv` to connect to them. I
plan to move the pairing info into the repo at some point.

# Installation

For each remote-control button, the [remote-control/](remote-control) directory has a
`.shortcut` file and a `.jpg` file with its icon. To add it to the home screen, from the
Shortcuts app, do `Add to Home Screen`, and choose the corresponding icon as its image.
The main shortcut does not need a button, but needs to be added to the Shortcuts app, and
needs to be changed with the hostname of the daemon.

The daemon Python code uses a virtual environment to install dependencies and the
multiviewer package (used by tests). To set up `.venv` and install the repo’s git hooks,
run [setup-repo.sh](bin/setup-repo.sh). That script sets `core.hooksPath=githooks`, so new
commits automatically run the formatting scripts (Black and mdformat) via the pre-commit
hook.

[start-mvd.sh](bin/start-mvd.sh) starts the daemon. At startup, the new daemon first kills
the prior daemon and then starts a new HTTP server.

# Testing

The [tests/](tests) directory has end-to-end tests that run the multiviewer through its
commands and check that the J-Tech's screen matches what is expected.

To run all tests:

```sh
bin/test-all.sh
```
