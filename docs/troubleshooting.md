# Troubleshooting

Where KyprX says that something went wrong, what each of its warnings means, and how to get the
desktop back the way you want it. The commands can be copied into a terminal as they are; replace
anything in angle brackets first.

## Where to look first

### The line at the bottom of the window

The KyprX window answers every change on the line along its bottom: what it did, or why it could
not. A message stays there for six seconds, then goes, and is not kept anywhere in the window.
Some controls do not leave the reason on the line at all;
KNOWN-ISSUES.md lists which.

### The Problems box

On the Settings tab. It lists what KyprX finds wrong with the setup, one line each, and is on the
tab only while there is something to list. Hold the pointer over a line for the details. Every
line it can show is explained in [What the Problems box says](#what-the-problems-box-says).

### What KyprX needs

The **What KyprX needs** box is on the Settings tab while one of the four programs KyprX is
built on is not installed and running: it names each one that is not, and the command that puts
it right on this computer ([Settings](user-guide/settings.md#what-kyprx-needs)). **About
KyprX…**, on the same tab, lists all four, right or not. The tiling is KyprX's own; when it is
not running, the band at the top of the Tiling tab says why
([Windows are not tiled](#windows-are-not-tiled)).

To see where each answer came from, run `python3 /usr/share/kyprx/daemon/requirements.py --facts`
(where KyprX was installed as a package) or `python3 daemon/requirements.py --facts` (installed
with `install.sh`, from the folder it was installed from): one line per project, saying what the
answer was built on, after a line naming the KWin this session runs. The blur's line names every
copy of its file, each with the KWin it was built for and, on Arch, the package that installed
it. It changes nothing.

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

A `kyprd` started by hand for a dry run writes in the terminal it was started from instead, each
line beginning `kyprd [dry run]:`. A failure the service caught is one line:

```
kyprd: could not <what it was doing>: <kind of error> at <file>:<line> in <function>: <message>
```

Some lines say `failed on <what>` instead of `could not <what it was doing>`.
Send this line, with what you did just before it, to whoever looks into the problem. Not every
failure reaches the log, and not every one that does is marked as an error, so `-p err` can miss
it; KNOWN-ISSUES.md lists each gap.

**KyprX's part inside the compositor** writes to the compositor's own log:

```sh
journalctl --user -u plasma-kwin_wayland --since "30 min ago"
```

A mistake the compositor finds in KyprX's script shows there as a warning. The script's own
lines, such as `KyprX: tiling started` and `KyprX: tiling stopped`, are debug lines, which the
desktop's default logging rules leave out. The daemon's log above is the one to read first: what
the tiling is told comes from it. To see the script's own lines, give the compositor a logging
rule with a drop-in for its service, which reaches the compositor and no other program:

```sh
mkdir -p ~/.config/systemd/user/plasma-kwin_wayland.service.d
printf '[Service]\nEnvironment="QT_LOGGING_RULES=js.debug=true;qml.debug=true"\n' \
  > ~/.config/systemd/user/plasma-kwin_wayland.service.d/kyprx-debug.conf
systemctl --user daemon-reload
```

It takes effect at the next login. After that login,
`systemctl --user show plasma-kwin_wayland -p Environment` names the rule, and

```sh
journalctl --user -u plasma-kwin_wayland -b -g 'KyprX:'
```

shows every line the script wrote since. A rule given this way wins over the `*.debug=false` of
`qtlogging.ini`: the sandbox's nested KWin gets its rule the same way, and its lines come
through. The drop-in on a desk's own compositor is not measured. It lets through every debug
line of every script the
compositor runs, so the journal grows while it is there; delete the file, run
`systemctl --user daemon-reload`, and log in again to take it away.

Among the script's lines, those of the room a window's minimum is given and of a window that
moves itself say what was done to which window, by its class, with the numbers:

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
That script tiles the windows, tells KyprX when windows open and close, and carries KyprX's keys.
Without it nothing is tiled, new windows are not set up and the Windows tab cannot list what is
open. Fix: install the KyprX package again, or run `./install.sh` again from the copy of the
KyprX repository you installed from ([Install](../README.md#install)); the details under the
line say which.

**KyprX cannot see your windows: its part of the compositor is switched off.**
Same effect. Switch **KyprX** on in System Settings, on the KWin Scripts page
(`systemsettings kcm_kwin_scripts` opens it), and apply -- or run `./install.sh` again, which
switches it on and makes the compositor load it.

**Part of KyprX starts only at the next login: log out and back in.**
The compositor reads KyprX's part of it again only at login. After an update it still runs the
part it loaded before, or no part of KyprX has asked for its settings since the background
service started. The details say what waits until then: for the tiling, **Until then the desktop
tiles as it did, and what is new on the Tiling tab waits.** or **Until then nothing is tiled**;
for the keys, how many do nothing yet, by name (`KyprXSettings` opens the KyprX window,
`KyprXCheatsheet` the cheatsheet, `KyprXWallpaper` the wallpaper picker; the others are the
tiling's, such as `KyprXFocusLeft`). Log out and back in. If the line stays, see the first two
lines above.

**N window rule(s) are outside the active list.**
These rules are in `~/.config/kwinrulesrc` but not on its list of rules in force, so they do
nothing. KyprX never deletes them, because they may be somebody's kept work. Nothing needs doing.
Only up to KWin 6.7: from 6.8 every rule group is in force.

**N window rule(s) could take KyprX's naming.**
These rules force a title bar, as KyprX's own do, but do not carry KyprX's name; when a window's
title bar is turned back on, KyprX takes back only a rule with its name on it. **Tidy up rule
names**, in the same box, puts KyprX's name in front of the name each rule has. Nothing else in a
rule changes, and no copy of the desk is kept first.

**Every window without a setting of its own is drawn with its title bar hidden, by a group the
decoration's own settings left behind.**
See [A window will not get its title bar back](#a-window-will-not-get-its-title-bar-back). While
this line is shown, the box holds the button **Give those windows their title bars back**.

One problem is reported somewhere else: when the global theme, the application style or the
window decoration is not the one KyprX expects, the Colours box on the Appearance tab starts with
**Not what this app expects.** ([Appearance](user-guide/appearance.md)).

## "KyprX is not running"

This message appears when the KyprX window starts and the background service does not answer.
After you close it, the window does not open. The message says to run `install.sh` again "from
the KyprX folder" -- that means the copy of the KyprX repository you installed from, not the
KyprX folder at `~/.config/kyprx/`, which holds your setup.

1. See what the service said when it last tried to start:

   ```sh
   systemctl --user status kyprd
   journalctl --user -u kyprd -n 50
   ```

2. If the repository has been moved or deleted since you installed, most of what the installer
   put in place points into a folder that has gone. Put the repository back, or run
   `./install.sh` again from where it is now.
3. Otherwise, run `./install.sh` again. It puts back every file the installer places.

## The window does not open after a system update

On a Fedora system that updates as a whole, a KyprX installed with `install.sh` uses the PySide6
of the system image -- the library its windows are drawn with -- and an image update can take it
away: one was measured doing so. The settings window, the cheatsheet and the wallpaper picker
then do not open, while the background service goes on. This says whether it is that:

```sh
python3 -c 'import PySide6'
```

`ModuleNotFoundError: No module named 'PySide6'` is this. Add it to the system, then restart:

```sh
rpm-ostree install python3-pyside6
systemctl reboot
```

KyprX's own package is not affected: it requires `python3-pyside6`, so the update brings it in.

## A shortcut does nothing

1. **Check that it is bound.** Each row on the Shortcuts tab shows its key, or **not bound**.
   [Shortcuts](user-guide/shortcuts.md) explains how to set one.
2. **Check whether the desktop knows the action.** Every key on the Shortcuts tab but the window
   keys and KRunner is KyprX's, and the compositor knows them only after it has loaded KyprX's
   script, which after an update is at the next login. The Problems box then says **Part of KyprX
   starts only at the next login**, and the Wallpaper tab says **no key yet — install.sh has not
   reloaded the compositor script**. Log out and back in.
3. **Check whether it is a tiling key.** The tiling keys do nothing while KyprX's tiling is not
   running ([Windows are not tiled](#windows-are-not-tiled)), and most act on tiled windows only:
   with **Automatic tiling** off, only the focus keys, the layout keys and Toggle Automatic Tiling
   do anything. Another action may hold the same key: the desktop then runs the one it registered
   first ([Shortcuts](user-guide/shortcuts.md#when-another-action-has-the-same-key)).
4. **Check that the key reaches KDE at all.** Watch the desktop's shortcut registry while you
   press the key:

   ```sh
   dbus-monitor "interface='org.kde.kglobalaccel.Component',member='globalShortcutPressed'"
   ```

   Each shortcut KDE fires prints a few lines naming its owner (`kwin` for KyprX's keys, the
   tiling keys and the window keys) and the
   shortcut, such as `KyprXCheatsheet`; Ctrl+C stops watching. If nothing appears for your key
   while other shortcuts do, KDE did not fire it. KWin's debug console tells whether the
   combination never arrived or arrived bound to nothing -- it shows every key the compositor
   receives, on its **Input Events** tab:

   ```sh
   qdbus org.kde.KWin /KWin showDebugConsole
   ```

   If the key is missing from the debug console too, the keyboard is not sending it (some
   keyboards send nothing for one key while certain modifiers are held). Try another keyboard, or
   bind another combination.

## Windows are not tiled

1. **Open the Tiling tab.** When KyprX's tiling is not running, a band across its top says why
   and what to do
   ([When tiling is switched off](user-guide/tiling.md#when-tiling-is-switched-off)). An orange
   line at the top of the **Zone layouts** box saying **The zone layouts and arrangements cannot
   be read here, so nothing in these boxes is sent.** is not one of these: the windows go on
   being tiled, and only the tab's boxes
   are locked, until the background service from before an update gives way to the new one
   ([After updating KyprX](#after-updating-kyprx)).
2. **Check Automatic tiling**, on the same tab. Off, windows stay where they are put, and only a
   window dropped into a zone moves.
3. **Check that the window is one KyprX tiles.** A dialog, a window on every desktop, a window
   that cannot be resized, one too large for its zone, KyprX's own settings window, one of a
   class ticked under **Float** on the Windows tab, and one on an ignored screen or in a list
   under **Never tiled** are left where they are
   ([Floating windows](user-guide/tiling.md#floating-windows)). **Toggle Float** puts a floating
   one into the tiling. A window only on another activity is laid out on that activity.
4. **Check whether the screen was full.** A window that opens when every zone of the
   arrangement's last layout is taken floats, squeezes in or goes to a new desktop
   ([A new window opened on another desktop](#a-new-window-opened-on-another-desktop)).
5. **Check the Problems box** on the Settings tab: KyprX's part of the compositor not installed
   or switched off is the first line it shows.

## A new window opened on another desktop

A window that opens when its screen already has a window in every zone of the arrangement's last
layout, as a fifth window does on Balanced, goes to a desktop of its own, named after the one it
came from with a number: **Work · 2** for **Work**, when **When the arrangement is full** is on
**Open it on a new desktop**. Every rule of it is in
[A window that opens with every zone taken](user-guide/tiling.md#a-window-that-opens-with-every-zone-taken).

- **To find it**, look after your other desktops, or right after the one it came from when
  **Where a new desktop goes** says so. The name card names the desktop as the window goes there.
- **The screen stayed where it was** when the window opened in the first 30 seconds after you
  logged in or the tiling was switched back on, or when the desktop did not give it the focus as
  it opened.
- **To bring it back**, move it to the desktop it came from, with the window's own menu (Alt+F3)
  or by dragging it in the Overview. A window moved onto a desktop squeezes in, whatever the
  setting.
- **To keep new windows where you are**, choose **Let it float over the others** or **Squeeze it
  in by splitting the last zone**, or give the arrangement a layout for one window more.
- **A desktop KyprX made stays** while something is on it, a minimised window or a window of
  another activity included, or while a screen shows it; and for good once it is renamed, which
  makes it yours. **A desktop of yours went away** when nothing was on it and its name was
  another desktop's, a middle dot and a number -- how KyprX knows its own. Name it any other way
  and KyprX leaves it alone. **No room for another desktop**, on the name card, means there are
  25 already, the most the desktop allows.
- **The window squeezed in** although the arrangement was full: it is one of the windows that
  never go to a new desktop, such as a dialog or one that came back from being minimised, or a
  window rule of yours forces the desktop at **Force** or **Force temporarily**. **A window your
  rule puts on a desktop went to a new one**: the rule is at **Apply initially** or
  **Remember**, which put the window there as it opens but do not hold it (read in KWin's
  source, not measured).

KyprX's part inside the compositor writes a line for each window it sends away, such as
`KyprX: sent org.kde.dolphin to Work · 2, made for it, and the screen went with it`, among its
debug lines ([The log](#the-log)).

## Two tilers fight

Windows that keep jumping between two layouts are another tiling script at work beside KyprX's.
Nothing in KyprX looks for one: a tiling script switched on in System Settings, under Window
Management, KWin Scripts, lays out the same windows, and the two undo each other's work. Switch
the other one off there, then log out and back in: switched off, a tiling script can go on tiling
until the session ends (measured in a nested KWin).

## A change to the compositor script did nothing

The compositor keeps what it has loaded of KyprX's script, `kwin-script/`, for the whole session,
and never reads its files again before the next login: a change to the script, by an update or by
hand, reaches the desktop only after you log out and back in. Running `./install.sh` again does
not change that, once the session has run the script. The Tiling tab says so with a band while
the script running is older than the one installed. To try a change without logging out, run it
in a compositor of its own: `scripts/sandbox.sh`, described in
CONTRIBUTING.

## A window keeps its title bar

On the Windows tab, the window's **Status** column says **app refuses**. The application draws
its own title bar and does not let the compositor draw one, so KyprX has no title bar to hide.
The switch that changes this is inside the application itself -- in the Firefox family, for
example, it is the option to use the system title bar. Change it there, then close the window
and open it again. With **Say when something did not work** ticked, KyprX also shows a desktop
notification when it first finds such a window.

## A window will not get its title bar back

You untick **Hide title bar** on the Windows tab and the window still has no title bar. The known
cause is a group that Klassy's own settings leave behind in its config file: Klassy reads that
group as a setting for every window that has no setting of its own, so when the group says to
hide the title bar, every one of those windows loses it.

KyprX removes that group by itself a few seconds after it appears, keeps a copy of the desk
first, and notes the removal in its log. It does not do this while KyprX is taken off the desk,
and cannot during a dry run or when the write fails. In those cases the Problems box shows the
line that starts **Every window without a setting of its own**, together with the button **Give
those windows their title bars back**, which asks first, keeps a copy, and removes the group.
Klassy has the details.

## The screen stops for a moment when the colours change

This is expected. Applying a colour scheme makes every open application repaint; changing a
colour the window outline follows makes the compositor read the decoration's settings again. The
screen stops while either happens. How long was measured: see the comments in `daemon/theme.py`
(`plan`) and `daemon/reload.py` (`invalidate_colour_cache`).
[Appearance](user-guide/appearance.md) says which changes cause the stop and which do not. When
the colour came from a new wallpaper, the log has one line starting `the wallpaper and its
colour:`, giving the time each step took.

## After updating KyprX

A new version takes effect the next time each part of KyprX starts: the background service, the
window, and KyprX's part inside the compositor. The compositor keeps a part of KyprX it has
already run for the whole session, so the new one usually starts at the next login; until then
the old part goes on tiling as it did
([A change to the compositor script did nothing](#a-change-to-the-compositor-script-did-nothing)).
On a Fedora system that updates as a whole, the restart the update needs anyway is that login.
Elsewhere, until you log out and back in, the window says so with a band and a **Restart the
background service** button
([KyprX was updated while it ran](user-guide/README.md#kyprx-was-updated-while-it-ran)).

Right after an update, the background service is still the one from before it until it starts
again, and meanwhile the Tiling tab's **Arrangements** and **Zone layouts** boxes are locked:
the service from before the update speaks of them in a form the new window does not read, so the
window changes nothing in them rather than guess. The windows go on being tiled. Log out and
back in, then open the tab again
([When the boxes cannot be used](user-guide/tiling.md#when-the-boxes-cannot-be-used)).

Your setup is kept. When a new version keeps its own files in a new shape, it first copies the
files it will rewrite into the KyprX folder's `snapshots/`, in a folder whose name ends in
`_before-bringing-this-install-up-to-date`; the log says which. Putting one back is copying its
files back, with the background service stopped.

An update started from the window -- **Update now** -- runs as a service of its own,
`kyprx-update`, so that restarting the background service, its own last step, does not stop the
update. What it said is in that service's journal:

```sh
journalctl --user -u kyprx-update
```

When the update does not go through, the window shows the last of what it said; run in a
terminal, `./install.sh --update` shows every step. When the new version's background service
does not start, the update stops there with an error, and the service's own journal says why:

```sh
journalctl --user -u kyprd
```

## The blur or the title bars stopped after an update

Klassy and Better Blur DX are compiled for one version of the desktop's window manager, KWin --
the exact one: KWin 6.8.2 does not load a Better Blur DX built for 6.8.1. After a Plasma update,
until each is built again for the new KWin, the window manager cannot load it: the blur goes, or
the title bars come back, and **What KyprX needs** says **installed, not running**. The window
manager loads them as the session starts, so a new build counts only after logging out and back
in.

For the blur, the box reads the KWin it was built for out of its file and says it beside the KWin
this session runs. The line under it is one of three:

- **Built for an older KWin.** Build it again, then log out and back in.
  - On Arch: `paru -S --rebuild aur/kwin-effects-better-blur-dx`, with the name of the package
    you have, which the box gives. A plain `paru -S` builds nothing: paru keeps the package it
    built in `~/.cache/paru/clone`, says *is up to date -- skipping build*, and installs that
    old build again; `aur/` builds it from the AUR even where a repository such as Chaotic-AUR
    offers a ready-made copy under the same name. With yay it is `yay -S --rebuild aur/<package>`,
    and a plain `yay -S` is the same trap. With neither helper, the box gives a line that clones
    the package from the AUR, builds it with `makepkg -si`, and removes the folder. Installed
    from KyprX's package, pacman says so too as the update that brings the new KWin ends: *KyprX:
    Better Blur DX is built for KWin 6.8.1, and KWin 6.8.2 is installed now*, with
    the same command. It says it again after a reinstall that brought the old build back, and
    nothing once the build matches.
  - On Fedora, its repository publishes a new build for each Plasma release. Update again once it
    has: `sudo dnf upgrade`, or `rpm-ostree upgrade` and a restart.
- **Built for a newer KWin.** KWin was updated and this session still runs the one from before:
  log out and back in.
- **Built for this KWin.** Building it again does not help, unless that was just done and the
  session has not started again since. The window manager's log says why it
  did not load it:

  ```sh
  journalctl --user -b | grep better_blur_dx
  ```

  A line with *Effect unsupported* is the effect refusing to run, as it does without OpenGL.

Where the box cannot tell -- Klassy, whose file names no KWin, or a blur whose file names none --
it gives the most likely cause, a build for another KWin, with the same command. After logging
back in, **Check again**, on the Settings tab, confirms it.

## The system update stops at a repository that answers 404

On a Fedora system that updates as a whole, `rpm-ostree` stops the whole update when a
repository it reads answers 404, where `dnf` would skip that repository and go on. It happens on
the move to a new Fedora release, at a repository that has nothing for that release yet:

```text
Status code: 404 for https://.../cyberbessa/kyprx/fedora-45-x86_64/repodata/repomd.xml
```

KyprX's repository file names three repositories -- KyprX's own, Better Blur DX's and Klassy's --
and all three carry Fedora 44 and 45. A file saved before KyprX carried Fedora 45 names an older
repository for Klassy, which has no Fedora 45. Save the file again over the old one, then update:

```sh
sudo curl -Lo /etc/yum.repos.d/kyprx.repo \
  https://copr.fedorainfracloud.org/coprs/cyberbessa/kyprx/repo/fedora-45/cyberbessa-kyprx-fedora-45.repo
rpm-ostree upgrade
systemctl reboot
```

`kyprx.repo` is the name [the install](user-guide/install.md#fedora-systems-that-update-as-a-whole)
gives the file. If KyprX's repository is in a file of another name in `/etc/yum.repos.d/`, save
over that one instead, so that the repository is not listed twice. When the error names a
repository that is not one of the three, the fix is that repository's: until it carries the new
release, `enabled=0` in its file lets the update through.

## A video wallpaper looks stuck

It is most likely paused on purpose. Smart Video Wallpaper Reborn pauses the video according to
its own setting, changed with **Pause the video** on the Wallpaper tab; its default, in 2.15.0,
is **Maximized or full-screen windows**. A paused video still shows through KyprX's see-through
windows, so it looks like a still picture. The plugin also pauses for reasons of its own, a low
battery for one, in its own settings. If **What KyprX needs** says the plugin is **too old**,
update it first. See [Wallpaper](user-guide/wallpaper.md) and
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

It means the plugin's optional compiled part is not installed. The plugin needs it for one choice
only, **Day-night cycle**, and its own settings warn when that choice is picked; KyprX never sets
it. Nothing needs doing. Seen with Smart Video Wallpaper Reborn 2.15.0.

## Something changed that you did not want

- **A change made with one control** keeps no copy. Change it back where you made it.
- **Go back to a copy…**, on the Settings tab. A copy of the desk is kept before every change
  that writes a great deal at once: restoring the defaults, taking KyprX off the desk, putting
  the setup back, going back to a copy, giving title bars back, putting KyprX's zone layouts and
  arrangements back, and applying what arrived in the KyprX folder. The list shows what going
  back would change, before anything is done, and going back keeps a copy of the desk as it is,
  so it can be undone too.
- **The KyprX folder.** The line under **Your KyprX folder** on the Settings tab says when KyprX
  applied something that arrived there. If you keep `~/.config/kyprx/` in git:

  ```sh
  git -C ~/.config/kyprx diff -- .              # what changed since your last commit
  git -C ~/.config/kyprx log -p -- .            # every change you committed
  git -C ~/.config/kyprx restore -- <file>      # put one file back as it was last committed
  ```

  KyprX applies a file put back this way by itself, after keeping a copy of the desk.
- **Take KyprX off this desk…**, on the Settings tab, puts KDE back on its own defaults and
  Breeze theme, and KyprX stops changing anything. **Put my setup back**, in the band that then
  appears, reverses it.
- **Remove KyprX from this computer…**, on the Settings tab, is for leaving KyprX altogether.

[Settings](user-guide/settings.md) describes each of these buttons and the KyprX folder.

## Restarting the background service

```sh
systemctl --user restart kyprd
```

A settings window opened with its key closes during the restart, and so does the cheatsheet or
the wallpaper picker if one is open: the service started those windows, and stopping the service
stops everything it started. A window opened from the application menu or from a terminal stays
open. You seldom need to start it by hand: after a crash the system does not restart it, but it
starts again by itself the next time a window opens or closes, or the KyprX window needs it.

Never stop it with `pkill`. AGENTS.md explains
why.

## Seeing what a change would do without doing it

The dry run is the whole app without any change to your settings: every change is written down in
plain words instead of being made. The recipe is in
AGENTS.md, and what a dry run does and does
not hold back is in MAP.md.

In the window, during a dry run:

- an orange band across the top starts with **Dry run.** Nothing is written, and each change is
  written down where `kyprd --dry-run` is running;
- every message on the bottom line starts with **Dry run** and says that nothing was written;
- the **Title bar settings…** button cannot be pressed, because Klassy's own settings save for
  real and a dry run cannot stop that;
- if the band turns red and says **The dry run is over.**, the dry-run service has gone away and
  the real one answers now. The window has stopped sending anything; close it and open it again.

On the desktop, KyprX's tiling makes and removes no desktop during a dry run: a window that opens
when every zone of its screen is taken floats instead. That holds from the dry-run service's
first answer to the tiling, which its start asks for; a desktop made or removed before that
answer arrives, by the real service's last one, is recorded all the same
(MAP). If `kyprd --dry-run` answers `REFUSING to start in dry run`,
the real service came back before the dry run could start; the recipe says what to do then.

Some changes can be previewed without a dry run: **Restore KyprX's defaults…**, **Take KyprX off
this desk…**, **Go back to a copy…** and **Put my setup back** each show exactly what they would
change, and ask before they do anything.
