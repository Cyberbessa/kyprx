# Shortcuts

The Shortcuts tab lists the keys that make a tiling desktop usable, and changes them. The list is
fixed: KyprX's tiling keys, the keys for automatic tiling and its layouts, the window actions that
go with them, KRunner, and the three keys that open KyprX's own windows. The desktop has many more
actions, and they stay in System Settings; this tab only holds the ones the cheatsheet shows.

The keys belong to the desktop, not to KyprX. This tab reads and changes the same shortcuts that
System Settings' Shortcuts page shows, and a key changed in one place is changed in the other. The
same list is what **Meta+/** puts on screen: see [The cheatsheet](#the-cheatsheet) below.

## The line at the top

*Press **Edit**, then the keys you want. The window keys and KRunner are the desktop's own; every
other key here is KyprX's.*

## Listening for keys

While a row waits for keys, a band shows above the list: **Listening for keys.** *The desktop's own
shortcuts are paused while this row waits.* Every shortcut on the desktop stops working for that
moment, so that the keys you press reach the row instead of doing what they normally do. The band
goes away, and the shortcuts come back, as soon as the row stops listening.

## The list

Two columns, **Action** and **Shortcut**, and five groups, each under its name in bold. The names
are the ones KyprX and the desktop give their actions. An action the desktop does not know is left
out of the list: KyprX's actions are known once the compositor has loaded KyprX's part of it, which
after an update is at the next login.

### Focus and move

The keys that move the focus from one window to the next, and the focused window from one zone of
the layout to the next. The four focus keys work with **Automatic tiling** on the
[Tiling](tiling.md) tab on or off, and never go to a window that is only on another activity. The
four move keys act on the tiled windows, so they do nothing while **Automatic tiling** is off, nor
on a screen KyprX's tiling leaves alone ([Ignored screens](tiling.md#never-tiled)); they act on
the focused window, and only while it is tiled.

| Action | What it does | KyprX's default |
|---|---|---|
| Focus Left | Moves the focus to the nearest window on the left, on any screen; of two as near, to the one used last. | Meta+Ctrl+H |
| Focus Down | The same, below. | Meta+Ctrl+J |
| Focus Up | The same, above. | Meta+Ctrl+K |
| Focus Right | The same, on the right. | Meta+Ctrl+L |
| Move Left | Swaps the focused window with the tiled window on its left, on the same screen. | Meta+Shift+H |
| Move Down | The same, below. | Meta+Shift+J |
| Move Up | The same, above. | Meta+Shift+K |
| Move Right | The same, on the right. | Meta+Shift+L |

### Resize and arrange

The keys that change the layout the windows are in: the size of a window's zone, which window is in
the master zone, the order of the windows, and whether a window is tiled at all. Like the move keys
they act on the tiled windows, so they do nothing while **Automatic tiling** is off, nor on a
screen KyprX's tiling leaves alone. The size keys and **Set Master** act on the focused window, and
only while it is tiled.

| Action | What it does | KyprX's default |
|---|---|---|
| Shrink Width | Makes the focused window narrower, by moving the nearest line beside it 5 % of the space that line divides. | Meta+Ctrl+Shift+H |
| Grow Height | Makes it taller, the same way. | Meta+Ctrl+Shift+J |
| Shrink Height | Makes it shorter. | Meta+Ctrl+Shift+K |
| Grow Width | Makes it wider. | Meta+Ctrl+Shift+L |
| Toggle Float | Floats the focused window in the middle of the screen at three quarters of its size, or puts it back into the tiling ([Floating windows](tiling.md#floating-windows)). | Meta+F |
| Set Master | Swaps the focused window with the one in the master zone; pressed on the master, with the second. | Meta+Return |
| Rotate | Turns the windows of the screen one place round: the last one goes into the master zone, and each of the others one place on. | Meta+O |
| Rotate Back | The other way round: the master goes to the end. | Meta+Shift+O |

A window is never made smaller than it can be: when the window beside it cannot give up the room,
the line stops. A line moved with these keys stays where it is for that number of windows on that
screen, as one moved with the mouse does. The lines also move by themselves, to give a window the
room its own minimum size needs, and the size keys start from the lines as you see them then
([A window bigger than its zone](tiling.md#a-window-bigger-than-its-zone)). A move key
([Focus and move](#focus-and-move)), **Set Master** or **Rotate** that puts a window in a zone too
small for it can be followed by a trade that gives it a zone it fits.

### Layouts

| Action | What it does | KyprX's default |
|---|---|---|
| Toggle Automatic Tiling | Switches **Automatic tiling** on the [Tiling](tiling.md#automatic-tiling) tab on or off, for every screen, and it stays so. A card in the middle of the screen in use says which, unless **Show names on screen** is off ([The name card](tiling.md#the-name-card)). It does nothing while KyprX's tiling is not running. | Meta+T |
| Next Layout | With **Automatic tiling** on, moves the screen in use to the next arrangement in the rotation ([Arrangements](tiling.md#arrangements)). With it off, moves the screen to the next entry of the bar a drag shows there, **Whole screen** and the zone layouts a drag offers, and draws that one's zones on the screen for a moment ([The layout keys](tiling.md#the-layout-keys)). Either way a card in the middle of that screen shows the name and the zones, unless **Show names on screen** is off on the Tiling tab ([The name card](tiling.md#the-name-card)). On a screen KyprX's tiling leaves alone it does nothing and shows no name. | Meta+\ |
| Previous Layout | The same, to the previous one. | Meta+\| |

### Window management

| Action | What it does |
|---|---|
| Close Window | Closes the focused window. |
| Minimize Window | Minimises the focused window. |
| Maximize Window | Maximises the focused window. |
| Peek at Desktop | Shows the desktop. |
| Switch One Desktop to the Left | Goes to the virtual desktop on the left. |
| Switch One Desktop to the Right | Goes to the virtual desktop on the right. |
| Toggle Overview | Opens or closes the Overview. |
| Toggle Present Windows (All desktops) | Shows the windows of every desktop side by side. |
| Walk Through Windows | The window switcher. |
| KRunner | The desktop's search and launcher. |

KRunner is the one action here that does not come from the compositor. It is on the list because
a tiling desktop is used with it constantly.

KyprX sets no default for these keys: they are the desktop's.

### KyprX

| Action | What it does | KyprX's default |
|---|---|---|
| Shortcut cheatsheet | Shows [the cheatsheet](#the-cheatsheet). | Meta+/ |
| Settings | Opens the KyprX window, floating above the other windows ([Floating windows](tiling.md#floating-windows)). | Meta+K |
| Wallpaper picker | Opens the [wallpaper picker](wallpaper.md). | Meta+R |

### KyprX's defaults

Every key in the **KyprX's default** columns above is a default KyprX's part of the compositor gives
its action when it first registers it. Each is a row like any other: it can be changed or removed
here. A default counts only until the desktop holds a key for the action, so a key you set here
stays when KyprX is installed again, and an action that has a key keeps it when an update of KyprX
gives it another default. If one of KyprX's actions does not exist on the desktop yet, the
**Problems** box on the [Settings](settings.md#problems) tab says so.

### When another action has the same key

Other programs register some of these keys too. Out of the box on Plasma 6.7, Spectacle puts
**Start/Stop Region Recording** on Meta+R, and the desktop's own tile editor, **Toggle Tiles
Editor**, is on Meta+T. That is what Spectacle 6.7.5's own files and the desktop's record of its
default keys say. The desktop keeps a shared key on both actions and runs only the one it
registered first, which on a new desk is usually the other one, so the key would do nothing for
KyprX.

So each time KyprX starts, a key that one of four of KyprX's actions holds -- the three above and
**Toggle Automatic Tiling** -- is taken away from any other action that holds it as well, the way
**Use it here** takes one (below). Only that key is taken: the other action keeps any other key it
has, and the tile editor is left with no key. The log says what was taken and from which
action. A key you moved away from KyprX's action is not KyprX's any more, and KyprX leaves it
alone. Up to Plasma 6.6 the desktop refused the key to KyprX's action instead, and the action stays
without one until you give it a key here.

The other tiling keys and layout keys are not taken back by themselves. When another action holds
one of them too, press **Remove** on its row, then **Edit** and the same key: the window names the
other action, and **Use it here** takes the key from it.

## A row

Each row shows the action's keys, then, for some actions, **on the card:**, then **Edit** and
**Remove**.

### The keys

Every key the action has, separated by `/`, or **not bound** in grey when it has none. The keys are
listed in a fixed order, and the first one listed is the one **Edit** replaces and **Remove** takes
away. When an action has more than one key, the pointer resting on the row shows *also bound to*
and the others.

### on the card:

Shown only on an action with more than one key: KRunner, for example, which Plasma 6.7 gives three.
It chooses which of those keys the cheatsheet shows. It rebinds nothing. Until you choose, the
cheatsheet shows the first key listed.

The choice is kept as the key itself, not as a place in the list, so it holds when the desktop
lists the keys in another order. If that key is taken off the action, the cheatsheet shows the
first key instead.

### Edit

Press **Edit**, then press the keys. The button becomes **Cancel** while the row listens, and the
band above the list shows. The row takes one combination, such as Meta+Alt+Up; it replaces the
first key listed and leaves the action's other keys as they are.

- **Keep the pointer over the window while you press the keys.** When focus follows the mouse (see
  [Tiling](tiling.md#focus)), a pointer that drifts off the window takes the keyboard with it. The
  row then stops listening, and the message line at the bottom of the window says why.
- **AltGr cannot be part of a shortcut.** On a keyboard layout where the right Alt key is AltGr,
  the row stops and says so. Use the left Alt.
- **Esc, Tab or Shift+Tab cancel**, when pressed without Meta, Ctrl or Alt, and the message line
  says *left as it was*. With Meta, Ctrl or Alt held they are ordinary keys, so Meta+Tab can be
  bound. **Cancel** also stops the row without changing anything.
- While a row listens, Esc cancels the row; it does not close the window.
- Leaving the tab, closing the window or quitting stops the row, and the desktop gets its shortcuts
  back. If the window is killed instead, KyprX gives them back when the window is gone.

**A key with no modifier is asked about.** A key pressed without Meta, Ctrl or Alt (Shift does not
count) would become a shortcut for the whole desktop and stop reaching every application. The
window asks **Use a key on its own?**: **Yes** binds it, **No** leaves the row as it was, and
**No** is the answer already chosen. F-keys (F1 to F35) and the special keys that type nothing,
such as volume, media, brightness and launcher keys, are not asked about.

**A key another action holds is named first.** Before anything is bound, KyprX asks the desktop who
holds the key. If another action does, whichever program it belongs to, the window asks **That key
is already in use**, naming that action and its program, with two answers:

- **Use it here** takes the key away from the other action and binds it to this one, as one
  change. If binding it here fails, the other action gets its key back.
- **Cancel** leaves both actions as they were. It is the answer already chosen.

The window has to ask, because from Plasma 6.7 the desktop accepts a key two actions share without
a word. It keeps the key on both, and when the key is pressed only one of them runs: the one the
desktop registered first.

After a change, the message line says what changed, as *action: old key → new key*. KyprX reads
back what the desktop stored, and if the key did not go in, the message line says so and the row
shows what the desktop really has.

### Remove

Takes the action's first key away. Any other key the action has stays. The message line says
*action: key → none*, so a key removed by mistake can be set again with **Edit**. The button is
hidden on an action with no key.

## The cheatsheet

The **Shortcut cheatsheet** key, **Meta+/** unless you changed it, puts the fixed list on screen as
a card in the middle of the screen. It floats above the other windows, the KyprX window among them:
the tiling leaves it alone. The same card opens from the application menu (right-click **KyprX**,
then **Show the shortcut cheatsheet**) and from the command `kyprx --cheatsheet`.

**What it shows.** The five groups of the list, each one whole, stacked in columns: two, or three
on a screen too short for two once a panel is on it. The groups are stacked so that the tallest
column is as short as it can be, which leaves the least room empty beside the others, and in the
order of the list wherever that costs nothing. On a 1920x1080 screen that is two columns:
**Focus and move** over **Resize and arrange**, and **Layouts**, **Window management** and
**KyprX** under each other beside them. On a 1080-pixel screen at 125 %, three: **Focus and move**
over **Layouts**; **Resize and arrange** over **KyprX**; and **Window management**. On a screen too
narrow for that card, such as 1440x900, the groups are stacked another way that fits its width
when one does. On a screen smaller than
about 1440x900 once its scale is counted -- 1366x768, or 1920x1080 at 150 % -- none fits, and the
card goes past the screen's edges
(KNOWN-ISSUES). Each action has its name and one key, drawn
as a row of keyboard keys: the key chosen with **on the card:**, or the first one listed. An action
with no key shows *not bound*. In each column every row's keys start at the same place, and Meta,
Ctrl, Alt and Shift are all drawn the same width, so the keys line up down the column. Some keys
are drawn as symbols:

| Key | Drawn as |
|---|---|
| Up, Down, Left, Right | ↑ ↓ ← → |
| Page Up, Page Down | Pg↑ Pg↓ |
| Return, Enter | ↵ |
| Backspace | ⌫ |
| Delete | ⌦ |
| Tab | TAB |

The card reads the keys each time it opens, so a key changed on this tab shows the next time.

**How it closes.** Esc, Space or Return; a click anywhere on it; or another window taking the
focus. Pressing the key again while it is open closes it and opens a fresh one, so there is never
more than one.

**How it looks.** It has the same rounded corners and the same outline, in thickness and colour,
as the other windows: both come from the window decoration (see
Klassy). The card itself is see-through at the **Opacity** in the
Window section of the [Appearance](appearance.md) tab, and it is blurred like the other see-through
windows when blur is on (see [Effects](effects.md)). The names and the keys on it stay solid.

## Good to know

- **Edit cannot add a second key.** It always replaces the first key listed. On an action with no
  key, it adds one.
- **The changes are made on the desktop at once.** There is no Apply button on this tab.
- **In a dry run nothing is bound**, and the row goes back to the key the desktop still has.
- **The keys of this list are also kept in the KyprX folder and in the copies of the desk.** How
  those work is on the [Settings](settings.md) page. A key a copy of the desk or the folder holds
  for an action the desktop does not have binds nothing.
