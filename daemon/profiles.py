"""A profile: the Appearance tab, kept under a name.

What a profile carries is declared here once, and it is exactly what that tab shows: how
see-through the windows are, the colours -- mode, preset, a colour of your own and how far it
soaks in -- the corner radius and the window outline. Nothing about the title bar: its buttons,
opacity, spacing and colours are this app's fixed opinion (`daemon/defaults.py`), changed in the
decoration's own dialog, and not part of a look. And nothing else about the desktop: which windows hide their title bar, which are see-through at all, the
blur's strength, the tiling, the shortcuts, the wallpaper. A profile is what somebody wants back
after trying another set of colours, and none of those move with the colours.

Four decisions worth their reasons.

**The values are the effective ones, not the file's.** A key the decoration's config does not
carry reads as whatever the decoration ships, and that is what the Appearance tab shows for it.
Captured from the file alone, a profile taken on an install that never wrote the outline's
thickness would carry no thickness and put none back; compared against the file alone, "is this
the look on the desktop" would change its answer the day the key appeared. So a look holds what
each key *reads as*, which is the one reading `daemon/declared.py` has -- `effective_value`, the
question it asks before writing a declared default -- and the capture, the comparison and the
load all go through it. "On the desktop now" and "loading it would write nothing" are then one
fact, and `scripts/drive.py` asserts they are.

**The transparency is the strength, not the ticks.** Which windows are see-through is a choice
made per window on the Windows tab and stays there; how see-through they are is one number for
all of them, and it is the number a profile carries. Loading one moves every ticked window to
it -- except a window given a number of its own on that tab, which no profile carries or moves --
exactly as moving the control on the Appearance tab does -- and inside the same write as the
radius and the outline, so the screen stops once.

**Colour from the wallpaper is always off in a profile.** The switch decides how the
*next* colour is chosen, and a loaded profile is meant to stay: with the switch left on, the next
wallpaper set from the picker would recolour the desktop over it. So loading one switches it off,
and it is a tick on the Appearance tab to switch back on -- deliberately by hand.

**A key this app stops carrying is dropped on reading.** Version 1 of the file carried the
title bar's keys from when they were controls -- button icon style, shape and hover colours -- and
was in nobody's hands but
this desk's; it is still read, with those keys taken out, because a profile is a small backup and
refusing yesterday's is the one thing a backup must never do. A key a profile never carried is
refused outright: a look handed in with one is a mistake, not a backup.

The window outline's colour is carried even when the outline's style reads no colour, the same
way the Appearance form carries all seven of its keys: a value nothing reads is inert, and
dropping it would make a profile saved on one style and loaded on another lose the colour it had.

The file is this app's own, and it is held to the promise `config.json` and `state.json` are held
to: in dry run it is never written, and what a dry run saves, renames or deletes stands in memory
for as long as that daemon runs -- which is what lets `scripts/drive.py` drive the whole round
trip and `scripts/simulate.sh` prove afterwards that not a byte moved.
"""

from __future__ import annotations

import json
import os

import state
import theme

#: The daemon's working copy, beside its settings for the reason `state.CONFIG_PATH` gives; the
#: KyprX folder carries a copy the daemon writes. `LEGACY_PATH` is read only while this is not
#: there yet, so a move that failed is never a list of profiles that reads as empty.
PATH = os.path.expanduser("~/.local/state/kyprx/profiles.json")
LEGACY_PATH = os.path.expanduser("~/.config/kyprx/profiles.json")


def _source() -> str:
    return PATH if os.path.exists(PATH) or not os.path.exists(LEGACY_PATH) else LEGACY_PATH

#: Of the file. Version 2 is where the title bar's keys left and the transparency arrived;
#: `Profiles.__init__` says how a version 1 file is read. A look carries no version of its own:
#: the keys it may hold are the ones declared below, and a key it does not carry is left where
#: it is on loading.
VERSION = 2

#: The decoration's keys a look carries, by group: the corner radius, and the whole of the Outline
#: section of the Appearance tab -- the same seven keys that page has a control for.
KLASSY = {
    "Windeco": ("WindowCornerRadius",),
    "WindowOutlineStyle": ("WindowOutlineThickness",
                           "WindowOutlineStyleActive", "WindowOutlineCustomColorActive",
                           "WindowOutlineCustomColorOpacityActive",
                           "WindowOutlineStyleInactive", "WindowOutlineCustomColorInactive",
                           "WindowOutlineAccentColorOpacityActive"),
}

#: The blur effect's mirror of the corner radius. The Appearance tab is the one place the radius
#: is set and it writes both, so a look carries both: a blur rounded less than the window shows as
#: a bright sliver in each corner.
BLUR = ("CornerRadius",)

#: The colours, as the Appearance tab chooses them. `auto` sits beside them in the look and is
#: always false -- see the module note.
THEME = ("mode", "preset", "accent", "tint")

#: The strength, as the compositor counts it: a percentage, 100 being opaque. The bounds
#: `SetSettings` keeps, kept here too so a look handed in cannot carry a number the control
#: could never show.
TRANSPARENCY_RANGE = (1, 100)

#: What version 1 of the file carried and this one does not. Taken out on reading, never
#: refused -- see the module note.
RETIRED_WINDECO = ("ButtonIconStyle", "ButtonShape")
RETIRED_BLOCKS = ("button_colours", "button_colours_inactive")

#: How close two tint factors have to be to count as the same. The value is written as `%g` and
#: read back through `float`, so anything closer than this is one number spelled twice.
TINT_TOLERANCE = 0.001

#: Long enough for any name somebody would type, short enough to stay one line in the table.
NAME_LIMIT = 80


# ---------------------------------------------------------------- what a look is

def tree(look: dict) -> dict:
    """A look's decoration-and-blur half, in the shape `declared.write_declared` takes: source,
    group, key.

    The blur effect is one flat section, spelled with an empty group name the way every flat
    source is declared in `daemon/defaults.py`. The strength is not in here: it is not a key in
    anybody's config file but a number written into a window rule per window, and
    `Daemon.apply_look` strikes it beside this.
    """
    return {"klassy": {group: dict(entries) for group, entries in (look.get("klassy") or {}).items()},
            "blur": {"": dict(look.get("blur") or {})}}


def normalise(look) -> dict:
    """A look handed in from outside, checked and typed. Raises ValueError with a sentence.

    Only the keys declared above may appear, and a subset of them is fine: a key a look does not
    carry is left where it is on loading -- absent stays absent, never stored as nothing. The
    colours are the one part that has to be there: without a mode and a preset there is nothing
    for the desktop to be put on.
    """
    if not isinstance(look, dict):
        raise ValueError("a look has to be an object")
    known = {"klassy", "blur", "transparency", "theme"}
    for key in look:
        if key not in known:
            raise ValueError(f"a look does not carry {key}")
    out: dict = {"klassy": {}, "blur": {}, "theme": {}}
    for group, entries in (look.get("klassy") or {}).items():
        if group not in KLASSY:
            raise ValueError(f"a look does not carry the decoration's {group} group")
        for key, value in (entries or {}).items():
            if key not in KLASSY[group]:
                raise ValueError(f"a look does not carry {group}/{key}")
            out["klassy"].setdefault(group, {})[key] = str(value)
    for key, value in (look.get("blur") or {}).items():
        if key not in BLUR:
            raise ValueError(f"a look does not carry the blur effect's {key}")
        out["blur"][key] = str(value)
    if "transparency" in look:
        try:
            strength = int(look["transparency"])
        except (TypeError, ValueError):
            raise ValueError("the transparency has to be a number") from None
        low, high = TRANSPARENCY_RANGE
        out["transparency"] = min(max(strength, low), high)
    colours = look.get("theme")
    if not isinstance(colours, dict):
        raise ValueError("a look needs its colours: a mode, a preset, a colour of your own or "
                         "none, and a tint")
    mode = str(colours.get("mode") or "")
    if mode not in theme.MODES:
        raise ValueError(f"{mode or '(no mode)'} is not a mode")
    preset = str(colours.get("preset") or "")
    if not preset:
        raise ValueError("a look needs a preset")
    accent = str(colours.get("accent") or "")
    if accent and not theme.is_colour(accent):
        raise ValueError(f"{accent} is not a colour")
    try:
        tint = float(colours.get("tint") or 0)
    except (TypeError, ValueError):
        raise ValueError("the tint has to be a number") from None
    # No colour of your own means nothing to soak in, which is how `set_theme` reads it too.
    tint = min(max(tint, 0.0), 1.0) if accent else 0.0
    out["theme"] = {"mode": mode, "preset": preset, "accent": accent, "tint": tint, "auto": False}
    return out


def trouble(look: dict) -> str:
    """"" when this look can go on the desktop here, otherwise the sentence saying why not.

    A preset this machine does not have is the ordinary case: a profile is a small file, and one
    written on a desktop with Carl installed reads perfectly well on one without. It is listed,
    with this sentence on it, and refused when asked for -- before anything is written.
    """
    try:
        normalise(look)
    except ValueError as e:
        return f"this profile cannot be read: {e}"
    colours = look["theme"]
    chosen = theme.preset(colours["preset"])
    if chosen is None:
        return f"there is no preset called {colours['preset']}"
    if chosen.mode != colours["mode"]:
        return f"{chosen.name} is a {chosen.mode} preset and this profile is {colours['mode']}"
    return theme.available(chosen)


def same_theme(colours: dict, now: dict) -> bool:
    """Are these the colours the desktop is wearing? `now` is `theme.current()`.

    The tint counts only while there is a colour of your own to soak in: without one it is nought
    on both sides by construction, and `set_theme` reads it that way too.
    """
    accent = str(colours.get("accent") or "")
    if (str(colours.get("mode") or ""), str(colours.get("preset") or ""), accent) != (
            now["mode"], now["preset"], now["accent"]):
        return False
    if not accent:
        return True
    return abs(float(colours.get("tint") or 0) - float(now.get("tint") or 0)) < TINT_TOLERANCE


def is_on(look: dict, worn: dict) -> bool:
    """Is this look the one the desktop is wearing? `worn` is `Daemon.worn_look()`.

    Key by key against the worn look, whose every value is the effective one -- which makes this
    the same test the declared writer applies before writing a key: equal as strings, or absent
    and therefore to be written. A look with trouble on it is never on, whatever it says; a look
    that carries no strength is on whatever the strength is, and *Update with the current look*
    is how it acquires one.
    """
    if trouble(look):
        return False
    look = normalise(look)
    for group, entries in look["klassy"].items():
        for key, value in entries.items():
            if (worn.get("klassy") or {}).get(group, {}).get(key) != value:
                return False
    for key, value in look["blur"].items():
        if (worn.get("blur") or {}).get(key) != value:
            return False
    if "transparency" in look and look["transparency"] != worn.get("transparency"):
        return False
    return same_theme(look["theme"], worn.get("theme") or {})


def _retire(look: dict) -> None:
    """Take a version 1 look's title bar keys out, in place.

    Targeted pops rather than a pass through `normalise`: a look that cannot be read is kept as
    it is -- see `Profiles.__init__` -- and this must not raise on one.
    """
    windeco = (look.get("klassy") or {}).get("Windeco")
    if isinstance(windeco, dict):
        for key in RETIRED_WINDECO:
            windeco.pop(key, None)
    for block in RETIRED_BLOCKS:
        look.pop(block, None)


# ---------------------------------------------------------------- where they are kept

class Profiles:
    """The profiles, in the order they were saved, and the file they live in.

    A name is compared without regard to case and to the space around it -- `Nord` and `nord`
    are one profile -- but is shown exactly as it was typed.
    """

    def __init__(self):
        self.entries: list[dict] = []
        #: Set when the file is there and cannot be read. Nothing is saved over such a file:
        #: `state.read_json` reads an unreadable file as an empty one, and the next save would then
        #: replace whatever somebody had kept with the one profile just saved. The daemon logs the
        #: sentence at start, and every change is refused with it until the file is put right.
        self.unreadable = ""
        source = _source()
        if os.path.exists(source):
            try:
                with open(source, encoding="utf-8") as fh:
                    json.load(fh)
            except (OSError, json.JSONDecodeError) as e:
                self.unreadable = f"{source} could not be read, so nothing is saved over it: {e}"
                return
        d = state.read_json(source, {})
        if not isinstance(d, dict):
            return
        #: A version 1 file is read with its retired keys dropped, on every start until the next
        #: save writes it out as version 2 -- a daemon coming up does not write, so the file is
        #: not rewritten here. Idempotent, so reading it twice is the same as once.
        try:
            outdated = int(d.get("version") or 1) < VERSION
        except (TypeError, ValueError):
            # A version that is not a number is a file edited by hand; read it as the oldest, which
            # only ever drops keys this version no longer carries.
            outdated = True
        for entry in d.get("profiles") or []:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or "").strip()
            look = entry.get("look")
            if name and isinstance(look, dict):
                if outdated:
                    _retire(look)
                # Kept as it is, readable or not: `trouble()` says so on the row, and a profile
                # somebody cannot load is still theirs to rename or delete. Dropping it here would
                # lose it on the next save without a word.
                self.entries.append({"name": name, "look": look})

    def names(self) -> list[str]:
        return [entry["name"] for entry in self.entries]

    def _index(self, name: str) -> int:
        wanted = str(name).strip().casefold()
        return next((i for i, entry in enumerate(self.entries)
                     if entry["name"].casefold() == wanted), -1)

    def get(self, name: str) -> dict | None:
        i = self._index(name)
        return self.entries[i] if i >= 0 else None

    def put(self, name: str, look: dict, replace: bool = False) -> str:
        """Keep this look under this name. "" when done, otherwise the sentence saying why not."""
        if self.unreadable:
            return f"error: {self.unreadable}"
        name = str(name).strip()
        if not name:
            return "error: a profile needs a name"
        if len(name) > NAME_LIMIT:
            return f"error: a profile's name has to fit in {NAME_LIMIT} characters"
        i = self._index(name)
        if i >= 0 and not replace:
            return f"error: there is already a profile called {self.entries[i]['name']}"
        entry = {"name": name, "look": look}
        if i >= 0:
            # Its place in the list is kept, and the name takes the spelling just typed.
            self.entries[i] = entry
        else:
            self.entries.append(entry)
        self.save()
        return ""

    def rename(self, name: str, to: str) -> str:
        if self.unreadable:
            return f"error: {self.unreadable}"
        to = str(to).strip()
        if not to:
            return "error: a profile needs a name"
        if len(to) > NAME_LIMIT:
            return f"error: a profile's name has to fit in {NAME_LIMIT} characters"
        i = self._index(name)
        if i < 0:
            return f"error: there is no profile called {str(name).strip() or '(nothing)'}"
        j = self._index(to)
        if j >= 0 and j != i:
            return f"error: there is already a profile called {self.entries[j]['name']}"
        self.entries[i]["name"] = to
        self.save()
        return ""

    def delete(self, name: str) -> str:
        if self.unreadable:
            return f"error: {self.unreadable}"
        i = self._index(name)
        if i < 0:
            return f"error: there is no profile called {str(name).strip() or '(nothing)'}"
        del self.entries[i]
        self.save()
        return ""

    def replace(self, entries: list) -> str:
        """Put this list in place of the one kept. "" when done, otherwise why not.

        What a settings file being imported does with its profiles. **Replaced and not merged**,
        because that is what a backup means: a list that kept a profile the file does not carry is
        not the list that was saved.

        A file that could not be read is never saved over, exactly as in every other mutator here.
        An entry that is not an object, or has no name, or repeats a name already taken, is passed
        over rather than refused -- one bad row in somebody's backup is not a reason to drop the
        rest of it. A look that cannot be read at all is refused, with the sentence `normalise`
        raised, and nothing is changed.

        A profile naming a preset this machine does not have is taken all the same, and that is
        deliberate: `trouble()` lists it with the reason beside its name and refuses to load it,
        which is the behaviour that already exists, and it is why `normalise` checks the shape and
        not what is installed here.
        """
        if self.unreadable:
            return f"error: {self.unreadable}"
        fresh: list = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or "").strip()[:NAME_LIMIT]
            if not name or any(e["name"].casefold() == name.casefold() for e in fresh):
                continue
            try:
                fresh.append({"name": name, "look": normalise(entry.get("look") or {})})
            except ValueError as e:
                return f"error: {name}: {e}"
        self.entries = fresh
        self.save()
        return ""

    def save(self) -> None:
        # The whole list, every time, like `state.json`: a field this app stops keeping disappears
        # on the next save with no migration to write.
        state.write_json(PATH, {"version": VERSION,
                                "profiles": [{"name": e["name"], "look": e["look"]}
                                             for e in self.entries]})
