# Effects

The Effects tab has two sections, **Blur** and **Window animation**. Each starts with a switch that
turns its effect on or off for the whole desktop. While a switch is off, every control in its
section is greyed; the values are kept, and switching it back on brings them back as they were.

Both effects ship switched off: on a desktop where nothing has turned one on, its switch here is
unticked. **Restore KyprX's defaults…** on the [Settings](settings.md) tab switches both on.
Until something writes a setting, the tab shows the value the effect itself uses, which can
differ from KyprX's default; those values are on the
Better Blur DX and
Geometry Change pages.

What one window gets is decided on the [Windows](windows.md) tab: its **Blur** column is the
per-window side of the Blur section, its **Animate** column of Window animation.

## Blur

The blur is drawn by Better Blur DX, an effect the desktop must be running
(Better Blur DX). It shows only through a see-through window;
how see-through windows are is set on [Appearance](appearance.md).

- **Blur windows** is the switch. KyprX's default: on. While it is off, the Windows tab's **Blur**
  column is greyed. When Better Blur DX is missing or not running, the switch and the box are
  greyed and an orange line under the switch says which;
  [What KyprX needs](settings.md#what-kyprx-needs) says what to do.
- **Which windows** is a menu with four answers:

  | Answer | Which windows are blurred |
  |---|---|
  | **Only the windows ticked on the Windows tab** | those with their **Blur** box ticked |
  | **Every window except the ones unticked there** | all but those with their **Blur** box unticked. KyprX's default |
  | **Every window** | all, whatever the Windows tab says |
  | **No window** | none |

  With the last two the Windows tab has nothing to decide, so its **Blur** column is greyed. With
  Better Blur DX 2.5.1 those two answers do not do what they say
  (what they do instead).

- **Window frames** blurs behind the frame around a window as well. KyprX's default: on.
- **Menus** blurs behind menus as they open. KyprX's default: on.
- **Panels** blurs behind the desktop's panels. KyprX's default: on.

The five numbers:

| Setting | Range | KyprX's default | What it changes |
|---|---|---|---|
| **Strength** | 1 to 15 | 6 | How far the blur spreads what is behind the window. |
| **Noise** | 0 to 20 | 5 | Grain mixed into the blur, which hides the banding a smooth blur can show. |
| **Brightness** | 0 to 200 % | 100 % | Lightens or darkens what shows through the window. |
| **Saturation** | 0 to 300 % | 150 % | How strong the colours behind the window come through. |
| **Contrast** | 0 to 200 % | 100 % | How far apart the light and dark parts behind the window are drawn. |

The blur's corners are not set here: they follow **Corner radius** on
[Appearance](appearance.md).

## Window animation

The animation is drawn by Geometry Change, an effect KyprX can do without. Without it, this
section changes nothing on screen (Geometry Change).

- **Animate windows as they move and resize** is the switch. KyprX's default: on. While it is off,
  the Windows tab's **Animate** column is greyed. When the effect is missing or not running, the
  switch and the box are greyed, with an orange line under the switch saying which.
- **Duration** is how long a window takes to settle when it is moved or resized: 0 to 2000 ms.
  KyprX's default: 250 ms. The time an animation takes on screen also depends on the desktop's
  own animation speed, not only on this number
  (Geometry Change).
