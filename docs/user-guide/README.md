# The KyprX window

This page is about the window as a whole: how to open it, the strip of three controls above the
tabs, when a change is written, the line along the bottom, the coloured bands that can appear
across the top, and how to close it. Each tab has a page of its own, listed under
[The tabs](#the-tabs).

From top to bottom the window has:

1. a band across the top, only when there is something to say (see
   [The bands across the top](#the-bands-across-the-top));
2. the strip with **Adjust new windows**, **Colour from the wallpaper** and **Profile**;
3. the seven tabs;
4. the line at the bottom, where the window says what it has just done.

## Opening the window

- **Meta+K** opens it. That is the key KyprX starts with; the [Shortcuts](shortcuts.md) tab can
  change it. After installing a package, open KyprX from the application menu the first time: that
  is what switches it on, and the key works from then on ([Installing](install.md)).
- **The application menu** has it as **KyprX**, filed under Settings. Right-click the entry for two
  more actions: **Show the shortcut cheatsheet** (see [Shortcuts](shortcuts.md)) and **Pick a
  wallpaper** (see [Wallpaper](wallpaper.md)). From a terminal, `kyprx --cheatsheet` and
  `kyprx --wallpaper` open the same two.
- **From a terminal**, `kyprx` opens the window on the Windows tab, and `kyprx` followed by a tab
  name opens it on that tab, for example `kyprx tiling`. Upper or lower case does not matter.

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

**Only one KyprX window opens at a time.** Opening it again, by any of the ways above, asks the
window that is already open to come forward and opens nothing new. A minimised window is brought
back; a maximised one stays maximised. It stays on the tab it was on, even when the second command
named another tab.

If a box titled **KyprX is not running** appears instead of the window, see
[Troubleshooting](../troubleshooting.md#kyprx-is-not-running).

## The tabs

Hold the pointer over a tab's name for a one-line description of it.

- [Windows](windows.md): one row per application, and which of KyprX's treatments each one gets:
  title bar, outline, transparency and its own opacity, blur, floating, animation.
- [Appearance](appearance.md): saved profiles, the desktop's colours, the window frame (opacity,
  corner radius, outline), and the way to the title bar's own settings.
- [Effects](effects.md): the blur behind see-through windows, and the animation when a window
  moves or resizes.
- [Wallpaper](wallpaper.md): whether the wallpaper picker offers pictures or videos, where the
  videos come from, when a video pauses, and how the picker is laid out.
- [Tiling](tiling.md): how focus moves, the layouts the layout key cycles through, the gaps, and
  how tiled, new and never-tiled windows behave.
- [Shortcuts](shortcuts.md): every key KyprX and the tiler answer to, how to change one, and the
  cheatsheet that lists them.
- [Settings](settings.md): notifications, the KyprX folder and the copies of the desk, the
  problems KyprX has found, credits, and the buttons that restore KyprX's defaults or take KyprX
  off the desk.

Most sections of a tab have a small circled **i** beside their title. Hold the pointer over it, or
over the section, for one sentence about what the section is for; clicking the **i** shows the
same sentence.

## Above the tabs

The strip above the tabs stays the same whichever tab is open. Its three controls are written the
moment you use them.

### Adjust new windows

Ticked, every new window gets KyprX's defaults as it opens. [Windows](windows.md) lists what those
defaults are. A window counts as new the first time KyprX sees its application. After that, KyprX
does not apply its defaults to it again: its row on the Windows tab decides.

Unticked, new windows are left alone. They are still listed on the Windows tab, and the line at the
bottom of the window names the ones waiting (see [The line at the bottom](#the-line-at-the-bottom)).
Ticking the box again gives KyprX's defaults to every waiting window that is still open.

Untick it while you are setting windows up by hand and do not want KyprX to touch new ones.

KyprX's default: ticked.

### Colour from the wallpaper

Ticked, every wallpaper you set from the wallpaper picker hands its colour to the desktop, whether
it is a picture or a video. Ticking or unticking it changes nothing on screen by itself: it decides
where the *next* colour comes from.

Putting a profile on unticks it, so that the profile's colours stay as they were saved.

What the colour does to the desktop, and how to choose a colour of your own instead, is on
[Appearance](appearance.md).

KyprX's default: unticked.

### Profile

A menu of the profiles you have saved. It shows the profile the desktop is wearing, and choosing
another one puts that one on. Each entry has a strip of that profile's colours beside its name.

- **Current profile** is shown when the desktop matches none of the saved profiles. It cannot be
  chosen.
- A profile that cannot go on this computer is listed as its name, a dash and the reason, greyed,
  and cannot be chosen.
- The menu is greyed while there are no saved profiles, and when the file that holds them cannot be
  read. Hold the pointer over it to see which.

While a profile goes on, the whole strip is greyed, the pointer shows that the window is busy, and
the line at the bottom says **Putting** *name* **on… the desktop's own tools take a second or two**.
If the profile is refused, the line says why and the menu goes back to the profile that was on.

Profiles are saved, updated, renamed and deleted in the Profiles box on the
[Appearance](appearance.md) tab, which can also put one on.

## Changes apply by themselves

There is no Apply button anywhere in the window. Most changes are written a moment after you make
them, and every further change within that moment starts the wait again, so running through a menu
with the arrow keys, or clicking a number up several steps, is one change.

| What you change | When it is written |
|---|---|
| A tick box, menu, number or colour on the Effects and Tiling tabs, or in the Window section of Appearance, except **Opacity** | 0.7 seconds after your last change there |
| Anything in the Colours box on Appearance, and **Opacity** in its Window section | 0.5 seconds after your last change there |
| A tick in the table on the Windows tab | 0.4 seconds after your last tick; every tick made by then goes together |
| Everything else: the strip above the tabs, a number chosen in the Windows tab's **Opacity** column, the buttons of the Profiles box, a key on the Shortcuts tab, the Wallpaper tab, the Settings tab | at once |

- **A number you type is read when you finish it**: when you press Enter or move to another
  control. It is not read while you type, so typing 120 is one change and not 1, 12 and 120.
- **Text is read the same way.** Text typed into a box, such as the never-tiled lists on the Tiling
  tab or the video folder on the Wallpaper tab, is read when you press Enter or leave the box.
- **The mouse wheel does not change a menu or a number.** Rolling the wheel over one scrolls the
  tab instead.
- **Leaving a tab** sends at once whatever was waiting on the Effects and Tiling tabs and in the
  Window section of Appearance. The shorter waits in the table above finish on their own.
- **Closing the window** sends whatever was waiting on the Effects and Tiling tabs, in the Window
  section of Appearance and in the Windows tab's table. A change in the Colours box or to
  **Opacity** on the Appearance tab is not sent: wait half a second after it before you close the
  window (KNOWN-ISSUES.md).

There is no undo in the window. The line at the bottom says what each change replaced, and
**Go back to a copy…**, on the [Settings](settings.md) tab, puts back a whole earlier copy of the
desk.

## The line at the bottom

The line under the tabs is where the window says what it is doing and what it has just done. For
example:

- what a change to most settings on the Appearance, Effects and Tiling tabs replaced, such as
  **Corner radius 8 px → 12 px**. It names two settings at most, then says how many more changed,
  as in **and 2 more**;
- what a number chosen in the Windows tab's **Opacity** column replaced, as the window class
  followed by **opacity 92 % → 80 %**;
- that a slow change has started, before the screen stops for it: **Applying to 3 windows…**, or
  **Putting** *name* **on… the desktop's own tools take a second or two**. The pointer shows that
  the window is busy until it is done;
- why KyprX refused something, in the words its background service gave, or
  **That did not go through.**

A message stays on the line for six seconds, or until the next one replaces it. A message about a
change still in progress goes as soon as the change is done.

When no message is showing, the line is empty, unless new windows are being left alone (see
[Adjust new windows](#adjust-new-windows)). Then it says so, and names up to five of the waiting
applications by their window class:

- **New windows are being left alone. 3 waiting:** followed by the names, with **…** after the
  fifth when there are more;
- **New windows are being left alone. Tick *Adjust new windows* to catch them up.** when none is
  waiting.

During a dry run, every message starts with **Dry run -- nothing was written:**. The standing line
about new windows does not.

[Troubleshooting](../troubleshooting.md) says where to look when the line is not enough.

## The bands across the top

A band across the top of the window means the window is not in its ordinary state. Each one is
described below with what to do about it.

### Dry run

An orange band that starts with **Dry run.** The background service was started by hand in dry
run, to try KyprX without changing anything: nothing is written, and every change you make is
written down instead, in plain words, in the terminal where the dry run was started or in the
journal. While it lasts:

- every message on the line at the bottom starts with **Dry run -- nothing was written:**;
- the **Title bar settings…** buttons, on the Appearance and Settings tabs, cannot be pressed,
  because the decoration's own settings save for real and a dry run cannot hold that back.

Nothing needs doing about the band: it is there so that no change looks real. Close the window
before you stop the dry run. How to start one, and what it holds back, is in
[Troubleshooting](../troubleshooting.md#seeing-what-a-change-would-do-without-doing-it).

### The dry run is over

A red band that starts with **The dry run is over.** The dry run the window was opened on has
stopped, and the service that answers now writes for real, so the window has stopped sending
anything. Every change you try says **The dry run has ended, so this window sends nothing. Close
it and open it again to go on.**

The **Title bar settings…** buttons stay closed.

What to do: close the window and open it again. The new window talks to the service that is
running now, and its changes are real.

### KyprX was updated while it ran

An orange band that says **KyprX X is installed, and the background service is still Y**. A new
version of KyprX was installed while the old one was running, and the background service is still
the old one. The Settings tab's greyed line says which version the window is.

What to do: **Restart the background service**, at the end of the band. A window opened with the
settings key closes with it; open it again. When the band says instead that this window is the
older one, close the window and open it again. Logging out and back in does both.

### Something KyprX needs is missing

An orange band that starts with **KyprX is missing part of what it is built on:** and names the
programs. One of the five programs KyprX is built on is not installed, is too old, or is installed
and not running -- which is what a compiled program does after a Plasma update, until it is built
again for the new Plasma. The tab that depends on it also says so on itself.

What to do: **What to do**, at the end of the band, opens the Settings tab, where
[What KyprX needs](settings.md#what-kyprx-needs) gives the command for this computer.

### KyprX is off this desk

An orange band that starts with **KyprX is off this desk.** It is there after **Take KyprX off
this desk…**, on the [Settings](settings.md) tab. New windows are left alone (which is why
**Adjust new windows** is unticked), and your setup is kept in the KyprX folder and in the copy of
the desk taken just before.

What to do: **Put my setup back**, at the end of the band, when you want KyprX back. It first
shows **Put your setup back?** with exactly what would change; **Put it back** does it. A copy of
the desk as it is now is kept first. Then the copy taken before KyprX was taken off goes back on,
exactly, and whatever arrived in the KyprX folder meanwhile is applied. The line at the bottom
says **Your setup is back, and KyprX is on the desk again.** when it is done. If that copy cannot
be put back, the line says why; **Go back to a copy…**, on the Settings tab, lists the other
copies. Other ways back are on [Settings](settings.md).

### Tiling is switched off

An orange band at the top of the Tiling tab only, which says **Tiling is switched off, so nothing
on this tab is doing anything.** Something has switched the tiling script off.

What to do: **Switch tiling back on**, at the end of the band, puts the tiling script back on and
changes nothing else. [Tiling](tiling.md) has the rest.

When Krohnkite is not installed at all, the same band says so instead, and that nothing on the tab
does anything until it is. There is no button then: switching on a program that is not there would
do nothing. [What KyprX needs](settings.md#what-kyprx-needs) says how to install it.

The Wallpaper tab and the Colours box on the Appearance tab have orange bands of their own; their
pages explain them.

## The dot before a setting's name

On the Appearance, Effects and Tiling tabs, a small grey dot in front of a setting's name means
nothing is written for that setting yet: the value shown is the one the program itself uses when
nothing is set, and it is what applies now. Nothing is written for it until you change it. Hold the
pointer over the dot to read the same.

The dot goes away once a value is written for the setting.

Grey means two other things on those tabs:

- **A greyed control with its name in ordinary colour** does nothing at the moment, usually because
  the switch or the choice above it makes it pointless. Its value is kept, and it counts again when
  that changes.
- **A greyed name** means KyprX does not know what value applies to that setting. A menu in that
  state shows **(not set)**.

On the Windows tab, a dot beside a number in the **Opacity** column means that window is drawn at
the shared number from the Appearance tab; [Windows](windows.md) explains it.

## Closing the window

**Esc** closes the window, except while a row on the Shortcuts tab is listening for a new key.
There, Esc leaves that key as it was and the window stays open.

Leaving the Shortcuts tab or closing the window also stops a row that is listening, so the
desktop's own shortcuts come back.

## Good to know

- Whether the window stays open when KyprX's background service restarts depends on how it was
  opened: [Restarting the background service](../troubleshooting.md#restarting-the-background-service)
  says which.
- The window cannot be made smaller than 820 × 560 pixels. Narrower than that, the colour presets
  on the Appearance tab do not fit side by side.
