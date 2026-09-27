"""The Appearance tab: what a window looks like, the desktop's colours, and the looks kept under a
name.

`AppearancePage` is a page of the form engine for the window's frame and outline -- it owns the
corner radius for the whole app, writing the blur's to match -- with the boxes that are not keys
built into it: `TransparencyRow`, the one strength every see-through window without a number of its
own shares; the Colours box (`gui/colours_box.py`); the Profiles box (`gui/profiles_box.py`); and
the title bar's line and door (`gui/decoration.py`). The main window reaches several of those by
name -- `colours`, `profiles`, `transparency`, `title_bar` -- so the names are part of this page's
face.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QWidget

from client import Client
from colours_box import ThemeBox
from decoration import TitleBarBox
from fields import APPEARANCE_FIELDS, OUTLINE_ACCENT_STYLES, OUTLINE_CUSTOM_STYLES
from form import SettingsPage
from profiles_box import ProfilesBox
from widgets import FieldLabel, Spin, unavailable, warning


# ---------------------------------------------------------------------- transparency

class TransparencyRow(QWidget):
    """One number for every see-through window without one of its own, and the write that
    reaches them all.

    Its own read and its own write, unlike everything beside it, because this is a setting of this
    app's rather than a key in the decoration's file: the form engine writes groups, and this goes
    through `SetSettings`. Debounced for the same reason as everything else here: the daemon
    writes it to one rule per see-through window and every write ends in a compositor reconfigure,
    so dragging the number from 92 to 80 has to be one write and not twelve.

    **A row rather than a box.** How see-through a window is belongs with the corner it is rounded
    at and the ring drawn round it -- the three things that decide what a window looks like -- and
    those are one section now. It was a box of its own when it arrived, and before that it sat
    above the Windows table, where it read as a property of the rows.
    """

    #: What the window's footer should say while this is going in.
    says = Signal(str)

    def __init__(self, client: Client, parent=None):
        super().__init__(parent)
        self.c = client
        self._loading = False
        self._pending = QTimer(self)
        self._pending.setSingleShot(True)
        self._pending.setInterval(500)
        self._pending.timeout.connect(self._write)

        self.strength = Spin()
        self.strength.setRange(1, 100)
        self.strength.setSuffix(" %")
        self.strength.setMaximumWidth(90)
        self.strength.setToolTip("How solid a see-through window is, 100 % being opaque. It "
                                 "reaches every window whose Transparency is ticked on the "
                                 "Windows tab and that has no opacity of its own there, and no "
                                 "other.")
        # Connected after the range is set, and that was measured: `setRange(1, 100)` on a fresh
        # spinbox emits `valueChanged(1)` when a slot is already listening, and this box would
        # then have written 1 % half a second after the window opened.
        self.strength.valueChanged.connect(self._changed)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.strength)
        row.addStretch()

    def reload(self) -> None:
        """Paint the number from the daemon's answer.

        Refuses while a change of its own is waiting, for the reason every box on this page does:
        the daemon says "something changed" within a second of every write, and repainting on top
        of a number half typed throws it away. `setValue` emits when the number differs, so the
        guard around it is what keeps opening the window from writing.
        """
        if self._pending.isActive():
            return
        self._loading = True
        try:
            value = (self.c.settings() or {}).get("transparency")
            if value is not None:
                self.strength.setValue(int(value))
        finally:
            self._loading = False

    def _changed(self, _value: int) -> None:
        if self._loading:
            return
        self._pending.start()

    def _write(self) -> None:
        """One number, and a line while the compositor takes it: this reaches every see-through
        window on the desktop and ends in a reconfigure, which is a visible pause."""
        self.says.emit(f"Opacity {self.strength.value()} %…")
        QApplication.processEvents()
        # Cleared only when it was taken: a refusal is already on the line, with its reason.
        if self.c.set_settings(transparency=int(self.strength.value())):
            self.says.emit("")


# ---------------------------------------------------------------------- the Appearance tab

class AppearancePage(SettingsPage):
    """The window's frame and its outline.

    It owns the corner radius for the whole app. The blur effect keeps a radius of its own and the
    two have to agree — a blur rounded less than the window shows as a bright sliver in each
    corner — so this page writes both and the Effects tab stopped asking.

    The five other frame settings were controls here while the corner was being investigated, and
    are fixed again now that it has been: the answer was the button outline, declared in
    `daemon/defaults.py`, not any of them. They are declared there at the values that
    investigation settled on, and this page puts them in place whenever it writes.

    Last, the title bar, which nothing on this page asks about any more: one line and the button
    that opens the decoration's own dialog, where it is changed. See `TitleBarBox`.

    The whole of what a window looks like is one section now -- how see-through it is, the corner
    it is rounded at and the ring drawn round it -- and the rows of that ring that the style in
    force does not read are greyed rather than left there offering to set a value nothing reads.
    """

    enforces = "appearance"

    RADIUS = ("klassy", "Windeco", "WindowCornerRadius")

    #: The keys this page has a control for, per state, as (style, custom colour).
    OUTLINE_PAIRS = ((("klassy", "WindowOutlineStyle", "WindowOutlineStyleActive"),
                      ("klassy", "WindowOutlineStyle", "WindowOutlineCustomColorActive")),
                     (("klassy", "WindowOutlineStyle", "WindowOutlineStyleInactive"),
                      ("klassy", "WindowOutlineStyle", "WindowOutlineCustomColorInactive")))

    def __init__(self, client: Client, parent=None):
        super().__init__(APPEARANCE_FIELDS, client, parent)
        #: Above the colours, because a profile is the colours and what they land on, kept under
        #: a name -- see `ProfilesBox`.
        self.profiles = ProfilesBox(client, self)
        self.extra_top.addWidget(self.profiles)
        self.colours = ThemeBox(client)
        self.extra_top.addWidget(self.colours)
        #: First row of the Window section, above the corner and the ring: the three of them are
        #: what a window looks like. Which windows are see-through is still chosen row by row on
        #: the Windows tab; this is how see-through they are.
        self.transparency = TransparencyRow(client)
        self.transparency.says.connect(self.says)
        # A `FieldLabel` and not a plain one, so its name lines up with the names under it. Its dot
        # never shows: this app owns the number outright, so there is no "not written" state.
        #
        # *Opacity* and not *Transparency*, because the number counts how solid a window is: 100
        # is opaque, and a label saying the opposite of its number made the bigger number look
        # like the more see-through one. The tick on the Windows tab keeps *Transparency*, which
        # is what it switches.
        self.section_forms["Window"].insertRow(0, FieldLabel("Opacity"), self.transparency)
        #: The way back, and the whole of it. The outline is the wallpaper's to move and nobody
        #: else's, so between two wallpapers it is yours -- and this is how it is put on the
        #: desktop's colour by hand, without waiting for a wallpaper to hand that colour over.
        self.take_theme = QPushButton("Take the theme colour")
        self.take_theme.setToolTip("Puts the colour from Colours above on the ring, wherever the "
                                   "style reads one.")
        self.take_theme.clicked.connect(self._take_theme_colour)
        self.section_forms["Window"].addRow(QLabel(""), self.take_theme)
        #: Which of the outline rows are doing anything depends on the two style menus, so they
        #: are followed. `_load` runs it once more, so the tab opens in the right shape.
        for style, _colour in self.OUTLINE_PAIRS:
            self.widgets[style].currentIndexChanged.connect(self._follow_outline)
        #: Last, and asked about by nothing on this page: where the title bar is changed.
        self.title_bar = TitleBarBox()
        self.extra_bottom.addWidget(self.title_bar)
        self.colours.reloaded.connect(self._colours_reloaded)
        #: The box's progress line is the window's, like every other one.
        self.colours.says.connect(self.says)
        #: When Klassy is missing or the compositor is not running it: the title bar, the ring
        #: and the corner below are Klassy's settings, and without it they do nothing. Above the
        #: scroll area, like the Tiling tab's band, so it is not something to scroll back up to.
        self.klassy_band = warning()
        self.layout().insertWidget(0, self.klassy_band)

    def _load(self, data: dict) -> None:
        super()._load(data)
        missing = unavailable(data, "klassy")
        self.klassy_band.setText(f"{missing} The title bar, the outline and the corner here are "
                                 f"its settings. The Settings tab says what to do."
                                 if missing else "")
        self.klassy_band.setVisible(bool(missing))
        # Which ends in `reloaded`, and that is where the two things this page keeps in step with
        # the box are done -- here they would be done on a page load and nowhere else.
        self.colours.load(self.c.theme())
        self.transparency.reload()
        self.profiles.reload()
        self._follow_outline()

    def _follow_outline(self, *_) -> None:
        """Grey the rows of the ring that the style in force does not read.

        Four of the seven controls here set a value only two of the seven styles ever look at: the
        custom colour of each state, that colour's opacity, and the accent's opacity. Left live
        they invite somebody to choose a colour that nothing draws -- which is the interface
        stating something untrue, the one thing the tables in this app are not allowed to do.

        Greyed and not hidden. A row that vanishes reads as a feature that vanished, and with
        every change applying by itself the page would step under somebody's hands every time a
        menu moved. The label is left alone either way: a greyed label here means the app does not
        know what applies, which is `_paint`'s to say and a different fact.
        """
        active, inactive = self.OUTLINE_PAIRS
        style, colour = active
        chosen = self.widgets[style].currentData()
        for ident, applies in (
                (colour, chosen in OUTLINE_CUSTOM_STYLES),
                (("klassy", "WindowOutlineStyle", "WindowOutlineCustomColorOpacityActive"),
                 chosen in OUTLINE_CUSTOM_STYLES),
                (("klassy", "WindowOutlineStyle", "WindowOutlineAccentColorOpacityActive"),
                 chosen in OUTLINE_ACCENT_STYLES),
                (inactive[1],
                 self.widgets[inactive[0]].currentData() in OUTLINE_CUSTOM_STYLES)):
            if ident in self.widgets:
                self.widgets[ident].setEnabled(applies)
        self.take_theme.setEnabled(bool(self.colours.applied_accent())
                                   and chosen in OUTLINE_CUSTOM_STYLES)

    def _colours_reloaded(self) -> None:
        """Whatever the Colours box has just learned, the form beside it has to learn as well.

        Two things travel this way, and both used to be worked out once and then go stale under an
        open window, because every path that refreshes that box refreshes only that box -- the
        daemon's `Changed`, its `ColourReady`, and the box's own write.

        The button: enabled only while there is a colour to take, so clearing the colour greys it
        out instead of leaving it clickable and silent. The swatch: the window outline's colour is
        written by the daemon when a wallpaper hands its colour over, and this page has a control
        for that very key -- left alone it showed the colour the file used to hold, and the next
        write would have put that back.
        """
        #: **Both halves of each pair**, and the style is the half that was missing. Choosing a
        #: preset now moves the active outline on to the style that reads a colour as well as
        #: writing the colour, so a form that repainted the colour and left the style would show a
        #: colour beside a style that reads none -- and the next write would put the old style back
        #: over the new colour. `refresh` leaves anything already touched alone.
        self.refresh(self.c.groups(), [ident for pair in self.OUTLINE_PAIRS for ident in pair])
        #: After the repaint and not before it: which rows are live follows the styles that have
        #: just been painted. `_paint` blocks the signals, so nothing here fires on its own.
        self._follow_outline()

    def _take_theme_colour(self) -> None:
        """Fill the outline colour from the theme's, on whichever states actually read one.

        Only those: writing a colour into a state whose style draws from the palette would be a
        value nothing reads, and a control claiming to have done something. `daemon/klassy.py`
        refuses the same write for the same reason.
        """
        accent = self.colours.applied_accent()
        if not accent:
            return
        for style, colour in self.OUTLINE_PAIRS:
            if self.widgets[style].currentData() in OUTLINE_CUSTOM_STYLES:
                self.widgets[colour].set_value(accent)
                self.touched.add(colour)
        # A `ColorButton` set from code emits nothing, so the clock has to be started by hand --
        # this is the one control in the window whose value another control fills in.
        self.queue()

    def extra_changes(self) -> dict:
        """Mirror the radius into the blur, and only when the radius itself is being written.

        Keyed off `changes()` rather than off the widget: the widget always has a value, so
        mirroring unconditionally would write the blur's radius on every write from this page,
        including the ones that were about the outline.
        """
        radius = (self.changes().get("klassy") or {}).get("Windeco", {}).get(
            "WindowCornerRadius")
        return {"blur": {"CornerRadius": radius}} if radius is not None else {}
