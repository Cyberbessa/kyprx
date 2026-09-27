"""The Tiling tab: the layout rotation, how tiling behaves, and the focus settings that go with it.

A page of `gui/fields.py`'s `TILING_FIELDS` in the form engine, with what the fields cannot say on
their own: the gaps as one grid, which layouts the rotation walks and in what order, settings that
do nothing while their switch is off, and the focus policies the desktop discourages under a tiler.
It has no on/off control -- tiling is what KyprX is for -- and any change here puts the tiling
script back on if something had switched it off.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout,
                               QWidget)

from fields import FOCUS_DELAY_NOTE, FOCUS_DISCOURAGED, FOCUS_STEALING_NOTE, TILING_FIELDS
from form import SettingsPage
from widgets import SECTION_HINTS, Section, Spin, unavailable, warning


#: The band's two sentences. Off is a switch away from on; not installed is not, and the button
#: that switches tiling back on would switch on nothing, so it goes while that is the case.
TILING_OFF = "Tiling is switched off, so nothing on this tab is doing anything."
TILING_MISSING = "Nothing on this tab does anything until it is. The Settings tab says what to do."


class TilingPage(SettingsPage):
    """Tiling: the layout rotation, how it behaves, and the focus settings that go with it.

    There is no on/off control any more, and that is the point of this app rather than an omission:
    KyprX exists to put a tiling desktop on KDE, so "tiling off" is not one of its states. Applying
    anything here switches the tiling script back on if something had switched it off — see the
    `tiling` entry in `daemon/defaults.py`. Turning it off for good is done in the desktop's own
    settings, and the next change here will undo that.
    """

    enforces = "tiling"

    #: A switch and the setting that does nothing while it is off. Greyed rather than hidden, and
    #: the widget rather than the label -- the label's grey means something else here.
    FOLLOWS = ((("tiling", "", "limitTileWidth"), ("tiling", "", "limitTileWidthRatio")),
               (("tiling", "", "adjustLayout"), ("tiling", "", "adjustLayoutLive")))

    def __init__(self, client, parent=None):
        super().__init__(TILING_FIELDS, client, parent)
        self.layout_boxes: dict[str, QSpinBox] = {}
        self._layouts_at_load: dict[str, str] = {}

        layouts = Section("Layouts", SECTION_HINTS["Layouts"] + " Nought takes one out.")
        column = QVBoxLayout(layouts)
        #: Two columns of six rather than twelve rows of one number, which took the whole of the
        #: first screen of this tab on a window of the size it opens at.
        form = QGridLayout()
        form.setColumnStretch(4, 1)
        form.setHorizontalSpacing(12)
        column.addLayout(form)
        self._layouts_form = form
        self._layout_names: dict[str, str] = {}
        #: Where each layout sits in the tiler's own list, which is what it falls back on when two
        #: share a number. The boxes are not in that order any more -- KyprX's three come first --
        #: so their order cannot stand in for it.
        self._layout_rank: dict[str, int] = {}
        #: What the numbers add up to, read off the boxes rather than off the file, so it cannot
        #: describe a cycle nobody has. It is what makes a column of numbers mean something
        #: without a sentence of instructions above it.
        self.cycle = QLabel()
        self.cycle.setWordWrap(True)
        column.addWidget(self.cycle)
        #: Under Focus rather than above it. Focus is first on this tab because it is the one thing
        #: here that decides how the desktop *feels* rather than how it is arranged -- the owner
        #: asked for it there -- and the layouts come next, which is the order the two are used in.
        self.after("Focus", layouts)

        #: The band and the way out of it, together. Until now the way out was *Apply*, which is
        #: why the band said so; with every change applying by itself there is no click to name,
        #: so the one thing that switches tiling back on without changing anything else is a
        #: button of its own. It sends what an Apply with nothing changed used to send.
        self.banner = warning(TILING_OFF)
        self.banner.setVisible(False)
        self.switch_on = QPushButton("Switch tiling back on")
        self.switch_on.setToolTip("Puts the tiling script back on and changes nothing else.")
        self.switch_on.clicked.connect(self._switch_on)
        band = QHBoxLayout()
        band.setContentsMargins(0, 0, 0, 0)
        band.addWidget(self.banner, 1)
        band.addWidget(self.switch_on)
        self.band = QWidget()
        self.band.setLayout(band)
        self.band.setVisible(False)
        #: Above the scroll area and not inside it: "nothing on this tab is doing anything" is not
        #: a thing to find by scrolling back up to it.
        self.layout().insertWidget(0, self.band)

        self._gaps_grid()
        for switch, _dependent in self.FOLLOWS:
            self.widgets[switch].toggled.connect(self._follow_switches)
        self._follow_switches()

        self.focus_policy = self.widgets[("windows", "", "FocusPolicy")]
        self.focus_policy.currentIndexChanged.connect(self._follow_focus_policy)
        self._follow_focus_policy()

    def _follow_focus_policy(self) -> None:
        """Grey out what the compositor is going to ignore anyway.

        Measured in the compositor's own source: under a click-to-focus policy it zeroes the focus
        delay, and under either under-mouse policy it forces focus stealing prevention to None.
        A control left enabled there would show a number that has already been thrown away — the
        interface would be stating something untrue, which is worse than offering nothing.
        """
        policy = self.focus_policy.currentData()
        for ident, applies, why in (
                (("windows", "", "DelayFocusInterval"), policy not in ("click", "click-mouse"),
                 FOCUS_DELAY_NOTE),
                (("windows", "", "FocusStealingPreventionLevel"),
                 policy not in FOCUS_DISCOURAGED, FOCUS_STEALING_NOTE)):
            # The widget and not the label. A greyed label in this window means "nothing tells
            # this app what applies here", which is a different fact and is drawn by `_paint`.
            # The reason goes on the label, because Qt sends no tooltip event to a dead widget.
            self.widgets[ident].setEnabled(applies)
            self.labels[ident].setToolTip(self.fields[ident].hint if applies else why)

    def _load(self, data: dict) -> None:
        super()._load(data)
        self._warn_on_discouraged()
        self._follow_focus_policy()
        self._follow_switches()
        off = not (data.get("plugins") or {}).get("krohnkite", False)
        missing = unavailable(data, "krohnkite")
        self.banner.setText(f"{missing} {TILING_MISSING}" if missing else TILING_OFF)
        self.switch_on.setVisible(not missing)
        self.band.setVisible(off or bool(missing))
        self.banner.setVisible(off or bool(missing))
        tiling = data.get("tiling") or {}
        defaults = data.get("tiling_defaults") or {}
        for key, label in data.get("layouts") or []:
            self._layout_names[key] = label
            # The tiler's defaults count 1 to 12 along its own list, so they are that list's order.
            try:
                self._layout_rank[key] = int(defaults.get(key, 99))
            except (TypeError, ValueError):
                self._layout_rank[key] = 99
            if key not in self.layout_boxes:
                spin = Spin()
                spin.setRange(0, 20)
                spin.setMinimumWidth(64)
                spin.setMaximumWidth(140)
                spin.valueChanged.connect(self._say_cycle)
                spin.valueChanged.connect(self.queue)
                at = len(self.layout_boxes)
                self.layout_boxes[key] = spin
                self._layouts_form.addWidget(QLabel(label), at // 2, (at % 2) * 2)
                self._layouts_form.addWidget(spin, at // 2, (at % 2) * 2 + 1)
            raw = str(tiling.get(key, defaults.get(key, "0")))
            spin = self.layout_boxes[key]
            spin.setValue(int(float(raw or 0)))
            # Record what the widget makes of it, not what the file said. The two differ whenever
            # the box renormalises: an empty value becomes 0, anything above 20 is clamped to 20,
            # `04` becomes `4`. Comparing the file's spelling against the widget's would report a
            # change nobody made — and this one does not merely write a stray key, it takes a
            # layout out of the rotation and restarts the tiler to do it.
            self._layouts_at_load[key] = str(spin.value())
        self._say_cycle()

    def _follow_switches(self, *_) -> None:
        for switch, dependent in self.FOLLOWS:
            self.widgets[dependent].setEnabled(self.widgets[switch].isChecked())

    def _gaps_grid(self) -> None:
        """The four screen edges side by side, instead of five rows of one number each.

        The **same** label widgets are moved, not new ones: `_paint` writes the dot and the enabled
        state into the ones it built, and a copy would leave those saying nothing.
        """
        form = self.section_forms["Gaps"]
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        places = (("screenGapTop", 0, 0), ("screenGapBottom", 0, 2),
                  ("screenGapLeft", 1, 0), ("screenGapRight", 1, 2),
                  ("screenGapBetween", 2, 0))
        grid.setHorizontalSpacing(12)
        for key, row, column in places:
            ident = ("tiling", "", key)
            at, _role = form.getWidgetPosition(self.widgets[ident])
            if at >= 0:
                form.takeRow(at)
            grid.addWidget(self.rows[ident], row, column)
            grid.addWidget(self.widgets[ident], row, column + 1)
        grid.setColumnStretch(4, 1)
        form.addRow(grid)

    def _switch_on(self) -> None:
        """Put the tiling script back on, and write nothing else.

        The same call the page makes when something on it changes -- `enforce` names what this
        page is responsible for, and for tiling that is the one switch. The values come from
        `daemon/defaults.py` and never from here: a setting with no control has nothing to read a
        value back from.
        """
        self.says.emit("Switching tiling back on…")
        self.c.set_groups({"enforce": [self.enforces]})
        QTimer.singleShot(400, lambda: self.load(self.c.groups()))

    def _say_cycle(self, *_) -> None:
        """The cycle these numbers make, in the order the key would walk it.

        Read off the boxes and not off the file, so it describes what is on screen even while a
        change of somebody's is still settling. Two layouts sharing a number are listed in the
        tiler's own list order, which is how it sorts them: a stable sort over that list.
        """
        ordered = sorted(((b.value(), self._layout_rank.get(k, 99), self._layout_names.get(k, k))
                          for k, b in self.layout_boxes.items() if b.value() > 0),
                         key=lambda entry: entry[:2])
        names = ", ".join(name for _, _, name in ordered)
        self.cycle.setText(f"The key cycles: {names}." if names
                           else "No layout is in the cycle, so the key does nothing.")

    def _warn_on_discouraged(self) -> None:
        """The desktop warns about two of these policies. Carry the warning rather than hide it."""
        for i in range(self.focus_policy.count()):
            if self.focus_policy.itemData(i) in FOCUS_DISCOURAGED:
                self.focus_policy.setItemData(
                    i,
                    "The desktop warns against this one: it breaks the window switcher, and a "
                    "tiling script that navigates by keyboard goes with it.",
                    Qt.ItemDataRole.ToolTipRole)

    def extra_changes(self) -> dict:
        moved = {k: str(b.value()) for k, b in self.layout_boxes.items()
                 if str(b.value()) != self._layouts_at_load.get(k)}
        return {"tiling": moved} if moved else {}
