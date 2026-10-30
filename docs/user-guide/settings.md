# Settings

The Settings tab holds what KyprX keeps about itself, and the few changes that write a great deal
at once. From top to bottom:

1. **Notifications**;
2. **Your KyprX folder**;
3. **What KyprX needs**, with **Check again**, only while one of the programs KyprX is built on is
   not right;
4. **Problems**, with its two repairs, only while KyprX has found something wrong;
5. KyprX's version, with **About KyprX…** and **Look for a new version**;
6. a row along the bottom: **Go back to a copy…** on the left, and **Restore KyprX's defaults…**,
   **Take KyprX off this desk…** and **Remove KyprX from this computer…** on the right.

KyprX's messages call everything it controls on this computer **the desk**: the window
decoration's settings, the window rules, the window manager's settings for focus, blur and
animation, KyprX's tiling, the colours, the keys on the [Shortcuts](shortcuts.md) tab and the
wallpaper.

The tick box on this tab is written the moment you use it. The buttons that write a great deal at
once ask first, show what they would change, and keep a copy of the desk before they write
anything; in every one of those questions the answer already selected is the one that changes
nothing. What each button then says appears on the line at the bottom of the window
([The line at the bottom](README.md#the-line-at-the-bottom)).

## Notifications

**Say when something did not work.** Ticked, KyprX shows a desktop notification, titled
**KyprX**, when one of the five things below fails. Nothing is shown when things go well, so
unticking it silences those only. KyprX's default: ticked.

| The notification says | When |
|---|---|
| The application's window class, then **This app refuses a server-side decoration: it draws its own title bar. Look for a title bar option in its own settings.** | the first time KyprX finds that an application keeps its own title bar although **Hide title bar** is ticked for it ([A window keeps its title bar](../troubleshooting.md#a-window-keeps-its-title-bar)) |
| **The wallpaper could not be changed.** | a wallpaper chosen in the picker, with **Colour from the wallpaper** ticked, did not go on ([Wallpaper](wallpaper.md#colour-from-the-wallpaper)) |
| **The wallpaper's colour could not be applied.** | the colour that wallpaper hands to the desktop did not go on |
| **The KyprX folder was not applied**, then the first problem found, and how many more there are | something arrived in the KyprX folder that cannot be applied (see [What is refused, and what is skipped](#what-is-refused-and-what-is-skipped)). Said once for each different set of problems, not at every attempt |
| **Part of the KyprX folder was not applied**, then the first thing that did not go in | what arrived in the folder was applied, except a part this computer could not take, such as a colour preset it does not have |

Every one of these also goes to KyprX's log ([The log](../troubleshooting.md#the-log)). During a
dry run nothing reaches the screen: the notification is written in the log instead.

## Your KyprX folder

The KyprX folder is `~/.config/kyprx/`: everything KyprX controls on the desk, as a handful of
readable files you can copy to another computer, keep in git, or edit. KyprX writes it by itself
a few seconds after anything changes, and applies by itself whatever arrives in it, after keeping
a copy of the desk.

### The path, Copy and Open the folder

The box starts with the folder's path, with `~` standing for your home folder. The path can be
selected with the mouse; hold the pointer over it for the full path.

- **Copy** puts the folder's full path on the clipboard, and the line at the bottom says **The
  folder's path is on the clipboard.**
- **Open the folder** first brings the folder and the desk into step, then opens the folder in the
  file manager. Bringing them into step means what any pass does (see below): if something arrived
  in the folder and has stood still for three seconds, it is applied before the folder opens. When
  the folder is not there yet, the line at the bottom says **The folder is not there yet: KyprX
  writes it a moment after it starts.**

### The line under the path

One sentence says how the folder stands with the desk. It changes as soon as KyprX reports
anything new.

- **In step with the desk.** Nothing is waiting in either direction.
- **Waiting before applying what arrived:** followed by the reason:
  - **the folder's files are still changing** — KyprX waits until they have been still for three
    seconds;
  - **git is in the middle of** a merge, a rebase, a cherry-pick, a revert or writing its index
    **in the repository around the folder**;
  - **the desktop's shortcut registry or shell is not up yet** — at the start of a session, see
    [When KyprX applies what arrives](#when-kyprx-applies-what-arrives).
- **What is in the folder cannot be applied, so nothing was applied and nothing in it is written
  over:** followed by every problem found, on an orange background. See
  [What is refused, and what is skipped](#what-is-refused-and-what-is-skipped).
- **Applied what arrived in the folder at** *time* **(***files***). A copy of the desk from before
  was kept — Go back to a copy… undoes it.** The time is the hour and minute it was applied, and
  the files are the ones that arrived. Two more sentences can follow:
  - **Where the folder and the desk had both changed something, the folder won:** followed by each
    setting, named by its file and its place in the file, for example `settings.json/opacity`;
  - **Not applied:** followed by each part this computer could not take.
- **Dry run: the folder is not written, and a change arriving in it is only reported.**

### What is in the folder

| File | What it holds |
|---|---|
| `settings.json` | KyprX's own settings: notifications, colour from the wallpaper, the opacity of see-through windows, what a new window gets, and which key the cheatsheet shows for an action that has several |
| `profiles.json` | The profiles made on the [Appearance](appearance.md#profiles) tab |
| `windows.json` | One entry per window that differs from what a new window gets, with its columns from the [Windows](windows.md) tab |
| `decoration.json` | All of the window decoration's own settings, which is more than KyprX's window shows; its per-window settings that are not one window's entry; and the decoration presets those point at |
| `kwin.json` | The window manager's settings for the window border, focus, the blur and the window animation, and whether each of those two is switched on |
| `tiling.json` | KyprX's tiling, everything on the [Tiling](tiling.md) tab but Focus: whether it is switched on and tiles automatically, whether names show on screen, where a new window goes and what it does when its arrangement is full, where a new desktop goes, the gaps, the zone layouts and the arrangements, and the windows that float or are never tiled. A window with a row of its own on the Windows tab says whether it floats in `windows.json` instead |
| `shortcuts.json` | Every key of every action on the [Shortcuts](shortcuts.md) tab |
| `colours.json` | The mode, the colour preset, a colour of your own and how far it soaks in |
| `wallpaper.json` | The wallpaper of every activity, by the activity's name and by the path of each screen's file, when a video pauses, and the wallpaper picker's layout, whether the strip shows its text, whether a wallpaper goes on every screen, video folder and whether KDE's own wallpapers are listed |
| `kyprx.json` | Which shape these files are in. Leave it as KyprX wrote it |
| `README.md` | A short description of the folder |
| `.gitignore`, `.stignore` | Keep the copies of the desk and half-written files out of git and out of Syncthing |
| `snapshots/` | The copies of the desk (see [Go back to a copy](#go-back-to-a-copy)). Not part of the setup |

Every JSON file is written with its keys in alphabetical order, two spaces of indent, and no date
or time inside, so that comparing two versions of the folder shows the change and nothing else.

`README.md`, `.gitignore` and `.stignore` are written only when they are missing, and never over a
file that is there: edit them as you like. One you delete comes back at the next pass that writes
the folder. The one exception is a `README.md` that is still, letter for letter, the text an
earlier KyprX wrote: nobody has touched it, so it is brought up to date with this one's.

MAP lists every file KyprX keeps on the computer, in this
folder and outside it.

### Editing the folder by hand

Any file can be edited, and the edit is applied by itself a few seconds after you save it (see
[When KyprX applies what arrives](#when-kyprx-applies-what-arrives)). Every file is checked first:
a mistake in any of them means nothing is applied, and the line under the path says where the
mistake is.

**`settings.json`**

| Key | What it holds | The same setting in the window |
|---|---|---|
| `notify` | `true` or `false` | **Say when something did not work**, above |
| `colour_from_wallpaper` | `true` or `false` | **Colour from the wallpaper**, above the tabs ([The KyprX window](README.md#colour-from-the-wallpaper)) |
| `opacity` | a whole number from 1 to 100 | **Opacity**, in the Window box of the [Appearance](appearance.md#window) tab |
| `new_windows` | four switches, each `true` or `false`: `hide_title_bar`, `outline`, `transparency`, `blur` | none: see below |
| `cheatsheet_shows` | for an action with several keys, the one the cheatsheet shows, written like `Meta+Space` | **on the card**, on the [Shortcuts](shortcuts.md) tab |

**`new_windows` is the only way to choose what a new window gets.** No control in the window
changes it. Its four switches are the ticks an application's window gets the first time KyprX
meets that application: **Hide title bar**, **Outline**, **Transparency** and **Blur**, in that
order; `hide_title_bar` set to `true` means the title bar is hidden. KyprX's own values, and what
a new window gets in the other columns, are on [Windows](windows.md#what-a-new-window-gets).

Changing them moves no window KyprX has already met: they decide what the *next* new application
gets. The one exception is a change that brings a new `windows.json` along with it, such as a
`git pull` that carries both files. Then every window `windows.json` does not list is brought to
the new values too, because the entries in that file were written against them.

**`windows.json`** holds one entry per window class under `windows`:

| Key | Column on the Windows tab | What it holds |
|---|---|---|
| `hide_title_bar` | **Hide title bar** | `true` or `false` |
| `outline` | **Outline** | `true` or `false` |
| `transparency` | **Transparency** | `true` or `false` |
| `opacity` | **Opacity** | the window's own number, a whole number from 1 to 99. Left out, the window takes the shared **Opacity** of the Appearance tab |
| `blur` | **Blur** | `true` or `false` |
| `float` | **Float** | `true` or `false` |
| `animate` | **Animate** | `true` or `false` |
| `draws_own_title_bar` | none | written only for a window whose title bar is hidden: whether the application draws a title bar of its own. It tells a computer that has not met the application yet how to hide its bar. Leave it as KyprX wrote it |
| `decoration` | none | the window's other settings made in the decoration's own settings, under the decoration's own names |

A window that is listed is brought to its entry, and a key left out of an entry reads as what a
new window gets. A window that is not listed is brought to what a new window gets, not floating and
animated, so deleting a window's entry puts it back to that. A window class KyprX has not met yet
can be added: it is set up as the entry says, and counts as met from then on. The windows KyprX
never adjusts by itself
([Windows](windows.md#windows-that-never-get-the-defaults-by-themselves)) get no entry.

**`colours.json`**

| Key | What it holds |
|---|---|
| `mode` | `dark` or `light` |
| `preset` | the colour preset's short name: `klassy-dark`, `longive`, `catppuccin-mocha`, `nord`, `gruvbox-dark`, `dracula`, `solarized-dark`, `monochrome-dark`, `klassy-light`, `catppuccin-latte`, `solarized-light`, `gruvbox-light`, `rose-pine-dawn` or `monochrome-light`. `carl` is read as `longive` |
| `own_colour` | a colour of your own, as three numbers from 0 to 255 separated by commas, such as `255,152,8`; empty for none |
| `tint` | how far your own colour soaks into the backgrounds, as a fraction: `0.25` is 25 % |

The presets themselves are described on [Appearance](appearance.md#the-presets).

**`wallpaper.json`**

- `activities` holds one entry per activity, by its name; a second activity with the same name is
  written with ` #2` after it. Each entry has `on_screen`, a list with one item per screen, in the
  order of the screens:
  - `screen`: which screen, as a number, `0` being the primary and `1` the next. A screen is a
    place in the desktop's order of screens rather than one monitor: make another monitor the
    primary, and its wallpaper is the one for `0`. An item without it is put back the way a folder
    written before the screens were numbered is (see below);
  - `kind`: `image` or `video`, or the name of another wallpaper plugin, which KyprX does not set;
  - `file`: the path of the picture or video, with `~` for your home folder;
  - `pause`, for a video only: when it pauses, as the video plugin numbers its own choices: `0`
    **Maximized or full-screen windows**, `1` **Active window**, `2` **At least one window is
    visible**, `3` **Never**.
- `picker` holds `layout`, `pages` or `strip`; `strip_text`, `true` or `false`, for whether the
  strip shows the names and the keys; `all_screens`, `true` or `false`, for **Set for all
  screens**; `video_folder`, a path, or empty for the folder the
  [Wallpaper](wallpaper.md) tab works out by itself; `image_folder`, the same for pictures; and
  `kde_wallpapers`, `true` or `false`, for whether KDE's own wallpapers are listed. A `layout` of
  `strip-names`, which an earlier KyprX wrote, reads as `strip` with `strip_text` true.

**`shortcuts.json`** holds, under `keys`, each action's name and the list of its keys, each written
like `Meta+Alt+Left`: the modifiers first, in the order Meta, Ctrl, Alt, Shift. A key that takes
several presses in a row is a list of its presses. An action from outside the window manager, such
as KRunner's, is named by its program, a slash and the action.

**`profiles.json`** holds the list of profiles, each with its `name` and its `look`. A name can be
changed freely. A look is checked when the file arrives, and a key a look does not carry stops the
whole folder from being applied.

**`decoration.json` and `kwin.json`** use the other programs' own group and key names, and the
values exactly as those programs write them. Which keys KyprX knows, and what each does, is on
Klassy for the decoration, and on
KDE Plasma, Better Blur DX
and Geometry Change for the window manager, the blur and the
window animation. In `kwin.json`, `plugins` switches the blur and the window animation on or off
with `true` or `false`, and the two lists of windows inside it (not animated, not blurred) hold
only windows KyprX does not look after: the others are in `windows.json`.

**`tiling.json`** uses the names of KyprX's tiling's own settings, each value but the zone layouts
and arrangements as text in quotes, the way KyprX writes it, and a setting left out is one nothing
has been written for.

| Key | What it holds | The same setting on the [Tiling](tiling.md) tab |
|---|---|---|
| `tiling` | `"true"` or `"false"`; left out, it reads as off | none: whether KyprX's tiling is switched on ([When tiling is switched off](tiling.md#when-tiling-is-switched-off)) |
| `autoTiling` | `"true"` or `"false"` | **Automatic tiling** |
| `showOsd` | `"true"` or `"false"` | **Show names on screen** |
| `newWindowPosition` | `"0"` at the end of the layout, `"1"` as the master window, `"2"` before the focused window, `"3"` after it | **Where a new window goes** |
| `newWindowOverflow` | `"0"` on a new desktop, `"1"` floating over the others, `"2"` squeezed in by splitting the last zone | **When the arrangement is full** |
| `newDesktopPosition` | `"0"` after your desktops, `"1"` right after the one the window came from | **Where a new desktop goes** |
| `floatUtility` | `"true"` or `"false"` | **Float utility windows** |
| `adjustLayoutLive` | `"true"` or `"false"` | **Neighbours follow while you drag an edge** |
| `screenGapTop`, `screenGapBottom`, `screenGapLeft`, `screenGapRight`, `screenGapBetween` | a whole number of pixels from `"0"` to `"200"` | the [Gaps](tiling.md#gaps) |
| `arrangements` | the zone layouts and the arrangements, as one value written out rather than in quotes, with the rules of the two boxes. Ones an earlier KyprX wrote stay as it wrote them until something in either box is edited ([Arrangements from an earlier KyprX](tiling.md#arrangements-from-an-earlier-kyprx)) | the [Arrangements](tiling.md#arrangements) and [Zone layouts](tiling.md#zone-layouts) boxes |
| `floatingClass` | window classes between commas, only those of windows KyprX does not look after, as the lists of `kwin.json` hold | the **Float** column on the [Windows](windows.md#float) tab |
| `floatingTitle`, `ignoreClass`, `ignoreTitle`, `ignoreScreen` | entries between commas | the four lists under [Never tiled](tiling.md#never-tiled) |

A gap outside 0 to 200 is read as the nearer end, and any other value the tiling cannot read as
one of its own, such as `"7"` for `newWindowOverflow`, as the setting left out.

### When KyprX writes the folder

About two and a half seconds after the last change on the desk. A change within that time starts
the wait again, so dragging a number is one write.

It notices:

- every change made in KyprX's window;
- a change another program makes to the decoration's settings, its presets, the window manager's
  settings or the window rules, such as one made in the decoration's own settings or in System
  Settings;
- a key changed in System Settings;
- the wallpaper or the activity changing.

A change it does not watch for, such as a colour scheme chosen in System Settings, reaches the
folder at the next pass: the next change of the kinds above, the next start of KyprX's background
service, or **Open the folder**.

Only the parts the desk changed are written; a file with nothing new in it is left alone. A file
deleted from the folder is written again from the desk at the next pass.

The folder is not written while KyprX is off the desk (see
[Take KyprX off this desk](#take-kyprx-off-this-desk)), during a dry run, or while something that
arrived in it cannot be applied.

### When KyprX applies what arrives

**What counts as arriving:** any of the nine setup files that differs from what KyprX last wrote
or applied there. A copy, a `git pull`, a checkout, a stash or an edit are all the same to KyprX.

**Not half-way.** It waits until the folder's files have been still for three seconds, and while
git is in the middle of something in the repository around the folder, looking again every three
seconds. The line under the path says what it is waiting for.

**Everything is checked first.** One problem in any file, and nothing is applied (see
[What is refused, and what is skipped](#what-is-refused-and-what-is-skipped)).

**A copy of the desk is kept first**, with the files that arrived kept beside it. If the copy cannot
be kept, nothing is applied. **Go back to a copy…** undoes what was applied.

**Only what changed goes in, setting by setting.** KyprX remembers the last moment the folder and
the desk agreed, and for each setting in a file that arrived:

- changed in the folder only: the folder's value goes in;
- changed on the desk only, since that moment: the desk's value stays;
- changed on both: the folder's value goes in, and the line under the path names the setting.

A list, a number or a word is one setting; a group of settings is compared setting by setting.
The zone layouts and arrangements in `tiling.json` are one setting, however many there are, because
an arrangement names the zone layouts it uses: when the folder and the desk both changed them, the
folder's go in whole, and the desk's are in the copy of the desk kept first. The same ones written
as an earlier KyprX wrote them on one side count as no change
([Arrangements from an earlier KyprX](tiling.md#arrangements-from-an-earlier-kyprx)).

**A new computer.** When KyprX remembers no such moment and the folder has its `kyprx.json`, the
whole folder is applied. That is what happens when you copy the folder onto a fresh install: the
next time KyprX's background service starts, the folder goes on before any window is given the
defaults. The copy of the desk kept before it is never thrown away (see
[Go back to a copy](#go-back-to-a-copy)).

**At the start of a session**, the shortcut registry or the desktop shell can come up after KyprX.
When what arrived carries keys or a wallpaper, KyprX waits for them for up to a minute, and keeps
new windows from being given the defaults meanwhile. After a minute it applies what it can, and
keeps the keys it could not put on yet for when it can.

**KyprX's own keys on a new computer.** KyprX's own actions exist on the desktop only once its part
inside the compositor has started, which on a computer where KyprX was just installed is after the
folder has been applied. Their keys from the folder are kept until then and put on as soon as the
actions are there; the folder keeps saying them meanwhile.

**Every window is brought to the folder.** Each window KyprX looks after is brought to its entry in
`windows.json`, or to what a new window gets when it has none.

The decoration, the window manager and the windows go first, together, so the screen stops once
for all of them; then KyprX's own settings and profiles; then the keys, the colours and the
wallpaper. During a dry run what arrived is described in the log and never applied.

### What is refused, and what is skipped

**Refused: nothing is applied, and nothing in the folder is written over.** The line under the
path turns orange and lists every problem, and a notification says so when notifications are on.
KyprX goes on refusing, and writes nothing into the folder either, until the file is put right; the
next save of it is applied. A folder is refused when:

- a file is not valid JSON: the file, the line and the column are named;
- a file holds a whole number too long to read, more than 4300 digits: the file is named, with no
  line;
- a file is not an object with names in it, or cannot be read as text;
- `kyprx.json` cannot be read, does not say which shape the folder is in, or says it was written
  by a newer KyprX: then the whole folder is left exactly as it is;
- in `settings.json`: `notify` or `colour_from_wallpaper` is not `true` or `false`; `opacity` is
  not a whole number from 1 to 100; a switch in `new_windows` is not `true` or `false`; a key in
  `cheatsheet_shows` is not a key;
- in `profiles.json`: the profiles are not a list, or a profile's look cannot be read;
- in `windows.json`: an entry or one of its switches is not what the table above says, or
  `opacity` is not a whole number from 1 to 99;
- in `decoration.json` or `kwin.json`: a part that should hold names holds something else;
- in `tiling.json`: zone layouts and arrangements that break one of the two boxes' rules, which
  the line names, or that a newer KyprX wrote; a value that is not text in quotes; or a setting
  whose name is not letters and digits;
- in `shortcuts.json`: a key that is not a key;
- in `colours.json`: a mode other than `dark` or `light`, or an own colour that is not three
  numbers from 0 to 255;
- in `wallpaper.json`: `kde_wallpapers`, `strip_text` or `all_screens` is not `true` or `false`, a
  `screen` is not a whole number from 0, or two wallpapers of one activity name the same screen.

**Skipped and said: the rest goes in.** Each of these is named after **Not applied:** on the line
under the path, and in a **Part of the KyprX folder was not applied** notification:

- a colour preset this computer does not have: the colours are left as they are;
- a wallpaper whose file is not there, an activity this computer does not have, or a video when
  the video wallpaper plugin is not installed: that screen's wallpaper, or that activity's, is left
  as it is;
- for a folder written before its screens were numbered, an activity whose screens have different
  wallpapers: the first screen's goes on all of them, unless the primary screen already shows it;
- a key another action holds now: that action's keys are left as they are;
- the colours, the profiles or the wallpaper refused by the desktop's own tools.

Each screen gets its own wallpaper back, and a screen the folder does not name keeps the one it
has: a folder written on a computer with one screen sets the primary screen of a computer with two
and leaves the other alone. A screen the folder names and this computer does not have is left out,
and only the log says so, because a folder shared with a computer with fewer screens would
otherwise say it on every arrival.

### What the folder leaves out

- **The wallpaper files themselves.** The folder names them by their path. Bring your wallpaper
  folder along, to the same place under your home folder.
- **Facts about this computer:** which windows it has met, which applications refuse to have
  their title bar taken off, and which screen's wallpaper the colour comes from (**Colour from the
  wallpaper of**, on [Appearance](appearance.md)), whose name is this computer's. Two computers
  sharing a folder would otherwise correct each other for ever.
- **The decoration's bundled presets.** Only a preset that one of the decoration's per-window
  settings points at travels. The decoration's own record of this computer, and the leftover
  group its settings can leave behind (see [Problems](#problems)), are left out too.
- **Whether new windows are being adjusted**, the **Adjust new windows** tick above the tabs: it is
  what you untick while you set something up by hand, a moment rather than a setup.
- **Window rules you wrote yourself** in System Settings. KyprX's own rules are rebuilt from
  `windows.json`.
- **A window at exactly what a new window gets**, and KyprX's own overlays.
- **The copies of the desk** in `snapshots/`, which belong to this computer.

### Keeping the folder in git

- KyprX never runs git itself: what to commit, and when, is yours. A change you make in the window
  is in the folder about two and a half seconds later.
- The `.gitignore` KyprX writes keeps `snapshots/` and half-written `*.new` files out of the
  repository.
- The folder can be a repository of its own, or sit inside a larger one, such as a repository of
  all your settings files. The folder, or any file in it, can be a symbolic link into that
  repository: KyprX writes into the file the link points at and leaves the link as it is.
- A `git pull`, `checkout`, `stash` or `restore` that changes the folder is applied like any other
  edit, once git has finished. Checking out an old commit puts that old setup on the desk;
  **Go back to a copy…** undoes it.
- The commands to see and undo what changed are in
  [Troubleshooting](../troubleshooting.md#something-changed-that-you-did-not-want).

### Go back to a copy

**Go back to a copy…**, on the left of the row along the bottom of the tab, puts the desk back as
it was before an earlier change that wrote a great deal at once. When there is no copy yet, the line
at the bottom says **There is no copy of the desk yet: one is kept before each change that writes a
great deal at once.**

Otherwise a window titled **Go back to a copy of the desk** lists the copies, newest first, each as
the date and time it was taken and why. Selecting one shows underneath exactly what going back to
it would change, in the words a dry run uses. **Go back to this copy** is greyed until a copy is
selected; **Cancel** is the answer already selected.

- A copy taken during a dry run ends in **(dry run: in memory only)**. It is kept in the background
  service's memory, never on disk, and is gone when that dry run stops.
- A copy that cannot be put back ends in the reason, in brackets, and cannot be selected: one taken
  by a newer KyprX, or one that does not say what shape it is in.

**Going back keeps a copy of the desk as it is first**, so going back can be undone too. The line at
the bottom says **Keeping a copy of the desk as it is, then going back… the desktop's own tools take
a second or two**, and then one of:

- **The desk is back as it was. The copy of how it was a moment ago is first in the list, if you
  want that back.**
- **Most of it came back, but:** followed by what did not;
- **That did not go through:** followed by the reason. Nothing was changed.

**What a copy holds**, and puts back exactly:

- the decoration's settings, its per-window settings and its presets;
- the window manager's settings for the window border, focus, the blur and the window animation,
  and whether each of those two is switched on;
- KyprX's tiling, the zone layouts and arrangements included, written as they were when the copy
  was taken. A copy taken before KyprX tiled the windows itself holds none of it, and leaves
  KyprX's tiling as it is now rather than delete it for not having it;
- the window rules that are KyprX's, in the copy or now. A rule KyprX made since the copy goes, one
  it made that was deleted since comes back, and a rule of yours that KyprX took on since, by
  putting its name on it, goes back to how it was. A rule you wrote in System Settings after the
  copy was taken is not KyprX's, and is left as it is;
- KyprX's own settings, its profiles, and which windows it has met;
- the colours;
- every key of every action on the Shortcuts tab;
- the wallpaper of every activity.

What cannot come back is said rather than forced: a key another action holds now (that action's
keys are left as they are), a wallpaper file that is gone, an activity this computer no longer
has, a video when the video plugin is not installed, and colours the desktop's own tools refused.
MAP has the file-by-file detail.

**When a copy is kept.** The list gives the reason in these words:

| The list says | Kept before |
|---|---|
| **before restoring KyprX's defaults** | [Restore KyprX's defaults…](#restore-kyprxs-defaults) |
| **before taking KyprX off this desk** | [Take KyprX off this desk…](#take-kyprx-off-this-desk) |
| **before putting the setup back** | [Put my setup back](#put-my-setup-back) |
| **before going back to** *copy* | going back to another copy |
| **before applying what arrived in the KyprX folder** | [applying what arrived](#when-kyprx-applies-what-arrives) in the folder |
| **before removing the decoration's leftover Exceptions group** | removing that group, whether KyprX does it by itself or [the button](#give-those-windows-their-title-bars-back) is pressed |
| **before KyprX's zone layouts and arrangements** | **Put KyprX's zone layouts and arrangements back…** on the [Tiling](tiling.md#the-zone-layouts-and-arrangements-kyprx-comes-with) tab |

**How many are kept.** The twenty newest, plus every copy that is never thrown away: the one kept
before **Take KyprX off this desk…**, and the one kept before a whole folder is applied on a new
computer. The copies live in `snapshots/` inside the KyprX folder, one folder each, named by when
and why; each can be read, copied elsewhere or deleted by hand.

Going back to a copy while KyprX is off the desk also puts KyprX back on it (see
[Put my setup back](#put-my-setup-back)).

## What KyprX needs

KyprX is built on four programs: Klassy, Better Blur DX, Geometry Change and Smart Video Wallpaper
Reborn. This box is on the tab only while one of them is not right, and then it has a line for each
one that is not: the program's name, which links to its page, the version installed, and one of:

- **not installed**: without it KyprX has none of what it does;
- **installed, not running**: the program is there but the desktop is not using it. For Klassy
  and Better Blur DX this is what happens after a Plasma update, until the program is built again
  for the new Plasma;
- **too old**: Smart Video Wallpaper Reborn older than 2.15.0.

Under each line, an orange line says what is wrong and gives the command that puts it right on this
computer, which you can select and copy. **Check again** looks again, after you have installed or
updated one; the line at the bottom of the window says what it found, and once every one is
installed and running the box goes. KyprX also looks again every time the window opens. When KyprX
cannot find out what is installed at all, the box says **KyprX could not find out what is installed
here.**

The tiling is not among the four: it is KyprX's own, and when it is not running, the band at the
top of the [Tiling](tiling.md#when-tiling-is-switched-off) tab and the **Problems** box below say
why. While anything here is not right, a band across the top of the window names it, on every tab
(see [Something KyprX needs is missing](README.md#something-kyprx-needs-is-missing)), and its
**What to do** opens this tab. All four, right or not, are in [About KyprX](#about-kyprx).

## Problems

What KyprX found wrong on this computer, one line each. The box is on the tab only while there is
something in it. Hold the pointer over a line for the details. The box is checked again whenever
something changes while the tab is open.

| The line says | In short |
|---|---|
| **KyprX cannot see your windows: its part of the compositor is not installed.** | KyprX's script inside the window manager is missing, so nothing on the Windows tab is real. Shown first |
| **KyprX cannot see your windows: its part of the compositor is switched off.** | the same, with the script installed but switched off. Shown first |
| **Part of KyprX starts only at the next login: log out and back in.** | the compositor still runs the part of KyprX it loaded before an update, or none has asked for the tiling since the background service started. The details say what waits until then: the desktop tiling as it did, with what is new on the Tiling tab waiting, or nothing tiled at all; and the keys that do nothing yet, its tiling's among them, by name. Logging out and back in loads the part installed |
| *N* **window rule(s) are outside the active list.** | rules in the file that the desktop does not use |
| *N* **window rule(s) could take KyprX's naming.** | rules that force a title bar without KyprX's name; see **Tidy up rule names** below |
| **Every window without a setting of its own is drawn with its title bar hidden, by a group the decoration's own settings left behind.** | see **Give those windows their title bars back** below |

What each line means, and what to do about it, is in
[What the Problems box says](../troubleshooting.md#what-the-problems-box-says).

### Tidy up rule names

**Tidy up rule names** puts `KyprX: ` in front of the name of every window rule that forces a title
bar and does not carry that name yet. A name the desktop made up by itself, such as **Window
settings for** *application*, or no name at all, is replaced by the window class instead. Nothing
else in any rule changes, and no copy of the desk is kept. The line at the bottom says *N*
**rule(s) renamed.** or **Nothing to rename.**

KyprX treats a rule with its name as its own: it can take the rule back when a window's title bar
is turned on again, **Take KyprX off this desk…** takes KyprX's settings out of it, and going back
to a copy restores it.

The button is in the box only while the line it answers is: with nothing to rename, it is not
shown.

### Give those windows their title bars back

This button is in the Problems box only while the last line of the table above is shown.
The window decoration's own settings can leave behind a group that the decoration reads as a
setting for every window with no setting of its own, and when that group hides the title bar,
every such window loses it. KyprX removes the group by itself, but not while it is off the desk, and
it cannot during a dry run or when the write fails; that is when the line and the button appear.

The button asks **Give those windows their title bars back?** first, with **No** already selected.
It keeps a copy of the desk, removes the group, and the line at the bottom says **Done. Go back to a
copy… undoes it.**, or why it could not.
Klassy has the details of the group.

## The bottom of the tab

Two rows. The first is KyprX's version, with **About KyprX…** and **Look for a new version**. The
second holds the changes that write a great deal at once: **Go back to a copy…** on the left (see
[Go back to a copy](#go-back-to-a-copy)), then **Restore KyprX's defaults…**, **Take KyprX off this
desk…** and **Remove KyprX from this computer…**.

### KyprX's version

The greyed line on the left says which version of KyprX this window runs.

### About KyprX

**About KyprX…** opens a window titled **About KyprX**, which holds what is read rather than set:

- KyprX's version;
- **What KyprX is built on**: the four programs, one line each, right or not, in the words of
  [What KyprX needs](#what-kyprx-needs): the name, which opens the program's page, the version
  installed and how it stands, with what to do under one that is not right;
- **Credits**: the programs KyprX works with and the colour palettes its presets come from, one
  line each: the name, which opens the project's home page in the browser, what it is in KyprX, who
  made it, and its licence. Under them, a line saying the tiling is KyprX's own, with ideas from
  KZones and Hyprland and none of their code, then KyprX's own licence and a link to `CREDITS.md`,
  which opens in whatever opens a text file. [CREDITS.md](../../CREDITS.md) is the whole record.

**Close** closes it.

### Look for a new version

**Look for a new version**, beside the version line, asks which version is the newest: KyprX's
public repository, or, for a clone of the repository, the branch it follows. It is the one door
to a new version: KyprX never looks by itself, the question is asked only when the button is
pressed, and the answer comes on the line at the bottom — **KyprX <version> is the newest
version.**, or **Could not find out whether there is a new version:** with the reason. The button
is greyed while it waits.

A newer version — or, for a clone of the repository, new changes on the branch it follows — is
answered with a dialog, which takes one of four shapes:

- **Update now** and **Not now**, for an install made with `install.sh` that can update itself
  ([Updating](install.md#updating)). **Update now** installs the new version over this one and
  restarts the background service: a KyprX window opened with its key closes then, so open it
  again. KyprX's part inside the compositor is the new version from the next login; until then it
  tiles as it did.
- the command to copy, for a package: your system's package manager updates KyprX, and KyprX does
  not run it for you, because the command asks for the administrator's password. What has to
  follow the command is said with it, such as the restart a system that updates as a whole needs.
- the command to copy, for an install made with `install.sh` while this window is on a dry run:
  an update writes, and a dry run updates nothing.
- **Close** alone, for an install made with `install.sh` that cannot update itself, with the
  reason: a clone with changes of its own is not updated over them, and a release whose target
  folder is already there says so.

When an update started with **Update now** does not go through, the window says **The update did
not go through**, with the last of what the update said and the command that shows every step. The
whole of what it said is in the journal of the update's own service
([After updating KyprX](../troubleshooting.md#after-updating-kyprx)).

Neither the question nor **Update now** asks for a password. A clone whose remote wants one says
that its remote could not be asked: run `./install.sh --update` in a terminal, where git asks. A
credential helper you set up for git is git's own, and asks the way it always does.

### Take KyprX off this desk

**Take KyprX off this desk…** puts the desktop back on KDE's own defaults and stops KyprX. It asks
**Take KyprX off this desk?** first, with exactly what would change listed under the question, and
**Take KyprX off** to go ahead. The line at the bottom says **Keeping a copy of the desk, then taking
KyprX off… the desktop's own tools take a few seconds**, then **KyprX is off this desk. Put my setup
back, at the top of the window, undoes it.**

**What it leaves is plain KDE**, each program on its own defaults:

- every setting KyprX has a value for is deleted, so the decoration, the window border, focus, the
  blur, the window animation and the tiling each go back to the value their own program uses when
  nothing is written. For the tiling that is no tiling at all: its switch, deleted, reads as off;
- from every window rule named `KyprX: `, the forced title bar and the opacity are taken out. A rule
  left doing nothing is deleted; a rule that still holds something of yours, such as an activity or
  a desktop, stays, and keeps its name;
- a window's own per-window decoration setting is deleted, unless it holds something of somebody
  else's; then it stays, with its title bar shown, no border override and no preset. KyprX's preset
  without the outline goes too, unless something still points at it;
- the windows KyprX looks after are taken out of the lists of floating, not animated and not blurred
  windows;
- Better Blur DX and the window animation are switched off;
- KDE's own Breeze global theme goes on, the dark one or the light one after the mode in force,
  with no colour of your own. Anything of yours that the global theme would delete as it goes on,
  such as an icon theme you chose yourself, is written back.

**Then KyprX stops.** **Adjust new windows** is unticked, so new windows are left alone. The KyprX
folder is brought up to date one last time and is then neither written nor applied, so it keeps
your setup. The leftover decoration group is no longer removed by itself. An orange band across the
top of the window says KyprX is off the desk ([The KyprX window](README.md#kyprx-is-off-this-desk)).

**What it does not touch:** your shortcuts, your wallpaper, your profiles, your zone layouts and
arrangements, the colours of the decoration's buttons, window rules not named `KyprX: `, the two
rules that keep KyprX's cheatsheet and wallpaper picker floating, and the desktops KyprX made for
windows that found their arrangement full: they stay, with whatever is on them, and one left empty
goes the next time KyprX's tiling runs
([A window that opens with every zone taken](tiling.md#a-window-that-opens-with-every-zone-taken)).
Three things it does not undo, because they are not KyprX's to undo: KDE's own blur effect, if
something else switched it off (KyprX never switches it on or off), a key taken from another action
with **Use it here** on the [Shortcuts](shortcuts.md) tab, and a key KyprX took for one of the four
actions of its own it takes keys back for when it starts
([When another action has the same key](shortcuts.md#when-another-action-has-the-same-key)).

Plain KDE is each program's own defaults, not the desktop as it was before KyprX: nothing recorded
that.

The copy of the desk kept first is never thrown away. If taking KyprX off fails part-way, the line
at the bottom says so, and **Put my setup back** or **Go back to a copy…** puts the desk back.
Pressed while KyprX is already off, the button answers **KyprX is already off this desk**.

### Put my setup back

**Put my setup back**, in the band across the top of the window, first keeps a copy of the desk as
it is, then puts back the copy kept before KyprX was taken off, exactly: the decoration, every
rule, the colours, the global theme, and whether new windows were being adjusted. Then the folder
is written and applied again, and whatever arrived in it meanwhile is applied like any other
arrival. Its question and messages are on
[The KyprX window](README.md#kyprx-is-off-this-desk).

**Two other buttons also put KyprX back on the desk:** **Restore KyprX's defaults…**, and **Go back
to a copy…** with any other copy. Each keeps the KyprX folder, as it stood, inside the copy of the
desk it keeps first, because from then on KyprX writes the desk into the folder again. After
**Restore KyprX's defaults…**, **Adjust new windows** is ticked; after going back to a copy, it is
as the copy had it.

### Restore KyprX's defaults

**Restore KyprX's defaults…** writes every value KyprX has an opinion about. The question **Restore
KyprX's defaults?** lists what it writes and what it leaves alone, and under it exactly what would
change: every setting that would move, file by file, from what to what, in the words a dry run
uses, and what the desktop would then do, such as stop the screen, have the tiling read its
settings again or apply a colour scheme. When nothing would change, the list says **Nothing would
change: everything already reads this way.** **Restore the defaults** goes ahead.

**What it writes.** Each row's values are on the page linked beside it.

| What | KyprX's values |
|---|---|
| The title bar: the decoration's icons and buttons, an opaque bar, the title and the spacing, and no colour of their own on the close, maximise and minimise buttons | [Appearance: Title bar](appearance.md#title-bar) |
| The window frame: corner radius, the outline, and the frame settings no control shows | [Appearance: Window](appearance.md#window) |
| **Opacity**, which reaches every see-through window that has no number of its own | [Appearance: Window](appearance.md#window) |
| The blur and the window animation, each switched on | [Effects](effects.md) |
| Focus, everything under **Automatic tiling**, and the gaps on the Tiling tab, with tiling switched on | [Tiling](tiling.md) |
| What a new window gets | [Windows](windows.md#what-a-new-window-gets) |
| KyprX's three settings about itself: **Adjust new windows**, **Colour from the wallpaper** and **Say when something did not work** | [The KyprX window](README.md#above-the-tabs), and [Notifications](#notifications) above |
| The wallpaper picker's layout, **Show the names and the keys in the strip** and **Set for all screens**, both unticked, its video folder, which is emptied so that the Wallpaper tab works one out again, and **Also list KDE's own wallpapers**, which is ticked | [Wallpaper](wallpaper.md) |
| The desktop's colours | [Appearance: Colours](appearance.md#colours) |

A setting that already reads KyprX's value is not written, so pressing it twice writes nothing the
second time. When **Adjust new windows** was unticked, every window that waited meanwhile is given
the defaults as well, and the list says how many.

**What it leaves alone:** the windows you set by hand on the Windows tab, including each window's
own opacity; the lists of floating, not animated and never-tiled windows; the zone layouts and
arrangements on the Tiling tab; your shortcuts, and which key the cheatsheet shows; your wallpaper,
and which screen's wallpaper the colour comes from; your profiles; the colours of the decoration's
other eight buttons.

**How it writes.** A copy of the desk is kept first, and without one nothing is written. Then the
decoration, the window manager and the windows' opacity go in together, so the screen stops once
for them; then KyprX's own settings; then the colours last, which stop the screen again while the
desktop's colour tools work. The line at the bottom says **Keeping a copy of the desk, then putting
KyprX's defaults back… the desktop's own tools take a second or two**, then one of:

- **KyprX's defaults are back. Go back to a copy… undoes it.**
- **Only part of it went in:** followed by what did not, and **Go back to a copy… undoes the
  rest.** The one part that can fail on its own is the colours.
- **That did not go through:** followed by the reason.

Pressed while KyprX is off the desk, it also puts KyprX back on (see
[Put my setup back](#put-my-setup-back)).

## Good to know

- **Copy the whole folder, `kyprx.json` included.** On a computer where KyprX remembers no
  agreement with the folder, a folder without `kyprx.json` is not applied: the desk is written
  over it.
- **Opening the folder can apply something.** **Open the folder** runs a pass at once, so a change
  that arrived in the folder and has stood still for three seconds is applied before the file
  manager opens.
- **The folder follows your edits, not the other way round.** While a file in it has a mistake,
  KyprX writes nothing into the folder, so the file you are fixing is never written over.
- **Removing the leftover decoration group keeps a copy each time**, even when KyprX does it by
  itself, so such copies can appear in the list without your pressing anything.
- **Only one thing is remembered about KyprX being off**: which copy to put back. Going back to a
  copy that is not that one, or restoring the defaults, puts KyprX back on the desk without it.

### Remove KyprX from this computer

**Remove KyprX from this computer…** is where removing KyprX starts, however it was installed. A
package manager removes the files it installed and nothing in your settings, so KyprX first takes
back what it keeps and what only it used, and then gives you the command that removes its files.

It asks **Remove KyprX from this computer?** with two questions, and chooses neither answer for
you; **Remove KyprX** can be pressed only when both are answered:

- **Your desktop**: put KDE back as KDE has it, which is what
  [Take KyprX off this desk](#take-kyprx-off-this-desk) does, copy of the desk included; or leave
  it looking as it does now. Left as it is, windows keep the look KyprX gave them, and the desktop
  goes on behaving as KyprX set it -- focus follows the mouse, among the rest -- while KyprX's
  panel style and colour presets go when its files are removed;
- **Your KyprX folder**: keep it, with your setup and the copies of the desk, so that installing
  KyprX again, here or on another computer, applies it; or remove it, with the copies in it. A
  folder that is a git repository is never removed by KyprX: it says so, and leaves it to you.

Under the questions, once both are answered, is exactly what would change. Whatever the answers,
KyprX then switches off and unloads its part inside the compositor, and with it its tiling, whose
settings go, the zone layouts and arrangements with them; deletes the two rules that place its
cheatsheet and wallpaper picker; takes its keys out of the desktop's shortcut list; removes its
own colour scheme unless the desktop is wearing it; and removes what it remembers about this
computer, its caches, and the two files the desktop keeps in its name: the folders KDE's file
dialog last opened for it, and the panel's cache of KyprX's style, unless the panel goes on
wearing it. After that, KyprX tiles no window, and the desktops it made for windows stay as
ordinary desktops. The keys KyprX took from other actions -- Meta+R from Spectacle's **Start/Stop
Region Recording**, Meta+T from KWin's **Toggle Tiles Editor** -- stay without one: System
Settings, under **Shortcuts**, gives each its key back.

Klassy, Better Blur DX, Geometry Change and Smart Video Wallpaper Reborn stay: they are programs of
their own. When you remove the KyprX package, your package manager also removes the ones it
installed only for KyprX, and asks first; the ones you installed yourself stay. On Arch, installed
from the release's PKGBUILD, they may have come in by a command of your own: [Removing, on
Arch](install.md#arch-installed-from-the-releases-pkgbuild) has the command that names them.

When it is done, a message lists what was done and what was kept, and gives the command that
removes KyprX's files, with **Copy the command**: `sudo dnf remove kyprx` on Fedora,
`rpm-ostree uninstall kyprx` and a restart on a Fedora system that updates as a whole,
`sudo pacman -Rs kyprx` on Arch, or `install.sh --uninstall` from the folder KyprX was installed
from, which removes nothing until this button has run. KyprX does not run it. Closing the message
closes the window. Opening KyprX again before the command has run brings it back on, with its look,
as on a new install.

