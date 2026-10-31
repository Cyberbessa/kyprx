<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="share/icons/kyprx-mark.png">
    <img src="share/icons/hicolor/256x256/apps/kyprx.png" width="140" alt="KyprX">
  </picture>
</p>

<h1 align="center">KyprX — KDE-Native Hyprland Experience</h1>

<p align="center">
  The clean, tiled, title-bar-free look of Hyprland, built into KDE Plasma 6 —<br>
  and one window to shape all of it.
</p>

<p align="center">
  <a href="https://github.com/cyberbessa/kyprx/releases"><img src="https://img.shields.io/github/v/release/cyberbessa/kyprx?label=release&color=informational" alt="Latest release"></a>
  <a href="https://copr.fedorainfracloud.org/coprs/cyberbessa/kyprx/"><img src="https://img.shields.io/badge/Fedora-COPR-51A2DA?logo=fedora&logoColor=white" alt="Fedora: COPR"></a>
  <a href="https://aur.archlinux.org/packages/kyprx"><img src="https://img.shields.io/aur/version/kyprx?logo=archlinux&logoColor=white&label=AUR" alt="Arch: AUR"></a>
  <img src="https://img.shields.io/badge/KDE%20Plasma-6-1D99F3?logo=kde&logoColor=white" alt="KDE Plasma 6">
  <img src="https://img.shields.io/badge/session-Wayland-FFBC00?logo=wayland&logoColor=white" alt="Wayland">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0--or--later-blue" alt="GPL-3.0-or-later"></a>
  <a href="https://ko-fi.com/cyberbessa"><img src="https://img.shields.io/badge/Ko--fi-support%20KyprX-FF5E5B?logo=kofi&logoColor=white" alt="Support KyprX on Ko-fi"></a>
</p>

<p align="center">
  <a href="#install"><b>Install</b></a> ·
  <a href="#why-youll-like-it"><b>Features</b></a> ·
  <a href="#see-it-move"><b>See it</b></a> ·
  <a href="#roadmap"><b>Roadmap</b></a> ·
  <a href="docs/user-guide/README.md"><b>User guide</b></a> ·
  <a href="https://ko-fi.com/cyberbessa"><b>Support KyprX</b></a>
</p>

<p align="center">
  <img src="screenshots/wallpaper-colour.avif" width="100%" alt="A wallpaper chosen from the picker, and the tiled windows with no title bars taking its colour">
</p>

---

Hyprland looks stunning — but getting that look has always meant leaving KDE Plasma, and
everything Plasma does for you, behind. **KyprX brings the look to Plasma instead.** Windows open
tiled side by side, with no title bars, a slim accent outline, a touch of transparency and blur
behind them — while your apps, your settings and the rest of your desktop stay right where they
are.

**Native, not bolted on.** There is no second compositor, and nothing is replaced: KyprX tiles your
windows from inside KWin, KDE's own window manager, sets up the decoration, blur and animation
plugins KWin runs — and gathers all of it into a single window, where each change lands the moment
you make it.

## Why you'll like it

- **Tiled from the first window.** Open an app and it takes its place in the layout: no dragging,
  no snapping. KyprX tiles the windows itself, and focus, swapping and resizing are each a key
  away.
- **Layouts you draw.** Split a zone, take one away, set its share in percent — or start from the
  zone layouts KyprX comes with. An arrangement picks one for each number of windows, each desktop
  starts on the one you choose for it, and a key flips between arrangements. Prefer to place windows yourself? In manual mode a window goes where
  you drag it; take it through the bar of layouts along the top, and the zones show and it drops
  into the one under the pointer. Drag it to the top edge and it is maximized, as KDE does.
- **Windows that float when they should.** Dialogs float by themselves, any app or title can be
  told to float or never to be tiled, and a key floats the window in front of you.
- **No title bars, all the style.** Clean frames with an accent outline, transparency and blur —
  set once for everything, or app by app.
- **One window, not a stack of settings pages.** Decoration, blur, tiling, animations, shortcuts
  and colours, side by side. There is no Apply button: what you change is simply there.
- **A new look in one click.** Catppuccin, Nord, Gruvbox, Dracula, Solarized, Rosé Pine and
  Monochrome, dark and light — or the colour of your wallpaper, soaked into the whole desktop.
- **Profiles.** Keep a look under a name and bring it back in a second.
- **Wallpapers that move.** A picker for pictures and video wallpapers, one key away.
- **Every shortcut at a glance.** One key shows them all, and every key can be changed.
- **Made for dotfiles.** Your whole setup is a folder of readable files, `~/.config/kyprx/`. Keep
  it in git, carry it to another computer, and KyprX applies it by itself.
- **Safe to try.** A copy of your desktop is kept before every big change, stock KDE is one click
  away, and removing KyprX asks first, takes back what only KyprX used, and says what stays.

## See it move

**The wallpaper picker.** Meta+R opens it over the desktop: the chosen wallpaper large in the
middle, the rest leaning away behind it like pages of an open book, and Enter puts it on. A strip
of thumbnails beside one big picture is one setting away. Pictures or videos.

<p align="center">
  <img src="screenshots/wallpaper-picker.avif" width="100%" alt="The wallpaper picker opening over the desktop, moving through video wallpapers, and putting one on">
</p>

**Transparency, live.** One number sets how see-through every window is, and the windows follow
as the number changes.

<p align="center">
  <img src="screenshots/transparency.avif" width="100%" alt="The opacity on the Appearance tab lowered, and the tiled windows turning see-through as it changes">
</p>

**Every shortcut at a glance.** Meta+/ shows them all over whatever is on screen, grouped: tiling,
layouts, window management, and KyprX itself.

<p align="center">
  <img src="screenshots/cheatsheet.avif" width="100%" alt="The shortcut cheatsheet opening over the desktop, with the keys for tiling, for layouts, for window management and for KyprX">
</p>

## One window, tab by tab

<table>
  <tr>
    <td width="50%"><img src="screenshots/tab-windows.png" alt="The Windows tab"><br><b>Windows</b> — every app on a row of its own: title bar, transparency, blur, floating and animation, and a box in a column's header to set it for every app at once.</td>
    <td width="50%"><img src="screenshots/tab-appearance.png" alt="The Appearance tab"><br><b>Appearance</b> — profiles, colour presets, a colour of your own or the wallpaper's, and the windows' opacity, corners and outline.</td>
  </tr>
  <tr>
    <td><img src="screenshots/tab-tiling.png" alt="The Tiling tab"><br><b>Tiling</b> — focus, automatic or manual tiling, your arrangements, the one each desktop starts on, the zone layouts they pick from and the split builder that draws them, the gaps, where a new window goes, and the windows never tiled.</td>
    <td><img src="screenshots/tab-effects.png" alt="The Effects tab"><br><b>Effects</b> — the blur behind windows, menus and panels, and the animation as windows move.</td>
  </tr>
  <tr>
    <td><img src="screenshots/tab-shortcuts.png" alt="The Shortcuts tab"><br><b>Shortcuts</b> — the keys for tiling, for the layouts, for window management and for KyprX itself, each one yours to change.</td>
    <td><img src="screenshots/tab-wallpaper.png" alt="The Wallpaper tab"><br><b>Wallpaper</b> — pictures or videos, the video folder, when a video pauses, and the picker's layout.</td>
  </tr>
  <tr>
    <td><img src="screenshots/tab-settings.png" alt="The Settings tab"><br><b>Settings</b> — your KyprX folder and the copies of your desktop, what KyprX needs, and the way back to stock KDE.</td>
    <td></td>
  </tr>
</table>

## Install

**Fedora 44**

```sh
sudo dnf copr enable cyberbessa/kyprx
sudo dnf install kyprx
```

**Arch** and friends — EndeavourOS, CachyOS, Manjaro…

KyprX is on its way to the AUR. Until it is there, each release carries its PKGBUILD, and an AUR
helper builds it and brings in everything it needs from the AUR. This one line builds the package
in a temporary folder and deletes that folder at the end, so nothing of the build is left where you
run it; paru keeps its own copies of what it builds from the AUR in `~/.cache/paru/clone/`:

```sh
bash -c 'build=$(mktemp -d) && cd "$build" && curl -fL -o PKGBUILD https://github.com/cyberbessa/kyprx/releases/latest/download/PKGBUILD && paru -Ui; rm -rf "${build:?}"'
```

Paste it as it is into fish, the shell CachyOS starts with, or into bash or zsh: the three read it
alike, and it runs in bash whichever one it is pasted into.

Everything KyprX is built on comes with it. For Fedora Kinoite and the systems built on it, for
other distributions, and for updating and removing, see
[Installing, updating and removing KyprX](docs/user-guide/install.md).

Then open **KyprX** from your application menu: the first launch is what switches it on. It leaves
your colours and global theme as they are, and asks whether to put KyprX's look on. From then on,
three keys are all you need:

| Key | What it does |
|---|---|
| **Meta+K** | opens KyprX |
| **Meta+/** | shows every shortcut |
| **Meta+R** | opens the wallpaper picker |

## Roadmap

KyprX is built and kept by one person. Your support decides how fast this list becomes releases:
the goal on Ko-fi is always the next item here, and reaching it is what starts it.

1. **Scratchpads.** One key brings an app — a terminal, your notes, your music — floating over
   whatever you are doing, and the same key sends it away. Hyprland's special workspaces, on
   Plasma.
2. **Coming from Hyprland? Bring your config.** Point KyprX at your `hyprland.conf` and it brings
   your gaps, borders, rounding, transparency, blur and the keybindings that have a Plasma
   equivalent — shown to you before anything changes.
3. **A dock, done the KyprX way.** Set up, place and style a dock that belongs to the tiled
   desktop, from the same window as everything else.
4. **Fewer moving parts.** Tiling, the window animation and video wallpapers built into KyprX
   itself — three dependencies fewer.
5. **One app.** The decoration and the blur inside KyprX too, as far as KWin allows, so that KyprX
   installs and updates as a single app. Deep, KWin-level work — which is exactly why support
   matters.

## Support KyprX

If KyprX made your desktop feel like yours, you can help keep it going:

<p align="center">
  <a href="https://ko-fi.com/cyberbessa"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Support KyprX on Ko-fi"></a>
</p>

Every coffee buys time: to keep up with each Plasma release, to keep the packages building, and
to work through the roadmap. Not in a position to give? Starring the repository, sharing a
screenshot of your desktop and reporting what breaks all help too.

## Built on

KyprX brings together four excellent projects. They deserve a star as well:

| Project | What it brings |
|---|---|
| [Klassy](https://github.com/paulmcauley/klassy) | the window decoration: hidden title bars, outlines, the frame |
| [Better Blur DX](https://github.com/xarblu/kwin-effects-better-blur-dx) | the blur behind see-through windows |
| [Geometry Change](https://github.com/peterfajdiga/kwin4_effect_geometry_change) | the animation as windows move and resize |
| [Smart Video Wallpaper Reborn](https://github.com/luisbocanegra/plasma-smart-video-wallpaper-reborn) | video wallpapers |

The tiling is KyprX's own. Its ideas come from two projects worth knowing too: the zones of
[KZones](https://github.com/gerritdevriese/kzones) that a window is dropped into, and the dwindle
layout of [Hyprland](https://github.com/hyprwm/Hyprland). No code was taken from either of them.

## Learn more

- [User guide](docs/user-guide/README.md) — the window, tab by tab.
- [Installing, updating and removing](docs/user-guide/install.md).
- [Troubleshooting](docs/troubleshooting.md) — what went wrong, and how to get your desktop back.

## Licence

KyprX is free software, under the GNU General Public License, version 3 or later. A few files keep
other licences: the colour schemes and the Plasma style's `plasmarc` are made from Klassy's and
keep its LGPL-2.0-or-later, and the metadata software centres show is CC0-1.0.
[CREDITS.md](CREDITS.md) lists every project KyprX works with or takes colours from, and what
their licences ask.

<sub>Each release of KyprX arrives here as one commit: the code, the package recipes in
`packaging/`, and the user guide.</sub>
