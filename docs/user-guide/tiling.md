# Tiling

The Tiling tab sets how KyprX lays windows out: whether it does that by itself as windows open
and close or leaves you to drop each window into a zone; where a window that opens goes, down to
one that finds every zone taken; the arrangements a screen is laid out by, the zone layouts they
are made of, and the arrangement each desktop starts on; the space around the windows; and which
windows are never tiled. Above all of that is **Focus**, which decides which window you are
typing into.

KyprX tiles the windows itself, from its part inside the compositor. The Focus box is the
desktop's own setting (KDE Plasma). The keys that move the focus
and the windows are on the [Shortcuts](shortcuts.md) tab.

Each change is written by itself, as everywhere in the window
([Changes apply by themselves](README.md#changes-apply-by-themselves)). KyprX's tiling reads a
change straight away and moves the windows it concerns, and nothing else on the desktop is
reloaded for it. A change in the Focus box is the one that has the compositor read its own
settings again.

The zone layouts, the arrangements and the lists of windows have no default of KyprX's: they are
yours, and **Restore KyprX's defaults…** leaves them as they are. The ones KyprX comes with are
put back by a button of their own
([The zone layouts and arrangements KyprX comes with](#the-zone-layouts-and-arrangements-kyprx-comes-with)).
Every setting on this tab has a small circled **i** after its name; hold the pointer over it for
one sentence about what the setting does.

## When tiling is switched off

The tab has no switch for tiling: KyprX is there to make KDE a tiling desktop. To place the
windows yourself, switch **Automatic tiling** off instead, on this tab or with its key.

While KyprX's tiling is not running, or runs on from before an update, an orange band across the
top of the tab says why. It sits above the boxes, so it does not scroll out of sight:

| The band starts | What it means, and what to do |
|---|---|
| **Tiling is switched off** | Something switched KyprX's tiling off, or nothing ever switched it on: a copy of the desk, the KyprX folder, a hand edit, or an update from a version before KyprX tiled itself. **Switch tiling back on**, at the end of the band, switches it back on and changes nothing else; any change on this tab switches it back on too, together with the change itself |
| **KyprX's part of the compositor is from before the update** | The compositor still runs the part of KyprX it loaded at login. That part goes on tiling as it did, and what is new on the tab starts at the next login. Log out and back in |
| **KyprX's part of the compositor is not the one that tiles yet** | No part of KyprX in the compositor has asked for the tiling since the background service started. Log out and back in. Where the band stays, the **Problems** box on the [Settings](settings.md#problems) tab says whether that part is installed and switched on |
| **KyprX is off this desk** | **Take KyprX off this desk…** was used. **Put my setup back**, in the band at the top of the window, brings KyprX back ([KyprX is off this desk](README.md#kyprx-is-off-this-desk)) |

Every band but the one about a part from before the update says that nothing on the tab is doing
anything -- true of every box but Focus, which works whatever the band says. While the tiling is
switched off, or KyprX is off this desk, the **Float** column on the
[Windows](windows.md#float) tab is greyed too: KyprX tiles nothing, and nothing floats.

## Focus

The desktop's own four focus settings, the ones in System Settings under Window Behavior, under
the same names. They are at the top of the tab because, with no windows overlapping, the pointer
is how you move between them.

- **Window activation policy** is what it takes for a window to become the one you are typing
  into. The desktop's six answers, under the desktop's own names:

  - **Click to focus.** A window becomes active when you click it.
  - **Click to focus (mouse precedence).** The same, except when the desktop has to pick the next
    window itself, for example after one closes: then it picks the one under the pointer.
  - **Focus follows mouse.** Moving the pointer onto a window makes it active. A window that
    merely appears under the pointer does not take focus that way.
  - **Focus follows mouse (mouse precedence).** The same, and when the desktop has to pick the
    next window itself, it picks the one under the pointer. KyprX's default.
  - **Focus under mouse.** The window under the pointer always has focus.
  - **Focus strictly under mouse.** The same, and when the pointer is over no window, no window
    has focus.

  The last two carry a warning, shown when you hold the pointer over them in the menu: *The
  desktop warns against this one: it breaks the window switcher, and a tiling script that
  navigates by keyboard goes with it.*
- **Delay focus by** is how long the pointer rests on a window before it takes focus: 0 to
  3000 ms. KyprX's default: 50 ms. Greyed under the two click-to-focus policies.
- **Focus stealing prevention** decides whether a window that opens takes focus: **None — a new
  window always takes focus**, **Low**, **Medium**, **High**, **Extreme — nothing takes focus
  unless you give it**. KyprX's default: Low. Greyed under the two under-mouse policies, which
  the desktop treats as None.
- **Separate screen focus** makes each screen remember its own focused window. It needs a second
  monitor. KyprX's default: on.

A greyed control keeps its value; the pointer over its name says why it is greyed. Raising a
window when you click or point at it is not on this tab: it stays in the desktop's own settings.

## Automatic tiling

- **Automatic tiling.** On, KyprX lays the windows out by the screen's arrangement as they open
  and close: a window that opens takes a zone, and when one closes the others close up. Off is
  manual tiling: windows stay where they are put, and a window dragged through the bar at the top
  of the screen, or with Shift held, is offered the zones
  ([Dragging a window](#dragging-a-window)). Switched off, every window stays where it is;
  switched back on, every window is laid out again. KyprX's default: on. The same switch is in
  the strip above the tabs ([Automatic tiling](README.md#automatic-tiling)).
- **Toggle Automatic Tiling**, **Meta+T** unless you changed it, switches it from anywhere, for
  every screen, and it stays switched: the box here follows, and so does the KyprX folder. With
  **Show names on screen** on, the name card says which. The key does nothing while KyprX's
  tiling is switched off or KyprX is off this desk, and nothing in a dry run.
- In manual tiling no window is tiled, so the keys that move, resize, swap and float tiled
  windows do nothing, and the Arrangements box folds away. The focus keys, the layout keys and
  Toggle Automatic Tiling work in both; in manual tiling the layout keys move a screen along the
  zone layouts a drag offers ([The layout keys](#the-layout-keys)).
- **Show names on screen.** A card in the middle of the screen, for a moment, naming what the
  layout keys move the screen to, what Toggle Automatic Tiling did, and the desktop a window is
  sent to when its arrangement is full ([The name card](#the-name-card)). It is not greyed while
  **Automatic tiling** is off. KyprX's default: on.
- **Where a new window goes** is where a window that has just opened is put in the screen's
  order: **At the end of the layout** (KyprX's default), **As the master window** (first, every
  other window moves on one place), **Before the focused window**, or **After the focused
  window**. The window you were using is the one focused last before the new one opened. Greyed
  while **Automatic tiling** is off.
- **When the arrangement is full** is what a window that opens does when its screen already has a
  window in every zone of the arrangement's last layout -- the fifth window on **Balanced**, whose
  last layout is for four:
  - **Open it on a new desktop.** The window goes to a desktop of its own, made for it, and is
    tiled there ([A window that opens with every zone taken](#a-window-that-opens-with-every-zone-taken)).
    Making that desktop, and removing it once nothing is on it, each stops the screen for a
    moment.
  - **Let it float over the others.** It floats in the middle of the screen at three quarters of
    its size, never smaller than it can be. **Toggle Float** tiles it, and it squeezes in.
    KyprX's default.
  - **Squeeze it in by splitting the last zone.** The last zone is split in half along its longer
    side, the new window taking the second half, and again for each window more, up to nine
    windows on the screen.

  This is for a window that opens. One that comes back to a full screen -- from being minimised,
  from floating, from another screen -- always squeezes in. Greyed while **Automatic tiling** is
  off.
- **Where a new desktop goes** is where the desktop of **Open it on a new desktop** is made:
  **After your desktops** (KyprX's default; your desktops keep their numbers, so keys like the
  desktop's own Ctrl+F1 to Ctrl+F4 still go to the same one) or **Right after the one it came
  from** (and after the desktops KyprX made from that one already, so that they stay together;
  the desktops after them move one place along while it is there). With your desktops in more
  than one row, either answer moves some of them in the grid while the new desktop is there: the
  desktop lays its grid out again row by row, so **1 2** above **3 4** becomes **1 2 3** above
  **4 5** with a fifth at the end; until KyprX removes it, **Switch One Desktop to the Left**
  and **to the Right**, the desktop's own keys that go up and down, and the pager lead elsewhere
  from the second row on (read in KWin's source, not measured). In one row, nothing moves but
  what comes after the new desktop. KyprX removes the
  desktop once nothing is on it and you have left it. Greyed while **Automatic tiling** is off
  and while **When the arrangement is full** is on anything but **Open it on a new desktop**.
- **Float utility windows.** Dialogs, and the small windows an application opens beside itself,
  are left where they are put instead of being tiled. KyprX's default: on.
- **Neighbours follow while you drag an edge.** When you drag the edge of a tiled window, the
  windows beside it are resized as you go, rather than when you let go. KyprX's default: on. The
  last two are greyed while **Automatic tiling** is off.

### The name card

With **Show names on screen** on, KyprX shows a card in the middle of a screen for a little over
a second:

- a layout key pressed with **Automatic tiling** on: the arrangement's name, a picture of its
  zones above in the screen's proportions, the master zone the stronger colour, and
  **Arrangement · 3 windows** under the name. With one window or none, the picture is the layout
  for two and the line says **Arrangement**;
- the same keys with it off: the zone layout's name, or **Whole screen**, with its zones above
  and **Zones offered when you drag a window** below;
- **Toggle Automatic Tiling** pressed: **Automatic tiling on** with the screen's arrangement, or
  **Automatic tiling off** with the zone layout a drag offers there. On a screen KyprX's tiling
  leaves alone, the words alone. The card comes once the
  setting is written, a moment after the key; switching the box on this tab shows none;
- a window sent to another desktop because its arrangement was full: on the screen it opened on,
  the name of that desktop, and under it the desktop it came from, as in **Work was full**;
- no desktop could be made: **No room for another desktop**, and **The window floats**.

The card is sized by its screen and is at most three fifths of its width; a name too long for one
line is given two and made smaller, so it is never cut. It is drawn in the desktop's colours and
takes neither the focus nor a click. A card asked for while one shows takes its place.

### A window that opens with every zone taken

Under **Open it on a new desktop**, a window that opens on a screen where every zone of the
arrangement's last layout is taken goes to another desktop, made for it, and is tiled there by
the same arrangement.

**Which windows.** An application's own window that KyprX would tile, opening on one desktop a
screen shows, while no window is being dragged or resized. One that opens within two seconds of a
window taking its screen to a desktop of its own, on that screen and on the desktop it left,
counts as well: it is taken for the rest of a group of windows an application opened at once,
and goes where the first one went (two seconds is an estimate). Only a tiled window takes a zone, and a window floating while
it waits for room counts as one too; other floating windows do not. A dialog, a utility window,
a window on every desktop or on several, one that opens minimised, and one whose window class
comes only after it opens never go to a new desktop: the ones KyprX tiles squeeze in. So does a
window that comes back to a full screen, one you move onto a full desktop yourself, and any other
that opens on a desktop no screen shows.

**Its name.** The desktop is named after the one the window opened on, with a middle dot and a
number: a window that finds **Work** full goes to **Work · 2**, and once that is full too, the
next goes to **Work · 3**, whether it opened on **Work** or on **Work · 2**. One of those with a
zone free on the window's screen is used before a new one is made, and a new one takes the
smallest number not in use.

**Whether the screen goes with it.** The screen goes to the new desktop, and the window has the
focus there, when you opened the window yourself -- nothing the desktop reports says who opened a
window: measured in a nested KWin, a window that opens has the focus as it appears, at **Focus
stealing prevention** Low and Medium alike, whether you opened it or it opened by itself. So
KyprX goes by the clock: in the first 30 seconds after its tiling starts, at login or
when switched back on, a window goes quietly (the screen stays, the focus goes back, the name
card says where it went; 30 seconds is an estimate of how long a login takes to open its
applications). A window the desktop does not give the focus as it opens goes quietly at any time.
With two screens, the screens share their desktops, so the other one goes too (measured in a
nested KWin).

**When it goes away.** When the last window on a desktop KyprX made closes while a screen shows
it, that screen goes back to the desktop whose name it carries: **Work**, for **Work · 2**. A
desktop KyprX made is removed about three seconds after nothing is on it and no screen shows it.
A minimised window counts, and so does a window of another activity; a window on every desktop
does not. Each window that closes or changes desktop, each desktop that comes or goes, and each
switch of desktop or activity starts the three seconds again.

**Known by its name.** KyprX knows the desktops it made by their names alone: another desktop's
exact name, a middle dot with a space on either side, and a whole number from 2. One an earlier
session left empty is removed once the tiling starts; one you rename becomes yours, and KyprX
never removes it; one you name that way yourself, **Work · 2** beside a **Work**, is taken for
KyprX's, and removed once nothing is on it and no screen shows it.

**The limits.**

- The desktop allows 25 desktops at most (measured). With 25, no desktop is made: the window
  floats, and the name card says **No room for another desktop**.
- A window rule that forces a window's desktop, **Force** or **Force temporarily**, wins: the
  window stays and squeezes in, and the desktop made for it is removed at once (measured, with
  **Force**). A rule at **Apply initially** or **Remember** puts the window on its desktop as it
  opens but does not hold it there: it goes to a desktop of its own like any other, and a rule at
  **Remember** then remembers that desktop, which KyprX removes later (read in KWin's source,
  not measured; KNOWN-ISSUES).
- In a dry run no desktop is made or removed: the window floats, and no card shows
  ([Seeing what a change would do without doing
  it](../troubleshooting.md#seeing-what-a-change-would-do-without-doing-it)).
- While KyprX's tiling is not running, nothing is removed.
- Each desktop KyprX made that lived more than a moment leaves a few lines in `~/.config/kwinrc`
  after it is gone: the compositor writes them and never takes them away (measured;
  KNOWN-ISSUES).

### A window bigger than its zone

Some windows cannot be made smaller than a minimum size of their own, and the desktop does not
stop a tiler from making them smaller all the same. KyprX never lays a window out smaller than it
can be. When a window's zone is too small, KyprX makes room, stopping at the first of these that
works:

1. **The lines move.** The line beside the zone moves just far enough, and the windows beside it
   give up that room -- never so much that one of them gets smaller than it can be, nor less than
   5 % of the space the line divides. The lines go back by themselves once the window closes or
   needs less room.
2. **Two windows trade places.** The window swaps with one that fits where it is, a tall window
   into the tall master zone say, as long as both fit afterwards and no other window loses its
   room. The two stay in their new places, as after **Move**.
3. **The last one in floats.** Of those whose leaving lets the others fit, the one that came to
   that screen last floats in the middle of the screen, at three quarters of the screen's size
   and never smaller than it can be, and comes to the front once, above the tiled windows,
   without taking the focus. It is not kept on top. It goes back into the tiling by itself as
   soon as there is room -- when a window closes, is minimised or floats, or the screen goes to
   another arrangement.

A window too big for the screen even on its own floats at once; one wider or taller than the
screen starts at the screen's left or top edge, so its title bar can be reached.

**The one that came last** is the window that joined that screen's tiling last. A window
minimised and brought back keeps its place in that order; a window floated by **Toggle Float**
or by a rule joins again as the last one when it asks for its zone again, and floats if there is
still no room. A window you are
dragging or resizing, and a maximised or full-screen one, is never moved for room nor the one
that floats.

While it floats waiting for room, the window counts as one of the screen's windows for **When
the arrangement is full**. Dragged through the bar at the top of the screen and let go over a
zone, it stays there, floating, and no longer waits. The size keys and a dragged edge start from
the lines as you see them, moved for room or not, and a line you move then stays where you put
it, with the lines moved for room (KNOWN-ISSUES).

### A window that moves itself

Some applications move or resize their own window after it opens. A tiled window that does that
goes back to its zone once it has been still for a quarter to half a second. One that keeps doing
it is put back three times in ten seconds at most; after that it is left where its application
puts it, and tried again once it has been still for ten seconds. A window that answers its zone
with a size of its own, in the zone's top left corner and no larger than the zone -- a terminal
that sizes itself to whole characters -- keeps that size after one more try, for as long as it
stays that size in that corner; moved or grown from there by its application, it is put back
again. A window that grows bigger than its zone gets the room as above.

None of this touches a window you are dragging or resizing, a maximised, full-screen or floating
window, one you put in half the screen with the desktop's own quick-tile keys, or a window its
application moves to another screen, which is tiled there instead. A window its application
moved just before you grabbed it, and that you let go where you grabbed it, goes back to its
zone once it is still. The numbers are estimates, not
measurements (KNOWN-ISSUES).

## Arrangements

An **arrangement** is how automatic tiling divides a screen for each number of windows: the whole
screen for one window, and for two and more, one of your zone layouts with that many zones
([Zone layouts](#zone-layouts)), up to the last one it has. A window that opens when every zone
of that last layout is taken does what [When the arrangement is full](#automatic-tiling) says. A
window that squeezes in, as one that comes back to a full screen always does, is fitted by
cascading from the last layout: the last zone split in half along its longer side, the newest
window taking the second half, and again for each window more.

**A screen lays out nine windows at most.** A tenth that joins it by squeezing in -- as a window
that comes back to a full screen always does, and as one that opens does when **When the
arrangement is full** is on **Squeeze it in by splitting the last zone** -- floats in the middle
of the screen, waiting for room, and is tiled again as soon as one of the nine goes. A tenth
window that opens when that setting is on **Open it on a new desktop** or **Let it float over
the others** does what the setting says. Nine is the most an arrangement has layouts for, and
the most windows whose room KyprX was measured working out quickly: past it, working out the
room again at every window that opened or closed froze the screen.

Each screen is on one arrangement, and **Next Layout** and **Previous Layout** move the screen in
use through the rotation while **Automatic tiling** is on
([The layout keys](#the-layout-keys)). On a screen KyprX's tiling leaves alone they do nothing
([Ignored screens](#never-tiled)). With **Automatic tiling** off the box folds to its title and
one line, and opens again with the switch.

### The list

A table with one row per arrangement: **Arrangement**, its name, and **In rotation**, a tick. The
layout keys walk the ticked ones, in the order of this list; one at least stays ticked, and
unticking the last one is refused. The arrow keys move in the table, Space ticks, Tab goes on to
the buttons.

- **Add…** asks for a name and puts a new arrangement at the end, in the rotation, with the whole
  screen for one window and, for two, the first zone layout with two zones: **Two halves**, as
  KyprX comes.
- **Duplicate** puts a copy of the selected arrangement straight after it, named with *copy* at
  the end. The copy uses the same zone layouts, so a change to one of them changes both; how to
  give either one a layout of its own is under
  [A layout for each number of windows](#a-layout-for-each-number-of-windows).
- **Rename…** gives the selected arrangement another name. Each screen stays where it is.
- **Move up** and **Move down** move it in the order the layout keys walk.
- **Delete…** asks **Delete this arrangement?** first, with **No** already chosen, and there is
  no way back. The zone layouts it uses stay under Zone layouts. It is greyed for the only
  arrangement and for the only one in the rotation. A screen that was on the deleted one goes to
  the first in the rotation.

A name is 1 to 40 characters, and no two arrangements share one, whatever the case of its
letters; an arrangement and a zone layout may.

### A layout for each number of windows

Under the list, a heading names the selected arrangement, as **Balanced, by number of windows**,
with a card for each of its layouts, drawn in your screen's proportions: **1 · Whole screen**,
then the zone layout it uses for each number, as **2 · Two halves**. Each zone carries a number,
the order windows fill the zones in; the zone filled first, the **master zone**, is washed in the
desktop's highlight colour; a tick in the corner of a picture means a drag offers that zone
layout. The card for one window chooses nothing. The dashed plus card at the end, named for one
window more, adds the layout for that many.

Click a card to choose what the arrangement uses for that many windows. Further down, a heading
such as **Layout for 3 windows** shows every zone layout with that many zones, the one in use
ringed; click another to use it in its place -- the zone layout itself is not changed, nor any
other arrangement. Under them:

- **Edit in Zone layouts** selects the zone layout in use in the Zone layouts box and scrolls to
  it.
- **Remove this layout**, on the arrangement's last layout alone, takes that layout away; the
  zone layout stays under Zone layouts. A window that opens past the new last one then does what
  **When the arrangement is full** says, and one that comes back squeezes in. The choice stays
  open, with none ringed and the plus card ringed, so another can be chosen for that number of
  windows at once.

When no zone layout has that many zones, the box says so and adds nothing: make one under Zone
layouts first. To change one zone layout for this arrangement alone, **Edit in Zone layouts**,
**Duplicate** there, and choose the copy here: no other arrangement uses it. An arrangement has
layouts for up to 9 windows. Once it has the one for 9, the plus card, **10 windows**, adds
nothing: it is not greyed, and clicking it says why in the line, as its tooltip does. A tenth
window that opens does what **When the arrangement is full** says, and one that comes back waits
for room, floating, as every window past nine on a screen does.

## Desktops

The box under Arrangements shows the desktop's virtual desktops, in the desktop's order, one card
each: its name, the arrangement it starts on, and that arrangement's last layout drawn above
them. Click a card for a menu of the arrangements; choose one, and every screen showing that
desktop goes to it at once and starts on it from then on, after every login too. **First in the
rotation**, first in the menu, is what a desktop with no choice starts on. A card is ringed
while its desktop has a choice of its own.

- **Next Layout** and **Previous Layout** still move a screen on from its desktop's arrangement,
  as far as the next login; the box goes on showing the choice, which is where the desktop
  starts.
- **By name.** A desktop is known here by its name: renaming it in the desktop's settings puts it
  back on the first in the rotation until you choose again. A choice made for a name this
  computer does not have -- carried by a KyprX folder another computer shares -- stays, and
  applies to a desktop given that name.
- **The desktops KyprX makes** for a window that finds every zone taken are not listed: they
  start on the arrangement of the desktop they were made from.
- **Every screen and every activity** showing a desktop starts on its choice.
- **An arrangement deleted** under Arrangements leaves the desktops chosen for it on the first in
  the rotation.

The box folds with **Automatic tiling** off, as Arrangements does. When the desktop could not be
asked which desktops it has, the box says so and lists none. The choice travels in the KyprX
folder's `tiling.json`, and **Restore KyprX's defaults…** leaves it as it is.

## Zone layouts

A **zone layout** is one way of dividing a screen, into two zones to nine, under a name. The zone
layouts are one list, and serve twice: the arrangements are made of them -- one zone layout can
serve several arrangements -- and the ones with **Offer on drag** on are what a dragged window is
offered ([Dragging a window](#dragging-a-window)) and what the layout keys walk while
**Automatic tiling** is off. The box stays open with **Automatic tiling** off.

It starts with a card for each zone layout, in their order: its picture, its name under it, and a
tick in the corner of the picture when a drag offers it. The pointer resting on a card shows its
whole name, its number of zones, whether a drag offers it and which arrangements use it. Click a
card to select it; the builder below shows it. Under the cards, two rows of buttons:

- **Add…** asks for a name and puts a new zone layout at the end: two halves side by side, to
  start from. A drag does not offer it until **Offer on drag** is on, and no arrangement uses it
  until one is given it.
- **Duplicate** puts a copy of the selected zone layout straight after it, named with *copy* at
  the end. No arrangement uses the copy. A drag offers it when it offers the one it copied, while
  fewer than twelve are offered.
- **Rename…** gives it another name; the arrangements using it go on using it.
- **Move left** and **Move right** move it in the order a drag offers them in and the layout keys
  walk them in.
- **Offer on drag** puts the zone layout in the bar a drag shows across the top of the screen.
  The bar has room for twelve: a thirteenth is refused, and so is turning it off on the last one,
  which a drag needs.
- **Delete…** asks first, and there is no way back. It is greyed while an arrangement uses the
  zone layout (its tooltip then names every one that does), and for the only zone layout a drag
  offers.

A name is 1 to 40 characters, and no two zone layouts share one, whatever the case of its
letters.

### The builder

Under the buttons, the selected zone layout's name and its number of zones, and under them the
zone layout, large. **Choose a zone** by clicking it; a right-click on a zone opens a menu with
the four buttons below.

- **Split side by side** and **Split top to bottom** split the chosen zone in two; the new second
  half is the one chosen next. A zone in a row of zones side by side, split side by side, becomes
  one more zone of that row; split top to bottom, two zones of its own, one above the other. A
  zone in a column works the same way round.
- **Remove this zone** takes the chosen zone away, its space going to the part before it in its
  row or column, or to the one after it when it is the first, so every other part keeps its size.
  When the master zone is removed, the zone that takes its space is the master from then on. A
  zone layout keeps two zones at least.
- **Make master zone** makes windows fill the chosen zone first, then the others in order.
- **The dividers** are the lines between two parts. Drag one to move it: only the two parts on
  either side give or take. The change is written when you let go; Esc during the drag puts the
  divider back, and does not close the window.
- **The percentage box** beside the builder, **Left of the divider:** or **Above the
  divider:**, is the share of the part before the chosen divider, in whole percent. Type a number
  to move the divider there. Clicking a divider chooses it, and clicking a zone chooses the
  zone's own divider. With no divider chosen, the box shows a dash.

**A zone layout an arrangement uses keeps its number of zones**, because the arrangement uses it
for that many windows. While one does, a line under the builder names every arrangement that uses
it, the pointer over that line says the rest, the two split buttons and **Remove this zone** are
greyed, and **Make a copy to change**, beside the line, puts a copy straight after it that no
arrangement uses and selects it.

**How far the builder goes:** 2 to 9 zones; every part keeps 5 % of its row or column at least,
so a zone of less than 10 % cannot be halved along it; splits go 6 deep at most; the box adds no
zone layout past 32: **Add…**, **Duplicate** and **Make a copy to change** are greyed then, and
say how many to delete first. Arrangements from an earlier KyprX can bring more than 32, and more than
twelve offered on a drag
([Arrangements from an earlier KyprX](#arrangements-from-an-earlier-kyprx)): each is shown and
can be changed, and no more is offered until fewer than twelve are.

### The zone layouts and arrangements KyprX comes with

Fifteen zone layouts, in this order, and four arrangements made of them. In each, the master zone
is the first on the left, at the top, except in the three centred ones, where it is the middle
column.

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

The four are all in the rotation, in this order, and in each the layout for one window is the
whole screen. A screen on one of them offers a drag, to start with, **Four quarters** on
Balanced, **Wide left** on Master 75/25, **Centred column** on Centred Three Columns and
**Spiral** on Dwindle ([Dragging a window](#dragging-a-window)).

**Put KyprX's zone layouts and arrangements back…**, alone at the bottom of the Zone layouts box,
replaces every zone layout and every arrangement with these, the two together, because the
arrangements name the zone layouts they use. It asks **Put KyprX's zone layouts and arrangements
back?** first, with **No** already chosen, saying which of yours go, which of KyprX's own come
back as they came, and whether either list goes back to KyprX's order. A copy of
the desk is kept first, so **Go back to a copy…** on the
[Settings](settings.md#go-back-to-a-copy) tab brings yours back. It is sent the moment you
answer -- not a moment later, as an edit is, so that an edit made straight after never takes its
place before that copy is kept. It is greyed when there is nothing to put back.

### Arrangements from an earlier KyprX

An earlier KyprX had no zone layouts: each arrangement held its own layouts, a drag offered every
layout of the screen's arrangement, and a setting called **Zones for manual tiling** chose where
a drag started. A desk, a KyprX folder or a copy from then is read as it is, and means this:

- **Each layout is a zone layout.** The list is KyprX's fifteen, then one for each layout of an
  arrangement that none of them is, named after its arrangement and its number of zones: an
  arrangement called **Writing** with a layout of its own for three windows gives
  **Writing (3 zones)**.
- **One shape is one zone layout.** A layout with the same zones, shares and master zone as one
  before it is that zone layout, whichever arrangement had it: **Two halves** is one zone layout
  however many arrangements had it, and moving its divider changes all of them.
- **A drag offers the zone layouts with Offer on drag on**, whichever arrangement uses them,
  rather than every layout of the screen's arrangement. KyprX's fifteen keep their own, and the
  layout each arrangement's **Zones for manual tiling** chose is offered as well. A layout that
  is neither leaves the bar until **Offer on drag** is turned on for it: on KyprX's own
  arrangements, **Wide left, two stacked** and **Wide left, three stacked**, which a screen on
  Master 75/25 was offered, and **Centred column, right split** and **Centred column, sides
  split**, which one on Centred Three Columns was; and a zone layout made from an arrangement of
  yours, as **Writing (3 zones)** is, unless it was that arrangement's choice.
- **Each screen starts on its arrangement's own zone layout**, the one it uses for the most
  windows that a drag offers. The choice made in **Zones for manual tiling** is not carried;
  where it was a layout for fewer windows, or the whole screen, the screen starts on the other
  one, and the one chosen is in the bar. KyprX's own four arrangements, as they came, start
  where they did.
- **Nothing is rewritten** until something is edited in the Arrangements or Zone layouts box, or
  zone layouts and arrangements this KyprX wrote reach the desk, from the KyprX folder or a copy.
  Until then the desk and the folder keep the text the earlier KyprX wrote, which an earlier
  KyprX sharing the folder reads still. From the first edit on, they hold the form this KyprX
  writes, which an earlier KyprX refuses
  (KNOWN-ISSUES).

### When the boxes cannot be used

An orange line at the top of the Zone layouts box says so, once for both boxes, and nothing in
either can be changed:

- **The zone layouts and arrangements stored on this desk cannot be read:** followed by what is
  wrong. Somebody edited them by hand, say. KyprX tiles with its own meanwhile, and the boxes
  show those. The one way out is **Put KyprX's zone layouts and arrangements back…**, which
  writes over what is stored.
- **These zone layouts and arrangements were written by a newer KyprX**: this one changes none of
  them and sends nothing, tiles with its own meanwhile, and offers no way to put KyprX's own
  back, which would lose what the newer one wrote.
- **The zone layouts and arrangements cannot be read here, so nothing in these boxes is sent.**
  The background service sent nothing this window can read, and the boxes are empty: right after
  an update it is the service from before, until you log out and back in
  ([After updating KyprX](../troubleshooting.md#after-updating-kyprx)). The windows go on being
  tiled meanwhile.

## Dragging a window

**A window you drag goes where you let it go.** While you drag it, a bar of thumbnails runs
across the top of the screen under the pointer: **Whole screen** first, then the zone layouts a
drag offers, in the order of the Zone layouts box, the first twelve, and after them the one the
screen is on when it is not among those. Under the bar is the name of the zone layout the screen
offers, whether **Show names on screen** is on or off. The bar shows on every drag with
**Automatic tiling** off, and with it on, on the drag of a floating window -- KyprX's settings
window among them.

**The zones show once the pointer has been through the bar**, and stay until you let go: drag up
into the bar and back down, and the zones of the offered zone layout are drawn over each screen,
the zone under the pointer washed in the desktop's highlight colour. A drag that starts with the
pointer in the bar, above it or beside it -- a maximised window taken anywhere on its title bar --
has to go below the bar first and come back up into it. The zones also show while you hold Shift,
and, with **Automatic tiling** off, after a layout key during the drag.

**Pass over a thumbnail** once the zones show, and its zones are the ones offered, on that
screen. Let go in one of them and that zone layout stays on the screen; let go anywhere else --
on the bar, at the top edge, where there are no zones, or with **Esc** -- and the screen goes
back to the zone layout it had.

**Which zone layout a screen offers.** Each screen starts on its arrangement's own: of the zone
layouts the arrangement uses, the one for the most windows that a drag offers, or the first zone
layout a drag offers when it uses none of those. It follows the arrangement; a zone layout picked
in the bar, or with the layout keys, stays on the screen until then. One that is deleted, or that
a drag no longer offers, sends the screen back to its arrangement's own; **Whole screen**, picked,
stays.

**Let go over a zone**, and the window takes that zone and floats there. A window is never made
smaller than it can be: one whose minimum size is larger than the zone keeps that size, at the
zone's corner.

**A tiled window** -- one KyprX laid out with **Automatic tiling** on -- shows no bar and no
zones unless you hold Shift. Let go over another tiled window and it swaps places with it, on
this screen or another; let go anywhere else and it goes back to its own place, as it does over a
screen KyprX leaves alone. With Shift held it shows the bar and the zones at once, and let go
over a zone it leaves the tiling, the windows it leaves closing up; **Toggle Float** puts it
back. A window KyprX would tile, dragged from an ignored screen and let go on a screen KyprX
tiles, joins that screen's layout at the end. If **Automatic tiling** is switched off while you
drag a tiled window, the rest of that drag is one with it off: the bar shows, and the zones once
the pointer has been through it.

**Esc** during a drag puts the window back where it started, and nothing else happens.

**The top edge maximises.** Drag a window until the pointer touches the top of the screen -- the
top 5 pixels of the area windows can use, or a panel along the top -- and that whole area is
washed in the highlight colour and named **Maximize**, under the bar or, where no bar shows, at
the top of the area; let go there and the window is maximised.
It does this only while the desktop's own setting for it is on: **Maximize: Windows dragged to
top edge**, on the Screen Edges page of System Settings, which is on unless you switched it off;
a change there counts once the desktop reads its settings again, which it does when the change is
applied. It wins over the bar and the zones, for
any window that can be maximised; a tiled one keeps its place in the layout and takes it again
when restored. The desktop's own action for the top edge stays off while KyprX tiles, and KyprX
does the maximising instead, without the desktop's animation.

**Holding Shift** is read from the desktop itself: while Shift is held during a drag, KWin draws
an outline of one of its own tiles, and KyprX hides it and shows its zones instead. Where KWin's
own tile layout for the screen is empty, KWin draws no outline, and Shift shows nothing
(KNOWN-ISSUES). To drag with **Meta** and the left button, hold
Meta alone as you press the button and add Shift once the window moves: with Meta and Shift both
held as the button goes down, the desktop starts no move.

**Dragging the edge of a tiled window** moves the line on that side of its zone, and the windows
beside it follow, as you drag or when you let go, as
[Neighbours follow while you drag an edge](#automatic-tiling) says. Let go, and the line stays
where you left it, for that number of windows on that screen. Esc while you pull an edge, on its
own without Meta held, puts the window and its neighbours back. The size keys on the
[Shortcuts](shortcuts.md#resize-and-arrange) tab move the same lines from the keyboard.

**The desktop's own screen-edge actions are off while KyprX tiles**: the ones that maximise a
window dragged to the top edge and tile one dragged to a side edge. They are switched off in the
compositor's memory only, so System Settings still shows them as you set them, and they are back
as soon as KyprX's tiling stops. The top edge's maximise is KyprX's own meanwhile, as above. A
window KyprX never tiles ([Never tiled](#never-tiled)) is dragged the desktop's own way, with
nothing of KyprX's but the top edge's maximise; held with Shift, it is the desktop's own tiling,
and the top edge is left to that.

## The layout keys

**Next Layout** and **Previous Layout**, on the [Shortcuts](shortcuts.md#layouts) tab, act on the
screen in use. What they move it along depends on **Automatic tiling**:

- **On**, the rotation: the screen goes to the next or previous arrangement, its windows are laid
  out again by that one, and it offers a drag that arrangement's own zone layout. With **Show
  names on screen** on, the name card names the arrangement.
- **Off**, the bar a drag shows on that screen: **Whole screen**, then the zone layouts a drag
  offers. The arrangement stays and no window moves; the zones of the zone layout the screen is
  on are drawn on it for a little over a second, and with **Show names on screen** on, the name
  card names it. A key pressed while a window is being dragged changes the zones that drag offers
  and shows them, as passing through the bar does; the zone layout the key moved to stays,
  wherever you let go.

Both go round, first to last and back. On a screen KyprX's tiling leaves alone they do nothing
and show nothing ([Ignored screens](#never-tiled)).

## Floating windows

A floating window is left where it is put, and the tiled windows are laid out without it. It is
still KyprX's: **Toggle Float** can put it into the tiling, unless noted below. What floats is
decided in three layers, the first one first.

1. **KyprX decides by itself.**
   - **Never tiled at all:** the desktop's own windows that are no application's (panels, the
     desktop itself, menus, tooltips, notifications, on-screen displays), the compositor's and
     KyprX's own overlays, the classes and titles under [Never tiled](#never-tiled), and a window
     that cannot be resized. **Toggle Float** does nothing on these.
   - **Always floating:** a window on every desktop, which belongs to no one screen's layout.
     **Toggle Float** does nothing on it either.
   - **Floating, while Float utility windows is on:** dialogs, and the small windows an
     application opens beside itself, such as a tool palette.
   - **Floating while it waits for room:** see
     [A window bigger than its zone](#a-window-bigger-than-its-zone).
   - **Floating above the others:** KyprX's own settings window. It opens in the middle of its
     screen at its own size, never more than nine tenths of the screen nor smaller than it can
     be, and stays above the other windows while it floats. A window that opens while it is the
     one you are using goes above it until you come back to it. The cheatsheet and the wallpaper
     picker, never tiled, are kept above too, so either opens over it. **Toggle Float** tiles the
     settings window until it closes; pressed again, it floats it in the middle of the screen at
     three quarters of its size, kept above again. On a screen KyprX's tiling leaves alone, it
     opens where the desktop puts it.
2. **Your lists.** Every window of a class ticked in the **Float** column of the
   [Windows](windows.md#float) tab, and every window whose title contains one of the **Floating
   window titles** under [Never tiled](#never-tiled). They are read again when a window's class
   or title changes.
3. **Your hand.** **Toggle Float** on the focused window, with **Automatic tiling** on. A tiled
   window floats in the middle of the screen at three quarters of its size, never smaller than it
   can be, and the others close up; pressed again, it goes back into its place. It wins over your
   lists and over **Float utility windows**, and it lasts until the window closes. On a window
   floating while it waits for room, it asks for the zone again. On an ignored screen it does
   nothing.

## Each screen and desktop on its own

Each screen keeps, for each virtual desktop and each activity, its own arrangement, the order of
its windows, the lines between them as you last moved them for each number of windows, and the
zone layout a drag offers there. A screen starts on the first arrangement in the rotation -- and
a window that opens on a screen is laid out by that screen's arrangement, the others staying
where they are -- unless
its desktop has one of its own under [Desktops](#desktops); on a desktop KyprX made for a window
that found every zone taken, the window's screen starts on the arrangement and zone layout of the
desktop the window came from. The lines KyprX moves by itself to give a window the room it needs
are not kept; two windows that traded places for room keep the new order.

A window is laid out on the activity you are on when it is on that activity or on every activity;
one only on other activities takes no zone here, is not moved, and is never chosen by the focus
keys. Switching activity lays out the one you switch to and leaves the other's windows where they
are; a window on every activity follows you and joins the end of the order there, as a window on
two desktops does when you switch desktop. A window moved to another activity leaves the layout
here. With no activity manager running, everything works as
with one activity.

A minimised window leaves the layout and the others close up; brought back, it takes its place
again. A maximised or full-screen window keeps its place, is not moved, and gets its zone back
when made ordinary again.

All of this lasts as long as the session. After you log out, or when the compositor restarts,
every screen starts again on its desktop's arrangement under [Desktops](#desktops), or on the
first in the rotation where none is chosen. The lines you moved for an arrangement are also
forgotten when the layouts it lays a screen out by change -- another zone layout chosen, a layout
added or removed, a divider moved -- even when the change comes in while KyprX's tiling is
switched off, as when a copy of the desk or the KyprX folder puts other ones back
(KNOWN-ISSUES).

## Gaps

The four screen edges sit in two rows, with **Between windows** under them. Each number goes from
0 to 200 px.

| Setting | KyprX's default | What it changes |
|---|---|---|
| **Top** | 10 px | The space between the top of the screen and the windows. |
| **Bottom** | 10 px | The space between the bottom of the screen and the windows. |
| **Left** | 10 px | The space between the left edge of the screen and the windows. |
| **Right** | 10 px | The space between the right edge of the screen and the windows. |
| **Between windows** | 10 px | The space between one window and the next. Two windows side by side are exactly this apart. |

The screen is the part panels leave free. When a panel is added, removed, resized or moved to
another edge, the tiled windows on every screen on show are laid out again in the space left. A
panel whose visibility setting changes, so that it reserves its strip or stops reserving it, goes
unnoticed until something else lays that screen out
(KNOWN-ISSUES).

## Never tiled

Four lists of windows and screens KyprX's tiling leaves alone, typed as entries with commas
between them. A list is written when you press Enter or leave the field, so a half-typed name
never reaches the tiling. Emptying a field empties the list. KyprX has no default for any of
them.

- **Floating window titles.** A window whose title contains one of these floats: left where it is
  put, and **Toggle Float** can still tile it.
- **Ignored window classes.** Applications KyprX's tiling does not touch at all, named by window
  class.
- **Ignored window titles.** A window whose title contains one of these is not tiled at all.
- **Ignored screens.** Screens KyprX's tiling leaves alone, by the name the desktop gives them,
  such as DP-1 -- names, and not numbers; the same names as under **Colour from the wallpaper
  of** on [Appearance](appearance.md) and in KDE's display settings. A window on an ignored
  screen is in no layout: never laid out, never swapped with, and resizing its edge leaves no
  moved line behind. **Toggle Float**, **Set Master**, **Rotate**, the move keys, the size keys
  and the layout keys do nothing there; the focus keys still work. No zones are offered. A tiled
  window let go over an ignored screen goes back to its place; a window KyprX would tile, dragged
  from an ignored screen to one it tiles, joins that screen's layout at the end. When a screen is
  let back in, every window on it goes back into its zone.

**How an entry matches.** A class matches a window whose class, or whose program name, is that
entry, whatever the case: `dolphin` and `org.kde.dolphin` both find Dolphin. An entry in square
brackets is a part of the name, so `[term]` finds every class with *term* in it, and an entry
with `*` in it is a pattern. A title entry is a part of the title, and there the case counts.

**KyprX's own list applies as well**, whatever is written in **Ignored window classes**: your
list adds to it and never replaces it. It holds the classes listed under
[Windows that never get the defaults by themselves](windows.md#windows-that-never-get-the-defaults-by-themselves),
and Yakuake and the lock screen besides.

Floating and ignored are not the same. A floating window is still KyprX's, and **Toggle Float**
can put it into the layout; an ignored window is left out of the tiling altogether. To float
every window of an application, tick its **Float** box on the [Windows](windows.md#float) tab --
that table has one row per window class, and a class is not a title, which is why floating by
title is here.
