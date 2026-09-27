# Tiling

The Tiling tab sets how windows are laid out side by side: which layouts the layout keys cycle
through, the space around the windows, what the layout does when a window is moved or opens, and
which windows are never tiled. Above all of that is **Focus**, which decides which window you are
typing into.

The tiling itself is done by Krohnkite, a tiling script for the desktop that KyprX needs
(Krohnkite). The Focus box is the desktop's own setting
(KDE Plasma).

There is no Apply button: each change is written by itself, as everywhere in the window (see
[Changes apply by themselves](README.md#changes-apply-by-themselves)).

**KyprX's default**, below, is the value that **Restore KyprX's defaults…** on the
[Settings](settings.md) tab writes. Until something writes a setting, the tab shows the value
Krohnkite or the desktop uses when nothing is written, which can be different. **Ignored window
classes** is the one exception (see [Never tiled](#never-tiled)).

## When tiling is switched off

The tab has no switch for tiling. KyprX is there to make KDE a tiling desktop, so tiling off is not
one of its settings.

While tiling is switched off, an orange band runs across the top of the tab, with a **Switch tiling
back on** button at its end ([Tiling is switched off](README.md#tiling-is-switched-off)). The band
sits above the boxes, so it does not scroll out of sight. The button switches Krohnkite back on and
changes nothing else.

Any change on this tab also switches tiling back on, together with the change itself.

To keep tiling off, switch Krohnkite off in the desktop's own settings (System Settings, KWin
Scripts). The next change on this tab switches it back on.

The band says that nothing on the tab is doing anything. That is true of every box but Focus:
Focus does not depend on Krohnkite, and it works with tiling off.

When Krohnkite is not installed, the band says that instead, without the button, and the
[Settings](settings.md#what-kyprx-needs) tab says how to install it. The settings on this tab are
still kept, and apply once Krohnkite is there.

## Focus

The desktop's own four focus settings, the ones in System Settings under Window Behavior, with the
same names. They are at the top of the tab because, with no windows overlapping, the pointer is
how you move between them.

**Window activation policy** is what it takes for a window to become the one you are typing into.
It offers the desktop's six answers, under the desktop's own names:

- **Click to focus.** A window becomes active when you click it.
- **Click to focus (mouse precedence).** The same, except when the desktop has to pick the next
  window itself, for example after one closes: then it picks the one under the pointer.
- **Focus follows mouse.** Moving the pointer onto a window makes it active. A window that merely
  appears under the pointer does not take focus that way.
- **Focus follows mouse (mouse precedence).** The same, and when the desktop has to pick the next
  window itself, it picks the one under the pointer. KyprX's default.
- **Focus under mouse.** The window under the pointer always has focus.
- **Focus strictly under mouse.** The same, and when the pointer is over no window, no window has
  focus.

The last two carry a warning, shown when you hold the pointer over them in the menu: *The desktop
warns against this one: it breaks the window switcher, and a tiling script that navigates by
keyboard goes with it.*

**Delay focus by** is how long the pointer rests on a window before that window takes focus, from
0 to 3000 ms. KyprX's default: 50 ms.

**Focus stealing prevention** decides whether a window that opens takes focus from the one you are
using. It has five levels: **None — a new window always takes focus**, **Low**, **Medium**,
**High** and **Extreme — nothing takes focus unless you give it**. KyprX's default: Low.

**Separate screen focus** makes each screen remember its own focused window. It needs a second
monitor. KyprX's default: on.

Two of these are greyed under some policies, because the desktop ignores them there:

- **Delay focus by** is greyed under **Click to focus** and **Click to focus (mouse precedence)**.
  Focus comes from the click, and the desktop sets the delay aside.
- **Focus stealing prevention** is greyed under **Focus under mouse** and **Focus strictly under
  mouse**. The desktop treats it as None under those two.

A greyed control keeps its value. Hold the pointer over its name to read why it is greyed.

Raising a window when you click it or point at it is not on this tab. It stays in the desktop's
own settings, under Window Behavior.

## Layouts

One number for each of Krohnkite's twelve layouts, in two columns: **Spiral**, **Quarter** and
**Binary tree** first, then **Tile**, **Monocle**, **Three column**, **Stacked**, **Columns**,
**Spread**, **Floating**, **Stair** and **Cascade**. Each box takes 0 to 20.

The numbers are the order the layout keys walk. **Next Layout** goes from the lowest number to the
highest and then starts again at the lowest; **Previous Layout** goes the other way. Both keys are
on the [Shortcuts](shortcuts.md) tab.

- **0 takes a layout out of the cycle.** It also takes away its key: Krohnkite does not set up a
  layout at 0, so a shortcut that switches straight to that layout does nothing until the layout
  has a number again.
- **Two layouts with the same number** both stay in the cycle, one after the other in the order of
  Krohnkite's own list (Krohnkite).
- **Only 0 to 12 counts.** The boxes go up to 20, but Krohnkite ignores a number above 12 and uses
  its own number for that layout instead
  (KNOWN-ISSUES).

KyprX's default: **Spiral** 1, **Quarter** 2, **Binary tree** 3, and 0 for the other nine. The
layout keys then cycle Spiral, Quarter and Binary tree, and nothing else.

Under the numbers, one line says the cycle they make, in the order the key walks it, for example
*The key cycles: Spiral, Quarter, Binary tree.* It follows the boxes as you change them. A number
above 12 is counted in it as typed, although Krohnkite does not use it. With every layout at 0 the
line says *No layout is in the cycle, so the key does nothing.* Krohnkite then uses Tile alone.

## Gaps

The four screen edges sit in two rows, with **Between windows** under them. Each number goes from
0 to 200 px.

| Setting | KyprX's default | What it changes |
|---|---|---|
| **Top** | 10 px | The space between the top of the screen and the windows. |
| **Bottom** | 10 px | The space between the bottom of the screen and the windows. |
| **Left** | 10 px | The space between the left edge of the screen and the windows. |
| **Right** | 10 px | The space between the right edge of the screen and the windows. |
| **Between windows** | 10 px | The space between one window and the next. |

## When a window moves

**Adjust the layout when a window changes.** When you drag the edge of a tiled window, its
neighbours are resized to make room instead of being overlapped. With it off, the window goes back
to the size of its place when you let go. KyprX's default: on.

**Adjust it while dragging.** The neighbours follow while you drag, not only when you let go.
Greyed while the setting above is off. KyprX's default: on.

**Keep tiling while dragging.** A tiled window you drag stays tiled: dropped anywhere but on
another window, it goes back to its place. With it off, a window dragged away from its place comes
loose and floats where you drop it. Either way, a window dropped on another tiled window swaps
places with it. KyprX's default: on.

**Keep windows on screen.** No window is laid out with part of it off the screen: the tiler moves
it back inside. KyprX's default: on.

## New windows

**Where a new window goes** is where a window that has just opened is put in the layout. Krohnkite
keeps the windows in one order, and each layout places them by that order; in most layouts the first
is the master window. The four answers, and what Krohnkite 0.9.9.2 does with each:

- **Wherever the layout puts it.** The new window goes last. KyprX's default.
- **As the master window.** The new window goes first.
- **Before the focused window.** The new window goes second, right after the first window,
  wherever the focus is.
- **After the focused window.** Krohnkite does not know this answer and treats it as the first
  one: the new window goes last.

So the last two do not do what they say
(KNOWN-ISSUES,
Krohnkite).

**Float utility windows.** Dialogs, splash screens and the small tool windows an application opens
beside itself are left where they are put instead of being tiled. KyprX's default: on.

## Tiled windows

**Limit tile width** stops one window being stretched across a very wide screen. KyprX's default:
off.

**Width limit ratio**, from 0 to 5, is how wide a tiled window may be while the limit is on: the
height of the screen, less its panels, times this number. A wider window is narrowed and centred in
its place. It does not apply in the Monocle layout, and 0 means no limit. Greyed while **Limit tile
width** is off. KyprX's default: 1.6. Its tooltip says the ratio is to the window's own height;
Krohnkite 0.9.9.2 uses the screen's (KNOWN-ISSUES).

**Prevent minimising.** A window cannot be minimised: it comes straight back and takes focus.
KyprX's default: off.

**Maximise in monocle layout.** In the Monocle layout, which shows one window at a time, that window
fills the screen up to its panels, without the gaps. Monocle is not in KyprX's cycle, so this counts
only once Monocle has a number. KyprX's default: on.

**No border on tiled windows.** Tiled windows are drawn without their decoration, the frame around
the window. KyprX's default: off.

## Never tiled

Four lists of windows and screens the tiler leaves alone. Each is typed as entries with commas
between them; an empty field says *comma separated*. A list is written when you press Enter or
leave the field, so a half-typed name never reaches the tiler. Emptying a field empties the list.
KyprX has no default for any of them. How an entry is matched against a window, and whether case
counts, is on Krohnkite.

**Floating window titles.** A window whose title contains one of these floats: the tiler leaves it
where it is put.

**Ignored window classes.** Applications the tiler does not touch at all, named by window class.

**Ignored window titles.** A window whose title contains one of these is not tiled at all.

**Ignored screens.** Screens the tiler leaves alone. Krohnkite 0.9.9.2 takes screen names here,
such as DP-1, and not numbers, although the tooltip says the screens are counted from nought
(KNOWN-ISSUES).

Floating and ignored are not the same. A floating window is still the tiler's, and its **Toggle
Float** key can put it into the layout. An ignored window is left out of the tiler altogether.

**An empty Ignored window classes is not an empty list.** While nothing is written there, Krohnkite
ignores a built-in list of its own, among them `krunner`, `yakuake`, `spectacle` and
`plasmashell`, and the field still shows empty. Whatever is written there replaces that whole list;
it is not added to it (KNOWN-ISSUES).

To float every window of an application, tick its **Float** box on the
[Windows](windows.md#float) tab. That table has one row per window class, and a class is not a
title, which is why floating by title is here.

## Good to know

- **A change here lays every tiled window out again**, unless it is in the Focus box. Krohnkite
  reads its settings only when it starts, so KyprX restarts it after each change, and a tiler that
  has just started lays the whole screen out from scratch
  (Krohnkite). The screen stops
  for a moment while it happens (measured — see the comment in `daemon/writer.py`,
  `Transaction.commit`).
- **On a new install, tiling can start switched off.** Krohnkite is installed switched off, and
  installing KyprX does not switch it on. Until something does, the band is at the top of this tab.
  **Switch tiling back on**, any change on this tab, or **Restore KyprX's defaults…** switches it
  on.
- **KyprX's cycle is put in place once, by itself.** The first time KyprX starts, if the layout
  numbers are still Krohnkite's own order, it changes them to KyprX's cycle. An order somebody
  arranged, even with one number moved, is left as it is
  (how it tells).
