"""What the app remembers between runs.

Far less than you would expect, and that is the point: **the config files are the state**. Whether
a window hides its title bar, keeps the outline or gets blurred is read back out of
the decoration and compositor config every time, so a change made anywhere else — by hand, by the
theme's own settings app, by a restored backup — shows up here as fact rather than as drift.

Only what cannot be read back out of a file is stored. About windows, three things:

* **which classes have been seen before**, so the default is applied once and never fought over
  afterwards. Turn a window's title bar back on and it stays on;
* **which apps refuse a server-side decoration**, which is knowable only by trying and looking;
* **which windows are see-through at a number of their own** (`Config.own_transparency`): the rule
  that carries the number looks exactly like the rule of a window at the shared strength.

Beside those, this app's own settings (`Config`: paused, notifications, the colour from the
wallpaper, the shared strength, what a new window gets, the cheatsheet's chosen keys, the
picker's folder and layout), and, while KyprX is taken off the desk, which copy of the desk *Put
my setup back* restores (`State.off`).

Both files are held to the same promise the config files are: **in dry run nothing here is
written either.** It is not a detail. Marking a class as seen is what stops the defaults being
applied to it ever again, so a dry run that wrote this would quietly change what the *next* real
run does — a side effect outliving the session that was supposed to have none.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field

import writer
from defaults import SWITCHES as _DEFAULT_SWITCHES
from defaults import TRANSPARENCY as _DEFAULT_TRANSPARENCY
from defaults import WALLPAPER as _DEFAULT_WALLPAPER

#: The daemon's working copy of its own settings. Beside `state.json` rather than in
#: `~/.config/kyprx/`, which is the KyprX folder: the folder is the description of the setup that
#: somebody reads, versions and carries elsewhere, written by the daemon from these -- see
#: `daemon/folder.py`. A file in the folder is never what the daemon starts from, so an edit made
#: there, or a folder copied over it, cannot leave the daemon half on one setup and half on another.
CONFIG_PATH = os.path.expanduser("~/.local/state/kyprx/config.json")
STATE_PATH = os.path.expanduser("~/.local/state/kyprx/state.json")

#: Where the settings lived before the folder, read only when the working copy is not there yet --
#: an install whose one-off move (`migrate.move_working_copies`) has not happened, or failed. A
#: failed move must not read as "no settings": that would start with new windows being adjusted
#: and every switch at its default.
LEGACY_CONFIG_PATH = os.path.expanduser("~/.config/kyprx/config.json")

#: Stamped into `state.json`, and read by `migrate.py` to know whether a one-off pass has already
#: run against this install. Bump it when something outside these two files has to be brought up
#: to date — a name written into somebody else's config, say — never for a change to their own
#: contents, which are read back field by field and need no version at all.
#:
#: 4 is the tiling script's layout order moving to KyprX's own, once, where nobody had chosen one
#: -- see `migrate.new_layout_order`. 5 is the title bar's opacity keys moving to the names the
#: decoration reads -- see `migrate.rename_title_bar_keys`. 6 is this app's own two files moving
#: out of what became the KyprX folder -- see `migrate.move_working_copies`.
#:
#: Only `migrate._stamp_version` ever raises the number. `State.save` writes back the one it read,
#: which is what lets a pass that failed run again at the next start: saving used to stamp this
#: constant, so the first window seen after a failed pass marked it done.
STATE_VERSION = 6

#: What the wallpaper picker's two choices may be. Neither is stored any more -- which one is on
#: is read from the shell, by `wallpaper.mode_of` -- so this is now what a *request* is checked
#: against rather than a stored value. Still declared once, for the same reason: spelled out at
#: each site, they were already in five places and one of them was about to disagree.
#:
#: Which of the two a fresh install gets is not here but in `defaults.WALLPAPER`, beside every
#: other opinion this app has, because that is what *Restore defaults* puts back.
WALLPAPER_MODES = ("image", "video")
WALLPAPER_LAYOUTS = ("pages", "strip")


#: The range a window's own number may take. See `Config.own_transparency` for why it stops short of
#: 100.
OWN_TRANSPARENCY_RANGE = (1, 99)


def own_strength(value) -> int | None:
    """One window's own number, or None when it is not one: not a whole number, or outside the
    range. Refused rather than clamped -- a 100 turned into 99 is a window see-through that was
    asked to be opaque."""
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
        whole = float(value) == number
    except (TypeError, ValueError):
        return None
    low, high = OWN_TRANSPARENCY_RANGE
    return number if whole and low <= number <= high else None


def own_strengths(listed) -> dict:
    """A class-to-number mapping as read from a file somebody may have edited by hand: every entry
    that is not a named class with a number in range is passed over, and the rest kept."""
    if not isinstance(listed, dict):
        return {}
    out = {}
    for window_class, value in listed.items():
        number = own_strength(value)
        if str(window_class).strip() and number is not None:
            out[str(window_class).strip()] = number
    return out


def read_json(path: str, default: dict) -> dict:
    """One of this app's own files, or `default` when there is no such file or nothing in it that
    reads as one: not JSON, not text, not an object at the top. Every caller reads fields out of an
    object, and a file somebody edited into a list used to stop the daemon at its first `.get`."""
    try:
        with open(path, encoding="utf-8") as fh:
            found = json.load(fh)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return dict(default)
    return found if isinstance(found, dict) else dict(default)


def write_json(path: str, data: dict) -> None:
    """One of this app's own files, written whole and atomically -- and in dry run not at all.

    Shared with `daemon/profiles.py`, which keeps its file to the same promise: what a dry run
    changes in memory stands for the daemon's lifetime and never reaches disk.

    **In dry run it says what it would have saved**, compared with the file as it is on disk. It
    used to return without a word, which made these three files the one write a dry run could not
    show -- `scripts/simulate.sh` had to read the settings back over the bus to notice them at all.
    The marker is `would have saved`, never `would have written`: the driver reads the second as a
    config file changing, and saving a profile must not look like that.
    """
    if writer.dry_run():
        import explain
        writer.report(explain.own_file(path, read_json(path, {}), data))
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".new"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


@dataclass
class Defaults:
    """What a window gets the first time it is seen. The theme, in other words.

    The values are not spelled out here: they come from `daemon/defaults.py`, which is the one
    place this app's opinions are declared. Two copies of a default is two things to change and
    one of them forgotten.
    """

    titlebar: bool = _DEFAULT_SWITCHES["titlebar"]   # False means hidden, the point of the app
    outline: bool = _DEFAULT_SWITCHES["outline"]
    transparency: bool = _DEFAULT_SWITCHES["transparency"]
    blur: bool = _DEFAULT_SWITCHES["blur"]

    @classmethod
    def from_dict(cls, given) -> "Defaults":
        """The fields a mapping names, each read as a switch; anything else in it is passed over.

        The one way in from outside -- the settings file, a settings file being imported, a call
        over the bus. Handed straight to the constructor, a key this version has never heard of
        stopped an import half way, with its config files already written."""
        if not isinstance(given, dict):
            return cls()
        return cls(**{k: bool(v) for k, v in given.items() if k in cls.__dataclass_fields__})


def key_sequence(value) -> list[int] | None:
    """A key sequence as a list of whole numbers, or None when it is not one."""
    if not isinstance(value, list):
        return None
    try:
        return [int(x) for x in value]
    except (TypeError, ValueError):
        return None


@dataclass
class Config:
    paused: bool = False
    notify: bool = True
    #: Whether a wallpaper set from the picker also hands its colour to the desktop.
    #:
    #: A bool and nothing else, because there is nothing else to keep. The colour itself is already
    #: on the desktop, in `kdeglobals [General] AccentColor`, and how far it soaks in is already in
    #: the derived scheme's `TintFactor` -- both read back by `daemon/theme.py`. Copying either of
    #: them here would be a second truth able to disagree with the first.
    #:
    #: Top level rather than inside `wallpaper` below, because it is not one of the picker's
    #: settings: the picker behaves identically either way, and the switch is on the Appearance tab
    #: beside the colour it feeds.
    auto_colour: bool = False
    #: How see-through a window is when its Transparency is ticked, in per cent. One number for
    #: every ticked window that has none of its own -- see `own_transparency` below. The question
    #: the table asks is still "is this window see-through", not "how much".
    #:
    #: Not inside `defaults` below, which is what a *window* gets the first time it is seen. This
    #: is a strength rather than a state, and it applies to every window already ticked the moment
    #: it changes.
    transparency: int = _DEFAULT_TRANSPARENCY
    #: The windows that are see-through at a number of their own rather than at `transparency`,
    #: by window class. Chosen on the Windows tab, one class at a time, and asked for by the owner
    #: in so many words: the strength moves, these do not.
    #:
    #: Stored, where almost nothing else about a window is, because it cannot be read back out of
    #: a config file. The rule a class's number is written into looks exactly like the rule a
    #: window standing at the strength has, so "this window's number is its own" is a fact that
    #: exists only here -- and it is what every road that moves the strength asks before moving a
    #: window (`transparency_targets` in `daemon/kyprd_transparency.py`).
    #:
    #: 1 to 99 and never 100. A hundred is opaque, and opaque is the tick's answer, not a number:
    #: a class kept at 100 here would read as unticked, and ticking it would put it straight back.
    own_transparency: dict = field(default_factory=dict)
    defaults: Defaults = field(default_factory=Defaults)
    #: Which key combination the cheatsheet shows, for the actions that carry more than one.
    #: Keyed by `shortcuts.qualified`, and the value is the whole sequence rather than a position
    #: in the action's list — a position means nothing the moment the desktop reorders or drops
    #: one, and KRunner carries three.
    #:
    #: The only thing this app remembers about shortcuts. The keys themselves are never stored
    #: here: the compositor serves the registry and rewrites it at logout, so a copy kept here
    #: would be a second truth that goes stale on its own.
    cheatsheet_keys: dict = field(default_factory=dict)
    #: The wallpaper picker's settings: which folder the videos are in, and which of its two
    #: layouts the key opens. `{"video_dir": "...", "layout": "pages" | "strip"}`.
    #:
    #: **Which kind of wallpaper it lists is deliberately not here.** That is the wallpaper plugin
    #: the activity in use is wearing, which lives in the shell's config and is a choice made per
    #: activity -- so one word kept here could not be both, and was not: two activities on this
    #: desk wore different plugins while this said one thing about both. It is read from the shell
    #: every time instead, by `wallpaper.mode_of`. A `mode` in a file written before this is
    #: ignored rather than migrated: nothing is lost, because the desktop knows.
    #:
    #: Deliberately not in `Defaults` above, which is what a *window* gets. It is nonetheless one
    #: of the things *Restore defaults* puts back, from `defaults.WALLPAPER`, and that is a
    #: decision rather than an oversight: it used to be argued here that a folder somebody chose
    #: is not this app's opinion and must not be thrown away, and the owner decided the other way.
    #: What makes it cheap is the next paragraph -- the folder is worked out from the machine when
    #: there is none, so clearing it costs a recomputation and not a choice.
    #:
    #: The folder is stored rather than worked out every time. It is worked out **once**, from
    #: where the videos the plugin already knows about live -- and once somebody has chosen a
    #: folder of their own, a list that changes must not move it back.
    wallpaper: dict = field(default_factory=lambda: dict(_DEFAULT_WALLPAPER))

    @classmethod
    def load(cls) -> "Config":
        """The settings file, field by field, each read as the type it has to be.

        Every block is checked for its shape before it is read, and a block that is not what it
        should be reads as the default. The daemon reads this at start, where one value somebody
        edited by hand -- a key sequence with a word in it -- used to stop it coming up at all."""
        found = CONFIG_PATH if os.path.exists(CONFIG_PATH) or not os.path.exists(
            LEGACY_CONFIG_PATH) else LEGACY_CONFIG_PATH
        return cls.from_dict(read_json(found, {}))

    @classmethod
    def from_dict(cls, d) -> "Config":
        """The same reading from a mapping rather than the file: a copy of the desk being put back
        carries these settings as they were, and has to be read with exactly the care the file
        is."""
        d = d if isinstance(d, dict) else {}
        defaults = Defaults.from_dict(d.get("defaults"))
        chosen = d.get("cheatsheet_keys")
        chosen = chosen if isinstance(chosen, dict) else {}
        paper = d.get("wallpaper")
        paper = paper if isinstance(paper, dict) else {}
        layout = str(paper.get("layout", _DEFAULT_WALLPAPER["layout"]))
        try:
            strength = int(d.get("transparency", _DEFAULT_TRANSPARENCY))
        except (TypeError, ValueError):
            strength = _DEFAULT_TRANSPARENCY
        return cls(paused=bool(d.get("paused", False)),
                   notify=bool(d.get("notify", True)),
                   auto_colour=bool(d.get("auto_colour", False)),
                   transparency=min(max(strength, 1), 100),
                   own_transparency=own_strengths(d.get("own_transparency")),
                   defaults=defaults,
                   cheatsheet_keys={str(k): keys for k, v in chosen.items()
                                    if (keys := key_sequence(v)) is not None},
                   wallpaper={"video_dir": str(paper.get("video_dir",
                                                          _DEFAULT_WALLPAPER["video_dir"])),
                              "layout": (layout if layout in WALLPAPER_LAYOUTS
                                         else _DEFAULT_WALLPAPER["layout"])})

    def save(self) -> None:
        write_json(CONFIG_PATH, asdict(self))


class State:
    """Seen classes and the ones whose app refuses a server-side decoration."""

    def __init__(self):
        d = read_json(STATE_PATH, {"version": 0, "seen": [], "refuses_ssd": []})
        #: The version as read, written back unchanged -- see `STATE_VERSION`.
        try:
            self.version = int(d.get("version", 0))
        except (TypeError, ValueError):
            self.version = 0
        #: Names only. A list that is not one -- a string, say, which `set()` would split into
        #: letters -- reads as empty rather than as a class for every character in it.
        self.seen: set[str] = self._names(d.get("seen"))
        self.refuses_ssd: set[str] = self._names(d.get("refuses_ssd"))
        #: Set while KyprX is taken off the desk: the copy of the desk kept before, which *Put my
        #: setup back* restores. Empty otherwise. Here, and not in the KyprX folder, because it is
        #: a fact about this desk: the folder is exactly what it leaves alone while it lasts.
        off = d.get("off")
        self.off: dict = off if isinstance(off, dict) and off.get("copy") else {}
        #: The version of KyprX that ran here last, so that the first start of another one knows
        #: it is one -- see `InstallationPart.note_the_version`. Not the format's `version` above.
        self.app_version = str(d.get("app_version") or "")

    @staticmethod
    def _names(listed) -> set[str]:
        return {str(x) for x in listed if str(x).strip()} if isinstance(listed, list) else set()

    def save(self) -> None:
        #: Written as a fresh dict rather than as the file plus changes, which is what makes a
        #: field that stops existing disappear on the next save with no migration to write.
        data = {"version": self.version, "seen": sorted(self.seen),
                "refuses_ssd": sorted(self.refuses_ssd)}
        if self.off:
            data["off"] = dict(self.off)
        if self.app_version:
            data["app_version"] = self.app_version
        write_json(STATE_PATH, data)

    def mark_seen(self, window_class: str) -> bool:
        """Returns True the first time a class is seen."""
        if window_class in self.seen:
            return False
        self.seen.add(window_class)
        return True

    def set_refuses_ssd(self, window_class: str, refuses: bool) -> bool:
        """Returns True when the answer changed."""
        had = window_class in self.refuses_ssd
        if refuses == had:
            return False
        self.refuses_ssd.add(window_class) if refuses else self.refuses_ssd.discard(window_class)
        return True
