"""KyprX's own tiling, as the daemon knows it: the settings in `kwinrc [Script-kyprx]` and what
each one reads as when it is missing, the zone layouts and the arrangements -- one JSON value, in
one of two shapes -- and the answer the compositor script asks for.

**The engine runs in the compositor script, and the script never reads this group.** A script reads
its settings through `KWin.readConfig`, which sees a change to `kwinrc` only after the compositor is
reconfigured (read in KWin 6.7.5's source) -- and a reconfigure, with the tiler unloaded around it
so that it would read itself again, is what every change cost a tiling script that reads `kwinrc`:
the screen stopped for 558 ms and for 656 ms on two gap changes made that way, measured by the gap
between frames (`scripts/stall.py`), and every window was tiled again. So the daemon reads the group
and resolves it into one answer (`resolve`), and the script asks for that answer over the bus --
`Tiling()` on `/Windows` -- when it loads, at every `KyprXInventory`, and each time the daemon
invokes its `KyprXTiling` action after a write, and applies an answer only when its text differs
from the last one it applied. Asking at every inventory is what lets the daemon know the script's
version soon after a start of its own, which always asks for one. A change to the tiling asks the
compositor for nothing else.

**Pure**: no bus, no Qt, no file. It takes a group the way `kconfig.KConfig` holds one, so a key
with no value -- the `[$d]` marker, which reads back as something other than a string -- reads here
as a key that is not there. The daemon's answer, the folder, the migration, the copies of the desk
and the tests all go through these readings. The window keeps its own copy of the rules of the
newest shape (`gui/splits.py`, which cannot import this), and a test holds the two to one verdict
and one text.

**The arrangements are somebody's content, like a profile.** `daemon/defaults.py` declares none,
so *Restore defaults* and taking KyprX off the desk leave them where they are, and a group without
the key means KyprX's own zone layouts and arrangements (`DEFAULT_VALUE`).

**Two shapes, and both are read for as long as there is KyprX.** In version 1 every arrangement
holds its own layouts, one for each number of windows. In version 2 the zone layouts are one pool
-- each with a name, and whether dragging a window offers its zones -- and an arrangement names one
of them for each number of windows. This module writes version 2, and reads version 1 for good:
copies of the desk and KyprX folders kept in git carry it, and they are somebody's. Nothing
migrates a stored value. What a value *means* -- to the engine, to the window -- is its upgrade
(`upgrade`), made each time it is read, and two values in different versions are the same when
their upgrades are (`alike`), so a desk and its folder stay in version 1 until somebody edits on
the Tiling tab or a version-2 value reaches the desk; what *carries* one -- the folder, a settings
file, `SetGroups`, a copy of the desk -- keeps the version it was given. Two in one version are the
same only as one text: an earlier KyprX reading the same folder reads more in version 1 than the
upgrade keeps.
"""

from __future__ import annotations

import copy
import json
import re
import unicodedata

#: The shape this KyprX writes, and the newest it reads. A higher one is refused with a sentence of
#: its own: rewriting a newer KyprX's value would lose whatever the newer shape added.
FORMAT = 2

#: The first shape, where every arrangement holds its own layouts. Read, never written; the
#: module's docstring says why the reader stays.
FIRST_FORMAT = 1

#: The shape of the answer `Tiling()` gives the compositor script, which is the first thing the
#: script checks in it. Fields are only ever added to it, so an engine of an earlier version reads
#: an answer of a later daemon -- the running one until the next login, say.
ANSWER_VERSION = 1

#: The most windows an arrangement has a layout for, one for each number of windows from one up,
#: and so the most zones a zone layout has. A window that opens past an arrangement's last layout
#: does what *When the arrangement is full* says.
MAX_WINDOWS = 9

#: How deep splits nest. A layout that is one zone is depth 0; each split puts its parts one deeper.
MAX_DEPTH = 6

#: The smallest part a split may give, in percent.
MIN_SHARE = 5

#: A name, after the spaces at either end are taken off, and an id: an arrangement's and a zone
#: layout's alike.
NAME_MAX = 40
ID_MAX = 32
_ID = re.compile(r"[a-z0-9-]{1,32}")


class ArrangementsError(ValueError):
    """What is wrong with some arrangements, in one plain sentence -- the one `SetGroups` answers
    with, the Tiling tab shows, and the folder's problems list."""


class DesktopsError(ValueError):
    """What is wrong with the arrangement chosen for each desktop, in one plain sentence."""


#: What joins a desktop's name to the number of a desktop KyprX made after it, "Room · 2": the
#: engine's `CHAIN_MARK`, held to it by tests/test_script_contract.py.
CHAIN_MARK = " \u00b7 "

#: The most desktops the arrangement chosen for each can name: the 25 a compositor allows
#: (`MAX_DESKTOPS` in engine.mjs) four times over, since names of another machine's desktops,
#: carried by a KyprX folder both share, stay in it.
MOST_DESKTOPS = 100


def chain_name(name: str) -> tuple[str, int] | None:
    """A desktop's name read as one KyprX made, `(base, n)` for "<base> · <n>" -- n a whole number
    from 2, written without a leading zero -- and None for any other name: the engine's
    `chainName`, which tests/test_script_contract.py holds this to over a table of names."""
    text = str(name)
    at = text.rfind(CHAIN_MARK)
    if at < 0:
        return None
    digits = text[at + len(CHAIN_MARK):]
    if not digits.isascii() or not digits.isdigit() or digits.startswith("0"):
        return None
    n = int(digits) if len(digits) <= 16 else None
    if n is None or n < 2 or n > 2 ** 53:
        return None
    return text[:at], n


def made_desktops(listed: list[dict]) -> set[str]:
    """The ids of the desktops KyprX made, by the engine's rule (`markOf`): a chain name whose base
    is the exact name of another desktop."""
    names = [(str(d.get("id")), str(d.get("name"))) for d in listed]
    out = set()
    for ident, name in names:
        mark = chain_name(name)
        if mark and any(other != ident and other_name == mark[0] for other, other_name in names):
            out.add(ident)
    return out


def desktops_of(raw) -> dict[str, str]:
    """The arrangement chosen for each desktop as the engine is told it: desktop name to an
    arrangement's id. Anything that is not such an object -- the key absent, text that is not
    JSON -- reads as none chosen, and an entry that is not text to text is passed over."""
    try:
        value = json.loads(raw) if isinstance(raw, str) and raw.strip() else {}
    except (ValueError, RecursionError):
        return {}
    if not isinstance(value, dict):
        return {}
    return {name: ident for name, ident in value.items()
            if isinstance(name, str) and name and isinstance(ident, str) and _ID.fullmatch(ident)}


def canonical_desktops(value) -> str | None:
    """The one text the arrangement chosen for each desktop is written as: compact JSON, its
    desktops by name in order. None for an empty one, which takes the key away -- every desktop on
    the first arrangement in the rotation again. Text is read as JSON first, so the text `Groups`
    gave sends back as itself. Raises `DesktopsError` for anything else: not an object, a name that
    is empty or not text, an id that is not an arrangement's kind of id, or more than
    `MOST_DESKTOPS` desktops."""
    if isinstance(value, str):
        try:
            value = json.loads(value) if value.strip() else {}
        except (ValueError, RecursionError):
            raise DesktopsError("The arrangement chosen for each desktop is not JSON.") from None
    if not isinstance(value, dict):
        raise DesktopsError("The arrangement chosen for each desktop has to be an object, from "
                            "a desktop's name to an arrangement's id.")
    if len(value) > MOST_DESKTOPS:
        raise DesktopsError(f"An arrangement can be chosen for {MOST_DESKTOPS} desktops at most.")
    for name, ident in value.items():
        if not isinstance(name, str) or not name:
            raise DesktopsError("A desktop is named by text that is not empty.")
        if not isinstance(ident, str) or not _ID.fullmatch(ident):
            raise DesktopsError(f"The arrangement chosen for {name!r} is not an arrangement's "
                                f"id.")
    if not value:
        return None
    return json.dumps(dict(sorted(value.items())), ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------- reading a value

def _whole(value) -> bool:
    """A whole number, and not true or false: Python counts a bool as an int, JSON never does."""
    return isinstance(value, int) and not isinstance(value, bool)


def _windows(count: int) -> str:
    return f"{count} window" + ("" if count == 1 else "s")


def _node(node, depth: int, where: str, root: bool = False) -> tuple[dict, int]:
    """One node, checked and copied -- a zone `{}`, or a split of two parts or more -- and how many
    zones it holds. `master` belongs to a layout's root and to nothing under it."""
    if not isinstance(node, dict):
        raise ArrangementsError(f"{where} has a part that is not a zone or a split.")
    keys = set(node) - ({"master"} if root else set())
    if not keys:
        return {}, 1
    unknown = sorted(keys - {"split", "sizes", "parts"})
    if unknown:
        raise ArrangementsError(f'{where} carries "{unknown[0]}", which this KyprX does not know.')
    if keys != {"split", "sizes", "parts"}:
        missing = sorted({"split", "sizes", "parts"} - keys)[0]
        raise ArrangementsError(f"{where} has a split with no {missing}.")
    split, sizes, parts = node["split"], node["sizes"], node["parts"]
    if split not in ("h", "v"):
        raise ArrangementsError(f"{where} has a split that is neither h (side by side) nor v "
                                f"(top to bottom).")
    if (not isinstance(sizes, list) or not isinstance(parts, list) or len(parts) < 2
            or len(sizes) != len(parts)):
        raise ArrangementsError(f"{where} has a split that is not two parts or more, each with "
                                f"a size.")
    if depth + 1 > MAX_DEPTH:
        raise ArrangementsError(f"{where} nests its splits more than {MAX_DEPTH} deep.")
    # Each part is a zone at least, so a split of more parts than a layout may have zones is
    # refused before it is walked: a value from a file somebody edited can be any size at all.
    if len(parts) > MAX_WINDOWS:
        raise ArrangementsError(f"{where} has more than {MAX_WINDOWS} zones.")
    if not all(_whole(s) and s >= MIN_SHARE for s in sizes):
        raise ArrangementsError(f"{where} has a part smaller than {MIN_SHARE} %, or one that is "
                                f"not a whole percent.")
    total = sum(sizes)
    if total != 100:
        # The total is said only while it is short. The reader turns at most 4300 digits into a
        # number (Python's limit, `sys.get_int_max_str_digits`), but two parts that long can add
        # up to a number of 4301 digits, and turning that back into text raised a plain
        # ValueError -- measured on Python 3.14 -- out of every reader of the arrangements, which
        # catch this module's error alone. `gui/splits.py` says it the same way.
        raise ArrangementsError(
            f"{where} has a split whose parts add up to {total} %, not 100." if total < 10 ** 6
            else f"{where} has a split whose parts add up to far more than 100 %.")
    copied, count = [], 0
    for part in parts:
        normal, inside = _node(part, depth + 1, where)
        copied.append(normal)
        count += inside
    return {"split": split, "sizes": list(sizes), "parts": copied}, count


def _master(root: dict, normal: dict, count: int, where: str) -> None:
    """The root's master zone, checked, onto its normalised copy: one of its `count` zones, counted
    from 0 in depth-first order, and left out at 0 -- the default -- so that a layout has one
    canonical text."""
    if "master" in root:
        master = root["master"]
        if not _whole(master) or not 0 <= master < count:
            raise ArrangementsError(f"{where} names a master zone it does not have: the zones are "
                                    f"0 to {count - 1}.")
        if master:
            normal["master"] = master


# ------------------------------------------------ version 1: every arrangement holds its layouts

def _layout(root, count: int, where: str) -> dict:
    """The layout for `count` windows, checked and copied: exactly that many zones, and its master
    one of them."""
    normal, found = _node(root, 0, where, root=True)
    if found != count:
        raise ArrangementsError(f"{where} has {found} zone{'' if found == 1 else 's'}, and it "
                                f"needs {count}.")
    _master(root, normal, count, where)
    return normal


def _arrangement(entry, position: int, ids: set, names: set) -> dict:
    if not isinstance(entry, dict):
        raise ArrangementsError(f"Arrangement {position} is not an object with names in it.")
    unknown = sorted(set(entry) - {"id", "name", "cycle", "manual", "layouts"})
    if unknown:
        raise ArrangementsError(f'Arrangement {position} carries "{unknown[0]}", which this KyprX '
                                f"does not know.")
    missing = [key for key in ("id", "name", "manual", "layouts") if key not in entry]
    if missing:
        raise ArrangementsError(f"Arrangement {position} has no {missing[0]}.")
    ident, name, called = _named_entry(entry, position, "Arrangement", "arrangements", ids, names)
    cycle = _cycle(entry, called)
    layouts = entry["layouts"]
    if not isinstance(layouts, list) or not 1 <= len(layouts) <= MAX_WINDOWS:
        raise ArrangementsError(f"The arrangement {called} needs from 1 to {MAX_WINDOWS} layouts, "
                                f"one for each number of windows.")
    normal = [_layout(root, count, f"The layout for {_windows(count)} in {called}")
              for count, root in enumerate(layouts, 1)]
    manual = entry["manual"]
    if not _whole(manual) or not 1 <= manual <= len(normal):
        raise ArrangementsError(f"The arrangement {called} has to say which layout manual tiling "
                                f"shows, by its number of windows: 1 to {len(normal)}.")
    ids.add(ident)
    names.add(name.casefold())
    return {"id": ident, "name": name, "cycle": cycle, "manual": manual, "layouts": normal}


def _named_entry(entry: dict, position: int, kind: str, plural: str, ids: set,
                 names: set) -> tuple[str, str, str]:
    """An entry's id and name, checked against the others of its list: `(id, name, "name")` --
    the last quoted, the way every sentence about it names it. An arrangement and a zone layout
    are two lists, so one of each may share a name or an id."""
    ident = entry["id"]
    if not isinstance(ident, str) or not _ID.fullmatch(ident):
        raise ArrangementsError(f"{kind} {position} needs an id of 1 to {ID_MAX} lower-case "
                                f"letters, digits and dashes.")
    if ident in ids:
        raise ArrangementsError(f'Two {plural} have the id "{ident}".')
    name = entry["name"].strip() if isinstance(entry["name"], str) else ""
    if not 1 <= len(name) <= NAME_MAX:
        raise ArrangementsError(f"{kind} {position} needs a name of 1 to {NAME_MAX} characters.")
    called = f'"{name}"'
    if name.casefold() in names:
        raise ArrangementsError(f"Two {plural} are called {called}.")
    return ident, name, called


def _cycle(entry: dict, called: str) -> bool:
    # Absent means in the rotation, the way `gui/splits.py` reads it: the canonical text always
    # carries the word, so only a value somebody wrote by hand can lack it.
    cycle = entry.get("cycle", True)
    if not isinstance(cycle, bool):
        raise ArrangementsError(f"The arrangement {called} has to say whether it is in the "
                                f"rotation with true or false.")
    return cycle


def _first_format(obj: dict) -> dict:
    """Version 1, normalised exactly as this module normalised it before version 2 existed, and
    refused in the same sentences: the ones somebody holding such a value may have seen."""
    unknown = sorted(set(obj) - {"version", "arrangements"})
    if unknown:
        raise ArrangementsError(f'The arrangements carry "{unknown[0]}", which this KyprX does '
                                f"not know.")
    listed = obj.get("arrangements")
    if not isinstance(listed, list) or not listed:
        raise ArrangementsError("There has to be one arrangement at least.")
    ids: set = set()
    names: set = set()
    normal = [_arrangement(entry, position, ids, names)
              for position, entry in enumerate(listed, 1)]
    if not any(a["cycle"] for a in normal):
        raise ArrangementsError("One arrangement at least has to be in the rotation.")
    return {"version": FIRST_FORMAT, "arrangements": normal}


# ------------------------------------------------ version 2: one pool of zone layouts

def _tree(root, where: str) -> tuple[dict, int]:
    """A zone layout's tree, checked and copied, and how many zones it has: two to
    `MAX_WINDOWS`. One zone is the whole screen, which every arrangement has for one window and
    which is no zone layout."""
    normal, found = _node(root, 0, where, root=True)
    if not 2 <= found <= MAX_WINDOWS:
        raise ArrangementsError(f"{where} has {found} zone{'' if found == 1 else 's'}, and a zone "
                                f"layout has 2 to {MAX_WINDOWS}.")
    _master(root, normal, found, where)
    return normal, found


def _zone_layout(entry, position: int, ids: set, names: set) -> tuple[dict, int]:
    """One zone layout of the pool, checked and copied, and its number of zones."""
    if not isinstance(entry, dict):
        raise ArrangementsError(f"Zone layout {position} is not an object with names in it.")
    # Sorted as text: a value handed over as an object, and not read from JSON, can have keys
    # that are not text, and two of those sorted with text ones would raise a TypeError.
    unknown = sorted(set(entry) - {"id", "name", "drag", "tree"}, key=str)
    if unknown:
        raise ArrangementsError(f'Zone layout {position} carries "{unknown[0]}", which this KyprX '
                                f"does not know.")
    missing = [key for key in ("id", "name", "tree") if key not in entry]
    if missing:
        raise ArrangementsError(f"Zone layout {position} has no {missing[0]}.")
    ident, name, called = _named_entry(entry, position, "Zone layout", "zone layouts", ids, names)
    # Absent means offered, for the reason `cycle` gives: only a hand-written value lacks it.
    drag = entry.get("drag", True)
    if not isinstance(drag, bool):
        raise ArrangementsError(f"The zone layout {called} has to say whether dragging a window "
                                f"offers it with true or false.")
    tree, count = _tree(entry["tree"], f"The zone layout {called}")
    ids.add(ident)
    names.add(name.casefold())
    return {"id": ident, "name": name, "drag": drag, "tree": tree}, count


def _slots(entry: dict, called: str, pool: dict[str, tuple[str, int]]) -> dict[str, str]:
    """An arrangement's zone layouts by number of windows: the keys exactly "2" up to its last,
    with none left out -- none with a nought in front, and nine windows at most -- and each value
    the id of a zone layout with that many zones. `{}` is an arrangement of the whole screen
    alone."""
    slots = entry["windows"]
    if not isinstance(slots, dict):
        raise ArrangementsError(f"The arrangement {called} has to name its zone layouts by number "
                                f"of windows, in an object.")
    last = len(slots) + 1
    if last > MAX_WINDOWS or set(slots) != {str(count) for count in range(2, last + 1)}:
        raise ArrangementsError(f"The arrangement {called} has to name one zone layout for each "
                                f"number of windows from 2 up, none left out, to {MAX_WINDOWS} at "
                                f"most.")
    normal = {}
    for count in range(2, last + 1):
        ident = slots[str(count)]
        if not isinstance(ident, str) or ident not in pool:
            raise ArrangementsError(f"The arrangement {called} uses a zone layout for "
                                    f"{_windows(count)} that is not there.")
        name, zones = pool[ident]
        if zones != count:
            raise ArrangementsError(f'The arrangement {called} uses "{name}" for '
                                    f"{_windows(count)}, and it has {zones} zones.")
        normal[str(count)] = ident
    return normal


def _arrangement_2(entry, position: int, ids: set, names: set,
                   pool: dict[str, tuple[str, int]]) -> dict:
    if not isinstance(entry, dict):
        raise ArrangementsError(f"Arrangement {position} is not an object with names in it.")
    unknown = sorted(set(entry) - {"id", "name", "cycle", "windows"}, key=str)
    if unknown:
        raise ArrangementsError(f'Arrangement {position} carries "{unknown[0]}", which this KyprX '
                                f"does not know.")
    missing = [key for key in ("id", "name", "windows") if key not in entry]
    if missing:
        raise ArrangementsError(f"Arrangement {position} has no {missing[0]}.")
    ident, name, called = _named_entry(entry, position, "Arrangement", "arrangements", ids, names)
    cycle = _cycle(entry, called)
    windows = _slots(entry, called, pool)
    ids.add(ident)
    names.add(name.casefold())
    return {"id": ident, "name": name, "cycle": cycle, "windows": windows}


def _second_format(obj: dict) -> dict:
    """Version 2: the pool, then the arrangements that name its layouts. No limit on how many of
    either: an upgrade of many arrangements adds a zone layout for every layout the pool did not
    have, and a value this reads it takes whole. The window limits what it adds itself."""
    unknown = sorted(set(obj) - {"version", "layouts", "arrangements"}, key=str)
    if unknown:
        raise ArrangementsError(f'The arrangements carry "{unknown[0]}", which this KyprX does '
                                f"not know.")
    listed = obj.get("layouts")
    if not isinstance(listed, list) or not listed:
        raise ArrangementsError("There has to be one zone layout at least.")
    ids: set = set()
    names: set = set()
    layouts, pool = [], {}
    for position, entry in enumerate(listed, 1):
        layout, count = _zone_layout(entry, position, ids, names)
        layouts.append(layout)
        pool[layout["id"]] = (layout["name"], count)
    if not any(layout["drag"] for layout in layouts):
        raise ArrangementsError("One zone layout at least has to be offered when a window is "
                                "dragged.")
    listed = obj.get("arrangements")
    if not isinstance(listed, list) or not listed:
        raise ArrangementsError("There has to be one arrangement at least.")
    ids, names = set(), set()
    normal = [_arrangement_2(entry, position, ids, names, pool)
              for position, entry in enumerate(listed, 1)]
    if not any(a["cycle"] for a in normal):
        raise ArrangementsError("One arrangement at least has to be in the rotation.")
    return {"version": FORMAT, "layouts": layouts, "arrangements": normal}


def validate(obj) -> dict:
    """A normalised copy of a value, in its own version, or `ArrangementsError` saying what is
    wrong.

    Normalised the way the canonical text needs it: names without spaces at either end, `cycle`
    and `drag` always there, `master` only where it is not the first zone, whole numbers only, and
    nothing else -- a name this version does not know is refused rather than dropped, so that
    nothing a newer KyprX wrote is lost by being rewritten here. The version is read first, so a
    value from a newer KyprX is refused for that and not for a name it added; version 1 is read
    by its own rules (`_first_format`), and stays version 1 -- `upgrade` is what makes it 2.
    """
    if not isinstance(obj, dict):
        raise ArrangementsError("The arrangements have to be an object with a version and a list "
                                "of arrangements in it.")
    version = obj.get("version")
    if _whole(version) and version > FORMAT:
        raise ArrangementsError(f"The arrangements were written by a newer KyprX: they are "
                                f"version {version}, and this one reads version {FORMAT}.")
    if _whole(version) and version == FIRST_FORMAT:
        return _first_format(obj)
    if _whole(version) and version == FORMAT:
        return _second_format(obj)
    unknown = sorted(set(obj) - {"version", "layouts", "arrangements"}, key=str)
    if unknown:
        raise ArrangementsError(f'The arrangements carry "{unknown[0]}", which this KyprX does '
                                f"not know.")
    raise ArrangementsError(f"The arrangements have to say they are version {FIRST_FORMAT} or "
                            f"{FORMAT}.")


def parse(text: str) -> dict:
    """The arrangements a text holds, validated, in their own version."""
    if not isinstance(text, str):
        raise ArrangementsError("The arrangements have to be text, as JSON.")
    try:
        found = json.loads(text)
    except json.JSONDecodeError as e:
        raise ArrangementsError(f"The arrangements are not readable JSON: {e.msg} at line "
                                f"{e.lineno}, column {e.colno}.") from e
    except ValueError as e:
        # After the clause above, which catches a subclass of this. A whole number longer than
        # Python's limit for turning digits into a number (4300 digits by default,
        # `sys.get_int_max_str_digits`) is refused by the reader with a plain ValueError rather
        # than a JSONDecodeError -- measured on Python 3.14 -- and every reader of the
        # arrangements catches this module's error alone.
        raise ArrangementsError("The arrangements are not readable JSON: a number in them is "
                                "too long.") from e
    except RecursionError as e:
        # A text nested thousands deep stops the reader before any rule here could: one
        # sentence like the others, rather than the error escaping into whoever asked.
        raise ArrangementsError("The arrangements are not readable JSON: they nest too deep.") from e
    return validate(found)


def canonical(value) -> str:
    """The one text a value is written as, in its own version, from the value or from any text of
    it.

    Two texts of the same value are the same text once canonical, which is what lets the window
    decide whether anything changed without being fooled by spacing or key order, and what
    `SetGroups` writes. A version-1 value and its upgrade mean the same and are two texts:
    whoever compares two values asks `alike`, which goes by this text within one version and by
    the upgrades' across two.
    """
    normal = parse(value) if isinstance(value, str) else validate(value)
    return json.dumps(normal, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------- names and ids

def slug(name: str) -> str:
    """A name as an id: letters without their accents, digits, and single dashes between them.
    The window's rule (`gui/splits.py`), and a test holds the two to one answer."""
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")
    return text[:ID_MAX].strip("-")


def make_id(name: str, taken, empty: str = "layout") -> str:
    """A new id: the name as a slug, with `-2`, `-3`… when that is taken, and `<empty>-1`, `-2`…
    for a name with nothing a slug can keep. The window's rule, which names the zone layouts it
    adds the same way (`gui/splits.py`)."""
    base = slug(name)
    if base and base not in taken:
        return base
    stem, n = (base, 2) if base else (empty, 1)
    while True:
        suffix = f"-{n}"
        candidate = stem[:ID_MAX - len(suffix)].rstrip("-") + suffix
        if candidate not in taken:
            return candidate
        n += 1


def slot_name(names, base: str, count: int) -> str:
    """The name of a zone layout made for an arrangement's layout for `count` windows:
    `<base> (k zones)`, or `<base> (k zones) 2`, ` 3`… when a name among `names` has that already,
    case ignored -- the arrangement's name cut, and its spaces at the end taken off, so that the
    whole fits in `NAME_MAX`. What the upgrade names the layouts it adds: the window makes no zone
    layout for an arrangement, and names none this way."""
    taken = {name.casefold() for name in names}
    tail = f" ({count} zones)"
    n = 1
    while True:
        suffix = "" if n == 1 else f" {n}"
        candidate = base[:NAME_MAX - len(tail) - len(suffix)].rstrip() + tail + suffix
        if candidate.casefold() not in taken:
            return candidate
        n += 1


# ---------------------------------------------------------------- the upgrade, and the meaning

def _text_of(node: dict) -> str:
    """A tree's canonical text: two trees are one layout when theirs are one text."""
    return json.dumps(node, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def upgrade(value) -> dict:
    """What a value means in the newest shape: a version-2 value as it is, and a version-1 one
    made into version 2. Text is read first. Raises `ArrangementsError` only for what `validate`
    refuses, and never for a value it takes.

    1. The pool is a copy of `UPGRADE_POOL`, in its order and with its own drag flags.
    2. Each arrangement in its order, and in it each layout from two windows up: a tree a zone
       layout already holds -- the same canonical text, master zone included, the first that
       holds it -- is that zone layout; any other is added after the last, named after the
       arrangement and its number of zones (`slot_name`), with an id made of that name
       (`make_id`), and not offered on a drag.
    3. The layout an arrangement's manual tiling showed is offered on a drag, so the zones a drag
       started from are still offered; `manual` 1, the whole screen, is no zone layout and marks
       nothing. Version 1's bar offered every layout of the screen's arrangement, and nothing more
       is ticked for that: a layout `UPGRADE_POOL` does not tick and no arrangement's `manual`
       names leaves the bar until somebody turns *Offer on drag* on for it (KNOWN-ISSUES.md).
    4. The arrangements keep their ids, names, rotation and order.

    The same value always gives the same value, which is what lets two readings of one stored
    text agree with nothing written, and an upgrade's upgrade is itself. It is not one-to-one:
    step 3 keeps nothing of a `manual` whose zone layout a drag offers already, which is why two
    values are compared by `alike` and not by their upgrades alone.
    """
    normal = parse(value) if isinstance(value, str) else validate(value)
    if normal["version"] == FORMAT:
        return normal
    layouts = copy.deepcopy(list(UPGRADE_POOL))
    held: dict[str, int] = {}
    for at, layout in enumerate(layouts):
        held.setdefault(_text_of(layout["tree"]), at)
    names = [layout["name"] for layout in layouts]
    ids = {layout["id"] for layout in layouts}
    dragged: set[str] = set()
    arrangements = []
    for entry in normal["arrangements"]:
        windows = {}
        for count, tree in enumerate(entry["layouts"][1:], 2):
            text = _text_of(tree)
            if text not in held:
                name = slot_name(names, entry["name"], count)
                ident = make_id(name, ids)
                layouts.append({"id": ident, "name": name, "drag": False,
                                "tree": copy.deepcopy(tree)})
                held[text] = len(layouts) - 1
                names.append(name)
                ids.add(ident)
            windows[str(count)] = layouts[held[text]]["id"]
        if entry["manual"] >= 2:
            dragged.add(windows[str(entry["manual"])])
        arrangements.append({"id": entry["id"], "name": entry["name"], "cycle": entry["cycle"],
                             "windows": windows})
    for layout in layouts:
        layout["drag"] = layout["drag"] or layout["id"] in dragged
    return validate({"version": FORMAT, "layouts": layouts, "arrangements": arrangements})


def _readable(value) -> dict | None:
    """`validate`'s copy of a value, or None for one it refuses."""
    try:
        return validate(value)
    except ArrangementsError:
        return None


def alike(a, b) -> bool:
    """Do two zone layouts and arrangements say the same thing to every KyprX that reads them?
    Each is a value as JSON holds it, never a text of one: whoever holds texts reads them first
    (`parse`), because what a text that does not read stands for is theirs to say.

    - **Two in one version** are alike only when they are one canonical text. Not when their
      upgrades are: the upgrade keeps nothing of what version 1 calls `manual` -- the layout
      manual tiling shows, *Zones for manual tiling* in an earlier KyprX -- wherever the zone
      layout it names is offered on a drag already (`upgrade`, step 3), so two version-1 values
      that differ there alone upgrade to one value, while to an earlier KyprX, which reads a
      KyprX folder it shares with this one, they are two choices. Compared by their upgrades, a
      choice made there was taken here for no change and kept off this desk, and the next change
      made here wrote the earlier choice back into the folder, which undid it there without a
      word: measured with the KyprX from before version 2 and this one sharing one folder, each
      through its own folder pass, Balanced's *Zones for manual tiling* moved from four windows
      to two.
    - **Two in different versions** are alike when their upgrades are one text. Only a KyprX that
      reads both holds one of each, and to it they mean the same: that is what the window hands
      back, in version 2, for a desk still in version 1, and what a folder from a machine that
      has edited carries -- none of it a change.
    - **Anything no rule of either version takes** -- a text in the value's place, which is
      arrangements nobody could read, carried as they are; a value from a newer KyprX; the
      folder's marker for a name that is not there -- is alike only to the same text or value,
      and never to one a rule takes: there is nothing in it to read, and it is somebody's work.

    The one rule for both of the daemon's askers, so that a desk and its folder agree on what a
    change is: `DeskPart._tiling_value_alike`, of two texts it has read, and the folder's merge
    (`folder.merge`), of each pair of the four sides it weighs.
    """
    first, second = _readable(a), _readable(b)
    if first is None or second is None:
        return first is None and second is None and a == b
    if first["version"] == second["version"]:
        return canonical(first) == canonical(second)
    return canonical(upgrade(first)) == canonical(upgrade(second))


def _in_order(node: dict) -> dict:
    """A copy of a checked tree with its keys in the order the answer has always had them --
    split, sizes, parts, then master -- because the engine of the last version tells an edit from
    no edit by comparing the text of each arrangement's layouts (`JSON.stringify`, in
    `engine.mjs`): the same layouts in another key order would read to it as an edit nobody
    made."""
    if not node.get("split"):
        return {}
    out = {"split": node["split"], "sizes": list(node["sizes"]),
           "parts": [_in_order(part) for part in node["parts"]]}
    if node.get("master"):
        out["master"] = node["master"]
    return out


def expanded(value) -> list[dict]:
    """The arrangements of a value as the engine is answered them, in version 1's terms: each one
    `{id, name, cycle, manual, layouts}`, its layouts one for each number of windows from one up
    -- the whole screen first, then each zone layout's tree -- and `manual` the most windows whose
    zone layout a drag offers, or its last layout's when none is offered (1 for an arrangement of
    the whole screen alone).

    For a desk whose value is still in version 1 this is the very text the answer carried before
    version 2 wherever no layout past the one manual tiling showed is offered on a drag after the
    upgrade -- KyprX's own four arrangements, and any whose manual tiling showed its last layout,
    among them -- so the engine still running from before the update sees no change there. Where
    one is, `manual` is that layout's number of windows: the zones a drag offers grow by the ones
    the pool offers. The engine of this version reads `pool` beside it and tiles by the zone
    layouts themselves.
    """
    normal = upgrade(value)
    pool = {layout["id"]: layout for layout in normal["layouts"]}
    out = []
    for entry in normal["arrangements"]:
        last = len(entry["windows"]) + 1
        held = [pool[entry["windows"][str(count)]] for count in range(2, last + 1)]
        dragged = [count for count, layout in enumerate(held, 2) if layout["drag"]]
        out.append({"id": entry["id"], "name": entry["name"], "cycle": entry["cycle"],
                    "manual": dragged[-1] if dragged else last,
                    "layouts": [{}] + [_in_order(layout["tree"]) for layout in held]})
    return out


# ---------------------------------------------------------------- KyprX's own

def _h(sizes: list[int], parts: list[dict] | None = None) -> dict:
    """A split side by side, of zones unless `parts` says otherwise. A new object every call, so
    no two layouts below share one."""
    return {"split": "h", "sizes": list(sizes), "parts": parts or [{} for _ in sizes]}


def _v(sizes: list[int], parts: list[dict] | None = None) -> dict:
    """A split top to bottom; see `_h`."""
    return {"split": "v", "sizes": list(sizes), "parts": parts or [{} for _ in sizes]}


def _pool(*entries: tuple[str, str, bool, dict]) -> list[dict]:
    return [{"id": ident, "name": name, "drag": drag, "tree": tree}
            for ident, name, drag, tree in entries]


def _checked_pool(layouts: list[dict]) -> tuple[dict, ...]:
    ids: set = set()
    names: set = set()
    return tuple(_zone_layout(entry, position, ids, names)[0]
                 for position, entry in enumerate(layouts, 1))


#: The zone layouts every upgrade from version 1 starts its pool with, in this order (two zones,
#: then three, four and five), with their drag flags. **Frozen**: the upgrade has to give the same
#: value for the same stored text in every KyprX to come, or two KyprX reading one folder would
#: disagree about what it means. So this is its own literal and never `DEFAULT_VALUE`'s, which may
#: change; a test pins its canonical text, and KyprX's own arrangements as version 1 had them,
#: upgraded through it, give `DEFAULT_VALUE` byte for byte today. A tuple, so nothing appends to it
#: by mistake.
UPGRADE_POOL: tuple[dict, ...] = _checked_pool(_pool(
    ("halves", "Two halves", True, _h([50, 50])),
    ("wide-left", "Wide left", True, _h([75, 25])),
    ("wide-right", "Wide right", False, _h([25, 75])),
    ("top-and-bottom", "Top and bottom", False, _v([50, 50])),
    ("half-left-two", "Half left, two stacked", True, _h([50, 50], [{}, _v([50, 50])])),
    ("wide-left-two", "Wide left, two stacked", False, _h([75, 25], [{}, _v([50, 50])])),
    ("centred-column", "Centred column", True, {**_h([25, 50, 25]), "master": 1}),
    ("three-columns", "Three columns", True, _h([33, 33, 34])),
    ("quarters", "Four quarters", True, _h([50, 50], [_v([50, 50]), _v([50, 50])])),
    ("wide-left-three", "Wide left, three stacked", False, _h([75, 25], [{}, _v([33, 33, 34])])),
    ("centred-right-split", "Centred column, right split", False,
     {**_h([25, 50, 25], [{}, {}, _v([50, 50])]), "master": 1}),
    ("spiral", "Spiral", True, _h([50, 50], [{}, _v([50, 50], [{}, _h([50, 50])])])),
    ("four-columns", "Four columns", False, _h([25, 25, 25, 25])),
    ("half-left-three", "Half left, three stacked", False, _h([50, 50], [{}, _v([33, 33, 34])])),
    ("centred-sides-split", "Centred column, sides split", False,
     {**_h([25, 50, 25], [_v([50, 50]), {}, _v([50, 50])]), "master": 2}),
))

#: What a desk tiles by when nothing else was chosen, and what *Put KyprX's zone layouts and
#: arrangements back* brings back -- by deleting the key, not by writing this. The pool the builder
#: starts from, and four arrangements, all in the rotation. Checked against every rule above as
#: this module loads, so a mistake here stops the daemon's checks rather than reaching a screen.
DEFAULT_VALUE = validate({"version": FORMAT, "layouts": _pool(
    ("halves", "Two halves", True, _h([50, 50])),
    ("wide-left", "Wide left", True, _h([75, 25])),
    ("wide-right", "Wide right", False, _h([25, 75])),
    ("top-and-bottom", "Top and bottom", False, _v([50, 50])),
    ("half-left-two", "Half left, two stacked", True, _h([50, 50], [{}, _v([50, 50])])),
    ("wide-left-two", "Wide left, two stacked", False, _h([75, 25], [{}, _v([50, 50])])),
    ("centred-column", "Centred column", True, {**_h([25, 50, 25]), "master": 1}),
    ("three-columns", "Three columns", True, _h([33, 33, 34])),
    ("quarters", "Four quarters", True, _h([50, 50], [_v([50, 50]), _v([50, 50])])),
    ("wide-left-three", "Wide left, three stacked", False, _h([75, 25], [{}, _v([33, 33, 34])])),
    ("centred-right-split", "Centred column, right split", False,
     {**_h([25, 50, 25], [{}, {}, _v([50, 50])]), "master": 1}),
    ("spiral", "Spiral", True, _h([50, 50], [{}, _v([50, 50], [{}, _h([50, 50])])])),
    ("four-columns", "Four columns", False, _h([25, 25, 25, 25])),
    ("half-left-three", "Half left, three stacked", False, _h([50, 50], [{}, _v([33, 33, 34])])),
    ("centred-sides-split", "Centred column, sides split", False,
     {**_h([25, 50, 25], [_v([50, 50]), {}, _v([50, 50])]), "master": 2}),
), "arrangements": [
    {"id": "balanced", "name": "Balanced", "cycle": True,
     "windows": {"2": "halves", "3": "half-left-two", "4": "quarters"}},
    {"id": "master-75", "name": "Master 75/25", "cycle": True,
     "windows": {"2": "wide-left", "3": "wide-left-two", "4": "wide-left-three"}},
    {"id": "centred-three", "name": "Centred Three Columns", "cycle": True,
     "windows": {"2": "halves", "3": "centred-column", "4": "centred-right-split",
                 "5": "centred-sides-split"}},
    {"id": "dwindle", "name": "Dwindle", "cycle": True,
     "windows": {"2": "halves", "3": "half-left-two", "4": "spiral"}},
]})


# ---------------------------------------------------------------- the group

#: The gaps, by their key and by their name in the answer.
_GAPS = {"screenGapTop": "top", "screenGapBottom": "bottom", "screenGapLeft": "left",
         "screenGapRight": "right", "screenGapBetween": "between"}

#: Every key of the group and the kind of value it holds: `bool` is true or false, `int` a whole
#: number in `RANGES`, `choice` one of the numbers in `RANGES`, `list` entries between commas,
#: `json` the zone layouts and arrangements' text, and `desktops` the arrangement each desktop
#: starts on, as JSON from a desktop's name to an arrangement's id (`desktops_of`). A key the group has beyond these means nothing
#: to the engine, and the folder and the copies of the desk carry it as it is.
#:
#: How the engine matches a list's entries is the script's, said here because these are the keys it
#: is said about: an entry with `*` in it is a glob, one in square brackets -- `[term]` -- a part of
#: the name, and anything else the whole of the window's class or of its resource name, case
#: ignored. Titles are parts of the title, case counting. Screens are the names the compositor
#: gives its outputs, such as `DP-1`.
KEYS: dict[str, str] = {
    "tiling": "bool", "autoTiling": "bool", "arrangements": "json",
    **{key: "int" for key in _GAPS},
    "floatUtility": "bool", "newWindowPosition": "choice", "newWindowOverflow": "choice",
    "newDesktopPosition": "choice", "adjustLayoutLive": "bool", "showOsd": "bool",
    "floatingClass": "list", "floatingTitle": "list", "ignoreClass": "list", "ignoreTitle": "list",
    "ignoreScreen": "list", "desktopArrangements": "desktops",
}

#: The numbers each numeric key takes. A gap outside its range is held to the nearer end of it; a
#: choice outside its own, or anything that is not a whole number, reads as the key's absent value.
#:
#: - `newWindowPosition`, where a window that opens goes in the screen's order: 0 at the end of the
#:   layout, 1 as the master, 2 before the focused window, 3 after it.
#: - `newWindowOverflow`, what a window that opens does when the screen already has a window in
#:   every zone of its arrangement's last layout: 0 goes to a new desktop, 1 floats in the middle
#:   of the screen, 2 squeezes in, its zone split from the last one (the cascade).
#: - `newDesktopPosition`, where that new desktop is made: 0 after the last desktop, 1 straight
#:   after the one the window came from.
RANGES: dict[str, tuple[int, int]] = {**{key: (0, 200) for key in _GAPS},
                                      "newWindowPosition": (0, 3), "newWindowOverflow": (0, 2),
                                      "newDesktopPosition": (0, 1)}

#: What each key reads as when the group does not have it: the engine's own defaults, as the text
#: the file would hold -- the arrangements as `DEFAULT_VALUE`'s canonical text, in version 2. Not
#: what KyprX declares (`defaults.SETTINGS["tiling"]`), and `tiling` is where the two part: absent,
#: it reads as off. That is what makes *Take KyprX off this desk* -- which deletes every key KyprX
#: declares -- leave a desk that no engine tiles, and it is why the migration writes the key rather
#: than leaving it out. Where the declaration and this agree, as they do for the gaps, nothing has
#: to be written for a desk to read the way KyprX wants.
DEFAULTS: dict[str, str] = {
    "tiling": "false", "autoTiling": "true", "arrangements": canonical(DEFAULT_VALUE),
    **{key: "10" for key in _GAPS},
    "floatUtility": "true", "newWindowPosition": "0", "newWindowOverflow": "1",
    "newDesktopPosition": "0", "adjustLayoutLive": "true", "showOsd": "true",
    "floatingClass": "", "floatingTitle": "", "ignoreClass": "", "ignoreTitle": "",
    "ignoreScreen": "", "desktopArrangements": "",
}

#: The engine's own list of classes it never tiles is `policy.AUTO_SKIP` -- the windows that are
#: never touched on their own, which are the same windows -- and these two besides: the drop-down
#: terminal and the lock screen's greeter.
_IGNORED_TOO = ("yakuake", "kscreenlocker_greet")

_NUMBER = re.compile(r"-?[0-9]+")


def _text(group, key: str) -> str | None:
    """A key's value when it is text, and None when it is absent or a key with no value."""
    raw = group.get(key) if isinstance(group, dict) else None
    return raw if isinstance(raw, str) else None


def entries(raw) -> list[str]:
    """A comma-separated list as the engine reads it: every entry trimmed, the empty ones dropped.
    Anything that is not text -- an absent key, a key with no value -- is an empty list."""
    return [x.strip() for x in raw.split(",") if x.strip()] if isinstance(raw, str) else []


def value_of(group: dict, key: str):
    """One key of the group as the engine acts on it: a bool, a whole number, a list of entries, or
    the zone layouts and arrangements (what the stored value means, in version 2 -- or the default
    value when the stored text cannot be read).

    True and false are read in any case and anything else as the key's absent value. Raises
    `KeyError` for a key that is not one of `KEYS`: a typo that quietly read as a default would be
    the worst shape this could take.
    """
    kind = KEYS[key]
    raw = _text(group, key)
    if kind == "list":
        return entries(raw)
    if kind == "json":
        return arrangements_of(group)[0]
    if kind == "desktops":
        return desktops_of(raw)
    absent = DEFAULTS[key]
    if kind == "bool":
        word = (raw or "").strip().lower()
        return word == "true" if word in ("true", "false") else absent == "true"
    text = (raw or "").strip()
    number = None
    if _NUMBER.fullmatch(text):
        # Read without its leading zeros, and only while it is short. Python turns at most 4300
        # digits into a number (`sys.get_int_max_str_digits`) and raises a plain ValueError past
        # that -- measured on Python 3.14 -- which `resolve` passed on, and `Tiling()` told the
        # engine to tile nothing. A number longer than nine digits is past one end or the other
        # of every range here, and its sign says which.
        digits = text.lstrip("-").lstrip("0")
        number = int(digits or "0") if len(digits) <= 9 else 10 ** 9
        number = -number if text.startswith("-") else number
    low, high = RANGES[key]
    if kind == "int":
        return int(absent) if number is None else min(max(number, low), high)
    return number if number is not None and low <= number <= high else int(absent)


def arrangements_of(group: dict) -> tuple[dict, bool, str]:
    """What the engine tiles by and the window edits, whether the group stores any of it, and what
    is wrong with what it stores.

    `(value, stored, problem)`, the value always version 2 -- the stored one's upgrade -- and
    always a copy. Nothing stored: the default value, False, "". Stored and readable: what it
    means, True, "". Stored and not readable -- not JSON, or a value that breaks a rule, or one
    written by a newer KyprX -- the default value, True, and the sentence saying why: the engine
    tiles by the defaults meanwhile, and the stored text is left exactly as it is, because it is
    somebody's work and may be one edit away from readable. A key with no value (`[$d]`) is
    stored, and means the default.
    """
    stored = isinstance(group, dict) and "arrangements" in group
    raw = _text(group, "arrangements")
    if raw is None:
        return copy.deepcopy(DEFAULT_VALUE), stored, ""
    try:
        return upgrade(parse(raw)), True, ""
    except ArrangementsError as e:
        return copy.deepcopy(DEFAULT_VALUE), True, str(e)


def _builtin_ignore() -> list[str]:
    # Imported here, and not at the top, because the three modules import each other in a ring:
    # `effects` imports this one for its `TILING_DEFAULTS`, and `policy` imports `effects`. Tried
    # at the top, the import failed unless `effects` came first: with `policy` first, this module
    # reached `policy` before it had defined `AUTO_SKIP`, and with this module first, `effects`
    # reached it before it had defined `DEFAULTS`.
    import policy
    return list(policy.AUTO_SKIP) + [c for c in _IGNORED_TOO if c not in policy.AUTO_SKIP]


def _own_windows() -> tuple[list[str], list[str], list[str]]:
    """KyprX's own windows as the engine treats them: the settings window floats, opens in the
    middle of its screen, and stays above the others while it is open; the two overlays stay above
    it, so that the cheatsheet or the picker opened while it is open is not hidden under it.
    Imported here for the reason `_builtin_ignore` gives: `kyprd_names` imports `klassy` and
    `rules`, and nothing in this module needs them at the top."""
    import kyprd_names
    settings = kyprd_names.SETTINGS_CLASS
    return ([settings], [settings],
            [settings, kyprd_names.CHEATSHEET_CLASS, kyprd_names.WALLPAPER_CLASS])


def __getattr__(name: str):
    """`BUILTIN_IGNORE`: the classes the engine never tiles, whatever the group says --
    `policy.AUTO_SKIP` and `_IGNORED_TOO`. What the person lists in `ignoreClass` adds to these
    and never replaces them.

    `BUILTIN_FLOAT`: the classes that float whatever the group says, and that Toggle Float can
    still tile -- KyprX's own settings window. What the person lists in `floatingClass` adds to
    these too.

    Each built when it is asked for, a new list each time, for the reason in `_builtin_ignore`."""
    if name == "BUILTIN_IGNORE":
        return _builtin_ignore()
    if name == "BUILTIN_FLOAT":
        return _own_windows()[0]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---------------------------------------------------------------- the answer

#: Where the tiling stands, as `state_of` answers it: the engine tiles; its switch is off; KyprX is
#: taken off the desk; no compositor script has asked for its settings since the daemon started;
#: the script that asked is another version than the one installed.
STATES = ("on", "off", "off-desk", "no-script", "old-script")


def runs(group: dict, *, off: bool) -> bool:
    """Whether the engine tiles by this group: its switch on, and KyprX not off the desk. The one
    rule `resolve` answers the engine with and `TilingPart.tiling_on_now` answers the window with."""
    return bool(value_of(group, "tiling") and not off)


def resolve(group: dict, *, off: bool) -> dict:
    """The answer `Tiling()` gives the compositor script: every setting the engine needs, read the
    way the engine reads it, in one object.

    `off` is whether KyprX is taken off the desk (`State.off`), which the caller asks because it is
    not in this group. With it, or with the switch off, `tiling` is false and the engine places
    nothing; the rest is there all the same, in one shape whatever the answer.

    `ignore.classes` is `BUILTIN_IGNORE` with the person's own list after it, and `float.classes`
    `BUILTIN_FLOAT` with the person's own after it. `float.centred` are the classes whose window
    opens in the middle of its screen, and `float.above` the classes kept above the other windows
    while they float (`_own_windows`).

    `arrangements` are what the stored value means, each with its layouts for every number of
    windows (`expanded`): the shape every engine so far reads, and for a desk nobody edited since
    version 1, the very text it always was. `pool` is the zone layouts themselves, in their order,
    each `{id, name, drag, tree}`: what this version's engine offers a drag and walks with the
    layout keys while automatic tiling is off. `slots` names, for each arrangement by its id, the
    zone layout each of its layouts is, in the order of its `layouts` -- "" for the whole screen
    of one window. Two zone layouts may hold one tree, as Duplicate under Zone layouts leaves them,
    and then a tree alone does not say which one an arrangement uses; it is a field of its own,
    and not one more in each arrangement, so that the arrangements stay the text the engine from
    before the pool compares. The engine needs no version of the value: the answer has its own.

    Whether the daemon runs in a dry run is not here: this is pure, and the caller adds it
    (`TilingPart.tiling_answer`, and the answer `Daemon.Tiling` gives when this raised).
    """
    ignore = _builtin_ignore()
    for window_class in value_of(group, "ignoreClass"):
        if window_class not in ignore:
            ignore.append(window_class)
    floating, centred, above = _own_windows()
    for window_class in value_of(group, "floatingClass"):
        if window_class not in floating:
            floating.append(window_class)
    value = arrangements_of(group)[0]
    return {
        "version": ANSWER_VERSION,
        "tiling": runs(group, off=off),
        "auto": value_of(group, "autoTiling"),
        "osd": value_of(group, "showOsd"),
        "live": value_of(group, "adjustLayoutLive"),
        "floatUtility": value_of(group, "floatUtility"),
        "newWindow": value_of(group, "newWindowPosition"),
        "overflow": value_of(group, "newWindowOverflow"),
        "newDesktop": value_of(group, "newDesktopPosition"),
        "gaps": {name: value_of(group, key) for key, name in _GAPS.items()},
        "float": {"classes": floating, "titles": value_of(group, "floatingTitle"),
                  "centred": centred, "above": above},
        "ignore": {"classes": ignore, "titles": value_of(group, "ignoreTitle"),
                   "screens": value_of(group, "ignoreScreen")},
        "arrangements": expanded(value),
        "pool": [{"id": layout["id"], "name": layout["name"], "drag": layout["drag"],
                  "tree": _in_order(layout["tree"])} for layout in value["layouts"]],
        "slots": {entry["id"]: [""] + [entry["windows"][str(count)]
                                       for count in range(2, len(entry["windows"]) + 2)]
                  for entry in value["arrangements"]},
        # The arrangement each desktop starts on, by the desktop's name: only the ids that are
        # arrangements now, so a choice of one deleted since reads as none chosen.
        "desktops": {name: ident
                     for name, ident in value_of(group, "desktopArrangements").items()
                     if any(entry["id"] == ident for entry in value["arrangements"])},
    }


def state_of(group: dict, *, off: bool, script_version: str, tree_version: str) -> str:
    """One of `STATES`, the first that holds in this order: off the desk, the switch off, no
    script, another script, on.

    `script_version` is the version the compositor script last said it was (`Tiling()`'s argument,
    "" when none has asked), and `tree_version` the one installed (`KPlugin.Version` in
    `kwin-script/metadata.json`). The order is what each state can be done about: nothing on the
    Tiling tab tiles while KyprX is off the desk; a switch that is off is switched on; and a script
    that is not there, or not the installed one, is the compositor's.
    """
    if off:
        return "off-desk"
    if not value_of(group, "tiling"):
        return "off"
    if not script_version:
        return "no-script"
    if script_version != tree_version:
        return "old-script"
    return "on"


# ---------------------------------------------------------------- the KyprX folder

#: What a key of the group can be called and still be written back as one: KConfig escapes values
#: and not names, so a name with a newline or a bracket in it, from a file somebody edited, would
#: write a line or a whole group of its own into `kwinrc`.
_KEY_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def describe_part(group: dict, managed: set[str]) -> dict:
    """The group as the KyprX folder carries it, in `tiling.json`.

    Every key the group has, as its text -- a key that is absent stays absent, so applying the
    folder puts back the absence too -- with two exceptions. `arrangements` is the validated value
    as an object, in the version it is stored in, so the file reads as the zone layouts and
    arrangements rather than as one long line, and a desk in version 1 makes a folder in version
    1; a stored text that cannot be read stays text, exactly as it is, because it is somebody's
    work. And `floatingClass` leaves out the classes this app speaks for (`managed`): each of those
    carries its Float in its row in `windows.json`. A key with no value is left out, as absent.
    """
    out: dict = {}
    for key, raw in (group or {}).items():
        if not isinstance(raw, str):
            continue
        if key == "arrangements":
            try:
                out[key] = parse(raw)
            except ArrangementsError:
                out[key] = raw
        elif key == "floatingClass":
            out[key] = ",".join(c for c in entries(raw) if c not in managed)
        else:
            out[key] = raw
    return out


def group_from_part(part: dict) -> dict[str, str]:
    """The group a `tiling.json` part stands for: every key as its text, and `arrangements` -- an
    object -- as its canonical text, in its own version. A text in its place goes back as it came.

    For a part `part_problems` found nothing wrong with: a value that is not one of those shapes
    is left out, and arrangements that break a rule raise `ArrangementsError`. The Float of each
    row is the caller's to put back into `floatingClass`.
    """
    out: dict[str, str] = {}
    for key, value in (part or {}).items():
        if key == "arrangements" and not isinstance(value, str):
            out[key] = canonical(value)
        elif isinstance(value, str):
            out[key] = value
    return out


def part_problems(part) -> list[str]:
    """Everything in a `tiling.json` part that could not be written back, one sentence each.

    The arrangements are checked against every rule of their version, because only a value that
    keeps them can be written as their canonical text. The other values have to be text, the way
    KyprX writes them, and are otherwise not judged: the engine reads one it cannot use as its
    absent value, which is what it does with the same text in `kwinrc`, so a folder taken from a
    desk always goes back onto it.
    """
    if not isinstance(part, dict):
        return ["The tiling settings have to be an object with names in it."]
    out = []
    for key, value in part.items():
        if not _KEY_NAME.fullmatch(str(key)):
            out.append(f"A setting cannot be called {key!r}: a name is letters and digits.")
        elif key == "arrangements":
            if isinstance(value, str):
                continue
            if not isinstance(value, dict):
                out.append("The arrangements have to be an object, the way KyprX writes them.")
                continue
            try:
                validate(value)
            except ArrangementsError as e:
                out.append(str(e))
        elif not isinstance(value, str):
            out.append(f"{key} has to be text in quotes, the way KyprX writes it.")
    return out
