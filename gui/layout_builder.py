"""The pictures of a layout on the Tiling tab: a card for one, the editor that changes one, and the
row that wraps them.

`LayoutCard` draws a zone layout small, in the screen's proportions -- its zones, the number each
fills in, and the master zone washed in the window's highlight -- with its name under it and a tick
when a drag offers it. `AddCard` is the card at the end of an arrangement's row that adds the
layout for one window more, and `OfferButton` the button that says whether a drag offers a zone
layout, wearing the cards' own tick while it does (`paint_tick`). `LayoutBuilder` draws the one
being edited large, and is where a zone is chosen and a divider dragged. None of them knows what an
arrangement is or ever writes anything: the builder says what was chosen and, once the mouse is let
go, what the layout has become, and the boxes (`gui/arrangements_box.py`,
`gui/zone_layouts_box.py`) decide the rest. The shapes come from `gui/splits.py`, which is where
every rule about them lives; `FlowLayout` puts a row of cards on as many lines as the width needs,
so a long one never makes the page scroll sideways, and `tab_before` puts a row made as a box
paints where it is drawn in the keyboard's Tab order.

Nothing here is built at import time: `scripts/dry-run.sh` imports every module with no
application running, and a font or a pixmap made then fails that import.
"""

from __future__ import annotations

import copy
import re

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QIcon, QPainter, QPainterPath, QPalette,
                           QPen, QPixmap, QTextLayout, QTextOption)
from PySide6.QtWidgets import QLayout, QPushButton, QSizePolicy, QWidget

import splits

#: A card's width. A fixed one keeps a row of cards in columns, and is what the name is fitted to;
#: the picture's height follows the screen's proportions, so a layout drawn here has the shape it
#: will have on the desk -- about 70 on a 16:10 screen and 63 on a 16:9 one.
CARD_WIDTH = 120

#: Between a card's picture and its name.
CARD_GAP = 4

#: The editor's width, and its height the same way.
BUILDER_WIDTH = 336

#: Around each picture, the room its rings are drawn in -- the same gutter `Swatch` keeps.
GUTTER = 4

#: What a card's name may not carry as it is drawn: a line break or a tab, which a name typed into
#: the file by hand can hold, and which the two lines it is fitted to have no room for.
_BREAKS = re.compile(r"[\x00-\x1f\x7f]")

#: How near a divider the pointer has to be to take it, in pixels either side.
GRAB = 5


def screen_ratio(widget: QWidget | None = None) -> float:
    """Width over height of the screen the widget is on, or of the primary one before it is on
    any. Held between upright and very wide: a ratio from a screen reporting nothing is no reason
    to draw a picture a pixel high."""
    screen = widget.screen() if widget is not None else None
    screen = screen or QGuiApplication.primaryScreen()
    size = screen.size() if screen is not None else QSize(16, 9)
    ratio = size.width() / size.height() if size.height() > 0 else 16 / 9
    return max(0.5, min(3.0, ratio))


def picture_size(width: int, ratio: float) -> QSize:
    return QSize(width, max(24, round(width / ratio)))


# ---------------------------------------------------------------------- a row that wraps

class FlowLayout(QLayout):
    """Items left to right, on as many lines as the width takes -- Qt's own *Flow Layout* example.

    Qt has no such layout of its own, and a box of nine cards in a plain row asks for the width of
    nine: at the window's smallest that is wider than the page, and the page scrolls sideways for
    one row. This asks for the width of its widest item and the height its lines need at the width
    it is given.
    """

    def __init__(self, parent=None, spacing: int = 8):
        super().__init__(parent)
        self._items = []
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(spacing)

    def addItem(self, item) -> None:  # noqa: N802 -- Qt's spelling
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):  # noqa: N802 -- Qt's spelling
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):  # noqa: N802 -- Qt's spelling
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):  # noqa: N802 -- Qt's spelling
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802 -- Qt's spelling
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802 -- Qt's spelling
        return self._arrange(QRect(0, 0, width, 0), moving=False)

    def setGeometry(self, rect) -> None:  # noqa: N802 -- Qt's spelling
        super().setGeometry(rect)
        self._arrange(rect, moving=True)

    def sizeHint(self) -> QSize:  # noqa: N802 -- Qt's spelling
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802 -- Qt's spelling
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def _arrange(self, rect, moving: bool) -> int:
        margins = self.contentsMargins()
        area = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x, y, line = area.x(), area.y(), 0
        gap = self.spacing()
        for item in self._items:
            if item.widget() is not None and item.widget().isHidden():
                continue
            hint = item.sizeHint()
            if x + hint.width() > area.right() + 1 and line > 0:
                x, y, line = area.x(), y + line + gap, 0
            if moving:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + gap
            line = max(line, hint.height())
        return y + line - rect.y() + margins.bottom()


def flow_holder(spacing: int = 8) -> tuple[QWidget, FlowLayout]:
    """A widget wearing a `FlowLayout`, sized so the page asks it its height for its width."""
    holder = QWidget()
    flow = FlowLayout(holder, spacing)
    policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    policy.setHeightForWidth(True)
    holder.setSizePolicy(policy)
    return holder, flow


def tab_before(cards: list, after: QWidget) -> None:
    """Put a row of cards, in its order, straight before `after` in the keyboard's Tab order.

    Qt puts a widget at the end of its window's Tab order when it is given a parent, so a card
    made as a box paints is reached after every other control in the window, wherever it is
    drawn -- measured offscreen on the Tiling tab: every card after the last button of both boxes.
    `QWidget.setTabOrder` only puts a widget after another, so the row goes after the nearest
    control before `after` in that order: one that takes the focus at all -- given one that does
    not, on either side, `setTabOrder` does nothing (measured) -- and not a card of the row, which
    may be in its place already."""
    before = after.previousInFocusChain()
    while before is not after and (before in cards
                                   or before.focusPolicy() == Qt.FocusPolicy.NoFocus):
        before = before.previousInFocusChain()
    for first, second in zip([before, *cards], cards):
        QWidget.setTabOrder(first, second)


# ---------------------------------------------------------------------- drawing one

def paint_layout(painter: QPainter, frame: QRectF, root: dict, palette: QPalette, *,
                 gap: float, numbers: int, chosen=None) -> dict:
    """Draw a layout's zones in `frame`, and give back where each one went, by path.

    The colours are the palette's, asked for on every paint: this window repaints the desktop's
    colour scheme while it is open, so a colour taken once is the previous scheme's from then on.
    The zone the windows fill first is washed with the highlight -- the master zone -- and every
    zone carries its number in that order, which is the one thing about a layout its shape does
    not show. `numbers` is the largest the numbers are drawn, in pixels; `chosen` is a zone's
    path to ring.
    """
    width, height = round(frame.width()), round(frame.height())
    placed = splits.zone_rects(root, width, height)
    order = splits.fill_order(root)
    base = palette.color(QPalette.ColorRole.Base)
    edge = palette.color(QPalette.ColorRole.Mid)
    text = palette.color(QPalette.ColorRole.Text)
    wash = QColor(palette.color(QPalette.ColorRole.Highlight))
    wash.setAlpha(110)
    font = QFont(painter.font())
    drawn: dict[tuple, QRectF] = {}
    for path, (x, y, w, h) in placed.items():
        box = QRectF(frame.x() + x + gap / 2, frame.y() + y + gap / 2,
                     max(1.0, w - gap), max(1.0, h - gap))
        drawn[path] = box
        radius = min(4.0, box.width() / 4, box.height() / 4)
        painter.setPen(QPen(edge, 1))
        painter.setBrush(base)
        painter.drawRoundedRect(box, radius, radius)
        if path == order[0]:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(wash)
            painter.drawRoundedRect(box, radius, radius)
        size = min(numbers, box.width() * 0.55, box.height() * 0.55)
        if size >= 6:
            font.setPixelSize(round(size))
            painter.setFont(font)
            painter.setPen(text)
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, str(order.index(path) + 1))
    if chosen is not None and chosen in drawn:
        painter.setPen(QPen(palette.color(QPalette.ColorRole.Highlight), 2.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(drawn[chosen].adjusted(-1, -1, 1, 1), 4, 4)
    return drawn


#: The tick's size, in pixels, on a card's picture and on *Offer on drag* alike.
TICK = 14


def paint_tick(painter: QPainter, palette: QPalette, badge: QRectF) -> None:
    """The tick that says a drag offers a zone layout, filling `badge`: a check in the colour a
    scheme gives text on a selection, on the selection's own colour -- a pair the scheme sets to be
    read together. Drawn rather than written, for the reason `Hint` draws its mark: a check
    character is in some fonts and not in others. The same badge on a card's picture and on
    *Offer on drag* (`OfferButton`), so the two read as one thing."""
    size = badge.width()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(palette.color(QPalette.ColorRole.Highlight))
    painter.drawEllipse(badge)
    pen = QPen(palette.color(QPalette.ColorRole.HighlightedText), 1.6 * size / TICK)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    check = QPainterPath(QPointF(badge.x() + size * 0.28, badge.y() + size * 0.52))
    check.lineTo(QPointF(badge.x() + size * 0.44, badge.y() + size * 0.68))
    check.lineTo(QPointF(badge.x() + size * 0.73, badge.y() + size * 0.34))
    painter.drawPath(check)


class LayoutCard(QPushButton):
    """One zone layout as a card: its picture, its name under it, and a tick when a drag offers it.

    Drawn the way `Swatch` draws a preset, and for its reasons: ringed when it is the one chosen,
    washed under the pointer, ringed thinly where the keyboard is, and the same card faintly when
    it cannot be chosen -- no invented grey, because what is unavailable is still this layout.

    The name is fitted to the card's width on two lines at most, the second cut short with an
    ellipsis when the name is longer, and drawn by the painter, which shows it as it is spelled.
    The whole of it, and what the card is read out as, are the caller's to give (`show_layout`): a
    card in a row of arrangements names a number of windows, and one in the pool does not.
    """

    def __init__(self, ratio: float = 16 / 9, parent=None):
        super().__init__(parent)
        self.root: dict = {}
        self.title = ""
        self.drag = False
        self._hover = False
        self._ratio = ratio
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fit()

    def set_ratio(self, ratio: float) -> None:
        if ratio != self._ratio:
            self._ratio = ratio
            self._fit()

    def _picture(self) -> QSize:
        return picture_size(CARD_WIDTH - 2 * GUTTER, self._ratio)

    def _fit(self) -> None:
        """Fixed in both directions: as wide as every card, and as tall as the picture and two
        lines of the font in force -- which is why it is worked out again when the font changes."""
        lines = 2 * self.fontMetrics().lineSpacing()
        self.setFixedSize(CARD_WIDTH, GUTTER + self._picture().height() + CARD_GAP + lines + GUTTER)
        self.update()

    def show_layout(self, root: dict, title: str, *, drag: bool = False, tip: str = "",
                    accessible: str = "") -> None:
        """Show this layout under this name. `tip` is the tooltip as it is to be set -- a name in
        it made plain first (`tiling_value.plain_tip`) -- and `accessible` what the card is read
        out as, the title when it is not given."""
        self.root = root
        self.title = title
        self.drag = drag
        self.setToolTip(tip)
        self.setAccessibleName(accessible or title)
        self.setAccessibleDescription("Offered when a window is dragged." if drag else "")
        self.update()

    def lines(self) -> list[str]:
        """The name as it is drawn: the lines it wraps to at the picture's width, two at most, the
        second ending in an ellipsis when the rest does not fit on it."""
        width = self._picture().width()
        text = _BREAKS.sub(" ", self.title)
        layout = QTextLayout(text, self.font())
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        layout.setTextOption(option)
        spans: list[tuple[int, int]] = []
        layout.beginLayout()
        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(width)
            spans.append((line.textStart(), line.textLength()))
        layout.endLayout()
        # Qt counts a line's start and length in UTF-16 units, and Python a string in code points:
        # cut by Qt's count, a name with a character from beyond the first 65536 -- an emoji --
        # would lose a letter at every line after it.
        units = text.encode("utf-16-le")

        def piece(start: int, length: int | None = None) -> str:
            end = len(units) if length is None else 2 * (start + length)
            return units[2 * start:end].decode("utf-16-le", errors="ignore").strip()

        if len(spans) <= 2:
            return [piece(*span) for span in spans]
        rest = piece(spans[1][0])
        return [piece(*spans[0]),
                self.fontMetrics().elidedText(rest, Qt.TextElideMode.ElideRight, width)]

    def changeEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        super().changeEvent(event)
        if event.type() == QEvent.Type.FontChange:
            self._fit()

    def enterEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self.palette()
        if not self.isEnabled():
            painter.setOpacity(0.40)
        picture = self._picture()
        frame = QRectF(GUTTER, GUTTER, picture.width(), picture.height())
        self._paint_picture(painter, palette, frame)
        # The card's own font again: `paint_layout` leaves the painter with the numbers' size.
        painter.setFont(self.font())
        painter.setPen(palette.color(QPalette.ColorRole.WindowText))
        step = self.fontMetrics().lineSpacing()
        for i, line in enumerate(self.lines()):
            painter.drawText(QRectF(GUTTER, frame.bottom() + CARD_GAP + i * step,
                                    picture.width(), step),
                             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, line)
        whole = QRectF(1.5, 1.5, self.width() - 3.0, self.height() - 3.0)
        if self._hover and self.isEnabled():
            wash = QColor(palette.color(QPalette.ColorRole.Text))
            wash.setAlpha(48 if self.isDown() else 28)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(wash)
            painter.drawRoundedRect(whole, 6, 6)
        if self.isChecked():
            painter.setPen(QPen(palette.color(QPalette.ColorRole.Highlight), 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(whole, 6, 6)
        if self.hasFocus():
            painter.setOpacity(1.0)
            painter.setPen(QPen(palette.color(QPalette.ColorRole.Highlight), 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0),
                                    7, 7)
        painter.end()

    def _paint_picture(self, painter: QPainter, palette: QPalette, frame: QRectF) -> None:
        """The picture: the screen, the layout's zones on it, and the tick in its corner when a
        drag offers it. The name, the rings and the wash are the card's whatever its picture is
        (`AddCard` draws another)."""
        screen = QColor(palette.color(QPalette.ColorRole.Mid))
        screen.setAlpha(90)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(screen)
        painter.drawRoundedRect(frame, 4, 4)
        paint_layout(painter, frame.adjusted(2, 2, -2, -2), self.root, palette, gap=2.0,
                     numbers=11)
        if self.drag:
            paint_tick(painter, palette,
                       QRectF(frame.right() - TICK - 2, frame.top() + 2, TICK, TICK))


class AddCard(LayoutCard):
    """The card at the end of an arrangement's row of layouts: the layout for one window more.

    A card and not a button under the row, so that what adds a layout stands where the layout will
    be -- the same size, ringed while the layout for that many windows is being chosen, washed under
    the pointer, in the keyboard's Tab order after the last layout. Its picture is the screen's
    outline, dashed, with a plus in it; its name is the number of windows it adds the layout for
    (`set_count`), and it is read out as what it does."""

    def set_count(self, count: int, tip: str = "") -> None:
        """Add the layout for `count` windows; `tip` is its tooltip as it is to be set."""
        self.show_layout({}, splits.windows(count), tip=tip,
                         accessible=f"Add the layout for {splits.windows(count)}")

    def _paint_picture(self, painter: QPainter, palette: QPalette, frame: QRectF) -> None:
        edge = palette.color(QPalette.ColorRole.Mid)
        pen = QPen(edge, 1.5, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(frame.adjusted(1, 1, -1, -1), 4, 4)
        reach = min(frame.width(), frame.height()) * 0.18
        middle = frame.center()
        plus = QPen(palette.color(QPalette.ColorRole.WindowText), 2.0)
        plus.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(plus)
        painter.drawLine(QPointF(middle.x() - reach, middle.y()),
                         QPointF(middle.x() + reach, middle.y()))
        painter.drawLine(QPointF(middle.x(), middle.y() - reach),
                         QPointF(middle.x(), middle.y() + reach))


class OfferButton(QPushButton):
    """*Offer on drag*: whether a drag offers the zone layout selected, as a button that stays down
    while it does, with the cards' own tick beside its words (`paint_tick`).

    A button among the box's buttons rather than a tick box beside the builder, so that what puts a
    zone layout in the bar a drag shows sits with what adds, copies and orders one. The icon is set
    by hand on every change -- the tick while it is down, and a clear picture of the same size while
    it is up, so the words never move -- rather than left to a `QIcon`'s on and off states, which
    each style reads its own way. And painted again when the palette changes, for the reason
    `paint_layout` reads its colours on every paint: this window repaints the desktop's colour
    scheme while it is open. And painted again when its window gains or loses the focus, as the
    cards' ticks are, in the colours `QWidget.palette` would answer: the active ones while the
    button is not shown yet, since it is shown in a window that has the focus. The window comes as
    `WindowActivate` and `WindowDeactivate` to a widget inside it: measured offscreen, a button in
    a window was sent those two and never `ActivationChange`, which goes to the window alone.

    **The tick is drawn in the colours of a button that can be pressed**, whatever this one is at
    the time: the style greys the icon of a greyed button itself, and a tick drawn in the greyed
    colours stays grey once the button is not. Measured offscreen: on the box's first paint after
    a reading the button is set before it is enabled, and the badge drawn from its palette then --
    a greyed widget's palette answers in its disabled colours -- stayed grey on a button that was
    not."""

    def __init__(self, parent=None):
        super().__init__("Offer on drag", parent)
        self.setCheckable(True)
        # Room for the badge and a pixel round it, as on a card's picture.
        self.setIconSize(QSize(TICK + 2, TICK + 2))
        self.toggled.connect(self._paint_icon)
        self._paint_icon()

    def set_offered(self, on: bool) -> None:
        self.setChecked(bool(on))
        self._paint_icon()

    def _paint_icon(self, *_) -> None:
        ratio = max(1.0, self.devicePixelRatioF())
        size = self.iconSize()
        picture = QPixmap(round(size.width() * ratio), round(size.height() * ratio))
        picture.setDevicePixelRatio(ratio)
        picture.fill(Qt.GlobalColor.transparent)
        if self.isChecked():
            palette = QPalette(self.palette())
            palette.setCurrentColorGroup(
                QPalette.ColorGroup.Active if not self.isVisible() or self.isActiveWindow()
                else QPalette.ColorGroup.Inactive)
            painter = QPainter(picture)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            paint_tick(painter, palette, QRectF((size.width() - TICK) / 2,
                                                (size.height() - TICK) / 2, TICK, TICK))
            painter.end()
        self.setIcon(QIcon(picture))

    def changeEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self._paint_icon()

    def event(self, event) -> bool:
        if event.type() in (QEvent.Type.WindowActivate, QEvent.Type.WindowDeactivate):
            self._paint_icon()
        return super().event(event)


# ---------------------------------------------------------------------- the editor

class LayoutBuilder(QWidget):
    """The layout being edited, large: choose a zone, drag a divider.

    **Nothing leaves it while the mouse is down.** A drag redraws the layout under the pointer and
    says where the divider is (`moving`), but the layout it has become is said once, when the
    button is let go (`edited`) -- so a drag is one change, the way a run along a spin box is one
    write. Esc during the drag puts back the layout it started from and is kept from the window,
    which closes on Esc: what Esc means in the middle of a drag is *not this*, not *close*.

    While a button is held on it, it is `held`, which the tab counts as busy (`TilingValue.hold`):
    the page does not repaint under somebody's hands, and repaints the moment they are lifted
    (`released`).
    """

    #: A zone was chosen: its path.
    zone_chosen = Signal(object)
    #: A divider was chosen: its split's path and its index in that split.
    divider_chosen = Signal(object, int)
    #: The layout as a drag has it now, for whatever shows the divider's number.
    moving = Signal(object)
    #: A drag ended somewhere else than it began: the layout it made.
    edited = Signal(object)
    #: The mouse button is up again, or a drag was called off.
    released = Signal()
    #: The menu for a zone was asked for, at this point on the screen.
    menu_wanted = Signal(object, QPoint)

    def __init__(self, ratio: float = 16 / 9, parent=None):
        super().__init__(parent)
        self.root: dict = {}
        self.read_only = True
        self.zone = ()
        self.divider: tuple | None = None
        self.held = False
        self._drag: dict | None = None
        self._hovered: tuple | None = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.set_ratio(ratio)

    # ---------------------------------------------------------------- what it shows

    def set_ratio(self, ratio: float) -> None:
        picture = picture_size(BUILDER_WIDTH, ratio)
        self.setFixedSize(picture.width() + 2 * GUTTER, picture.height() + 2 * GUTTER)
        self.update()

    def set_layout(self, root: dict, read_only: bool, zone=None, divider=None,
                   accessible: str = "") -> None:
        """Show this layout, with a zone and a divider chosen -- the ones asked for when it still
        has them, its master zone and that zone's divider when it does not. A drag under way is
        called off: what it was dragging may not be there any more. `accessible` is what the
        builder is read out as -- the layout's name, which only the caller knows."""
        if self._drag is not None:
            self._end_drag(say=False)
        self.root = root
        self.read_only = read_only
        self.zone = tuple(zone) if splits.is_zone_path(root, zone) else splits.fill_order(root)[0]
        self.divider = divider if self._has_divider(divider) else self._divider_beside(self.zone)
        self._hovered = None
        self.setAccessibleName(accessible or "A zone layout")
        self.update()

    def _frame(self) -> QRectF:
        return QRectF(GUTTER, GUTTER, self.width() - 2 * GUTTER, self.height() - 2 * GUTTER)

    def _size(self) -> tuple[int, int]:
        frame = self._frame()
        return round(frame.width()), round(frame.height())

    def _has_divider(self, divider) -> bool:
        if not divider or self.read_only:
            return False
        path, index = divider
        if not splits.has_path(self.root, path):
            return False
        node = splits.node_at(self.root, path)
        return not splits.is_zone(node) and 0 <= index < len(node["parts"]) - 1

    def _divider_beside(self, zone: tuple):
        """A zone's own divider: the one after it in its split, or the one before when it is
        the last part. What the box's number edits until a divider is chosen."""
        if self.read_only or not zone:
            return None
        parent = splits.node_at(self.root, zone[:-1])
        index = zone[-1]
        return (zone[:-1], index if index < len(parent["parts"]) - 1 else index - 1)

    # ---------------------------------------------------------------- where the pointer is

    def _local(self, position) -> QPointF:
        point = QPointF(position)
        return point - self._frame().topLeft()

    def _divider_at(self, position):
        """The divider under the pointer, the nearest when two are close, the deeper on a tie --
        a divider inside a part is shorter and harder to hit than the one beside it."""
        if self.read_only:
            return None
        point = self._local(position)
        best = None
        for path, index, direction, at, low, high in splits.edges(self.root, *self._size()):
            along, across = (point.x(), point.y()) if direction == "h" else (point.y(), point.x())
            distance = abs(along - at)
            if distance <= GRAB and low <= across <= high:
                rank = (distance, -len(path))
                if best is None or rank < best[0]:
                    best = (rank, (path, index, direction))
        return best[1] if best else None

    def _zone_at(self, position):
        point = self._local(position)
        for path, (x, y, w, h) in splits.zone_rects(self.root, *self._size()).items():
            if x <= point.x() < x + w and y <= point.y() < y + h:
                return path
        return None

    # ---------------------------------------------------------------- the mouse

    def mousePressEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        if event.button() != Qt.MouseButton.LeftButton or not self.isEnabled():
            super().mousePressEvent(event)
            return
        self.held = True
        position = event.position()
        found = self._divider_at(position)
        if found is not None:
            path, index, direction = found
            self.divider = (path, index)
            self.divider_chosen.emit(path, index)
            self._start_drag(path, index, direction)
        else:
            zone = self._zone_at(position)
            if zone is not None:
                self.zone = zone
                self.divider = self._divider_beside(zone)
                self.zone_chosen.emit(zone)
        self.update()

    def _start_drag(self, path: tuple, index: int, direction: str) -> None:
        """Remember where the drag began, measured once: the pair of parts the divider sits
        between, in the layout as it was. Measured against that and not against the layout as
        the drag reshapes it, so the divider follows the pointer rather than its own last step."""
        zone_rect, split_rect = splits.layout_rects(self.root, *self._size())
        part = path + (index,)
        x, y, w, h = zone_rect.get(part) or split_rect[part]
        sx, sy, sw, sh = split_rect[path]
        side = direction == "h"
        self._drag = {"path": path, "index": index, "side": side,
                      "start": x if side else y, "length": sw if side else sh,
                      "base": copy.deepcopy(self.root)}
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.grabKeyboard()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        position = event.position()
        drag = self._drag
        if drag is None:
            found = self._divider_at(position)
            hovered = found[:2] if found else None
            if hovered != self._hovered:
                self._hovered = hovered
                self.update()
            if found is None:
                self.unsetCursor()
            else:
                self.setCursor(Qt.CursorShape.SplitHCursor if found[2] == "h"
                               else Qt.CursorShape.SplitVCursor)
            return
        point = self._local(position)
        along = point.x() if drag["side"] else point.y()
        if drag["length"] <= 0:
            return
        share = splits.nearest((along - drag["start"]) * 100 / drag["length"])
        moved = splits.move_divider(drag["base"], drag["path"], drag["index"], share)
        if moved != self.root:
            self.root = moved
            self.moving.emit(moved)
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return
        drag = self._drag
        if drag is not None:
            self._drag = None
            self.releaseKeyboard()
            # Said before `released`, and the order is the point: the box takes the new layout
            # and queues it first, so whatever was owed while the button was down comes after
            # the edit rather than painting over it.
            if self.root != drag["base"]:
                self.edited.emit(copy.deepcopy(self.root))
        self.held = False
        self.update()
        self.released.emit()

    def keyPressEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        if self._drag is not None and event.key() == Qt.Key.Key_Escape:
            self._end_drag()
            event.accept()
            return
        super().keyPressEvent(event)

    def _end_drag(self, say: bool = True) -> None:
        """Call a drag off: the layout it started from is back, and nothing was edited. `say`
        is false when the caller is about to show another layout anyway, and no listener should
        hear about the one going."""
        drag = self._drag
        self._drag = None
        self.releaseKeyboard()
        if drag is not None:
            self.root = drag["base"]
            if say:
                self.moving.emit(copy.deepcopy(self.root))
        was_held = self.held
        self.held = False
        self.update()
        if was_held and say:
            self.released.emit()

    def hideEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        # A drag the window can no longer see the end of is called off rather than left holding
        # the page busy until a release that will not come here.
        if self._drag is not None or self.held:
            self._end_drag()
        super().hideEvent(event)

    def focusOutEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        # The same for a window that loses the keyboard with the button still down -- another
        # window taken to the front -- which may never hear the button come up.
        if self._drag is not None or self.held:
            self._end_drag()
        super().focusOutEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        zone = self._zone_at(QPointF(event.pos()))
        if zone is None or not self.isEnabled() or self._drag is not None:
            return
        self.zone = zone
        self.divider = self._divider_beside(zone)
        self.zone_chosen.emit(zone)
        self.update()
        self.menu_wanted.emit(zone, event.globalPos())

    def leaveEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        if self._hovered is not None:
            self._hovered = None
            self.update()
        super().leaveEvent(event)

    # ---------------------------------------------------------------- painting

    def paintEvent(self, event) -> None:  # noqa: N802 -- Qt's spelling
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self.palette()
        if not self.isEnabled():
            painter.setOpacity(0.40)
        frame = self._frame()
        screen = QColor(palette.color(QPalette.ColorRole.Mid))
        screen.setAlpha(90)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(screen)
        painter.drawRoundedRect(frame, 6, 6)
        paint_layout(painter, frame, self.root, palette, gap=8.0, numbers=26,
                     chosen=self.zone if self.isEnabled() else None)
        if not self.read_only:
            self._paint_dividers(painter, palette, frame)
        painter.end()

    def _paint_dividers(self, painter: QPainter, palette: QPalette, frame: QRectF) -> None:
        """A grip in the middle of each divider, so it reads as something to take hold of; the
        chosen one, the one under the pointer and the one being dragged in the highlight."""
        idle = palette.color(QPalette.ColorRole.Mid)
        lit = palette.color(QPalette.ColorRole.Highlight)
        dragged = (self._drag["path"], self._drag["index"]) if self._drag else None
        for path, index, direction, at, low, high in splits.edges(self.root, *self._size()):
            which = (path, index)
            on = which in (self.divider, self._hovered, dragged)
            middle = (low + high) / 2
            reach = min(14.0, (high - low) / 3)
            if direction == "h":
                start = QPointF(frame.x() + at, frame.y() + middle - reach)
                end = QPointF(frame.x() + at, frame.y() + middle + reach)
            else:
                start = QPointF(frame.x() + middle - reach, frame.y() + at)
                end = QPointF(frame.x() + middle + reach, frame.y() + at)
            pen = QPen(lit if on else idle, 4 if on else 3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(start, end)
