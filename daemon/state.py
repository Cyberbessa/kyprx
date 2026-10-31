"""What the app remembers between runs.

Far less than you would expect, and that is the point: **the config files are the state**. Whether
a window hides its title bar, keeps the outline or gets blurred is read back out of
the decoration and compositor config every time, so a change made anywhere else — by hand, by the
theme's own settings app, by a copy of the desk put back — shows up here as fact rather than as
drift.

Only what cannot be read back out of a file is stored. About windows, three things:

* **which classes have been seen before**, so the default is applied once and never fought over
  afterwards. Turn a window's title bar back on and it stays on;
* **which apps refuse a server-side decoration**, which is knowable only by trying and looking;
* **which windows are see-through at a number of their own** (`Config.own_transparency`): the rule
  that carries the number looks exactly like the rule of a window at the shared strength;
* **which windows were ticked while the strength stood at 100 %** (`Config.ticked_at_100`): there
  the rule a tick writes — opacity 100, forced — reads exactly like the nothing an unticked window
  reads, so the tick exists only here until the strength comes back down.

Beside those, this app's own settings (`Config`: paused, notifications, the colour from the
wallpaper, the shared strength, what a new window gets, the cheatsheet's chosen keys, the
picker's folder and layout); while KyprX is taken off the desk, which copy of the desk *Put
my setup back* restores (`State.off`); and whether the settings window still has to ask about
KyprX's look (`State.look`).

Both files are held to the same promise the config files are: **in dry run nothing here is
written either.** It is not a detail. Marking a class as seen is what stops the defaults being
applied to it ever again, so a dry run that wrote this would quietly change what the *next* real
run does — a side effect outliving the session that was supposed to have none.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field

import shortcuts
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
#: 5 is the title bar's opacity keys moving to the names the decoration reads -- see
#: `migrate.rename_title_bar_keys`. 6 is this app's own two files moving out of what became the
#: KyprX folder -- see `migrate.move_working_copies`. 7 is the declared settings on a fresh install
#: (`migrate._bootstrap_pass`) and corner radius 7.5 on an older one. 4 and 8 have no pass: an
#: install below either is only stamped, and the number stays 8 so that a file stamped 8 reads as
#: up to date.
#:
#: Only `migrate._stamp_version` ever raises the number. `State.save` writes back the one it read,
#: which is what lets a pass that failed run again at the next start: saving used to stamp this
#: constant, so the first window seen after a failed pass marked it done.
STATE_VERSION = 8

#: Where the question about KyprX's look stands (`State.look`): to be asked when the settings
#: window opens; answered by putting KyprX's look on, or by keeping the person's own; or answered
#: by a KyprX folder that arrived carrying a colour preset, which put its colours on. Colours of
#: KyprX's put on by any door answer it again after a *Keep my look* (`State.look_went_on`). A
#: first start puts nothing of the look on, the owner's choice, so an install that never had it is
#: asked once (`DefaultsPart.look_offer`). An install that was already set up when the question
#: came to exist has no answer and is never asked: it reads as "".
LOOK_DUE = "due"
LOOK_KYPRX = "kyprx"
LOOK_OWN = "own"
LOOK_FOLDER = "folder"
LOOKS = (LOOK_DUE, LOOK_KYPRX, LOOK_OWN, LOOK_FOLDER)

#: What the wallpaper picker's choices may be. Neither the mode nor the layout is stored anywhere
#: else -- which one is on is read from the shell, by `wallpaper.mode_of`, and the layout is
#: checked by `wallpaper_layout` below -- so this is what a *request* is checked against rather
#: than a list of stored values. Still declared once, for the same reason: spelled out at each
#: site, they were already in five places and one of them was about to disagree.
#:
#: Which of the two a fresh install gets is not here but in `defaults.WALLPAPER`, beside every
#: other opinion this app has, because that is what *Restore defaults* puts back.
WALLPAPER_MODES = ("image", "video")
WALLPAPER_LAYOUTS = ("pages", "strip")

#: Layout ids this app wrote once and reads still, with what each one meant, spelled in the new
#: terms. `strip-names` was the strip with the file name under the picture, from 0.1.2 to 0.1.4;
#: it is the strip with its text switched on now (`strip_text`). Kept here rather than migrated,
#: because the id lives in more places than this app's own file -- the KyprX folder on another
#: machine, a copy of the desk -- and every one of them reaches
#: `wallpaper_layout` and `strip_text` below on its way in. Without this an old `strip-names`
#: would open Pages, the default for a name nobody knows.
RETIRED_LAYOUTS = {"strip-names": {"layout": "strip", "strip_text": True}}


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


#: The switches the Windows tab's column boxes set for every window at once, and so the ones a window
#: can keep as set by hand (`Config.kept`). The outline is not among them: the tab has no column
#: for it.
KEPT_SWITCHES = ("titlebar", "transparency", "blur")


def kept_switches(listed):
    """The windows that keep switches as set by hand, as read from a file somebody may have edited:
    a class-to-names mapping, each list holding only names from `KEPT_SWITCHES`, once each, in that
    order, and a class with none left out. Anything that is not such a mapping -- a file from before
    the column boxes, which has no key -- is None, which the daemon reads as *not yet looked for*
    (`WindowsPart.seed_kept`) rather than as no window keeping anything."""
    if not isinstance(listed, dict):
        return None
    out = {}
    for window_class, names in listed.items():
        named = {str(n) for n in names} if isinstance(names, list) else set()
        kept = [n for n in KEPT_SWITCHES if n in named]
        if str(window_class).strip() and kept:
            out[str(window_class).strip()] = kept
    return out


def wallpaper_layout(value) -> str:
    """A picker layout as this app holds it: the name when it is one, the default otherwise.

    The one normaliser every layout handed in from outside goes through -- the settings file, the
    KyprX folder, a call over the bus. An unknown name reaching
    the picker would open nothing, and a fallback spelled again at each site is how a renamed
    default leaves the sites disagreeing; the guard in `tests/test_picker_layouts.py` keeps the
    names out of every daemon module but this one and `defaults`. A retired id reads as the layout
    it became (`RETIRED_LAYOUTS`).
    """
    text = str(value) if value is not None else ""
    text = RETIRED_LAYOUTS.get(text, {}).get("layout", text)
    return text if text in WALLPAPER_LAYOUTS else _DEFAULT_WALLPAPER["layout"]


def strip_text(paper, fallback=None) -> bool:
    """Whether the strip writes its text -- the selected wallpaper's name under the picture, how
    many there are and which keys do what, and a card's name -- as a block of picker settings
    carries it.

    Read like `kde_wallpapers` below, with one step between the key and the fallback: a block
    whose layout is a retired id says what that id meant (`RETIRED_LAYOUTS`), so an old
    `strip-names` opens the strip with its text on rather than the bare one. A true or false in the
    key itself wins over that, because it was written by something that knew the switch.
    """
    paper = paper if isinstance(paper, dict) else {}
    value = paper.get("strip_text")
    if not isinstance(value, bool):
        value = RETIRED_LAYOUTS.get(str(paper.get("layout") or ""), {}).get("strip_text")
    if not isinstance(value, bool):
        value = fallback if isinstance(fallback, bool) else None
    return bool(_DEFAULT_WALLPAPER["strip_text"] if value is None else value)


def kde_wallpapers(paper, fallback=None) -> bool:
    """Whether the picker also lists KDE's own wallpapers, as a block of picker settings carries
    it: the key when it is there, `fallback` when it is not, and the declared default when
    neither is. A value that is not true or false counts as absent, the way a spelled-out
    `"no"` would read as true were it taken at face value.

    The one normaliser the switch is read through, for the reason `wallpaper_layout` above is the
    one normaliser of layouts. Who hands in what decides what a missing key means: a call over
    the bus and the KyprX folder being applied pass the value held now, so a block written
    before the switch existed leaves it alone; a config being loaded passes
    nothing, and reads as the declared default -- which is what the switch meant before it
    existed.
    """
    value = (paper or {}).get("kde_wallpapers")
    if not isinstance(value, bool):
        value = fallback if isinstance(fallback, bool) else None
    return bool(_DEFAULT_WALLPAPER["kde_wallpapers"] if value is None else value)


def colour_screen(value) -> str:
    """The screen the colour from the wallpaper comes from, as this app holds it: an output's name,
    such as `HDMI-A-1`, or "" for the primary screen -- whichever monitor is the primary then.
    Anything that is not text reads as the primary."""
    return value.strip() if isinstance(value, str) else ""


def all_screens(paper, fallback=None) -> bool:
    """Whether a wallpaper chosen in the picker goes on every screen of the activity, as a block of
    picker settings carries it -- KDE's own *Set for all screens*. Off, it goes on the screen the
    picker opened on, which is what KDE's own Wallpaper page does. Read the way `kde_wallpapers`
    above is, and for its reasons."""
    value = (paper or {}).get("all_screens") if isinstance(paper, dict) else None
    if not isinstance(value, bool):
        value = fallback if isinstance(fallback, bool) else None
    return bool(_DEFAULT_WALLPAPER["all_screens"] if value is None else value)


def owed_of(saved) -> dict[str, list[list[int]]]:
    """`state.json`'s owed keys as `State` holds them: a name for each action, and for each a list
    of key sequences, each a list of whole numbers. Anything else in the file reads as nothing owed
    -- a hand edit must not stop the daemon, and an entry that cannot be read cannot be put on."""
    if not isinstance(saved, dict):
        return {}
    out = {}
    for name, sequences in saved.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(sequences, list):
            continue
        if all(isinstance(s, list) and s and all(isinstance(k, int) and not isinstance(k, bool)
                                                 for k in s) for s in sequences):
            out[name] = [list(s) for s in sequences]
    return out


def off_of(saved: dict) -> dict:
    """While KyprX is taken off the desk, what `state.json` keeps about it -- the copy of the desk
    *Put my setup back* restores -- and an empty dict otherwise, or for anything else in its place.
    The one reading of the field, for `State` and for whoever has to know what the file says rather
    than what the daemon holds (`TilingPart`, which answers from disk even in a dry run)."""
    off = saved.get("off") if isinstance(saved, dict) else None
    return off if isinstance(off, dict) and off.get("copy") else {}


def saved_off() -> dict:
    """`off_of` the file on disk: what this desk's `state.json` says, whatever a dry run holds."""
    return off_of(read_json(STATE_PATH, {}))


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

        The one way in from outside -- the settings file, a call over the bus. Handed straight to
        the constructor, a key this version has never heard of would raise rather than be passed
        over."""
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


def chosen_keys(chosen) -> dict:
    """The cheatsheet's chosen keys as read from a file somebody may have edited by hand -- every
    entry whose value is not a key sequence passed over.

    Each is held under the one name `shortcuts.qualified` spells its action by; where a file names
    the same action both ways, with its component and without, the entry already spelt so wins.
    """
    if not isinstance(chosen, dict):
        return {}
    out = {}
    for name, value in chosen.items():
        keys = key_sequence(value)
        now = shortcuts.qualified(*shortcuts.unqualified(str(name)))
        if keys is None or (now != str(name) and now in chosen):
            continue
        out[now] = keys
    return out


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
    #: Which screen's wallpaper that colour comes from: an output's name, such as `DP-1`, or "" for
    #: the primary screen, whichever monitor is the primary at the time. A name that is not
    #: connected falls back on the primary (`wallpaper.colour_view`).
    #:
    #: Beside `auto_colour` rather than in `wallpaper` below, and that is what keeps it on this
    #: computer: an output's name is this machine's, so the KyprX folder, which carries the
    #: picker's block to other machines, never sees it. *Restore defaults* copies
    #: the settings and puts back only what is declared, so it leaves this as it leaves the
    #: cheatsheet's keys, and going back to a copy of the desk leaves it too (`restore_desk`).
    colour_screen: str = ""
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
    #: The window classes whose Transparency tick is being **remembered** while the strength stands
    #: at 100 %, where the rule a tick writes (opacity 100, forced) is byte for byte what an
    #: unticked window reads -- so there the tick cannot be deduced from the config files like
    #: every other fact about a window, and has to be kept here. It is held only while it has to
    #: be: below 100 the rule is deducible again and the list reads empty, whoever saved it --
    #: `from_dict` sees to that -- and while it lasts, every reader that would otherwise deduce the
    #: tick away asks `TransparencyPart.held` first. A class with a number of its own never
    #: belongs here (its own number is how see-through it is, which is deducible), and neither
    #: does one of the windows KyprX leaves alone -- `Daemon.__init__` drops both kinds.
    #:
    #: Like `own_transparency` above, this cannot be read back out of another program's config: a
    #: forced 100 and no rule at all look the same, so "this tick was chosen" exists only here.
    ticked_at_100: list = field(default_factory=list)
    defaults: Defaults = field(default_factory=Defaults)
    #: The switches each window keeps as somebody set them on its row, by window class: the cells a
    #: column's box on the Windows tab leaves alone when it sets every other window
    #: (`WindowsPart.set_column`). A row ticked unlike its column's box keeps that switch; ticked
    #: like it again, it follows the column. Only the three switches the column boxes set
    #: (`KEPT_SWITCHES`), and only for the windows KyprX manages.
    #:
    #: Stored, like `own_transparency` above, because it cannot be read back: a window whose title
    #: bar shows because somebody showed it reads exactly like one whose title bar shows because
    #: nothing hid it. None until the daemon has looked once at the windows set unlike the defaults
    #: before the boxes existed, and kept them (`WindowsPart.seed_kept`) -- so the first click on a
    #: column cannot undo choices made before it.
    kept: dict | None = None
    #: Which key combination the cheatsheet shows, for the actions that carry more than one.
    #: Keyed by `shortcuts.qualified`, and the value is the whole sequence rather than a position
    #: in the action's list — a position means nothing the moment the desktop reorders or drops
    #: one, and KRunner carries three.
    #:
    #: The only thing this app remembers about shortcuts. The keys themselves are never stored
    #: here: the compositor serves the registry and rewrites it at logout, so a copy kept here
    #: would be a second truth that goes stale on its own.
    cheatsheet_keys: dict = field(default_factory=dict)
    #: The wallpaper picker's settings: which folder the videos are in, and which of its layouts
    #: the key opens. `{"video_dir": "...", "image_dir": "...", "layout": "pages" | "strip",
    #: "strip_text": bool, "all_screens": bool, "kde_wallpapers": bool}`. `strip_text` is whether the
    #: strip writes its text, and `all_screens` whether a wallpaper chosen goes on every screen
    #: rather than the picker's own, each read through its reader above for the reason
    #: `kde_wallpapers` is.
    #:
    #: **Which kind of wallpaper it lists is deliberately not here.** That is the wallpaper plugin
    #: the activity in use is wearing, which lives in the shell's config and is a choice made per
    #: activity -- so one word kept here could not be both, and was not: two activities on this
    #: desk wore different plugins while this said one thing about both. It is read from the shell
    #: every time instead, by `wallpaper.mode_of`. A `mode` in a file written before this is
    #: ignored rather than migrated: nothing is lost, because the desktop knows.
    #:
    #: `kde_wallpapers` is the one stored opinion about *what* the picker lists when it lists
    #: pictures: whether the wallpapers the desktop itself ships stand in the list beside the
    #: chosen folder (`defaults.WALLPAPER` says on). Read through `kde_wallpapers` above, never
    #: off the dict bare, so every road in agrees on what a missing key means.
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
        paper = d.get("wallpaper")
        paper = paper if isinstance(paper, dict) else {}
        try:
            strength = int(d.get("transparency", _DEFAULT_TRANSPARENCY))
        except (TypeError, ValueError):
            strength = _DEFAULT_TRANSPARENCY
        strength = min(max(strength, 1), 100)
        #: The held ticks mean something only at 100 %, where the tick cannot be deduced. Below
        #: that every tick is readable off the window rules again, so a list carried in from a
        #: file reads as empty rather than as ticks waiting to come back -- which is also what
        #: keeps an old list from resurfacing when the strength returns to 100 later: the ticks
        #: that matter then are the ones made while it stood there.
        ticks = d.get("ticked_at_100")
        ticks = (sorted({str(c).strip() for c in ticks if str(c).strip()})
                 if isinstance(ticks, list) else [])
        return cls(paused=bool(d.get("paused", False)),
                   notify=bool(d.get("notify", True)),
                   auto_colour=bool(d.get("auto_colour", False)),
                   colour_screen=colour_screen(d.get("colour_screen")),
                   transparency=strength,
                   own_transparency=own_strengths(d.get("own_transparency")),
                   ticked_at_100=ticks if strength >= 100 else [],
                   defaults=defaults,
                   kept=kept_switches(d.get("kept")),
                   cheatsheet_keys=chosen_keys(d.get("cheatsheet_keys")),
                   wallpaper={"video_dir": str(paper.get("video_dir",
                                                          _DEFAULT_WALLPAPER["video_dir"])),
                              "image_dir": str(paper.get("image_dir",
                                                          _DEFAULT_WALLPAPER.get("image_dir", ""))),
                              "layout": wallpaper_layout(paper.get("layout")),
                              "strip_text": strip_text(paper),
                              "all_screens": all_screens(paper),
                              "kde_wallpapers": kde_wallpapers(paper)})

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
        self.off: dict = off_of(d)
        #: The version of KyprX that ran here last, so that the first start of another one knows
        #: it is one -- see `InstallationPart.note_the_version`. Not the format's `version` above.
        self.app_version = str(d.get("app_version") or "")
        #: Keys a KyprX folder or a copy of the desk brought for actions the shortcut registry did
        #: not have yet, by `shortcuts.qualified` name, each action's whole list of sequences --
        #: KyprX's own above all, which exist only once its compositor script has registered them
        #: (`CopiesPart._restore_shortcuts`, `FolderPart.pay_owed_keys`). Kept here, and not only
        #: in memory, because by the next login the script registers its actions at their
        #: defaults before this daemon starts, and a daemon that had forgotten them would write
        #: those defaults out into the folder.
        self.owed_keys: dict[str, list[list[int]]] = owed_of(d.get("owed_keys"))
        #: Where the question about KyprX's look stands, one of `LOOKS`. The first start stamps it
        #: due (`migrate._stamp_version`); a file still at version 0 -- missing, a dry run's first
        #: start, a first start whose passes failed -- reads as due too, since nothing of the look
        #: went on there either. An install at a version and without the key was set up before
        #: the question existed, and reads as "", which is never asked.
        raw = d.get("look")
        self.look = raw if raw in LOOKS else (LOOK_DUE if self.version == 0 else "")

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
        if self.owed_keys:
            data["owed_keys"] = {k: [list(s) for s in v] for k, v in sorted(self.owed_keys.items())}
        if self.look:
            data["look"] = self.look
        write_json(STATE_PATH, data)

    def look_went_on(self, how: str = LOOK_KYPRX) -> None:
        """KyprX's colours went on the desk by a door other than the question -- `how`, one of
        `LOOKS`: a mode or a preset chosen in the Colours box, a profile, a copy of the desk or a
        KyprX folder that wore a preset, a wallpaper's colour, *Restore defaults*. A question still
        due is answered by it, and so is a *Keep my look* given earlier, which no longer describes
        this desk: the Colours box says its findings as that choice (`ThemePart.theme`,
        `kept_own_look`), and would go on calling something gone wrong since then a choice. An
        install never asked, or one whose answer already put a look on, is left as it is. Saved
        only when it moves."""
        if self.look in (LOOK_DUE, LOOK_OWN) and how != self.look:
            self.look = how
            self.save()

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
