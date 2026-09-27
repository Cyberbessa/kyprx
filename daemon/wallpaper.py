"""The wallpaper: what there is to choose from, and asking the shell to change it.

**Nothing here writes a config file, and that is the whole design.** The wallpaper lives in
`plasma-org.kde.plasma.desktop-appletsrc`, which the shell owns and rewrites on its way out of the
session -- so editing it while a session is running is a change that silently undoes itself. It is
the same trap the global shortcut registry has, and it has the same answer: ask the owner. The
shell's `evaluateScript` is that door, and it is the one the desktop's own
`plasma-apply-wallpaperimage` goes through.

Three things that were measured rather than assumed:

* **The bus name is `org.kde.plasmashell`, lower case.** `org.kde.PlasmaShell` is the interface on
  `/PlasmaShell`, not a service; asking for it as one fails.
* **`desktopsForActivity(currentActivity())` is what keeps one activity out of another's way.**
  `desktops()` -- what the desktop's own command uses -- returns every activity's desktop, so a
  machine with two activities loses the difference between them on the first change.
* **The video plugin only switches video when exactly one is enabled.** Its `onVideoUrlsChanged`
  stops on an empty list and calls `next()` on a list of one; with two or more it recalculates and
  changes nothing at all. So choosing a video is written as "enable that one, disable the rest",
  which leaves the list -- and the per-video settings in it -- untouched, and is also the only
  spelling that has any visible effect.

URLs are built the way the two plugins already spell them: a `file://` and then the path as it is,
with only the three characters that genuinely end a URL escaped. That is not laziness. The video
plugin writes its own list with raw spaces and a raw colon in it, and an entry spelled any other way
would not match the entry already there -- it would be appended beside it as a second row for the
same file, and the desktop would end up with two.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from urllib.parse import unquote

import dbus

SERVICE = "org.kde.plasmashell"
PATH = "/PlasmaShell"
IFACE = "org.kde.PlasmaShell"

#: The desktop's own image plugin, and the third-party one for video.
IMAGE_PLUGIN = "org.kde.image"
VIDEO_PLUGIN = "luisbocanegra.smart.video.wallpaper.reborn"

#: The shell's own config: each desktop's wallpaper, and which plugin draws it. Never opened here --
#: the shell is asked -- but the daemon watches it change (`watch_the_desktop`).
APPLETSRC = "~/.config/plasma-org.kde.plasma.desktop-appletsrc"

#: Where the desktop says the activity in use changed, which changes the plugin in use with it.
ACTIVITIES_IFACE = "org.kde.ActivityManager.Activities"
ACTIVITY_CHANGED = "CurrentActivityChanged"

#: The two the picker knows, by the word this app uses for each. Which of them is on is a fact
#: about the desktop and is never a setting of this app's -- see `mode_of`.
PLUGINS = {"image": IMAGE_PLUGIN, "video": VIDEO_PLUGIN}

#: The first release of Smart Video Wallpaper Reborn that fixes what this desk runs into: its
#: window tracking on Plasma 6.7, pausing for a full-screen window, and playing again after
#: *Show desktop*. Anything older is reported on the Settings tab. Read from the plugin's own
#: `metadata.json`; the fixes are in its 2.15.0 release notes.
VIDEO_PLUGIN_FIXED = "2.15.0"

#: What a script of ours prints in front of its answer. A reply that does not begin with it is a
#: failure however healthy the bus call looked -- the same two-sided test `gui/client.py` makes.
OK = "kyprx-ok"

#: Suffixes worth offering. Deliberately wider than what any one machine can decode: a file whose
#: preview cannot be built is still a file somebody may want as their wallpaper, and the interface
#: shows it with no picture rather than dropping it.
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".avif", ".jxl", ".heic", ".heif",
                  ".bmp", ".svg", ".svgz", ".tif", ".tiff")
VIDEO_SUFFIXES = (".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".wmv", ".flv")

#: `WIDTHxHEIGHT.ext` -- how a wallpaper package names the images inside it.
SIZE_RE = re.compile(r"^(\d+)x(\d+)\b")


class WallpaperError(Exception):
    """The shell could not be reached, or would not do it."""


# ---------------------------------------------------------------- talking to the shell

def _shell():
    return dbus.Interface(dbus.SessionBus().get_object(SERVICE, PATH), IFACE)


def _evaluate(script: str) -> str:
    """Run a script in the shell and return what it printed, minus the marker.

    Both ways of failing count. The bus can refuse the call, and the script can run and print
    something that is not ours -- which is what an error inside it looks like from here.
    """
    try:
        reply = str(_shell().evaluateScript(script)).strip()
    except dbus.DBusException as e:
        raise WallpaperError(f"the desktop shell did not answer: {e}") from e
    if not reply.startswith(OK):
        raise WallpaperError(f"the desktop shell refused: {reply or 'it said nothing'}")
    return reply[len(OK):]


def _js(value) -> str:
    """A Python value as a JavaScript literal.

    Through `json.dumps` and never through quotes written by hand. The desktop's own wallpaper
    command carries a whole error message about a single quote in a file name; the video folder on
    this machine has spaces and a colon in its path. A literal built by escaping properly cannot
    have that class of bug.
    """
    return json.dumps(value, ensure_ascii=True)


_READ = """
var out = [];
var ds = desktopsForActivity(currentActivity());
for (var i = 0; i < ds.length; i++) {
    var d = ds[i];
    var row = { id: String(d.id), plugin: String(d.wallpaperPlugin) };
    d.currentConfigGroup = ["Wallpaper", %(image)s, "General"];
    row.image = String(d.readConfig("Image"));
    d.currentConfigGroup = ["Wallpaper", %(video)s, "General"];
    row.videos = String(d.readConfig("VideoUrls"));
    row.last = String(d.readConfig("LastVideo"));
    row.change = String(d.readConfig("ChangeWallpaperMode"));
    row.pause = String(d.readConfig("PauseMode"));
    out.push(row);
}
print(%(ok)s + JSON.stringify({ activity: String(currentActivity()), desktops: out }));
"""


#: Every activity, by id and by name, with the same reading of each of its desktops that `_READ`
#: gives for the one in use. What the KyprX folder and a copy of the desk carry: the activity in use
#: alone would change the folder every time somebody switched activity, and on a second machine
#: sharing the folder it would put one activity's wallpaper on another.
_READ_ALL = """
var out = [];
var ids = activities();
for (var a = 0; a < ids.length; a++) {
    var rows = [];
    var ds = desktopsForActivity(ids[a]);
    for (var i = 0; i < ds.length; i++) {
        var d = ds[i];
        var row = { id: String(d.id), plugin: String(d.wallpaperPlugin) };
        d.currentConfigGroup = ["Wallpaper", %(image)s, "General"];
        row.image = String(d.readConfig("Image"));
        d.currentConfigGroup = ["Wallpaper", %(video)s, "General"];
        row.videos = String(d.readConfig("VideoUrls"));
        row.last = String(d.readConfig("LastVideo"));
        row.change = String(d.readConfig("ChangeWallpaperMode"));
        row.pause = String(d.readConfig("PauseMode"));
        rows.push(row);
    }
    out.push({ activity: String(ids[a]), name: String(activityName(ids[a])),
               current: String(ids[a]) === String(currentActivity()), desktops: rows });
}
print(%(ok)s + JSON.stringify({ activities: out }));
"""


def _activity(activity: str | None) -> str:
    """The activity a write script reaches, as JavaScript: the one named, or -- what the picker and
    the Wallpaper tab always mean -- the one in use when the script runs."""
    return _js(activity) if activity else "currentActivity()"


def snapshot_all() -> list[dict]:
    """Every activity's desktops, each in the shape `snapshot` answers with for the one in use, plus
    its `name` and whether it is `current`. A read."""
    answer = _evaluate(_READ_ALL % {"image": _js(IMAGE_PLUGIN), "video": _js(VIDEO_PLUGIN),
                                    "ok": _js(OK)})
    try:
        found = json.loads(answer)
    except json.JSONDecodeError as e:
        raise WallpaperError(f"the desktop shell answered something unreadable: {e}") from e
    return [a for a in found.get("activities") or [] if isinstance(a, dict)]


def snapshot() -> dict:
    """What the desktops of the activity in use have on them right now.

    A read, so it happens in dry run too -- reading the session is not a change to it.
    """
    answer = _evaluate(_READ % {"image": _js(IMAGE_PLUGIN), "video": _js(VIDEO_PLUGIN),
                                "ok": _js(OK)})
    try:
        state = json.loads(answer)
    except json.JSONDecodeError as e:
        raise WallpaperError(f"the desktop shell answered something unreadable: {e}") from e
    if not state.get("desktops"):
        raise WallpaperError("the activity in use has no desktop to put a wallpaper on")
    return state


# ---------------------------------------------------------------- what there is to choose from

#: The three characters that end a URL where they stand, and so are the only ones escaped. `%`
#: is first in the table because it is the escape itself; `str.translate` makes one pass over the
#: original, so nothing written here can be escaped twice.
_ESCAPE = str.maketrans({"%": "%25", "#": "%23", "?": "%3F"})


def to_url(path: str) -> str:
    """A local path as the two plugins spell it. See the note at the top of this file."""
    return "file://" + os.path.abspath(path).translate(_ESCAPE)


def to_path(url: str) -> str:
    """The local path a `file://` URL names, whichever way round it was spelled."""
    if not url.startswith("file://"):
        return url
    return unquote(url[len("file://"):])


def picture_for(target: str) -> str:
    """The image file behind a target, for anything that needs pixels rather than a URL.

    A target is not always a file: a wallpaper package is a **directory**, written with a trailing
    slash so the plugin can pick the resolution and the light or dark variant itself. Which one it
    actually shows is therefore its decision and not ours, and the biggest picture in the package
    is the closest thing to an answer available from outside it.
    """
    path = to_path(target)
    if not path:
        return ""
    if os.path.isdir(path):
        return _preview_of(path)
    return path if os.path.exists(path) else ""


def wallpaper_dirs() -> list[str]:
    """Every directory the desktop's own wallpaper chooser looks in, in its order."""
    home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    rest = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    out: list[str] = []
    seen: set[str] = set()
    for base in [home] + rest.split(":"):
        if not base:
            continue
        for sub in ("wallpapers", "backgrounds"):
            path = os.path.join(base, sub)
            # Kept as the session spells it, and only compared as what it really points at. On a
            # layout where `/home` is a link to `/var/home`, resolving the path outright writes a URL
            # nobody else on this desktop writes -- it works, and it stops matching the one already in
            # the config, which turns "it is already that" into a change written every single time.
            real = os.path.realpath(path)
            if os.path.isdir(path) and real not in seen:
                seen.add(real)
                out.append(path)
    return out


def plugin_dir(plugin: str) -> str:
    """Where this wallpaper plugin is installed, the user's copy first, or "" when it is not.

    Looked for as a directory rather than asked of `kpackagetool6`, because this is called to draw
    a settings page and starting a process to draw a page is a page that stutters.
    """
    home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    rest = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    for base in [home] + rest.split(":"):
        path = os.path.join(base, "plasma", "wallpapers", plugin) if base else ""
        if path and os.path.isdir(path):
            return path
    return ""


def plugin_installed(plugin: str) -> bool:
    """Is this wallpaper plugin on the machine at all?"""
    return bool(plugin_dir(plugin))


def plugin_version(plugin: str) -> str:
    """The installed plugin's own version, from its `metadata.json`, or "" when there is none."""
    path = plugin_dir(plugin)
    try:
        with open(os.path.join(path, "metadata.json"), encoding="utf-8") as fh:
            return str(((json.load(fh) or {}).get("KPlugin") or {}).get("Version") or "")
    except (OSError, ValueError, AttributeError):
        return ""


def version_below(version: str, floor: str) -> bool:
    """Is `version` older than `floor`? Numbers compared part by part; "" is never below."""
    def parts(v):
        return [int(p) for p in re.findall(r"\d+", v)]
    return bool(version) and parts(version) < parts(floor)


def _package_name(package: str) -> str | None:
    """A package's name in this session's language, or None if it is not a package.

    `metadata.json` is the current shape and carries a name per language. Some packages still ship
    the old `metadata.desktop` beside it, and a few ship only that -- so both are read, in that
    order. A package with neither is not a package; that is how a directory that merely *contains*
    packages is told apart from one that is one.
    """
    languages = [lang for lang in (os.environ.get("LANG", "").split(".")[0],
                                   os.environ.get("LANG", "").split("_")[0]) if lang]
    meta = os.path.join(package, "metadata.json")
    if os.path.isfile(meta):
        try:
            with open(meta, encoding="utf-8") as fh:
                plugin = (json.load(fh) or {}).get("KPlugin") or {}
        except (OSError, json.JSONDecodeError, AttributeError):
            plugin = {}
        for lang in languages:
            if plugin.get(f"Name[{lang}]"):
                return str(plugin[f"Name[{lang}]"])
        return str(plugin.get("Name") or plugin.get("Id") or os.path.basename(package))
    old = os.path.join(package, "metadata.desktop")
    if os.path.isfile(old):
        found = {}
        try:
            with open(old, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    key, sep, value = line.partition("=")
                    if sep and key.strip().startswith("Name"):
                        found[key.strip()] = value.strip()
        except OSError:
            pass
        for lang in languages:
            if found.get(f"Name[{lang}]"):
                return found[f"Name[{lang}]"]
        return found.get("Name") or os.path.basename(package)
    return None


def _images_in(package: str) -> list[str]:
    for sub in ("contents/images", "contents/images_dark"):
        folder = os.path.join(package, sub)
        if not os.path.isdir(folder):
            continue
        files = [os.path.join(folder, n) for n in sorted(os.listdir(folder))
                 if n.lower().endswith(IMAGE_SUFFIXES)]
        if files:
            return files
    return []


def _preview_of(package: str) -> str:
    """The biggest image in a package, for the picture the interface draws.

    Biggest, because the picture is drawn small and scaled down beats scaled up. The light set is
    preferred over the dark one: which of them the desktop ends up using is the plugin's decision,
    and this is only a thumbnail.
    """
    files = _images_in(package)
    if not files:
        return ""

    def area(path: str) -> int:
        match = SIZE_RE.match(os.path.basename(path))
        return int(match.group(1)) * int(match.group(2)) if match else 0

    best = max(files, key=area)
    if area(best):
        return best
    # No resolution in any name, so there is nothing to compare but the files themselves.
    try:
        return max(files, key=lambda p: os.path.getsize(p))
    except OSError:
        return files[0]


def _entry(kind: str, identifier: str, name: str, target: str, preview: str) -> dict:
    return {"kind": kind, "id": identifier, "name": name, "target": target, "preview": preview}


def _package_entry(package: str) -> dict | None:
    name = _package_name(package)
    if name is None or not _images_in(package):
        return None
    # The **directory** is what is written, with the slash the desktop writes, not an image inside
    # it. That is what lets the plugin pick the resolution and the light or dark variant itself.
    return _entry("image", package, name, to_url(package) + "/", _preview_of(package))


def scan_images(image_dir: str = "") -> list[dict]:
    """Every wallpaper the desktop's own chooser would offer, in three shapes, plus image_dir.

    A package; a loose image file sitting in the wallpapers directory, which distributions really
    do ship; and a directory of packages, which is one level deeper than the format says and which
    this machine has. Descending exactly one level covers it without turning this into a walk of
    the whole data directory.
    """
    out: dict[str, dict] = {}
    folders = list(wallpaper_dirs())
    if image_dir and os.path.isdir(image_dir):
        real_img = os.path.realpath(image_dir)
        if real_img not in [os.path.realpath(d) for d in folders]:
            folders.insert(0, image_dir)
    for folder in folders:
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            continue
        for name in names:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                if name.lower().endswith(IMAGE_SUFFIXES):
                    out.setdefault(path, _entry("image", path, os.path.splitext(name)[0],
                                                to_url(path), path))
                continue
            if not os.path.isdir(path):
                continue
            entry = _package_entry(path)
            if entry is not None:
                out.setdefault(path, entry)
                continue
            try:
                nested = sorted(os.listdir(path))
            except OSError:
                continue
            for inner in nested:
                deeper = os.path.join(path, inner)
                if os.path.isdir(deeper):
                    entry = _package_entry(deeper)
                    if entry is not None:
                        out.setdefault(deeper, entry)
                elif os.path.isfile(deeper) and inner.lower().endswith(IMAGE_SUFFIXES):
                    out.setdefault(deeper, _entry("image", deeper, os.path.splitext(inner)[0],
                                                  to_url(deeper), deeper))
    return sorted(out.values(), key=lambda e: e["name"].lower())


def scan_videos(folder: str) -> list[dict]:
    """The videos in one folder. No recursion: a folder of wallpapers is a folder, not a tree."""
    if not folder or not os.path.isdir(folder):
        return []
    out = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if os.path.isfile(path) and name.lower().endswith(VIDEO_SUFFIXES):
            out.append(_entry("video", path, os.path.splitext(name)[0], to_url(path), ""))
    return out


def _known_videos(state: dict) -> list[dict]:
    """The video plugin's own list, from the first desktop that has one."""
    for desktop in state.get("desktops") or []:
        raw = desktop.get("videos") or ""
        try:
            parsed = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(parsed, list) and parsed:
            return [v for v in parsed if isinstance(v, dict)]
    return []


def default_video_dir(state: dict) -> str:
    """Where to look for videos when nobody has said.

    Taken from the machine rather than invented: the folder the videos the plugin already knows
    about live in, which is the folder somebody already chose once. Only when there are none does
    this fall back to the session's own videos directory.
    """
    counts: dict[str, int] = {}
    for video in _known_videos(state):
        folder = os.path.dirname(to_path(str(video.get("filename") or "")))
        if folder and os.path.isdir(folder):
            counts[folder] = counts.get(folder, 0) + 1
    if counts:
        return max(counts, key=lambda f: counts[f])
    for candidate in (_xdg_videos_dir(), os.path.expanduser("~/Videos")):
        if candidate and os.path.isdir(candidate):
            return candidate
    return ""


def _xdg_videos_dir() -> str:
    """The session's own videos directory, from the file the desktop keeps it in.

    Read from `user-dirs.dirs` rather than from the environment, because the variable is only
    exported into a shell that has sourced it -- which a D-Bus activated daemon has not.
    """
    path = os.path.join(os.environ.get("XDG_CONFIG_HOME")
                        or os.path.expanduser("~/.config"), "user-dirs.dirs")
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                key, sep, value = line.strip().partition("=")
                if sep and key.strip() == "XDG_VIDEOS_DIR":
                    return os.path.expandvars(value.strip().strip('"')).replace(
                        "$HOME", os.path.expanduser("~"))
    except OSError:
        pass
    return ""


def default_image_dir(state: dict | None = None) -> str:
    """Where to look for pictures when nobody has said.

    Taken from user-dirs.dirs (XDG_PICTURES_DIR), or ~/Pictures if it exists.
    """
    path = os.path.join(os.environ.get("XDG_CONFIG_HOME")
                        or os.path.expanduser("~/.config"), "user-dirs.dirs")
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                key, sep, value = line.strip().partition("=")
                if sep and key.strip() == "XDG_PICTURES_DIR":
                    d = os.path.expandvars(value.strip().strip('"')).replace(
                        "$HOME", os.path.expanduser("~"))
                    if os.path.isdir(d):
                        return d
    except OSError:
        pass
    pictures = os.path.expanduser("~/Pictures")
    if os.path.isdir(pictures):
        return pictures
    return ""


def catalogue(mode: str, video_dir: str, image_dir: str = "", state: dict | None = None) -> list[dict]:
    if mode == "video":
        return scan_videos(video_dir)
    return scan_images(image_dir)


def rotates(state: dict) -> bool:
    """Is the video plugin set to move on to another video by itself?

    Read and never written: `ChangeWallpaperMode` is somebody's choice about their desktop. But a
    picker that promises "this one, looping" while the plugin is on Slideshow or a timer is a
    picker that lies, so the interface is told and says so. 0 is Never, which is what the promise
    needs; anything else is not.
    """
    for desktop in state.get("desktops") or []:
        raw = str(desktop.get("change") or "")
        if raw and raw not in ("0", "false"):
            return True
    return False


def mode_of(state: dict) -> str:
    """Which kind of wallpaper the desktops of this activity are wearing: "image" or "video".

    **This is where the picker's mode comes from, and it is not stored anywhere.** The wallpaper
    plugin is a choice made per activity, in the shell's own config, by whoever opens *Desktop and
    Wallpaper* -- this app is one of several things that can change it. A copy kept in this app's
    settings could only ever be a second truth able to disagree with the first, and was one: two
    activities on this desk wear different plugins, and one stored word cannot be both.

    Derived rather than remembered is also what makes the two directions safe. There is no value
    to write back when the desktop changes, so a watcher cannot start a round of writes answering
    each other.

    The first desktop answers for the activity. Several screens can in principle disagree, and
    `plugin_plan` settles that by writing every desktop of the activity rather than by guessing
    which one meant it.
    """
    desktops = state.get("desktops") or []
    if not desktops:
        return ""
    return "video" if str(desktops[0].get("plugin")) == VIDEO_PLUGIN else "image"


def mode_for(target: str) -> str:
    """Which plugin can show this wallpaper. **The target decides, and nothing else does.**

    Not what the desktop happens to be wearing when the call arrives, and that is a correction.
    The picker is opened on one activity and Enter is pressed on whatever activity is in front a
    moment later -- and the two can wear different plugins, which is the whole reason the mode is
    read from the desktop rather than stored. Deciding by the desktop at that moment wrote an
    image file into the video plugin's `LastVideo`, which is a desktop showing nothing.

    A wallpaper package is a directory, so anything without a video suffix is an image -- the same
    way round as `catalogue`, which only ever offers videos from a folder of them.
    """
    path = to_path(target).rstrip("/")
    return "video" if os.path.splitext(path)[1].lower() in VIDEO_SUFFIXES else "image"


def current_target(mode: str, state: dict) -> str:
    """What is on the desktop now, in the same spelling an entry's `target` has."""
    desktops = state.get("desktops") or []
    if not desktops:
        return ""
    first = desktops[0]
    if mode == "video":
        return str(first.get("last") or "") if first.get("plugin") == VIDEO_PLUGIN else ""
    return str(first.get("image") or "") if first.get("plugin") == IMAGE_PLUGIN else ""


# ---------------------------------------------------------------- changing it

#: Setting the image. The config goes in **before** the plugin is named, and that order is the
#: same in both scripts below for the same reason -- see the note on the video one.
_WRITE_IMAGE = """
var ds = desktopsForActivity(%(activity)s);
for (var i = 0; i < ds.length; i++) {
    var d = ds[i];
    d.currentConfigGroup = ["Wallpaper", %(plugin)s, "General"];
    d.writeConfig("Image", %(target)s);
    d.wallpaperPlugin = %(plugin)s;
}
print(%(ok)s + ds.length);
"""

#: Setting the video. Three things here are the whole feature, and none of them is obvious.
#:
#: **The list is read and rewritten inside the shell, not out here.** Sending a list built from an
#: earlier read would write over whatever landed in between -- the contention `daemon/writer.py`
#: exists to refuse for files, in a place that transaction cannot reach.
#:
#: **Exactly one entry ends up enabled.** The plugin's `onVideoUrlsChanged` stops on an empty list
#: and switches on a list of one; with two or more it recalculates and **changes nothing, with no
#: error anywhere**. One enabled entry is also what makes it loop rather than advance, because its
#: player asks for an infinite loop whenever there is only one video. So this is not tidiness: it
#: is the only spelling that does what was asked, and "let me enable a few" puts the bug back.
#:
#: **The config is written before the plugin is named.** Coming from the image plugin, naming the
#: plugin first starts it on the previous `LastVideo` and only then switches -- a visible flash of
#: the video before last.
_WRITE_VIDEO = r"""
function norm(u) {
    try { u = decodeURIComponent(String(u)); } catch (e) { u = String(u); }
    return u.replace(/\/+$/, "");
}
var chosen = %(target)s;
var ds = desktopsForActivity(%(activity)s);
for (var i = 0; i < ds.length; i++) {
    var d = ds[i];
    d.currentConfigGroup = ["Wallpaper", %(plugin)s, "General"];
    var list;
    try { list = JSON.parse(d.readConfig("VideoUrls")); } catch (e) { list = []; }
    if (!Array.isArray(list)) { list = []; }
    var found = false;
    for (var j = 0; j < list.length; j++) {
        var same = norm(list[j].filename) === norm(chosen);
        list[j].enabled = same;
        if (same) { found = true; }
    }
    if (!found) {
        list.push({ filename: chosen, enabled: true, duration: 0, customDuration: 0,
                    playbackRate: 0, alternativePlaybackRate: 0, loop: false });
    }
    d.writeConfig("VideoUrls", JSON.stringify(list));
    d.writeConfig("LastVideo", chosen);
    d.writeConfig("LastVideoPosition", 0);
    d.wallpaperPlugin = %(plugin)s;
}
print(%(ok)s + ds.length);
"""


def _run(script: str, expected: int) -> None:
    """Run a write script and insist it reached every desktop it was supposed to.

    Counting is the second half of knowing it worked. A script that throws half way through still
    prints nothing, which the marker catches -- but a script that ran against a desktop list that
    changed underneath it prints a number, and only the number says so.
    """
    answer = _evaluate(script).strip()
    if answer != str(expected):
        raise WallpaperError(
            f"the shell changed {answer or 'no'} desktop(s), not the {expected} it was asked for")


def showing(state: dict) -> str:
    """Whatever is on the first desktop now, whichever plugin put it there.

    `current_target` answers *for a mode* and says nothing when the running plugin is not that
    mode's. That is right for the picker, whose job is to say whether what you are looking at is
    what it would set -- and wrong for taking a colour off the screen, where the question is simply
    what is there. The two disagree on any desktop whose picker is set to one kind and whose first
    screen is wearing the other, which is not a rare state at all.
    """
    for mode in ("image", "video"):
        found = current_target(mode, state)
        if found:
            return found
    return ""


def same_target(left: str, right: str) -> bool:
    """Two URLs naming the same thing, whichever way each was spelled.

    Both halves matter. The spelling, because one plugin writes its spaces raw and the other does
    not; and the path itself, because `/home` being a link to `/var/home` makes two true names for
    one file -- and a comparison that misses that reports a change on every single apply.
    """
    if not left or not right:
        return False
    return (os.path.realpath(to_path(left).rstrip("/"))
            == os.path.realpath(to_path(right).rstrip("/")))


def video_list(target: str, state: dict) -> list[dict]:
    """What the plugin's list would become: the chosen video enabled, every other one switched off.

    This is what the change is **described** as. The change itself is made by the script, which
    reads and rewrites the list inside the shell -- a list built out here and sent whole would
    write over anything that landed in between.

    The list is kept entire either way. Each row carries settings somebody chose, one of them a
    playback rate of its own, and replacing the list with a single row would throw all of that
    away to say something that can be said without it.
    """
    videos = [dict(v) for v in _known_videos(state)]
    found = False
    for video in videos:
        match = same_target(str(video.get("filename") or ""), target)
        video["enabled"] = match
        found = found or match
    if not found:
        videos.append({"filename": target, "enabled": True, "duration": 0, "customDuration": 0,
                       "playbackRate": 0, "alternativePlaybackRate": 0, "loop": False})
    return videos


def _heading(state: dict, plugin: str) -> str:
    return (f"--- the wallpaper of activity {state.get('activity', '?')}, "
            f"{len(state.get('desktops') or [])} desktop(s)\n+++ {plugin}\n")


#: Changing which plugin draws the wallpaper, and nothing else about it. Each plugin keeps its own
#: config under its own group, so the one being switched to comes back showing whatever it had --
#: which is what the desktop's own dialog does, and the reason nothing is written here but the name.
_WRITE_PLUGIN = """
var ds = desktopsForActivity(%(activity)s);
for (var i = 0; i < ds.length; i++) { ds[i].wallpaperPlugin = %(plugin)s; }
print(%(ok)s + ds.length);
"""


def _screens(state: dict) -> str:
    count = len(state.get("desktops") or [])
    return "this activity's screen" if count == 1 else f"this activity's {count} screens"


def plugin_plan(mode: str, state: dict,
                activity: str | None = None) -> tuple[str, Callable[[], None], str] | None:
    """Put this kind of wallpaper on every desktop of the activity. None when it is already so.

    Answering None is not a nicety here, it is the whole loop prevention: this app writes the
    plugin only when the plugin is not already that, so a change it made itself, coming back
    through the watcher, ends here rather than starting another round.

    The third element is the change in plain words, for the dry-run report.
    """
    plugin = PLUGINS.get(mode)
    if not plugin:
        return None
    desktops = state.get("desktops") or []
    if not desktops or all(str(d.get("plugin")) == plugin for d in desktops):
        return None
    was = str(desktops[0].get("plugin") or "") or "(none)"
    text = _heading(state, plugin) + f"-wallpaperplugin={was}\n+wallpaperplugin={plugin}\n"
    script = _WRITE_PLUGIN % {"plugin": _js(plugin), "ok": _js(OK), "activity": _activity(activity)}
    plain = (f"switch {_screens(state)} to {'video' if mode == 'video' else 'picture'} "
             f"wallpapers -- each kind keeps its own settings, so it comes back showing what it "
             f"showed last")
    return text, lambda: _run(script, len(desktops)), plain


# ---------------------------------------------------------------- when the video pauses

#: The video plugin's `PauseMode`, in its own dialog's words -- the ones somebody will find there.
#: What each costs is on the Wallpaper tab, beside the control.
PAUSE_MODES = {
    "0": "Maximized or full-screen windows",
    "1": "Active window",
    "2": "At least one window is visible",
    "3": "Never",
}


def pause_default() -> str:
    """What the video plugin does when its config says nothing, read from its own schema.

    Read rather than assumed, and needed for one reason: a desktop whose file carries no
    `PauseMode` is on this value, and asking for it must write nothing -- a control painted on the
    Wallpaper tab must never put the plugin's default into the file just by being drawn."""
    import kconfig
    schema = os.path.join(plugin_dir(VIDEO_PLUGIN), "contents", "config", "main.xml")
    return str(kconfig.schema_defaults(schema).get("General", {}).get("PauseMode", "0"))


def pause_mode(state: dict) -> str:
    """When the video pauses on the activity in use, as the plugin's number. The first desktop
    answers for the activity, the way it does for the plugin in `mode_of`."""
    desktops = state.get("desktops") or []
    raw = str((desktops[0] if desktops else {}).get("pause") or "")
    return raw if raw in PAUSE_MODES else pause_default()


#: Setting when the video pauses: the plugin's own key, in its own group, on every desktop of the
#: activity in use -- the same reach a video chosen in the picker has.
_WRITE_PAUSE = """
var ds = desktopsForActivity(%(activity)s);
for (var i = 0; i < ds.length; i++) {
    var d = ds[i];
    d.currentConfigGroup = ["Wallpaper", %(plugin)s, "General"];
    d.writeConfig("PauseMode", %(value)s);
}
print(%(ok)s + ds.length);
"""


def pause_plan(value: str, state: dict,
               activity: str | None = None) -> tuple[str, Callable[[], None], str] | None:
    """Make the video pause at `value` -- one of `PAUSE_MODES` -- on every desktop of the activity.

    None when every desktop already pauses that way, a desktop with nothing in its file counting
    as the plugin's default. That is what keeps painting the Wallpaper tab from writing anything,
    and what `scripts/drive.py` checks by asking for the value that is already there.

    The key is never read by this app for anything else. It is the plugin's, and this only writes
    what somebody picked on the Wallpaper tab -- the owner's decision, with the cost measured and
    written beside the control, was that KyprX changes it only when asked.
    """
    value = str(value)
    if value not in PAUSE_MODES:
        return None
    desktops = state.get("desktops") or []
    default = pause_default()
    now = [str(d.get("pause") or "") for d in desktops]
    if not desktops or all((p if p in PAUSE_MODES else default) == value for p in now):
        return None
    was = pause_mode(state)
    text = (f"--- when the video pauses, activity {state.get('activity', '?')}\n"
            f"+++ {VIDEO_PLUGIN}\n-PauseMode={was}\n+PauseMode={value}\n")
    script = _WRITE_PAUSE % {"plugin": _js(VIDEO_PLUGIN), "value": _js(int(value)),
                             "activity": _activity(activity),
                             "ok": _js(OK)}
    plain = (f"pause the video wallpaper on {_screens(state)}: "
             f"{PAUSE_MODES.get(was, was)} → {PAUSE_MODES[value]}")
    return text, lambda: _run(script, len(desktops)), plain


def _settled(mode: str, target: str, state: dict) -> bool:
    """Is the desktop already showing this, in the way this app would have set it?

    Not just "is that the file". In video mode the plugin has to be the one running **and** the
    chosen video has to be the only one enabled, because a list with two enabled entries is a
    desktop that will move on to a different video by itself.
    """
    desktops = state.get("desktops") or []
    if not desktops:
        return False
    if mode == "video":
        if not all(d.get("plugin") == VIDEO_PLUGIN for d in desktops):
            return False
        enabled = [v for v in _known_videos(state) if v.get("enabled")]
        return (len(enabled) == 1
                and same_target(str(enabled[0].get("filename") or ""), target)
                and same_target(current_target("video", state), target))
    return (all(d.get("plugin") == IMAGE_PLUGIN for d in desktops)
            and same_target(current_target("image", state), target))


def plan(mode: str, target: str, state: dict,
         activity: str | None = None) -> tuple[str, Callable[[], None], str] | None:
    """What changing the wallpaper to this would do, and how to do it. None when it is already so.

    Answering None is what makes applying the wallpaper already on screen silent, and that is
    worth more than the call it saves: it is the property `scripts/drive.py` asserts, because a
    setter that reports a change when nothing changed is a page that writes by itself.
    """
    if _settled(mode, target, state):
        return None
    expected = len(state.get("desktops") or [])
    desktops = state.get("desktops") or []
    shown = os.path.basename(to_path(target).rstrip("/")) or target
    if mode == "video":
        listing = video_list(target, state)
        enabled = sum(1 for v in listing if v.get("enabled"))
        text = (_heading(state, VIDEO_PLUGIN)
                + f"-LastVideo={current_target('video', state) or '(none)'}\n"
                + f"+LastVideo={target}\n"
                + f" VideoUrls: {len(listing)} known, {enabled} enabled\n")
        script = _WRITE_VIDEO % {"plugin": _js(VIDEO_PLUGIN), "target": _js(target), "ok": _js(OK),
                                 "activity": _activity(activity)}
        others = len(listing) - 1
        switch = ("" if all(d.get("plugin") == VIDEO_PLUGIN for d in desktops)
                  else ", switching them to video wallpapers")
        plain = (f"play {shown} as the wallpaper on {_screens(state)}{switch}: in the video "
                 f"plugin's list it is the one switched on and the other {others} are switched "
                 f"off but kept, and it starts from the beginning")
    else:
        text = (_heading(state, IMAGE_PLUGIN)
                + f"-Image={current_target('image', state) or '(none)'}\n"
                + f"+Image={target}\n")
        script = _WRITE_IMAGE % {"plugin": _js(IMAGE_PLUGIN), "target": _js(target), "ok": _js(OK),
                                 "activity": _activity(activity)}
        switch = ("" if all(d.get("plugin") == IMAGE_PLUGIN for d in desktops)
                  else ", switching them to picture wallpapers")
        plain = f"show {shown} as the wallpaper on {_screens(state)}{switch}"
    return text, lambda: _run(script, expected), plain
