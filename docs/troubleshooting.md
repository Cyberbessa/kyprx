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

On the Settings tab. It lists what KyprX finds wrong with the setup, one line each, and says
**Nothing to report.** when there is nothing. Hold the pointer over a line for the details. The box
is checked again every time something changes while the tab is open. Every line it can show is
explained in [What the Problems box says](#what-the-problems-box-says).

### What KyprX needs

The **What KyprX needs** box, on the Settings tab, says for each of the five programs KyprX is
built on whether it is installed and running, and when one is not, the command that puts it right
on this computer ([Settings](user-guide/settings.md#what-kyprx-needs)). While one is not right, a
band across the top of the window names it on every tab.

### Desktop notifications

Some failures happen when no KyprX window is open: an application that keeps its own title bar, a
wallpaper or a colour that would not apply, a KyprX folder that could not be applied. With **Say
when something did not work** ticked on the Settings tab, KyprX shows these as desktop
notifications. [Settings](user-guide/settings.md) lists them.

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

## What the Problems box says

The lines appear in this order. The words in bold are exactly what the box shows.

**KyprX cannot see your windows: its part of the compositor is not installed.**
KyprX's script inside the compositor is missing. That script tells KyprX when windows open and
close, and it carries KyprX's own keys. Without it, new windows are not set up and the Windows tab
cannot list what is open. To fix it, run `./install.sh` again from the copy of the KyprX
repository you installed from (see [Install](../README.md#install)).

**KyprX cannot see your windows: its part of the compositor is switched off.**
This has the same effect: the script is installed but switched off. Switch **KyprX** on in System
Settings, on the KWin Scripts page (`systemsettings kcm_kwin_scripts` opens it), and apply. Or run
`./install.sh` again, which switches it on and makes the compositor load it.

**One key is not registered yet, so it does nothing.**
The details name the missing ones after **Not registered:**, even when there is more than one.
`KyprXSettings` stands for the key that opens the KyprX window, `KyprXCheatsheet` for the
cheatsheet and `KyprXWallpaper` for the wallpaper picker. The
compositor learns KyprX's keys only when it loads KyprX's script, which it does at login or when
the installer asks it to. Run `./install.sh` again, or log out and back in.

**Some per-window settings were written where the decoration cannot see them.**
The window decoration, Klassy, reads its per-window settings in numbered order and stops at the
first missing number, so the settings after a gap do nothing. The details give the numbers past
the gap. To fix it, change the **Hide title bar** or **Outline** box of any window on the Windows
tab. KyprX then rewrites the whole list without the gap and keeps the settings that were past it,
so the windows they are for take them on.

**N window rule(s) are outside the active list.**
N is the number of rules. KDE keeps its window rules in `~/.config/kwinrulesrc`, with a list of
the rules in force. These rules are in the file but not on the list, so they do nothing. KyprX
never deletes them, because they may be somebody's kept work. Nothing needs doing.

**N window rule(s) could take KyprX's naming.**
These rules force a title bar, as KyprX's own rules do, but do not carry KyprX's name. When a
window's title bar is turned back on, KyprX takes back only a rule with its name on it. **Tidy up
rule names**, in the same box, puts KyprX's name in front of the name each rule has; a name KDE
made up by itself becomes the application's name instead. Nothing else in a rule changes, and no
copy of the desk is kept first.

**Every window without a setting of its own is drawn with its title bar hidden, by a group the
decoration's own settings left behind.**
See [A window will not get its title bar back](#a-window-will-not-get-its-title-bar-back). While
this line is shown, the button **Give those windows their title bars back** is beside **Tidy up
rule names**.

**Nothing to report.**
KyprX found nothing wrong.

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
2. **Check whether it is one of KyprX's own keys**: the settings window, the cheatsheet or the
   wallpaper picker. The compositor knows them only after it has loaded KyprX's script, which it
   does at login or when the installer asks it to. The Problems box then says **One key is not
   registered yet, so it does nothing.**, and the Wallpaper tab says **no key yet — install.sh has
   not reloaded the compositor script**. Run `./install.sh` again, or log out and back in.
3. **Check whether it is a tiling key.** The tiling keys belong to the tiling script, so they do
   nothing while tiling is switched off. The Tiling tab then shows a band across its top, with a
   **Switch tiling back on** button beside it.
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
the window, and KyprX's part inside the compositor, which the background service reloads by itself
on its first start as the new version. On a Fedora system that updates as a whole, that is the
restart the update needs anyway. Elsewhere, until you log out and back in, the window says so with
a band and a **Restart the background service** button
([KyprX was updated while it ran](user-guide/README.md#kyprx-was-updated-while-it-ran)).

Your setup is kept. When a new version keeps its own files in a new shape, it first copies the
files it will rewrite, as they were, into the KyprX folder's `snapshots/`, in a folder whose name
ends in `_before-bringing-this-install-up-to-date`; the log says which. Putting one back is copying
its files back, with the background service stopped.

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
  putting the setup back, going back to a copy, applying a backup file, giving title bars back,
  and applying what arrived in the KyprX folder. The list shows the copies, newest first, and what
  going back to the selected one would change, before anything is done. Going back keeps a copy of
  the desk as it is at that moment, so going back can be undone too.
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

If `kyprd --dry-run` answers `REFUSING to start in dry run`, the real service came back before
the dry run could start. The recipe says what to do then.

Some changes can be previewed without a dry run. **Restore KyprX's defaults…**, **Take KyprX off
this desk…**, **Go back to a copy…** and **Put my setup back** each show exactly what they would
change, and ask before they do anything. [The KyprX window](user-guide/README.md) describes the
bands and the bottom line.
