# Wallpaper

The Wallpaper tab decides what the wallpaper picker offers and what it looks like. The picker is a
window of its own, opened with **Meta+R**, where you choose the wallpaper itself. It is described
below, under [The wallpaper picker](#the-wallpaper-picker).

Everything on the tab is written the moment you change it (see
[The KyprX window](README.md#changes-apply-by-themselves)).

**Everything here is about the activity you are in.** In Plasma each activity has its own
wallpaper. The tab shows the activity you are in, and a change reaches every screen of that
activity and no other activity. Switch to another activity and the tab follows it.

From top to bottom the tab has an orange warning band (only when there is something to say), the
**Picker** section, the **Layout** section, and one line of summary.

## The warning at the top

An orange band across the top of the tab. It appears only when something is wrong, and it can
carry more than one of these lines:

- **Smart Video Wallpaper Reborn is not installed, so the picker can only offer pictures.** Video
  wallpapers need that plugin, and KyprX does not install it. Where it comes from is on
  Smart Video Wallpaper Reborn.
- **the video plugin is set to change the wallpaper by itself, so a video chosen here will not
  stay. Its own settings are where that is turned off; this app does not touch it.** The video
  plugin's own **Change Wallpaper** setting, in *Desktop and Wallpaper*, is not **Never** on a
  screen of this activity. KyprX only reads that setting. Set it to **Never** there and the line
  goes away.
- **Smart Video Wallpaper Reborn** *version* **is installed. 2.15.0 fixes how it pauses and plays
  again on this Plasma; it comes from Get New Plugins in Desktop and Wallpaper, or from the
  plugin's own page.** The installed plugin is older than 2.15.0. Video wallpapers still play. What
  that release fixes is on
  Smart Video Wallpaper Reborn.
- **the video folder is not there right now:** *folder*. **Videos** is ticked, and the
  **Video folder** does not exist at the moment, for example because it is on a drive that is not
  plugged in. The picker has nothing to list until it is back.
- **the Smart Video Wallpaper Reborn plugin is not installed, so there is nothing to play a video
  with**. The activity you are in is set to video wallpapers, but the plugin is not on this
  computer.
- A line that starts **the desktop shell did not answer** or **the desktop shell refused**, or
  that says **the activity in use has no desktop to put a wallpaper on**. KyprX could not ask the
  desktop what it is showing, so the tab cannot show it either.
  [Troubleshooting](../troubleshooting.md) says where to look next.

The missing plugin and the old plugin are also reported in the Problems box on the
[Settings](settings.md) tab.

## Picker

The section's **i** says: *What the wallpaper key offers you when you press it. A wallpaper you
choose reaches every screen of the activity you are in, and no other.*

**Pictures — the wallpapers KDE knows about** and **Videos — played by Smart Video Wallpaper
Reborn** choose which kind of wallpaper the activity you are in shows, and so what the picker
lists.

This is not a setting KyprX keeps. It is the desktop's own **Wallpaper type**, the one in
*Desktop and Wallpaper* (right-click the desktop). Ticking **Videos** here switches every screen of
the activity you are in to video wallpapers, and changing **Wallpaper type** there moves the tick
here. Each kind keeps its own settings, so switching back to one brings back the wallpaper it
showed last. If the desktop does not take the change, the tick goes back to what the desktop shows.

**Videos** is greyed, with the tooltip *Smart Video Wallpaper Reborn is not installed.*, when that
plugin is missing. There is no KyprX default here: the tab always shows what the desktop has.

**Pictures folder** is the folder the picker lists pictures from, in addition to the wallpapers KDE
ships. Type a folder and press Enter, or press **Choose…**, which opens a folder chooser titled
*Where the pictures are*. The field and the button are greyed unless **Pictures** is ticked; the
folder is kept either way. While no folder is set, KyprX looks in your Pictures folder
(`XDG_PICTURES_DIR` in `~/.config/user-dirs.dirs`, or `~/Pictures`). Empty the field to go back to
the default.

**Video folder** is the folder the picker lists videos from. Only the videos directly in it are
listed, not the ones in folders inside it. Type a folder and press Enter, or press **Choose…**,
which opens a folder chooser titled *Where the videos are*. The field and the button are greyed
unless **Videos** is ticked; the folder is kept either way.

While no folder is set, KyprX works one out every time it needs one, and shows it in the field. It
takes the first of these that exists:

1. the folder that holds the most videos from the video plugin's own list;
2. your Videos folder as the desktop records it, in `~/.config/user-dirs.dirs`;
3. `~/Videos`.

Empty the field to go back to a worked-out folder. KyprX's default: empty, so the folder is worked
out.

**Pause the video** is the video plugin's own **Pause** setting, with its four choices in the
plugin's own words:

- **Maximized or full-screen windows**
- **Active window**
- **At least one window is visible**
- **Never**

It says when the plugin stops the video, to spare the computer the work of playing it. The tooltip
says what playing all the time costs. Those figures were measured — see the comment in
`gui/tab_wallpaper.py` (`PAUSE_TIP`).

The menu shows the choice in force on the activity you are in, and a new choice is written on every
screen of that activity. When nothing has ever been chosen, it shows the plugin's own default,
which KyprX reads from the plugin itself. In Smart Video Wallpaper Reborn 2.15.0 that is
**Maximized or full-screen windows**.

KyprX has no default of its own for it and never changes it by itself. It is written in two cases
only: when you pick another choice here, and when a copy of the desk or the KyprX folder that
carries a different choice is applied (both are on [Settings](settings.md)). Opening the tab
writes nothing.

The menu is greyed unless **Videos** is ticked. A paused video still shows through see-through
windows, so it can look like a still picture: see
[A video wallpaper looks stuck](../troubleshooting.md#a-video-wallpaper-looks-stuck).

## Layout

The section's **i** says: *What the wallpaper picker looks like when it opens. Both show the same
wallpapers and answer the same keys.*

**Pages — over the desktop, the chosen one in the middle and the rest behind it** and
**Strip — a column of thumbnails beside one big picture, in a panel** choose which layout the
picker opens in. Each is described below, under [Pages](#pages) and [Strip](#strip). KyprX's
default: **Pages**.

## The line at the bottom

The last line of the tab reads, for example, **24 to choose from · 2 screens · opens with
Meta+R**. It says:

- how many wallpapers the picker would list right now;
- how many screens the activity you are in has, only when there is more than one;
- which key opens the picker, as it is set on the [Shortcuts](shortcuts.md) tab. **no key yet**
  means the picker has no key there. **no key yet — install.sh has not reloaded the compositor
  script** means the desktop does not know the picker's shortcut at all; see
  [A shortcut does nothing](../troubleshooting.md#a-shortcut-does-nothing).

## The wallpaper picker

### Opening it

- **Meta+R**. That is the key KyprX starts with; the [Shortcuts](shortcuts.md) tab can change it.
- **Pick a wallpaper**, when you right-click KyprX in the application menu.
- `kyprx --wallpaper`, from a terminal.

The picker opens in the middle of the screen with the wallpaper that is on screen now selected, or
the first one in the list when that one is not in it. Pressing the key again while the picker is
open closes it and opens a new one.

**Moving through the list changes nothing on the desktop.** Nothing happens until you set a
wallpaper, so **Esc** leaves the desktop exactly as it was.

The picker closes by itself as soon as another window takes the focus.

### What it lists

What the picker lists follows **Pictures** and **Videos** on the tab, which is the kind of
wallpaper the activity you are in is showing.

**Pictures** lists what is in the `wallpapers` folder of each of the desktop's data folders:
`~/.local/share/wallpapers` first, then the system's, usually `/usr/local/share/wallpapers` and
`/usr/share/wallpapers`. In each one it takes:

- **wallpaper packages**: a folder with a `metadata.json` or `metadata.desktop` file and its
  pictures in `contents/images` (or `contents/images_dark`). A package is listed under its own
  name, in your session's language when the package has a name in it;
- **picture files** lying loose in the folder, each under its file name without the ending;
- **packages one folder further down**, for collections that group their packages in a folder.

They are listed in alphabetical order. The picture file types are `.png`, `.jpg`, `.jpeg`,
`.webp`, `.avif`, `.jxl`, `.heic`, `.heif`, `.bmp`, `.svg`, `.svgz`, `.tif` and `.tiff`, in upper
or lower case.

**Videos** lists the video files directly in the **Video folder**, each under its file name without
the ending, sorted by file name. The video file types are `.mp4`, `.mkv`, `.webm`, `.mov`, `.avi`,
`.m4v`, `.wmv` and `.flv`, in upper or lower case.

A file whose picture cannot be made on this computer is still listed and can still be set.

### Pages

The default layout. There is no panel: the picker is the wallpapers themselves, laid over the
desktop.

- The selected wallpaper sits large in the middle of the screen, as a page with the shape of your
  screen. Its picture is cropped to that shape.
- Behind it, up to five wallpapers on each side lean away like the pages of an open book: the ones
  before it in the list on the left, the ones after it on the right. The further back a page is,
  the darker it is drawn, and each one behind has a thin dark line round it.
- The page in front has a border drawn like the outline of the focused window, in the same colour
  and thickness: the **Outline** and **Focused window** settings on [Appearance](appearance.md).
  With **Focused window** set to **None**, or **Outline** at 0, it has no border.
- There is no text, except one line under the page in front when there is something to say (see
  [Setting a wallpaper](#setting-a-wallpaper)).
- The pointer is a hand over a page and an arrow anywhere else.

### Strip

A panel in the middle of the screen, in your colour scheme's window colour, with the window
**Corner radius** and outline from [Appearance](appearance.md).

- On the left, a strip of narrow cards, one per wallpaper, side by side. It scrolls sideways to keep
  the selected card in view, and the selected card has a border in the outline's colour.
- On the right, the selected wallpaper as one big picture, shown whole, with its name in bold under
  it.
- Under the name, a line such as **24 image(s) — arrows to move, Enter to set, Esc to leave**
  (**video(s)** for videos). A line about a problem, when there is one, goes above it.

### Keys and clicks

| Key or click | What it does |
|---|---|
| **Right** or **Down** arrow | Selects the next wallpaper. |
| **Left** or **Up** arrow | Selects the previous one. |
| **Home** / **End** | Selects the first / the last. |
| **Page Down** / **Page Up** | Moves five forward / back in Pages, and as many cards as the strip shows at once in Strip. |
| **Enter** (on the main keyboard or the number pad) or **Space** | Sets the selected wallpaper. |
| **Esc** | Closes the picker without changing anything. |
| Pages: a click on a page behind | Brings that page to the front. It does not set it. |
| Pages: a click on the page in front | Sets it. |
| Pages: a click anywhere else | Closes the picker without changing anything. |
| Strip: a click on a card | Sets that wallpaper at once. |

In Pages a click on a page behind only brings it forward, because those pages are thin slivers and
a click a little off would otherwise set a wallpaper you never looked at. In Strip every card is
whole, so a click sets it.

### Setting a wallpaper

**A wallpaper reaches every screen of the activity you are in, and no other activity.** Every
screen gets the same one. Other activities keep theirs.

- **A picture** is set as the desktop's picture wallpaper. A package is set as a whole, not as one
  picture from it, so the desktop still picks the size and the light or dark version itself.
- **A video** is played by Smart Video Wallpaper Reborn, from the beginning. In the plugin's own
  list of videos, the one you chose is ticked and every other one is unticked. Nothing is removed
  from that list, and each video keeps its own settings in it; a video not yet in the list is added
  to it. The plugin switches to a video, and plays it over and over, only when it is the one video
  ticked.

While the wallpaper is being set, the picker shows the word **setting** followed by the
wallpaper's name. When the desktop takes it, the picker closes. When it does not, the picker stays
open and shows **could not set**, the name, and **— see the daemon's log**
([Troubleshooting](../troubleshooting.md) says where the log is).

Other lines the picker can show, under the page in front or in the Strip's panel:

- **nothing to choose from**: the list is empty, for example a video folder with no videos in it;
- **the video plugin is set to change the wallpaper on its own, so this one will not stay**: the
  same thing the tab's warning says, see [The warning at the top](#the-warning-at-the-top);
- the folder and desktop problems listed under [The warning at the top](#the-warning-at-the-top),
  in the same words;
- **dry run: a wallpaper chosen here is written down, not put up**, while KyprX runs in dry run
  (see
  [Troubleshooting](../troubleshooting.md#seeing-what-a-change-would-do-without-doing-it)).
  Choosing a wallpaper then closes the picker as usual, and the wallpaper stays as it was.

### Colour from the wallpaper

When **Colour from the wallpaper**, above the tabs of the settings window, is ticked (see
[The KyprX window](README.md#colour-from-the-wallpaper)), every wallpaper set from the picker hands
its colour to the desktop. What that colour does is on
[Appearance](appearance.md#colours).

- KyprX starts working the colour out as soon as the selection stops on a wallpaper, so it is
  usually ready by the time you set it.
- The picker closes at once, and the new wallpaper appears a moment later, together with the new
  colours. How long that takes was measured — see the comment in `daemon/kyprd_wallpaper.py`
  (`WallpaperPart.set_wallpaper`). The screen can stop briefly while the colours change; see
  [Troubleshooting](../troubleshooting.md#the-screen-stops-for-a-moment-when-the-colours-change).
- Because the picker has closed by then, a failure is not shown in it. It goes to the log and, when
  notifications are on ([Settings](settings.md)), to a desktop notification: **The wallpaper could
  not be changed.** or **The wallpaper's colour could not be applied.**

With **Colour from the wallpaper** unticked, the wallpaper changes straight away and the colours are
left alone.

### Pictures of the wallpapers

The small pictures the picker shows are made once and kept (where they are kept is on
MAP). The first time a big folder is opened they fill in
one by one, starting at the selected wallpaper and working outwards; after that they come up at
once. A file replaced by another of the same name gets a new picture.

- For a package, the picture is the largest one in it.
- For a video, it is a frame from about one second in (from the very start, for a shorter clip),
  taken with `ffmpeg`.

When a wallpaper has no picture, because `ffmpeg` is not installed or because this computer cannot
read that picture file, it is still listed and can still be set. In Strip its card shows its name,
written sideways, and the big picture reads **no preview**. In Pages it is a plain page. Without
`ffmpeg`, **Colour from the wallpaper** also has no colour to take from a video.

### Always fully opaque

The picker is always drawn fully opaque, whatever **Opacity** says on [Appearance](appearance.md),
and the blur is kept off it. It shows pictures, and a little of whatever is behind it mixed in would
change the picture you are judging.

## Good to know

- **Another kind of wallpaper.** When the activity you are in shows a kind of wallpaper that is
  neither pictures nor Smart Video Wallpaper Reborn, such as a slideshow, the tab shows **Pictures**
  ticked. Setting a picture from the picker then puts the ordinary picture wallpaper back.
- **Only those folders are looked in.** A picture kept anywhere else, in `~/Pictures` for
  example, is listed once it is copied into `~/.local/share/wallpapers`.
- **Choosing the wallpaper that is already on** changes nothing on the desktop. With
  **Colour from the wallpaper** ticked, it still hands that wallpaper's colour to the desktop, which
  is the way to take the colour of the wallpaper you already have.
- **On more than one screen**, the picker is sized for the main screen, and the wallpaper you set
  still goes on all of them.
- **Two activities, two kinds.** One activity can show a picture and another a video. The tab, the
  picker and **Pause the video** always follow the activity you are in.
