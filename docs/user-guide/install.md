# Installing, updating and removing KyprX

KyprX is built on four other programs, and needs every one of them: Klassy (the window
decoration), Better Blur DX (the blur), Geometry Change (the window animation) and Smart Video
Wallpaper Reborn (video wallpapers). The packages install them with KyprX. The tiling is KyprX's
own, so no tiling script is among them. It runs on KDE Plasma 6 in a Wayland session.

Installing a package changes nothing on your desktop. KyprX switches itself on the first time you
open it, from the application menu, or while `./install.sh` runs. That first start puts on KyprX's
settings: its tiling, focus following the mouse, the blur and the window animation, and Klassy's
window frames, drawn in your own colours, with the outline round the active window in your accent
colour. Your global theme, your colours, your panel and your accent colour stay as they are.

The first time the settings window opens, it asks whether to put KyprX's look on as well, and
lists exactly what that would change: Klassy's global theme, one of KyprX's colour presets, its
panel style and an amber outline round the active window. **Keep my look** is the default, and
closing the question counts as that. **Put KyprX's look on** keeps a copy of the desk first; going
back to it puts back what KyprX writes, while a global theme and colours of your own come back from
System Settings, where you chose them. Either way, the Colours box on the
[Appearance](appearance.md#kyprxs-look-the-first-time) tab changes it later. An update never asks.

## Fedora

KyprX's repository is in COPR, Fedora's service for community packages. KyprX installs on Fedora
44: Better Blur DX's repository no longer builds for Fedora 43, so a new install there stops for
want of it, and Klassy's has no Fedora 45 yet. Enabling KyprX's repository offers to enable the
two repositories it depends on as well, for Klassy and Better Blur DX; answer yes.

```sh
sudo dnf copr enable cyberbessa/kyprx
sudo dnf install kyprx
```

Then open **KyprX** from the application menu.

## Fedora systems that update as a whole

Kinoite and the systems built on it install a package by layering it onto the system, which takes
effect after a restart. Add KyprX's repository and the two it depends on, then layer the package:

```sh
sudo curl -Lo /etc/yum.repos.d/kyprx.repo \
  https://copr.fedorainfracloud.org/coprs/cyberbessa/kyprx/repo/fedora-$(rpm -E %fedora)/cyberbessa-kyprx-fedora-$(rpm -E %fedora).repo
rpm-ostree install kyprx
systemctl reboot
```

The repository file carries the two repositories KyprX depends on as well. If `rpm-ostree`
still says that `klassy` or `kwin-effects-better-blur-dx` cannot be found, their repositories have
to be added the same way; the
[packaging notes](../../packaging/README.md#the-repositories-kyprx-depends-on) list them.

## Arch, and systems built on it

The four programs are in the AUR, and KyprX is on its way there. Until it is, each release on
GitHub carries KyprX's PKGBUILD, and `paru` builds it and installs the four with it. This one
line builds the package in a temporary folder and deletes that folder at the end, so nothing of
the build is left where you run it; paru keeps its own copies of the four programs it builds in
`~/.cache/paru/clone/`, as it does for every AUR package:

```sh
bash -c 'build=$(mktemp -d) && cd "$build" && curl -fL -o PKGBUILD https://github.com/cyberbessa/kyprx/releases/latest/download/PKGBUILD && paru -Ui; rm -rf "${build:?}"'
```

Paste it as it is into fish, the shell CachyOS starts with, or into bash or zsh: the three read
it alike, and it runs in bash whichever one it is pasted into.

With another AUR helper, such as `yay`, install the four with it first -- `klassy`,
`kwin-effects-better-blur-dx`, `kwin-effects-geometry-change` and
`plasma6-wallpapers-smart-video-wallpaper-reborn` -- then run the same line with `makepkg -si` in
place of `paru -Ui`. Klassy and Better Blur DX are built on your computer, which takes a few
minutes.

## Any other system

Install the four programs first -- each one's page says how -- and KyprX's own requirements:
PySide6, dbus-python and PyGObject for Python 3, and Plasma's `kwriteconfig6` and
`plasma-apply-colorscheme`. Then download a release, unpack it where it will stay, and run the
installer inside your Plasma session:

```sh
./install.sh --dry-run    # check the requirements and show every step, changing nothing
./install.sh              # install, for your user only
```

The installer installs nothing you are missing: it names what is missing, with the command for
your system, and stops. Keep the folder where it is: the installed files point into it.

## Updating

Updating never starts by removing anything: the new version goes in over the old one. To find out
whether there is one, press **Look for a new version**, on the
[Settings](settings.md#look-for-a-new-version) tab: KyprX never looks by itself.

How a new version arrives depends on how KyprX was installed:

- **Fedora**: `sudo dnf upgrade --refresh kyprx`. If it finds nothing, try again later: the
  package is built a few minutes after the release.
- **A Fedora system that updates as a whole**: `rpm-ostree upgrade`, then restart the computer.
- **Arch**: the same [line as the install](#arch-and-systems-built-on-it), which builds the new
  release's package over the installed one; `makepkg -si` in place of `paru -Ui` if that is how
  KyprX was installed.
- **`install.sh`**: `./install.sh --update`, or **Update now** in the dialog that
  [Look for a new version](settings.md#look-for-a-new-version) opens. On a clone of the
  repository it brings in what the branch it follows has; on a folder unpacked from a release it
  unpacks the newest release beside the old folder, which stays until you delete it. `--dry-run`
  on either shows what would be done, changing nothing.

Your setup is kept, your look included: an update never asks about KyprX's look, and changes none
of it. When a new version keeps its own files in a new shape, KyprX first copies the
files it will rewrite into your KyprX folder, `~/.config/kyprx/snapshots/`, and the log says
where.

The new version takes over as each part of KyprX starts again. If you update while KyprX is running,
the window shows a band until then, with a button that restarts the background service (see
[KyprX was updated while it ran](README.md#kyprx-was-updated-while-it-ran)). Logging out and back
in does the same. If the Tiling tab then shows a band saying that KyprX's part of the compositor is
from before the update, log out and back in: the compositor keeps the part of KyprX it has loaded
for the rest of the session, and that part goes on tiling as it did until then.

**After a Plasma update.** Klassy and Better Blur DX are compiled for one version of KDE's window
manager. Until each is built again for the new one, the title bars or the blur stop working, and
KyprX says so on the Settings tab under [What KyprX needs](settings.md#what-kyprx-needs), with what
to do. On Fedora their repositories publish the new build. On Arch you build it again with the
command KyprX gives, `paru -S --rebuild aur/` and the package's name -- `yay -S --rebuild aur/` with
yay: a plain `paru -S` or `yay -S` installs the helper's earlier build again rather than making a
new one. For the blur, KyprX's package also says so at the end of the update that brings the new
KWin, in the update's own output. Either way, log out and back in
afterwards, because the window manager loads them as the session starts
([The blur or the title bars stopped after an update](../troubleshooting.md#the-blur-or-the-title-bars-stopped-after-an-update)).

## Removing

Removing KyprX starts in KyprX: **Remove KyprX from this computer…**, at the bottom of the
[Settings](settings.md#remove-kyprx-from-this-computer) tab. A package manager removes the files a
package installed and never touches your settings, so KyprX does that part first. It asks two
questions, and chooses neither answer for you:

- whether KDE goes back as KDE has it, or your desktop stays looking as it does now;
- whether your KyprX folder, `~/.config/kyprx/`, with your setup and the copies of the desk, is
  kept. A folder that is a git repository is never removed by KyprX.

It then takes back what only KyprX used and gives you the command that removes its files:

| Installed with | The command |
|---|---|
| Fedora | `sudo dnf remove kyprx` |
| A Fedora system that updates as a whole | `rpm-ostree uninstall kyprx`, then restart |
| Arch | `sudo pacman -Rs kyprx` |
| `install.sh` | `./install.sh --uninstall`, from the folder you installed from |

Run before the button, `./install.sh --uninstall` removes nothing: it says the button comes first.
`--force` removes the files anyway, and leaves everything the button would have taken back.

Three things stay, whatever you answer:

- the desktops KyprX made for windows, as ordinary desktops;
- the keys KyprX took from other actions -- Meta+R from Spectacle's **Start/Stop Region
  Recording**, Meta+T from KWin's **Toggle Tiles Editor** -- which are left without one. System
  Settings, under **Shortcuts**, gives each its key back;
- with your desktop left as it is, the look and the window behaviour KyprX gave it -- focus that
  follows the mouse among it. KyprX's panel style and colour presets go with its files, and
  nothing is put in their place.

The four programs are not removed by KyprX: they are programs of their own. The package manager
removes the ones it installed only for KyprX, and asks first; the ones you installed yourself stay.

### Arch, installed from the release's PKGBUILD

pacman leaves a program you installed by a command of your own, and KyprX's own command names only
KyprX. Installed as [above](#arch-and-systems-built-on-it) with `paru`, the four came in as KyprX's
own needs, and `sudo pacman -Rs kyprx` takes the ones nothing else needs. With `yay` and
`makepkg -si`, all four came in by a command of yours, so name the four:

```sh
sudo pacman -Rs kyprx klassy kwin-effects-better-blur-dx \
  kwin-effects-geometry-change plasma6-wallpapers-smart-video-wallpaper-reborn
```

pacman lists everything it will remove, and asks before it removes anything: read the list. It
takes what you named and whatever was installed only for it, and never a package something else
still needs, so on a Plasma desktop Plasma itself stays. Tried on a clean Arch, in a container,
with the 0.2.0 release installed by that line, run from fish: the four came in as KyprX's own
needs, and `sudo pacman -Rs kyprx` took KyprX, the four and their files. The command naming the
four was tried on a clean Arch while KyprX needed a fifth program, named with them: afterwards
KyprX, the five and their files were gone.

Two things stay behind, and each is yours to delete or keep:

- the copies of what the AUR helper built, in `~/.cache/paru/clone/` or `~/.cache/yay/` --
  `paru -Sc` or `yay -Sc` offers to clear them;
- tools installed only to build the four, such as `extra-cmake-modules`, which nothing needs once
  they are built. `pacman -Qdt` lists every package nothing needs -- the whole system's, not only
  KyprX's -- so read it before removing any of them.

A PKGBUILD built some other way leaves, in the folder it was built in, the PKGBUILD, the
downloaded code (`kyprx-<version>.tar.gz`), the built package
(`kyprx-<version>-1-any.pkg.tar.zst`) and the files the build tools add there, such as a hidden
`.SRCINFO` or the `src` and `pkg` folders. KyprX needs none of them once it is installed: delete
them, or the whole folder if it was made for them alone.
