"""The Appearance tab's Colours box: light or dark, one of the presets, and a colour of your own.

`ThemeBox` reads the colours from the daemon's `theme` and writes them through `set_theme`, with
reads, writes and a debounce of its own rather than the form engine's, because a preset is a name
that stands for a colour scheme, not a key. `Swatch` draws each preset in the four colours its
scheme file actually holds, read by the daemon rather than typed here, and `scheme_colours` turns
those into Qt colours for the profiles' icons as well.
"""

from __future__ import annotations

import html

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QRadioButton, QVBoxLayout, QWidget)

from client import Client
from widgets import SECTION_HINTS, ColorButton, Section, Spin, warning


# ---------------------------------------------------------------------- the desktop's colours

#: What a colour of your own reaches on its own, and what soaking adds, in one sentence. The
#: measurement behind it -- how far Klassy Dark's window background moves at which strength -- is
#: recorded beside the code that writes the tint: the `TintFactor` paragraph of `daemon/theme.py`'s
#: module docstring.
SOAK_HINT = ("A colour of your own reaches highlights, links and the selection. Soaking pulls "
             "every other colour toward it as well, backgrounds included.")


#: How many swatches to a row. Four of them and the longest preset name still fit side by side in
#: the window's own width.
SWATCH_COLUMNS = 4


def scheme_colours(raw: list) -> list[QColor]:
    """The four colours the daemon reads out of a scheme's file -- the window, a content area,
    the selection and the text -- or nothing when the scheme is not on this machine. One reading
    for the swatch grid and for a profile's row, so the two cannot disagree about a preset."""
    out = []
    for value in raw or []:
        parts = str(value).split(",")
        if len(parts) < 3:
            return []
        out.append(QColor(*(int(x) for x in parts[:3])))
    return out if len(out) == 4 else []


class Swatch(QPushButton):
    """One preset, drawn in the colours it would actually apply.

    The four colours come from the scheme's own file by way of the daemon, not from a table here.
    A preset that is drawn from a list somebody typed is a preset that can lie about itself the
    first time the file behind it changes — and one of these files is meant to be edited by hand.

    **Five states, drawn apart.** It used to draw two -- on the desktop, or not -- so the pointer
    passing over a card changed nothing at all and there was no sign a card could be clicked. Now:
    dimmed for one that cannot go on this machine, washed under the pointer, ringed thickly for the
    one on the desktop, and ringed thinly in the window's own highlight for wherever the keyboard
    is. Hover and the keyboard compose with the ring; a card that cannot be chosen shows neither.

    The wash is the card's **own** text colour and not the interface's highlight, for the reason
    the ring is: a wash in the desktop's colour over a card showing some other palette would be
    the wrong colour in the wrong place. That colour is the one every scheme guarantees against
    its own window -- the ratio `scripts/dry-run.sh` measures -- so it shows on all of them,
    including the monochrome pair.
    """

    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.entry = entry
        self._hover = False
        self.setCheckable(True)
        self.setAutoExclusive(True)
        #: Four extra pixels each way over the card itself, which stays the size it was: the rings
        #: live in that gutter, and the keyboard's sits outside the one for the desktop.
        self.setFixedSize(172, 72)
        trouble = str(entry.get("trouble") or "")
        self.setEnabled(not trouble)
        if not trouble:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(str(entry.get("name", "")))
        tip = [str(entry.get("note") or ""), trouble]
        self.setToolTip("<br>".join(t for t in tip if t))

    def _colours(self) -> list:
        return scheme_colours(self.entry.get("swatch") or [])

    def enterEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(3.5, 3.5, self.width() - 7.0, self.height() - 7.0)
        name = str(self.entry.get("name", ""))
        colours = self._colours()
        if not colours:
            # Nothing to draw it in, because the scheme is not on this machine. Say that, rather
            # than drawing a plausible rectangle in the interface's own colours.
            painter.setPen(QPen(self.palette().mid().color(), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(box, 5, 5)
            painter.setPen(self.palette().mid().color())
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, f"{name}\nnot installed")
            if self.hasFocus():
                painter.setPen(QPen(self.palette().highlight().color(), 1.5))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(QRectF(0.75, 0.75, self.width() - 1.5,
                                               self.height() - 1.5), 7, 7)
            painter.end()
            return
        window, view, selection, text = colours
        if not self.isEnabled():
            # The same colours, drawn faintly. No invented grey: what is unavailable here is this
            # preset, and it is still this preset.
            painter.setOpacity(0.40)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(window)
        painter.drawRoundedRect(box, 5, 5)
        # A content area, the way a window carries one, with a selected row in it. Three of the
        # four colours land where they land on a real window, which is the point of drawing this
        # rather than listing the values.
        inner = QRectF(box.left() + 8, box.top() + 23, box.width() - 16, box.height() - 31)
        painter.setBrush(view)
        painter.drawRoundedRect(inner, 3, 3)
        painter.setBrush(selection)
        painter.drawRoundedRect(QRectF(inner.left() + 5, inner.top() + 6,
                                       inner.width() * 0.46, 9), 2, 2)
        painter.setPen(text)
        painter.drawText(QRectF(box.left() + 9, box.top() + 4, box.width() - 18, 17),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, name)
        if self._hover and self.isEnabled():
            # A wash and not a ring: the ring is taken and means something else. A shade more of it
            # while the card is held down, which gives a pressed state for nothing.
            wash = QColor(text)
            wash.setAlpha(48 if self.isDown() else 28)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(wash)
            painter.drawRoundedRect(box, 5, 5)
        if self.isChecked():
            # The one on the desktop wears a ring, in the swatch's own text colour and not the
            # interface's highlight: a border in the desktop's colour around a card showing some
            # other palette is a theme-coloured border in the wrong place, and with no ring at all
            # nothing said which preset was on. The text colour is the one every scheme guarantees
            # against its own window colour -- the ratio `scripts/dry-run.sh` measures.
            painter.setPen(QPen(text, 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(box, 5, 5)
        if self.hasFocus():
            # Where the keyboard is, which is a fact about this window rather than about the
            # desktop's colours -- so this is the one ring here drawn in the window's own palette,
            # and it goes outside the card in the gutter the size buys.
            painter.setOpacity(1.0)
            painter.setPen(QPen(self.palette().highlight().color(), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(0.75, 0.75, self.width() - 1.5, self.height() - 1.5),
                                    7, 7)
        painter.end()


class ThemeBox(Section):
    """Light or dark, one of the presets, and a colour of your own.

    Not a `Field` and not part of the form engine (`gui/form.py`), deliberately: a preset is not a
    `(source, group, key)` triple, it is a name that stands for a colour scheme, and
    `SettingsPage.changes()` has nothing to say about it. This is the shape
    `TransparencyRow` takes as well -- its own reads, its own writes, its own debounce.

    Applying is not free. Each change runs up to three of the desktop's own tools, every one of
    them a Qt program, and the whole session repaints. So: a debounce long enough to swallow a
    drag along the strength control, and the box goes dead while a change is in flight.
    """

    #: Painted from a fresh answer. The page around this box has two things that depend on what is
    #: in it -- whether *Take the theme colour* has a colour to take, and the outline's own swatch,
    #: which a wallpaper moves in the file while the page is open. Both used to be worked out once
    #: when the tab was built and then go stale under the window, because every path that refreshes
    #: this box refreshes only this box.
    reloaded = Signal()
    #: What the window's footer should say. The box has a line of its own, and it says which preset
    #: is on; progress belongs to the window, in one shape, in one place.
    says = Signal(str)

    def __init__(self, client: Client, parent=None):
        super().__init__("Colours", SECTION_HINTS["Colours"], parent)
        self.c = client
        #: Set while the widgets are painted from the daemon's answer. Not `blockSignals` alone:
        #: checking one auto-exclusive radio emits `toggled(False)` on its sibling, so a box that
        #: wrote on any toggle would write on its way up -- which `scripts/simulate.sh` catches as
        #: "opening the interface would have written", and is right to.
        self._loading = False
        self._busy = False
        self._data: dict = {}
        self._swatches: list = []

        self._pending = QTimer(self)
        self._pending.setSingleShot(True)
        self._pending.setInterval(500)
        self._pending.timeout.connect(self._write)

        self.trouble = warning()

        # Their own container, so the two of them are exclusive among themselves and not among
        # every other checkable thing in this box.
        modes = QWidget()
        mode_row = QHBoxLayout(modes)
        mode_row.setContentsMargins(0, 0, 0, 0)
        self.dark = QRadioButton("Dark")
        self.light = QRadioButton("Light")
        for button in (self.dark, self.light):
            mode_row.addWidget(button)
            button.toggled.connect(self._mode_picked)
        mode_row.addStretch()

        self.holder = QWidget()
        self.grid = QGridLayout(self.holder)
        self.grid.setContentsMargins(0, 0, 0, 0)
        # A stretch in the column after the last, so four fixed-width swatches sit together on the
        # left instead of being spread across whatever width the window happens to have.
        self.grid.setColumnStretch(SWATCH_COLUMNS, 1)

        #: The sentence under the grid: one sentence, the same for every preset, and a widget
        #: rather than fixed text because `_write` borrows it as the status line while a change
        #: is in flight.
        self.panel = QLabel()
        self.panel.setWordWrap(True)

        self.accent = ColorButton("Your own colour")
        self.accent.picked.connect(self._touch)
        self.clear_accent = QPushButton("Clear")
        self.clear_accent.setToolTip("Back to the colours the preset came with")
        self.clear_accent.clicked.connect(self._clear_accent)
        accent_row = QHBoxLayout()
        accent_row.setContentsMargins(0, 0, 0, 0)
        accent_row.addWidget(self.accent)
        accent_row.addWidget(self.clear_accent)
        accent_row.addStretch()
        accent_holder = QWidget()
        accent_holder.setLayout(accent_row)

        self.offer = QLabel()
        self.offer.setWordWrap(True)
        self.take = QPushButton("Take it")
        self.take.clicked.connect(self._take_offered)
        offer_row = QHBoxLayout()
        offer_row.setContentsMargins(0, 0, 0, 0)
        offer_row.addWidget(self.offer, 1)
        offer_row.addWidget(self.take)
        offer_holder = QWidget()
        offer_holder.setLayout(offer_row)
        self._offer_holder = offer_holder

        self.soak = QCheckBox("Let it soak into the backgrounds")
        self.soak.toggled.connect(self._touch)
        self.strength = Spin()
        self.strength.setRange(5, 90)
        self.strength.setSuffix(" %")
        self.strength.setMaximumWidth(90)
        self.strength.valueChanged.connect(self._touch)
        soak_row = QHBoxLayout()
        soak_row.setContentsMargins(0, 0, 0, 0)
        soak_row.addWidget(self.soak)
        soak_row.addWidget(self.strength)
        soak_row.addStretch()
        soak_holder = QWidget()
        soak_holder.setLayout(soak_row)

        #: Which of its three states the window outline is in, said whatever else is going on.
        #: It used to live inside the wallpaper's offer, so it was printed only while the colour on
        #: screen was the wallpaper's own -- the one state in which it had least to say -- and was
        #: silent on every desktop that does not take colours from its wallpaper at all.
        self.outline_line = QLabel()
        self.outline_line.setWordWrap(True)

        # A column and not a form: three of the eleven rows this used to be ever used the label
        # column, and one of those three was an empty label holding a place. Each caption sits on
        # the row it names instead.
        mode_row.insertWidget(0, QLabel("Mode"))
        accent_row.insertWidget(0, QLabel("Your own colour"))
        # Under the colour rather than beside it: soaking is something that colour does, not a
        # second setting.
        soak_row.insertSpacing(0, 18)

        column = QVBoxLayout(self)
        column.addWidget(self.trouble)
        column.addWidget(modes)
        column.addWidget(self.holder)
        column.addWidget(self.panel)
        # The wallpaper's offer above the colour and not below it: it is what to decide before
        # choosing one by hand.
        column.addWidget(offer_holder)
        column.addWidget(accent_holder)
        column.addWidget(soak_holder)
        column.addWidget(self.outline_line)

    # ---------------------------------------------------------------- painting it

    def load(self, data: dict) -> None:
        """Paint the box from the daemon's answer.

        Refuses while a change of its own is waiting or under way, for the reason
        `SettingsPage.load` refuses: the daemon says "something changed" within a second of every
        write, including this one's, and repainting on top of a choice half made throws it away.
        """
        if self._pending.isActive() or self._busy:
            return
        self._loading = True
        try:
            self._data = data or {}
            mode = str(self._data.get("mode") or "") or "dark"
            (self.dark if mode == "dark" else self.light).setChecked(True)
            self._fill(mode)
            chosen = str(self._data.get("preset") or "")
            for swatch in self._swatches:
                swatch.setChecked(str(swatch.entry.get("id") or "") == chosen)
            accent = str(self._data.get("accent") or "")
            self.accent.set_value(accent)
            tint = float(self._data.get("tint") or 0)
            self.soak.setChecked(bool(accent) and tint > 0)
            fallback = float(self._data.get("default_tint") or 0.25)
            self.strength.setValue(int(round((tint or fallback) * 100)))
            trouble = [str(t) for t in (self._data.get("trouble") or [])]
            self.trouble.setText("<b>Not what this app expects.</b> " + "; ".join(trouble)
                                 + ". Picking a mode here puts it back.")
            self.trouble.setVisible(bool(trouble))
        finally:
            self._loading = False
        self._sync()
        self.reloaded.emit()

    def _fill(self, mode: str) -> None:
        while self.grid.count():
            taken = self.grid.takeAt(0).widget()
            if taken is not None:
                taken.setParent(None)
                taken.deleteLater()
        self._swatches = []
        entries = [p for p in (self._data.get("presets") or []) if p.get("mode") == mode]
        for i, entry in enumerate(entries):
            swatch = Swatch(entry, self.holder)
            swatch.toggled.connect(self._swatch_picked)
            self.grid.addWidget(swatch, i // SWATCH_COLUMNS, i % SWATCH_COLUMNS)
            self._swatches.append(swatch)

    def _picked(self):
        return next((s for s in self._swatches if s.isChecked()), None)

    def _sync(self) -> None:
        """Keep the controls saying what is true, and the sentence under the grid honest.

        **Nothing here can be set while no preset is ringed**, and that is a defect being said out
        loud rather than a rule being invented. A colour of your own is written beside the preset
        it belongs to, so with no preset there is nothing to write it against: choosing one simply
        did nothing at all, silently. Now the row greys and the line under the grid says what to do
        first.
        """
        picked = self._picked()
        has_preset = picked is not None
        has_accent = bool(self.accent.value())
        self.accent.setEnabled(has_preset)
        self.soak.setEnabled(has_preset and has_accent)
        self.strength.setEnabled(has_preset and has_accent and self.soak.isChecked())
        self.clear_accent.setEnabled(has_preset and has_accent)
        self._say_offer()
        self._say_outline()
        if picked is None:
            self.panel.setText("The colours on this desktop are not one of these. Pick one to "
                               "take them over — a colour of your own goes on top of a preset.")
            return
        # Named in words as well as ringed: the sentence is what says which preset is on.
        self.panel.setText(f"<b>{picked.entry.get('name', '')}</b> is on. The panel follows its "
                           "colours.")

    def _say_offer(self) -> None:
        """What the wallpaper is offering, and whether the desktop has taken it.

        Three states worth telling apart, because they are three different things to do next: the
        colour on screen came from the wallpaper and nothing is owed; somebody has since chosen
        their own, which stands until the next wallpaper; or there is no colour to be had from this
        wallpaper at all, with the reason.
        """
        showing = bool(self._data.get("auto_colour"))
        self._offer_holder.setVisible(showing)
        if not showing:
            return
        why = str(self._data.get("wallpaper_trouble") or "")
        offered = str(self._data.get("from_wallpaper") or "")
        if why or not offered:
            self.offer.setText(why or "this wallpaper has no colour to give")
            self.take.setVisible(False)
            return
        if offered == self.accent.value():
            self.offer.setText("This colour came from your wallpaper.")
            self.take.setVisible(False)
            return
        self.offer.setText(f"Your wallpaper offers <b>{offered}</b>. The colour below is yours, and "
                           f"stands until the next wallpaper.")
        self.take.setVisible(True)

    def _say_outline(self) -> None:
        """Which of its three states the window outline is in.

        Compared against the colour the desktop is actually **wearing** and not against the widget
        beside it: a colour chosen half a second ago and still inside the debounce, or one the
        daemon refused, would otherwise make this line describe a desktop nobody has.

        It promises nothing about what happens next beyond the two things that are true: a colour
        taken from a wallpaper reaches the outline, and **choosing a preset above puts that
        preset's own colour on it**. A colour typed into the box does neither, and *Take the theme
        colour* under *Outline*, below, is how that one is put in step by hand.

        Every sentence here was rewritten when the preset rule arrived, and it is worth saying why
        rather than leaving it to look like tidying. Three of them said a wallpaper's colour was
        the *only* thing that moved the ring, and one said this box could not reach it at all --
        each of which had become a control stating something untrue, which is the defect the
        `· default` marker exists to have stopped.
        """
        if not self._data.get("outline_follows"):
            self.outline_line.setText(
                "The window outline is on a style that draws from the palette, so no colour here "
                "reaches it. Choosing a preset above puts that preset's own colour on it; "
                "<i>Appearance &gt; Outline</i>, below, is where the style is chosen.")
            return
        worn, accent = str(self._data.get("outline_colour") or ""), self.applied_accent()
        if not accent:
            # No colour of your own to be in step with, and the button that would align it is
            # greyed out for the same reason -- so this says where the outline is and stops.
            self.outline_line.setText(
                "The window outline is on a colour of its own, set under <i>Outline</i> below. "
                "Choosing a preset above puts that preset's colour on it, and so does a colour "
                "taken from your wallpaper.")
            return
        if worn == accent:
            self.outline_line.setText("The window outline is on this same colour.")
            return
        self.outline_line.setText(
            "The window outline is on a colour of its own. A colour that came from your wallpaper "
            "moves it, and so does choosing a preset above; <i>Take the theme colour</i>, under "
            "<i>Outline</i> below, puts it on the colour above.")

    def _take_offered(self) -> None:
        offered = str(self._data.get("from_wallpaper") or "")
        if not offered:
            return
        self.accent.set_value(offered)
        self.soak.setChecked(True)
        self._touch()

    def set_auto(self, on: bool) -> None:
        """*Colour from the wallpaper* was flicked in the strip at the top of the window.

        Told rather than re-read, and that is not a shortcut: `load` above refuses to repaint
        while a colour change of this box's is inside its debounce or in flight, so a box left to
        find out through the daemon's round trip would show an offer row that lags the switch and
        then snaps. The switch itself is written by the strip; this is only the half of it that
        is drawn here.
        """
        self._data = dict(self._data, auto_colour=bool(on))
        self._say_offer()

    def applied_accent(self) -> str:
        """The colour the desktop is actually wearing, as the daemon last reported it.

        Read by the Outline section beside this box, which offers to take it, and by the line that
        says where the outline stands. Deliberately the applied colour and not
        `self.accent.value()`: a colour half chosen here and not yet written is not one the outline
        should be aligned to, nor one to describe the desktop with.
        """
        return str(self._data.get("accent") or "")

    # ---------------------------------------------------------------- choosing

    def _mode_picked(self, on: bool) -> None:
        if self._loading or not on:
            return
        mode = "dark" if self.dark.isChecked() else "light"
        self._fill(mode)
        # The mode's own default, rather than whatever sat at the same position in the other
        # mode's grid: the two lists are not the same length and position means nothing across
        # them. This is the preset the global theme applies by itself, which is the one place it
        # is always safe to land.
        for swatch in self._swatches:
            if not swatch.entry.get("trouble"):
                swatch.setChecked(True)
                break
        self._touch()

    def _swatch_picked(self, on: bool) -> None:
        """A preset is its own colours, so choosing one puts them back.

        A colour of your own is dropped rather than laid over the new preset. It is the answer to
        "put Carl back", which otherwise gave Carl tinted with whatever the last wallpaper had
        chosen and looked like a preset that had not been applied. Choosing the colour after the
        preset is how a colour of your own is kept.

        **Here and not in the daemon**, and that is not tidiness. The same rule inside `set_theme`
        would silently discard the colour of every settings file imported and every profile loaded
        whose preset differs from the one in force — a backup that does not restore — and would
        break the check that drives every installed preset with a probe colour in one payload.

        Switching **mode** arrives here too: `_mode_picked` checks that mode's default preset, and
        checking one emits `toggled`. Deliberate — landing on a preset is landing on its colours.
        """
        if self._loading or not on:
            return
        self.accent.set_value("")
        self.soak.setChecked(False)
        self._touch()

    def _clear_accent(self) -> None:
        self.accent.set_value("")
        self.soak.setChecked(False)
        self._touch()

    def _touch(self, *_) -> None:
        if self._loading:
            return
        self._sync()
        self._pending.start()

    # ---------------------------------------------------------------- writing

    def chosen(self) -> dict:
        picked = self._picked()
        if picked is None:
            return {}
        accent = self.accent.value()
        soaking = bool(accent) and self.soak.isChecked()
        return {"mode": "dark" if self.dark.isChecked() else "light",
                "preset": str(picked.entry.get("id") or ""),
                "accent": accent,
                "tint": (self.strength.value() / 100.0) if soaking else 0}

    def _write(self) -> None:
        """Put the colours on the desktop, and say so while it happens.

        The line goes in the window's footer and not in this box any more: `self.panel` names the
        preset that is on, and borrowing it for progress meant the name disappeared for exactly the
        second and a half the change takes. One shape for every slow write in this window, and this
        is one of them.

        A refusal now repaints from the daemon. It used to put a sentence on the line and leave the
        grid ringing a preset the desktop had refused -- a control stating something untrue, which
        is the fault this app treats as the serious one.
        """
        payload = self.chosen()
        if not payload or self._busy:
            return
        self._busy = True
        picked = self._picked()
        name = str(picked.entry.get("name", "")) if picked is not None else ""
        self.says.emit(f"Putting <b>{html.escape(name)}</b> on… the desktop's own tools take a "
                       f"second or two" if name else "Applying…")
        self.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        # One pass of the event loop so the line above is on screen. The call below blocks for as
        # long as the desktop's own tools take, and a window that freezes with nothing said is a
        # window that looks broken. Re-entry is what `_busy` is for.
        QApplication.processEvents()
        try:
            ok = self.c.set_theme(payload)
        finally:
            QApplication.restoreOverrideCursor()
            self.setEnabled(True)
            self._busy = False
        # Nothing to add on a refusal: the client has already put the daemon's reason on the line,
        # and a sentence of this box's own would only cover it.
        if ok:
            self.says.emit("")
        QTimer.singleShot(400, lambda: self.load(self.c.theme()))
