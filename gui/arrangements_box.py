"""The Tiling tab's Arrangements box: the arrangements automatic tiling lays a screen out by, and
which zone layout each one uses for each number of windows.

`ArrangementsBox` lists the arrangements -- the ones in rotation ticked, in the order Next Layout
and Previous Layout walk them -- with the buttons that add, copy, rename, move and delete one. Under
the list is the selected arrangement's layout for each number of windows, as cards: the whole
screen for one window, and for more, one of the zone layouts with that many zones; and at the end
of the row, a card that adds the layout for one window more (`AddCard`). A card chosen shows the
zone layouts it can be, with a way to the Zone layouts box to edit the one in use -- and, on the
last layout, *Remove this layout*. It chooses among the zone layouts and never makes one: when
none has as many zones as there are windows it says so, and making one is the Zone layouts box's.

With automatic tiling off nothing is laid out by an arrangement, so the box folds to its title and
a line that says so (`set_collapsed`); the page decides when.

It edits the value the Zone layouts box edits too (`gui/tiling_value.py`): an edit made here is
handed to that one value, both boxes paint the result, and the page sends it. The rules of an
arrangement, and what is refused, are `gui/splits.py`'s.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QPushButton,
                               QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

import splits
from layout_builder import AddCard, LayoutCard, flow_holder, screen_ratio, tab_before
from splits import windows
from tiling_value import TilingValue, fitted, plain_tip
from widgets import SECTION_HINTS, Heading, Section, note


#: On the rotation's header, and on every tick. The layout keys walk the rotation while automatic
#: tiling is on; off, they walk the zone layouts a drag offers instead (`engine.mjs`), which is why
#: the box folds away then.
ROTATION_TIP = ("In rotation: Next Layout and Previous Layout walk the ticked arrangements, in the "
                "order of this list.")

#: Behind the heading over an arrangement's layouts.
SLOTS_TIP = ("The zone layout this arrangement lays a screen out by for each number of windows on "
             "it. One window has the whole screen. A window that opens with every zone of the "
             "last layout taken does what When the arrangement is full says, and one that comes "
             "back from being minimised, from floating or from another screen squeezes in, the "
             "last zone split in two. The card with a plus adds the layout for one window more.")

#: Behind the heading over the zone layouts a layout can be. What it says to do for a layout of
#: this arrangement's own is the whole way there: this box makes no zone layout, and a copy is
#: made where every zone layout is made.
CHOICES_TIP = ("Any of your zone layouts with as many zones as there are windows. One zone layout "
               "can serve several arrangements, and a change to it under Zone layouts changes "
               "every arrangement that uses it. To change it for this arrangement alone, "
               "duplicate it under Zone layouts and choose the copy here.")

#: What the box says, folded, while automatic tiling is off.
OFF = "Arrangements are used by automatic tiling, which is off."


class ArrangementsBox(Section):
    """The arrangements, and which zone layout each uses for each number of windows.

    The selection -- which arrangement, and which number of windows is being chosen for -- is kept
    across every paint, whichever box made the edit, and falls back to the first arrangement only
    when the one selected is gone; one window more than an arrangement's last is chosen for only on
    the arrangement it is being added to (`_paint_all`). Every name is shown as it is spelled: the
    box's own line and its questions are plain text, and a tooltip that names something is made
    plain (`plain_tip`). No button carries a name.

    **The keyboard's Tab order is the order on screen.** Tab leaves the list for the buttons under
    it, and the cards made as the box paints are put where they are drawn, an arrangement's
    layouts before the card that adds one (`_fill`).
    """

    #: A zone layout to select in the Zone layouts box, by its id, and scroll to.
    show_layout = Signal(str)

    def __init__(self, model: TilingValue, parent=None):
        super().__init__("Arrangements", SECTION_HINTS["Arrangements"], parent)
        self.model = model
        #: The arrangement selected, by its id, which a rename keeps.
        self._aid = ""
        #: The number of windows whose layout is being chosen: one of the arrangement's own, from 2
        #: to its last; one more than its last while the card that adds it is choosing; or None,
        #: while nothing is.
        self._slot: int | None = None
        #: The arrangement, by its id, whose layout for one window more than its last is being
        #: chosen: the one whose card that adds it was clicked, or *Remove this layout* -- which
        #: leaves the layout it took away being chosen for. None the rest of the time
        #: (`_paint_all`).
        self._adding: str | None = None
        self._ratio = 16 / 9
        #: Set across a paint, so a widget set from code edits nothing.
        self._painting = False

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Arrangement", "In rotation"])
        self.table.horizontalHeaderItem(1).setToolTip(ROTATION_TIP)
        self.table.verticalHeader().setVisible(False)
        self.table.setFrameShape(QTableWidget.Shape.NoFrame)   # as the other tables
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # Tab leaves the table, as it leaves every other control; the arrows move in it. A table
        # keeps Tab to itself by default, going from cell to cell and round again: measured
        # offscreen, Tab from the last tick went back to the first name, and nothing under the
        # list could be reached by Tab from above it.
        self.table.setTabKeyNavigation(False)
        # The page scrolls already, and a table scrolling inside it is a trap for the wheel -- so
        # it takes the height of its rows, the way the profiles' does.
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Fixed upright as well as fixed in height. A table asks to grow both ways by default, and
        # one item that asks makes the whole box one that grows: on a window taller than the page,
        # the box took the spare height and spread it as gaps between its rows.
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._table_selected)
        self.table.itemChanged.connect(self._rotation_ticked)

        self.add_button = QPushButton("Add…")
        self.duplicate_button = QPushButton("Duplicate")
        self.rename_button = QPushButton("Rename…")
        self.up_button = QPushButton("Move up")
        self.down_button = QPushButton("Move down")
        self.delete_button = QPushButton("Delete…")
        self.add_button.setToolTip("A new arrangement, in the rotation, with the whole screen for "
                                   "one window and your first zone layout of two zones for two.")
        self.duplicate_button.setToolTip("A copy of the selected arrangement, straight after it, "
                                         "using the same zone layouts.")
        self.rename_button.setToolTip("Give the selected arrangement another name. Each screen "
                                      "keeps the arrangement it is on.")
        self.up_button.setToolTip("Earlier in the order the layout keys walk the rotation in.")
        self.down_button.setToolTip("Later in the order the layout keys walk the rotation in.")
        self.add_button.clicked.connect(self._add)
        self.duplicate_button.clicked.connect(self._duplicate)
        self.rename_button.clicked.connect(self._rename)
        self.up_button.clicked.connect(lambda: self._move(-1))
        self.down_button.clicked.connect(lambda: self._move(1))
        self.delete_button.clicked.connect(self._delete)
        #: The stretch before *Delete…*, as on the profiles: the one button that cannot be undone
        #: sits away from the ones that can.
        actions = QHBoxLayout()
        for button in (self.add_button, self.duplicate_button, self.rename_button,
                       self.up_button, self.down_button):
            actions.addWidget(button)
        actions.addStretch()
        actions.addWidget(self.delete_button)

        #: The name in it is fitted to `tiling_value.NAME_ROOM` (`fitted`), and the heading is not
        #: wrapped: a wrapped label beside a stretch is given the narrowest width it can take, and
        #: broke a heading of this kind -- "Balanced, for each number of windows" -- in two (seen
        #: offscreen).
        self.slots_heading = Heading("", SLOTS_TIP)
        holder, self._slots_flow = flow_holder()
        self._slots_holder = holder
        self.slot_cards: list[LayoutCard] = []
        #: The layout for one window more: the last card of the row, whatever the row holds
        #: (`_fill`). Never greyed for a refusal of its own -- nine windows already, say -- because
        #: Qt sends no tooltip event to a dead widget (the comment in
        #: `TilingPage._follow_focus_policy`): a click says why in the box's line instead
        #: (`_add_slot_wanted`).
        self.add_card = AddCard()
        self.add_card.clicked.connect(self._add_slot_wanted)
        self._slots_flow.addWidget(self.add_card)

        self.choices_heading = Heading("", CHOICES_TIP)
        holder, self._choices_flow = flow_holder()
        self._choices_holder = holder
        self.choice_cards: list[LayoutCard] = []
        self.none_note = note()
        self.edit_button = QPushButton("Edit in Zone layouts")
        self.edit_button.setToolTip("Select the zone layout in use in the Zone layouts box below, "
                                    "where it is edited.")
        self.edit_button.clicked.connect(self._edit_it)
        self.remove_slot_button = QPushButton("Remove this layout")
        self.remove_slot_button.setToolTip("A window that opens past the last layout left then "
                                           "does what When the arrangement is full says. The zone "
                                           "layout stays under Zone layouts.")
        self.remove_slot_button.clicked.connect(self._remove_slot)
        #: Under the chooser's cards, while a layout the arrangement has is chosen. On one line: no
        #: button on it carries a name, so it never needs the width a row that wraps would give.
        choice_buttons = QHBoxLayout()
        choice_buttons.setContentsMargins(0, 0, 0, 0)
        choice_buttons.addWidget(self.edit_button)
        choice_buttons.addWidget(self.remove_slot_button)
        choice_buttons.addStretch()
        self._choice_buttons = QWidget()
        self._choice_buttons.setLayout(choice_buttons)

        #: The box's own line: why an edit was refused, or what an edit did besides itself. Shown
        #: only while it has something to say (`_tell`). Plain text, for the reason the Zone
        #: layouts box's line is (`ZoneLayoutsBox.line`): what it says names arrangements.
        self.line = note()
        self.line.setTextFormat(Qt.TextFormat.PlainText)
        self.line.setVisible(False)

        #: Everything but the title and the line that says the box is folded.
        self.body = QWidget()
        column = QVBoxLayout(self.body)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(self.table)
        column.addLayout(actions)
        column.addWidget(self.slots_heading)
        column.addWidget(self._slots_holder)
        column.addWidget(self.choices_heading)
        column.addWidget(self._choices_holder)
        column.addWidget(self.none_note)
        column.addWidget(self._choice_buttons)
        column.addWidget(self.line)
        self.off_line = note(OFF)
        self.off_line.setVisible(False)
        outer = QVBoxLayout(self)
        outer.addWidget(self.body)
        outer.addWidget(self.off_line)

        model.shown.connect(self._shown)
        self._paint_all()

    # ---------------------------------------------------------------- what the page asks

    def set_collapsed(self, collapsed: bool) -> None:
        """Folded to its title and one line, while automatic tiling is off: nothing is laid out by
        an arrangement then, and Next Layout and Previous Layout walk the zone layouts a drag
        offers instead. What is chosen stays chosen, and comes back with the switch."""
        self.body.setVisible(not collapsed)
        self.off_line.setVisible(collapsed)

    def collapsed(self) -> bool:
        return self.off_line.isVisibleTo(self)

    def _current(self) -> dict | None:
        return splits.arrangement(self.model.value, self._aid) if self.model.value else None

    # ---------------------------------------------------------------- painting

    def _shown(self, anew: bool) -> None:
        """The value to show changed, from the daemon or from an edit in either box."""
        self._ratio = screen_ratio(self)
        if anew:
            self._tell("")
        value = self.model.value
        if value and splits.arrangement(value, self._aid) is None:
            # Gone: the first one, with nothing being chosen for -- a number of windows chosen on
            # the one that went says nothing about this one.
            self._aid, self._slot = value["arrangements"][0]["id"], None
        self._paint_all()

    def _paint_all(self) -> None:
        entry = self._current()
        last = splits.last_count(entry) if entry else 0
        # Kept only while it is a number of windows the arrangement has a layout for, or the one
        # after its last on the arrangement it is being added to (`_adding`). Reached any other
        # way, the one after the last is a choice nobody asked for, one click from adding a
        # layout. Measured offscreen on KyprX's own: Delete… with Centred Three Columns' layout
        # for 5 windows chosen selected Dwindle, whose last is for 4, and left 5 chosen for it;
        # and putting KyprX's own back with a layout for 5 given to Balanced, and chosen, left 5
        # chosen, to add again what the reset had just taken away.
        adding = entry is not None and self._adding == entry["id"] \
            and self._slot == last + 1 <= splits.MAX_WINDOWS
        if self._slot is not None and not (adding or 2 <= self._slot <= last):
            self._slot = None
        if not adding:
            self._adding = None
        self._painting = True
        try:
            self._paint_table()
            self._paint_slots()
            self._paint_choices()
        finally:
            self._painting = False
        self._sync()

    def _paint_table(self) -> None:
        """The list, painted over the rows already there where it can be: a tick is answered in
        the middle of the table's own signal, and an item deleted under it there is a crash."""
        value = self.model.value
        items = value["arrangements"] if value else []
        editable = self.model.editable()
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(len(items))
            selected = -1
            for row, entry in enumerate(items):
                name = self.table.item(row, 0)
                if name is None:
                    name = QTableWidgetItem()
                    self.table.setItem(row, 0, name)
                name.setText(entry["name"])
                name.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                tick = self.table.item(row, 1)
                if tick is None:
                    tick = QTableWidgetItem()
                    self.table.setItem(row, 1, tick)
                flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable
                if editable:
                    flags |= Qt.ItemFlag.ItemIsEnabled
                tick.setFlags(flags)
                tick.setCheckState(Qt.CheckState.Checked if entry["cycle"]
                                   else Qt.CheckState.Unchecked)
                tick.setToolTip(ROTATION_TIP)
                if entry["id"] == self._aid:
                    selected = row
            if selected >= 0:
                self.table.setCurrentCell(selected, 0)
                self.table.selectRow(selected)
            else:
                self.table.clearSelection()
        finally:
            self.table.blockSignals(False)
        self.table.setEnabled(value is not None)
        height = self.table.horizontalHeader().sizeHint().height() + 2
        for row in range(self.table.rowCount()):
            height += self.table.rowHeight(row)
        self.table.setFixedHeight(height)

    @staticmethod
    def _fill(flow, cards: list[LayoutCard], count: int, chosen, ratio: float, before,
              tail: QWidget | None = None) -> None:
        """As many cards in `flow` as `count`, the ones there kept, so a card the keyboard is on
        stays the one it is on. `chosen(i)` is what clicking card `i` does. A card made goes in the
        keyboard's Tab order with the others, straight before `before`, the control drawn after
        them (`tab_before`) -- and in the row before `tail`, a card that stays the last, taken out
        and put back after the ones made."""
        while len(cards) > count:
            gone = cards.pop()
            flow.removeWidget(gone)
            gone.setParent(None)
            gone.deleteLater()
        grows = len(cards) < count
        if grows and tail is not None:
            flow.removeWidget(tail)
        while len(cards) < count:
            made = LayoutCard(ratio)
            made.clicked.connect(lambda _on=False, i=len(cards): chosen(i))
            flow.addWidget(made)
            cards.append(made)
        if grows:
            if tail is not None:
                flow.addWidget(tail)
            tab_before(cards, before)

    def _paint_slots(self) -> None:
        entry = self._current()
        value = self.model.value
        last = splits.last_count(entry) if entry else 0
        self._fill(self._slots_flow, self.slot_cards, last, lambda i: self._slot_chosen(i + 1),
                   self._ratio, self.add_card, tail=self.add_card)
        for k, card in enumerate(self.slot_cards, start=1):
            card.set_ratio(self._ratio)
            if k == 1:
                card.show_layout({}, "1 · Whole screen",
                                 tip=plain_tip("One window has the whole screen, in every "
                                               "arrangement."),
                                 accessible="The layout for 1 window: the whole screen")
                card.setChecked(False)
            else:
                held = splits.layout(value, entry["windows"][str(k)])
                card.show_layout(held["tree"], f"{k} · {held['name']}", drag=held["drag"],
                                 tip=plain_tip(f"For {windows(k)}: {held['name']}"),
                                 accessible=f"The layout for {windows(k)}: {held['name']}")
                card.setChecked(k == self._slot)
            card.setEnabled(self.model.loaded)
        # Ringed while the layout it adds is the one being chosen for, as a layout's card is.
        self.add_card.set_ratio(self._ratio)
        self.add_card.set_count(last + 1)
        self.add_card.setChecked(entry is not None and self._slot == last + 1)
        self.add_card.setVisible(entry is not None)
        self._slots_holder.updateGeometry()
        self.slots_heading.set_text(
            f"{fitted(self.slots_heading.label, entry['name'])}, by number of windows"
            if entry else "")
        self.slots_heading.setVisible(entry is not None)

    def _paint_choices(self) -> None:
        """The zone layouts the number of windows being chosen for can have, the one in use
        ringed; nothing, while no number is being chosen for."""
        entry = self._current()
        k = self._slot
        value = self.model.value
        offered = splits.choices(value, k) if entry is not None and k is not None else []
        in_use = entry["windows"].get(str(k)) if entry is not None and k is not None else None
        self._fill(self._choices_flow, self.choice_cards, len(offered), self._choice_chosen,
                   self._ratio, self.edit_button)
        for card, held in zip(self.choice_cards, offered):
            here = held["id"] == in_use
            card.set_ratio(self._ratio)
            card.show_layout(held["tree"], held["name"], drag=held["drag"],
                             tip=plain_tip(f"{held['name']}: the layout for {windows(k)} now."
                                           if here else
                                           f"Use {held['name']} for {windows(k)}."),
                             accessible=f"{held['name']}, {k} zones")
            card.setChecked(here)
            card.setEnabled(self.model.editable())
        self._choices_holder.updateGeometry()
        choosing = k is not None
        self.choices_heading.set_text(f"Layout for {windows(k)}" if choosing else "")
        self.choices_heading.setVisible(choosing)
        self._choices_holder.setVisible(bool(offered))
        # Where to make one, and nothing here that makes one: the zone layouts are made, copied
        # and cut down under Zone layouts alone.
        self.none_note.setText(f"No zone layout has {k} zones yet. Make one under Zone layouts."
                               if choosing else "")
        self.none_note.setVisible(choosing and not offered)
        last = splits.last_count(entry) if entry is not None else 0
        self.edit_button.setVisible(in_use is not None)
        # On the last layout alone, which is the one it takes away: a layout in the middle of the
        # row cannot go without every one after it.
        self.remove_slot_button.setVisible(in_use is not None and k == last >= 2)
        self._choice_buttons.setVisible(in_use is not None)

    def _sync(self) -> None:
        """Every button says what can be done now, and a greyed one says why not."""
        value = self.model.value
        entry = self._current()
        editable = self.model.editable() and entry is not None
        items = value["arrangements"] if value else []
        row = splits.index_of(value, self._aid) if value else -1
        self.add_button.setEnabled(self.model.editable())
        for button in (self.duplicate_button, self.rename_button):
            button.setEnabled(editable)
        self.up_button.setEnabled(editable and row > 0)
        self.down_button.setEnabled(editable and 0 <= row < len(items) - 1)
        why = splits.delete_problem(value, self._aid) if editable else ""
        self.delete_button.setEnabled(editable and not why)
        self.delete_button.setToolTip(why or "Forget the selected arrangement. The zone layouts "
                                             "it uses stay under Zone layouts.")

        # Greyed only while nothing in the box can be changed, as every button is then; a
        # refusal of its own is in its tooltip, and in the line once it is clicked.
        why = splits.add_slot_problem(value, self._aid) if editable else ""
        last = splits.last_count(entry) if entry else 0
        self.add_card.setEnabled(editable)
        self.add_card.setToolTip(
            why or (f"Add the layout for {windows(last + 1)}: one of your zone layouts with "
                    f"{last + 1} zones." if entry else ""))
        self.remove_slot_button.setEnabled(editable and last > 1)

        k = self._slot
        in_use = entry["windows"].get(str(k)) if entry is not None and k is not None else None
        self.edit_button.setEnabled(self.model.loaded and in_use is not None)

    # ---------------------------------------------------------------- choosing

    def _table_selected(self) -> None:
        value = self.model.value
        if self._painting or not value:
            return
        row = self.table.currentRow()
        items = value["arrangements"]
        if 0 <= row < len(items) and items[row]["id"] != self._aid:
            # The same number of windows stays chosen where the arrangement has a layout for it.
            # The one after its last is chosen only by the card that adds it, on the arrangement
            # it was clicked on: a choice of it would add a layout to this one, so the paint drops
            # it (`_paint_all`).
            self._aid = items[row]["id"]
            self._paint_all()

    def _slot_chosen(self, k: int) -> None:
        """A layout card clicked: the zone layouts it can be are shown under the cards. One window
        has the whole screen, which is no choice, and the line says so."""
        if self._painting:
            return
        if k == 1:
            self._slot = None
            self._tell("One window always has the whole screen.")
        else:
            self._slot = k
        self._paint_all()

    def _add_slot_wanted(self) -> None:
        """The card that adds the layout for N windows: the zone layouts with N zones, to choose
        one from -- or, refused, why not, in the line, and the card is not left ringed by the
        click that toggled it."""
        entry = self._current()
        if entry is None or not self.model.editable():
            return
        why = splits.add_slot_problem(self.model.value, entry["id"])
        if why:
            self._refuse(why)
            return
        self._slot, self._adding = splits.last_count(entry) + 1, entry["id"]
        self._paint_all()

    def _choice_chosen(self, i: int) -> None:
        """A zone layout chosen for the number of windows being chosen for: in place of the one
        there, or as the layout for one window more than the last."""
        entry, k = self._current(), self._slot
        if self._painting or entry is None or k is None or not self.model.editable():
            return
        offered = splits.choices(self.model.value, k)
        if not 0 <= i < len(offered):
            return
        chosen = offered[i]["id"]
        try:
            if k <= splits.last_count(entry):
                if entry["windows"][str(k)] == chosen:
                    self._paint_all()            # the one in use already: its ring comes back
                    return
                value = splits.set_slot(self.model.value, entry["id"], k, chosen)
            else:
                value = splits.add_slot(self.model.value, entry["id"], chosen)
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._commit(value)

    def _edit_it(self) -> None:
        """*Edit in Zone layouts*: the zone layout in use, selected in that box and scrolled to."""
        entry, k = self._current(), self._slot
        held = entry["windows"].get(str(k)) if entry is not None and k is not None else None
        if held:
            self.show_layout.emit(held)

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

    def _rotation_ticked(self, item: QTableWidgetItem) -> None:
        value = self.model.value
        if self._painting or item.column() != 1 or not self.model.editable():
            return
        items = value["arrangements"]
        if not 0 <= item.row() < len(items):
            return
        entry = items[item.row()]
        on = item.checkState() == Qt.CheckState.Checked
        if on == entry["cycle"]:
            return
        try:
            changed = splits.set_cycle(value, entry["id"], on)
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._commit(changed)

    def _remove_slot(self) -> None:
        """*Remove this layout*: the last one, while it is the one chosen -- which is when the
        button is shown, so a click that outlived it does nothing."""
        entry = self._current()
        if entry is None or not self.model.editable() \
                or not self._slot == splits.last_count(entry) >= 2:
            return
        try:
            value = splits.remove_last_slot(self.model.value, entry["id"])
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        # The layout taken away, when it was the one being chosen for, goes on being chosen for:
        # one more than the last now, to choose another for it on this arrangement.
        self._adding = entry["id"]
        self._commit(value)

    # ---------------------------------------------------------------- the list

    def _add(self) -> None:
        name = self.model.ask_name(self, "Add an arrangement", "A name for it:")
        if name is None or not self.model.editable():
            return
        try:
            value, ident = splits.add(self.model.value, name)
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._aid, self._slot = ident, None
        self._commit(value)

    def _duplicate(self) -> None:
        entry = self._current()
        if entry is None or not self.model.editable():
            return
        try:
            value, ident = splits.duplicate(self.model.value, entry["id"])
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._aid = ident
        self._commit(value, f"{splits.arrangement(value, ident)['name']} uses the same zone "
                            f"layouts as {entry['name']}.")

    def _rename(self) -> None:
        entry = self._current()
        if entry is None or not self.model.editable():
            return
        ident = entry["id"]
        name = self.model.ask_name(self, "Rename this arrangement", "A new name for it:",
                                   entry["name"])
        if name is None or not self.model.editable():
            return
        # The question let the page's paint in, if one was owed: the arrangement it named may
        # have been renamed or taken off the desk meanwhile.
        entry = splits.arrangement(self.model.value, ident)
        if entry is None or name.strip() == entry["name"]:
            return
        try:
            value = splits.rename(self.model.value, ident, name)
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._commit(value)

    def _move(self, step: int) -> None:
        if self._current() is None or not self.model.editable():
            return
        try:
            value = splits.move(self.model.value, self._aid, step)
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._commit(value)

    def _delete(self) -> None:
        entry = self._current()
        if entry is None or not self.model.editable():
            return
        ident = entry["id"]
        why = splits.delete_problem(self.model.value, ident)
        if why:
            self._tell(why)
            return
        if self.model.sure(self, "Delete this arrangement?",
                           f"Delete {entry['name']}? The zone layouts it uses stay under Zone "
                           f"layouts, and there is no way back."):
            return
        if not self.model.editable() or splits.arrangement(self.model.value, ident) is None:
            return
        row = splits.index_of(self.model.value, ident)
        try:
            value = splits.delete(self.model.value, ident)
        except splits.ArrangementsError as e:
            self._refuse(e)
            return
        self._aid = value["arrangements"][min(row, len(value["arrangements"]) - 1)]["id"]
        self._commit(value)
