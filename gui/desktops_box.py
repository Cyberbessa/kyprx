"""The Tiling tab's Desktops box: the desktops KDE has, each with the arrangement it starts on.

The owner asked to see the virtual desktops on the Tiling tab and choose there which arrangement
each one is on. One card per desktop, in the compositor's order, with the picture of its
arrangement's last layout; clicking it opens a menu of the arrangements, and *First in the
rotation*, which is what a desktop with no choice starts on. The choice is the tiler's key
`desktopArrangements` -- JSON from a desktop's name to an arrangement's id -- sent with the page's
other changes (`extra_changes`, `sent`, `said`, the shape `TilingValue` takes), so it goes out on
the page's clock and in its one call.

By name, as the daemon and the engine read it (`tiling.desktops_of`, `startOf` in engine.mjs), so a
choice outlives a login, where a desktop keeps its name. Names this desk does not have -- a
desktop renamed, or another machine's in a KyprX folder both share -- are kept as they are and
never sent away. The desktops KyprX makes for a window that finds every zone taken are not listed:
the daemon leaves them out (`TilingPart.desktops_now`), and they start on the arrangement of the
desktop they were made from. Next Layout and Previous Layout move a screen on from its desktop's
choice until the next login, and change nothing here.
"""

from __future__ import annotations

import json

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMenu, QVBoxLayout

import splits
from layout_builder import LayoutCard, flow_holder, screen_ratio, tab_before
from tiling_value import TilingValue, plain_tip
from widgets import SECTION_HINTS, Section, note

KEY = "desktopArrangements"

#: The menu's first entry, and what a desktop with no choice is shown on.
FIRST = "First in the rotation"

#: Folded, while automatic tiling is off, as the Arrangements box folds.
OFF = "The desktops start on an arrangement of automatic tiling, which is off."

#: When the daemon could not ask the compositor which desktops there are.
UNKNOWN = ("The desktops could not be read from the desktop, so none can be given an arrangement "
           "here right now.")


def canonical(chosen: dict) -> str:
    """The text a choice is compared by, the daemon's own spelling of it
    (`tiling.canonical_desktops`): "" for none."""
    return json.dumps(dict(sorted(chosen.items())), ensure_ascii=False,
                      separators=(",", ":")) if chosen else ""


def read(raw) -> dict:
    """The choice the file holds, read as the daemon reads it: text to text, else none."""
    try:
        value = json.loads(raw) if isinstance(raw, str) and raw.strip() else {}
    except (ValueError, RecursionError):
        return {}
    if not isinstance(value, dict):
        return {}
    return {k: v for k, v in value.items() if isinstance(k, str) and k and isinstance(v, str)}


class DesktopsBox(Section):
    """The desktops, each a card naming the arrangement it starts on."""

    #: A choice was made: the page starts its clock.
    changed = Signal()

    def __init__(self, model: TilingValue, parent=None):
        super().__init__("Desktops", SECTION_HINTS["Desktops"], parent)
        self.model = model
        #: The desktops as the daemon last listed them, or None when it could not.
        self.listed: list[dict] | None = None
        #: What is chosen here, and the file's text it is compared against.
        self.chosen: dict[str, str] = {}
        self.baseline = ""
        self.cards: list[LayoutCard] = []
        self._ratio = 16 / 9

        self._holder, self._flow = flow_holder()
        self.unknown = note(UNKNOWN)
        self.unknown.setVisible(False)
        self.off_line = note(OFF)
        self.off_line.setVisible(False)
        outer = QVBoxLayout(self)
        outer.addWidget(self._holder)
        outer.addWidget(self.unknown)
        outer.addWidget(self.off_line)
        model.shown.connect(lambda _anew: self._paint())

    # ---------------------------------------------------------------- what the page asks

    def load(self, data: dict, listed: list[dict] | None) -> None:
        """The file's choice and the desktops there are, from the daemon. What is chosen here is
        the file's from now on: the page repaints only while nothing on it waits to be sent."""
        stored = read((data.get("tiling") or {}).get(KEY))
        self.chosen = dict(stored)
        self.baseline = canonical(stored)
        self.listed = [d for d in listed if isinstance(d, dict)] if isinstance(listed, list) \
            else None
        self._paint()

    def extra_changes(self) -> dict:
        """The choice, when it is not the file's: its canonical text, or None for none, which
        takes the key away."""
        text = canonical(self.chosen)
        if text == self.baseline:
            return {}
        return {"tiling": {KEY: text or None}}

    def sent(self, tiling: dict) -> None:
        if KEY in tiling:
            self.baseline = tiling[KEY] or ""

    def said(self) -> str:
        """The words for the window's line: each desktop whose choice is not the file's."""
        was = read(self.baseline)
        moved = [name for name in sorted(set(was) | set(self.chosen))
                 if was.get(name) != self.chosen.get(name)]
        return ", ".join(f"{name} starts on {self._name_of(self.chosen.get(name))}"
                         for name in moved)

    def set_collapsed(self, collapsed: bool) -> None:
        self._holder.setVisible(not collapsed and self.listed is not None)
        self.unknown.setVisible(not collapsed and self.listed is None)
        self.off_line.setVisible(collapsed)

    def collapsed(self) -> bool:
        return self.off_line.isVisibleTo(self)

    # ---------------------------------------------------------------- painting

    def _arrangements(self) -> list[dict]:
        value = self.model.value
        return list(value["arrangements"]) if value else []

    def _first(self) -> dict | None:
        listed = self._arrangements()
        return next((a for a in listed if a.get("cycle", True)), listed[0] if listed else None)

    def _of(self, ident: str | None) -> dict | None:
        """The arrangement a desktop starts on: its choice when that is an arrangement, the first
        in the rotation otherwise -- as the engine reads it (`startOf`)."""
        value = self.model.value
        found = splits.arrangement(value, ident) if value and ident else None
        return found or self._first()

    def _name_of(self, ident: str | None) -> str:
        found = self._of(ident)
        return found["name"] if found else ""

    def _paint(self) -> None:
        self._ratio = screen_ratio(self)
        listed = self.listed or []
        while len(self.cards) > len(listed):
            gone = self.cards.pop()
            self._flow.removeWidget(gone)
            gone.setParent(None)
            gone.deleteLater()
        grows = len(self.cards) < len(listed)
        while len(self.cards) < len(listed):
            card = LayoutCard(self._ratio)
            card.clicked.connect(lambda _on=False, i=len(self.cards): self._choose(i))
            self._flow.addWidget(card)
            self.cards.append(card)
        if grows and self.cards:
            tab_before(self.cards, self.off_line)
        value = self.model.value
        for card, desktop in zip(self.cards, listed):
            name = str(desktop.get("name") or "")
            ident = self.chosen.get(name)
            entry = self._of(ident)
            tree = {}
            if entry and value:
                last = splits.last_count(entry)
                if last >= 2:
                    tree = splits.layout(value, entry["windows"][str(last)])["tree"]
            on = entry["name"] if entry else ""
            how = on if ident and splits.arrangement(value, ident) else f"{on}, {FIRST.lower()}"
            card.set_ratio(self._ratio)
            card.show_layout(tree, f"{name} — {on}",
                             tip=plain_tip(f"{name} starts on {how}. Click to choose another."),
                             accessible=f"Desktop {desktop.get('number')}, {name}: starts on "
                                        f"{how}")
            card.setChecked(bool(ident) and splits.arrangement(value, ident) is not None)
            card.setEnabled(self.model.loaded and bool(name))
        self._holder.updateGeometry()
        self.set_collapsed(self.collapsed())

    # ---------------------------------------------------------------- choosing

    def _choose(self, index: int) -> None:
        """The menu of the arrangements for one desktop, opened under its card. Opened inside the
        value's `asking`, so the page does not repaint under it."""
        listed = self.listed or []
        if not (0 <= index < len(listed)):
            return
        name = str(listed[index].get("name") or "")
        card = self.cards[index]
        card.setChecked(name in self.chosen)    # a click toggles a checkable card; undone
        first = self._first()
        menu = QMenu(card)
        none = menu.addAction(f"{FIRST} ({first['name']})" if first else FIRST)
        none.setCheckable(True)
        none.setChecked(name not in self.chosen)
        none.setData("")
        menu.addSeparator()
        for entry in self._arrangements():
            action = menu.addAction(entry["name"])
            action.setCheckable(True)
            action.setChecked(self.chosen.get(name) == entry["id"])
            action.setData(entry["id"])
        with self.model.asking():
            picked = menu.exec(card.mapToGlobal(card.rect().bottomLeft()))
        if picked is None:
            return
        self.pick(name, str(picked.data() or ""))

    def pick(self, name: str, ident: str) -> None:
        """`name` to start on the arrangement `ident`, or on the first in the rotation for ""."""
        if ident:
            self.chosen[name] = ident
        else:
            self.chosen.pop(name, None)
        self._paint()
        self.changed.emit()
