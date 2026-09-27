# Credits

KyprX is free software, under the GNU General Public License, version 3 or any later version — see
[`LICENSE`](LICENSE). It keeps settings of its own (every file it keeps is listed in
MAP), but the desktop settings it changes belong to programs other people wrote, and most
of its colour presets wear palettes other people chose. This page says whose, under what terms, and
what those terms ask of KyprX.

The licences below are as each project's repository and its installed metadata state them. Carl
links a website rather than a repository, so its licences are those its installed metadata
declares.

## The programs it works with

| Project | By | Where | Licence | What KyprX uses it for |
|---|---|---|---|---|
| **Klassy** | Paul A McAuley, continuing KDE's Breeze (Martin Gräßlin, Hugo Pereira Da Costa and others) | [paulmcauley/klassy](https://github.com/paulmcauley/klassy) | Its code GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL, file by file, as KDE does; its colour schemes LGPL-2.0-or-later; its Plasma styles LGPL and its global themes LGPL 2.1, as their metadata declare | The window decoration, its dark and light global themes, and its two colour schemes, offered as presets. Two of its files are the base of files shipped here, below. See Klassy |
| **Better Blur DX** | xarblu, continuing taj-ny's Better Blur, itself a fork of Plasma's blur effect | [xarblu/kwin-effects-better-blur-dx](https://github.com/xarblu/kwin-effects-better-blur-dx) | GPL-3.0 | The blur behind windows. See Better Blur DX |
| **Krohnkite** | Vjatcheslav V. Kolchkov, continuing Eon S. Jeon's Kröhnkite | [anametologin/krohnkite](https://github.com/anametologin/krohnkite), archived there with a note that the project moved to [codeberg.org/anametologin/Krohnkite](https://codeberg.org/anametologin/Krohnkite) | MIT | The tiling. See Krohnkite |
| **Geometry Change** | Peter Fajdiga | [peterfajdiga/kwin4_effect_geometry_change](https://github.com/peterfajdiga/kwin4_effect_geometry_change) | GPL-3.0 | The window animation. See Geometry Change |
| **Smart Video Wallpaper Reborn** | Luis Bocanegra, with Rog131 and adhe | [luisbocanegra/plasma-smart-video-wallpaper-reborn](https://github.com/luisbocanegra/plasma-smart-video-wallpaper-reborn) | GPL-2.0-or-later | Optional: video wallpapers. See Smart Video Wallpaper Reborn |
| **Carl** | jomada | [seduccionlinux.wordpress.com](https://seduccionlinux.wordpress.com) | Global theme GPL-3.0-or-later, Plasma style LGPL; its colour scheme file names no licence | Optional: its colour scheme is offered as a preset when it is installed. Nothing of it is shipped here. See Carl |

## The palettes

Nine of the colour presets wear these palettes. Their colours are theirs; the scheme files built
from them are KyprX's work on the structure of Klassy's, and carry Klassy's licence (see below).

| Preset | Palette by | Where | Licence |
|---|---|---|---|
| Catppuccin Mocha, Catppuccin Latte | Catppuccin | [catppuccin/catppuccin](https://github.com/catppuccin/catppuccin) | MIT |
| Nord | Sven Greb | [nordtheme/nord](https://github.com/nordtheme/nord) | MIT |
| Gruvbox Dark, Gruvbox Light | Pavel Pertsev (morhetz) | [morhetz/gruvbox](https://github.com/morhetz/gruvbox) | MIT/X11, as its README states |
| Dracula | Dracula Theme | [dracula/dracula-theme](https://github.com/dracula/dracula-theme) | MIT |
| Solarized Dark, Solarized Light | Ethan Schoonover | [altercation/solarized](https://github.com/altercation/solarized) | MIT |
| Rosé Pine Dawn | Rosé Pine | [rose-pine/rose-pine-theme](https://github.com/rose-pine/rose-pine-theme) | MIT |

The other presets are not borrowed palettes. Monochrome Dark and Monochrome Light are KyprX's own;
their single background for the whole window follows the shape of Carl's scheme, as the header of
`share/color-schemes/KyprXMonochromeDark.colors` explains. Klassy Dark and Klassy Light are
Klassy's own schemes, and Carl is Carl's. A colour of your own, or one taken from your wallpaper,
is yours.

## What it runs on

All of these are used as the system installs them; none is copied into this repository.

| Project | What KyprX uses it for | Licence |
|---|---|---|
| KDE Plasma and its compositor, KWin | The desktop itself: KyprX drives its scripting, window rules, shortcut registry, the shell's scripting (for the wallpaper) and settings tools (`kwriteconfig6` and the `plasma-apply-*` tools). See KDE Plasma | Mostly GPL and LGPL, file by file |
| Breeze, KDE's own look | Two roles. Its two colour schemes are named for a moment when a palette has to be re-applied under an unchanged name, and its two global themes are what *Take KyprX off this desk…* applies | Colour schemes LGPL-2.0-or-later; global themes GPL-2.0-or-later |
| Python | The language KyprX's background program (the daemon) and its settings window are written in | Python-2.0.1 (the Python Software Foundation licence) |
| Qt and PySide6 | The settings window and the overlays | LGPL-3.0-only or GPL-3.0-only |
| dbus-python | The daemon's side of the desktop's message bus | MIT |
| PyGObject, GLib and GdkPixbuf | The daemon's main loop, and reading pictures for a wallpaper's colour | LGPL-2.1-or-later |
| ffmpeg | Video thumbnails, and a video wallpaper's colour | LGPL-2.1-or-later; GPL or version 3 of either, depending on how it was built |
| systemd | Starts the daemon as the user unit `kyprd.service` (`share/kyprd.service`) when something first calls it on the desktop's message bus, and stops it with the session. It does not restart it: the next call starts it again | LGPL-2.1-or-later for most of it |

## What the licences ask of KyprX

**Two kinds of file here are derived from Klassy's, and they keep Klassy's licence.**

- The eleven colour schemes in `share/color-schemes/` keep the sections and keys of Klassy's
  `KlassyDark.colors` (all but its French name) and its colour effects, except that the two
  Monochrome schemes grey the `Color` value of their `[ColorEffects]` groups. `KlassyDark.colors`
  is LGPL-2.0-or-later.
- The Plasma style's `share/desktoptheme/kyprx/plasmarc` carries two blocks of settings,
  `[ContrastEffect]` and `[AdaptiveTransparency]`, from Klassy's `klassy-dark` style, whose
  metadata declares LGPL.

So those twelve files are under LGPL-2.0-or-later rather than under KyprX's own licence. Each one's
header names its original authors and says what it is derived from, and the licence's text is in
[`LICENSES/LGPL-2.0-or-later.txt`](LICENSES/LGPL-2.0-or-later.txt). `REUSE.toml` declares
GPL-3.0-or-later for every file and lets a file's own licence lines win, which is how these twelve
keep theirs. They sit beside KyprX's own files rather than inside them, and the LGPL version 2
itself allows any copy to be put under the ordinary GPL, version 2 or a later one (its section 3).

**Nothing else here carries another project's licence.** Klassy, Better Blur DX, Krohnkite,
Geometry Change, Smart Video Wallpaper Reborn and Carl are separate projects: KyprX writes their
settings, applies the themes among them and opens Klassy's settings dialog, and contains none of
their code. What it repeats from them is the names of their settings and some of their default
values, which it needs in order to write those settings. The palettes reach this repository only
as colour values in the scheme files.

The palettes and Krohnkite are MIT-licensed, and their notices are reproduced below.

## Notices

The MIT licence, as it applies to each of these:

- Krohnkite — Copyright (c) 2018 Eon S. Jeon; Copyright (c) 2024 Vjatcheslav V. Kolchkov
- Catppuccin — Copyright (c) 2021 Catppuccin
- Nord — Copyright (c) 2016-present Sven Greb
- Gruvbox — no copyright line of its own; its README names the licence as MIT/X11, and its author
  is morhetz (Pavel Pertsev)
- Dracula — Copyright (c) 2023 Dracula Theme
- Solarized — Copyright (c) 2011 Ethan Schoonover
- Rosé Pine — Copyright (c) 2023 Rosé Pine

> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
> associated documentation files (the "Software"), to deal in the Software without restriction,
> including without limitation the rights to use, copy, modify, merge, publish, distribute,
> sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or
> substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
> NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
> NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
> DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT
> OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

The authors of Klassy's `KlassyDark.colors`, as its header names them and as the eleven colour
schemes repeat: Andrew Lake, Marco Martin, Nate Graham, Noah Davis, Neal Gompa, David Redondo,
Thomas Duckworth and Paul A McAuley. The style's `plasmarc` names Paul A McAuley, the author of
`klassy-dark`.
