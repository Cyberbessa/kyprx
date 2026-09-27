"""What KyprX needs on this machine: the five projects it is built on, whether each one is there,
which version, and whether the compositor is actually running it.

Every one of the five is required. KyprX is those five put to one use, and a desk without one of
them is not KyprX, so the packages install them with it. What is checked here is what can still
go wrong after that: one removed by hand; one never installed, because KyprX was installed from a
working tree; and the one that happens to everybody sooner or later -- a compiled plugin built for
the KWin that ran before the last Plasma update. The compositor then lists it and does not run it,
and the blur or the title bars simply stop, with nothing on screen saying why.

**How each one is found**, and why that way:

- Krohnkite, Geometry Change and the video plugin by their `metadata.json` in the data folders the
  desktop searches (`about.data_dirs`), which also carries their version. A file, not
  `kpackagetool6`: this is asked when a window opens, and a process started to draw a page is a
  page that stutters (`wallpaper.plugin_dir` says the same).
- Better Blur DX by the compositor's own list of the effects it can load, and whether it runs by
  the list of those it has loaded. Its file, in the folders Qt looks for plugins in, when the
  compositor cannot be asked.
- Klassy by its decoration plugin's file, and whether it runs by the decoration the compositor says
  it is drawing with -- while `kwinrc` asks for Klassy's. The compositor falls back to its own
  decoration when it cannot load the one asked for.
- The version of the two compiled ones from the package manager, which is the only thing that
  records it.

**Nothing here writes**, and the compositor is only asked questions: `scripts/buswatch.py` lets
exactly those through. The package managers' versions cost a process each, so the daemon keeps the
answer and works it out again only when asked to (`InstallationPart.needs`).

Run as a program -- `python3 daemon/requirements.py` -- it prints what is wrong and exits 1, or says
all five are there and exits 0. `install.sh` runs it before installing anything.
"""

from __future__ import annotations

import glob
import json
import os
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
    """One of the five, as KyprX knows it."""
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
    Project("tiling", "Krohnkite", "tiling", effects.TILING_PLUGIN,
            "https://codeberg.org/anametologin/Krohnkite",
            {about.FEDORA: "kwin-scripts-krohnkite", about.ARCH: "kwin-scripts-krohnkite"}),
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


def qt_plugin_dirs() -> list[str]:
    """The folders Qt looks for plugins in: `QT_PLUGIN_PATH`, then each system layout's own."""
    found = [p for p in os.environ.get("QT_PLUGIN_PATH", "").split(":") if p]
    found += sorted(glob.glob("/usr/lib*/qt6/plugins")) + sorted(glob.glob("/usr/lib/*/qt6/plugins"))
    out: list[str] = []
    for path in found:
        if path not in out and os.path.isdir(path):
            out.append(path)
    return out


def package_version(name: str) -> str:
    """The version the package manager records for `name`, or "" when it records none.

    `rpm` first and then `pacman`, whichever is installed and knows the package: an Arch system may
    carry `rpm` with nothing in its database, and then it simply knows nothing.
    """
    for argv in (["rpm", "-q", "--qf", "%{VERSION}", name], ["pacman", "-Q", name]):
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
            # `klassy 1:6.7.3-1`: the version, without the epoch and without the release.
            text = text.split()[-1].split(":")[-1].rsplit("-", 1)[0]
        return text
    return ""


def machine() -> Machine:
    """This machine, as it is now."""
    return Machine(system=about.system(), kwin=kconfig.KConfig(writer.KWINRC),
                   data_dirs=about.data_dirs(), plugin_dirs=qt_plugin_dirs(),
                   effects=reloader.effects_known(), decoration=reloader.decoration_running(),
                   package_version=package_version)


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


def _has_plugin_file(m: Machine, leaf: str) -> bool:
    return any(os.path.isfile(os.path.join(base, leaf)) for base in m.plugin_dirs)


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
        installed, version = _metadata_version(m, effects.GEOMETRY_METADATA)
        if not installed:
            return MISSING, ""
        if (loaded is not None and effects.plugin_enabled(m.kwin, project.plugin)
                and project.plugin not in loaded):
            return NOT_RUNNING, version
        return OK, version
    if project.key == "tiling":
        installed, version = _metadata_version(m, effects.TILING_METADATA)
        return (OK if installed else MISSING), version
    # The video plugin.
    installed, version = _metadata_version(
        m, f"plasma/wallpapers/{project.plugin}/metadata.json")
    if not installed:
        return MISSING, ""
    if project.minimum and wallpaper.version_below(version, project.minimum):
        return TOO_OLD, version
    return OK, version


def _detail(project: Project, state: str, version: str) -> str:
    if state == MISSING:
        return f"{project.name} is not installed: without it KyprX has no {project.purpose}."
    if state == NOT_RUNNING:
        return (f"{project.name} is installed, but the compositor is not running it, so there is no "
                f"{project.purpose}.")
    if state == TOO_OLD:
        return (f"{project.name} {version} is installed, and KyprX needs {project.minimum} or "
                f"newer.")
    return ""


def _fix(project: Project, state: str, system: str) -> str:
    """What to do on this system, said as the command to run where there is one."""
    package = project.packages[about.ARCH if system == about.ARCH else about.FEDORA]
    if state == NOT_RUNNING:
        if system == about.ARCH:
            return (f"It was built for another version of KWin. Build it again for this one: "
                    f"paru -S {package}")
        if system in (about.FEDORA, about.FEDORA_ATOMIC):
            again = ("sudo dnf upgrade" if system == about.FEDORA
                     else "rpm-ostree upgrade, then restart the computer")
            return (f"It was built for another version of KWin. Its repository publishes a build "
                    f"for each Plasma release; once it has, update: {again}")
        return f"It was built for another version of KWin: build it again ({project.url})."
    if state in (MISSING, TOO_OLD):
        if system == about.FEDORA:
            verb = "install" if state == MISSING else "upgrade"
            return f"sudo dnf {verb} {package}"
        if system == about.FEDORA_ATOMIC:
            if state == MISSING:
                return f"rpm-ostree install {package}, then restart the computer"
            return "rpm-ostree upgrade, then restart the computer"
        if system == about.ARCH:
            return f"paru -S {package}"
        return f"Install it from {project.url}"
    return ""


def assess(m: Machine) -> list[Need]:
    """Every project, as it stands on the machine `m` describes."""
    out = []
    for project in PROJECTS:
        state, version = _state(project, m)
        out.append(Need(key=project.key, name=project.name, purpose=project.purpose,
                        plugin=project.plugin, url=project.url, state=state, version=version,
                        detail=_detail(project, state, version),
                        fix=_fix(project, state, m.system)))
    return out


def check() -> list[dict]:
    """Every project, as it stands on this machine now, as plain data for the bus."""
    return [asdict(need) for need in assess(machine())]


def main() -> int:
    wrong = [n for n in assess(machine()) if n.state != OK]
    for n in wrong:
        print(f"  {n.detail}\n    {n.fix}")
    if not wrong:
        print("  all five projects KyprX is built on are installed and running")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
