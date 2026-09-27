# Shortcuts

The Shortcuts tab lists the keys that make a tiling desktop usable, and changes them. The list is
fixed: the tiling actions, the window actions that go with them, KRunner, and KyprX's own three.
The desktop has many more actions, and they stay in System Settings; this tab only holds the ones
the cheatsheet shows.

The keys belong to the desktop, not to KyprX. This tab reads and changes the same shortcuts that
System Settings' Shortcuts page shows, and a key changed in one place is changed in the other. The
same list is what **Meta+/** puts on screen: see [The cheatsheet](#the-cheatsheet) below.

## The line at the top

*Press **Edit**, then the keys you want. The tiling actions come from the tiling script; the rest
are the desktop's own.* The words "the tiling script" link to
[Krohnkite's readme](https://github.com/anametologin/krohnkite#readme), which describes what each
tiling action does in each layout. What KyprX expects of Krohnkite is on the
Krohnkite page.

## Listening for keys

While a row waits for keys, a band shows above the list: **Listening for keys.** *The desktop's own
shortcuts are paused while this row waits.* Every shortcut on the desktop stops working for that
moment, so that the keys you press reach the row instead of doing what they normally do. The band
goes away, and the shortcuts come back, as soon as the row stops listening.

## The list

Two columns, **Action** and **Shortcut**, and three groups, each under its name in bold. The names
are the ones the tiling script and the desktop give their actions. An action the desktop does not
know is left out of the list.

### Tiling

| Action | What it does |
|---|---|
| Focus Up | Moves the focus to the window above. |
| Focus Down | Moves the focus to the window below. |
| Focus Left | Moves the focus to the window on the left. |
| Focus Right | Moves the focus to the window on the right. |
| Move Up/Prev | Moves the focused window up, or one place back in the layout. |
| Move Down/Next | Moves the focused window down, or one place forward in the layout. |
| Move Left | Moves the focused window to the left. |
| Move Right | Moves the focused window to the right. |
| Grow Height | Makes the focused window taller. |
| Shrink Height | Makes the focused window shorter. |
| Grow Width | Makes the focused window wider. |
| Shrink Width | Makes the focused window narrower. |
| Toggle Float | Takes the focused window out of the tiling, or puts it back. |
| Next Layout | Switches to the next layout in the cycle set on the [Tiling](tiling.md) tab. |
| Previous Layout | Switches to the previous layout in the same cycle. |

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

### KyprX

| Action | What it does | KyprX's default |
|---|---|---|
| Shortcut cheatsheet | Shows [the cheatsheet](#the-cheatsheet). | Meta+/ |
| Settings | Opens the KyprX window. | Meta+K |
| Wallpaper picker | Opens the [wallpaper picker](wallpaper.md). | Meta+R |

These three are rows like any other: each can be changed or removed here. The default counts only
until the desktop holds a key for the action, so a key you set here stays when KyprX is installed
again. If one of the three does not exist on the desktop yet, the **Problems** box on the
[Settings](settings.md) tab says so.

KyprX sets no default for the Tiling and Window management keys: those are Krohnkite's and the
desktop's.

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
  [Tiling](tiling.md)), a pointer that drifts off the window takes the keyboard with it. The row
  then stops listening, and the message line at the bottom of the window says why.
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
a card in the middle of the screen. It floats: the tiling leaves it alone. The same card opens from
the application menu (right-click **KyprX**, then **Show the shortcut cheatsheet**) and from the
command `kyprx --cheatsheet`.

**What it shows.** Two columns: **Tiling** in the first, **Window management** and **KyprX** stacked
in the second. Each action has its name and one key, drawn as a row of keyboard keys: the key
chosen with **on the card:**, or the first one listed. An action with no key shows *not bound*.
Meta, Ctrl, Alt and Shift are all drawn the same width, so the keys line up down each column. Some
keys are drawn as symbols:

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
  those work is on the [Settings](settings.md) page.
