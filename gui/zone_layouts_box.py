"""The Tiling tab's Zone layouts box: every way of dividing a screen that the arrangements and a drag
can use, and the builder that edits them.

`ZoneLayoutsBox` shows the zone layouts as cards (`LayoutCard`), in their order -- the order a drag
offers them in -- with the buttons that add, copy, rename, move and delete one, and *Offer on drag*
(`OfferButton`), which says whether a drag offers the one selected. Under them is the one selected:
its name, then the builder (`gui/layout_builder.py`) beside what can be done to the zone and the
divider chosen there; then which arrangements use it, and the way to put KyprX's own zone layouts
and arrangements back.

It edits the value the Arrangements box edits too (`gui/tiling_value.py`): an edit made here is
handed to that one value, both boxes paint the result, and the page sends it. The rules of a zone
layout, and what is refused, are `gui/splits.py`'s.
"""

from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QMenu, QPushButton, QVBoxLayout

import splits
from layout_builder import (LayoutBuilder, LayoutCard, OfferButton, flow_holder, screen_ratio,
                            tab_before)
from splits import windows
from tiling_value import NAME_ROOM, TilingValue, fitted, listed, plain_tip
from widgets import SECTION_HINTS, Section, Spin, note, warning


#: What *Offer on drag* does. The bar a drag shows, and Next Layout and Previous Layout while
#: automatic tiling is off, offer the whole screen and the first twelve zone layouts offered on a
#: drag, in this box's order (`splits.MAX_DRAG`, `MAX_OFFERED` in `engine.mjs`). A desk can hold
#: more offered than that -- the upgrade from version 1 offers, besides KyprX's own, every layout a
#: drag offered before (`tiling.upgrade`) -- so the sentence says what the bar has room for, and
#: not that no more can be offered.
DRAG_TIP = ("Offer on drag: a window dragged shows a bar at the top of the screen that offers the "
            "whole screen and the zone layouts with Offer on drag on, in this order -- on every "
            "drag while automatic tiling is off, and while it is on, for a floating window or a "
            "tiled one dragged with Shift. Once the window has been through the bar, or with "
            "Shift held, it is offered the zones of the zone layout its screen is on. With "
            "automatic tiling off, Next Layout and Previous Layout walk the same list. The bar has "
            "room for twelve, and no more is offered here once twelve are.")

#: What the builder shows, on its tooltip and in what it is read out as rather than on a line of
#: its own under it: the numbers and the wash are on every card as well, and are read once.
BUILDER_TIP = ("The numbers are the order windows fill the zones in, and the washed zone is the "
               "master zone, filled first. Click a zone to choose it, drag a divider to move it, "
               "and right-click a zone for what can be done to it.")

#: What the reset says it keeps. The daemon keeps a copy of the desk before it takes the key away
#: (`SetGroups`), and *Go back to a copy…* on the Settings tab puts that copy back, zone layouts,
#: arrangements and all.
KEPT = ("A copy of the desk is kept first, so Go back to a copy… on the Settings tab brings them "
        "back.")


class ZoneLayoutsBox(Section):
    """The zone layouts, and the builder that edits them.

    **What an arrangement uses keeps its number of zones.** An arrangement uses a zone layout for
    as many windows as it has zones, so a layout in use cannot be split or lose a zone here --
    the buttons say who uses it, and a line under the builder names them too, with *Make a copy
    to change*, which makes one nobody uses. A divider moved or another master zone chosen keeps
    the number, and changes every arrangement that uses the layout, which that line's tooltip
    says.

    The selection -- which zone layout, which zone and which divider -- is kept across every paint,
    whichever box made the edit, and falls back to the first zone layout only when the one selected
    is gone. Every name is shown as it is spelled: the box's own lines and its questions are plain
    text, and a tooltip that names something is made plain (`plain_tip`).
    """

    def __init__(self, model: TilingValue, parent=None):
        super().__init__("Zone layouts", SECTION_HINTS["Zone layouts"], parent)
        self.model = model
        #: The zone layout selected, by its id, which a rename keeps.
        self._lid = ""
        self._ratio = 16 / 9
        #: Set across a paint, so a widget set from code edits nothing.
        self._painting = False
        #: Which zone layout the builder showed last, so a zone is kept only on the same one.
        self._shown_layout: str | None = None
        #: The zone to choose on the next paint, after a split or a removal made it a new one.
        self._want_zone = None

        #: Why nothing in the two boxes can be changed: shown here, once, for both. Plain text,
        #: because the daemon's sentence about a stored value it cannot read can name an
        #: arrangement, or a key somebody typed.
        self.trouble = warning()
        self.trouble.setTextFormat(Qt.TextFormat.PlainText)

        holder, self._flow = flow_holder()
        self._cards_holder = holder
        self.cards: list[LayoutCard] = []

        self.add_button = QPushButton("Add…")
        self.duplicate_button = QPushButton("Duplicate")
        self.rename_button = QPushButton("Rename…")
        self.left_button = QPushButton("Move left")
        self.right_button = QPushButton("Move right")
        self.delete_button = QPushButton("Delete…")
        self.rename_button.setToolTip("Give the selected zone layout another name. The "
                                      "arrangements that use it go on using it.")
        self.left_button.setToolTip("Earlier in the order a drag offers zone layouts in.")
        self.right_button.setToolTip("Later in the order a drag offers zone layouts in.")
        self.add_button.clicked.connect(self._add)
        self.duplicate_button.clicked.connect(self._duplicate)
        self.rename_button.clicked.connect(self._rename)
        self.left_button.clicked.connect(lambda: self._move(-1))
        self.right_button.clicked.connect(lambda: self._move(1))
        self.delete_button.clicked.connect(self._delete)
        #: Whether a drag offers the zone layout selected: down while it does. The tooltip is the
        #: whole sentence, and is what it is read out as too -- it has no mark beside it.
        self.drag_button = OfferButton()
        self.drag_button.setToolTip(DRAG_TIP)
        self.drag_button.setAccessibleDescription(DRAG_TIP)
        self.drag_button.toggled.connect(self._drag_ticked)
        #: Two rows: the first makes, copies, names and orders a zone layout, and the second opens
        #: with *Offer on drag*, where it is seen at once. The stretch before *Delete…*, as on the
        #: profiles: the one button that cannot be undone sits away from the ones that can.
        actions = QVBoxLayout()
        first = QHBoxLayout()
        for button in (self.add_button, self.duplicate_button, self.rename_button,
                       self.left_button, self.right_button):
            first.addWidget(button)
        first.addStretch()
        second = QHBoxLayout()
        second.addWidget(self.drag_button)
        second.addStretch()
        second.addWidget(self.delete_button)
        actions.addLayout(first)
        actions.addLayout(second)

        self.builder = LayoutBuilder()
        self.builder.setToolTip(BUILDER_TIP)
        self.builder.setAccessibleDescription(BUILDER_TIP)
        self.builder.zone_chosen.connect(lambda _path: self._sync())
        self.builder.divider_chosen.connect(lambda _path, _index: self._sync())
        self.builder.moving.connect(self._divider_moving)
        self.builder.edited.connect(self._builder_edited)
        self.builder.menu_wanted.connect(self._zone_menu)
        model.hold(self.builder)
        #: The name of the zone layout in the builder, over it and the buttons beside it. Plain
        #: text, bold by the font -- a plain-text label would print the markup -- wrapped, and on
        #: a line of its own: beside the builder, a name of forty wide letters made the page 53 px
        #: wider than the room it has at the window's narrowest (measured offscreen).
        self.name_label = QLabel()
        self.name_label.setTextFormat(Qt.TextFormat.PlainText)
        self.name_label.setWordWrap(True)
        bold = QFont(self.name_label.font())
        bold.setBold(True)
        self.name_label.setFont(bold)
        self.split_h = QPushButton("Split side by side")
        self.split_v = QPushButton("Split top to bottom")
        self.remove_zone_button = QPushButton("Remove this zone")
        self.master_button = QPushButton("Make master zone")
        self.split_h.clicked.connect(lambda: self._split("h"))
        self.split_v.clicked.connect(lambda: self._split("v"))
        self.remove_zone_button.clicked.connect(self._remove_zone)
        self.master_button.clicked.connect(self._make_master)
        zone_buttons = QGridLayout()
        zone_buttons.setContentsMargins(0, 0, 0, 0)
        zone_buttons.addWidget(self.split_h, 0, 0)
        zone_buttons.addWidget(self.split_v, 0, 1)
        zone_buttons.addWidget(self.remove_zone_button, 1, 0)
        zone_buttons.addWidget(self.master_button, 1, 1)
        # The spare width to a column of its own, so the four keep the width their words need.
        zone_buttons.setColumnStretch(2, 1)
        self.divider_label = QLabel()
        self.divider_spin = Spin()
        self.divider_spin.setSuffix(" %")
        self.divider_spin.setMaximumWidth(90)
        self.divider_spin.valueChanged.connect(self._divider_spun)
        divider_row = QHBoxLayout()
        divider_row.setContentsMargins(0, 0, 0, 0)
        divider_row.addWidget(self.divider_label)
        divider_row.addWidget(self.divider_spin)
        divider_row.addStretch()
        controls = QVBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.addLayout(zone_buttons)
        controls.addLayout(divider_row)
        building = QHBoxLayout()
        building.addWidget(self.builder, 0, Qt.AlignmentFlag.AlignTop)
        building.addLayout(controls, 1)
        # Held to the top rather than pushed there by a stretch: a stretch in here would make the
        # box one that grows, and the page's spare height would go into it as gaps.
        building.setAlignment(controls, Qt.AlignmentFlag.AlignTop)

        #: Who uses the zone layout selected, while somebody does, in a short line; why it keeps its
        #: zones, and who changes with it, in its tooltip (`_used_words`). Plain text, because it
        #: names arrangements.
        self.used = note()
        self.used.setTextFormat(Qt.TextFormat.PlainText)
        self.copy_button = QPushButton("Make a copy to change")
        self.copy_button.clicked.connect(self._copy_to_change)
        used_row = QHBoxLayout()
        used_row.addWidget(self.used, 1)
        used_row.addWidget(self.copy_button, 0, Qt.AlignmentFlag.AlignTop)

        #: The box's own line: why an edit was refused, or what an edit did besides itself. Shown
        #: only while it has something to say (`_tell`). Plain text, because what it says names
        #: zone layouts and arrangements, and a name is shown as it is spelled. A label left to
        #: guess between plain and rich text, as Qt's labels are, takes a text with no tag in it as
        #: plain and one with a tag as rich -- measured offscreen: a name escaped for rich text
        #: shows as `Tom&#x27;s &amp; Jerry`, and one with a tag in it, `<b>Work</b>`, as markup.
        self.line = note()
        self.line.setTextFormat(Qt.TextFormat.PlainText)
        self.line.setVisible(False)

        #: Alone on its row and at the far side, for the reason *Restore KyprX's defaults…* is: it
        #: replaces everything in this box and the one above it.
        self.reset_button = QPushButton("Put KyprX's zone layouts and arrangements back…")
        self.reset_button.clicked.connect(self._put_back)
        reset_row = QHBoxLayout()
        reset_row.addStretch()
        reset_row.addWidget(self.reset_button)

        column = QVBoxLayout(self)
        column.addWidget(self.trouble)
        column.addWidget(self._cards_holder)
        column.addLayout(actions)
        column.addWidget(self.name_label)
        column.addLayout(building)
        column.addLayout(used_row)
        column.addWidget(self.line)
        column.addLayout(reset_row)

        model.shown.connect(self._shown)
        self._paint_all()

    # ---------------------------------------------------------------- what the page asks

    def select(self, ident: str) -> bool:
        """Select this zone layout, as the Arrangements box asks -- *Edit in Zone layouts*. False
        when the value has no such zone layout."""
        value = self.model.value
        if value is None or splits.layout(value, ident) is None:
            return False
        if ident != self._lid:
            self._lid = ident
            self._paint_all()
        return True

    def card_for(self, ident: str) -> LayoutCard | None:
        """The card that shows this zone layout, for the page to scroll to."""
        value = self.model.value
        i = splits.layout_index(value, ident) if value else -1
        return self.cards[i] if 0 <= i < len(self.cards) else None

    def _current(self) -> dict | None:
        return splits.layout(self.model.value, self._lid) if self.model.value else None

    # ---------------------------------------------------------------- painting

    def _shown(self, anew: bool) -> None:
        """The value to show changed, from the daemon or from an edit in either box."""
        self._ratio = screen_ratio(self)
        if anew:
            self._tell("")
        value = self.model.value
        if value and splits.layout(value, self._lid) is None:
            self._lid = value["layouts"][0]["id"]
        self._paint_all()

    def _paint_all(self) -> None:
        self._painting = True
        try:
            self.trouble.setText(self.model.locked)
            self.trouble.setVisible(bool(self.model.locked))
            self._paint_cards()
            self._paint_builder()
        finally:
            self._painting = False
        self._sync()

    def _paint_cards(self) -> None:
        """The cards, painted over the ones already there where it can be, so a card the keyboard
        is on stays the one it is on. A card made goes in the keyboard's Tab order with the others,
        before *Add…*: given its parent at a paint, it would be reached last (`tab_before`)."""
        value = self.model.value
        layouts = value["layouts"] if value else []
        while len(self.cards) > len(layouts):
            gone = self.cards.pop()
            self._flow.removeWidget(gone)
            gone.setParent(None)
            gone.deleteLater()
        grows = len(self.cards) < len(layouts)
        while len(self.cards) < len(layouts):
            made = LayoutCard(self._ratio)
            made.clicked.connect(lambda _on=False, i=len(self.cards): self._card_chosen(i))
            self._flow.addWidget(made)
            self.cards.append(made)
        if grows:
            tab_before(self.cards, self.add_button)
        for card, held in zip(self.cards, layouts):
            count = splits.zones(held["tree"])
            said = [held["name"], f"{count} zones"]
            if held["drag"]:
                said.append("Offered when a window is dragged")
            found = splits.users(value, held["id"])
            if found:
                said.append(f"{listed([a['name'] for a, _ in found])} "
                            f"{'uses' if len(found) == 1 else 'use'} it for {count} windows")
            card.set_ratio(self._ratio)
            card.show_layout(held["tree"], held["name"], drag=held["drag"],
                             tip=plain_tip("\n".join(said)),
                             accessible=f"{held['name']}, {count} zones")
            card.setChecked(held["id"] == self._lid)
            card.setEnabled(self.model.loaded)
        self._cards_holder.updateGeometry()

    def _paint_builder(self) -> None:
        held = self._current()
        if held is None:
            self.builder.set_layout({}, read_only=True)
            self.builder.setEnabled(False)
            self.name_label.setText("")
            self.drag_button.set_offered(False)
            self._shown_layout = None
            return
        same = self._shown_layout == held["id"]
        zone = self._want_zone if self._want_zone is not None else (
            self.builder.zone if same else None)
        divider = self.builder.divider if same and self._want_zone is None else None
        self._want_zone = None
        count = splits.zones(held["tree"])
        self.builder.set_ratio(self._ratio)
        self.builder.set_layout(held["tree"], read_only=not self.model.editable(), zone=zone,
                                divider=divider, accessible=f"{held['name']}, {count} zones")
        self.builder.setEnabled(self.model.loaded and not self.model.locked)
        self._shown_layout = held["id"]
        self.name_label.setText(f"{fitted(self.name_label, held['name'], 3 * NAME_ROOM // 2)} · "
                                f"{count} zones")
        self.drag_button.set_offered(held["drag"])

    def _sync(self) -> None:
        """Every button says what can be done now, and a greyed one says why not."""
        value = self.model.value
        held = self._current()
        editable = self.model.editable()
        chosen = editable and held is not None
        lid = held["id"] if held else ""
        items = value["layouts"] if value else []
        i = splits.layout_index(value, lid) if chosen else -1

        why = splits.create_problem(value) if editable else ""
        self.add_button.setEnabled(editable and not why)
        self.add_button.setToolTip(why or "A new zone layout, two halves to start from, at the "
                                          "end. A drag does not offer it until Offer on drag is "
                                          "on.")
        self.duplicate_button.setEnabled(chosen and not why)
        self.duplicate_button.setToolTip(why or "A copy of the selected zone layout, straight "
                                                "after it, that no arrangement uses.")
        self.copy_button.setEnabled(chosen and not why)
        self.copy_button.setToolTip(why or "A copy of it, straight after it, that no arrangement "
                                           "uses -- and so one that can be split, and lose a "
                                           "zone.")
        self.rename_button.setEnabled(chosen)
        self.left_button.setEnabled(chosen and i > 0)
        self.right_button.setEnabled(chosen and 0 <= i < len(items) - 1)
        why = splits.delete_layout_problem(value, lid) if chosen else ""
        self.delete_button.setEnabled(chosen and not why)
        self.delete_button.setToolTip(plain_tip(why) or (
            "Forget the selected zone layout, which no arrangement uses." if chosen else ""))
        self.drag_button.setEnabled(chosen)

        zone = self.builder.zone
        for button, direction, does in (
                (self.split_h, "h", "Splits the zone chosen in two, side by side: one zone more."),
                (self.split_v, "v", "Splits the zone chosen in two, one above the other: one "
                                    "zone more.")):
            why = splits.split_problem(value, lid, zone, direction) if chosen else ""
            button.setEnabled(chosen and not why)
            button.setToolTip(plain_tip(why) or does)
        why = splits.remove_zone_problem(value, lid, zone) if chosen else ""
        self.remove_zone_button.setEnabled(chosen and not why)
        self.remove_zone_button.setToolTip(
            plain_tip(why) or "Takes the zone chosen away. Its space goes to the zone before it, "
                              "or after it when it is the first, and when it was the master zone, "
                              "the zone that takes its space is the master zone from then on.")
        root = held["tree"] if held else {}
        is_master = bool(held) and splits.fill_order(root)[0] == zone
        self.master_button.setEnabled(chosen and not is_master)
        self.master_button.setToolTip(
            "The zone chosen is the master zone already: windows fill it first." if is_master
            else "Windows fill the master zone first, then the rest in order.")
        self._show_divider(root if held else None)

        found = splits.users(value, lid) if held else []
        said, why = self._used_words(found) if found else ("", "")
        self.used.setText(said)
        self.used.setToolTip(plain_tip(why))
        self.used.setVisible(bool(found))
        self.copy_button.setVisible(bool(found))

        offered = self.model.reset_offered()
        self.reset_button.setEnabled(offered)
        self.reset_button.setToolTip(
            "Replace every zone layout and arrangement with the ones KyprX comes with. Asks "
            "first." if offered
            else "These are the zone layouts and arrangements KyprX comes with already."
            if self.model.loaded and not self.model.locked
            else "Not while the zone layouts and arrangements cannot be changed here.")

    def _used_words(self, found: list) -> tuple[str, str]:
        """Who uses the zone layout selected, in the few words of the line under the builder; and
        for its tooltip, why it keeps its zones and who changes with it."""
        held = self._current()
        said = (f"Used by {listed([a['name'] for a, _ in found])} for "
                f"{windows(found[0][1])}.")
        whom = found[0][0]["name"] if len(found) == 1 else "each of them"
        return said, (f"{splits.used_problem(self.model.value, held['id'])} Moving a divider or "
                      f"choosing another master zone changes {whom} as well.")

    def _show_divider(self, root) -> None:
        """The number beside the builder: the share of the part before the divider chosen."""
        divider = self.builder.divider if root else None
        on = bool(divider) and self.model.editable() and splits.has_path(root, divider[0])
        self.divider_spin.blockSignals(True)
        try:
            if on:
                path, index = divider
                node = splits.node_at(root, path)
                low, high = splits.divider_range(root, path, index)
                self.divider_spin.setSpecialValueText("")
                self.divider_spin.setRange(low, high)
                self.divider_spin.setValue(node["sizes"][index])
                self.divider_label.setText("Left of the divider:" if node["split"] == "h"
                                           else "Above the divider:")
            else:
                # A dash and not a number: with no divider chosen there is no share to show, and
                # a greyed "0 %" reads as one.
                self.divider_spin.setRange(0, 0)
                self.divider_spin.setSpecialValueText("—")
                self.divider_label.setText("Divider:")
        finally:
            self.divider_spin.blockSignals(False)
        self.divider_spin.setEnabled(on)
        self.divider_spin.setToolTip("Moves the divider chosen in the picture; the part across "
                                     "it gives or takes, and every other one keeps its size."
                                     if on else "Choose a divider in the picture to move it.")

    # ---------------------------------------------------------------- choosing

    def _card_chosen(self, i: int) -> None:
        value = self.model.value
        if self._painting or value is None or not 0 <= i < len(value["layouts"]):
            return
        self._lid = value["layouts"][i]["id"]
        self._paint_all()

    def _divider_moving(self, root) -> None:
        """A drag under way: the number and the card follow it, and nothing is edited."""
        self._show_divider(root)
        card = self.card_for(self._lid)
        if card is not None:
            card.root = root
            card.update()

    # ---------------------------------------------------------------- editing

    def _commit(self, value, told: str = "") -> None:
        """Hand an edited value to the model; the line says what it did besides itself, or why
        it was refused. Both boxes paint it before this one's line is set."""
        self._tell(self.model.commit(value, told))

    def _tell(self, text: str) -> None:
        self.line.setText(text)
        self.line.setVisible(bool(text))

    def _refuse(self, why) -> None:
        self._tell(str(why))
        self._paint_all()

    def _edit_tree(self, change) -> None:
        """Apply `change` to the selected zone layout's tree and take the result."""
        held = self._current()
        if held is None or not self.model.editable():
            return
        try:
            value = splits.set_tree(self.model.value, held["id"], change(held["tree"]))
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._commit(value)

    def _builder_edited(self, root) -> None:
        self._edit_tree(lambda _tree: root)

    def _divider_spun(self, share: int) -> None:
        if self._painting or self.builder.divider is None:
            return
        path, index = self.builder.divider
        self._edit_tree(lambda tree: splits.move_divider(tree, path, index, share))

    def _make_master(self) -> None:
        zone = self.builder.zone
        self._edit_tree(lambda tree: splits.set_master(tree, splits.leaf_paths(tree).index(zone)))

    def _split(self, direction: str) -> None:
        """Split the zone chosen in two, in place: the zone keeps the first half, and the new zone,
        the second, is the one chosen after it."""
        held = self._current()
        if held is None or not self.model.editable():
            return
        zone = self.builder.zone
        why = splits.split_problem(self.model.value, held["id"], zone, direction)
        if why:
            self._tell(why)
            return
        parent = splits.node_at(held["tree"], zone[:-1]) if zone else None
        made = (zone[:-1] + (zone[-1] + 1,) if parent is not None
                and parent["split"] == direction else zone + (1,))
        try:
            value = splits.split_layout(self.model.value, held["id"], zone, direction)
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._want_zone = made
        self._commit(value)

    def _remove_zone(self) -> None:
        """Take the zone chosen away; the zone that takes its space is the one chosen after it."""
        held = self._current()
        if held is None or not self.model.editable():
            return
        zone = self.builder.zone
        why = splits.remove_zone_problem(self.model.value, held["id"], zone)
        if why:
            self._tell(why)
            return
        try:
            value = splits.remove_layout_zone(self.model.value, held["id"], zone)
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._want_zone = self._taker(held["tree"], zone,
                                      splits.layout(value, held["id"])["tree"])
        self._commit(value)

    @staticmethod
    def _taker(before: dict, zone: tuple, after: dict):
        """Where the zone that took a removed zone's space is in the layout without it: the part
        before it in its split, or after it for the first -- its first zone, when that part is a
        split -- and in its split's place when the split was left with that part alone
        (`splits.remove_zone`). None when it cannot be found, and the builder chooses the master
        zone then."""
        parent = splits.node_at(before, zone[:-1])
        index = zone[-1] - 1 if zone[-1] else 0
        place = zone[:-1] if len(parent["parts"]) == 2 else zone[:-1] + (index,)
        if not splits.has_path(after, place):
            return None
        return place + splits.leaf_paths(splits.node_at(after, place))[0]

    def _drag_ticked(self, on: bool) -> None:
        """*Offer on drag*, on or off. A thirteenth, and the last one off, are refused in the line,
        and the button goes back as it was."""
        if self._painting:
            return
        held = self._current()
        if held is None or not self.model.editable() or on == held["drag"]:
            return
        try:
            value = splits.set_drag(self.model.value, held["id"], on)
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._commit(value)

    def _zone_menu(self, _path, where) -> None:
        """The builder's menu for a zone: what the buttons beside it do, where the pointer is.

        What was chosen runs once the menu has gone, and not from inside it, so a paint owed
        meanwhile is paid before it. And only while the zone layout the menu was opened on is
        still the one shown, with the tree and the zone it had: that paint can change the layout
        under the menu -- the KyprX folder, another machine -- or take it off the desk, and the
        selection then falls back to another, which a split chosen on the menu would change
        without a word. (Measured offscreen on the box before the pool, where a split chosen on
        one arrangement's layout went to another's once its own had left the desk meanwhile.)
        """
        if not self.model.editable():
            return
        held = self._current()
        opened_on = ((held["id"], copy.deepcopy(held["tree"]), self.builder.zone)
                     if held else None)
        menu = QMenu(self)
        acts = []
        for label, button, act in (
                ("Split side by side", self.split_h, lambda: self._split("h")),
                ("Split top to bottom", self.split_v, lambda: self._split("v")),
                ("Remove this zone", self.remove_zone_button, self._remove_zone),
                ("Make master zone", self.master_button, self._make_master)):
            action = menu.addAction(label)
            action.setEnabled(button.isEnabled())
            acts.append((action, act))
        with self.model.asking():
            chosen = menu.exec(where)
        act = next((act for action, act in acts if chosen is not None and action == chosen), None)
        menu.deleteLater()
        held = self._current()
        if act is not None and held is not None \
                and (held["id"], held["tree"], self.builder.zone) == opened_on:
            act()

    # ---------------------------------------------------------------- the list

    def _add(self) -> None:
        name = self.model.ask_name(self, "Add a zone layout", "A name for it:")
        if name is None or not self.model.editable():
            return
        try:
            value, ident = splits.add_layout(self.model.value, name)
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._lid = ident
        self._commit(value, "Two halves to start from. A drag does not offer it until Offer on "
                            "drag is on, and no arrangement uses it until one is given it under "
                            "Arrangements.")

    def _duplicate(self) -> None:
        self._copy("")

    def _copy_to_change(self) -> None:
        """*Make a copy to change*: a copy nobody uses, selected, to split and cut down."""
        self._copy("{name} is a copy no arrangement uses, so it can be split and lose a zone. "
                   "Under Arrangements, it can then be given to one for as many windows as it has "
                   "zones.")

    def _copy(self, told: str) -> None:
        """A copy of the selected zone layout, straight after it, selected; `told` is what the
        line says of it, `{name}` the copy's name."""
        held = self._current()
        if held is None or not self.model.editable():
            return
        try:
            value, ident = splits.duplicate_layout(self.model.value, held["id"])
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._lid = ident
        self._commit(value, told.format(name=splits.layout(value, ident)["name"]))

    def _rename(self) -> None:
        held = self._current()
        if held is None or not self.model.editable():
            return
        ident = held["id"]
        name = self.model.ask_name(self, "Rename this zone layout", "A new name for it:",
                                   held["name"])
        if name is None or not self.model.editable():
            return
        # The question let the page's paint in, if one was owed: the zone layout it named may have
        # been renamed or taken off the desk meanwhile.
        held = splits.layout(self.model.value, ident)
        if held is None or name.strip() == held["name"]:
            return
        try:
            value = splits.rename_layout(self.model.value, ident, name)
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._commit(value)

    def _move(self, step: int) -> None:
        if self._current() is None or not self.model.editable():
            return
        try:
            value = splits.move_layout(self.model.value, self._lid, step)
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._commit(value)

    def _delete(self) -> None:
        held = self._current()
        if held is None or not self.model.editable():
            return
        ident = held["id"]
        why = splits.delete_layout_problem(self.model.value, ident)
        if why:
            self._tell(why)
            return
        if self.model.sure(self, "Delete this zone layout?",
                           f"Delete {held['name']}? No arrangement uses it, and there is no way "
                           f"back."):
            return
        # What the question named, still there and still free to go: the paint it let in may have
        # given it to an arrangement.
        if not self.model.editable() or splits.layout(self.model.value, ident) is None:
            return
        i = splits.layout_index(self.model.value, ident)
        try:
            value = splits.delete_layout(self.model.value, ident)
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._lid = value["layouts"][min(i, len(value["layouts"]) - 1)]["id"]
        self._commit(value)

    def _put_back(self) -> None:
        """Every zone layout and arrangement replaced by KyprX's own, after a question that names
        what goes and promises the copy of the desk the daemon keeps first. Sent at once
        (`TilingValue.put_back` says why)."""
        if not self.model.reset_offered():
            return
        if self.model.sure(self, "Put KyprX's zone layouts and arrangements back?",
                           self._reset_words()):
            return
        self.model.put_back()

    def _reset_words(self) -> str:
        """What the reset's question says goes, and what comes back."""
        defaults = self.model.defaults
        theirs = (f"KyprX's own are the arrangements "
                  f"{listed([a['name'] for a in defaults['arrangements']])}, with "
                  f"{len(defaults['layouts'])} zone layouts.")
        if self.model.locked:
            return ("The zone layouts and arrangements stored on this desk cannot be read, and "
                    f"putting KyprX's own back writes over them. {theirs} {KEPT}")
        value = self.model.value
        gone: list[str] = []
        back: list[str] = []
        moved: list[str] = []
        for kind, key in (("arrangement", "arrangements"), ("zone layout", "layouts")):
            own = {item["id"]: item for item in defaults[key]}
            here = {item["id"]: item for item in value[key]}
            names = [item["name"] for item in value[key] if item["id"] not in own]
            if names:
                gone.append(f"the {kind}{'s' if len(names) > 1 else ''} {listed(names)}")
            # Changed here, or deleted here: either way it comes back as KyprX has it.
            back += [item["name"] for item in defaults[key] if here.get(item["id"]) != item]
            if [i for i in here if i in own] != [i for i in own if i in here]:
                moved.append(f"{kind}s")
        said = []
        if gone:
            said.append(f"Yours go: {', and '.join(gone)}.")
        if back:
            said.append(f"KyprX's own come back as they came: {listed(back)}.")
        if moved:
            said.append(f"The {' and the '.join(moved)} go back to KyprX's order.")
        if not said:
            said.append("What is shown is KyprX's own already, and what this desk stores of it "
                        "is taken away, so the desk follows KyprX's own from then on.")
        return " ".join(said + [theirs, KEPT])
