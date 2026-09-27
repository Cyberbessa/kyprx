"""The strip above the tabs: the three things somebody opens this window to do.

*Adjust new windows* (whether a window never seen before gets KyprX's defaults), *Colour from the
wallpaper* (whether each wallpaper chosen hands its colour to the desktop), and which profile the
desktop is wearing, where choosing another puts it on. The two ticks are this app's own settings,
written through `SetSettings`; the profile menu puts a kept profile on the desktop through
`LoadProfile`. Neither goes through the form engine, and a profile is made and kept on the
Appearance tab.
"""

from __future__ import annotations

import html

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout,
                               QWidget)

from client import Client
from profiles_box import look_icon
from widgets import Choice


#: One word for the thing that is kept under a name, and it is **profile**. The strip called it a
#: look and the tab beside it called it a profile; the same thing with two names is a thing to
#: learn twice. The file on disk and the daemon's own methods keep `profile` too, which is what
#: they were always called.
ADJUST_TIP = ("New windows get KyprX's defaults as they open: no title bar, the outline on, "
              "see-through and blurred. Unticked, they are listed and left alone until you tick "
              "it again.")

AUTO_TIP = ("Every wallpaper you choose hands its colour to the desktop. Loading a profile "
            "switches this off, so that profile stays as it is.")

PROFILE_TIP = ("The profile the desktop is wearing. Choosing another one puts it on, which takes "
               "a second or two.")

PROFILE_EMPTY_TIP = ("No profiles kept yet. They are made on the Appearance tab, where a profile "
                     "is the desktop as it is now, kept under a name.")


class LookBox(Choice):
    """The profile control. Deaf to the wheel like every other menu here, and this is the one that
    was measured: a notch with the pointer merely passing over it used to put another profile on
    the desktop -- one to three seconds of frozen screen, no way back, and *Colour from the
    wallpaper* switched off behind it. Every other menu in this window writes a key; this one
    repaints the desktop."""


class TopStrip(QWidget):
    """The three things always on screen, above the tabs.

    The division is what this strip is for: a tab is something set once, and these are the three
    things somebody opens this window to *do*. Two of them were buried in a tab and one of them —
    `Pause` — was the only one up here and asked to be read backwards.

    Its own reads and its own writes, the shape `TransparencyRow` and `ThemeBox` take and for the
    same reason: these are settings of this app's rather than keys in somebody else's config file,
    so they go through `SetSettings` and not through the form engine. No debounce either — a
    checkbox is one write, and putting a look on is a deliberate and expensive one.

    Everything else about a look stays in `ProfilesBox` on the Appearance tab: one place to make
    them, one place to put them on.
    """

    #: What the footer should say, for the window to put it there. `WindowsTab.copied` takes the
    #: same road, and for the same reason: the line belongs to the window, not to a widget in it.
    says = Signal(str)
    #: A look went on. The Appearance tab has controls for three of the things that just changed.
    loaded = Signal()
    #: *Colour from the wallpaper* was just flicked. The Colours box draws a line from that same
    #: setting and has to be told directly: its own `load` refuses while a colour change of its is
    #: inside the 500 ms debounce, so the daemon's round trip is not enough to keep it in step.
    auto_changed = Signal(bool)

    #: What the combo shows when the desktop is wearing something that is not on the list — which
    #: is the ordinary state until somebody saves one. Never a destination: the entry is disabled,
    #: because "put on the profile that is already on" is not a thing to ask for.
    UNNAMED = "Current profile"

    def __init__(self, client: Client, parent=None):
        super().__init__(parent)
        self.c = client
        #: Set while the widgets are painted from the daemon's answer, and checked by every
        #: handler below. The checkboxes need it because `setChecked` emits `toggled`; the combo
        #: does not, because `activated` is emitted only when somebody chooses — but it is checked
        #: there too, since a strip that wrote on its way up is exactly what `scripts/simulate.sh`
        #: catches as "opening the interface would have written", and is right to.
        self._loading = False
        #: Set while a look is going on. The call blocks for as long as the desktop's own colour
        #: tools take, and the daemon says "something changed" in the middle of it.
        self._busy = False
        #: The name behind each row of the combo, "" for the unnamed one. Kept beside the combo
        #: rather than read off it, because the rows are not the profiles when the unnamed entry
        #: is there.
        self._names: list[str] = []
        self._worn = ""

        #: The one inverted control in this app. The setting is `paused` and the question here is
        #: the opposite one, because ticked has to mean the app is working — that is the normal
        #: state, and a control whose normal state is unticked reads as something switched off.
        self.adjust = QCheckBox("Adjust new windows")
        self.adjust.setToolTip(ADJUST_TIP)
        self.adjust.toggled.connect(self._adjust_toggled)

        self.auto = QCheckBox("Colour from the wallpaper")
        self.auto.setToolTip(AUTO_TIP)
        self.auto.toggled.connect(self._auto_toggled)

        self.look = LookBox()
        self.look.setIconSize(QSize(48, 16))   # the strip the profiles table draws, same size
        self.look.setMinimumWidth(170)
        self.look.setMaximumWidth(320)
        #: `activated` and not `currentIndexChanged`: it is emitted only when somebody chooses a
        #: row, never when the list is refilled — and this list is refilled on every change the
        #: daemon reports. With the other signal, painting the strip would put a look on.
        self.look.activated.connect(self._look_chosen)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 6)
        row.addWidget(self.adjust)
        row.addSpacing(18)
        row.addWidget(self.auto)
        row.addStretch()
        row.addWidget(QLabel("Profile"))
        row.addWidget(self.look)

        #: A plain separator rather than a frame around the strip or a stylesheet: it comes out of
        #: the widget style like everything else here, and it is what makes these three read as a
        #: strip of their own instead of three controls left above the tabs.
        rule = QFrame()
        rule.setFrameShape(QFrame.Shape.HLine)
        rule.setFrameShadow(QFrame.Shadow.Sunken)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(row)
        layout.addWidget(rule)

    # ---------------------------------------------------------------- painting it

    def reload(self, settings: dict | None = None) -> None:
        """Paint the two checkboxes. The looks are painted separately -- see `set_looks`.

        `settings` is passed in by the window, which has just read it for the line at the bottom:
        one read rather than two, on a path that runs on every change the daemon reports.

        Both guards are load-bearing, and the first one became so with this very change.
        `setChecked` emits `toggled`, and *Adjust new windows* is the one control in this app whose
        unticked state is the daemon's default -- so the first paint of a fresh window really does
        change the widget, where the old `Pause` was set to false over false and emitted nothing.
        A stray write here is also the one kind `scripts/simulate.sh` cannot see on its own, since
        the settings file is never written in dry run and leaves no diff to find; `scripts/drive.py`
        reads the values back for exactly that reason.
        """
        if self._busy:
            return
        settings = self.c.settings() if settings is None else settings
        self._loading = True
        try:
            for widget, value in ((self.adjust, not settings.get("paused", False)),
                                  (self.auto, bool(settings.get("auto_colour", False)))):
                widget.blockSignals(True)
                widget.setChecked(value)
                widget.blockSignals(False)
        finally:
            self._loading = False

    def set_looks(self, data: dict) -> None:
        """The looks, from the daemon's own answer -- the same one the Appearance tab's table
        draws, so the two cannot disagree about which look is on.

        The answer is handed in rather than asked for here, and that is the whole point:
        `Profiles` costs 4 ms empty and about 2 ms more a profile, against `Settings`'s 0.1 --
        measured, and the number is beside the timer in `MainWindow`. The window asks once, on a
        settle, and both this and the table on the Appearance tab are painted from that one answer.

        Which look is on is worked out on every read (`profiles.is_on`) and kept nowhere, so there
        is nothing here that can go stale.
        """
        if self._busy:
            return
        entries = [e for e in ((data or {}).get("profiles") or []) if isinstance(e, dict)]
        unreadable = str((data or {}).get("trouble") or "")
        worn = next((i for i, e in enumerate(entries) if e.get("current")), None)

        self.look.blockSignals(True)
        self.look.clear()
        self._names = []
        if worn is None:
            self.look.addItem(self.UNNAMED)
            self._names.append("")
            # The combo is built here, so its model is Qt's own `QStandardItemModel` and a row can
            # simply be switched off.
            self.look.model().item(0).setEnabled(False)
        for entry in entries:
            name = str(entry.get("name") or "")
            colours = (entry.get("look") or {}).get("theme") or {}
            # The same strip of colours the table draws in its first column, for nothing: it is
            # what makes a name in a list stand for a look.
            self.look.addItem(look_icon(entry.get("swatch") or [],
                                        str(colours.get("accent") or "")), name)
            index = self.look.count() - 1
            self._names.append(name)
            if entry.get("trouble"):
                # Listed with the reason on it and refused, rather than left out: a look that
                # cannot go on this machine is still one somebody made. The reason goes in the
                # text and not only in a tooltip -- a greyed line nobody hovers explains nothing.
                self.look.setItemText(index, f"{name} — {entry['trouble']}")
                self.look.model().item(index).setEnabled(False)
                self.look.setItemData(index, str(entry["trouble"]), Qt.ItemDataRole.ToolTipRole)
        # With nothing worn the unnamed row is there and is row 0; with something worn it is not
        # there at all, so the profiles start at row 0 and `worn` is already the row.
        self.look.setCurrentIndex(0 if worn is None else worn)
        self._worn = "" if worn is None else self._names[worn]
        self.look.setEnabled(bool(entries) and not unreadable)
        self.look.setToolTip(unreadable or (PROFILE_TIP if entries else PROFILE_EMPTY_TIP))
        self.look.blockSignals(False)

    def _select(self, name: str) -> None:
        """Put the control back on this look without writing anything."""
        self.look.blockSignals(True)
        self.look.setCurrentIndex(self._names.index(name) if name in self._names else 0)
        self.look.blockSignals(False)

    # ---------------------------------------------------------------- doing things

    def _adjust_toggled(self, on: bool) -> None:
        if self._loading:
            return
        self.c.set_settings(paused=not on)

    def _auto_toggled(self, on: bool) -> None:
        """Its own write, and nothing else's: this is a setting of this app's, not a change to the
        desktop's colours, and it must not drag a theme apply along behind it."""
        if self._loading:
            return
        self.c.set_settings(auto_colour=bool(on))
        self.auto_changed.emit(bool(on))

    def _look_chosen(self, index: int) -> None:
        """Put that look on the desktop.

        The shape is `ProfilesBox._load`'s, and for its reasons: the call blocks for as long as
        the desktop's own colour tools take, so the line goes up first and the event loop is given
        one pass to paint it. A window that freezes with nothing said is a window that looks
        broken.
        """
        if self._loading or self._busy:
            return
        name = self._names[index] if 0 <= index < len(self._names) else ""
        if not name or name == self._worn:
            return
        self._busy = True
        self.setEnabled(False)
        self.says.emit(f"Putting <b>{html.escape(name)}</b> on… the desktop's own tools take a "
                       f"second or two")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            answer = self.c.load_profile(name)
        finally:
            QApplication.restoreOverrideCursor()
            self.setEnabled(True)
            self._busy = False
        if answer:
            # The desktop did not change, so neither does the control. A refusal left showing the
            # look that was refused would be the interface stating something untrue.
            self.says.emit(html.escape(answer))
            self._select(self._worn)
            return
        self.says.emit("")
        self._worn = name
        self.loaded.emit()
