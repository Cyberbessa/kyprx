# The KyprX window

The window as a whole: how to open it, the strip of four controls above the tabs, when a change
is written, the line at the bottom, the coloured bands that can appear across the top, and how to
close it. Each tab has a page of its own under [The tabs](#the-tabs).

From top to bottom:

1. a band across the top, only when there is something to say
   ([The bands across the top](#the-bands-across-the-top));
2. the strip with **Adjust new windows**, **Colour from the wallpaper**, **Automatic tiling** and
   **Profile**;
3. the seven tabs;
4. the line at the bottom, where the window says what it has just done.

## Opening the window

- **Meta+K** opens it. That is the key KyprX starts with; the [Shortcuts](shortcuts.md) tab can
  change it. After installing a package, open KyprX from the application menu the first time: that
  is what switches it on, and the key works from then on ([Installing](install.md)). The first
  time the window opens on a new install, it asks whether to put KyprX's look on
  ([Appearance](appearance.md#kyprxs-look-the-first-time)).
- **The application menu** has it as **KyprX**, under Settings. Right-click the entry for two
  more actions: **Show the shortcut cheatsheet** and **Pick a wallpaper**. From a terminal,
  `kyprx --cheatsheet` and `kyprx --wallpaper` open the same two.
- **From a terminal**, `kyprx` opens the window on the Windows tab; `kyprx` followed by a tab name
  opens it on that tab, for example `kyprx tiling`. Upper or lower case does not matter.

| Tab | Names the command accepts |
|---|---|
| Windows | `windows` |
| Appearance | `appearance`, `profiles`, `profile`, `titlebar`, `border` |
| Effects | `effects` |
| Wallpaper | `wallpaper`, `wallpapers` |
| Tiling | `tiling` |
| Shortcuts | `shortcuts` |
| Settings | `settings` |

A name that is not in the table opens the Windows tab, and the terminal shows
`kyprx: there is no tab called '<name>'; opening Windows.` followed by every name it accepts.

**Only one window opens at a time.** Opening it again, by any way above, asks the window that is
open to come forward. A minimised one is brought back; a maximised one stays maximised; it stays
on the tab it was on.

**It opens floating**, in the middle of the screen, and stays above the other windows while it
floats, as long as KyprX's tiling runs: the tiled windows
make no room for it. With **Automatic tiling** on, **Toggle Float** tiles it until it closes
([Floating windows](tiling.md#floating-windows)). The window cannot be made smaller than
820 × 560 pixels: narrower than that, the colour presets on the Appearance tab do not fit side by
side.

If a box titled **KyprX is not running** appears instead of the window, see
[Troubleshooting](../troubleshooting.md#kyprx-is-not-running).

## The tabs

Hold the pointer over a tab's name for a one-line description of it.

- [Windows](windows.md): one row per application, and which of KyprX's treatments each one gets.
- [Appearance](appearance.md): profiles, the desktop's colours, the window frame, and the way to
  the title bar's own settings.
- [Effects](effects.md): the blur behind see-through windows, and the window animation.
- [Wallpaper](wallpaper.md): what the wallpaper picker lists and how it is laid out.
- [Tiling](tiling.md): automatic or manual tiling, the arrangements, the zone layouts, the
  desktops and their starting arrangement, the gaps, and how focus moves.
- [Shortcuts](shortcuts.md): every key KyprX answers to, and how to change one.
- [Settings](settings.md): the KyprX folder, the copies of the desk, the problems found, and the
  buttons that restore the defaults or take KyprX off.

Most sections of a tab have a small circled **i** beside their title; on the Tiling tab every
setting has one after its name. Hold the pointer over it, or over the section, for one sentence
about what the section or setting does; clicking the **i** shows the same sentence.

## Above the tabs

The strip stays the same whichever tab is open. Its four controls are written the moment you use
them.

### Adjust new windows

Ticked, every new window gets KyprX's defaults as it opens
([what those are](windows.md#what-a-new-window-gets)). A window counts as new the first time KyprX
sees its application; after that, its row on the Windows tab decides.

Unticked, new windows are left alone. They are still listed, and the line at the bottom names the
ones waiting. Ticking the box again gives the defaults to every waiting window that is still open.

Untick it while you are setting windows up by hand and do not want KyprX to touch new ones.
KyprX's default: ticked.

### Colour from the wallpaper

Ticked, a wallpaper set from the picker hands its colour to the desktop, picture or video. With
more than one screen, only the wallpaper of the chosen screen does: the primary one, unless
another is chosen on [Appearance](appearance.md). The tick changes nothing on screen by itself; it
decides where the *next* colour comes from. Putting a profile on unticks it, so the profile's
colours stay as they were saved. What the colour does is on [Appearance](appearance.md).

KyprX's default: unticked.

### Automatic tiling

Ticked, KyprX lays the windows out by the screen's arrangement as they open and close. Unticked,
windows stay where they are put and a drag offers the zones. It is the same switch as
**Automatic tiling** on the [Tiling](tiling.md#automatic-tiling) tab and as **Toggle Automatic
Tiling**, **Meta+T**: changing any of the three changes the others.

It changes that one setting and nothing else: it does not switch KyprX's tiling back on when
something switched it off, as a change on the Tiling tab does. It is greyed, with the reason under
the pointer, while KyprX's tiling is switched off, while KyprX is off this desk, and while
KyprX's part of the compositor is not the one that tiles yet.

KyprX's default: ticked.

### Profile

A menu of the saved profiles. It shows the profile the desktop is wearing; choosing another one
puts it on. Each entry carries a strip of that profile's colours.

- **Current profile** is shown when the desktop matches none of the saved profiles. It cannot be
  chosen.
- A profile that cannot go on this computer is listed greyed, as its name, a dash and the reason.
- The menu is greyed while there are no saved profiles or the file that holds them cannot be read;
  hold the pointer over it to see which.

While a profile goes on, the strip is greyed and the line at the bottom says so. If it is refused,
the line says why and the menu goes back. Profiles are saved, updated, renamed and deleted in the
Profiles box on [Appearance](appearance.md).

## Changes apply by themselves

There is no Apply button anywhere in the window. Most changes are written a moment after you make
them, and every further change within that moment starts the wait again: running through a menu
with the arrow keys is one change.

| What you change | When it is written |
|---|---|
| A tick box, menu, number or colour on the Effects and Tiling tabs, or in the Window section of Appearance, except **Opacity**; an edit in the Tiling tab's **Arrangements** and **Zone layouts** boxes | 0.7 seconds after your last change there |
| Anything in the Colours box on Appearance, and **Opacity** in its Window section | 0.5 seconds after your last change there |
| A tick in the table on the Windows tab | 0.4 seconds after your last tick; every tick made by then goes together |
| Everything else: the strip above the tabs, a number in the Windows tab's **Opacity** column, the buttons of the Profiles box, a key on the Shortcuts tab, the Wallpaper tab, the Settings tab, and **Put KyprX's zone layouts and arrangements back…** | at once |

- **A number you type is read when you finish it**: on Enter, or on moving to another control.
  Typing 120 is one change, not 1, 12 and 120. Text is read the same way.
- **The mouse wheel does not change a menu or a number.** Rolling the wheel over one scrolls the
  tab.
- **Leaving a tab** sends at once whatever was waiting on the Effects and Tiling tabs and in the
  Window section of Appearance. The shorter waits finish on their own.
- **Closing the window** sends what was waiting on those and in the Windows tab's table -- but not
  a change in the Colours box or to **Opacity** on Appearance: wait half a second after it before
  you close the window (KNOWN-ISSUES.md).

There is no undo. The line at the bottom says what each change replaced, and **Go back to a
copy…** on the [Settings](settings.md) tab puts back a whole earlier copy of the desk.

## The line at the bottom

The line under the tabs says what the window is doing and what it has just done:

- what a change replaced, such as **Corner radius 8 px → 12 px**. Two settings at most are named,
  then **and N more**;
- that a slow change has started, before the screen stops for it: **Applying to 3 windows…**, or
  **Putting** *name* **on… the desktop's own tools take a second or two**. The pointer shows that
  the window is busy until it is done;
- why KyprX refused something, or **That did not go through.**

A message stays for six seconds, or until the next one replaces it; a message about a change
still in progress goes as soon as the change is done. When no message is showing, the line is
empty, unless new windows are being left alone (see
[Adjust new windows](#adjust-new-windows)). Then it says **New windows are being left alone.
3 waiting:** followed by the names of up to five of them, with **…** after the fifth when there
are more, or **New windows are being left alone. Tick *Adjust new windows* to catch them up.**
when none is waiting. During a dry run, every message starts with **Dry run -- nothing was
written:**; the standing line does not.
[Troubleshooting](../troubleshooting.md) says where to look when the line is not enough.

## The bands across the top

A band means the window is not in its ordinary state.

### Dry run

Orange, starting **Dry run.** The service was started by hand in dry run: nothing is written, and
every change is written down instead, in the terminal the dry run was started from or in the
journal. Every message on the line at the bottom is prefixed, and the **Title bar settings…**
button on the Appearance tab cannot be pressed, because Klassy's own settings save for real.
Nothing needs doing: close the window before you stop the dry run. How to start one is in
[Troubleshooting](../troubleshooting.md#seeing-what-a-change-would-do-without-doing-it).

### The dry run is over

Red, starting **The dry run is over.** The dry-run service has stopped and the one that answers
now writes for real, so the window sends nothing: every change you try says **The dry run has
ended, so this window sends nothing. Close it and open it again to go on.** Close the window and
open it again. The **Title bar settings…** button stays closed.

### KyprX was updated while it ran

Orange, saying **KyprX X is installed, and the background service is still Y**. A new version was
installed while the old service kept running. The Settings tab's greyed line says which version
the window is. What to do: **Restart the background service**, at
the end of the band. A window opened with the settings key closes with it; open it again. When the
band says instead that this window is the older one, close it and open it again. Logging out and
back in does both. Until then, the Tiling tab's Arrangements and Zone layouts boxes can be locked
([When the boxes cannot be used](tiling.md#when-the-boxes-cannot-be-used)). Whether a window
survives the restart at all depends on how it was opened:
[Restarting the background service](../troubleshooting.md#restarting-the-background-service).

### Something KyprX needs is missing

Orange, starting **KyprX is missing part of what it is built on:** and naming the programs. One of
the four KyprX is built on is not installed, is too old, or is installed and not running -- which
is what a compiled program is after a Plasma update, until it is built again. The tab that depends
on it says so on itself too. **What to do**, at the end of the band, opens the Settings tab, where
[What KyprX needs](settings.md#what-kyprx-needs) gives the command for this computer.

### KyprX is off this desk

Orange, starting **KyprX is off this desk.** It is there after **Take KyprX off this desk…** on
the [Settings](settings.md) tab. New windows are left alone, and your setup is kept in the KyprX
folder and in the copy of the desk taken just before.

What to do: **Put my setup back**, at the end of the band. It first shows **Put your setup
back?** with exactly what would change; **Put it back** does it. A copy of the desk as it is now
is kept, then the earlier copy goes back on exactly, and whatever arrived in the KyprX folder
meanwhile is applied. The line at the bottom says **Your setup is back, and KyprX is on the desk
again.** when it is done. If that copy cannot be put back, the
line says why; **Go back to a copy…** lists the others.

### KyprX's tiling is not running

Orange, on the Tiling tab only, saying why nothing is being laid out: **Tiling is switched off**
(the band then has **Switch tiling back on**, which changes nothing else), no part of KyprX in the
compositor asking for the tiling yet, or KyprX taken off the desk. After an update it can say
instead that KyprX's part of the compositor is from before the update: that part goes on tiling as
it did, and what is new on the tab starts at the next login.
[When tiling is switched off](tiling.md#when-tiling-is-switched-off) has every case.

The Wallpaper tab and the Colours box on the Appearance tab have orange bands of their own; their
pages explain them.

## The dot before a setting's name

On the Appearance, Effects and Tiling tabs, a small grey dot before a setting's name means
nothing has been written for it yet. The value shown is the one the program itself uses when
nothing is set, it is what applies now, and nothing is written until you change it. Hold the
pointer over the dot to read the same. The dot goes
away once a value is written.

Where a page of this guide says *KyprX's default*, it is the value KyprX starts with.
**Restore KyprX's defaults…** on the [Settings](settings.md#restore-kyprxs-defaults) tab writes
back most of them; that section lists what it leaves alone.

Grey means two other things on those tabs:

- **A greyed control with its name in ordinary colour** does nothing at the moment, usually
  because the switch above it makes it pointless. Its value is kept.
- **A greyed name** means KyprX does not know what value applies. A menu in that state shows
  **(not set)**.

On the Windows tab, a dot beside a number in the **Opacity** column means the window is drawn at
the shared number from the Appearance tab ([Windows](windows.md#opacity)).

## Closing the window

**Esc** closes the window, except while a row on the Shortcuts tab is listening for a new key:
there, Esc leaves that key as it was and the window stays open. Leaving the Shortcuts tab or
closing the window also stops a row that is listening, so the desktop's own shortcuts come back.
