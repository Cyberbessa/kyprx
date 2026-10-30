# Troubleshooting

Where KyprX says that something went wrong, what each of its warnings means, and how to get the
desktop back the way you want it. The commands can be copied into a terminal as they are; replace
anything in angle brackets first.

## Where to look first

### The line at the bottom of the window

The KyprX window answers every change on the line along its bottom: what it did, or why it could
not. A message stays there for six seconds. After that the line goes back to its standing text
(whether new windows are being left alone) or goes blank, and the message is not kept anywhere in
the window. Some controls do not leave the reason on the line at all;
KNOWN-ISSUES.md lists which.

### The Problems box

On the Settings tab. It lists what KyprX finds wrong with the setup, one line each, and is on the
tab only while there is something to list. Hold the pointer over a line for the details. The box
is checked again every time something changes while the tab is open. Every line it can show is
explained in [What the Problems box says](#what-the-problems-box-says).

### What KyprX needs

The **What KyprX needs** box is on the Settings tab while one of the four programs KyprX is built
on is not installed and running: it names each one that is not, and the command that puts it right
on this computer ([Settings](user-guide/settings.md#what-kyprx-needs)). **About KyprX…**, on the
same tab, lists all four, right or not. While one is not right, a band across the top of the window
names it on every tab. The tiling is KyprX's own, and when it
is not running, the band at the top of the Tiling tab says why
([Windows are not tiled](#windows-are-not-tiled)).

To see where each answer came from, run `python3 /usr/share/kyprx/daemon/requirements.py --facts`
(where KyprX was installed as a package) or `python3 daemon/requirements.py --facts` (installed
with `install.sh`, from the folder it was installed from): one line per project, saying what the
answer was built on. It changes nothing.

### Desktop notifications

Some failures happen when no KyprX window is open: an application that keeps its own title bar, a
wallpaper or a colour that would not apply, a KyprX folder that could not be applied. With **Say
when something did not work** ticked on the Settings tab, KyprX shows these as desktop
notifications. [Settings](user-guide/settings.md#notifications) lists them.

### The log

The background service, `kyprd`, writes what it does to the system journal:

```sh
journalctl --user -u kyprd --since "30 min ago"   # everything it said in the last half hour
journalctl --user -u kyprd -p err                 # only the failures it marked as errors
journalctl --user -u kyprd -f                     # follow it live while you do the thing again
```

A `kyprd` started by hand for a dry run writes in the terminal it was started from instead, and
each of its lines begins with `kyprd [dry run]:`.

**What a failure looks like.** A failure the service caught is one line:

```
kyprd: could not <what it was doing>: <kind of error> at <file>:<line> in <function>: <message>
```

Some lines say `failed on <what>` instead of `could not <what it was doing>`. After that come the
kind of error, the deepest place in KyprX's own code it went through (file, line and function)
and the error's own message. The place is not always the function that wrote the line. Send this
line, with what you did just before it, to whoever looks into the problem.

**What the log does not have.** Not every failure reaches the log, and not every one that does
is marked as an error, so `-p err` can miss it.
KNOWN-ISSUES.md lists each gap.

**KyprX's part inside the compositor** writes to the compositor's own log:

```sh
journalctl --user -u plasma-kwin_wayland --since "30 min ago"
```

A mistake the compositor finds in KyprX's script shows there as a warning. The script's own lines,
such as `KyprX: tiling started` and `KyprX: tiling stopped`, are debug lines, and the desktop's
default logging rules leave those out: on the desk this was written on, `*.debug=false` in
`/usr/share/qt6/qtlogging.ini` drops them. They show only where the compositor runs with a logging
rule that lets them through, as the nested KWin `scripts/sandbox.sh` starts does
(`QT_LOGGING_RULES` there); nothing of KyprX's sets one on the desk. The daemon's log above is the
one to read first: what the tiling is told comes from it.

**To see the script's own lines on the desk**, give the compositor such a rule with a drop-in for
its service, which reaches the compositor and no other program:

```sh
mkdir -p ~/.config/systemd/user/plasma-kwin_wayland.service.d
printf '[Service]\nEnvironment="QT_LOGGING_RULES=js.debug=true;qml.debug=true"\n' \
  > ~/.config/systemd/user/plasma-kwin_wayland.service.d/kyprx-debug.conf
systemctl --user daemon-reload
```

It takes effect at the next login, when the compositor starts with it. After that login,
`systemctl --user show plasma-kwin_wayland -p Environment` names the rule, and

```sh
journalctl --user -u plasma-kwin_wayland -b -g 'KyprX:'
```

shows `KyprX: tiling started` and every line the script wrote since. A rule given this way wins
over the `*.debug=false` of `qtlogging.ini`: the sandbox's nested KWin gets its rule the same way,
and its lines come through. The drop-in on a desk's own compositor is not measured. It lets
through every debug line of every script the compositor runs, so the journal grows while it is
there. To take it away, delete the file, run `systemctl --user daemon-reload`, and log in again.

Among the script's lines, those of the room a window's minimum is given and of a window that moves
itself say what was done to which window, by its class, with the numbers:

| The line, after `KyprX: ` | What happened |
|---|---|
| `the lines on <screen> move to give each window its minimum: <class> needs W x H, its zone of the layout is W x H` | the lines moved for room; `<screen>` is the screen, desktop and activity, joined by `\|` |
| `the lines on <screen> are the layout's own again` | the window that needed the room is gone, or needs less |
| `to make room on <screen>, <class> and <class> trade zones (<class> needs W x H)` | two windows traded zones |
| `<class> floats in the middle of <output> until there is room for it among the <n> windows tiled there (it needs W x H)` | the window that joined last floats, and waits for room |
| `<class> floats in the middle of <output>: it needs W x H, and the area less its gaps is W x H` | a window too big for the screen even alone |
| `<class> is tiled again on <output>: there is room for it now (it needs W x H)` | a waiting window went back into the tiling |
| `put <class> back in its zone (n of 3): it was at W x H at X, Y, its zone is W x H at X, Y` | a window its application moved, put back |
| `<class> answers its zone with a size of its own, in its corner: that size stands (W x H in a zone of W x H)` | a window that sizes itself, such as a terminal, keeps its size |
| `<class> is out of its zone again after being put back 3 times in 10 s: where it put itself stands (W x H at X, Y)` | the engine stopped putting that window back for now |
| `<class> grew past its zone: it needs W x H, its zone is W x H, and its screen is laid out again` | a window's minimum went up after it was tiled, or its title bar came late |
| `<class> needs W x H where it was laid out needing W x H: its screen is laid out again` (or `floated for room`) | a window came to need less, its title bar hidden, where that can give room back or make room for a window waiting for it |
| `the write to <class> has brought no change in <ms> ms: it is looked at once more before anything is counted` | a write slow to land, waited for once more |
| `could not raise <class>: <error>` or `could not put <class> back in its zone: <error>` | a call failed; the rest went on |

A part in brackets is there only when the window needs anything of its zone.

## What the Problems box says

The lines appear in this order. The words in bold are exactly what the box shows.

**KyprX cannot see your windows: its part of the compositor is not installed.**
KyprX's script inside the compositor is missing. That script tiles the windows, tells KyprX when
windows open and close, and carries KyprX's keys. Without it nothing is tiled, new windows are not
set up and the Windows tab cannot list what is open. To fix it, install the KyprX package again, or
run `./install.sh` again from the copy of the KyprX repository you installed from (see
[Install](../README.md#install)); the details under the line say which.

**KyprX cannot see your windows: its part of the compositor is switched off.**
This has the same effect: the script is installed but switched off. Switch **KyprX** on in System
Settings, on the KWin Scripts page (`systemsettings kcm_kwin_scripts` opens it), and apply. Or run
`./install.sh` again, which switches it on and makes the compositor load it.

**Part of KyprX starts only at the next login: log out and back in.**
The compositor reads KyprX's part of it again only at login. After an update it still runs the part
it loaded before, or no part of KyprX inside it has asked for its settings since the background
service started: the one running is too old to ask, or none is running. The details say what waits
until then. For the tiling, **Until then the desktop tiles as it did, and what is new on the Tiling
tab waits.**, or **Until then nothing is tiled**. For the keys, how many do nothing yet, by name:
`KyprXSettings` stands for the key that opens the KyprX window, `KyprXCheatsheet` for the
cheatsheet and `KyprXWallpaper` for the wallpaper picker; the others are the tiling's, such as
`KyprXFocusLeft` or `KyprXNextLayout`. A long list of them is the compositor still running a part of
KyprX from before an update. Log out and back in, which loads the part installed. If the line
stays, see the first two lines above.

**N window rule(s) are outside the active list.**
N is the number of rules. KDE keeps its window rules in `~/.config/kwinrulesrc`, with a list of
the rules in force. These rules are in the file but not on the list, so they do nothing. KyprX
never deletes them, because they may be somebody's kept work. Nothing needs doing. Only up to
KWin 6.7: from 6.8 every rule group is in force, and there is no such thing as outside the list.

**N window rule(s) could take KyprX's naming.**
These rules force a title bar, as KyprX's own rules do, but do not carry KyprX's name. When a
window's title bar is turned back on, KyprX takes back only a rule with its name on it. **Tidy up
rule names**, in the same box, puts KyprX's name in front of the name each rule has; a name KDE
made up by itself becomes the application's name instead. Nothing else in a rule changes, and no
copy of the desk is kept first.

**Every window without a setting of its own is drawn with its title bar hidden, by a group the
decoration's own settings left behind.**
See [A window will not get its title bar back](#a-window-will-not-get-its-title-bar-back). While
this line is shown, the box holds the button **Give those windows their title bars back**.

One problem is reported somewhere else. When the global theme, the application style or the window
decoration is not the one KyprX expects, the Colours box on the Appearance tab starts with **Not
what this app expects.**, as [Appearance](user-guide/appearance.md) describes.

## "KyprX is not running"

This message appears when the KyprX window starts and the background service does not answer.
After you close the message, the KyprX window does not open. The message says to run `install.sh`
again "from the KyprX folder". That means the copy of the KyprX repository you installed from, not
the KyprX folder at `~/.config/kyprx/`, which holds your setup.

1. See what the service said when it last tried to start:

   ```sh
   systemctl --user status kyprd
   journalctl --user -u kyprd -n 50
   ```

2. If the repository has been moved or deleted since you installed, most of what the installer put
   in place points into a folder that has gone. Put the repository back, or run
   `./install.sh` again from where it is now.
3. Otherwise, run `./install.sh` again. It puts back every file the installer places.

## A shortcut does nothing

1. **Check that it is bound.** Each row on the Shortcuts tab shows its key, or **not bound**.
   [Shortcuts](user-guide/shortcuts.md) explains how to set one.
2. **Check whether the desktop knows the action.** Every key on the Shortcuts tab but the window
   keys and KRunner is KyprX's, and the compositor knows them only after it has loaded KyprX's
   script, which after an update is at the next login. The Problems box then says **Part of KyprX
   starts only at the next login**, with the keys that do nothing yet behind it, and the Wallpaper
   tab says **no key yet — install.sh has not reloaded the
   compositor script**. Log out and back in.
3. **Check whether it is a tiling key.** The tiling keys do nothing while KyprX's tiling is not
   running, and the Tiling tab then shows a band across its top that says why
   ([Windows are not tiled](#windows-are-not-tiled)). Most of them act on tiled windows only: with
   **Automatic tiling** off, only the focus keys, the layout keys and Toggle Automatic Tiling do
   anything
   ([Tiling](user-guide/tiling.md#automatic-tiling)). And another action may hold the same key: the
   desktop then runs the one it registered first
   ([Shortcuts](user-guide/shortcuts.md#when-another-action-has-the-same-key)).
4. **Check that the key reaches KDE at all.** Watch the desktop's shortcut registry while you press
   the key:

   ```sh
   dbus-monitor "interface='org.kde.kglobalaccel.Component',member='globalShortcutPressed'"
   ```

   Each shortcut KDE fires prints a few lines naming its owner (`kwin` for KyprX's keys, the tiling
   keys and the window keys) and the shortcut, such as `KyprXCheatsheet`. Press Ctrl+C to stop
   watching. `dbus-monitor` comes with D-Bus's command-line tools. If nothing appears for your key
   while other shortcuts do appear, KDE did not fire it: either the combination arrived bound to
   nothing, or it never arrived. KWin's debug console tells the two apart. It shows every key the
   compositor receives, on its **Input Events** tab:

   ```sh
   qdbus org.kde.KWin /KWin showDebugConsole
   ```

   Some keyboards send nothing for one key while certain modifiers are held down. If the key is
   missing from the debug console too, the keyboard is not sending it. Try another keyboard, or
   bind another combination.

## Windows are not tiled

1. **Open the Tiling tab.** When KyprX's tiling is not running, a band across its top says why, and
   what to do: tiling switched off, with a button that switches it back on; no part of KyprX in
   the compositor asking for the tiling yet; or KyprX taken off the desk. After an update, the band
   can say instead that KyprX's part of the compositor is from before the update: that part goes on
   tiling as it did until the next login.
   [When tiling is switched off](user-guide/tiling.md#when-tiling-is-switched-off) has each one.
   An orange line at the top of the **Zone layouts** box that says **The zone layouts and
   arrangements cannot be read here** is not one of these: the windows go on being tiled, and only
   the tab's Arrangements and Zone layouts boxes are locked, until the background service from
   before an update gives way to the new one ([After updating KyprX](#after-updating-kyprx)).
2. **Check Automatic tiling**, on the same tab. Off, windows stay where they are put, and only a
   window dropped into a zone moves ([Automatic tiling](user-guide/tiling.md#automatic-tiling)).
3. **Check that the window is one KyprX tiles.** A dialog, a window on every desktop, a window that
   cannot be resized, one too large for its zone, KyprX's own settings window, one of a class
   ticked under **Float** on the Windows tab, and one on an ignored screen or in a list under
   **Never tiled** are left where they are
   ([Floating windows](user-guide/tiling.md#floating-windows)). **Toggle Float** puts a floating
   one into the tiling, unless it is on every desktop, on an ignored screen or never tiled at all.
   A window only on another activity is laid out on that activity, not on the one you are on.
4. **Check whether the screen was full.** A window that opens when every zone of the arrangement's
   last layout is taken goes to a new desktop, or floats, as **When the arrangement is full** on
   the Tiling tab says ([A new window opened on another desktop](#a-new-window-opened-on-another-desktop)).
5. **Check the Problems box** on the Settings tab: KyprX's part of the compositor not installed or
   switched off is the first line it shows
   ([What the Problems box says](#what-the-problems-box-says)).

## A new window opened on another desktop

A window that opens when its screen already has a window in every zone of the arrangement's last
layout, as a fifth window does on Balanced, goes to a desktop of its own, named after the desktop it
came from with a number: **Work · 2** for **Work**. That is **When the arrangement is full**, on the
Tiling tab, at KyprX's default, **Open it on a new desktop**. Every rule of it is in
[A window that opens with every zone taken](user-guide/tiling.md#a-window-that-opens-with-every-zone-taken).

- **To find it**, look after your other desktops, or right after the one it came from when **Where
  a new desktop goes** says so. The name card names the desktop as the window goes there, unless
  **Show names on screen** is off.
- **The screen stayed where it was** when the window opened in the first 30 seconds after you
  logged in or the tiling was switched back on, or when the desktop did not give it the focus as it
  opened. KyprX cannot tell a window you opened from one that opened by itself, and those 30
  seconds are when a login opens its applications.
- **To bring it back**, move it to the desktop it came from, with the window's own menu (Alt+F3)
  or by dragging it in the Overview. A window moved onto a desktop squeezes in, whatever the
  setting, and the desktop KyprX made goes about three seconds after nothing is left on it and you
  have left it.
- **To keep new windows where you are**, choose **Let it float over the others** or **Squeeze it in
  by splitting the last zone** under **When the arrangement is full**, or give the arrangement a
  layout for one window more
  ([A layout for each number of windows](user-guide/tiling.md#a-layout-for-each-number-of-windows)).
- **A desktop KyprX made stays** while something is on it, a minimised window or a window of
  another activity included, or while a screen shows it; and for good once it is renamed, which
  makes it yours. Nothing is removed while KyprX's tiling is not running, or during a dry run.
- **A desktop of yours went away** when nothing was on it: its name was another desktop's, a middle
  dot and a number, such as **Work · 2** beside **Work**, which is how KyprX knows its own. Name it
  any other way and KyprX leaves it alone.
- **No room for another desktop**, on the name card, means there are 25 desktops already, the most
  the desktop allows, so the window floats instead.
- **The window squeezed in** although its arrangement was full: it is one of the windows that
  never go to a new desktop, such as a dialog or a window that came back from being minimised
  (**Which windows**, under
  [A window that opens with every zone taken](user-guide/tiling.md#a-window-that-opens-with-every-zone-taken)),
  or a window rule of yours forces the desktop it opens on, at **Force** or **Force temporarily**,
  and the rule wins.
- **A window your window rule puts on a desktop went to a new one**: the rule is set to **Apply
  initially**, the first choice in KDE's Window Rules settings, or to **Remember**. Either puts the
  window on its desktop as it opens and does not hold it there, so it goes to a desktop of its own
  like any other; only a rule that forces the desktop keeps it where the rule puts it (read in
  KWin's source, not measured).

KyprX's part inside the compositor writes a line for each window it sends away, such as
`KyprX: sent org.kde.dolphin to Work · 2, made for it, and the screen went with it`, among its
debug lines, which the desktop's logging rules usually leave out ([The log](#the-log)).

## Two tilers fight

Windows that keep jumping between two layouts are another tiling script at work beside KyprX's.
Nothing in KyprX looks for one: a tiling script switched on in System Settings, under Window
Management, KWin Scripts, lays out the same windows as KyprX's own tiling, and the two undo each
other's work until one is switched off (KNOWN-ISSUES). Switch the
other one off there, then log out and back in: switched off, a tiling script can go on tiling until
the session ends (measured in a nested KWin).

## A change to the compositor script did nothing

The compositor keeps what it has loaded of KyprX's script, `kwin-script/`, for the whole session,
and never reads its files again before the next login: a change to the script, by an update or by
hand, reaches the desktop only after you log out and back in. Running `./install.sh` again does
not change that, once the session has run the script. The Tiling tab says so with a band while the
script running is older than the one installed.

To try a change to the script without logging out, run it in a compositor of its own:
`scripts/sandbox.sh`, described in CONTRIBUTING.

## A window keeps its title bar

On the Windows tab, the window's **Status** column says **app refuses**. The application draws its
own title bar and does not let the compositor draw one, so KyprX has no title bar to hide. Select
the row and the line under the table explains the same thing. The switch that changes this is in
the application itself. In the Firefox family, for example, it is the option to use the system
title bar. Change it there, then close the window and open it again. With **Say when something did
not work** ticked, KyprX also shows a desktop notification when it first finds such a window.

## A window will not get its title bar back

You untick **Hide title bar** on the Windows tab and the window still has no title bar. The known
cause is a group that Klassy's own settings leave behind in its config file. Klassy reads that
group as a setting for every window that has no setting of its own, so when the group says to hide
the title bar, every one of those windows loses it.

KyprX removes that group by itself a few seconds after it appears, keeps a copy of the desk first,
and notes the removal in its log. It does not do this while KyprX is taken off the desk, and cannot
during a dry run or when the write fails. In those cases the Problems box on the Settings tab
shows the line that starts **Every window without a setting of its own is drawn with its title bar
hidden**, together with the button **Give those windows their title bars back**. The button asks
first, keeps a copy of the desk, and then removes the group. Klassy has
the details.

## The screen stops for a moment when the colours change

This is expected. Applying a colour scheme makes every open application repaint. Changing a colour
that the window outline follows makes the compositor read the decoration's settings again. The
screen stops while either one happens. How long it stops was measured: see the comments in
`daemon/theme.py` (`plan`) and `daemon/reload.py` (`invalidate_colour_cache`).
[Appearance](user-guide/appearance.md) says which changes cause the stop and which do not.

When the colour came from a new wallpaper, the log has one line starting with
`the wallpaper and its colour:`. It gives the time each step took and ends with the whole time.

## After updating KyprX

A new version of KyprX takes effect the next time each part of it starts: the background service,
the window, and KyprX's part inside the compositor. The background service asks the compositor to
load that part again on its first start as the new version, but the compositor keeps a part of
KyprX it has already run for the whole session, so the new one usually starts at the next login.
Until then the part from before the update goes on tiling as it did, and the Tiling tab says that
what is new on it starts at the next login
([A change to the compositor script did nothing](#a-change-to-the-compositor-script-did-nothing)).
On a Fedora system that updates as a whole, the restart the update needs anyway is that login.
Elsewhere, until you log out and back in, the window says so with a band and a **Restart the
background service** button
([KyprX was updated while it ran](user-guide/README.md#kyprx-was-updated-while-it-ran)).

Right after an update, the background service is still the one from before it until it starts
again, at that login or with that button, and meanwhile the Tiling tab's **Arrangements** and
**Zone layouts** boxes are locked, with an orange line at the top of the Zone layouts box: **The
zone layouts and arrangements cannot be read here, so nothing in these boxes is sent.** The service
from before the update speaks of them in a form the new window does not read, so the window
changes nothing in them rather than guess. The windows go on being tiled meanwhile. Log out and
back in, then open the tab again
([When the boxes cannot be used](user-guide/tiling.md#when-the-boxes-cannot-be-used)). Zone
layouts and arrangements an earlier KyprX wrote stay as it wrote them until you edit one
([Arrangements from an earlier KyprX](user-guide/tiling.md#arrangements-from-an-earlier-kyprx)).

Your setup is kept. When a new version keeps its own files in a new shape, it first copies the
files it will rewrite, as they were, into the KyprX folder's `snapshots/`, in a folder whose name
ends in `_before-bringing-this-install-up-to-date`; the log says which. Putting one back is copying
its files back, with the background service stopped.

An update started from the window — **Update now**, in the dialog that
[Look for a new version](user-guide/settings.md#look-for-a-new-version) opens — runs as a service
of its own, `kyprx-update`, so that restarting the background service, its own last step, does not
stop the update itself. What it said is in that service's journal:

```sh
journalctl --user -u kyprx-update
```

When the update does not go through, the window shows the last of what it said. Run in a terminal,
`./install.sh --update` shows every step as it happens.

When the new version's background service does not start, the update stops there with an error
instead of saying it is done, and the service's own journal says why:

```sh
journalctl --user -u kyprd
```

## The blur or the title bars stopped after an update

Klassy and Better Blur DX are compiled for one version of the desktop's window manager, KWin. After
a Plasma update, until each is built again for the new KWin, the window manager cannot load it: the
blur goes, or the title bars come back, and **What KyprX needs** says **installed, not running**.

- On Fedora, their repositories publish a new build for each Plasma release. Update again once
  they have: `sudo dnf upgrade`, or on a Fedora system that updates as a whole,
  `rpm-ostree upgrade` and a restart.
- On Arch, build each one again: the box gives the command.

Nothing in KyprX needs changing. **Check again**, on the Settings tab, confirms it once the new
build is in.

## A video wallpaper looks stuck

It is most likely paused on purpose. Smart Video Wallpaper Reborn pauses the video according to
its own setting, which you can change with **Pause the video** on the Wallpaper tab. Its default,
in version 2.15.0, is **Maximized or full-screen windows**. A paused video still shows through
KyprX's see-through windows, so it looks like a still picture. KyprX changes that setting only when
you change it on the Wallpaper tab. The plugin also pauses for reasons of its own, a low battery
for one, which are in its own settings. If **What KyprX needs**, on the Settings tab, says the
video plugin is **too old**, update it first. See [Wallpaper](user-guide/wallpaper.md) and
Smart Video Wallpaper Reborn.

## "module com.github.luisbocanegra.svwr is not installed"

When the desktop shell starts and loads a Smart Video Wallpaper Reborn wallpaper, it can log this
line once:

```
…/DayNightCyclePlugin.qml:2:1: module "com.github.luisbocanegra.svwr" is not installed
```

To find it:

```sh
journalctl --user -b | grep -i svwr
```

It means the plugin's optional compiled part is not installed. The plugin needs that part for one
choice only, **Day-night cycle** ("Use KDE's Day-Night Cycle service"), and its own settings show a
warning when that choice is picked. The rest of the plugin does not use it. KyprX never sets that
choice. Nothing needs doing. This was seen with Smart Video Wallpaper Reborn 2.15.0.

## Something changed that you did not want

- **A change made with one control** keeps no copy. Change it back where you made it.
- **Go back to a copy…**, on the Settings tab. KyprX keeps a copy of the desk before every change
  that writes a great deal at once: **Restore KyprX's defaults…**, **Take KyprX off this desk…**,
  putting the setup back, going back to a copy, giving title bars back, putting KyprX's zone layouts
  and arrangements back on the Tiling tab, and applying what arrived in the KyprX folder. The list shows the copies, newest first, and what going back to the selected
  one would change, before anything is done. Going back keeps a copy of the desk as it is at that
  moment, so going back can be undone too.
- **The KyprX folder.** The line under **Your KyprX folder** on the Settings tab says when KyprX
  applied something that arrived there, such as a copy, a `git pull` or an edit, with the time and
  the files. If you keep `~/.config/kyprx/` in git, git shows every change KyprX writes there:

  ```sh
  git -C ~/.config/kyprx diff -- .              # what changed since your last commit
  git -C ~/.config/kyprx log -p -- .            # every change you committed
  git -C ~/.config/kyprx restore -- <file>      # put one file back as it was last committed
  ```

  KyprX applies a file put back this way by itself, after keeping a copy of the desk.
- **Take KyprX off this desk…**, on the Settings tab, puts KDE back on its own defaults and Breeze
  theme, and KyprX stops changing anything: new windows are left alone. **Put my setup back**, in
  the band that then appears across the top of the window, reverses it.
- **Remove KyprX from this computer…**, on the Settings tab, is for leaving KyprX altogether: it
  asks whether KDE goes back as KDE has it and whether the KyprX folder stays, takes back what
  only KyprX used, and gives the command that removes its files.

[Settings](user-guide/settings.md) describes each of these buttons and the KyprX folder.

## Restarting the background service

```sh
systemctl --user restart kyprd
```

A settings window opened with its key closes during the restart, and so does the cheatsheet or
the wallpaper picker if one is open. The service started those windows, and stopping the service
stops everything it started. A window opened from the application menu or from a terminal stays
open.

You seldom need to start it by hand. After a crash the system does not restart it, but it starts
again by itself the next time a window opens or closes, or the KyprX window needs it.

Never stop it with `pkill`. AGENTS.md explains
why.

## Seeing what a change would do without doing it

The dry run is the whole app without any change to your settings: every change is written down in
plain words instead of being made. The recipe is in
AGENTS.md, and what a dry run does and does not
hold back is in MAP.md.

In the window, during a dry run:

- An orange band across the top starts with **Dry run.** Nothing is written, and each change is
  written down where `kyprd --dry-run` is running: the terminal it was started from, or the
  journal.
- Every message on the bottom line starts with **Dry run** and says that nothing was written.
- The **Title bar settings…** buttons cannot be pressed, because Klassy's own settings save for
  real and a dry run cannot stop that.
- If the band turns red and says **The dry run is over.**, the dry-run service has gone away
  (closing its terminal is enough) and the real one answers now. The window has stopped sending
  anything. Close it and open it again to go on.

On the desktop, KyprX's tiling makes and removes no desktop during a dry run: a window that opens
when every zone of its screen is taken floats instead
([A window that opens with every zone taken](user-guide/tiling.md#a-window-that-opens-with-every-zone-taken)).
That holds from the dry-run service's first answer to the tiling, which its start asks for: a
desktop made or removed before that answer arrives, by the real service's last one, is recorded all
the same (MAP).

If `kyprd --dry-run` answers `REFUSING to start in dry run`, the real service came back before
the dry run could start. The recipe says what to do then.

Some changes can be previewed without a dry run. **Restore KyprX's defaults…**, **Take KyprX off
this desk…**, **Go back to a copy…** and **Put my setup back** each show exactly what they would
change, and ask before they do anything. [The KyprX window](user-guide/README.md) describes the
bands and the bottom line.
