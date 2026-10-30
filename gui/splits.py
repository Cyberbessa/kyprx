"""The zone layouts and the arrangements the Tiling tab edits, as data, with no Qt in it.

A zone layout is a tree with a name: a split of the screen into parts side by side (`h`) or top to
bottom (`v`), each part a whole percent and each a zone or a split of its own, two zones to nine.
The zone layouts are one pool, in an order, and each says whether dragging a window offers its
zones. An arrangement is a name and, for each number of windows from two up, the zone layout of
the pool with that many zones the tiler lays a screen out by; one window has the whole screen. A
window that opens past an arrangement's last layout does what *When the arrangement is full*
says.

The format is `daemon/tiling.py`'s, version 2, and this module keeps the window's copy of its
rules -- what is refused, and the canonical text a value is written as -- because the window builds
the text it sends (`SetGroups`) and decides whether anything changed by comparing that text with
the daemon's own reading of the file. Version 1, where each arrangement held its own layouts, is
not read here: the daemon reads it for good, and what it sends the window is always its upgrade to
version 2. Two copies of one rule drift apart unless something holds them together, so a test in
`tests/` gives both the same values and asks for the same verdict and the same text, byte for
byte, and asks this copy to take every upgrade the daemon makes as it is.

The rest is what the builder does to a zone layout and what the two lists do: split a zone, remove
one, move a divider, choose the master zone; add, copy, rename, move and delete zone layouts and
choose which ones a drag offers; add, copy, rename, move and delete arrangements, and choose the
zone layout each uses for each number of windows. Every one of them returns a new value and never
changes the one it was given, and every one refuses what the daemon would refuse rather than
leaving that to the write -- and two things more, which only this window holds to: it adds no zone
layout past `MAX_LAYOUTS`, and offers no more than `MAX_DRAG` on a drag.
"""

from __future__ import annotations

import copy
import json
import math
import re
import unicodedata

#: The format this module reads and writes. A higher one is refused with a sentence of its own:
#: an older window that rewrote a newer KyprX's value would lose whatever the newer format added.
#: A lower one is refused too: the daemon upgrades version 1 before it sends it.
FORMAT = 2

#: The most windows an arrangement has a layout for, and so the most zones a zone layout has.
MAX_WINDOWS = 9

#: How deep splits nest. A zone at the root is depth 0.
MAX_DEPTH = 6

#: The smallest part a split may give, in percent.
MIN_SHARE = 5

NAME_LIMIT = 40
ID_LIMIT = 32

#: The most zone layouts this window adds: its own limit, chosen rather than measured -- the format
#: has none. A desk can hold more -- an upgrade of many arrangements adds a zone layout for every
#: layout the pool did not have, and the daemon reads any number -- and every one is shown, kept
#: and editable; only adding past this is refused.
MAX_LAYOUTS = 32

#: The most zone layouts a drag offers. The bar a drag shows, which Next Layout and Previous Layout
#: walk while automatic tiling is off, lists the whole screen and the first twelve zone layouts a
#: drag offers, in the pool's order (`engine.mjs`): a thirteenth would be on it only while it was
#: a screen's own.
MAX_DRAG = 12

#: The frame `grow` measures the last zone in, to choose the direction it splits: fixed rather than
#: a screen's, so that what it answers is the same wherever it runs, and 16:9 because that is what
#: most screens are. `grow` is the rule the tests hold the tiler's own cascade past an arrangement's
#: last layout to (`tests/test_tiling_geometry.py`). The tiler splits the last zone by the same
#: rule in the screen's own pixels, so in this frame the two make one tree, and on a screen of
#: another shape they can part: on a portrait screen Balanced's last zone is stacked where `grow`
#: puts it side by side, and on an ultrawide one Dwindle's is side by side where it is stacked
#: here.
FRAME = (1600, 900)

#: What *Add…* starts a zone layout with.
TWO_HALVES = {"split": "h", "sizes": [50, 50], "parts": [{}, {}]}

_ID = re.compile(r"[a-z0-9-]{1,32}")
_TOP_KEYS = {"version", "layouts", "arrangements"}
_LAYOUT_KEYS = {"id", "name", "drag", "tree"}
_LAYOUT_REQUIRED = ("id", "name", "tree")
_ARRANGEMENT_KEYS = {"id", "name", "cycle", "windows"}
_ARRANGEMENT_REQUIRED = ("id", "name", "windows")
_SPLIT_KEYS = {"split", "sizes", "parts"}

_GONE = "That arrangement is not there any more."
_LAYOUT_GONE = "That zone layout is not there any more."
_PAST_THE_LAST = (f"An arrangement has layouts for up to {MAX_WINDOWS} windows; a window that "
                  f"opens past the last one does what When the arrangement is full says.")


class ArrangementsError(ValueError):
    """What is wrong with a value, or why an edit cannot be made, in one plain sentence."""


# ---------------------------------------------------------------------- reading a value

def _is_int(value) -> bool:
    """An integer and not a boolean, which Python counts as one."""
    return isinstance(value, int) and not isinstance(value, bool)


def windows(count: int) -> str:
    """`1 window`, `3 windows`."""
    return f"{count} window" + ("" if count == 1 else "s")


def _zones_text(count: int) -> str:
    return f"{count} zone" + ("" if count == 1 else "s")


def _node(node, depth: int, where: str, root: bool = False) -> dict:
    """One node, checked and copied: a zone `{}`, or a split of two parts or more."""
    if not isinstance(node, dict):
        raise ArrangementsError(f"{where} has a part that is not a JSON object.")
    keys = set(node) - ({"master"} if root else set())
    if not keys:
        return {}
    unknown = sorted(keys - _SPLIT_KEYS)
    if unknown:
        raise ArrangementsError(f"{where} has a key KyprX does not know: {unknown[0]}.")
    if keys != _SPLIT_KEYS:
        missing = sorted(_SPLIT_KEYS - keys)[0]
        raise ArrangementsError(f"{where} has a split with no {missing}.")
    direction, sizes, parts = node["split"], node["sizes"], node["parts"]
    if direction not in ("h", "v"):
        raise ArrangementsError(f"{where} has a split that is neither h nor v.")
    if not isinstance(sizes, list) or not isinstance(parts, list) or len(parts) < 2 \
            or len(sizes) != len(parts):
        raise ArrangementsError(f"{where} has a split that is not two parts or more, each "
                                f"with a size.")
    # Both refused at the split and before its parts are walked, the way `daemon/tiling.py` does:
    # a value from a file somebody edited can nest a thousand deep or hold a thousand parts, and
    # either is a refusal long before it is a walk.
    if depth + 1 > MAX_DEPTH:
        raise ArrangementsError(f"{where} nests its splits more than {MAX_DEPTH} deep.")
    if len(parts) > MAX_WINDOWS:
        raise ArrangementsError(f"{where} has more than {MAX_WINDOWS} zones.")
    if not all(_is_int(s) and s >= MIN_SHARE for s in sizes):
        raise ArrangementsError(f"{where} has a part smaller than {MIN_SHARE} %, or one that is "
                                f"not a whole percent.")
    total = sum(sizes)
    if total != 100:
        # Said as a number only while it is short: two parts of 4300 digits, as long as the reader
        # takes, can add up to 4301, which cannot be turned back into text (`daemon/tiling.py`).
        raise ArrangementsError(
            f"{where} has a split whose parts add up to {total} %, not 100." if total < 10 ** 6
            else f"{where} has a split whose parts add up to far more than 100 %.")
    return {"split": direction, "sizes": list(sizes),
            "parts": [_node(p, depth + 1, where) for p in parts]}


def checked_tree(root, where: str = "The zone layout") -> dict:
    """A zone layout's tree, checked and copied, or the reason it cannot be one: two zones to
    `MAX_WINDOWS` -- one zone is the whole screen, which is no zone layout -- and its master
    zone one of them, left out when it is the first."""
    node = _node(root, 0, where, root=True)
    found = zones(node)
    if not 2 <= found <= MAX_WINDOWS:
        raise ArrangementsError(f"{where} has {_zones_text(found)}; a zone layout has 2 to "
                                f"{MAX_WINDOWS}.")
    if "master" in root:
        master = root["master"]
        if not _is_int(master) or not 0 <= master < found:
            raise ArrangementsError(f"{where} names a master zone it does not have.")
        if master:
            node["master"] = master
    return node


def _named_item(item: dict, position: int, kind: str, plural: str, ids: set,
                names: set) -> tuple[str, str]:
    """An item's id and name, checked against the others of its list. Zone layouts and
    arrangements are two lists, so one of each may share a name or an id."""
    ident = item["id"]
    if not isinstance(ident, str) or not _ID.fullmatch(ident):
        raise ArrangementsError(f"{kind} {position} has an id KyprX cannot use: an id is 1 to "
                                f"{ID_LIMIT} of a to z, 0 to 9 and -.")
    if ident in ids:
        raise ArrangementsError(f"Two {plural} have the id {ident}.")
    name = item["name"].strip() if isinstance(item["name"], str) else ""
    if not 1 <= len(name) <= NAME_LIMIT:
        raise ArrangementsError(f"{kind} {position} needs a name of 1 to {NAME_LIMIT} "
                                f"characters.")
    if name.casefold() in names:
        raise ArrangementsError(f"Two {plural} are called {name}.")
    return ident, name


def _zone_layout(item, position: int, ids: set, names: set) -> dict:
    if not isinstance(item, dict):
        raise ArrangementsError(f"Zone layout {position} is not a JSON object.")
    # Sorted as text: a value handed over as an object can have keys that are not text, and
    # sorted among text ones they would raise a TypeError rather than this module's error.
    unknown = sorted(set(item) - _LAYOUT_KEYS, key=str)
    if unknown:
        raise ArrangementsError(f"Zone layout {position} has a key KyprX does not know: "
                                f"{unknown[0]}.")
    missing = [key for key in _LAYOUT_REQUIRED if key not in item]
    if missing:
        raise ArrangementsError(f"Zone layout {position} has no {missing[0]}.")
    ident, name = _named_item(item, position, "Zone layout", "zone layouts", ids, names)
    drag = item.get("drag", True)
    if not isinstance(drag, bool):
        raise ArrangementsError(f"{name}: whether a drag offers it is not true or false.")
    tree = checked_tree(item["tree"], f"The zone layout {name}")
    ids.add(ident)
    names.add(name.casefold())
    return {"id": ident, "name": name, "drag": drag, "tree": tree}


def _arrangement(item, position: int, ids: set, names: set, pool: dict) -> dict:
    if not isinstance(item, dict):
        raise ArrangementsError(f"Arrangement {position} is not a JSON object.")
    unknown = sorted(set(item) - _ARRANGEMENT_KEYS, key=str)
    if unknown:
        raise ArrangementsError(f"Arrangement {position} has a key KyprX does not know: "
                                f"{unknown[0]}.")
    missing = [key for key in _ARRANGEMENT_REQUIRED if key not in item]
    if missing:
        raise ArrangementsError(f"Arrangement {position} has no {missing[0]}.")
    ident, name = _named_item(item, position, "Arrangement", "arrangements", ids, names)
    cycle = item.get("cycle", True)
    if not isinstance(cycle, bool):
        raise ArrangementsError(f"{name}: whether it is in the rotation is not true or false.")
    slots = item["windows"]
    if not isinstance(slots, dict):
        raise ArrangementsError(f"{name}: its zone layouts by number of windows are not a JSON "
                                f"object.")
    last = len(slots) + 1
    if last > MAX_WINDOWS or set(slots) != {str(count) for count in range(2, last + 1)}:
        raise ArrangementsError(f"{name} has to name a zone layout for each number of windows "
                                f"from 2 up, none left out, and {MAX_WINDOWS} at most.")
    normal = {}
    for count in range(2, last + 1):
        held = slots[str(count)]
        if not isinstance(held, str) or held not in pool:
            raise ArrangementsError(f"{name}: the zone layout for {windows(count)} is not there.")
        found = zones(pool[held]["tree"])
        if found != count:
            raise ArrangementsError(f"{name}: {pool[held]['name']} has {_zones_text(found)}, not "
                                    f"{count}.")
        normal[str(count)] = held
    ids.add(ident)
    names.add(name.casefold())
    return {"id": ident, "name": name, "cycle": cycle, "windows": normal}


def validate(obj) -> dict:
    """A normalised copy of a value, or `ArrangementsError` saying what is wrong with it.

    Normalised the way the canonical text needs it: names stripped, `cycle` and `drag` always
    there, `master` only where it is not the first zone, and nothing else. The version is read
    first, so a value from a newer KyprX is refused for that and not for a key this one does not
    know.
    """
    if not isinstance(obj, dict):
        raise ArrangementsError("The arrangements are not a JSON object.")
    version = obj.get("version")
    if _is_int(version) and version > FORMAT:
        raise ArrangementsError(f"The arrangements were written by a newer KyprX, in format "
                                f"{version}; this one reads format {FORMAT}.")
    unknown = sorted(set(obj) - _TOP_KEYS, key=str)
    if unknown:
        raise ArrangementsError(f"The arrangements have a key KyprX does not know: "
                                f"{unknown[0]}.")
    if not _is_int(version) or version != FORMAT:
        raise ArrangementsError(f"The arrangements do not say they are format {FORMAT}.")
    items = obj.get("layouts")
    if not isinstance(items, list) or not items:
        raise ArrangementsError("There has to be one zone layout at least.")
    ids: set = set()
    names: set = set()
    layouts = [_zone_layout(item, i + 1, ids, names) for i, item in enumerate(items)]
    if not any(layout["drag"] for layout in layouts):
        raise ArrangementsError("One zone layout at least has to be offered when a window is "
                                "dragged.")
    items = obj.get("arrangements")
    if not isinstance(items, list) or not items:
        raise ArrangementsError("There has to be one arrangement at least.")
    pool = {layout["id"]: layout for layout in layouts}
    ids, names = set(), set()
    normal = [_arrangement(item, i + 1, ids, names, pool) for i, item in enumerate(items)]
    if not any(a["cycle"] for a in normal):
        raise ArrangementsError("One arrangement at least has to be in the rotation.")
    return {"version": FORMAT, "layouts": layouts, "arrangements": normal}


def parse(text: str) -> dict:
    """The value a text holds, validated."""
    try:
        obj = json.loads(text)
    except (TypeError, ValueError) as e:
        raise ArrangementsError("The arrangements are not readable JSON.") from e
    except RecursionError as e:
        # A text nested thousands deep stops the reader before any rule here could.
        raise ArrangementsError("The arrangements are not readable JSON: they nest too deep.") \
            from e
    return validate(obj)


def canonical(value) -> str:
    """The one text a value is written as, from the value or from any text of it.

    Two texts of the same value are the same text once canonical, which is what lets the window
    decide whether something changed without being fooled by spacing or key order.
    """
    normal = parse(value) if isinstance(value, str) else validate(value)
    return json.dumps(normal, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------------- the shape of a layout

def is_zone(node: dict) -> bool:
    return not node.get("split")


def leaf_paths(node: dict, path: tuple = ()) -> list[tuple]:
    """Every zone's path -- the index of the part taken at each split -- in depth-first order,
    which is the order `master` counts in."""
    if is_zone(node):
        return [path]
    found: list[tuple] = []
    for i, part in enumerate(node["parts"]):
        found += leaf_paths(part, path + (i,))
    return found


def zones(node: dict) -> int:
    return len(leaf_paths(node))


def depth(node: dict) -> int:
    """How deep the deepest zone is: 0 for a layout that is one zone."""
    return max(len(path) for path in leaf_paths(node))


def master_of(root: dict) -> int:
    master = root.get("master", 0)
    return master if _is_int(master) and 0 <= master < zones(root) else 0


def fill_order(root: dict) -> list[tuple]:
    """The order windows fill the zones in: the master zone first, then the rest in depth-first
    order."""
    paths = leaf_paths(root)
    master = master_of(root)
    return [paths[master]] + paths[:master] + paths[master + 1:]


def node_at(root: dict, path: tuple) -> dict:
    node = root
    for i in path:
        node = node["parts"][i]
    return node


def has_path(root: dict, path) -> bool:
    node = root
    for i in path or ():
        if is_zone(node) or not 0 <= i < len(node["parts"]):
            return False
        node = node["parts"][i]
    return True


def is_zone_path(root: dict, path) -> bool:
    return path is not None and has_path(root, path) and is_zone(node_at(root, path))


def nearest(value: float) -> int:
    """Half up, the way the compositor script rounds (`Math.round`), for the positive numbers
    here. Python's own `round` sends a half to the even neighbour, which is a pixel's difference
    from the tiler wherever a share lands on one."""
    return math.floor(value + 0.5)


def layout_rects(root: dict, width: int, height: int):
    """Every node's rectangle, in whole pixels: `(zones, splits)`, each by path.

    Each split's edges are placed from the running total of its shares, so the parts of a split
    always tile it exactly -- the last one ends where the split ends -- and a layout tiles the
    whole frame with nothing left over and nothing drawn twice.
    """
    zone_rects: dict[tuple, tuple[int, int, int, int]] = {}
    split_rects: dict[tuple, tuple[int, int, int, int]] = {}

    def place(node, path, x, y, w, h):
        if is_zone(node):
            zone_rects[path] = (x, y, w, h)
            return
        split_rects[path] = (x, y, w, h)
        side = node["split"] == "h"
        length = w if side else h
        start = total = 0
        last = len(node["parts"]) - 1
        for i, (share, part) in enumerate(zip(node["sizes"], node["parts"])):
            total += share
            end = length if i == last else min(length, max(start, nearest(length * total / 100)))
            if side:
                place(part, path + (i,), x + start, y, end - start, h)
            else:
                place(part, path + (i,), x, y + start, w, end - start)
            start = end

    place(root, (), 0, 0, max(0, int(width)), max(0, int(height)))
    return zone_rects, split_rects


def zone_rects(root: dict, width: int, height: int) -> dict[tuple, tuple[int, int, int, int]]:
    """Each zone's `(x, y, width, height)` in a frame of this size, by path."""
    return layout_rects(root, width, height)[0]


def rects(root: dict, width: int, height: int) -> list[tuple[int, int, int, int]]:
    """The zones' rectangles in a frame of this size, in fill order: the first is the master's."""
    placed = zone_rects(root, width, height)
    return [placed[path] for path in fill_order(root)]


def edges(root: dict, width: int, height: int) -> list[tuple]:
    """Every divider, as `(split path, index, direction, position, span start, span end)`.

    The divider `index` is the edge between part `index` and the next. Its `position` is an x for
    a split side by side and a y for one top to bottom; the span is the other axis.
    """
    zone_rect, split_rect = layout_rects(root, width, height)
    found = []
    for path, (x, y, w, h) in split_rect.items():
        node = node_at(root, path)
        side = node["split"] == "h"
        for i in range(len(node["parts"]) - 1):
            part = path + (i,)
            px, py, pw, ph = zone_rect.get(part) or split_rect[part]
            if side:
                found.append((path, i, "h", px + pw, y, y + h))
            else:
                found.append((path, i, "v", py + ph, x, x + w))
    return found


# ---------------------------------------------------------------------- editing a tree

#: The key `remove_zone` marks the master zone with while the tree is rebuilt around it. Never in
#: a tree it returns, and no key the rules let a tree carry, so a checked tree never has it already.
_MARK = " master"


def _fresh(node):
    """A copy of a tree that shares nothing, not even with itself. `copy.deepcopy` copies an
    object that appears twice as one object that appears twice, and a tree built in code --
    `[{}] * 3`, say -- holds one zone three times: an edit to one part of such a copy, or a mark
    on one zone (`remove_zone`), would land on all three. Measured: removing the right column of
    Centred column built that way lost its master zone."""
    if isinstance(node, dict):
        return {key: _fresh(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_fresh(value) for value in node]
    return node


def _parent(root: dict, path: tuple) -> dict | None:
    return node_at(root, path[:-1]) if path else None


def can_split(root: dict, path: tuple, direction: str) -> str:
    """Why this zone cannot be split this way, or "" when it can.

    Split the way its own split already runs, a zone becomes one more part of that split; split
    the other way, it becomes a split of its own, a level deeper.
    """
    if not is_zone_path(root, path) or direction not in ("h", "v"):
        return "Choose a zone to split."
    parent = _parent(root, path)
    if parent is not None and parent["split"] == direction:
        if parent["sizes"][path[-1]] < 2 * MIN_SHARE:
            return f"That zone is too small to halve: each part keeps {MIN_SHARE} % at least."
        return ""
    if len(path) + 1 > MAX_DEPTH:
        return f"Splits nest {MAX_DEPTH} deep at most, and that zone is as deep as they go."
    return ""


def split(root: dict, path: tuple, direction: str) -> dict:
    """The layout with this zone in two: it keeps the first half, and the new zone is the second.

    The master zone stays the same zone, so its number moves on by one when the new zone comes
    before it in depth-first order.
    """
    why = can_split(root, path, direction)
    if why:
        raise ArrangementsError(why)
    new = _fresh(root)
    master = master_of(root)
    position = leaf_paths(root).index(tuple(path))
    parent = _parent(new, path)
    if parent is not None and parent["split"] == direction:
        i = path[-1]
        share = parent["sizes"][i]
        parent["sizes"][i:i + 1] = [share - share // 2, share // 2]
        parent["parts"].insert(i + 1, {})
    elif parent is None:
        new = {"split": direction, "sizes": [50, 50], "parts": [{}, {}]}
    else:
        parent["parts"][path[-1]] = {"split": direction, "sizes": [50, 50], "parts": [{}, {}]}
    master = master + 1 if master > position else master
    new.pop("master", None)
    if master:
        new["master"] = master
    return new


def can_remove_zone(root: dict, path) -> str:
    """Why this zone cannot be removed, or "" when it can. The whole screen, one zone, stays."""
    if not is_zone_path(root, path) or not path:
        return "Choose a zone to remove."
    return ""


def remove_zone(root: dict, path: tuple) -> dict:
    """The layout without this zone.

    Its share goes to the part before it in its split, or to the one after it when it is the
    first, so every other part keeps its size; a split left with one part is that part, in its
    place. The master zone stays the same zone -- and when it is the one removed, the master is
    whoever took its space: the first zone, in depth-first order, of the part that did.
    """
    why = can_remove_zone(root, path)
    if why:
        raise ArrangementsError(why)
    path = tuple(path)
    new = _fresh(root)
    new.pop("master", None)
    parent = node_at(new, path[:-1])
    i = path[-1]
    taker = i - 1 if i else 1
    master = leaf_paths(root)[master_of(root)]
    if master == path:
        master = path[:-1] + (taker,) + leaf_paths(parent["parts"][taker])[0]
    # Marked by its place before any part moves, and found again by the mark after: the zones
    # after the one removed change their paths, and a split left with one part changes them all
    # the way down.
    node_at(new, master)[_MARK] = True
    parent["sizes"][taker] += parent["sizes"][i]
    del parent["sizes"][i]
    del parent["parts"][i]
    if len(parent["parts"]) == 1:
        alone = parent["parts"][0]
        if len(path) > 1:
            node_at(new, path[:-2])["parts"][path[-2]] = alone
        else:
            new = alone
    leaves = leaf_paths(new)
    position = next(k for k, leaf in enumerate(leaves) if node_at(new, leaf).pop(_MARK, False))
    if position:
        new["master"] = position
    return new


def divider_range(root: dict, split_path: tuple, index: int) -> tuple[int, int]:
    """How far a divider can go, as the share of the part before it."""
    sizes = node_at(root, split_path)["sizes"]
    pair = sizes[index] + sizes[index + 1]
    return MIN_SHARE, pair - MIN_SHARE


def move_divider(root: dict, split_path: tuple, index: int, share) -> dict:
    """The layout with one divider moved, so the part before it is `share` percent.

    Only the neighbour across the divider gives or takes: every other part of the split keeps
    its size. Clamped, so neither of the two drops below the smallest share.
    """
    new = _fresh(root)
    node = node_at(new, split_path)
    low, high = divider_range(root, split_path, index)
    pair = low + high
    share = max(low, min(high, int(share)))
    node["sizes"][index] = share
    node["sizes"][index + 1] = pair - share
    return new


def set_master(root: dict, leaf: int) -> dict:
    """The layout with zone `leaf` (in depth-first order) as the master zone, filled first."""
    if not 0 <= leaf < zones(root):
        raise ArrangementsError("That layout has no such zone.")
    new = _fresh(root)
    new.pop("master", None)
    if leaf:
        new["master"] = leaf
    return new


def grow_direction(root: dict, path: tuple, frame=FRAME) -> str:
    """Side by side when this zone is wider than it is tall in the fixed frame, else stacked."""
    _x, _y, w, h = zone_rects(root, *frame)[tuple(path)]
    return "h" if w > h else "v"


def can_grow(root: dict) -> str:
    """Why `grow` cannot make a layout of one zone more from this one, or "" when it can."""
    if zones(root) >= MAX_WINDOWS:
        return f"A zone layout has {MAX_WINDOWS} zones at most."
    last = fill_order(root)[-1]
    return can_split(root, last, grow_direction(root, last))


def grow(root: dict) -> dict:
    """The layout of one zone more: this one, with its last zone in fill order split along its
    longer side in `FRAME` -- the whole screen, `{}`, grows into two halves. The tiler squeezes a
    window in past an arrangement's last layout by the same rule in the screen's own pixels, and
    this is the rule the tests hold that cascade to (`tests/test_tiling_geometry.py`): in a 16:9
    frame the two make one tree, and on a portrait or an ultrawide screen the zone the tiler splits
    can run the other way. Nothing in the window makes a zone layout with it."""
    why = can_grow(root)
    if why:
        raise ArrangementsError(why)
    last = fill_order(root)[-1]
    return split(root, last, grow_direction(root, last))


# ---------------------------------------------------------------------- names and ids

def slug(name: str) -> str:
    """A name as an id: letters without their accents, digits, and single dashes between them."""
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")
    return text[:ID_LIMIT].strip("-")


def make_id(name: str, taken, empty: str = "layout") -> str:
    """A new id: its name as a slug, with `-2`, `-3`… when that is taken, and `<empty>-1`,
    `-2`… for a name with nothing a slug can keep -- `layout-1` for a zone layout,
    `arrangement-1` for an arrangement. An id never changes after this -- a rename keeps it --
    because it is what the tiler remembers each screen by, and what an arrangement names its zone
    layouts by. The daemon names the zone layouts its upgrade adds by the same rule
    (`daemon/tiling.py`), and a test holds the two to one answer."""
    base = slug(name)
    if base and base not in taken:
        return base
    stem, n = (base, 2) if base else (empty, 1)
    while True:
        suffix = f"-{n}"
        candidate = stem[:ID_LIMIT - len(suffix)].rstrip("-") + suffix
        if candidate not in taken:
            return candidate
        n += 1


def _free(name: str, problem) -> str:
    """`<name> copy`, or `<name> copy 2` and on when `problem` finds that taken, cut to fit."""
    n = 1
    while True:
        tail = " copy" if n == 1 else f" copy {n}"
        candidate = name[:NAME_LIMIT - len(tail)].rstrip() + tail
        if not problem(candidate):
            return candidate
        n += 1


def _named(names: list[str]) -> str:
    """`A`, `A and B`, `A, B and C`."""
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


# ---------------------------------------------------------------------- the zone layouts

def layout_index(value: dict, ident: str) -> int:
    return next((i for i, held in enumerate(value["layouts"]) if held["id"] == ident), -1)


def layout(value: dict, ident: str) -> dict | None:
    i = layout_index(value, ident)
    return value["layouts"][i] if i >= 0 else None


def choices(value: dict, count: int) -> list[dict]:
    """The zone layouts with `count` zones, in the pool's order: what an arrangement can use for
    `count` windows."""
    return [held for held in value["layouts"] if zones(held["tree"]) == count]


def users(value: dict, ident: str) -> list[tuple[dict, int]]:
    """Every arrangement that uses this zone layout, in the list's order, each with the number of
    windows it uses it for -- the layout's own number of zones, so the same for all of them."""
    return [(a, int(count)) for a in value["arrangements"]
            for count, held in a["windows"].items() if held == ident]


def _dragged(value: dict) -> int:
    return sum(held["drag"] for held in value["layouts"])


def used_problem(value: dict, ident: str) -> str:
    """Why this zone layout keeps its number of zones, or "" when no arrangement uses it: each
    arrangement that uses it uses it for that many windows."""
    found = users(value, ident)
    if not found:
        return ""
    count = found[0][1]
    verb = "uses" if len(found) == 1 else "use"
    return (f"{_named([a['name'] for a, _ in found])} {verb} it for {windows(count)}, so it "
            f"keeps its {count} zones.")


def layout_name_problem(value: dict, name: str, keep: str = "") -> str:
    """Why this cannot be a zone layout's name, or "". `keep` is the zone layout being renamed,
    whose own name is not a clash."""
    wanted = name.strip()
    if not wanted:
        return "A zone layout needs a name."
    if len(wanted) > NAME_LIMIT:
        return f"A name is {NAME_LIMIT} characters at most."
    for layout_ in value["layouts"]:
        if layout_["id"] != keep and layout_["name"].casefold() == wanted.casefold():
            return f"There is already a zone layout called {layout_['name']}."
    return ""


def create_problem(value: dict) -> str:
    """Why this window adds no zone layout now, or "" when it can add one."""
    count = len(value["layouts"])
    if count >= MAX_LAYOUTS:
        # Said as a number past one: an upgrade can leave far more than this window adds.
        spare = count - MAX_LAYOUTS + 1
        return (f"There are {count} zone layouts, and this window adds none past {MAX_LAYOUTS}: "
                f"delete {'one' if spare == 1 else spare} that nothing uses first.")
    return ""


def _layout_replaced(value: dict, ident: str, new: dict) -> dict:
    out = copy.deepcopy(value)
    out["layouts"][layout_index(value, ident)] = copy.deepcopy(new)
    return validate(out)


def _copy_drag(value: dict, source: dict) -> bool:
    """A copy is offered on a drag as its original is, while fewer than `MAX_DRAG` are -- never a
    refusal of the copy for it: past them, the copy is not offered until *Offer on drag* is turned
    on for it."""
    return source["drag"] and _dragged(value) < MAX_DRAG


def add_layout(value: dict, name: str) -> tuple[dict, str]:
    """The value with a new zone layout at the end of the pool, and its id: two halves, not
    offered on a drag until *Offer on drag* is turned on for it, so that adding one changes nothing
    on the screen."""
    why = create_problem(value) or layout_name_problem(value, name)
    if why:
        raise ArrangementsError(why)
    ident = make_id(name, {layout_["id"] for layout_ in value["layouts"]})
    out = copy.deepcopy(value)
    out["layouts"].append({"id": ident, "name": name.strip(), "drag": False,
                           "tree": copy.deepcopy(TWO_HALVES)})
    return validate(out), ident


def duplicate_layout(value: dict, ident: str) -> tuple[dict, str]:
    """The value with a copy of one zone layout straight after it, under a new id and a free name,
    and the copy's id. No arrangement uses the copy."""
    i = layout_index(value, ident)
    if i < 0:
        raise ArrangementsError(_LAYOUT_GONE)
    why = create_problem(value)
    if why:
        raise ArrangementsError(why)
    source = value["layouts"][i]
    name = _free(source["name"], lambda candidate: layout_name_problem(value, candidate))
    made = {"id": make_id(name, {layout_["id"] for layout_ in value["layouts"]}), "name": name,
            "drag": _copy_drag(value, source), "tree": copy.deepcopy(source["tree"])}
    out = copy.deepcopy(value)
    out["layouts"].insert(i + 1, made)
    return validate(out), made["id"]


def rename_layout(value: dict, ident: str, name: str) -> dict:
    """The value with one zone layout under another name, and the same id."""
    source = layout(value, ident)
    if source is None:
        raise ArrangementsError(_LAYOUT_GONE)
    why = layout_name_problem(value, name, keep=ident)
    if why:
        raise ArrangementsError(why)
    return _layout_replaced(value, ident, dict(source, name=name.strip()))


def move_layout(value: dict, ident: str, step: int) -> dict:
    """The value with one zone layout moved left (`-1`) or right (`1`) -- which is the order a drag
    offers them in, and the order the layout keys walk them in while automatic tiling is off."""
    i = layout_index(value, ident)
    j = i + step
    if i < 0 or not 0 <= j < len(value["layouts"]):
        raise ArrangementsError("That zone layout cannot move that way.")
    out = copy.deepcopy(value)
    items = out["layouts"]
    items[i], items[j] = items[j], items[i]
    return validate(out)


_LAST_DRAG = "It is the only zone layout offered when a window is dragged, and a drag needs one."


def delete_layout_problem(value: dict, ident: str) -> str:
    """Why this zone layout cannot be deleted, or "": not while an arrangement uses it -- every one
    that does is named -- and not the last one a drag offers."""
    source = layout(value, ident)
    if source is None:
        return _LAYOUT_GONE
    found = users(value, ident)
    if found:
        count = found[0][1]
        verb = "uses" if len(found) == 1 else "use"
        return (f"{_named([a['name'] for a, _ in found])} {verb} it for {windows(count)}: "
                f"choose another zone layout there first.")
    if source["drag"] and _dragged(value) == 1:
        return _LAST_DRAG
    return ""


def delete_layout(value: dict, ident: str) -> dict:
    why = delete_layout_problem(value, ident)
    if why:
        raise ArrangementsError(why)
    out = copy.deepcopy(value)
    out["layouts"].pop(layout_index(value, ident))
    return validate(out)


def drag_problem(value: dict, ident: str, on: bool) -> str:
    """Why this zone layout's *Offer on drag* cannot be set this way, or "": not a thirteenth
    (`MAX_DRAG`), and not the last one off."""
    source = layout(value, ident)
    if source is None:
        return _LAYOUT_GONE
    dragged = _dragged(value)
    if on and not source["drag"] and dragged >= MAX_DRAG:
        # Counted rather than said as twelve: an upgrade from version 1 offers every layout manual
        # tiling showed, and can leave more than a drag shows.
        fewer = dragged - MAX_DRAG + 1
        return (f"{dragged} zone layouts are offered when a window is dragged already, and a drag "
                f"shows {MAX_DRAG} at most: turn Offer on drag off for "
                f"{'one' if fewer == 1 else fewer} of them first.")
    if not on and source["drag"] and dragged == 1:
        return _LAST_DRAG
    return ""


def set_drag(value: dict, ident: str, on: bool) -> dict:
    why = drag_problem(value, ident, on)
    if why:
        raise ArrangementsError(why)
    return _layout_replaced(value, ident, dict(layout(value, ident), drag=bool(on)))


def set_tree(value: dict, ident: str, tree: dict) -> dict:
    """The value with one zone layout's tree changed, checked whole -- a divider moved, a master
    zone chosen, a zone split or removed. A tree of another number of zones is refused while an
    arrangement uses the layout (`used_problem`), which has to keep that many zones for that many
    windows; one of the same number changes every arrangement that uses it (`users`)."""
    source = layout(value, ident)
    if source is None:
        raise ArrangementsError(_LAYOUT_GONE)
    normal = checked_tree(tree, f"The zone layout {source['name']}")
    if zones(normal) != zones(source["tree"]):
        why = used_problem(value, ident)
        if why:
            raise ArrangementsError(why)
    return _layout_replaced(value, ident, dict(source, tree=normal))


def split_problem(value: dict, ident: str, path, direction: str) -> str:
    """Why this zone of a zone layout cannot be split this way in place, or "": not while an
    arrangement uses it, nor past `MAX_WINDOWS` zones, nor past what `can_split` allows."""
    source = layout(value, ident)
    if source is None:
        return _LAYOUT_GONE
    root = source["tree"]
    if not is_zone_path(root, path) or direction not in ("h", "v"):
        return "Choose a zone to split."
    why = used_problem(value, ident)
    if why:
        return why
    if zones(root) >= MAX_WINDOWS:
        return f"A zone layout has {MAX_WINDOWS} zones at most."
    return can_split(root, path, direction)


def split_layout(value: dict, ident: str, path, direction: str) -> dict:
    """The value with a zone of one zone layout split in two (`split`), in place."""
    why = split_problem(value, ident, path, direction)
    if why:
        raise ArrangementsError(why)
    return set_tree(value, ident, split(layout(value, ident)["tree"], tuple(path), direction))


def remove_zone_problem(value: dict, ident: str, path) -> str:
    """Why this zone of a zone layout cannot be removed, or "": not while an arrangement uses the
    layout, and not below two zones."""
    source = layout(value, ident)
    if source is None:
        return _LAYOUT_GONE
    root = source["tree"]
    if not is_zone_path(root, path):
        return "Choose a zone to remove."
    why = used_problem(value, ident)
    if why:
        return why
    if zones(root) <= 2:
        return "A zone layout has two zones at least."
    return can_remove_zone(root, path)


def remove_layout_zone(value: dict, ident: str, path) -> dict:
    """The value with a zone of one zone layout removed (`remove_zone`), in place."""
    why = remove_zone_problem(value, ident, path)
    if why:
        raise ArrangementsError(why)
    return set_tree(value, ident, remove_zone(layout(value, ident)["tree"], tuple(path)))


# ---------------------------------------------------------------------- the arrangements

def index_of(value: dict, ident: str) -> int:
    return next((i for i, a in enumerate(value["arrangements"]) if a["id"] == ident), -1)


def arrangement(value: dict, ident: str) -> dict | None:
    i = index_of(value, ident)
    return value["arrangements"][i] if i >= 0 else None


def last_count(entry: dict) -> int:
    """The most windows an arrangement has a layout for: 1 when it is the whole screen alone."""
    return len(entry["windows"]) + 1


def _replaced(value: dict, ident: str, new: dict) -> dict:
    out = copy.deepcopy(value)
    out["arrangements"][index_of(value, ident)] = copy.deepcopy(new)
    return validate(out)


def name_problem(value: dict, name: str, keep: str = "") -> str:
    """Why this cannot be an arrangement's name, or "". `keep` is the arrangement being renamed,
    whose own name is not a clash."""
    wanted = name.strip()
    if not wanted:
        return "An arrangement needs a name."
    if len(wanted) > NAME_LIMIT:
        return f"A name is {NAME_LIMIT} characters at most."
    for a in value["arrangements"]:
        if a["id"] != keep and a["name"].casefold() == wanted.casefold():
            return f"There is already an arrangement called {a['name']}."
    return ""


def free_name(value: dict, name: str) -> str:
    """`<name> copy`, or `<name> copy 2` and on when that is taken, cut to fit the limit."""
    return _free(name, lambda candidate: name_problem(value, candidate))


def add(value: dict, name: str) -> tuple[dict, str]:
    """The value with a new arrangement at the end, in the rotation, and its id: the whole screen
    for one window and, for two, the first zone layout of the pool with two zones -- none past
    that, and none for two when the pool has none of two zones."""
    why = name_problem(value, name)
    if why:
        raise ArrangementsError(why)
    ident = make_id(name, {a["id"] for a in value["arrangements"]}, "arrangement")
    two = next((layout_["id"] for layout_ in choices(value, 2)), None)
    out = copy.deepcopy(value)
    out["arrangements"].append({"id": ident, "name": name.strip(), "cycle": True,
                                "windows": {"2": two} if two else {}})
    return validate(out), ident


def duplicate(value: dict, ident: str) -> tuple[dict, str]:
    """The value with a copy of one arrangement straight after it, under a new id and a free name,
    and its id. The copy uses the same zone layouts: a change to one of them changes both."""
    i = index_of(value, ident)
    if i < 0:
        raise ArrangementsError(_GONE)
    source = value["arrangements"][i]
    name = free_name(value, source["name"])
    made = dict(copy.deepcopy(source), name=name,
                id=make_id(name, {a["id"] for a in value["arrangements"]}, "arrangement"))
    out = copy.deepcopy(value)
    out["arrangements"].insert(i + 1, made)
    return validate(out), made["id"]


def rename(value: dict, ident: str, name: str) -> dict:
    """The value with one arrangement under another name, and the same id."""
    source = arrangement(value, ident)
    if source is None:
        raise ArrangementsError(_GONE)
    why = name_problem(value, name, keep=ident)
    if why:
        raise ArrangementsError(why)
    return _replaced(value, ident, dict(source, name=name.strip()))


def move(value: dict, ident: str, step: int) -> dict:
    """The value with one arrangement moved up (`-1`) or down (`1`) the list -- which is the order
    the layout keys walk the rotation in."""
    i = index_of(value, ident)
    j = i + step
    if i < 0 or not 0 <= j < len(value["arrangements"]):
        raise ArrangementsError("That arrangement cannot move that way.")
    out = copy.deepcopy(value)
    items = out["arrangements"]
    items[i], items[j] = items[j], items[i]
    return validate(out)


def delete_problem(value: dict, ident: str) -> str:
    source = arrangement(value, ident)
    if source is None:
        return _GONE
    if len(value["arrangements"]) == 1:
        return "It is the only arrangement, and the tiler needs one."
    if source["cycle"] and sum(a["cycle"] for a in value["arrangements"]) == 1:
        return "It is the only one in the rotation: put another in first."
    return ""


def delete(value: dict, ident: str) -> dict:
    """The value without one arrangement. The zone layouts it used stay in the pool."""
    why = delete_problem(value, ident)
    if why:
        raise ArrangementsError(why)
    out = copy.deepcopy(value)
    out["arrangements"].pop(index_of(value, ident))
    return validate(out)


def set_cycle(value: dict, ident: str, on: bool) -> dict:
    """In the rotation or out of it. The last one in it stays: the layout keys need one to walk."""
    source = arrangement(value, ident)
    if source is None:
        raise ArrangementsError(_GONE)
    if not on and source["cycle"] and sum(a["cycle"] for a in value["arrangements"]) == 1:
        raise ArrangementsError(f"{source['name']} is the only one in the rotation, so it stays "
                                f"in: the layout keys need one to walk.")
    return _replaced(value, ident, dict(source, cycle=bool(on)))


def _fits(value: dict, layout_id: str, count: int) -> str:
    """Why this zone layout cannot be an arrangement's layout for `count` windows, or ""."""
    held = layout(value, layout_id)
    if held is None:
        return _LAYOUT_GONE
    found = zones(held["tree"])
    if found != count:
        return (f"{held['name']} has {_zones_text(found)}, and the layout for {windows(count)} "
                f"needs {count}.")
    return ""


def slot_problem(value: dict, ident: str, count: int, layout_id: str) -> str:
    """Why this arrangement cannot use this zone layout for `count` windows, or ""."""
    entry = arrangement(value, ident)
    if entry is None:
        return _GONE
    if not 2 <= count <= last_count(entry):
        return "That arrangement has no layout for that many windows."
    return _fits(value, layout_id, count)


def set_slot(value: dict, ident: str, count: int, layout_id: str) -> dict:
    """The value with an arrangement using another zone layout for `count` windows, one of the
    same number of zones (`choices`)."""
    why = slot_problem(value, ident, count, layout_id)
    if why:
        raise ArrangementsError(why)
    entry = arrangement(value, ident)
    return _replaced(value, ident, dict(entry, windows={**entry["windows"],
                                                        str(count): layout_id}))


def add_slot_problem(value: dict, ident: str) -> str:
    """Why this arrangement can have no layout for one window more, or ""."""
    entry = arrangement(value, ident)
    if entry is None:
        return _GONE
    if last_count(entry) >= MAX_WINDOWS:
        return _PAST_THE_LAST
    return ""


def add_slot(value: dict, ident: str, layout_id: str) -> dict:
    """The value with an arrangement's layout for one window more than its last: a zone layout
    chosen from the pool, of that many zones."""
    why = add_slot_problem(value, ident)
    if why:
        raise ArrangementsError(why)
    entry = arrangement(value, ident)
    count = last_count(entry) + 1
    why = _fits(value, layout_id, count)
    if why:
        raise ArrangementsError(why)
    return _replaced(value, ident, dict(entry, windows={**entry["windows"],
                                                        str(count): layout_id}))


def remove_last_slot(value: dict, ident: str) -> dict:
    """The value without an arrangement's last layout. The zone layout stays in the pool."""
    entry = arrangement(value, ident)
    if entry is None:
        raise ArrangementsError(_GONE)
    count = last_count(entry)
    if count <= 1:
        raise ArrangementsError("An arrangement keeps the whole screen for one window.")
    kept = {k: held for k, held in entry["windows"].items() if k != str(count)}
    return _replaced(value, ident, dict(entry, windows=kept))


# ---------------------------------------------------------------------- in words

def _name_of(value: dict, ident: str) -> str:
    held = layout(value, ident)
    return held["name"] if held else ident


def describe(before: dict, after: dict) -> list[str]:
    """What changed from one value to the other, in the words the tab uses.

    The zone layouts first, a line for each change to one -- and a change to its zones names every
    arrangement that uses it, because they change with it -- then the arrangements: added,
    renamed, deleted, in or out of the rotation, and a layout for a number of windows added,
    removed, or another zone layout in its place; and the order of either list. Read from the two
    values and from nothing else, so it cannot say something that did not change -- the same
    promise `SettingsPage._said` makes for the fields.
    """
    said: list[str] = []
    old = {held["id"]: held for held in before["layouts"]}
    new = {held["id"] for held in after["layouts"]}
    for held in after["layouts"]:
        was = old.get(held["id"])
        name = held["name"]
        if was is None:
            said.append(f"zone layout {name} added")
            continue
        if was["name"] != name:
            said.append(f"zone layout {was['name']} renamed {name}")
        if was["tree"] != held["tree"]:
            found = [a["name"] for a, _ in users(after, held["id"])]
            said.append(f"zone layout {name} changed"
                        + (f", and with it {_named(found)}" if found else ""))
        if was["drag"] != held["drag"]:
            said.append(f"zone layout {name} {'offered' if held['drag'] else 'no longer offered'} "
                        f"when a window is dragged")
    said += [f"zone layout {held['name']} deleted" for held in before["layouts"]
             if held["id"] not in new]
    kept = [held["id"] for held in before["layouts"] if held["id"] in new]
    if kept != [held["id"] for held in after["layouts"] if held["id"] in old]:
        said.append("the order of the zone layouts changed")

    old = {a["id"]: a for a in before["arrangements"]}
    new = {a["id"] for a in after["arrangements"]}
    for a in after["arrangements"]:
        was = old.get(a["id"])
        name = a["name"]
        if was is None:
            said.append(f"{name} added")
            continue
        if was["name"] != name:
            said.append(f"{was['name']} renamed {name}")
        if was["cycle"] != a["cycle"]:
            said.append(f"{name} {'in' if a['cycle'] else 'out of'} the rotation")
        n_was, n_now = last_count(was), last_count(a)
        for count in range(2, max(n_was, n_now) + 1):
            key = str(count)
            if count > n_was:
                said.append(f"{name}: {_name_of(after, a['windows'][key])} for "
                            f"{windows(count)} added")
            elif count > n_now:
                said.append(f"{name}: the layout for {windows(count)} removed")
            elif was["windows"][key] != a["windows"][key]:
                said.append(f"{name}: {_name_of(after, a['windows'][key])} for {windows(count)}, "
                            f"in place of {_name_of(before, was['windows'][key])}")
    said += [f"{a['name']} deleted" for a in before["arrangements"] if a["id"] not in new]
    kept = [a["id"] for a in before["arrangements"] if a["id"] in new]
    if kept != [a["id"] for a in after["arrangements"] if a["id"] in old]:
        said.append("the order of the arrangements changed")
    return said
