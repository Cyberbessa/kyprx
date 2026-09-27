"""The small pieces the window's tabs are built from.

The warning and danger bands and a note; spin boxes and a drop-down the mouse wheel scrolls past
instead of changing; a setting's label with the dot that says nothing has been written for it; a
section box with the mark beside its name that holds one sentence of explanation -- most of those
sentences are in `SECTION_HINTS` -- and a button that picks a colour. None of them talks to the
daemon, and none builds anything at import time: a pixmap made before there is an application fails
the import check in `scripts/dry-run.sh`.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (QColorDialog, QComboBox, QDoubleSpinBox, QGroupBox, QHBoxLayout,
                               QLabel, QPushButton, QSpinBox, QStyle, QStyleOptionGroupBox,
                               QToolTip, QWidget)


# ---------------------------------------------------------------------- the small shared pieces

#: Marks a value that comes from a default rather than from the config file.
#:
#: It used to mean something weaker and worse: "the key is not in the file and this app has no
#: idea what applies". It now knows for the settings that matter — the decoration and the
#: compositor both ship their defaults, and both are read — so the value beside the marker is a
#: real reading rather than a placeholder, and the control stays usable. What the marker still
#: says is worth saying: nothing has been written for this setting, and nothing will be until it
#: is changed to something else.
UNSET = ("KyprX has not written this. The value beside it is what applies, and nothing will be "
         "written until you change it.")


#: The one sentence each section of a form carries, behind the mark beside its name. Here rather
#: than in the tables of `gui/fields.py` because a section is a heading, not a field -- and because
#: the three tables are read by name in half a dozen places and adding a third element to every
#: tuple would be felt in all of them.
SECTION_HINTS = {
    "Window": "The corner, the ring around a window, and how see-through the windows are.",
    "Blur": "How the desktop behind a see-through window is blurred.",
    "Window animation": "The movement a window makes when it is moved or resized.",
    "Gaps": "The space kept around the windows and between them.",
    "When a window moves": "What the rest of the layout does while one window is moved.",
    "New windows": "Where a window goes when it opens.",
    "Tiled windows": "How the windows that are tiled are drawn and what may happen to them.",
    "Never tiled": "The windows the tiler leaves exactly where they are put.",
    "Focus": "What it takes for a window to become the one you are typing into. These are the "
             "desktop's own settings, kept here because focus is most of what makes a tiled "
             "screen feel like one.",
    "Layouts": "The arrangements the layout key cycles through, and the order it cycles them in.",
    "Profiles": "The whole of this tab, kept under a name. Loading one puts those colours, that "
                "opacity and that frame back on the desktop.",
    "Colours": "The desktop's colours, windows and panel alike. Choosing a preset puts its own "
               "colours back.",
    "Title bar": "Where the title bar is changed, which is the decoration's own settings.",
    "Notifications": "When KyprX puts something on your screen.",
    "The window decoration": "Everything KyprX leaves to the decoration's own settings.",
    "Backup": "Every setting there is, in one file you can keep or carry to another machine.",
    "Problems": "What KyprX found wrong on this machine.",
    "What KyprX needs": "The five projects KyprX is built on: whether each one is installed, "
                        "which version, and whether the desktop is running it.",
    "Credits": "The projects KyprX is a pair of hands on. CREDITS.md has every one, with its "
               "licence and what that licence asks of KyprX.",
    "Picker": "What the wallpaper key offers you when you press it.",
    "Layout": "What the wallpaper picker looks like when it opens.",
}

#: One of the two colours this app paints by hand. Everything else in this window comes out of the
#: desktop's own widget style, which is the point of using widgets at all -- but a band that says
#: something is wrong has to be the same band wherever it appears, and the style has no role for
#: it. It was this same string, copied into four places, until it became this one.
WARNING_STYLE = "background:#ff9808; color:black; padding:6px;"

#: The other one, and it is used once: the band that says a dry run is over while this window was
#: open on it. Orange means "something here is not doing anything"; that band means the opposite,
#: that what this window does from here is real, and it must not look like the usual warning.
DANGER_STYLE = "background:#c62828; color:white; padding:6px;"


def note(text: str = "") -> QLabel:
    """A line of explanation that stays on screen, word-wrapped.

    Used sparingly. What a section means lives behind its `Hint`, where it is one sentence; what is
    left out there is in the user guide, `docs/user-guide/`.
    """
    label = QLabel(text)
    label.setWordWrap(True)
    return label


def unavailable(data: dict, key: str) -> str:
    """What is wrong with one of the projects KyprX is built on, or "" when nothing is.

    `data` is what `Groups` answers, which carries the daemon's `needs`; `key` is the project's own
    key (`"klassy"`) or the id a tab switches it by (`"krohnkite"`). A tab asks this so that a
    switch or a page with nothing to act on says so, rather than pretending.
    """
    for need in data.get("needs") or []:
        if key in (need.get("key"), need.get("plugin")) and need.get("state") != "ok":
            return str(need.get("detail") or "")
    return ""


def warning(text: str = "") -> QLabel:
    """The orange band: something is wrong, or something on screen is not doing anything."""
    label = note(text)
    label.setStyleSheet(WARNING_STYLE)
    label.setVisible(bool(text))
    return label


class NoWheel:
    """A control the mouse wheel scrolls past instead of changing.

    Measured on this desk, on the one control that had it first: every widget style here answers
    `SH_ComboBox_AllowWheelScrolling` with true -- Klassy, Breeze and Fusion alike -- so a notch of
    the wheel with the pointer merely passing over a control changes its value. That was worth one
    class while the only thing it could do was put a look on the desktop. Now that every control
    in this window applies by itself, it is worth all of them: the form pages live in a scroll
    area, and scrolling past a row of spin boxes must not set any of them.

    The focus policy goes with it: a combo's default is `WheelFocus`, which is how the wheel
    reaches it in the first place.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        event.ignore()


class Spin(NoWheel, QSpinBox):
    """A whole number, written when it settles rather than as it is typed.

    `setKeyboardTracking(False)` is the second half of live apply: with it on, typing `120` is
    three values -- 1, 12, 120 -- and each one starts the timer again. Off, the box speaks once,
    when Enter is pressed or the focus leaves.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setKeyboardTracking(False)


class DoubleSpin(NoWheel, QDoubleSpinBox):
    """The same, for a number with a fraction."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setKeyboardTracking(False)


class Choice(NoWheel, QComboBox):
    """A menu the wheel scrolls past."""


class Dot(QWidget):
    """The mark in front of a setting nothing has been written for.

    It used to be the words `· default` stuck on the end of the label, which made the label column
    change width the moment anything was written -- and with every change applying by itself, that
    is on every settled edit, so the whole form would step sideways under somebody's hands.

    What it says is unchanged and is in `UNSET`: nothing has been written for this setting, the
    value beside it is what applies, and nothing will be written until it is changed.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._on = False
        self.setFixedSize(10, 14)
        self.setToolTip(UNSET)

    def show_mark(self, on: bool) -> None:
        if on != self._on:
            self._on = on
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        if not self._on:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.palette().mid().color())
        painter.drawEllipse(QRectF(2.0, 5.0, 5.0, 5.0))
        painter.end()


class FieldLabel(QWidget):
    """One setting's name, with the dot in front of it. `label` is the part that carries text."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.dot = Dot()
        self.label = QLabel(text)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)
        row.addWidget(self.dot)
        row.addWidget(self.label)


class Hint(QWidget):
    """The mark beside a section's name, and the one sentence behind it.

    Drawn rather than asked of an icon theme, for the reason `copy_icon` records: outside a
    graphical session `QIcon.fromTheme` returns nothing at all, and that is exactly where
    `scripts/simulate.sh` looks at this window. It is also why nothing here is built at import
    time -- a `QPixmap` made before there is an application fails the import check in
    `scripts/dry-run.sh`.

    **The ink is read from the palette on every paint rather than kept.** This window repaints the
    desktop's colour scheme while it is open, so a colour taken once is the previous scheme's from
    then on.

    The sentence goes on the tooltip *and* on the accessible description, and a click shows it as
    well: a tooltip alone is mouse-only, and this is the only explanation the section has.
    """

    SIZE = 14

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._hover = False
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.WhatsThisCursor)
        self.set_hint(text)

    def set_hint(self, text: str) -> None:
        self.setToolTip(text)
        self.setAccessibleDescription(text)

    def enterEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        QToolTip.showText(event.globalPosition().toPoint(), self.toolTip(), self)

    def paintEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # The text colour thinned, and not the palette's `mid`. Measured across the schemes this
        # app ships, which is what sent me back to it: `mid` against the window is 1.8:1 on
        # Catppuccin Mocha and 1.9:1 on Latte -- the mark was drawn, was in the right place, and
        # could not be found. Thinned to 175 it is 3.4:1 at worst (Latte) and 6.0:1 on Mocha, which
        # clears the bar `scripts/dry-run.sh` holds a receding foreground to. Full text under the
        # pointer. Thinned text rather than a fixed grey because it follows the scheme both ways.
        ink = self.palette().windowText().color()
        if not self._hover:
            ink.setAlpha(175)
        unit = self.SIZE / 14.0
        painter.setPen(QPen(ink, 1.1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(1.0 * unit, 1.0 * unit, 12.0 * unit, 12.0 * unit))
        painter.setPen(QPen(ink, 1.6))
        painter.drawPoint(QPointF(7.0 * unit, 4.3 * unit))
        painter.setPen(QPen(ink, 1.3))
        painter.drawLine(QPointF(7.0 * unit, 6.4 * unit), QPointF(7.0 * unit, 10.2 * unit))
        painter.end()


class Section(QGroupBox):
    """A group box that carries its own explanation, in one sentence, beside its name.

    The mark is placed where **the style** says the title is, rather than at a measured offset:
    the widget style here is the decoration's own and draws a group box its own way.
    """

    def __init__(self, title: str, hint: str = "", parent=None):
        super().__init__(title, parent)
        self._mark = None
        if hint:
            # On the box as well as on the mark. The mark is fourteen pixels of tooltip, which the
            # keyboard cannot reach and the pointer has to find; the box is the whole section.
            self.setToolTip(hint)
            self._mark = Hint(hint, self)

    def set_hint(self, text: str) -> None:
        self.setToolTip(text)
        if self._mark is not None:
            self._mark.set_hint(text)

    def _place_mark(self) -> None:
        if self._mark is None:
            return
        option = QStyleOptionGroupBox()
        self.initStyleOption(option)
        label = self.style().subControlRect(QStyle.ComplexControl.CC_GroupBox, option,
                                            QStyle.SubControl.SC_GroupBoxLabel, self)
        self._mark.move(label.right() + 6,
                        label.center().y() - self._mark.height() // 2 + 1)
        self._mark.raise_()

    def resizeEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        super().resizeEvent(event)
        self._place_mark()

    def showEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        super().showEvent(event)
        self._place_mark()


class ColorButton(QPushButton):
    """A swatch that opens a colour picker. The value is `R,G,B`, the way the theme stores it.

    It paints its own background, which is the point of it -- and which is why it has to draw its
    own disabled state too: a widget whose background is set by hand keeps that background when
    the style greys it, so a row that had been switched off went on showing a bright colour as
    though it were still doing something.
    """

    picked = Signal()

    def __init__(self, title: str = "Colour"):
        super().__init__()
        self._value = ""
        self._title = title
        self.clicked.connect(self._pick)
        self.setMinimumWidth(120)
        self.setMaximumWidth(200)

    def changeEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        super().changeEvent(event)
        if event.type() == QEvent.Type.EnabledChange:
            self.set_value(self._value)

    def _pick(self):
        current = QColor(*[int(x) for x in self._value.split(",")]) \
            if self._value.count(",") == 2 else QColor("white")
        chosen = QColorDialog.getColor(current, self, self._title)
        if chosen.isValid():
            self.set_value(f"{chosen.red()},{chosen.green()},{chosen.blue()}")
            self.picked.emit()

    def set_value(self, value: str) -> None:
        self._value = value or ""
        if self._value.count(",") == 2:
            colour = QColor(*(int(x) for x in self._value.split(",")))
            if not self.isEnabled():
                # Most of the way to the window's own colour: still recognisably this colour, and
                # unmistakably a control that is not doing anything.
                #
                # The application's palette and not this widget's, which was measured the hard way:
                # a stylesheet that sets `background` becomes this widget's own window colour, so
                # blending towards it blended the colour towards itself and changed nothing.
                window = QGuiApplication.palette().window().color()
                colour = QColor(*(round(c * 0.3 + w * 0.7) for c, w in
                                  ((colour.red(), window.red()), (colour.green(), window.green()),
                                   (colour.blue(), window.blue()))))
            ink = "black" if colour.red() + colour.green() + colour.blue() > 380 else "white"
            self.setStyleSheet(f"background:rgb({colour.red()},{colour.green()},{colour.blue()}); "
                               f"color:{ink};")
            self.setText(self._value)
        else:
            self.setStyleSheet("")
            self.setText("choose…")

    def value(self) -> str:
        return self._value
