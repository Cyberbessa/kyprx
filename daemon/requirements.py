"""What KyprX needs on this machine: the four projects it is built on, whether each one is there,
which version, and whether the compositor is actually running it.

Every one of the four is required. KyprX is those four put to one use, and a desk without one of
them is not KyprX, so the packages install them with it. The tiling is not one of them: it is
KyprX's own, in its compositor script, and whether it runs is the Tiling tab's to say
(`tiling_state`, in `daemon/kyprd_tiling.py`). What is checked here is what can still
go wrong after that: one removed by hand; one never installed, because KyprX was installed from a
working tree; and a compiled plugin the compositor lists and does not run, so that the blur or the
title bars simply stop, with nothing on screen saying why. The usual cause, sooner or later
everybody's, is a build for the KWin that ran before the last Plasma update -- but it is not the
only one, so for the blur it is read rather than assumed (`built_for`, below).

**How each one is found**, and why that way:

- Better Blur DX and Geometry Change by the compositor's own list of the effects it can load, and
  whether they run by the list of those it has loaded. When the compositor cannot be asked, the
  blur's file in the folders Qt looks for plugins in answers, and Geometry Change's
  `metadata.json` in the data folders the desktop searches (`about.data_dirs`), which also carries
  its version.
- The video plugin by its `metadata.json` in the data folders the desktop searches
  (`about.data_dirs`), which also carries its version. A file, not `kpackagetool6`: this is asked
  when a window opens, and a process started to draw a page is a page that stutters
  (`wallpaper.plugin_dir` says the same).
- Klassy by its decoration plugin's file, and whether it runs by the decoration the compositor says
  it is drawing with -- while `kwinrc` asks for Klassy's. The compositor falls back to its own
  decoration when it cannot load the one asked for.
- The version of the two compiled ones from the package manager, which is the only thing that
  records it.
- Why the blur is not running, by the KWin it was built for -- the tag in its plugin file
  (`built_for`) -- against the KWin running, from the compositor's `supportInformation`. Built for
  an older KWin, it has to be built again; for a newer one, the session still runs the KWin from
  before the update; for this one, building it again does not help -- unless that was done during
  this session -- and the compositor's log says why. Klassy's plugin carries no such tag, so its
  not running is told by the usual cause.

**The commands are this system's**: dnf or rpm-ostree on Fedora, and on Arch the AUR helper found
on the path -- paru, then yay -- or with neither the AUR's own clone and `makepkg`
(`_aur_command`). Each answer carries its command alone as well (`Need.command`), which the box's
*Copy the command* puts on the clipboard.

**Nothing here writes**, and the compositor is only asked questions: `scripts/buswatch.py` lets
exactly those through. The package managers' versions cost a process each (`rpm -q`, `pacman -Q`
or `dpkg-query`), and so does the package that owns a plugin which is not running, on Arch
(`pacman -Qqo`), so the daemon keeps the answer and works it out again only when asked to
(`InstallationPart.needs`).

Run as a program -- `python3 daemon/requirements.py` -- it prints what is wrong and exits 1, or says
all four are there and exits 0. `install.sh` runs it before installing anything. With `--facts`,
the answers are preceded by one line per project saying what its answer was built on, after one
naming the KWin running (`facts`); nothing is written and the exit code stays the same.
"""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import about  # noqa: E402
import effects  # noqa: E402
import kconfig  # noqa: E402
import klassy  # noqa: E402
import reload as reloader  # noqa: E402
import wallpaper  # noqa: E402
import writer  # noqa: E402

#: What a requirement can be. Only `OK` is fine; each of the others is said, with what to do.
OK = "ok"
MISSING = "missing"
NOT_RUNNING = "not running"
TOO_OLD = "too old"


@dataclass(frozen=True)
class Project:
    """One of the four, as KyprX knows it."""
    key: str
    name: str
    #: What KyprX has none of without it, as a noun phrase: "without it KyprX has no <purpose>".
    purpose: str
    #: The id the compositor, the shell or KyprX's own switches know it by.
    plugin: str
    url: str
    #: Its package on each family of systems (`about.FEDORA`, `about.ARCH`). The Fedora names are
    #: those of the repositories the KyprX package brings along; the Arch ones are the AUR's.
    packages: dict
    #: The oldest version KyprX works with, when there is one.
    minimum: str = ""


PROJECTS = (
    Project("klassy", "Klassy", "control over title bars and window outlines", klassy.DECORATION,
            "https://github.com/paulmcauley/klassy",
            {about.FEDORA: "klassy", about.ARCH: "klassy"}),
    Project("blur", "Better Blur DX", "blur behind windows", effects.BLUR_PLUGIN,
            "https://github.com/xarblu/kwin-effects-better-blur-dx",
            {about.FEDORA: "kwin-effects-better-blur-dx",
             about.ARCH: "kwin-effects-better-blur-dx"}),
    Project("animation", "Geometry Change", "window animation", effects.GEOMETRY_PLUGIN,
            "https://github.com/peterfajdiga/kwin4_effect_geometry_change",
            {about.FEDORA: "kwin-effects-geometry-change",
             about.ARCH: "kwin-effects-geometry-change"}),
    Project("video", "Smart Video Wallpaper Reborn", "video wallpapers", wallpaper.VIDEO_PLUGIN,
            "https://github.com/luisbocanegra/plasma-smart-video-wallpaper-reborn",
            {about.FEDORA: "plasma-smart-video-wallpaper-reborn",
             about.ARCH: "plasma6-wallpapers-smart-video-wallpaper-reborn"},
            minimum=wallpaper.VIDEO_PLUGIN_FIXED),
)


@dataclass
class Need:
    """One project, as it stands on this machine."""
    key: str
    name: str
    purpose: str
    plugin: str
    url: str
    state: str
    version: str
    #: What is wrong, in a sentence; empty when nothing is.
    detail: str
    #: What to do about it on this system; empty when nothing is wrong.
    fix: str
    #: The command in `fix` alone, for the box's *Copy the command*; empty when `fix` has none.
    command: str = ""


@dataclass
class Machine:
    """Everything the answer depends on, gathered in one place so that a test can make it up."""
    system: str
    #: `kwinrc`, for which plugins are switched on and which decoration is asked for.
    kwin: kconfig.KConfig
    data_dirs: list
    plugin_dirs: list
    #: (effects the compositor can load, effects it has loaded), or None when it cannot be asked.
    effects: tuple | None
    #: The decoration the compositor is drawing with, or None when it cannot be asked.
    decoration: str | None
    #: A package's version by its name, "" when it is not installed or nothing records it.
    package_version: object
    #: The version of the compositor running now, as numbers, or None when it cannot be asked.
    kwin_version: tuple | None = None
    #: The package that installed a file, by the file's path, "" when none or nothing says; None
    #: asks nothing.
    package_owner: object = None
    #: The AUR helper installed (`AUR_HELPERS`), "" for none; asked on Arch alone. The default is
    #: the one KyprX's own install line uses.
    aur_helper: str = "paru"


def qt_plugin_dirs() -> list[str]:
    """The folders Qt looks for plugins in: `QT_PLUGIN_PATH`, then each system layout's own."""
    found = [p for p in os.environ.get("QT_PLUGIN_PATH", "").split(":") if p]
    home = os.path.expanduser("~/.local")
    found += (
        sorted(glob.glob("/usr/lib*/qt6/plugins"))
        + sorted(glob.glob("/usr/lib/*/qt6/plugins"))
        + sorted(glob.glob("/usr/local/lib*/qt6/plugins"))
        + sorted(glob.glob("/usr/local/lib/*/qt6/plugins"))
        + sorted(glob.glob(f"{home}/lib*/qt6/plugins"))
    )
    out: list[str] = []
    for path in found:
        if path not in out and os.path.isdir(path):
            out.append(path)
    return out


def package_version(name: str) -> str:
    """The version the package manager records for `name`, or "" when it records none.

    `rpm` first, then `pacman`, then `dpkg-query`, whichever is installed and knows the package.
    """
    for argv in (["rpm", "-q", "--qf", "%{VERSION}", name],
                 ["pacman", "-Q", name],
                 ["dpkg-query", "-W", "-f=${Version}", name]):
        if not shutil.which(argv[0]):
            continue
        try:
            out = subprocess.run(argv, capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if out.returncode != 0 or not out.stdout.strip():
            continue
        text = out.stdout.strip()
        if argv[0] == "pacman":
            # `klassy 1:6.7.3-1`: the version, without the epoch and without the release. A name
            # no package has falls back to the one that provides it (measured: `pacman -Q sh`
            # printed `bash 5.3.9-1`), and the blur's `-git` and `-patched` packages provide
            # `kwin-effects-better-blur-dx` (their `.SRCINFO`), so theirs says its own version.
            text = text.split()[-1].split(":")[-1].rsplit("-", 1)[0]
        elif argv[0] == "dpkg-query":
            text = text.split(":")[-1].rsplit("-", 1)[0]
        return text
    return ""


def package_owner(path: str) -> str:
    """The package that installed the file at `path`, by `pacman -Qqo`: "" off Arch, or when no
    package owns it.

    So that the command to build a plugin again names the package this machine has: the AUR
    offers Better Blur DX under three names (`kwin-effects-better-blur-dx`, and `-git` and
    `-patched` after it), and an install of one asks which. Measured in an Arch container:
    `pacman -Qqo` on the blur's file printed `kwin-effects-better-blur-dx` and exited 0, and on a
    file no package owns said `error: No package owns ...` and exited 1.
    """
    if not shutil.which("pacman"):
        return ""
    try:
        out = subprocess.run(["pacman", "-Qqo", path], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    lines = out.stdout.split()
    name = lines[0] if out.returncode == 0 and lines else ""
    return name if re.fullmatch(r"[A-Za-z0-9@._+-]+", name) else ""


#: What KWin compares before it loads a compiled effect: the plugin's Qt interface id, this
#: followed by the exact version of KWin it was built against, patch number included --
#: `org.kde.kwin.EffectPluginFactory6.8.2`. KWin 6.8's `effect.h` names it `EffectPluginFactory_iid`
#: and `config-kwin.h.cmake` makes the version MAJOR.MINOR.PATCH, and `effectloader.cpp`
#: (`factory`) refuses a plugin with any other id, saying "was built for a different version of
#: KWin and needs to be rebuilt" -- a warning in the journal from 6.8, a debug line in 6.7 (read in
#: both sources). So 6.8.2 does not run a build for 6.8.1. The id is plain text in the plugin's
#: file: measured `6.7.5` in both `better_blur_dx.so` and `libkwin.so.6` on Fedora, and `6.8.2` in
#: both on Arch. Klassy's decoration plugin has another id, `org.kde.KPluginFactory`, which names
#: no version (measured), so the tag is the blur's alone. An id that changes shape finds no tag,
#: and the words fall back to the usual cause.
EFFECT_IID = b"org.kde.kwin.EffectPluginFactory"
#: The tag. In the plugin's metadata the next byte is the next key's, `\x03` (measured), never a
#: digit, so the patch number ends where the digits do.
_TAG = re.compile(re.escape(EFFECT_IID) + rb"(\d+)\.(\d+)\.(\d+)")
#: Far more than any effect is: the blur's file is 184 KB (2.5.1, measured).
_TAG_READ_LIMIT = 64 * 1024 * 1024


def built_for(path: str) -> tuple[int, ...] | None:
    """The version of KWin the compiled effect at `path` was built for, as numbers -- `(6, 8, 1)`
    -- or None when its file has no tag or cannot be read (`EFFECT_IID`)."""
    try:
        with open(path, "rb") as fh:
            found = _TAG.search(fh.read(_TAG_READ_LIMIT))
    except OSError:
        return None
    return tuple(int(n) for n in found.groups()) if found else None


#: The AUR helpers whose commands the box gives, in the order they are looked for: paru first, the
#: one KyprX's own install line runs (`update.ARCH_LINE`).
AUR_HELPERS = ("paru", "yay")


def aur_helper() -> str:
    """The first of `AUR_HELPERS` installed here, or "" for none -- which the AUR's own way, a
    clone and `makepkg`, then stands in for."""
    return next((helper for helper in AUR_HELPERS if shutil.which(helper)), "")


def machine() -> Machine:
    """This machine, as it is now. The compositor's support information is asked once, for both
    the decoration it draws with and its version."""
    info = reloader.support_information()
    system = about.system()
    return Machine(system=system, kwin=kconfig.KConfig(writer.KWINRC),
                   data_dirs=about.data_dirs(), plugin_dirs=qt_plugin_dirs(),
                   effects=reloader.effects_known(),
                   decoration=None if info is None else reloader.decoration_in(info),
                   package_version=package_version,
                   kwin_version=None if info is None else reloader.version_in(info),
                   package_owner=package_owner,
                   aur_helper=aur_helper() if system == about.ARCH else "")


def _metadata_version(m: Machine, leaf: str) -> tuple[bool, str]:
    """Is the package at `leaf` in a data folder, and which version does its metadata give?"""
    for base in m.data_dirs:
        path = os.path.join(base, leaf)
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    return True, str(((json.load(fh) or {}).get("KPlugin") or {}).get("Version") or "")
            except (OSError, ValueError, AttributeError):
                return True, ""
    return False, ""


def _plugin_paths(m: Machine, leaf: str) -> list[str]:
    """Every copy of the plugin file at `leaf`, in the order the plugin folders are searched.

    A copy is a file, not a spelling of one: on Arch `/usr/lib64` is a link to `lib` (measured in
    an Arch container), so the folders searched hold both `/usr/lib/qt6/plugins` and
    `/usr/lib64/qt6/plugins`, and the one file found through both would read in `facts` as a
    second copy the compositor might load instead. The first spelling found is the one kept."""
    out: list[str] = []
    seen: set[str] = set()
    for path in (os.path.join(base, leaf) for base in m.plugin_dirs):
        real = os.path.realpath(path)
        if real not in seen and os.path.isfile(path):
            seen.add(real)
            out.append(path)
    return out


def _has_plugin_file(m: Machine, leaf: str) -> bool:
    return bool(_plugin_paths(m, leaf))


#: The compiled plugin's file of each project that has one.
PLUGIN_FILES = {"klassy": klassy.DECORATION_PLUGIN_FILE, "blur": effects.BLUR_PLUGIN_FILE}


def _dotted(version: tuple) -> str:
    return ".".join(str(n) for n in version)


def _owner(project: Project, m: Machine) -> str:
    """The package to name for the project: the one that owns its plugin's first copy where the
    machine can say, the AUR's name otherwise."""
    paths = _plugin_paths(m, PLUGIN_FILES[project.key]) if project.key in PLUGIN_FILES else []
    found = m.package_owner(paths[0]) if paths and callable(m.package_owner) else ""
    return found or project.packages.get(about.ARCH, "")


def _built(project: Project, m: Machine) -> tuple[int, ...] | None:
    """The KWin the blur's first copy was built for (`built_for`); None for the others, which
    carry no tag. The first copy, because that is the order the folders are searched in -- the
    compositor's own plugin path can differ from this process's, and `facts` lists every copy."""
    if project.key != "blur":
        return None
    paths = _plugin_paths(m, effects.BLUR_PLUGIN_FILE)
    return built_for(paths[0]) if paths else None


def _build_case(built: tuple | None, running: tuple | None) -> str:
    """`older`, `newer` or `same`: the KWin a plugin was built for against the one running. ""
    when either is not known."""
    if not built or not running or len(running) < 3:
        return ""
    built, running = tuple(built)[:3], tuple(running)[:3]
    if built < running:
        return "older"
    if built > running:
        return "newer"
    return "same"


def _raw_switch(m: Machine, plugin: str) -> str:
    """The effect's on-and-off switch as `kwinrc` spells it, `absent` when the file does not."""
    raw = m.kwin.get(effects.PLUGINS_GROUP, f"{plugin}Enabled")
    if raw is None or raw is kconfig.NO_VALUE:
        return "absent"
    return str(raw)


def _metadata_words(m: Machine, leaf: str) -> str:
    """`metadata found, version X` -- or `not found` -- for the end of a `facts` line."""
    found, version = _metadata_version(m, leaf)
    if not found:
        return "metadata not found"
    return f"metadata found, version {version}" if version else "metadata found"


def _state(project: Project, m: Machine) -> tuple[str, str]:
    """(state, version) of one project on this machine."""
    listed, loaded = m.effects if m.effects is not None else (None, None)
    if project.key == "klassy":
        installed = (_has_plugin_file(m, klassy.DECORATION_PLUGIN_FILE)
                     or m.decoration == klassy.DECORATION)
        version = m.package_version(project.packages[about.ARCH if m.system == about.ARCH
                                                     else about.FEDORA]) if installed else ""
        if not installed:
            return MISSING, ""
        wanted = m.kwin.get("org.kde.kdecoration2", "library") == klassy.DECORATION
        if wanted and m.decoration is not None and m.decoration != klassy.DECORATION:
            return NOT_RUNNING, version
        return OK, version
    if project.key == "blur":
        installed = (project.plugin in listed if listed is not None
                     else _has_plugin_file(m, effects.BLUR_PLUGIN_FILE))
        if not installed:
            return MISSING, ""
        version = m.package_version(project.packages[about.ARCH if m.system == about.ARCH
                                                     else about.FEDORA])
        if (loaded is not None and effects.plugin_enabled(m.kwin, project.plugin)
                and project.plugin not in loaded):
            return NOT_RUNNING, version
        return OK, version
    if project.key == "animation":
        found, version = _metadata_version(m, effects.GEOMETRY_METADATA)
        # What the compositor can load is what counts, as for the blur: KWin 6.8 looks for a
        # scripted effect only under `kwin/effects`, 6.4 to 6.7 under `kwin-wayland/effects` too
        # (`ScriptedEffectLoader`, read in both sources), so a package where this compositor does
        # not look is not there for it. The file says the version, and decides when the compositor
        # cannot be asked.
        installed = project.plugin in listed if listed is not None else found
        if not installed:
            return MISSING, ""
        if (loaded is not None and effects.plugin_enabled(m.kwin, project.plugin)
                and project.plugin not in loaded):
            return NOT_RUNNING, version
        return OK, version
    # The video plugin.
    installed, version = _metadata_version(
        m, f"plasma/wallpapers/{project.plugin}/metadata.json")
    if not installed:
        return MISSING, ""
    if project.minimum and wallpaper.version_below(version, project.minimum):
        return TOO_OLD, version
    return OK, version


def _detail(project: Project, state: str, version: str, m: Machine,
            built: tuple | None = None) -> str:
    if state == MISSING:
        return f"{project.name} is not installed: without it KyprX has no {project.purpose}."
    if state == NOT_RUNNING:
        case = _build_case(built, m.kwin_version)
        if case in ("older", "newer"):
            return (f"{project.name} is installed, but the compositor is not running it: it was "
                    f"built for KWin {_dotted(built)}, and this session runs KWin "
                    f"{_dotted(m.kwin_version)}.")
        if case == "same":
            return (f"{project.name} is installed and built for this KWin, "
                    f"{_dotted(m.kwin_version)}, but the compositor is not running it, so there is "
                    f"no {project.purpose}.")
        return (f"{project.name} is installed, but the compositor is not running it, so there is no "
                f"{project.purpose}.")
    if state == TOO_OLD:
        return (f"{project.name} {version} is installed, and KyprX needs {project.minimum} or "
                f"newer.")
    return ""


def _aur_command(package: str, m: Machine, again: bool = False) -> str:
    """The command that builds `package` from the AUR and installs it, with the helper this machine
    has (`Machine.aur_helper`); `again` builds it even where that version is installed already.

    With paru, `paru -S --rebuild aur/<package>`, each part measured in an Arch container with
    paru 2.2.0. A plain `paru -S` builds nothing: paru keeps the package it built in
    `~/.cache/paru/clone`, and for the same version it says "is up to date -- skipping build",
    installs that old build again and exits 0. `--rebuild` builds it, and `--rebuild=yes` is the
    same flag spelt out. `aur/` is what keeps it the AUR's: with a pacman repository enabled that
    carries the same name -- a local one, standing in for Chaotic-AUR -- both other forms put that
    repository's binary back, and only this one built. yay 13.1.0 the same, measured the same way:
    a plain `yay -S` says "already made -- skipping build" and installs the old build again,
    `--rebuild` builds, and with the stand-in repository only `--rebuild aur/` built.

    With neither, the AUR's own way, as one line fish, bash and zsh read alike -- the shape of
    `update.ARCH_LINE`: a clone in a folder of its own, `makepkg -si` in it, and the folder
    removed. A fresh clone holds no earlier build, so it builds whether or not `again`.
    """
    if m.aur_helper in AUR_HELPERS:
        return f"{m.aur_helper} -S {'--rebuild aur/' if again else ''}{package}"
    return (f"bash -c 'build=$(mktemp -d) && git clone https://aur.archlinux.org/{package}.git "
            f"\"$build\" && cd \"$build\" && makepkg -si; rm -rf \"${{build:?}}\"'")


def _build_again(project: Project, m: Machine) -> tuple[str, str]:
    """How to build a compiled plugin again for the KWin running, on this system, and the command
    in it alone ("" where there is none).

    On Arch the AUR's build again (`_aur_command`). Then a new session, because the compositor
    loads its effects as it starts: the AUR package says, as it installs, "After updating this
    effect, log out and back in to restart KWin and load it", and the answer in Better Blur DX's
    issue #131 was the same rebuild and a new session.
    """
    if m.system == about.ARCH:
        command = _aur_command(_owner(project, m), m, again=True)
        return f"Build it again for this KWin: {command}, then log out and back in", command
    if m.system in (about.FEDORA, about.FEDORA_ATOMIC):
        command = "sudo dnf upgrade" if m.system == about.FEDORA else "rpm-ostree upgrade"
        then = "log out and back in" if m.system == about.FEDORA else "restart the computer"
        return (f"Its repository publishes a build for each Plasma release; once it has, "
                f"update: {command}, then {then}"), command
    return f"Build it again for this KWin ({project.url}), then log out and back in", ""


#: The blur's lines in the compositor's log. The effect starts every line it writes with its id --
#: `better_blur_dx: Effect supported` at each login here, `Effect unsupported: ...` when it
#: refuses to run (its `supported`, read in 2.6.0's source) -- and KWin names it when its library
#: will not load (`Did not get KPluginFactory for`, read in 6.8's `effectloader.cpp`).
BLUR_LOG = f"journalctl --user -b | grep {effects.BLUR_PLUGIN}"


def _fix(project: Project, state: str, m: Machine,
         built: tuple | None = None) -> tuple[str, str]:
    """What to do on this system, said as the command to run where there is one -- and that
    command alone, for the box's *Copy the command*, or "" where the words carry none."""
    system = m.system
    package = project.packages.get(about.ARCH if system == about.ARCH else about.FEDORA, "")
    if state == NOT_RUNNING:
        if project.key not in PLUGIN_FILES:
            # Geometry Change is a script, read by the compositor as it is: nothing in it is
            # built for one KWin, so the usual cause is not its.
            log = f"journalctl --user -b | grep {project.plugin}"
            return (f"It is a script, so there is nothing to build again for this KWin; the "
                    f"compositor's log may say why it did not load it: {log}"), log
        case = _build_case(built, m.kwin_version)
        if case == "older":
            return _build_again(project, m)
        if case == "newer":
            return ("This session still runs the KWin from before the last update: log out and "
                    "back in"), ""
        if case == "same":
            # A build made during this session is one the compositor has not tried yet: it
            # loads an effect as it starts, so the tag can match while the build it refused was
            # the one before.
            return (f"Not a version mismatch: if it was built again since you logged in, log out "
                    f"and back in; otherwise building it again does not help, and {BLUR_LOG} "
                    f"says why"), BLUR_LOG
        again, command = _build_again(project, m)
        said = f"Most often it was built for another version of KWin. {again}"
        if project.key == "blur":
            said += f". If it still does not run, {BLUR_LOG} says why"
        return said, command
    if state in (MISSING, TOO_OLD):
        if system == about.FEDORA and package:
            command = f"sudo dnf {'install' if state == MISSING else 'upgrade'} {package}"
            return command, command
        if system == about.FEDORA_ATOMIC and package:
            command = (f"rpm-ostree install {package}" if state == MISSING
                       else "rpm-ostree upgrade")
            return f"{command}, then restart the computer", command
        if system == about.ARCH and package:
            command = _aur_command(package, m)
            return command, command
        return f"Install it from {project.url}", ""
    return "", ""


def assess(m: Machine) -> list[Need]:
    """Every project, as it stands on the machine `m` describes."""
    out = []
    for project in PROJECTS:
        state, version = _state(project, m)
        # The plugin's file is read only for one that is not running.
        built = _built(project, m) if state == NOT_RUNNING else None
        fix, command = _fix(project, state, m, built)
        out.append(Need(key=project.key, name=project.name, purpose=project.purpose,
                        plugin=project.plugin, url=project.url, state=state, version=version,
                        detail=_detail(project, state, version, m, built), fix=fix,
                        command=command))
    return out


def check() -> list[dict]:
    """Every project, as it stands on this machine now, as plain data for the bus."""
    return [asdict(need) for need in assess(machine())]


def facts(m: Machine) -> list[str]:
    """What each answer was built on, one line per project, for whoever asks why.

    Each line names only what that project's answer used -- the file that was looked for, what the
    compositor answered, the switch's raw value -- so a state that surprises somebody can be
    traced to the fact it came from. The blur's names every copy of its file, each with the KWin it
    was built for and the package that owns it, because the answer reads the first copy and the
    compositor may load another. A line before them says which KWin runs, and on Arch one more
    which AUR helper the commands are given for. Writes nothing; `main`
    prints these under `--facts`, and the daemon and the window never ask for them.
    """
    listed, loaded = m.effects if m.effects is not None else (None, None)

    def among(name: str, effects_list) -> str:
        """`yes` or `no` for a list the compositor answered with, `cannot be asked` for None."""
        if effects_list is None:
            return "cannot be asked"
        return "yes" if name in effects_list else "no"

    def effect_line(project: Project, tail: str) -> str:
        return (f"{project.name}: listed by the compositor {among(project.plugin, listed)}; "
                f"running {among(project.plugin, loaded)}; "
                f"switch in kwinrc {_raw_switch(m, project.plugin)}; {tail}")

    def copy_words(path: str) -> str:
        """`plugin file <path>, built for KWin 6.8.2, package <name>` for one copy."""
        built = built_for(path)
        owner = m.package_owner(path) if callable(m.package_owner) else ""
        return (f"plugin file {path}, "
                f"{f'built for KWin {_dotted(built)}' if built else 'no build tag found'}"
                f"{f', package {owner}' if owner else ''}")

    blur_files = _plugin_paths(m, effects.BLUR_PLUGIN_FILE)
    drawn = ("(cannot be asked)" if m.decoration is None
             else m.decoration or "(nothing named)")
    library = m.kwin.get("org.kde.kdecoration2", "library")
    _, blur, animation, video = PROJECTS
    lines = [
        f"system: {m.system}",
        f"KWin running: {_dotted(m.kwin_version) if m.kwin_version else '(cannot be asked)'}",
        f"Klassy: plugin file "
        f"{'found' if _has_plugin_file(m, klassy.DECORATION_PLUGIN_FILE) else 'not found'}; "
        f"the compositor draws with {drawn}; "
        f"kwinrc asks for {library if library not in (None, kconfig.NO_VALUE) else '(nothing)'}",
        effect_line(blur, "; ".join(copy_words(path) for path in blur_files)
                    or "plugin file not found"),
        effect_line(animation, _metadata_words(m, effects.GEOMETRY_METADATA)),
        f"{video.name}: "
        f"{_metadata_words(m, f'plasma/wallpapers/{video.plugin}/metadata.json')}",
    ]
    if m.system == about.ARCH:
        lines.insert(2, f"AUR helper: {m.aur_helper or 'none, so the AUR clone and makepkg'}")
    return lines


def main() -> int:
    m = machine()
    if "--facts" in sys.argv[1:]:
        for line in facts(m):
            print(f"  {line}")
    wrong = [n for n in assess(m) if n.state != OK]
    for n in wrong:
        print(f"  {n.detail}\n    {n.fix}")
    if not wrong:
        print("  all four projects KyprX is built on are installed and running")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
