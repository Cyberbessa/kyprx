# Wallpaper

The Wallpaper tab decides what the wallpaper picker offers and what the picker looks like. The
picker itself is a window of its own, opened with **Meta+R**, described under
[The wallpaper picker](#the-wallpaper-picker).

**Everything here is about the activity you are in.** In Plasma each activity has its own
wallpaper, and each screen of an activity can have its own. The tab shows the activity you are
in; switch activity and the tab follows.

From top to bottom: an orange warning band (only when there is something to say), the **Picker**
section, the **Layout** section, and one line of summary.

## The warning at the top

An orange band across the top of the tab. It appears only when something is wrong, and it can
carry more than one of these lines:

- **Smart Video Wallpaper Reborn is not installed, so the picker can only offer pictures.** Video
  wallpapers need that plugin, and KyprX does not install it
  (Smart Video Wallpaper Reborn).
- **the screens of this activity show different kinds of wallpaper. Pictures and Videos here
  switch every one of them.** One screen shows a picture and another a video, which only
  *Desktop and Wallpaper* does. **Pictures** and **Videos** here show the kind of the screen the
  picker would open on; ticking one switches every screen of the activity to it.
- **the video plugin is set to change the wallpaper by itself, so a video chosen here will not
  stay. Its own settings are where that is turned off; this app does not touch it.** The video
  plugin's own **Change Wallpaper** setting, in *Desktop and Wallpaper*, is not **Never** on a
  screen of this activity. Set it to **Never** there and the line goes away; KyprX only reads
  that setting.
- **Smart Video Wallpaper Reborn** *version* **is installed. 2.15.0 fixes how it pauses and plays
  again on this Plasma; it comes from Get New Plugins in Desktop and Wallpaper, or from the
  plugin's own page.** The installed plugin is older than 2.15.0; video wallpapers still play.
  What that release fixes is on the
  plugin's page.
- **the video folder is not there right now:** *folder*. The folder is on a drive that is not
  plugged in, say. The picker has nothing to list until it is back.
- **the pictures folder** *folder* **has no wallpaper in it, so KDE's own wallpapers are
  listed**, or **the pictures folder is not there right now: …, so KDE's own wallpapers are
  listed** (or **…so the picker has nothing to list until it is back**, when **Also list KDE's
  own wallpapers** is unticked). The picker is never left empty on purpose. The same line is
  shown in the picker itself.
- **the Smart Video Wallpaper Reborn plugin is not installed, so there is nothing to play a
  video with.** The activity is set to video wallpapers, but the plugin is not on this computer.
- a line starting **the desktop shell did not answer** or **the desktop shell refused**, or
  saying **the activity
  in use has no desktop to put a wallpaper on**: KyprX could not ask the desktop what it is
  showing. [Troubleshooting](../troubleshooting.md) says where to look next.

The missing plugin and the old plugin are also reported in the Problems box on the
[Settings](settings.md) tab.

## Picker

**Pictures — the folder below, and KDE's own wallpapers** and **Videos — played by Smart Video
Wallpaper Reborn** choose which kind of wallpaper the activity shows, and so what the picker
lists. This is not a setting KyprX keeps: it is the desktop's own **Wallpaper type**, the one in
*Desktop and Wallpaper* (right-click the desktop). Ticking **Videos** here switches every screen
of the activity to videos, and changing **Wallpaper type** there moves the tick here. Each kind
keeps its own settings, so switching back brings back the wallpaper it showed last. If the
desktop does not take the change, the tick goes back to what the desktop shows.

**Videos** is greyed, with the tooltip *Smart Video Wallpaper Reborn is not installed.*, when
that plugin is missing. There is no KyprX default here: the tab always shows what the desktop
has.

**Pictures folder** is the folder the picker lists pictures from. Type a folder and press Enter,
or press **Choose…**. Greyed unless **Pictures** is ticked; the folder is kept either way. While
no folder is set, KyprX looks in your Pictures folder (`XDG_PICTURES_DIR` in
`~/.config/user-dirs.dirs`, or `~/Pictures`). Empty the field to go back to that.

**Also list KDE's own wallpapers**: while ticked, the picker lists beside your pictures every
wallpaper the desktop itself ships, from your own `~/.local/share/wallpapers` and the system's
`wallpapers` and `backgrounds` folders (the tooltip names them). Unticked, the list is the
pictures folder's alone -- but the box is no promise of an empty picker: a pictures folder with
no wallpaper in it gets KDE's own listed anyway, with the note above saying why. Greyed unless
**Pictures** is ticked. KyprX's default: ticked. A picture kept anywhere outside these folders is
listed once it is copied into one of them.

**Video folder** is the folder the picker lists videos from; only the videos directly in it, not
the ones in folders inside it. Greyed unless **Videos** is ticked; the folder is kept either way.
While no folder is set, KyprX works one out and shows it: the folder holding the most videos from
the video plugin's own list, else your Videos folder as the desktop records it, else `~/Videos`.
Empty the field to go back to a worked-out folder. KyprX's default: empty.

**Pause the video** is the video plugin's own **Pause** setting, in its four choices: **Maximized
or full-screen windows**, **Active window**, **At least one window is visible**, **Never**. It
says when the plugin stops the video to spare the computer the work of playing it (what playing
all the time costs was measured; see `PAUSE_TIP` in `gui/tab_wallpaper.py`). The menu shows the
choice in force on the activity you are in, and a new choice is written on every screen of it.
When nothing has ever been chosen it shows the plugin's own default, read from the plugin itself:
in 2.15.0, **Maximized or full-screen windows**. KyprX has no default of its own and never
changes it by itself: it is written only when you pick another choice here, or when a copy of the
desk or the KyprX folder carrying a different choice is applied. Opening the tab writes nothing.
The menu is greyed unless **Videos** is ticked.

A paused video still shows through see-through windows, so it can look like a still picture:
[A video wallpaper looks stuck](../troubleshooting.md#a-video-wallpaper-looks-stuck).

**Set for all screens** is there only with more than one screen. Unticked, a wallpaper chosen in
the picker goes on the screen the picker opened on. Ticked, it goes on every screen of the
activity. These are the words and the choice of KDE's own Wallpaper page. KyprX's default:
unticked. **Pictures**, **Videos** and **Pause the video** are not one screen's: each reaches
every screen of the activity, whatever this box says.

## Layout

**Pages — over the desktop, the chosen one in the middle and the rest behind it** and
**Strip — a column of thumbnails beside one big picture, in a panel** choose which layout the
picker opens in, described under [Pages](#pages) and [Strip](#strip). KyprX's default: **Pages**.

**Show the names and the keys in the strip**: ticked, the strip writes the selected wallpaper's
name under the big picture, a line with the count and the keys, and a card's name under the
pointer. Unticked, it shows the pictures and nothing else. Greyed while **Pages** is chosen:
Pages writes nothing but a problem either way. KyprX's default: unticked. A choice saved by an
earlier KyprX as **Strip with names** opens the strip with this box ticked.

## The line at the bottom

The last line reads, for example, **24 to choose from · 2 screens · opens with Meta+R**: how many
wallpapers the picker would list now; how many screens the computer has, only when more than
one; and which key opens the picker, as set on the [Shortcuts](shortcuts.md) tab. **no key yet**
means the picker has no key there; **no key yet — install.sh has not reloaded the compositor
script** means the desktop does not know the picker's shortcut at all
([A shortcut does nothing](../troubleshooting.md#a-shortcut-does-nothing)).

## The wallpaper picker

### Opening it

- **Meta+R**. That is the key KyprX starts with; the [Shortcuts](shortcuts.md) tab can change it.
- **Pick a wallpaper**, when you right-click KyprX in the application menu.
- `kyprx --wallpaper`, from a terminal.

The picker opens in the middle of the screen you are working on and is sized for that screen. The
wallpaper that screen shows is selected, or the first in the list. Pressing the key again while
it is open closes it and opens a new one, on the screen you are on then.

Moving through the list changes nothing on the desktop: nothing happens until you set a
wallpaper, so **Esc** leaves the desktop exactly as it was. The picker closes by itself as soon
as another window takes the focus.

### What it lists

The picker lists the kind of wallpaper the activity is showing; when its screens show different
kinds, it lists the kind of the screen it opens on.

**Pictures** lists what is in the pictures folder, and while **Also list KDE's own wallpapers**
is ticked what is in the `wallpapers` folder of each of the desktop's data folders
(`~/.local/share/wallpapers` first, then the system's, usually `/usr/local/share/wallpapers` and
`/usr/share/wallpapers`) and the `backgrounds` folders beside them, where distributions ship
theirs. In each folder it takes:

- **wallpaper packages**: a folder with a `metadata.json` or `metadata.desktop` file and its
  pictures in `contents/images` (or `contents/images_dark`), listed under its own name, in your
  session's language when the package has one;
- **picture files** lying loose in the folder, each under its file name without the ending;
- **packages one folder further down**, for collections that group theirs in a folder;
- in the system's `backgrounds` folders only, **picture files one folder further down**.

Everything is listed in alphabetical order. The picture types are `.png`, `.jpg`, `.jpeg`,
`.webp`, `.avif`, `.jxl`, `.heic`, `.heif`, `.bmp`, `.svg`, `.svgz`, `.tif` and `.tiff`, in upper
or lower case.

**Videos** lists the video files directly in the **Video folder**, each under its file name
without the ending, sorted by file name. The video types are `.mp4`, `.mkv`, `.webm`, `.mov`,
`.avi`, `.m4v`, `.wmv` and `.flv`, in upper or lower case.

A file whose picture cannot be made on this computer is still listed and can still be set. When
the activity shows a kind of wallpaper that is neither pictures nor this video plugin, such as a
slideshow, the tab shows **Pictures** ticked, and setting a picture puts the ordinary picture
wallpaper back.

### Pages

There is no panel: the picker is the wallpapers themselves, laid over the desktop.

- The selected wallpaper sits large in the middle of the screen, as a page with the shape of your
  screen, its picture cropped to that shape.
- Behind it, up to five wallpapers on each side lean away like the pages of an open book: the
  ones before it in the list on the left, the ones after it on the right. The further back, the
  darker, each with a thin dark line round it.
- The page in front has a border drawn like the outline of the focused window, in the same colour
  and thickness: the **Outline** and **Focused window** settings on [Appearance](appearance.md).
  With **Focused window** on **None**, or **Outline** at 0, it has no border.
- There is no text, except one line under the page in front when there is something to say. The
  pointer is a hand over a page and an arrow anywhere else.

### Strip

A panel in the middle of the screen, in your colour scheme's window colour, with the window
**Corner radius** and outline from [Appearance](appearance.md).

- On the left, a strip of narrow cards, one per wallpaper, scrolling sideways to keep the selected
  card in view; the selected card has a border in the outline's colour.
- On the right, the selected wallpaper as one big picture, shown whole.
- With **Show the names and the keys in the strip** unticked, nothing else: a line appears under
  the picture only when there is something wrong to say. With it ticked, the strip also writes
  the name of the selected wallpaper in bold, a line such as **24 image(s) — arrows to move,
  Enter to set, Esc to leave** (**video(s)** for videos), and a card's name under the pointer.

### Keys and clicks

| Key or click | What it does |
|---|---|
| **Right** or **Down** arrow | Selects the next wallpaper. |
| **Left** or **Up** arrow | Selects the previous one. |
| **Home** / **End** | Selects the first / the last. |
| **Page Down** / **Page Up** | Moves five forward / back in Pages, and as many cards as the strip shows at once in the strip. |
| **Enter** (main keyboard or number pad) or **Space** | Sets the selected wallpaper. |
| **Esc** | Closes the picker without changing anything. |
| Pages: a click on a page behind | Brings that page to the front. It does not set it: those pages are thin slivers, and a click a little off would otherwise set a wallpaper you never looked at. |
| Pages: a click on the page in front | Sets it. |
| Pages: a click anywhere else | Closes the picker without changing anything. |
| Strip: a click on a card | Sets that wallpaper at once. |

### Setting a wallpaper

**A wallpaper goes on the screen the picker opened on**, and the other screens keep theirs. With
**Set for all screens** ticked on the tab, it goes on every screen of the activity. Other
activities keep theirs either way. Choosing the wallpaper that is already on changes nothing --
though with **Colour from the wallpaper** ticked, choosing it on the screen the colour comes from
still hands that colour to the desktop: the way to take the colour of the wallpaper you already
have.

- **A picture** is set as the desktop's picture wallpaper. A package is set as a whole, so the
  desktop still picks the size and the light or dark version itself.
- **A video** is played by Smart Video Wallpaper Reborn, from the beginning. In the plugin's own
  list of videos, the one you chose is ticked and every other unticked; nothing is removed from
  that list, each video keeps its own settings in it, and a video not yet in it is added. The
  plugin switches to a video, and plays it over and over, only when it is the one video ticked.

While the wallpaper is being set, the picker shows the word **setting** followed by its name. It
closes when the desktop takes it; if not, it stays open and shows **could not set**, the name,
and **— see the daemon's log**. Other lines it can show: **nothing to choose from** (an empty
list); the folder and desktop-shell problems of
[The warning at the top](#the-warning-at-the-top), in the same words; for the video plugin,
**the video plugin is set to change the wallpaper on its own, so this one will not stay**; and,
in a dry run,
**dry run: a wallpaper chosen here is written down, not put up** -- choosing then closes the
picker as usual, and the wallpaper stays as it was.

### Colour from the wallpaper

When **Colour from the wallpaper**, above the tabs of the settings window, is ticked, a wallpaper
set from the picker hands its colour to the desktop when it goes on the screen the colour comes
from -- the primary screen, unless another is chosen under **Colour from the wallpaper of** on
[Appearance](appearance.md) -- or on every screen. One set on another screen changes that screen
and leaves the colours alone. What the colour does is on [Appearance](appearance.md#colours).

- KyprX starts working the colour out as soon as the selection stops on a wallpaper, so it is
  usually ready by the time you set it.
- The picker closes at once, and the new wallpaper appears a moment later, together with the new
  colours (measured; see the comment in `daemon/kyprd_wallpaper.py`, `WallpaperPart.set_wallpaper`).
  The screen can stop briefly while the colours change.
- Because the picker has closed by then, a failure is not shown in it. It goes to the log and,
  with notifications on ([Settings](settings.md)), to a desktop notification: **The wallpaper
  could not be changed.** or **The wallpaper's colour could not be applied.**

With the tick off, the wallpaper changes straight away and the colours are left alone.

### Pictures of the wallpapers

The small pictures the picker shows are made once and kept
(MAP). The first time a big folder is opened they fill
in one by one, starting at the selected wallpaper and working outwards; after that they come up
at once. A file replaced by another of the same name gets a new picture. For a package, the
picture is the largest one in it; for a video, a frame from about one second in, taken with
`ffmpeg`.

When a wallpaper has no picture -- `ffmpeg` missing, or a file this computer cannot read -- it is
still listed and can still be set. In the strip with its text ticked, its card shows its name,
written sideways, and the big picture reads **no preview**; with the text unticked, the card and
the big picture are left plain. In Pages it is a plain page. Without `ffmpeg`, **Colour from the
wallpaper** also has no
colour to take from a video.

The picker is always drawn fully opaque, whatever **Opacity** says on
[Appearance](appearance.md), and the blur is kept off it: it shows pictures, and a little of
whatever is behind it mixed in would change the picture you are judging.
