This document specifies the behavior of the multiviewer and its remote control.  It is
aimed at developers rather than users of the remote control.  We use python pseudo-code
for clarity.

# Power

The multiviewer holds a single boolean with the power state of the entire system,
including all devices:

```
Power: On | Off
```

The multiviewer is responsible for turning on and off devices to match this state.

# Windows, TVs, and Window Inputs

The multiviewer has four Windows:

```python
Window = W1 | W2 | W3 | W4
```

# Layouts

Windows are arranged on screen in various layouts. Each of the eight layouts completely
determines the window locations and sizes. There are five window sizes, relative to TV
width: full (1/1), prominent (2/3), medium (1/2), small (1/3), and pip (1/5). Here are
the eight layouts:

- `FULL`: one full-size window, which could be any of `W1`-`W4`.
- `PIP`: one full-size window, which could be any of `W1`-`W4`, and a second pip window,
which could be any overlayed in a corner.  
- `PBP(1)`, `PBP(2)` (picture-by-picture): `W1` and `W2`, side by side, vertically
  centered. In the `(1)` variant, `W1` and `W2` are medium size.  In the `(2)` variant,
  `W1` is prominent and `W2` is small.
- `TRIPLE(1)`, `TRIPLE(2)`: `W1` on the left, vertically centered, `W2` and `W3` stacked
  vertically on the right, vertically centered. In the `(1)` variant, `W1`, `W2`, `W3` are
  medium size.  In the `(2)` variant, `W1` is prominent and `W2` is small.
- `QUAD(1)`: Four medium sized windows in a 2x2 gird, with `W1` and `W2` side-by-side
  above `W3` and `W4` side-by-side.
- `QUAD(2)`: `W1` prominent on the left, vertically centered, `W2`, `W3`, `W4` small on
  the right, stacked vertically.

`FULL` and `PIP` are "fullscreen" layouts.  The other six are "multiview" layouts.

# Active windows

At all times, some prefix of `W1`-`W4` is active:

```python
num_active_windows: 1-4
```

Only active windows can appear on screen. In multiview layouts, all the active windows are
shown on screen.  E.g., if there are three active windows, then the multiview layout will
be `TRIPLE(x)` and will show `W1`, `W2`, `W3`. In fullscreen layouts, the fullscreen
window and the pip window are distinct active windows. No window appears on screen more
than once.

# Layout state

The multiviewer has various bits of state that completely determine the window layout.
First, there is a boolean that says whether the layout is multiview or fullscreen:

```python
mode: MULTIVIEW | FULLSCREEN
```

For multiview layouts, the state says whether to use submode `(1)` or `(2)`: 

```python
submode: SUBMODE1 | SUBMODE2
```

For fullscreen layouts, the state says whether to show the pip, and which windows are
displayed full and pip:

```python
show_pip: bool
full_window: Window
pip_window: Window
```

Even when fullscreen, the `submode` is relevant, because it will affect the layout when we
switch back to multiview.  Similarly, even when in a multiview layout, `show_pip` is
relevant, because it affect whether we show the `pip` window when we next switch to
fullscreen.

# Window TVs

There are four TVs:

```python
TV = TV1 | TV2 | TV3 | TV4
```

At all times, the windows display distinct TVs:

```python
window_tv: Dict[Window, TV]
```

Remote-control actions can change `window_tv` by swapping the TVs of two windows.

# Remote mode

Some of the remote-control buttons are dual use, and can act on the selected Apple TV or
on the multiviewer.  A boolean determines which of these is in effect:

```python
remote_mode: APPLE_TV | MULTIVIEW
```

# Selected window

At all times, the multiviewer at has a single selected window:

```python
selected_window: Window
```

The selected TV is the TV in the currently selected window, i.e.,
`window_tv[selected_window]`.

Audio always comes from the selected TV.

A boolean determines whether the selected window is shown with a distinct border color
from other windows:

```python
selected_window_border_color: bool
```

When `selected_window_border_color == True`, the selected window border color depends on
`remote_mode` and is either green (MULTIVIEW) or red (APPLE_TV).

# Buttons
  **Power**


  **Add Window**
  **Remove Window**
  **Remote**

Volume:
  **Mute**, **Volume Up**, **Volume Down**

Dual-use:
  Arrows: **Up**, **Down**, **Left**, **Right**
  **TV**
  **Select**
  **Play/Pause**
  **Back**


Per-TV State:
   volume delta
   pip location