"""The Tiling tab: how KyprX's own tiler lays windows out, and the focus settings that go with it.

A page of `gui/fields.py`'s `TILING_FIELDS` in the form engine, each setting with its sentence on a
mark after its name, and with what the fields cannot say on their own: the zone layouts and the
arrangements -- one value of the tiler's (`gui/tiling_value.py`), which two boxes edit, the
Arrangements box (`gui/arrangements_box.py`), folded away while automatic tiling is off, and the
Zone layouts box (`gui/zone_layouts_box.py`) -- the arrangement each desktop starts on
(`gui/desktops_box.py`), folded away with the Arrangements box, the gaps as one grid, settings that do nothing
while their switch is off or while a menu is on an answer that does not use them, the focus
policies the desktop discourages under a tiler, and the band that says when what is set here is
not in force, or not all of it, and why -- which the daemon decides, in `tiling_state`. It has no
on/off control -- tiling is what KyprX is for -- and any change here puts tiling back on if
something had switched it off.
"""

from __future__ import annotations

import html

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QPushButton, QScrollArea, QWidget

from arrangements_box import ArrangementsBox
from desktops_box import DesktopsBox
from fields import FOCUS_DELAY_NOTE, FOCUS_DISCOURAGED, FOCUS_STEALING_NOTE, TILING_FIELDS
from form import SettingsPage
from tiling_value import TilingValue
from widgets import warning
from zone_layouts_box import ZoneLayoutsBox


#: The band's sentences, by the daemon's `tiling_state`. Each says why what is on the tab is not in
#: force -- nothing of it, or under a part of the compositor from before an update, what is new --
#: and where the way out is; only a switch that is off has its way out on this tab, the button
#: beside the band. A state the daemon does not send -- an older daemon -- shows no band: this
#: window cannot tell then, and a band that guessed would be the tab saying something untrue.
TILING_OFF = "Tiling is switched off, so nothing on this tab is doing anything."
TILING_OFF_DESK = ("KyprX is off this desk, so its tiling waits and nothing on this tab is doing "
                   "anything. Put my setup back, at the top of the window, brings it back.")
#: The compositor keeps what it compiled of a script for the whole session and never reads the
#: files again before the next login (`docs/modules/kwin-script.md` has the finding), so a newer
#: KyprX's part of the compositor is not the one running until then. Two states say so, and each
#: band says what that login does and no more.
#:
#: "no-script": no part of the compositor has asked for the tiling since the daemon started -- a
#: part from before KyprX tiled never asks -- so nothing tiles.
TILING_NO_SCRIPT = ("KyprX's part of the compositor is not the one that tiles yet, so nothing on "
                    "this tab is doing anything. Log out and back in to start it.")
#: "old-script": a part of another version asked, and it goes on tiling with what it knows: the
#: answer it reads only ever gains fields, so the settings it had act at once, and what is new waits
#: for the part installed, which only that login starts.
TILING_OLD_SCRIPT = ("KyprX's part of the compositor is from before the update, so what is new on "
                     "this tab starts at the next login; until then the desktop tiles as it did. "
                     "Log out and back in to start it.")
BANDS = {"off": TILING_OFF, "off-desk": TILING_OFF_DESK, "no-script": TILING_NO_SCRIPT,
         "old-script": TILING_OLD_SCRIPT}

AUTO = ("tiling", "", "autoTiling")
#: What a window that finds every zone taken does, and where the desktop it then goes to is made.
OVERFLOW = ("tiling", "", "newWindowOverflow")
NEW_DESKTOP = ("tiling", "", "newDesktopPosition")


def _in_tab_order(part: QWidget) -> list[QWidget]:
    """The controls in `part` that take the focus, in the keyboard's Tab order -- read while the
    page is built, when what a part holds comes straight after it in that order. A control that
    hands its focus on to the one it belongs to, as a spin box's line does, is left out: it goes
    where that one goes.

    The focus proxy is asked only of a control that takes the focus at all, and after that is
    known: asked of a table header's viewport, whose proxy is the header, it leaves the two
    wrappers holding each other in PySide's records, and the collector then frees the header
    under its table. Measured offscreen with PySide 6.11: this walk over the Tiling page, the
    proxy asked first, had the next collection destroy the Arrangements table's header, and the
    page crashed at its next paint; asked in this order, nothing was destroyed (`Keyboard.stops`
    in tests/test_tiling_tab.py has why)."""
    found = []
    control = part.nextInFocusChain()
    while part.isAncestorOf(control):
        if control.focusPolicy() != Qt.FocusPolicy.NoFocus and control.focusProxy() is None:
            found.append(control)
        control = control.nextInFocusChain()
    return found


class TilingPage(SettingsPage):
    """Tiling: the zone layouts and the arrangements, how they behave, and the focus settings that
    go with it.

    There is no on/off control any more, and that is the point of this app rather than an omission:
    KyprX exists to put a tiling desktop on KDE, so "tiling off" is not one of its states. Applying
    anything here switches tiling back on if something had switched it off — see the `tiling`
    entry in `daemon/defaults.py`.

    **The zone layouts and arrangements have a refusal of their own, and the page keeps it.** While
    a question or a menu of either box is open, or a mouse button is down on the builder, the page
    does not repaint -- repainting inside a question's own event loop pulls the value out from
    under the answer -- and a repaint refused for that is owed, and paid the moment the value is
    idle (`TilingValue.busy`). Refused and forgotten, a change that arrived meanwhile would leave the
    boxes comparing against what the file held before it: putting a value back would then look like
    no change, and be sent nowhere.

    **Every setting carries its sentence on a mark after its name** (`marks`), and not on the
    name's tooltip alone: the owner asked for the marks on this tab.
    """

    enforces = "tiling"

    #: A switch and the settings that do nothing while it is off. Greyed rather than hidden, and
    #: the widget rather than the label -- the label's grey means something else here. With
    #: automatic tiling off nothing is tiled, so none of these has anything to act on: no window
    #: goes anywhere in a layout, no arrangement is ever full, no tiled edge is dragged. The names
    #: on screen follow no switch, and nor do the zone layouts, which a drag offers in both modes.
    #: The Arrangements box folds away with the switch instead (`_follow_switches`).
    FOLLOWS = ((AUTO, ("tiling", "", "adjustLayoutLive")),
               (AUTO, ("tiling", "", "newWindowPosition")),
               (AUTO, OVERFLOW),
               (AUTO, NEW_DESKTOP),
               (AUTO, ("tiling", "", "floatUtility")))

    #: A menu, the answers on which a setting does something, and that setting: greyed the way
    #: `FOLLOWS` greys, on any other answer. Where a new desktop goes matters only while a window
    #: that finds every zone taken is given a new desktop. A setting in both tables is live only
    #: while both allow it.
    FOLLOWS_ANSWER = ((OVERFLOW, ("0",), NEW_DESKTOP),)

    def __init__(self, client, parent=None):
        super().__init__(TILING_FIELDS, client, parent, marks=True)
        #: A repaint refused while the zone layouts and arrangements were busy, to be made when
        #: they are not.
        self._owed = False
        #: The one value both boxes edit, painted once per answer (`_load`). Its edits start the
        #: clock as a field's do; putting KyprX's own back is sent at once, before an edit made in
        #: the next moment can take its place (`TilingValue.put_back` says why).
        self.tiling_value = TilingValue(self)
        self.tiling_value.changed.connect(self.queue)
        self.tiling_value.send_now.connect(self.flush)
        self.tiling_value.idle.connect(self._pay_owed)
        #: Under the switch that says whether windows are laid out at all, and above the gaps: the
        #: arrangements are what is laid out, the zone layouts what they are made of and what a
        #: drag offers, and the gaps are the space around it.
        self.arrangements = ArrangementsBox(self.tiling_value)
        self.zone_layouts = ZoneLayoutsBox(self.tiling_value)
        #: Under the arrangements, which it chooses among, and above the zone layouts they are made
        #: of. Its choice is a key of its own, sent with the page's other changes.
        self.desktops = DesktopsBox(self.tiling_value)
        self.desktops.changed.connect(self.queue)
        self.arrangements.show_layout.connect(self._show_layout)
        self.after("Automatic tiling", self.arrangements)
        self.column.insertWidget(self.column.indexOf(self.arrangements) + 1, self.desktops)
        self.column.insertWidget(self.column.indexOf(self.desktops) + 1, self.zone_layouts)
        self._area = self.findChild(QScrollArea)

        #: The band and the way out of it, together. With every change applying by itself there is
        #: no click to name, so the one thing that switches tiling back on without changing anything
        #: else is a button of its own -- shown only for the one state it can do anything about.
        self.banner = warning(TILING_OFF)
        self.banner.setVisible(False)
        self.switch_on = QPushButton("Switch tiling back on")
        self.switch_on.setToolTip("Puts KyprX's tiling back on and changes nothing else.")
        self.switch_on.clicked.connect(self._switch_on)
        band = QHBoxLayout()
        band.setContentsMargins(0, 0, 0, 0)
        band.addWidget(self.banner, 1)
        band.addWidget(self.switch_on)
        self.band = QWidget()
        self.band.setLayout(band)
        self.band.setVisible(False)
        #: Above the scroll area and not inside it: "nothing on this tab is doing anything", or
        #: "what is new on this tab starts at the next login", is not a thing to find by scrolling
        #: back up to it.
        self.layout().insertWidget(0, self.band)

        self._gaps_grid()
        self._tab_down()
        for switch in dict.fromkeys(switch for switch, _dependent in self.FOLLOWS):
            self.widgets[switch].toggled.connect(self._follow_switches)
        for menu in dict.fromkeys(menu for menu, _answers, _dependent in self.FOLLOWS_ANSWER):
            self.widgets[menu].currentIndexChanged.connect(self._follow_switches)
        self._follow_switches()

        self.focus_policy = self.widgets[("windows", "", "FocusPolicy")]
        self.focus_policy.currentIndexChanged.connect(self._follow_focus_policy)
        self._follow_focus_policy()

    def load(self, data: dict) -> None:
        """Repaint, unless the zone layouts and arrangements are busy -- then the repaint is
        owed."""
        if self.tiling_value.busy():
            self._owed = True
            return
        self._owed = False
        super().load(data)

    def let_go_of_auto(self, _on: bool = False) -> None:
        """The strip above the tabs just wrote *Automatic tiling*: an edit of this page's own box
        still waiting would land after it and undo it, so it is dropped. The box is painted from
        the daemon at the next settle (`follow`)."""
        self.touched.discard(AUTO)

    def follow(self, data: dict) -> None:
        """*Automatic tiling* repainted from the daemon, alone, when somebody else wrote it -- the
        strip above the tabs, or Toggle Automatic Tiling -- and what greys and folds with it. A
        box somebody is changing here is left as it is (`refresh`)."""
        if self.tiling_value.busy():
            return
        self.refresh(data, [AUTO])
        self._follow_switches()

    def _tab_down(self) -> None:
        """The keyboard's Tab order, down the page as it is drawn: each section and box of the
        column in turn, each in the order of its own controls.

        Qt puts a widget at the end of its window's Tab order when it is given a parent, and the
        form gives every section its own before this page gives the two boxes theirs, between
        Automatic tiling and Gaps on screen: measured offscreen, Tab went from Ignored screens, at
        the foot of the page, up to the Zone layouts box, and then further up to the Arrangements
        box. Within a part the order is the one its controls were given their parent in, which is
        theirs on screen. The cards a box makes as it paints come later, and the box puts them in
        their place itself (`tab_before`)."""
        parts = [self.column.itemAt(i).widget() for i in range(self.column.count())]
        stops = [control for part in parts if part is not None
                 for control in _in_tab_order(part)]
        for first, second in zip(stops, stops[1:]):
            QWidget.setTabOrder(first, second)

    def _pay_owed(self) -> None:
        """Nothing of either box is open: the repaint refused meanwhile, from a fresh answer."""
        if self._owed and not self.tiling_value.busy():
            self._owed = False
            self.load(self.c.groups())

    def _show_layout(self, ident: str) -> None:
        """A zone layout the Arrangements box names -- *Edit in Zone layouts* -- selected in the
        Zone layouts box and scrolled to: the builder first, then the card, so that the card is in
        sight whatever happens, and the builder with it when the two fit at once."""
        if not self.zone_layouts.select(ident) or self._area is None:
            return
        self._area.ensureWidgetVisible(self.zone_layouts.builder, 0, 16)
        card = self.zone_layouts.card_for(ident)
        if card is not None:
            self._area.ensureWidgetVisible(card, 0, 16)

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
            # The reason goes on the label and its mark, because Qt sends no tooltip event to a
            # dead widget.
            self.widgets[ident].setEnabled(applies)
            self.rows[ident].set_hint(self.fields[ident].hint if applies else why)

    def _load(self, data: dict) -> None:
        super()._load(data)
        self._warn_on_discouraged()
        self._follow_focus_policy()
        self.tiling_value.load(data)
        # The desktops are asked of the compositor here, on this tab alone (`Desktops` in the
        # daemon), and not carried in `Groups`, which every tab reads.
        self.desktops.load(data, self.c.desktops())
        self._follow_switches()
        state = str(data.get("tiling_state") or "")
        text = BANDS.get(state, "")
        self.banner.setText(text)
        self.banner.setVisible(bool(text))
        self.switch_on.setVisible(state == "off")
        self.band.setVisible(bool(text))

    def _follow_switches(self, *_) -> None:
        """Grey every setting that does nothing as things stand: one whose switch is off
        (`FOLLOWS`), or whose menu is on an answer that does not use it (`FOLLOWS_ANSWER`). And
        fold the Arrangements box away while automatic tiling is off: nothing is laid out by an
        arrangement then, and the layout keys walk the zone layouts a drag offers instead.

        Worked out whole each time, from every switch and menu at once, and not one pair at a
        time: where a new desktop goes follows both the switch and the menu, and a pair on its
        own would ungrey it when either came back while the other still says no.
        """
        live: dict = {}
        for switch, dependent in self.FOLLOWS:
            live[dependent] = live.get(dependent, True) and self.widgets[switch].isChecked()
        for menu, answers, dependent in self.FOLLOWS_ANSWER:
            live[dependent] = (live.get(dependent, True)
                               and self.widgets[menu].currentData() in answers)
        for dependent, on in live.items():
            self.widgets[dependent].setEnabled(on)
        self.arrangements.set_collapsed(not self.widgets[AUTO].isChecked())
        self.desktops.set_collapsed(not self.widgets[AUTO].isChecked())

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
        """Put tiling back on, and write nothing else.

        The same call the page makes when something on it changes -- `enforce` names what this
        page is responsible for, and for tiling that is the one switch. The values come from
        `daemon/defaults.py` and never from here: a setting with no control has nothing to read a
        value back from.
        """
        self.says.emit("Switching tiling back on…")
        self.c.set_groups({"enforce": [self.enforces]})
        QTimer.singleShot(400, lambda: self.load(self.c.groups()))

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
        """The zone layouts and arrangements, and the arrangement each desktop starts on, when
        they changed: each against the daemon's reading, in one `tiling` group."""
        tiling = {**(self.tiling_value.extra_changes().get("tiling") or {}),
                  **(self.desktops.extra_changes().get("tiling") or {})}
        return {"tiling": tiling} if tiling else {}

    def _sent(self, payload: dict) -> None:
        """What was sent of the zone layouts and arrangements is what they compare with from now
        on, and so is the choice of each desktop's."""
        self.tiling_value.sent(payload.get("tiling") or {})
        self.desktops.sent(payload.get("tiling") or {})

    def _said(self) -> str:
        """The fields' words and the boxes', in that order, for the window's line -- as rich text
        with every character escaped, because the line shows what it is given as rich text
        whenever it looks like it (`Qt::mightBeRichText`), and the boxes' words carry names.
        Measured offscreen on a label like the line: `<b>Work</b> & Co` given as it is is drawn
        62 px wide, its tags taken for markup, where it takes 106 as plain text -- and 106 escaped
        this way. The line's own words -- *Dry run* -- are rich text already."""
        words = ", ".join(words for words in (super()._said(), self.tiling_value.said(),
                                              self.desktops.said()) if words)
        return f"<span>{html.escape(words, quote=False)}</span>" if words else ""
