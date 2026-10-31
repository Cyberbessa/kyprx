# Tiling

The Tiling tab sets how KyprX lays windows out: whether it does that by itself as windows open and
close, or leaves you to drop each window into a zone, and where a window that opens goes, down to
one that finds every zone taken; the arrangements a screen is laid out by, and the zone layouts
they are made of, which a dragged window is offered; the space around the windows; and which
windows are never tiled. Above all of that is **Focus**, which decides which window you are typing
into.

KyprX tiles the windows itself, from its part inside the compositor, the program that draws every
window on the desktop. The Focus box is the desktop's own setting
(KDE Plasma). The keys that move the focus and the windows are on
the [Shortcuts](shortcuts.md) tab.

There is no Apply button: each change is written by itself, as everywhere in the window (see
[Changes apply by themselves](README.md#changes-apply-by-themselves)). KyprX's tiling reads a
change straight away and moves the windows it concerns, and nothing else on the desktop is
reloaded for it. A change in the Focus box is the one that has the compositor read its own
settings again.

**KyprX's default**, below, is the value that **Restore KyprX's defaults…** on the
[Settings](settings.md) tab writes. Until something writes a setting, the tab shows the value the
tiling uses when nothing is written, which on this tab is KyprX's default every time. The zone
layouts, the arrangements and the lists of windows have no default of KyprX's: they are yours, and
**Restore KyprX's defaults…** leaves them as they are. The zone layouts and arrangements KyprX
comes with are put back by a button of their own
([The zone layouts and arrangements KyprX comes with](#the-zone-layouts-and-arrangements-kyprx-comes-with)).

Every setting on this tab has a small circled **i** after its name. Hold the pointer over it, or
over the name, for one sentence about what the setting does; clicking the **i** shows the same
sentence.

## When tiling is switched off

The tab has no switch for tiling. KyprX is there to make KDE a tiling desktop, so tiling off is not
one of its settings. To place the windows yourself, switch **Automatic tiling** off instead, on
this tab or with its key (see [Automatic tiling](#automatic-tiling)).

While KyprX's tiling is not running, or runs on from before an update, an orange band runs across
the top of the tab and says why. The band sits above the boxes, so it does not scroll out of sight.
It says one of these:

| The band starts | What it means, and what to do |
|---|---|
| **Tiling is switched off** | Something switched KyprX's tiling off, or nothing ever switched it on: a copy of the desk put back, the KyprX folder, a hand edit, or an update from a version of KyprX from before it tiled the windows itself. **Switch tiling back on**, at the end of the band, switches it back on and changes nothing else. Any change on this tab switches it back on too, together with the change itself |
| **KyprX's part of the compositor is from before the update** | The compositor is still running the part of KyprX it loaded at login, from before an update. That part goes on tiling as it did, with the settings it knows, and what is new on the tab starts at the next login. Log out and back in to start it |
| **KyprX's part of the compositor is not the one that tiles yet** | No part of KyprX in the compositor has asked for the tiling since the background service started: none is running, or one from before KyprX tiled the windows itself. Log out and back in to start the one installed. Where the band stays, the **Problems** box on the [Settings](settings.md#problems) tab says whether that part is installed and switched on |
| **KyprX is off this desk** | **Take KyprX off this desk…** was used. **Put my setup back**, in the band at the top of the window, brings KyprX back ([KyprX is off this desk](README.md#kyprx-is-off-this-desk)) |

Every band but the one about a part from before the update says that nothing on the tab is doing
anything. That is true of every box but Focus: Focus does not depend on KyprX's tiling, and it
works whatever the band says. While the tiling is switched off, or KyprX is off this desk, the
**Float** column on the [Windows](windows.md#float) tab is greyed too, because KyprX tiles nothing
and nothing floats.

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

A greyed control keeps its value. Hold the pointer over its name, or over the **i** after it, to
read why it is greyed.

Raising a window when you click it or point at it is not on this tab. It stays in the desktop's
own settings, under Window Behavior.

## Automatic tiling

The switch that decides whether KyprX lays the windows out by itself, and under it the names KyprX
shows on screen, what a window does as it opens, and how the windows beside a dragged edge follow
it. They are described here in the order the box has them.

**Automatic tiling.** On, KyprX lays the windows out by the screen's arrangement as they open and
close: a window that opens takes a zone, and when one closes the others close up. Off is manual
tiling: windows stay where they are put, and a window dragged through the bar at the top of the
screen, or with Shift held, is offered the zones to drop it in (see
[Dragging a window](#dragging-a-window)). Switched off, every window stays where it is; switched
back on, every window is laid out again. KyprX's default: on. The same switch is in the strip
above the tabs ([Automatic tiling](README.md#automatic-tiling)), one click from any tab; the two
boxes always show the same.

**Toggle Automatic Tiling**, **Meta+T** unless you changed it on the
[Shortcuts](shortcuts.md#layouts) tab, switches it from anywhere, for every screen,
and it stays switched: it changes this same setting, so the box on this tab follows, and so does
the KyprX folder. With **Show names on screen** on, the name card says **Automatic tiling on** or
**Automatic tiling off** on the screen in use ([The name card](#the-name-card)). The key does
nothing while KyprX's tiling is switched off or KyprX is off this desk, and nothing in a dry run,
which writes nothing.

In manual tiling no window is tiled, so the keys that move, resize, swap and float tiled windows do
nothing, and the Arrangements box folds away. The focus keys, the layout keys and Toggle Automatic
Tiling work in both. In manual tiling the layout keys move a screen along
the zone layouts a drag offers, instead of along the arrangements
([The layout keys](#the-layout-keys)).

**Show names on screen.** A card in the middle of the screen, for a moment, that names what **Next
Layout** or **Previous Layout** moves the screen to, the arrangement or, with **Automatic tiling**
off, the zone layout; says that **Toggle Automatic Tiling** switched automatic tiling on or off;
and names the desktop a window is sent to when its arrangement is full
([The name card](#the-name-card)). It is not greyed while **Automatic tiling** is off: the layout
keys move the screen in both. KyprX's default: on.

**Where a new window goes** is where a window that has just opened is put in the screen's order,
and so which zone it takes. The four answers:

- **At the end of the layout.** The new window goes last, into the last zone. KyprX's default.
- **As the master window.** The new window goes first, into the master zone, and every other window
  moves on one place.
- **Before the focused window.** The new window takes the place of the window you were using,
  which moves on one place.
- **After the focused window.** The new window goes straight after the window you were using.

The window you were using is the one focused last before the new one opened. Greyed while
**Automatic tiling** is off.

**When the arrangement is full** is what a window that opens does when its screen already has a
window in every zone of the arrangement's last layout: the fifth window on **Balanced**, whose last
layout is for four. The three answers:

- **Open it on a new desktop.** The window goes to a desktop of its own, made for it, and is tiled
  there (see [A window that opens with every zone taken](#a-window-that-opens-with-every-zone-taken)).
  Making that desktop, and removing it once nothing is on it, each stops the screen for a moment.
- **Let it float over the others.** The window floats in the middle of the screen at three quarters
  of its size, never smaller than it can be, and the tiled windows stay as they are. **Toggle
  Float** tiles it, and it squeezes in. KyprX's default.
- **Squeeze it in by splitting the last zone.** The last zone is split in half along its longer
  side, the new window taking the second half, and again for each window more, up to nine windows
  on the screen (see [Arrangements](#arrangements)).

This is for a window that opens: one that comes back to a full screen, from being minimised, from
floating or from another screen, always squeezes in. Greyed while **Automatic tiling** is off.

**Where a new desktop goes** is where the desktop that **Open it on a new desktop** gives a window
is made. The two answers:

- **After your desktops.** After the last desktop. The desktops you have keep their numbers, so a
  key that goes to a desktop by its number, such as the desktop's own Ctrl+F1 to Ctrl+F4, still
  goes to the same one. KyprX's default.
- **Right after the one it came from.** Straight after the desktop the window opened on, or after
  the desktops KyprX made from that one already, so that they stay together. The desktops after
  them move one place along while it is there.

Where your desktops are in more than one row, either answer moves some of them in the grid for as
long as the new desktop is there: the desktop lays its grid out again, row by row, for one desktop
more, so four desktops in two rows, **1 2** above **3 4**, become **1 2 3** above **4 5** with a
fifth at the end. Until KyprX removes it, **Switch One Desktop to the Left** and **to the Right**,
the desktop's own keys that go up and down, and the pager lead elsewhere from the second row on
(read in KWin's source, not measured). In one row, nothing moves but what comes after the new
desktop.

KyprX removes that desktop once nothing is on it and you have left it. Greyed while **Automatic
tiling** is off, and while **When the arrangement is full** is on anything but **Open it on a new
desktop**.

**Float utility windows.** Dialogs, and the small windows an application opens beside itself, are
left where they are put instead of being tiled. Greyed while **Automatic tiling** is off. KyprX's
default: on.

**Neighbours follow while you drag an edge.** When you drag the edge of a tiled window, the windows
beside it are resized as you go, rather than when you let go. Greyed while **Automatic tiling** is
off. KyprX's default: on.

### The name card

With **Show names on screen** on, KyprX shows a card in the middle of a screen for a little over a
second:

- **Next Layout** or **Previous Layout** pressed with **Automatic tiling** on: on the screen in
  use, the name of the arrangement it moved to, with a picture of that arrangement's zones above
  the name, in the screen's proportions and the master zone the stronger colour, and under the name
  **Arrangement · 3 windows**, the number of windows it lays out on that screen now. With one
  window or none, the picture is the layout for two and the line says **Arrangement**.
- The same keys with **Automatic tiling** off: the name of the zone layout the screen moved to, or
  **Whole screen**, with its zones above the name and **Zones offered when you drag a window**
  under it ([The layout keys](#the-layout-keys)).
- **Toggle Automatic Tiling** pressed: on the screen in use, **Automatic tiling on** with the
  screen's arrangement under it and its zones above, as Next Layout shows them, or **Automatic
  tiling off** with the zone layout a drag offers there now. On a screen KyprX's tiling leaves
  alone, the words alone. The card comes once the setting is written, a moment after the key, and
  only for the key: switching **Automatic tiling** on this tab shows none.
- A window sent to another desktop because its arrangement was full: on the screen it opened on,
  the name of that desktop, and under it the desktop it came from, as in **Work was full**.
- No desktop could be made for it: **No room for another desktop**, and **The window floats**.

The card is sized by its screen, and is at most three fifths of the screen's width: a name too long
for one line is given the room of two, and made smaller until it fits there, so it is never cut. It
is drawn in the desktop's colours, and takes neither the focus nor a click: the keys and the
pointer go on to the windows under it. A card asked for while one shows takes its place, and its
time starts again.

### A window that opens with every zone taken

Under **Open it on a new desktop**, a window that opens on a screen where every zone of the
arrangement's last layout is taken goes to another desktop, which KyprX makes for it, and is tiled
there by the same arrangement.

**Which windows.** An application's own window that KyprX would tile, opening on one desktop that a
screen shows, while no window is being dragged or resized. One that opens within two seconds of a
window taking its screen to a desktop of its own, on that screen and on the desktop it left,
counts as well: it is taken for the rest of a group of windows an application opened at once, and
goes where the first one went. Two seconds is an estimate, not a measurement. Only a tiled window
takes a zone, and a window floating while it waits for room counts as one too
([A window bigger than its zone](#a-window-bigger-than-its-zone)): other floating windows do not
count. A dialog, a utility window, a window on every desktop
or on several, one that opens minimised, and one whose window class comes only after it opens
(until then KyprX cannot tell whether it floats) never go to a new desktop: the ones KyprX tiles
squeeze in. So does a window that comes back to a full screen, one you move onto a full desktop
yourself, and any other that opens on a desktop no screen shows.

**Its name.** The desktop is named after the one the window opened on, with a middle dot and a
number: a window that finds **Work** full goes to **Work · 2**, and once that is full too, the next
goes to **Work · 3**, whether it opened on **Work** or on **Work · 2**. One of those desktops with a
zone free on the window's screen is used before a new one is made, and a new one takes the
smallest number not in use.

**Whether the screen goes with it.** The screen goes to the new desktop, and the window has the
focus there, when you opened the window yourself. Nothing the desktop tells KyprX says who opened a
window: measured in a nested KWin, a window that opens has the focus as it appears, at **Focus
stealing prevention** Low and Medium alike, whether you opened it or it opened by itself. So KyprX
goes by the clock. In the first 30 seconds after its tiling starts, at login or when the tiling is
switched back on, which is when a login opens the applications it starts, a window goes quietly:
the screen stays where it is, the focus goes back to the window you were using, and the name card
says where the window went. Thirty seconds is an estimate of how long a login takes to open them,
not a measurement. A window the desktop does not give the focus as it opens goes quietly at any
time. With two screens, the screens share their desktops, so the other one goes to the new desktop
as well (measured in a nested KWin with two screens).

**When it goes away.** When the last window on a desktop KyprX made closes while a screen shows it,
that screen goes back to the desktop whose name it carries: **Work**, for **Work · 2**. A desktop
KyprX made is removed about three seconds after nothing is on it and no screen shows it. A
minimised window on it counts, and so does a window of another activity; a window on every desktop
does not.
Each window that closes or changes desktop, each desktop that comes or goes, and each switch of
desktop or activity starts the three seconds again, so nothing is removed while you are still
moving between desktops.

**Known by its name.** KyprX knows the desktops it made by their names alone: the exact name of
another desktop, a middle dot with a space on either side, and a whole number from 2. So one that
an earlier session left empty is removed once the tiling starts; one you rename becomes yours, and
KyprX never removes it; and one you name that way yourself, **Work · 2** beside a **Work**, is
taken for KyprX's, and removed once nothing is on it and no screen shows it.

**The limits.**

- The desktop allows 25 desktops at most (measured in a nested KWin). With 25, no desktop is
  made: the window floats in the middle of the screen, and the name card says **No room for
  another desktop** and **The window floats**.
- A window rule that forces a window's desktop, set to **Force** or **Force temporarily**, wins:
  the window stays on that desktop and squeezes in, and the desktop made for it is removed at once
  (measured in a nested KWin, with **Force**). A rule set to **Apply initially**, the first choice
  in KDE's Window Rules settings, or to **Remember** puts the window on its desktop as it opens and
  does not hold it there: it goes to a desktop of its own like any other, and a rule at
  **Remember** then remembers that desktop, which KyprX removes later (read in KWin's source, not
  measured; KNOWN-ISSUES).
- In a dry run no desktop is made or removed: the window floats in the middle of the screen, and no
  card shows
  ([Seeing what a change would do without doing it](../troubleshooting.md#seeing-what-a-change-would-do-without-doing-it)).
- While KyprX's tiling is not running, nothing is removed: a desktop it made stays as it is until
  the tiling runs again.
- Each desktop KyprX made that lived more than a moment leaves a few lines in the desktop's own
  settings file, `~/.config/kwinrc`, after it is gone: the compositor writes them and never takes
  them away (measured in a nested KWin; KNOWN-ISSUES).

### A window bigger than its zone

Some windows cannot be made smaller than a size of their own, their minimum size, and the desktop
does not stop a tiler from making them smaller all the same: the window is then drawn cut off, or
spills over the windows beside it. KyprX never lays a window out smaller than it can be. When a
window's zone is too small for it, KyprX makes room, and stops at the first of these that works:

1. **The lines move.** The line beside the zone moves just far enough, and the windows beside it
   give up that room -- never so much that one of them gets smaller than it can be, nor less than
   5 % of the space the line divides. The lines go back where they were by themselves once the
   window closes or needs less room.
2. **Two windows trade places.** When no line can move far enough, the window swaps places with
   one that fits where it is, such as a tall window into the tall master zone, as long as both fit
   afterwards and no other window loses its room. The two stay in their new places afterwards, as
   after **Move**.
3. **The last one in floats.** When no trade is enough either, one window gives way: of those whose
   leaving lets the others fit, the one that came to that screen last -- the window that needed
   the room, or another that came after it. It floats in the middle of the screen, at three
   quarters of the screen's size and never smaller than it can be, and comes to the front once,
   above the tiled windows, without taking the focus. It
   is not kept on top: click a tiled window, and that one comes over it. It goes back into the
   tiling by itself as soon as there is room -- when a window closes, is minimised or floats, or
   the screen goes to another arrangement.

A window too big for the screen even on its own floats at once, whenever it came; one wider or
taller than the screen starts at the screen's left or top edge, so that its title bar can be
reached.

**The one that came last** is the window that joined that screen's tiling last. A window
minimised and brought back keeps its place in that order. A window floated by **Toggle Float**
or by a rule -- a title or class set to float or never to tile, for instance a title that changes
to one of those and back -- joins again as the last one when it
asks for its zone again, and floats if there is still no room; so does the window that floats
when you press Toggle Float on it. A window you are dragging or resizing, and a maximised or
full-screen one, is never moved for room nor the one that floats.

While it floats waiting for room, the window counts as one of the screen's windows for **When the
arrangement is full**. Dragged through the bar at the top of the screen and let go over a zone, it
stays there, floating, and no longer waits. The size keys and a dragged edge start from the lines as you see them, moved for room or
not, and a line you move then stays where you put it, with the lines moved for room
(KNOWN-ISSUES).

### A window that moves itself

Some applications move or resize their own window after it opens, for instance to put it back
where it was the last time. A tiled window that does that goes back to its zone once it has been
still for a moment, a quarter to half a second after its last move. One that keeps doing it is put
back three times in ten seconds at most; after that it is left where its application puts it, and
tried again only once it has been still for ten seconds. A window that answers its zone with a
size of its own, in the zone's top left corner and no larger than the zone -- a terminal that sizes
itself to whole characters -- keeps that size after one more try, for as long as it stays that
size in that corner; moved or grown from there by its application, it is put back again. A window
that grows bigger than its zone gets the room as above.

None of this touches a window you are dragging or resizing, a maximised, full-screen or floating
window, one you put in half the screen with the desktop's own quick-tile keys, or a window its
application moves to another screen, which is tiled there instead. A window its application moved
just before you grabbed it, and that you let go where you grabbed it, goes back to its zone once
it is still. The numbers are estimates, not measurements
(KNOWN-ISSUES).

## Arrangements

An **arrangement** is how automatic tiling divides a screen for each number of windows: the whole
screen for one window, and for two windows and more, one of your zone layouts with that many zones
([Zone layouts](#zone-layouts)), up to the last one it has. A window that opens when every zone of
that last layout is taken does what [When the arrangement is full](#automatic-tiling) says: by
default, it floats over the others. A window that squeezes in, as one that comes back to a full
screen always does, is fitted by cascading from the last layout: the last zone is split in half
along its longer side, the newest window taking the second half, and again for each window more.

**A screen lays out nine windows at most.** A tenth that joins it -- whatever **When the arrangement
is full** says, since a window that comes back always squeezes in -- floats in the middle of the
screen, waiting for room, as a window bigger than its zone does
([A window bigger than its zone](#a-window-bigger-than-its-zone)), and is tiled again by itself as
soon as one of the nine goes. Nine is the most an arrangement has layouts for, and the most windows
whose room KyprX was measured working out quickly: past it, working out the room again at every
window that opened or closed froze the screen.

Each screen is on one arrangement, and **Next Layout** and **Previous Layout**, the layout keys,
move the screen in use to the next or the previous one in the rotation while **Automatic tiling**
is on (see [The layout keys](#the-layout-keys) and
[Each screen and desktop on its own](#each-screen-and-desktop-on-its-own)). On a screen KyprX's
tiling leaves alone they do nothing ([Ignored screens](#never-tiled)).

**With Automatic tiling off** no window is laid out by an arrangement, and the box folds to its
title and one line: **Arrangements are used by automatic tiling, which is off.** What it holds
stays as it is, and the box opens again with the switch.

### The list

A table with one row per arrangement: **Arrangement**, its name, and **In rotation**, a tick. The
layout keys walk the ticked arrangements, in the order of this list; the column's title and each
tick say so when the pointer rests on them. One of them at least stays ticked: unticking the last
one is refused, and a line in the box says why. A name is shown in that line, and in the box's
questions, exactly as it is spelled. With the keyboard, the arrow keys move in the table, Space
ticks **In rotation**, and Tab goes on to the buttons under it.

Under the table:

- **Add…** asks for a name and puts a new arrangement at the end of the list, in the rotation,
  with the whole screen for one window and, for two, the first of the zone layouts with two zones:
  **Two halves**, as KyprX comes.
- **Duplicate** puts a copy of the selected arrangement straight after it, called after it with
  *copy* at the end, to change without losing the one it came from. The copy uses the same zone
  layouts, so a change to one of them changes both, as the line in the box says: **Balanced copy
  uses the same zone layouts as Balanced.** How to give either one a zone layout of its own is
  below ([A layout for each number of windows](#a-layout-for-each-number-of-windows)).
- **Rename…** gives the selected arrangement another name. Each screen stays on the arrangement it
  is on.
- **Move up** and **Move down** move it in the order the layout keys walk the rotation in.
- **Delete…** asks **Delete this arrangement?** first, with **No** already chosen, and there is no
  way back. The zone layouts it uses stay under Zone layouts. It is greyed for the only
  arrangement, and for the only one in the rotation; hold the pointer over it to read why. A screen
  that was on the deleted arrangement goes to the first one in the rotation.

A name is 1 to 40 characters long, and two arrangements cannot have the same name, whatever the
case of its letters. An arrangement and a zone layout may share one.

### A layout for each number of windows

Under the list, a heading names the selected arrangement, as **Balanced, by number of windows**,
with a small circled **i** after it, as each heading in the box has. Under it is a card for each of
its layouts, from one window up, drawn in your screen's proportions: **1 · Whole screen**, then the
zone layout it uses for each number of windows, as **2 · Two halves**. In every picture each zone
carries a number, the order windows fill the zones in, and the zone filled first, the **master
zone**, is washed in the desktop's highlight colour; a tick in the corner of a picture means a drag
offers that zone layout ([Dragging a window](#dragging-a-window)). One window always has the whole
screen, so clicking its card chooses nothing, and the line in the box says **One window always has
the whole screen.** The last card of the row, a dashed outline with a plus in it, is named for one
window more than the last layout, as **5 windows**, and adds the layout for that many windows.

Click any other card to choose what the arrangement uses for that many windows. Further down, a
heading such as **Layout for 3 windows** shows every zone layout with that many zones, in the order
of the Zone layouts box, with the one in use ringed: click another to use it in its place. The zone
layout itself is not changed, nor any other arrangement. Under them:

- **Edit in Zone layouts** selects the zone layout in use in the Zone layouts box below, and
  scrolls down to it.
- **Remove this layout**, beside it on the arrangement's last layout alone, takes that layout
  away, and the zone layout stays under Zone layouts. A window that opens past the new last one
  then does what **When the arrangement is full** says, and one that comes back squeezes in. The
  choice stays open, with none ringed and the plus card ringed, so another can be chosen for that
  number of windows at once.

**The layout for one window more.** Click the plus card, and it is ringed, with the same choice
under it: the zone layouts with that many zones, none ringed. The one clicked is added. When none
has that many zones, the box says so, as **No zone layout has 6 zones yet. Make one under Zone
layouts.**, and adds nothing: make one there, with **Add…** or **Duplicate** and the builder, and
come back to choose it.

**A zone layout of this arrangement's own.** One zone layout can serve several arrangements, and a
change to it changes every arrangement that uses it. To change one for this arrangement alone,
press **Edit in Zone layouts**, then **Duplicate** in the Zone layouts box, and choose the copy
here: no other arrangement uses it. The circled **i** after **Layout for** *N* **windows** says the
same.

An arrangement has layouts for up to 9 windows. Once it has the one for 9, the plus card, **10
windows**, adds nothing: it is not greyed, and clicking it says why in the line, as its tooltip
does. A tenth window that opens does what **When the arrangement is full** says, and one that comes
back waits for room, floating, as every window past nine on a screen does.

## Desktops

The box under Arrangements shows the desktop's virtual desktops, in the desktop's order, one card
each: its name, the arrangement it starts on, and that arrangement's last layout drawn above them.
Click a card for a menu of the arrangements: choose one, and every screen showing that desktop goes
to it at once, and starts on it from then on, after every login too; **First in the rotation**,
first in the menu with that arrangement's name beside it, is what a desktop with no choice starts
on. A card is ringed while its desktop has a choice of its own. The pointer resting on a card says
what it starts on.

- **Next Layout** and **Previous Layout** still move a screen on from its desktop's arrangement, as
  far as the next login; the box goes on showing the choice, which is where the desktop starts.
- **By name.** A desktop is known here by its name, so renaming it in the desktop's settings puts
  it back on the first in the rotation until you choose again. A choice made for a name this
  computer does not have -- carried by a KyprX folder another computer shares -- stays, and applies
  to a desktop given that name.
- **The desktops KyprX makes** for a window that finds every zone taken are not listed: they start
  on the arrangement of the desktop they were made from
  ([A window that opens with every zone taken](#a-window-that-opens-with-every-zone-taken)).
- **Every screen and every activity** showing a desktop starts on its choice.
- **An arrangement deleted** under Arrangements leaves the desktops chosen for it on the first in
  the rotation.

The box folds with **Automatic tiling** off, as Arrangements does, since no window is laid out by
an arrangement then. When the desktop could not be asked which desktops it has, the box says so and
lists none. The choice travels in the KyprX folder's `tiling.json`, and **Restore KyprX's
defaults…** leaves it as it is, as it leaves the arrangements.

## Zone layouts

A **zone layout** is one way of dividing a screen, into two zones to nine, under a name. The zone
layouts are one list, and serve twice. The arrangements are made of them: each uses one for each
number of windows, and one zone layout can serve several arrangements, for as many windows as it
has zones. And the ones with **Offer on drag** on are what a dragged window is offered
([Dragging a window](#dragging-a-window)), and what the layout keys walk while **Automatic tiling**
is off ([The layout keys](#the-layout-keys)). So the box stays open with **Automatic tiling** off.

It starts with a card for each zone layout, in their order: its picture, its name under it on two
lines at most, and a tick in the corner of the picture when a drag offers it. The pointer resting
on a card shows its whole name, its number of zones, whether a drag offers it and which
arrangements use it. Click a card to select it, and the builder below shows it.

Under the cards, two rows of buttons:

- **Add…** asks for a name and puts a new zone layout at the end: two halves side by side, to start
  from. A drag does not offer it until **Offer on drag** is on, and no arrangement uses it until
  one is given it under Arrangements; the line in the box says so.
- **Duplicate** puts a copy of the selected zone layout straight after it, called after it with
  *copy* at the end. No arrangement uses the copy. A drag offers it when it offers the one it
  copied, while fewer than twelve are offered.
- **Rename…** gives the selected zone layout another name. The arrangements that use it go on
  using it.
- **Move left** and **Move right** move it in the order of the list: the order a drag offers them
  in, and the layout keys walk them in.
- **Offer on drag**, first on the second row, stays down while a drag offers the selected zone
  layout, with the same tick the cards wear; click it to turn it on or off. On, it puts the
  zone layout in the bar a drag shows across the top of the screen, and in the list the layout
  keys walk while **Automatic tiling** is off. The bar has room for twelve: a thirteenth is
  refused, and so is turning it off on the last one, which a drag needs. The line in the box says
  why, and the button goes back as it was. Its tooltip says what it does, and that the bar has
  room for twelve.
- **Delete…**, at the far end of the second row, asks **Delete this zone layout?** first, with
  **No** already chosen, and there is no way back. It is greyed while an arrangement uses the zone
  layout, and its tooltip then names every one that does, so that another can be chosen there
  first; and it is greyed for the only zone layout a drag offers.

A name is 1 to 40 characters long, and two zone layouts cannot have the same name, whatever the
case of its letters.

### The builder

Under the buttons, the selected zone layout's name and its number of zones, as **Two halves · 2
zones**, and under them the zone layout, large, with what can be done to it beside it. The pointer
resting on it says what its numbers and its washed zone mean.

- **Choose a zone** by clicking it: it is ringed. A right-click on a zone opens a menu with the
  four buttons below.
- **Split side by side** and **Split top to bottom** split the chosen zone in two: the zone keeps
  the first half, and the new zone, the second, is the one chosen next. A zone in a row of zones
  side by side, split side by side, becomes one more zone of that row, and gives the new one half
  of its share; split top to bottom, it becomes two zones of its own, one above the other. A zone
  in a column works the same way round.
- **Remove this zone** takes the chosen zone away. Its space goes to the part before it in its row
  or column, a zone or a group of zones, or to the one after it when it is the first, so every
  other part keeps its size; a row or a column left with one part becomes that part. When the
  master zone is removed, the zone that takes its space is the master zone from then on. A zone
  layout keeps two zones at least.
- **Make master zone** makes windows fill the chosen zone first, then the others in order. It is
  greyed when the chosen zone is the master zone already.
- **The dividers** are the lines between two parts, each with a grip in its middle. Drag one to
  move it: only the two parts on either side of it give or take, and every other part keeps its
  size. The card and the number beside the builder follow while you drag, and the change is
  written when you let go. Esc during the drag puts the divider back where it was, and does not
  close the window.
- **The percentage box** beside the builder, **Left of the divider:** or **Above the divider:**, is
  the share of the part before the divider chosen, in whole percent. Type a number to move the
  divider there: again only the part across it gives or takes. Clicking a divider chooses it, and
  clicking a zone chooses the zone's own divider. With no divider chosen, the box shows a dash.

**A zone layout an arrangement uses keeps its number of zones**, because the arrangement uses it
for that many windows. While one does, a short line under the builder names every arrangement that
uses it, as **Used by Balanced, Centred Three Columns and Dwindle for 2 windows.**, and the pointer
resting on that line says the rest: **Balanced, Centred Three Columns and Dwindle use it for 2
windows, so it keeps its 2 zones. Moving a divider or choosing another master zone changes each of
them as well.** The two split buttons and **Remove this zone** are greyed, and say the same.
**Make a copy to change**, beside the line, puts a copy straight after it that no arrangement uses,
and selects it: that one can be split and lose a zone, and under Arrangements it can then be given
to an arrangement for as many windows as it has zones.

**How far the builder goes:**

- A zone layout has 2 to 9 zones.
- Every part keeps 5 % of the row or column it is in at least, so a zone of less than 10 % cannot
  be halved along it.
- Splits go 6 deep at most: a part split inside a part, six times over.
- The box adds no zone layout past 32. **Add…**, **Duplicate** and **Make a copy to change** are
  greyed then, and say how many to delete first. Arrangements from an earlier KyprX can bring more
  than 32, and more than twelve offered on a drag
  ([Arrangements from an earlier KyprX](#arrangements-from-an-earlier-kyprx)): each is shown and
  can be changed, and no more is offered until fewer than twelve are.

### The zone layouts and arrangements KyprX comes with

Fifteen zone layouts, in this order, and four arrangements made of them. In each zone layout the
master zone is the first on the left, at the top, except in the three centred ones, where it is the
middle column.

| Zones | Zone layout | Offered on a drag | Its zones |
|---|---|---|---|
| 2 | **Two halves** | yes | two halves side by side |
| 2 | **Wide left** | yes | three quarters on the left, a quarter on the right |
| 2 | **Wide right** | no | a quarter on the left, three quarters on the right |
| 2 | **Top and bottom** | no | two halves, one above the other |
| 3 | **Half left, two stacked** | yes | a half on the left, two stacked on the right |
| 3 | **Wide left, two stacked** | no | three quarters on the left, two stacked on the right |
| 3 | **Centred column** | yes | three columns, a quarter, a half and a quarter, the master in the middle |
| 3 | **Three columns** | yes | three columns of a third each |
| 4 | **Four quarters** | yes | four quarters |
| 4 | **Wide left, three stacked** | no | three quarters on the left, three stacked on the right |
| 4 | **Centred column, right split** | no | the centred column's three, the right one split in two |
| 4 | **Spiral** | yes | a half on the left, two stacked on the right, the lower one split side by side |
| 4 | **Four columns** | no | four columns of a quarter each |
| 4 | **Half left, three stacked** | no | a half on the left, three stacked on the right |
| 5 | **Centred column, sides split** | no | the centred column's three, both side ones split in two |

| Arrangement | Two windows | Three windows | Four windows | Five windows |
|---|---|---|---|---|
| **Balanced** | Two halves | Half left, two stacked | Four quarters | |
| **Master 75/25** | Wide left | Wide left, two stacked | Wide left, three stacked | |
| **Centred Three Columns** | Two halves | Centred column | Centred column, right split | Centred column, sides split |
| **Dwindle** | Two halves | Half left, two stacked | Spiral | |

The four are all in the rotation, in this order, and in each the layout for one window is the whole
screen. A screen on one of them offers a drag, to start with, **Four quarters** on Balanced, **Wide
left** on Master 75/25, **Centred column** on Centred Three Columns and **Spiral** on Dwindle
([Dragging a window](#dragging-a-window)).

**Put KyprX's zone layouts and arrangements back…**, alone at the bottom of the Zone layouts box,
replaces every zone layout and every arrangement with these, the two together, because the
arrangements name the zone layouts they use. It asks **Put KyprX's zone layouts and arrangements
back?** first, with **No** already chosen, saying which of yours go, which of KyprX's own come back
as they came, and whether either list goes back to KyprX's order. A copy of the desk is kept first,
so **Go back to a copy…** on the [Settings](settings.md#go-back-to-a-copy) tab brings yours back.
It is sent the moment you answer, and not a moment later as an edit is, so that an edit made
straight after it never takes its place before that copy is kept. It is greyed when there is
nothing to put back: what the boxes show is KyprX's own, and nothing is stored for them on the
desk.

### Arrangements from an earlier KyprX

An earlier KyprX had no zone layouts: each arrangement held its own layouts, one for each number of
windows. A drag offered every layout of the screen's arrangement, in the bar across the top of the
screen, and to start with the zones of the one the arrangement chose in a setting called **Zones
for manual tiling**. A desk, a KyprX folder or a copy of the desk from then is read as it is, for
as long as there is KyprX, and means this:

- **Each layout is a zone layout.** The zone layouts are KyprX's fifteen, in their order, and then
  one for each layout of an arrangement that none of them is, in the order of the arrangements,
  named after its arrangement and its number of zones: an arrangement called **Writing** with a
  layout of its own for three windows gives **Writing (3 zones)**.
- **One shape is one zone layout.** A layout with the same zones as a zone layout before it, the
  same shares and the same master zone, is that zone layout, whichever arrangement had it. So **Two
  halves**, which Balanced, Centred Three Columns and Dwindle each had for two windows, is one zone
  layout, and moving its divider changes all three, and any arrangement of yours that had the same
  two halves. The line under the builder names them all, and a copy chosen under Arrangements
  gives one of them its own
  ([A layout for each number of windows](#a-layout-for-each-number-of-windows)).
- **A drag offers the zone layouts with Offer on drag on**, whichever arrangement uses them,
  rather than every layout of the screen's arrangement. KyprX's fifteen keep their own, and the
  layout each arrangement's **Zones for manual tiling** chose is offered as well, unless it chose
  the whole screen, which the bar always offers. A layout that is neither leaves the bar until
  **Offer on drag** is turned on for it under Zone layouts ([Zone layouts](#zone-layouts)): on
  KyprX's own arrangements, **Wide left, two stacked** and **Wide left, three stacked**, which a
  screen on Master 75/25 was offered, and **Centred column, right split** and **Centred column,
  sides split**, which one on Centred Three Columns was; and a zone layout made from an arrangement
  of yours, as **Writing (3 zones)** is, unless it was that arrangement's choice.
- **Each screen starts on its arrangement's own zone layout**, the one it uses for the most
  windows that a drag offers ([Dragging a window](#dragging-a-window)). The choice made in **Zones
  for manual tiling** is not carried: where it was a layout for fewer windows than that one, or
  the whole screen, the screen starts on the other one, and the one chosen is in the bar, to be
  picked there.
  KyprX's own four arrangements, as they came, start where they did.
- **Nothing is rewritten** until something is edited in the Arrangements or the Zone layouts box,
  or zone layouts and arrangements this KyprX wrote reach the desk, from the KyprX folder or a
  copy of the desk. Until then the desk and the KyprX folder keep the text the earlier
  KyprX wrote, which an earlier KyprX sharing the folder reads still, and a change such a KyprX
  makes there comes onto this desk as it was made, its **Zones for manual tiling** included. From
  the first edit on, they hold zone layouts and arrangements in the form this KyprX writes, which
  an earlier KyprX refuses
  (KNOWN-ISSUES).

### When the boxes cannot be used

An orange line at the top of the Zone layouts box says so, once for both boxes, and nothing in
either can be changed:

- **The zone layouts and arrangements stored on this desk cannot be read:** followed by what is
  wrong with them. Somebody edited them by hand, for instance, even into a text holding a number
  too long to read, or nested too deep to read. KyprX tiles with its own meanwhile, and the boxes
  show those. The one thing that can be done is **Put KyprX's zone layouts and arrangements
  back…**, which writes over what is stored.
- **These zone layouts and arrangements were written by a newer KyprX**, so this one changes none
  of them and sends nothing. It tiles with its own meanwhile, and the boxes show those. It offers
  no way to put KyprX's own back either, which would lose what the newer one wrote.
- **The zone layouts and arrangements cannot be read here, so nothing in these boxes is sent.** The
  background service sent nothing this window can read, and the boxes are empty: right after an
  update, it is the service from before the update, until you log out and back in
  ([After updating KyprX](../troubleshooting.md#after-updating-kyprx)). The windows go on being
  tiled meanwhile.

## Dragging a window

**A window you drag goes where you let it go.** While you drag it, a bar of thumbnails runs across
the top of the screen under the pointer: **Whole screen** first, one zone that is the whole
screen, then the zone layouts a drag offers, in the order of the Zone layouts box, the first twelve
of them, and after them the one the screen is on when it is not among those. Under the bar is the
name of the zone layout the screen offers, whether **Show names on screen** is on or off. The bar
shows on every drag with **Automatic tiling** off, and with it on, on the drag of a floating window
-- KyprX's settings window among them.

**KyprX's zones show once the pointer has been through the bar**, and stay until you let go: drag
the window up into the bar and back down, and the zones of the zone layout the screen offers are
drawn over each screen, the zone under the pointer washed in the desktop's highlight colour. A drag
that starts with the pointer in the bar, above it or beside it -- a maximised window taken anywhere
on its title bar -- has to go below the bar first and come back up into it, so pulling a maximised
window down never shows the zones on its own. The zones also show while you hold Shift, for as long
as you hold it, and, with **Automatic tiling** off, after you press **Next Layout** or **Previous
Layout** during the drag ([The layout keys](#the-layout-keys)).

**Pass over a thumbnail** once the zones show, and its zones are the ones offered, on that screen;
the name under the bar is that thumbnail's. The bar stays as the drag first drew it until you let
go. Let go in one of its zones and that zone layout stays on the screen; let go anywhere else -- on
the bar, at the top edge, where there are no zones, or with **Esc** -- and the screen goes back to
the zone layout it had, so that a window dragged up past the bar does not change the zones of every
later drag.

**Which zone layout a screen offers.** Each screen starts on its arrangement's own: of the zone
layouts the arrangement uses, the one for the most windows that a drag offers, or the first zone
layout a drag offers when it uses none of those. It follows the arrangement: when the screen goes
to another arrangement, or **Offer on drag** under Zone layouts or a choice under Arrangements
makes another zone layout the arrangement's own, the screen goes to that one. A zone layout picked
in the bar, or with the layout keys, stays on the screen until then. One that is deleted, or that a
drag no longer offers, sends the screen back to its arrangement's own; **Whole screen**, picked,
stays.

**Let go over a zone**, and the window takes that zone and floats there. A window is never made
smaller than it can be: one whose own minimum size is larger than the zone keeps that size, at the
zone's corner.

**A tiled window** -- one KyprX laid out with **Automatic tiling** on -- shows no bar and no zones
unless you hold Shift. Let go over another tiled window, it swaps places with it, on this screen or
another; let go anywhere else, it goes back to its own place -- as it does over a screen KyprX
leaves alone ([Ignored screens](#never-tiled)). With Shift held it shows the bar and the zones at
once, and let go over a zone it leaves the tiling, and the windows it leaves close up; **Toggle
Float** puts it back. A window KyprX would tile, dragged from an ignored screen and let go on a
screen KyprX tiles, joins that screen's layout at the end. If **Automatic tiling** is switched off
while you drag a tiled window, the rest of that drag is one with it off: the bar shows, and the
zones once the pointer has been through it.

**Esc** during a drag puts the window back where it started, and nothing else happens.

**The top edge maximises.** Drag a window until the pointer touches the top of the screen -- the
top 5 pixels of the area windows can use, or a panel along the top -- and the whole of that area is
washed in the highlight colour and named **Maximize**, under the bar or, where no bar shows, at the
top of the area; let go there and the window is maximised. It does this only while the desktop's
own setting for it is on: **Maximize: Windows dragged to top edge**, on the Screen Edges page of
System Settings, which is on unless you switched it off; a change there counts once the desktop
reads its settings again, which it does when the change is applied. It wins over the bar and the
zones, for any window that can be maximised: a tiled one keeps its place in the layout, and takes
it again when you restore it. The desktop's own action for the top edge stays off while KyprX
tiles, and KyprX does the maximising instead, without the desktop's own animation; the desktop's
tiling at the side edges stays off too (see below).

**Holding Shift** is read from the desktop itself: no part of the desktop tells KyprX which keys are
held, but while Shift is held during a drag, KWin draws an outline of one of its own tiles, and
KyprX hides it and shows its zones instead. Where KWin's own tile layout for the screen is empty,
KWin draws no outline, and Shift shows nothing
(KNOWN-ISSUES). To drag with **Meta** and the left button, which
moves a window by any point of it, hold Meta alone as you press the button and add Shift once the
window moves: with Meta and Shift both held as the button goes down, the desktop starts no move.

**Dragging the edge of a tiled window** moves the line on that side of its zone, and the windows
beside it follow, as you drag or when you let go (see
[Neighbours follow while you drag an edge](#automatic-tiling)). Let go, and the line stays where
you left it, for that number of windows on that screen. Esc while you pull an edge, on its own
without Meta held, puts the window and its neighbours back. The size keys on the
[Shortcuts](shortcuts.md#resize-and-arrange) tab move the same lines from the keyboard.

**The desktop's own screen-edge actions are off while KyprX tiles**: the ones that maximise a
window dragged to the top edge of the screen and tile one dragged to a side edge. They are switched
off in the compositor's memory only, so System Settings still shows them as you set them, and they
are back as soon as KyprX's tiling stops. The top edge's maximise is KyprX's own meanwhile, as
above.

A window KyprX never tiles (see [Never tiled](#never-tiled)) is dragged the desktop's own way, with
nothing of KyprX's but the top edge's maximise; held with Shift, it is the desktop's own tiling,
and the top edge is left to that.

## The layout keys

**Next Layout** and **Previous Layout**, on the [Shortcuts](shortcuts.md#layouts)
tab, act on the screen in use. What they move it along depends on **Automatic tiling**:

- **On**, the rotation: the screen goes to the next or the previous arrangement in it
  ([The list](#the-list)), its windows are laid out again by that one, and it offers a drag that
  arrangement's own zone layout. With **Show names on screen** on, the name card names the
  arrangement.
- **Off**, the bar a drag shows on that screen: **Whole screen**, then the zone layouts a drag
  offers. The arrangement stays as it is and no window moves, so the zones of the zone layout the
  screen is on now are drawn on it for a little over a second, whether **Show names on screen** is
  on or off; with it on, the name card names that zone layout, with **Zones offered when you drag
  a window** under the name. A drag that starts meanwhile takes those zones away and shows its
  own, and a key pressed while a window is being dragged changes the zones that drag offers and
  shows them, as passing through the bar does; the zone layout the key moved to stays, wherever
  you let go.

Both go round: **Next Layout** from the last one to the first, and **Previous Layout** from the
first to the last. On a screen KyprX's tiling leaves alone they do nothing and show nothing
([Ignored screens](#never-tiled)).

## Floating windows

A floating window is left where it is put, and the tiled windows are laid out without it. It is
still KyprX's, though: **Toggle Float** can put it into the tiling, unless noted below. What
floats is decided in three layers, the first one first.

1. **KyprX decides by itself.**
   - **Never tiled at all:** the desktop's own windows that are no application's (panels, the
     desktop itself, menus, tooltips, notifications, on-screen displays and the like), the
     compositor's and KyprX's own overlays, the classes and titles under
     [Never tiled](#never-tiled), and a window that cannot be resized. **Toggle Float** does
     nothing on these.
   - **Always floating:** a window on every desktop, which belongs to no one screen's layout.
     **Toggle Float** does nothing on it either.
   - **Floating, while Float utility windows is on:** dialogs, and the small windows an
     application opens beside itself, such as a tool palette (see
     [Automatic tiling](#automatic-tiling)).
   - **Floating while it waits for room:** when a window's own minimum size is larger than its
     zone and neither moving the lines nor trading places makes the room, one window gives way:
     of those whose leaving lets the others fit, the one that came to the screen last. It floats
     in the middle of the screen, in front once, and goes back into the tiling by itself as soon
     as there is room ([A window bigger than its zone](#a-window-bigger-than-its-zone)).
   - **Floating above the others:** KyprX's own settings window. It opens in the middle of its
     screen at its own size, never more than nine tenths of the screen nor smaller than it can be,
     and stays above the other windows while it floats. A window that opens while it is the
     window you are using, such as the file manager that **Open the folder** opens, goes above it
     until you come back to the settings window. The shortcut cheatsheet and the wallpaper picker,
     which are never tiled, are kept above the other windows too, so either opens over it.
     **Toggle Float** tiles the settings window, which is then no longer kept above, until it
     closes; pressed again, it floats in the middle of the screen at three quarters of its size,
     kept above again. On a screen KyprX's tiling leaves alone, it opens where the desktop puts it.
2. **Your lists.** Every window of a class ticked in the **Float** column of the
   [Windows](windows.md#float) tab, and every window whose title contains one of the **Floating
   window titles** under [Never tiled](#never-tiled). They are read again when a window's class or
   title changes.
3. **Your hand.** **Toggle Float** on the focused window, with **Automatic tiling** on. A tiled
   window floats in the middle of the screen at three quarters of its size, never smaller than it
   can be, and the others close up; pressed again, the window goes back into its place. It wins
   over your lists and over **Float utility windows**, and it lasts until the window closes. On a
   window floating while it waits for room, it asks for the zone again: the window joins as the
   last one in, and floats again if there is still no room. On an ignored screen it does nothing.

## Each screen and desktop on its own

Each screen keeps, for each virtual desktop and each activity, its own arrangement. It keeps
there, too, the order of its windows, the lines between them as you last moved them for each number
of windows, and the zone layout a drag offers there ([Dragging a window](#dragging-a-window)). A
screen starts on the first arrangement in the rotation, and on that arrangement's own zone layout,
and a window that opens on a screen is laid out by that screen's arrangement, the others staying
where they are -- unless its desktop has an arrangement of its own under [Desktops](#desktops),
which it starts on instead. On a desktop KyprX made for a window that found every zone taken, the
window's screen starts on the arrangement and the zone layout of the desktop the window came from
([A window that opens with every zone taken](#a-window-that-opens-with-every-zone-taken)). The
lines KyprX moves by itself to give a window the room it needs are not kept: they go back once
that window closes or needs less. Two windows that traded places for room keep the new order
([A window bigger than its zone](#a-window-bigger-than-its-zone)).

A window is laid out on the activity you are on when it is on that activity or on every activity.
A window only on other activities takes no zone here, is not moved, and is never chosen by the
focus keys. Switching activity lays out the activity you switch to and leaves the other one's
windows where they are; a window on every activity follows you, and joins the end of the order
there, as a window on two desktops does when you switch desktop. A window moved to another activity
leaves the layout here. With no activity manager running, everything works as with one activity.

A minimised window leaves the layout and the others close up; brought back, it takes its place
again. A maximised or full-screen window keeps its place and is not moved, and gets its zone back
when it is made ordinary again.

All of this lasts as long as the session. After you log out, or when the compositor restarts,
every screen starts again on its desktop's arrangement under [Desktops](#desktops), or on the
first in the rotation where none is chosen (KNOWN-ISSUES). The lines you moved for an arrangement are also
forgotten when the layouts it lays a screen out by change, such as another zone layout chosen for
one of its numbers of windows, a layout added or removed, or a divider moved in a zone layout it
uses — even when the change comes in while KyprX's tiling is switched off, as when a copy of the
desk or the KyprX folder puts other ones back.

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

The screen is the part panels leave free. When a panel is added, removed, made bigger or smaller,
or moved to another edge, the tiled windows on every screen on show are laid out again in the space
left. A panel whose visibility setting changes, so that it reserves its strip or stops reserving
it, goes unnoticed until something else lays that screen out
(KNOWN-ISSUES). Two windows side by side are exactly **Between
windows** apart.

## Never tiled

Four lists of windows and screens KyprX's tiling leaves alone. Each is typed as entries with commas
between them; an empty field says *comma separated*. A list is written when you press Enter or
leave the field, so a half-typed name never reaches the tiling. Emptying a field empties the list.
KyprX has no default for any of them.

**Floating window titles.** A window whose title contains one of these floats: it is left where it
is put, and **Toggle Float** can still tile it.

**Ignored window classes.** Applications KyprX's tiling does not touch at all, named by window
class.

**Ignored window titles.** A window whose title contains one of these is not tiled at all.

**Ignored screens.** Screens KyprX's tiling leaves alone, by the name the desktop gives them, such
as DP-1: names, and not numbers. The names are the ones under **Colour from the wallpaper of**, on
[Appearance](appearance.md), and in KDE's display settings. A window on an ignored screen is in no
layout: it is never laid out, no window is ever swapped with it, and resizing its edge leaves no
moved line behind. **Toggle Float**, **Set Master**, **Rotate**, the move keys, the size keys,
**Next Layout** and **Previous Layout** do nothing there, the last two showing no name; the focus
keys still work. No zones are offered there. A tiled window let go
over an ignored screen goes back to its place, and a window KyprX would tile, dragged from an
ignored screen to a screen it tiles, joins that screen's layout at the end. When a screen is let
back in, every window on it goes back into its zone, wherever it was moved or however it was
resized meanwhile.

**How an entry matches.** A class matches a window whose class, or whose program name, is that
entry, whatever the case: `dolphin` and `org.kde.dolphin` both find Dolphin. An entry in square
brackets is a part of the name, so `[term]` finds every class with *term* in it, and an entry with
`*` in it is a pattern, `*` standing for any text. A title entry is a part of the title, and there
the case counts.

**KyprX's own list applies as well**, whatever is written in **Ignored window classes**: a list you
write adds to it and never replaces it. It holds the classes listed under
[Windows that never get the defaults by themselves](windows.md#windows-that-never-get-the-defaults-by-themselves)
— the desktop's shell and launcher, the log-out screen, screenshots, KyprX's overlays, games
through Steam or gamescope, and a few more — and Yakuake and the lock screen besides.

Floating and ignored are not the same. A floating window is still KyprX's, and **Toggle Float** can
put it into the layout. An ignored window is left out of the tiling altogether.

To float every window of an application, tick its **Float** box on the
[Windows](windows.md#float) tab. That table has one row per window class, and a class is not a
title, which is why floating by title is here.

## Good to know

- **A change outside the Focus box asks the compositor for nothing but the tiling reading its
  settings again.** No reload of the desktop is made for it, and the windows that move are the
  ones the change concerns.
- **Restore KyprX's defaults…** writes Focus, everything under **Automatic tiling** and the gaps,
  and switches tiling on. It leaves the zone layouts, the arrangements and the four lists alone.
  **Take KyprX off this desk…** leaves no tiling at all, and keeps the zone layouts and the
  arrangements; the desktops KyprX made for windows stay as they are
  ([Settings](settings.md#take-kyprx-off-this-desk)).
- **Everything on this tab but Focus travels in the KyprX folder's `tiling.json`**; the Float ticks
  of the Windows tab travel with their rows, in `windows.json`
  ([Settings](settings.md#what-is-in-the-folder)).
- **Another tiling script switched on tiles beside KyprX's.** Nothing in KyprX looks for one: a
  tiling script switched on in System Settings, under Window Management, KWin Scripts, lays out the
  same windows as KyprX's own tiling, and the two undo each other's work until one is switched off
  (Known issues).
