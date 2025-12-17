This document specifies the behavior of the multiviewer and its remote control. It is
aimed at developers rather than users of the remote control. We use python pseudo-code for
clarity. We first describe the bits of state in the multiviewer, and how that state
determines the device settings (screen layout, volume). We then describe the
remote-control buttons, and how they change the multiviewer state. This structure reflects
the software architecture, which has the abstract multiviewer state (`mv.py`) and buttons
that make straightforward changes to that state. There are distinct subsystems that
propagate bits of the multiviewer state to devices (`atvs.py`, `jtech_manager.py`,
`volume.py`).

# Power

The multiviewer holds a single boolean with the power state of the entire system,
including all devices:

```
power: ON | OFF
```

The multiviewer is responsible for turning on and off devices to match this state.

# Windows, TVs, and Window TVs

The multiviewer has four Windows:

```python
Window = W1 | W2 | W3 | W4
```

There are four TVs:

```python
TV = TV1 | TV2 | TV3 | TV4
```

At all times, the four windows hold distinct TVs:

```python
window_tv: Dict[Window, TV]
```

Some remote-control actions change `window_tv`.

# Screen Layouts

Windows are arranged on screen in various layouts, which determine the windows that are
displayed and their locations and sizes. There are five window sizes, relative to TV
width: full (1/1), prominent (2/3), medium (1/2), small (1/3), and pip (1/5). Here are the
eight layouts:

- `FULL`: one full-size window, which could be any of `W1`-`W4`.
- `PIP`: one full-size window, which could be any of `W1`-`W4`, and a second pip window,
  distinct from the full-size window, overlayed in a corner.
- `PBP(1)`, `PBP(2)` (picture-by-picture): `W1` and `W2`, side by side, vertically
  centered. In the `(1)` variant, `W1` and `W2` are medium size. In the `(2)` variant,
  `W1` is prominent and `W2` is small.
- `TRIPLE(1)`, `TRIPLE(2)`: `W1` on the left, vertically centered, `W2` and `W3` stacked
  vertically on the right, vertically centered. In the `(1)` variant, `W1`, `W2`, `W3` are
  medium size. In the `(2)` variant, `W1` is prominent and `W2` is small.
- `QUAD(1)`: Four medium sized windows in a 2x2 gird, with `W1` and `W2` side-by-side
  above `W3` and `W4` side-by-side.
- `QUAD(2)`: `W1` prominent on the left, vertically centered, `W2`, `W3`, `W4` small on
  the right, stacked vertically.

`FULL` and `PIP` are "fullscreen" layouts. The other six are "multiview" layouts.

# Layout state

The multiviewer has various bits of state that determine the window layout. First, there
is a boolean that says whether the layout is multiview or fullscreen:

```python
layout_mode: MULTIVIEW | FULLSCREEN
```

For multiview layouts, the state says whether all windows are the same size (submode `(1)`
or `W1` is prominent (submode `(2)`):

```python
multiview_submode: WINDOWS_SAME | W1_PROMINENT
```

Even when fullscreen, `multiview_submode` is relevant, because it will affect the layout
when we switch back to multiview.

The state has a count of the number of active windows, which defines the prefix of `W1`,
`W2`, `W3`, `W4` that may appear on screen. No window appears on screen more than once.

```python
num_active_windows: 1-4
```

In multiview layouts, all the active windows are shown on screen. E.g., if
`num_active_windows == 3`, then the multiview layout will be `TRIPLE(x)` and will show
`W1`, `W2`, `W3`; the submode is determined by `multiview_submode`. If
`num_active_windows == 1`, then `layout_mode == FULLSCREEN`; the converse does not hold.

In fullscreen layouts, the state says whether to show the pip window, and which windows
are displayed full and pip:

```python
fullscreen_mode: FULL | PIP
full_window: Window
pip_window: Window
```

The fullscreen window and the pip window are distinct active windows. Even when multiview,
`fullscreen_mode` matters, because it affects what we show when we next switch to
fullscreen. In multiview, `full_window` and `pip_window` are not meaningful, because other
aspects of state will determine them when we switch to fullscreen.

Finally, for pip layouts, the multiviewer has state for each TV that says where the pip
window is, when that TV is fullscreen.

```python
PipLocation = NE | NW | SE | SW
pip_location_by_tv: dict[TV, PipLocation]
```

# Selected window

At all times, the multiviewer at has a single selected window:

```python
selected_window: Window
```

The selected window is always one of the visible windows.

The selected TV is the TV in the currently selected window, i.e.,
`window_tv[selected_window]`.

Audio always comes from the selected TV.

# Volume

The soundbar supports volume up, volume down, and mute. The multiviewer has a boolean that
tracks mute state, and an integer "volume delta", which tracks the net number of presses
of volume up minus volume down.

```python
mute : MUTED | UNMUTED
volume_delta: int
```

The multiviewer maintains a separate volume delta for each TV.

```python
volume_delta_by_tv: dict[TV, int]
```

At all times, the multiviewer is responsible for making the soundbar mute state match
`mute` and making `volume_delta` match the selected TV, i.e.
`volume_delta_by_tv[window_tv[selected_window]]`. The multiviewer sends IR commands to the
soundbar when `volume_delta` changes, either because the volume delta of the selected TV
changes, or because the selected TV changes to a TV with a different volume delta.

# Remote Mode and Window Borders

Some of the remote-control buttons are dual use, and can act on the selected Apple TV or
on the multiviewer. A boolean determines which of these is in effect:

```python
remote_mode: APPLE_TV | MULTIVIEWER
```

Another boolean determines whether the selected window is shown with a distinct border
color from other windows:

```python
selected_window_has_distinct_border: bool
```

When `selected_window_has_distinct_border == True`, the selected window's border color
depends on `remote_mode` and is either green (`MULTIVIEWER`) or red (`APPLE_TV`). Windows
whose borders aren't red or green are gray.

When `selected_window_has_distinct_border == False`, all windows have gray borders.

# Remote-Control Buttons

The remote control has 15 buttons:

- Power
  - **Power**
- Remote
  - **Remote**
- Multiviewer
  - **Add Window**
  - **Remove Window**
- Dual-use (Multiviewer, Apple TV)
  - Arrows: **Up**, **Down**, **Left**, **Right**
  - **Select**
  - **Back**
  - **Home**
  - **Play/Pause**
- Volume
  - **Mute**
  - **Volume Up**
  - **Volume Down**

Some of the buttons can be double tapped; the threshold is 0.3s.

# Power Button

The **Power** button toggles the `power` state, and the multiviewer then turns on or off
all devices.

# Remote Button

The **Remote** button toggles `remote_mode`. Double tapping **Remote** brings up the iOS
remote app for the selected Apple TV, and does not change `remote_mode`.

# Volume Buttons

- **Mute**. This toggles `mute` state.
- **Volume Up**. This increments the volume delta of the selected TV.
- **Volume Down**. This decrements the volume delta of the selected TV.

# Dual-use Buttons for Apple TV

When `remote_mode == APPLE_TV`, the dual-use buttons behave exactly like the
Apple-TV-remote buttons of the same name, acting on the selected TV.

- **Up**, **Down**, **Left**, **Right**
- **Select**
- **Back**
- **Home**
- **Play/Pause**

# Play/Pause in Multiviewer

When `remote_mode == MULTIVIEWER`:

- **Play/Pause**: toggles `selected_window_has_distinct_border`.

# Dual-use Buttons in Multiview

When:

- `remote_mode == MULTIVIEWER`
- `layout_mode == MULTIVIEW`

the dual-use buttons behave as follows:

- **Select**: makes the selected window fullscreen, i.e. sets `layout_mode == FULLSCREEN`
  and `full_window == selected_window`, leaving `fullscreen_mode` unchanged. If
  `fullscreen_mode == PIP`, then the pip window is the next active window after the full
  window, wrapping around to `W1` if the full window is the last active window.

- **Back**: no-op.

- **Up**, **Down**, **Left**, **Right**: change the selected window to the window the
  arrow points to. Double tap swaps the TVs in the selected window and the window the
  arrow points to. Double tap, if the selected window is not prominent, moves the selected
  window to the pointed-to window.

- **Home**: toggles `multiview_submode`.

# Dual-use Buttons in Fullscreen

When:

- `remote_mode == MULTIVIEWER`
- `layout_mode == FULLSCREEN`

**Back** and **Home** behave as follows:

- **Back**: returns to multiview, i.e. makes `layout_mode == MULTIVIEW`. This does not
  change `window_tv` or `selected_window`.

- **Home**: toggles `fullscreen_mode`. After toggling, the full window is selected.

# Dual-use Buttons in `FULL`

When:

- `remote_mode == MULTIVIEWER`
- `layout_mode == FULLSCREEN`
- `fullscreen_mode == FULL`

the dual-use buttons behave as follows:

- **Select**: no-op.

- **Up**, **Down**: no-op.

- **Left**, **Right**: cycle `full_window` among the active windows. The selected window
  follows `full_window`.

# Dual-use Buttons in `PIP`

When:

- `remote_mode == MULTIVIEWER`
- `layout_mode == FULLSCREEN`
- `fullscreen_mode == PIP`

the dual-use buttons behave as follows:

- **Select**: swaps `full_window` and `pip_window`. This does not change `window_tv`.

- **Up**, **Down**: change the selected window between the full window and the pip window,
  if the arrow points from the selected window to the other window.

- **Left**, **Right**: cycle `pip_window` among the active windows other than
  `full_window`. If the pip window is selected, then the selected window follows
  `pip_window`.

- Double tap **Up**, **Down**, **Left**, **Right**: move the pip location in the
  direction of the arrow, when possible, regardless of the selected window.

# **Add Window** and **Remove Window**

- **Add Window**: if `num_active_windows < 4`, this increments `num_active_windows`, which
  causes the first (lowest numbered) inactive window to become active. If
  `layout_mode == MULTIVIEW`, the newly active window will appear on screen. If
  `layout_mode == FULLSCREEN`, the newly active window will not appear, but will be
  available for cycling.

- **Remove Window**: if `num_active_windows > 1`, this decrements `num_active_windows` and
  demotes the selected TV to become the first inactive TV, promoting the active TVs in
  higher numbered windows. If the selected window becomes inactive, then `W1` is selected;
  otherwise the selected window does not change. Afterwards, if `num_active_windows == 1`,
  then `layout_mode == FULLSCREEN` and `fullscreen_mode == FULL`.

**Add Window** and **Remove Window** do not change `window_tv`.

# Invariants

- `window_tv` maps windows to distinct TVs.

- `1 <= num_active_windows <= 4`; the active windows are the prefix `W1..Wn`.

- In multiview, all active windows are visible.

- The selected window is visible.

- If `num_active_windows == 1`, then `layout_mode == FULLSCREEN` and
  `fullscreen_mode == FULL`.

- In `PIP`, `full_window` and `pip_window` are distinct active windows.

- Audio follows the selected TV.

- Volume follows the selected TV:
  `volume_delta == volume_delta_by_tv[window_tv[selected_window]]`.
