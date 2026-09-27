# Installing, updating and removing KyprX

KyprX is built on five other programs, and needs every one of them: Klassy (the window
decoration), Better Blur DX (the blur), Krohnkite (the tiling), Geometry Change (the window
animation) and Smart Video Wallpaper Reborn (video wallpapers). The packages install them with
KyprX. It runs on KDE Plasma 6 in a Wayland session.

Installing changes nothing on your desktop. KyprX switches itself on the first time you open it,
from the application menu.

## Fedora

KyprX's repository is in COPR, Fedora's service for community packages. Enabling it offers to
enable the two repositories it depends on as well, for Klassy and Better Blur DX; answer yes.

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

The repository file names the repositories KyprX depends on. If `rpm-ostree` says that
`klassy` or `kwin-effects-better-blur-dx` cannot be found, their repositories have to be added the
same way; the [packaging notes](../../packaging/README.md#the-repositories-kyprx-depends-on) list
them.

## Arch, and systems built on it

KyprX and the five programs are in the AUR. An AUR helper installs them together:

```sh
paru -S kyprx      # or: yay -S kyprx
```

Klassy and Better Blur DX are built on your computer, which takes a few minutes.

## Any other system

Install the five programs first -- each one's page says how -- and KyprX's own requirements:
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

A new version arrives with the rest of your system's updates: `sudo dnf upgrade` on Fedora, the
automatic updates of a system that updates as a whole (after its restart), or `paru -Syu` on Arch.
For an install made with `install.sh`, download the new release and run `./install.sh` again from
it.

Your setup is kept. When a new version keeps its own files in a new shape, KyprX first copies the
files it will rewrite into your KyprX folder, `~/.config/kyprx/snapshots/`, and the log says
where.

The new version takes over as each part of KyprX starts again. If you update while KyprX is running,
the window shows a band until then, with a button that restarts the background service (see
[KyprX was updated while it ran](README.md#kyprx-was-updated-while-it-ran)). Logging out and back
in does the same.

**After a Plasma update.** Klassy and Better Blur DX are compiled for one version of KDE's window
manager. Until each is built again for the new one, the title bars or the blur stop working, and
KyprX says so on the Settings tab under [What KyprX needs](settings.md#what-kyprx-needs), with what
to do. On Fedora their repositories publish the new build; on Arch you build it again with the
command KyprX gives.

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

The five programs are not removed by KyprX: they are programs of their own. The package manager
removes the ones it installed only for KyprX, and asks first; the ones you installed yourself stay.
