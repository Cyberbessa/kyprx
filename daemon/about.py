"""This installation of KyprX: which version it is, how it was installed, and where the desktop's
data folders are.

**The version is one file**, `VERSION`, at the top of the tree this code runs from, found through
this file's real path the way the Credits box finds `CREDITS.md`. That tree is the working tree
for an install made by `install.sh`, whose links point into it, and `/usr/share/kyprx` for a
package, which `packaging/stage.sh` lays out the same way. One file rather than a constant in the
code, because what builds a package needs it before any code runs, and a number kept in several
places is several numbers.

**How it was installed** decides what removing it means: a package is taken off by the package
manager, a working tree by `install.sh --uninstall`. The tree says which it is by where it is.

**Which system this is** decides which words to use for a package: its name there, and the
command that installs it. Only three families are told apart, because only three have a package
of KyprX: Fedora, the Fedora images that update as a whole and install a package by layering it
(`rpm-ostree`, and a restart), and Arch with everything built on it. `ID_LIKE` is what makes a
derivative count as its family.

**The data folders** are the ones the desktop searches, the user's first: a file this app installs
may be in either, and the user's copy is the one the desktop uses. The walk follows the same rules
the desktop itself applies to the variables (`QStandardPaths` on which: doc.qt.io/qt-6/
qstandardpaths.html) -- `XDG_DATA_HOME` only when it is an absolute path, relative entries of
`XDG_DATA_DIRS` ignored, the defaults standing whenever nothing that counts is set -- and is kept
as the session spells it and deduplicated by what it points at, for the reason given at
`daemon/wallpaper.py`. The same walk `daemon/theme.py` and `daemon/wallpaper.py` make.
"""

from __future__ import annotations

import os

#: The top of the tree this code runs from: the folder above `daemon/`, every link resolved.
TOP = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
VERSION_FILE = os.path.join(TOP, "VERSION")


def version() -> str:
    """This installation's version, or "" when the file is not there to say it."""
    try:
        with open(VERSION_FILE, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


#: The version of the code this process is running, read once, when it starts. `version()` reads
#: the file again every time, and after an update the two differ: the file is the new version, the
#: process still the old one until it starts again.
RUNNING = version()


def from_package() -> bool:
    """Was this installed by a package manager, rather than linked from a working tree?

    A package puts the code under the system's prefix, where nobody keeps a working tree; a working
    tree is wherever somebody cloned or unpacked it, and `install.sh` links the session to it.
    """
    return TOP.startswith(("/usr/", "/opt/"))


def data_dirs(env=None) -> list[str]:
    """Every folder the desktop searches for data, the user's own first, and `env` naming the
    variables rather than this process's own -- so the same walk can be read against an
    environment a test built.

    The rules are the desktop's, not ours: `XDG_DATA_HOME` counts only when it is **absolute**
    (`QStandardPaths` passes a relative one over, and so do we), an entry of `XDG_DATA_DIRS` that
    is not absolute is ignored, and the defaults stand whenever nothing that counts is set.
    Duplicates are dropped by what a path points at, and the spelling the session used is the one
    kept -- the reason is the one `wallpaper_dirs` in `daemon/wallpaper.py` holds, and it matters
    for the same reason: a spelling nobody else on this desktop writes stops matching the one
    already in a config.
    """
    e = os.environ if env is None else env
    home = e.get("XDG_DATA_HOME") or ""
    home = home if home.startswith("/") else os.path.expanduser("~/.local/share")
    rest = [d for d in (e.get("XDG_DATA_DIRS") or "").split(":") if d.startswith("/")]
    if not rest:
        rest = ["/usr/local/share", "/usr/share"]
    out: list[str] = []
    seen: set[str] = set()
    for base in [home] + rest:
        key = os.path.realpath(base)
        if key not in seen:
            seen.add(key)
            out.append(base)
    return out


def data_path(leaf: str) -> str:
    """Where `leaf` is in the first data folder that has it, or "" when none does."""
    for base in data_dirs():
        path = os.path.join(base, leaf)
        if os.path.exists(path):
            return path
    return ""


FEDORA = "fedora"
FEDORA_ATOMIC = "fedora-atomic"
ARCH = "arch"
OTHER = "other"


def system(os_release: str = "/etc/os-release", booted: str = "/run/ostree-booted") -> str:
    """`FEDORA`, `FEDORA_ATOMIC`, `ARCH` or `OTHER`: whose package manager speaks here."""
    words: set[str] = set()
    try:
        with open(os_release, encoding="utf-8") as fh:
            for line in fh:
                key, _, value = line.strip().partition("=")
                if key in ("ID", "ID_LIKE"):
                    words.update(value.strip().strip('"').split())
    except OSError:
        return OTHER
    if "fedora" in words:
        return FEDORA_ATOMIC if os.path.exists(booted) else FEDORA
    if "arch" in words:
        return ARCH
    return OTHER


def removal_command(system_name: str | None = None) -> str:
    """The command that removes what is left of this installation once KyprX has taken back what
    it wrote: the package, by the system's package manager, or the links `install.sh` made. Said,
    never run -- removing a package is the package manager's, and asks for the administrator."""
    if not from_package():
        return f"{os.path.join(TOP, 'install.sh')} --uninstall"
    system_name = system_name or system()
    return {FEDORA: "sudo dnf remove kyprx",
            FEDORA_ATOMIC: "rpm-ostree uninstall kyprx",
            ARCH: "sudo pacman -Rs kyprx"}.get(system_name,
                                                "remove the kyprx package with your package manager")


def removal_after(system_name: str | None = None) -> str:
    """What has to follow `removal_command` before it is done, said apart from the command so that
    copying the command copies only the command. A system that updates as a whole takes a change
    of package in at the next start."""
    if from_package() and (system_name or system()) == FEDORA_ATOMIC:
        return "Then restart the computer: the package goes at the next start."
    return ""

