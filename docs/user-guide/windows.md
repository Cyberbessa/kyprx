# Windows

The Windows tab is a table with one row for each **window class**: the name the desktop knows an
application's windows by. The windows of one application normally share one class, so three
terminal windows are one row, and what you choose there applies to all three. The class often
looks nothing like the application's name; **Find a window…** is the way round that.

The table lists every class that has a window open now, and every class KyprX has met before:
one it gave its defaults to, or one you ticked a box for here. A
class stays listed after its last window closes, and keeps its settings. The rows are sorted by
class name.

## Above the table

**Show** has two boxes, and they work in opposite directions: ticking **System windows** shows
more rows, and so does unticking **Only open windows**. Each time the window opens they start as
described here.

- **Only open windows** hides the classes that have no window open right now. Their settings are
  kept either way. Ticked by default.
- **System windows** shows the desktop's own windows: the panel, the shell, KyprX's own overlays.
  These are the classes listed under
  [Windows that never get the defaults by themselves](#windows-that-never-get-the-defaults-by-themselves).
  Unticked by default.

**Find a window…** turns the pointer into the desktop's crosshair, the one its own window rules
settings use. Click any window on screen and its row is selected here and KyprX's own window is
raised.
If the filters were hiding that row, they are widened just enough to show it: the filter text is
cleared, **Only open windows** is unticked or **System windows** is ticked. The button is greyed
while it waits, up to two minutes; after that the window stops waiting but the pointer stays a
crosshair until something is clicked or Esc is pressed, and that click then selects nothing. The
line at the bottom says how it went:

| Line | What happened |
|---|---|
| Click the window you mean. Esc cancels. | The crosshair is up and waiting for a click. |
| Found: *class* | The row of that class is selected. |
| *class* is not a window this table lists. | The desktop named a class the table does not have. |
| Nothing picked. | Esc was pressed. |
| That is part of the desktop rather than a window. Try another. | The click landed on something that is not a window. |
| The desktop did not take the request. | The request could not be sent to the desktop. |
| The desktop did not say which application that is. | The desktop answered without a class. |
| Nothing picked: *reason* | Any other failure, including the wait running out. |

The **filter** field shows only the rows whose class or window title contains what you type,
whatever the case. It changes nothing else, and its clear button empties it.

## The table

Nine columns, in this order: **Window class**, the six settings **Hide title bar**,
**Transparency**, **Opacity**, **Blur**, **Float** and **Animate**, then **Status** and
**Title**. Hover a column's header for a one-line reminder of what it does. Hover a greyed box to
see why it is greyed on that row.

Every change, ticking or unticking, reaches the windows that are already open at once, both ways:
no reopening, no logging out (measured; see the comment in `daemon/reload.py`).

### The boxes in the column headers

**Hide title bar**, **Transparency** and **Blur** each have a box in their header, before the
column's name. It shows what a new window gets. Clicking it -- the box, not the name beside it --
changes that column for every window at once and for every window that opens from now on:

- every application KyprX has met and looks after gets the new tick at once, open or not, and
  nothing else changes. Blur's box reaches the see-through windows: the blur of an opaque one is
  not seen and is left for when it is see-through again;
- a new application gets it when it first opens, while **Adjust new windows** above the tabs is
  ticked;
- a cell you set by hand stays as you set it (below).

With a cell of one of those columns selected, **Ctrl+Space** does what clicking its header's box
does; **Space** alone ticks the cell. While the box goes out the table is greyed and the line at
the bottom says so.

**A cell you set by hand.** Tick a row's box so that it differs from its header's box, and that
cell is kept as you set it: a small diamond appears beside it, and the header's box never changes
it again. Tick the cell like the header's box again and the diamond goes: the cell follows its
column from then on. The applications you had set unlike KyprX's defaults before these boxes
existed are kept the same way, so the first click on a header leaves them where they are.

The boxes are greyed while KyprX is off this desk, and Blur's while **Which windows** on the
[Effects](effects.md) tab is **Every window** or **No window**, or **Blur windows** there is off,
as the column's cells are. **Restore KyprX's defaults…** puts the boxes back to KyprX's own
values and leaves the cells you set by hand as they are. KyprX's own overlays and the windows
under [Windows that never get the defaults by themselves](#windows-that-never-get-the-defaults-by-themselves)
are never reached by a header's box.

### Window class

The class, as the desktop names it. It is grey on a system window.

The small mark of two overlapping sheets at the left of every name copies the name to the
clipboard. Clicking anywhere else in the cell selects the row. **Ctrl+C** copies the class of the
selected row. Either way, the line at the bottom says **Copied:** and the name.

### Hide title bar

Ticked, the window has no title bar, and the theme draws the rest: the outline round the window
and its shadow. KyprX's default for a new window: ticked.

The bar is hidden by an entry in Klassy's window-specific overrides
(the override list); when no entry hides it yet,
ticking gives the window an entry of its own. Some applications draw their
own title bar instead of letting the desktop draw one: for those, KyprX also adds a window rule
that gives the window a real title bar, which the entry then hides -- without it the theme has
nothing to draw on. A rule of yours that already does that is used as it is, with `KyprX: ` put
in front of its name. In Klassy's own settings, alike entries next to each other show as one row;
Klassy reads its whole list again for every open window each time the desktop's colours or
settings are reloaded, so a list of one row per window made every wallpaper change freeze the
screen longer. Taking KyprX off the desk or the computer writes the list back one row per window.

Unticking gives the title bar back and takes back what KyprX did for it:

- the window's own entry in Klassy's list goes;
- a `KyprX: ` rule that forced a title bar for this window alone loses the two settings that did
  it; the rule itself goes only when nothing is left in it, and a rule covering other windows too
  is left as it is;
- when an entry that covers other windows too still hides the bar, KyprX gives this window an
  entry of its own that shows it, and leaves the shared entry alone;
- **Transparency**, **Opacity** and **Blur** are not changed.

### Transparency

Ticked, the desktop shows through the window, at the number in the **Opacity** column. KyprX's
default for a new window: ticked.

Ticking writes a window rule that sets how solid the window is, focused or not. Nothing is
written when a rule already draws the window at that number; the tick shows whether anything
makes the window see-through now, KyprX's rule or one of your own. Unticking writes a rule that
makes the window fully opaque, 100 %: KyprX does not simply take its own rule away, because a
rule of yours that makes every window see-through would still reach this one.

**At an Opacity of 100 % on the Appearance tab**, a ticked window and an unticked one are drawn
the same way. KyprX keeps the ticks made while the number stands there, and moving it below
100 % puts every kept tick back on the desk on its own, at the new number.

### Opacity

How solid the window is while it is see-through, from 1 to 99 %; 100 % would be opaque. The cell
shows a number on every row but KyprX's own overlays, which show a dash.

- **A dot** in front of the number means it is the **Opacity** number on the
  [Appearance](appearance.md) tab, which every see-through window without a number of its own
  shares. Moving that number moves these windows with it.
- **No dot** means one of two things, and the cell's tooltip says which: the window has a number
  of its own, which the Appearance tab's number, a profile and **Restore KyprX's defaults…** do
  not reach, while applying the KyprX folder puts back whatever numbers it carries; or a window
  rule that KyprX did not write draws it at that number, and KyprX leaves
  it there until you give the window a number of its own.
- **0 %** is a window hidden on purpose, such as KDE's screen-sharing helper
  (`xwaylandvideobridge`). KyprX leaves it at 0 %, whoever's rule holds it, its own included:
  the Appearance tab's number never reaches it.
- **The ▾ after the number** means the cell can be clicked.

Click the number, right-click it, or select it and press Enter, F2 or the menu key:

- **Same as the others — N %**, checked while the window has no number of its own. Choosing it
  takes the window's own number away.
- **95 %**, **90 %**, **85 %**, **80 %**, **75 %** and **70 %**, less the one that equals the
  Appearance tab's number. The window's own number is added to the list when it is not among
  them, and is checked.
- **Other…** asks for any whole number from 1 to 99. For 100 %, untick **Transparency** instead.

The choice is written at once: waiting ticks go out first, then the number. The line at the
bottom says what went in and what it replaced, as *class*: **opacity 92 % → 80 %**. When KyprX
refuses, a box titled **Opacity not changed** says why.

Greyed while **Transparency** is unticked -- the number stays, and ticking **Transparency** brings
it back -- and on a system window: KyprX leaves how solid those are to whoever set it.

### Blur

Ticked, the blur effect blurs whatever is behind the window. KyprX's default for a new window:
ticked.

KyprX adds the class to the blur effect's list of windows, or takes it out. Which way that list
counts is **Which windows** on the [Effects](effects.md) tab. Greyed:

- while **Transparency** is unticked: blur is seen through the window, so on an opaque one there
  is nothing of it to see. Nothing is written for blur in that state, and the tick comes back
  exactly as it was;
- while the Windows tab has no say: **Which windows** on **Every window** or **No window**, or
  **Blur windows** switched off.

### Float

Ticked, every window of this class always floats: KyprX's tiling leaves it where you put it. This
is a standing rule. **Toggle Float** is not the same: it floats one window until that window
closes, and it wins over this tick. How a floating window behaves, and floating by window title,
are on the [Tiling](tiling.md#floating-windows) tab.

KyprX adds the class to its tiling's list of windows that always float. An entry matches the way
the lists on the Tiling tab do: a window whose class, or whose program name, is the class,
whatever the case. A tick moves the windows on its screen at once -- the window floats where it
is or goes back into the layout, and the others make room or close up -- and nothing else on the
desktop is reloaded for it. A new window gets nothing here: it is left as that list already says.

Greyed while KyprX's tiling is switched off or KyprX is off this desk, because then KyprX tiles
nothing and nothing floats
([When tiling is switched off](tiling.md#when-tiling-is-switched-off)). Locked on KyprX's own
overlays, which have to float, and ticked and locked on KyprX's own settings window
([below](#kyprxs-own-overlays)).

### Animate

Ticked, the window animation plays when a window of this class is moved or resized. Unticking it
adds the class to the animation's list of windows it leaves out. A new window gets nothing here.
When nothing has written the list, the animation effect uses a short list of its own, so a few
classes show unticked from the start
(Geometry Change).

Greyed while the animation is switched off altogether, with
**Animate windows as they move and resize** on the [Effects](effects.md) tab.

### Status

Empty on most rows. The first that applies, in this order, wins:

| Status | Meaning |
|---|---|
| **app refuses** (in bold) | The application draws its own title bar and refuses the desktop's, so **Hide title bar** cannot help. See [below](#some-applications-refuse-a-title-bar). |
| **system window** | One of the classes KyprX never adjusts by itself. Shown only while **System windows** is ticked. |
| **not open** | No window of this class is open right now. Shown only while **Only open windows** is unticked. |
| **shared pattern** | The Klassy entry that governs this window is written for other windows too. Changing it here gives this window an entry of its own, copied from the shared one and placed ahead of it, so nothing else changes. |

### Title

The title of an open window of that class. Empty when none is open.

## Ticks go out together

A tick is not sent at once: KyprX waits a moment, and every box ticked in that moment goes out as
one change. While it goes out, the table is greyed and the line at the bottom says
**Applying to N windows…**. Closing the window sends waiting ticks at once. This is what keeps
five **Float** ticks from rearranging the screen five times.

## KyprX's own overlays

The shortcut cheatsheet and the wallpaper picker are windows of KyprX's own. They have rows while
they are open and **System windows** is ticked.

On those rows, **Hide title bar**, **Transparency**, **Opacity** and **Blur** show a grey dash
instead of a box: these windows have no frame on purpose, and KyprX never manages them like an
application. **Float** is locked: the overlays have to float. **Animate** is an ordinary box.

The settings window itself is not an overlay. Its class is `kyprx`, and it is an ordinary row but
for **Float**, which is ticked and locked: while KyprX's tiling runs, the settings window floats
whatever the tiling's list says, opens in the middle of its screen and stays above the other
windows. With **Automatic tiling** on, **Toggle Float** tiles it until it closes. While KyprX's
tiling is not running, the box stays ticked and locked, and its tooltip says so.

## Under the table

The first line under the table is about the **Opacity** column:

- with no window holding a number of its own: **Every see-through window is drawn at N %, the
  number on the Appearance tab. Click a number under Opacity to give one window its own.**;
- otherwise: **Own opacity:** followed by each such window and its number -- each name a link
  that selects its row, widening the filters if they hide it -- then **Every other see-through
  window is at N %, the Appearance tab's.**

A second line, below a thin rule, describes the selected row: the class in bold, then only what
applies -- **KyprX has not set this one up yet**; **set up under the name** *pattern*, shown
whenever the Klassy entry's pattern is not the bare class name -- the entries KyprX writes put
`(^|\s)` before the class and `$` after it, so this shows on every window whose title bar KyprX
hides; **that name covers other windows too, so changing this one here gives it an entry of its
own**, the same case as **shared pattern**; **left alone because it is:** followed by the kind of
window, in the desktop's own words, such as `dock` or `utility`; **its own opacity, N %, which
the Appearance tab's does not reach**; **not open right now**. On an **app refuses** row the line
explains what to do about it. With nothing selected it reads **Nothing selected.**, and when the
filters hide every row, **No window matches what is shown above.**

## What a new window gets

The first time KyprX meets a window class, it gives it KyprX's defaults, where the window does
not already have them. This happens once per class, and only while **Adjust new windows**, above
the tabs, is ticked. After that, whatever you choose on its row stands.

| Column | What a new window gets |
|---|---|
| **Hide title bar** | ticked, with the theme's thin ring round the window, its outline |
| **Transparency** | ticked, at the Appearance tab's **Opacity** number (92 % unless you changed it) |
| **Blur** | ticked |
| **Float** | nothing: left as the tiling's list already says |
| **Animate** | nothing: left as the animation's list already says |

**Float** and **Animate** are never set for a new window. At login every window is new at once,
and each of those lists is one list for every window: writing them then would have KyprX's
tiling, and for the animation's list the whole compositor, read its settings again for nothing.

The boxes in the headers of **Hide title bar**, **Transparency** and **Blur** change these
defaults, and every window met with them. The outline has no control in the window: the one place
to change it is `new_windows` in the `settings.json` file of the KyprX folder
([Settings](settings.md)). **Restore KyprX's defaults…** puts back the ones above.

## Windows that never get the defaults by themselves

These windows are listed like any other, but KyprX's defaults never reach them on their own. You
can still tick their boxes by hand, except on KyprX's own overlays.

**By class.** These are the **system window** rows. They cannot have an **Opacity** number of
their own, and the Appearance tab's number does not reach them. A `*` stands for any text.

| Class | What it is |
|---|---|
| `krunner` | KRunner, the desktop's search and launch bar |
| `plasmashell`, `org.kde.plasmashell` | the Plasma shell: panels, the desktop, widgets |
| `ksplashqml` | the splash screen shown while the session starts |
| `spectacle`, `org.kde.spectacle` | Spectacle, the screenshot tool |
| `xwaylandvideobridge` | the desktop's screen-sharing helper |
| `kwin_wayland` | the compositor itself |
| `ksmserver-logout-greeter` | the log-out screen |
| `org.kde.polkit-kde-authentication-agent-1` | the prompt that asks for your password before an administrator action |
| `kded5`, `kded6` | KDE's background services |
| `kruler`, `org.kde.kruler` | KRuler, the on-screen ruler |
| `kyprx-*` | KyprX's own overlays |
| `gamescope`, `Gamescope` | Gamescope, the compositor games run inside |
| `steam_app_*` | games run through Steam |
| `plasma-interactiveconsole` | Plasma's scripting console |

**By kind of window.** Whatever its class, a window is left alone when it is one of these: a
panel or dock, the desktop itself, a pop-up window, a splash screen, a notification (critical
ones too), a utility window such as a tool palette, a toolbar, a menu of any kind, a tooltip, an
on-screen display such as the volume indicator, a panel widget's pop-up, or the icon being
dragged in a drag and drop. So is any window the desktop does not report as an ordinary
application window. The line under the table names the kind.

## Some applications refuse a title bar

Some applications draw their own title bar, so there is nothing for KyprX to hide. KyprX checks
after setting a window up; when it did not take, the row's **Status** says **app refuses**, and
with **Say when something did not work** ticked on the Settings tab, a desktop notification says
so too. The switch that changes this is inside the application itself -- in the Firefox family,
for example, it is the option to use the system title bar.
[Troubleshooting](../troubleshooting.md#a-window-keeps-its-title-bar) has the details.

Your own Klassy entries and window rules count here like one of KyprX's: an entry you made in
Klassy's own settings shows on the row as it is (which entries count is on the
Klassy page), a window rule of yours that forces a
title bar is used as it is, and **Tidy up rule names** on the [Settings](settings.md) tab puts
KyprX's name on every such rule at once. The first time KyprX meets a class, it still gives it
the defaults where it differs from them.
