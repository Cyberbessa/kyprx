# Effects

The Effects tab has two sections, **Blur** and **Window animation**. Each one starts with a switch
that turns its effect on or off for the whole desktop. While a switch is off, every control in its
section is greyed. The controls keep their values, and turning the switch back on brings them back
as they were.

There is no Apply button: each change is written by itself, as everywhere in the window (see
[The KyprX window](README.md)).

**KyprX's default**, below, is the value that **Restore KyprX's defaults…** on the
[Settings](settings.md) tab writes. Until something writes a setting, the tab shows the value the
effect itself uses, which can be different. Those values are on the
Better Blur DX and
Geometry Change pages.

What happens to one window is decided on the [Windows](windows.md) tab. Its **Blur** column is the
per-window side of the Blur section, and its **Animate** column is the per-window side of the
Window animation section.

## Blur

The blur is drawn by Better Blur DX, an effect for the desktop that KyprX needs
(Better Blur DX). It blurs what is behind a window, so it
shows only through a window that is see-through. How see-through the windows are is set on the
[Appearance](appearance.md) tab.

**Blur windows** is the switch. It turns the blur effect on or off. While it is off, the Windows
tab's **Blur** column is greyed. KyprX's default: on. When Better Blur DX is not installed, or the
desktop is not running it, the switch and the box are greyed, and an orange line under the switch
says which; [What KyprX needs](settings.md#what-kyprx-needs) says what to do.

**Which windows** is a menu with four answers:

- **Only the windows ticked on the Windows tab.** A window is blurred only when its **Blur** box on
  the Windows tab is ticked.
- **Every window except the ones unticked there.** Every window is blurred unless its **Blur** box
  on the Windows tab is unticked. This is KyprX's default.
- **Every window.** Every window is blurred, whatever the Windows tab says.
- **No window.** No window is blurred.

With the last two answers the Windows tab has nothing to decide, so its **Blur** column is greyed.
With Better Blur DX 2.5.1, those two answers do not do what they say. What they do instead is on
the Better Blur DX page.

**Window frames** blurs behind the frame around a window as well as behind the window. KyprX's
default: on.

**Menus** blurs behind menus as they open. KyprX's default: on.

**Panels** blurs behind the desktop's panels. KyprX's default: on.

The last five are numbers:

| Setting | Range | KyprX's default | What it changes |
|---|---|---|---|
| **Strength** | 1 to 15 | 6 | How far the blur spreads what is behind the window. |
| **Noise** | 0 to 20 | 5 | Grain mixed into the blur, which hides the banding a smooth blur can show. |
| **Brightness** | 0 to 200 % | 100 % | Lightens or darkens what shows through the window. |
| **Saturation** | 0 to 300 % | 150 % | How strong the colours behind the window come through. |
| **Contrast** | 0 to 200 % | 100 % | How far apart the light and dark parts behind the window are drawn. |

The blur's corners are not set here. They follow **Corner radius** on the
[Appearance](appearance.md) tab.

## Window animation

The animation is drawn by Geometry Change, an effect for the desktop that KyprX can do without.
Without it, this section changes nothing on screen. Which movements it animates, and what happens
when it is not installed, are on the Geometry Change page.

**Animate windows as they move and resize** is the switch. It turns the animation on or off. While
it is off, the Windows tab's **Animate** column is greyed. KyprX's default: on. When Geometry Change
is not installed, or the desktop is not running it, the switch and the box are greyed, with an
orange line under the switch saying which.

**Duration** is how long a window takes to settle when it is moved or resized, from 0 to 2000 ms.
KyprX's default: 250 ms.

## Good to know

- **Both effects ship switched off.** On a desktop where nothing has switched one on, its switch
  here is unticked. **Restore KyprX's defaults…** switches both on.
- **The time an animation takes on screen also depends on the desktop's own animation speed**, not
  only on **Duration**. See Geometry Change.
