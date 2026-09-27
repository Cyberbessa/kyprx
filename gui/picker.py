"""The wallpaper picker, in two layouts.

Kept apart from the settings window for the reason the cheatsheet is: it shares almost nothing with
a settings form. One read, a window, and drawing code.

**Strip** is a column of narrow cards beside one big picture, inside a panel wearing the
decoration's own background, corner and outline. **Pages** has no panel at all: the window is
transparent, the chosen wallpaper sits large in the middle of the screen, and the rest lean away
behind it -- the ones before it to the left, the ones after it to the right -- like pages of a book
held open. Which one the key opens is a setting.

The window is the cheatsheet's window in every respect that was measured -- frameless, fixed size
so the tiler leaves it alone, placed by a rule because a Wayland client cannot place itself -- with
one deliberate difference. **The size does not come from `sizeHint()`.** A list of shortcuts has one
right size; a list of wallpapers does not, and a folder of two hundred videos would ask for a window
forty screens wide. So the size comes from the screen.

**Nothing is applied until Enter or a click.** Moving the selection redraws this window and touches
the desktop not at all, which is what makes Escape mean what it says.
"""

from __future__ import annotations

import math
import os
import sys
import threading
import time
from collections import OrderedDict

from PySide6.QtCore import QObject, QPointF, QRectF, QSize, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QImage, QPainter, QPen, QPixmap,
                           QPolygonF, QRegion, QTransform)
from PySide6.QtWidgets import QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

import thumbs
from cheatsheet import card_look, card_style

#: The picker's title. The compositor is told where to put this window by matching on the class,
#: and the daemon holds the same title string -- the two must not drift. See
#: `daemon/kyprd_names.py:WALLPAPER_TITLE`. **Both layouts use it**: they are one window with two ways of
#: drawing, not two windows, so the placement rule covers both without knowing either.
TITLE = "KyprX wallpapers"

#: How long a selection has to stand still before the full-size picture is decoded. Holding an
#: arrow key down otherwise queues one decode of a very large image per repeat.
SETTLE_MS = 110

#: How many pictures are decoded at once. Two: a decode is a core's worth of work and the window
#: has to keep drawing beside them; ffmpeg threads itself.
THUMB_WORKERS = 2

#: How many full-size pictures are kept once decoded, most recent last. Arrowing back to one you
#: were just looking at reads this rather than decoding again; eight of them at this desk's card
#: size are about 24 MB, for an overlay that lives a few seconds.
BIG_KEPT = 8

#: How many pages, drawn leaning and ready to copy, the Pages layout keeps. Ten are on screen at
#: once; the rest is slack for arrowing back. About 2.5 MB each at this desk's size and scale.
RENDERS_KEPT = 16

#: Set in the environment to have every paint print how long it took, on stderr. The number this
#: layout is measured by -- see `PagesPicker.paintEvent`.
PAINT_TIMES = bool(os.environ.get("KYPRX_PAINT_TIMES"))


class _Bridge(QObject):
    """The signals a worker thread hands a decoded picture back through.

    A `QObject` living on the window's thread, so an emit from a worker is queued and the slot
    runs where the pixmap can be made. Its own object rather than signals on the window, because
    a `QWidget` subclass cannot grow signals after the fact without a metaclass argument.
    """

    thumb_done = Signal(int, QImage)
    big_done = Signal(int, QImage)


class Picker(QWidget):
    """What both layouts are, which is everything except the drawing.

    The list, where in it you are, the queue that builds thumbnails one per turn of the event loop,
    the keys, the applying, the fixed size, the closing. A layout adds a body and a way to paint;
    it adds nothing else, and that is deliberate -- every one of the things above was measured
    once, and a second copy of any of them is a second thing to get wrong.
    """

    def __init__(self, client, data: dict):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle(TITLE)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.c = client
        self.look = card_look(client)
        self.entries: list[dict] = data.get("entries") or []
        self.pictures: list[QPixmap | None] = [None] * len(self.entries)
        self.index = self._start_at(data.get("current", ""))
        self.trouble = self._trouble(data)
        self.hint = self._hint(data)
        self._busy = False
        self._big: tuple[int, QPixmap] | None = None
        #: The decoding, none of it on this thread: the bridge the workers answer through, which
        #: positions are being decoded right now, the full-size pictures kept, which one is
        #: wanted next and whether one is being made, and the flag that tells every worker the
        #: window is gone.
        self._bridge = _Bridge(self)
        self._bridge.thumb_done.connect(self._on_thumb)
        self._bridge.big_done.connect(self._on_big)
        self._pool = QThreadPool.globalInstance()
        self._pool.setMaxThreadCount(THUMB_WORKERS)
        self._inflight: set[int] = set()
        self._bigs: OrderedDict[int, QPixmap] = OrderedDict()
        self._big_wanted: int | None = None
        self._big_running = False
        self._closing = False
        self._cancel = threading.Event()

        self.setFixedSize(self._window_size())
        self._build()

        self._settle = QTimer(self)
        self._settle.setSingleShot(True)
        self._settle.setInterval(SETTLE_MS)
        self._settle.timeout.connect(self._decode_big)

        self._queue = self._fill_order()
        self._show()
        QTimer.singleShot(0, self._fill_pump)
        # The one in front at open gets its full-size picture and its colour the same way a
        # selection that stops does, rather than waiting for the first key. Also what lets the
        # simulation reach the settle at all: it opens the picker and never moves, and a fault on
        # that path stayed out of its reach until it was found on screen.
        self._settle.start()

    # ---------------------------------------------------------------- what a layout provides

    def _window_size(self) -> QSize:
        raise NotImplementedError

    def _build(self) -> None:
        """Put the body together. A layout that paints everything itself has nothing to do here."""

    def _show(self) -> None:
        """Draw whatever has to change when the selection moves."""
        self.update()

    def _thumb_ready(self, position: int) -> None:
        self.update()

    def _big_ready(self) -> None:
        self.update()

    def _page_step(self) -> int:
        return 1

    def _at(self, point: QPointF) -> int | None:
        """Which wallpaper is under this point, or None for none of them."""
        return None

    def _say(self, text: str) -> None:
        self.trouble = text
        self.update()

    # ---------------------------------------------------------------- the list

    def _start_at(self, current: str) -> int:
        for position, entry in enumerate(self.entries):
            if entry.get("target") == current:
                return position
        return 0

    def _trouble(self, data: dict) -> str:
        """The line the picker carries over its pictures, when it has something to say.

        A dry run is always something to say. The picker closes on Enter exactly as it does for
        real, and with no band of its own a wallpaper that was only written down looked chosen.
        """
        if data.get("trouble"):
            said = str(data["trouble"])
        elif not self.entries:
            said = "nothing to choose from"
        elif data.get("rotates"):
            said = ("the video plugin is set to change the wallpaper on its own, "
                    "so this one will not stay")
        else:
            said = ""
        if self.c.dry_run():
            dry = "dry run: a wallpaper chosen here is written down, not put up"
            return f"{dry} -- {said}" if said else dry
        return said

    @staticmethod
    def _hint(data: dict) -> str:
        mode = "video" if data.get("mode") == "video" else "image"
        return (f"{len(data.get('entries') or [])} {mode}(s) — "
                f"arrows to move, Enter to set, Esc to leave")

    def _fill_order(self) -> list[int]:
        """Which thumbnails to build first: the selection, then outwards from it.

        The window is drawn before any of them exist, so what matters is that the cards somebody is
        looking at fill in first. Starting at the top of a list of seventy fills the far end while
        the near end is still empty -- and in Pages the far end is not even on screen.

        Bounded at both ends, and the upper one is not decoration. `left` starts at the selection
        and used to be checked only against zero, so with **nothing to choose from** it began at 0,
        appended 0, and the fill indexed an empty list. Measured the way these things are: the
        picker opened in video mode against a folder with no videos in it, and the overlay died on
        its own before drawing anything.
        """
        order = []
        left, right = min(self.index, len(self.entries) - 1), self.index + 1
        while left >= 0 or right < len(self.entries):
            if left >= 0:
                order.append(left)
                left -= 1
            if right < len(self.entries):
                order.append(right)
                right += 1
        return order

    def _fill_pump(self) -> None:
        """Hand the next thumbnails to the workers, as many as there are workers.

        Nothing is decoded on this thread. It used to be one thumbnail per turn of the event loop,
        which kept the window answering but not drawing smoothly: measured, 2.4 ms each from the
        cache and 130 to 176 ms each for a PNG the first time, taken out of the frames the window
        was trying to paint, plus a whole ffmpeg for a video. The queue's order is still
        `_fill_order`'s, and `_select` still moves the selection to its head.
        """
        while self._queue and len(self._inflight) < THUMB_WORKERS and not self._closing:
            position = self._queue.pop(0)
            if self.pictures[position] is not None or position in self._inflight:
                continue
            self._inflight.add(position)
            entry = self.entries[position]
            self._pool.start(lambda p=position, e=entry: self._thumb_work(p, e))

    def _thumb_work(self, position: int, entry: dict) -> None:
        """On a worker: decode, and hand back a `QImage` -- never a pixmap, never a widget."""
        image = None if self._closing else thumbs.thumbnail_image(entry, self._cancel)
        self._bridge.thumb_done.emit(position, image if image is not None else QImage())

    def _on_thumb(self, position: int, image: QImage) -> None:
        self._inflight.discard(position)
        if self._closing:
            return
        self.pictures[position] = None if image.isNull() else QPixmap.fromImage(image)
        self._thumb_ready(position)
        self._fill_pump()

    def _decode_big(self) -> None:
        """The full-size picture of what is selected, decoded once the selection has settled.

        And, first, the colour of it — asked for here because this is the moment it becomes worth
        knowing and there is nothing waiting on the answer. The daemon works it out beside its own
        loop, so by the time Enter is pressed the colour is a file read. Without it, the work
        happens after the picker has closed, with ffmpeg running for up to a second and a half on
        a video while the desktop is already being recoloured.

        The picture is decoded on a worker too, and the thumbnail stands in for it until it lands
        -- measured on this desk, 94 to 177 ms for a PNG, which used to be 94 to 177 ms with the
        window frozen. The last few decoded are kept, so arrowing back is instant.
        """
        if not self.entries:
            return
        self.c.prepare_colour(self.entries[self.index].get("target", ""))
        kept = self._bigs.get(self.index)
        if kept is not None:
            self._bigs.move_to_end(self.index)
            self._big = (self.index, kept)
            self._big_ready()
            return
        self._big_wanted = self.index
        self._big_pump()

    def _big_pump(self) -> None:
        """One full-size decode at a time, and the one wanted is whatever was asked for last."""
        if self._big_running or self._big_wanted is None or self._closing:
            return
        position, self._big_wanted = self._big_wanted, None
        self._big_running = True
        entry, wanted = self.entries[position], self._big_width()
        # Ahead of the thumbnails: the one somebody is looking at is worth more than the ones
        # off to the side, and a queued job with a higher priority runs next.
        self._pool.start(lambda: self._big_work(position, entry, wanted), 1)

    def _big_work(self, position: int, entry: dict, wanted: int) -> None:
        image = None if self._closing else thumbs.preview_image(entry, wanted, self._cancel)
        self._bridge.big_done.emit(position, image if image is not None else QImage())

    def _on_big(self, position: int, image: QImage) -> None:
        self._big_running = False
        if self._closing:
            return
        if not image.isNull():
            picture = QPixmap.fromImage(image)
            self._bigs[position] = picture
            self._bigs.move_to_end(position)
            while len(self._bigs) > BIG_KEPT:
                self._bigs.popitem(last=False)
            if position == self.index:
                self._big = (position, picture)
                self._big_ready()
        self._big_pump()

    def _big_width(self) -> int:
        """In device pixels, not logical ones: at a fractional scale a picture decoded to the
        card's logical width was drawn a fifth larger than it was, and looked it. The pixmap
        carries no device-pixel ratio of its own on purpose -- `thumbs.crop_box` and the draw
        both work in the pixmap's own pixels, and a ratio on the source would scale it twice."""
        return round(max(self.width(), 400) * self.devicePixelRatioF())

    def front_picture(self) -> QPixmap | None:
        """The best picture there is for what is selected right now.

        The big one when it has been decoded for *this* selection, and the thumbnail until then --
        which is what keeps the window from flashing empty while an arrow key is held down.
        """
        if self._big is not None and self._big[0] == self.index:
            return self._big[1]
        return self.pictures[self.index] if self.entries else None

    # ---------------------------------------------------------------- choosing

    def _select(self, position: int) -> None:
        if not self.entries:
            return
        self.index = max(0, min(position, len(self.entries) - 1))
        # And it jumps the queue. The order was worked out once, from where the window opened;
        # twenty presses later the selection is somewhere the queue has not reached yet, and
        # waiting for it to crawl there is a hole in the middle of the screen.
        if self.pictures[self.index] is None and self.index in self._queue:
            self._queue.remove(self.index)
            self._queue.insert(0, self.index)
        self._show()
        self._settle.start()

    def _apply(self) -> None:
        """Set this one, and be off the screen before anything happens because of it.

        The call itself is answered in about six milliseconds, measured -- everything the daemon
        does for it is a read, and the rest is deferred. What takes time is what follows: a quarter
        of a second later the daemon starts the change, and the compositor then stops the screen
        for well over a second while it rebuilds its colours. None of that is meant to be watched
        through a picker.

        **So the window is hidden the moment the answer is yes, and closed afterwards -- and
        `_busy` stays up until it is hidden.** The order matters twice over. Closing waits for the
        decoders to stop (`closeEvent`, up to a second and a half), so a picker that merely closed
        was still on screen when the compositor stopped, and the pause read as the key not having
        been taken. And hiding takes the focus away, which delivers `focusOutEvent` from *inside*
        `hide()`, before the window has left the screen -- with `_busy` already down that event
        closed the window, and the very wait hiding was meant to bury ran in plain view, with the
        window still mapped. Traced with the interface offscreen: `closeEvent` ran with
        `isVisible()` still true. Kept up, `_busy` makes the focus-out a no-op; the surface goes
        first, the wait happens behind nothing.

        A refusal hides nothing, which is the other half of the same care: the window stays, with
        the focus it had, and says what went wrong.
        """
        if self._busy or not self.entries:
            return
        self._busy = True
        entry = self.entries[self.index]
        self._say(f"setting {entry.get('name', '')}…")
        ok = self.c.set_wallpaper(entry.get("target", ""))
        if ok:
            self.hide()
            QGuiApplication.processEvents()
            self.close()
            # And end the process here rather than leaving it to `quitOnLastWindowClosed`: a
            # window hidden a moment ago is not the last *visible* one closing, and a picker left
            # running invisibly is the next Meta+R closing something nobody can see.
            QGuiApplication.quit()
            return
        # Staying open is the point. A picker that closed on a failure nobody read is a wallpaper
        # that silently did not change.
        self._busy = False
        self._say(f"could not set {entry.get('name', '')} — see the daemon's log")

    # ---------------------------------------------------------------- keys, mouse and focus

    def keyPressEvent(self, event):  # noqa: N802 — Qt's spelling
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.close()
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_Down):
            self._select(self.index + 1)
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Up):
            self._select(self.index - 1)
        elif key == Qt.Key.Key_Home:
            self._select(0)
        elif key == Qt.Key.Key_End:
            self._select(len(self.entries) - 1)
        elif key in (Qt.Key.Key_PageDown, Qt.Key.Key_PageUp):
            step = self._page_step()
            self._select(self.index + (step if key == Qt.Key.Key_PageDown else -step))
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self._apply()
        else:
            super().keyPressEvent(event)

    def focusOutEvent(self, event):  # noqa: N802 — Qt's spelling
        if not self._busy:
            self.close()

    def closeEvent(self, event):  # noqa: N802 — Qt's spelling
        """Stop the workers before the interpreter goes: a decode still running when the window
        is gone would hand a picture to a widget that no longer exists. The cancel stops ffmpeg
        within a twentieth of a second; a decoder in the middle of a PNG finishes on its own."""
        self._closing = True
        self._cancel.set()
        self._queue.clear()
        self._pool.waitForDone(1500)
        super().closeEvent(event)


# ---------------------------------------------------------------------- the strip

#: How wide one card in the strip is. Narrow on purpose: the strip says where you are in the list,
#: and the big picture beside it is what you are choosing from. Wide cards would show four of them.
#: The height is not here -- it is whatever is left of the window, so the strip fills its column.
TILE_WIDTH = 74
TILE_GAP = 3

#: How much of the window the strip takes. The rest is the picture.
STRIP_SHARE = 0.26

#: The card's own inset, and the one inside it. Named because the cards' height is what is left
#: of the window after both, and a number written twice is a number that stops agreeing.
CARD_MARGIN = 0
INNER_MARGIN = 18


class Tile(QWidget):
    """One wallpaper, cropped to a slice, with a border when it is the one selected."""

    picked = Signal(int)

    def __init__(self, index: int, entry: dict, look: dict, size: QSize, parent=None):
        super().__init__(parent)
        self.index = index
        self.entry = entry
        self.look = look
        self.pixmap: QPixmap | None = None
        #: The picture cropped to this card, kept until the picture or the size changes. It was
        #: cropped again on every paint -- a scale and a copy per card per scroll step.
        self._cropped: QPixmap | None = None
        self.selected = False
        self.setFixedSize(size)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(entry.get("name", ""))

    def set_pixmap(self, pixmap: QPixmap | None) -> None:
        self.pixmap = pixmap
        self._cropped = None
        self.update()

    def resizeEvent(self, event):  # noqa: N802 — Qt's spelling
        self._cropped = None
        super().resizeEvent(event)

    def set_selected(self, on: bool) -> None:
        if on != self.selected:
            self.selected = on
            self.update()

    def mousePressEvent(self, event):  # noqa: N802 — Qt's spelling
        self.picked.emit(self.index)

    def paintEvent(self, event):  # noqa: N802 — Qt's spelling
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        radius = min(self.look["radius"], 8.0)
        area = self.rect().adjusted(0, 0, -1, -1)
        path_colour = self.palette().window().color()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(path_colour.lighter(120) if path_colour.lightness() < 128
                         else path_colour.darker(108))
        painter.drawRoundedRect(area, radius, radius)
        if self.pixmap is not None and not self.pixmap.isNull():
            if self._cropped is None:
                self._cropped = thumbs.cropped(self.pixmap, area.size())
            painter.save()
            painter.setClipRect(area)
            painter.drawPixmap(area, self._cropped)
            painter.restore()
        else:
            # A wallpaper with no picture is still a wallpaper somebody may want. The name, turned
            # sideways because the card is taller than it is wide.
            painter.save()
            painter.translate(area.center())
            painter.rotate(-90)
            font = QFont()
            font.setPointSizeF(font.pointSizeF() * 0.85)
            painter.setFont(font)
            painter.setPen(QPen(self.palette().windowText().color()))
            painter.drawText(-area.height() // 2, -area.width() // 2, area.height(), area.width(),
                             Qt.AlignmentFlag.AlignCenter, self.entry.get("name", ""))
            painter.restore()
        if self.selected and self.look["thickness"] > 0:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(self.look["colour"], max(2.0, self.look["thickness"] + 1)))
            painter.drawRoundedRect(area, radius, radius)
        painter.end()


class StripPicker(Picker):
    """A column of narrow cards, and the one selected shown large beside them."""

    def _window_size(self) -> QSize:
        screen = QGuiApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        width, height = (1200, 560)
        if available is not None:
            width = min(max(int(available.width() * 0.62), 900), 1700)
            height = min(max(int(available.height() * 0.44), 460), 760)
        return QSize(width, height)

    def _build(self) -> None:
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(card_style(self.look))

        tile = QSize(TILE_WIDTH, max(120, self.height() - (CARD_MARGIN + INNER_MARGIN) * 2))
        self.strip_body = QWidget()
        strip_row = QHBoxLayout(self.strip_body)
        strip_row.setContentsMargins(0, 0, 0, 0)
        strip_row.setSpacing(TILE_GAP)
        self.tiles: list[Tile] = []
        for position, entry in enumerate(self.entries):
            card_widget = Tile(position, entry, self.look, tile)
            card_widget.picked.connect(self._apply_at)
            strip_row.addWidget(card_widget)
            self.tiles.append(card_widget)
        strip_row.addStretch()

        self.strip = QScrollArea()
        self.strip.setWidget(self.strip_body)
        self.strip.setWidgetResizable(True)
        self.strip.setFrameShape(QScrollArea.Shape.NoFrame)
        self.strip.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.strip.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.strip.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.strip.viewport().setAutoFillBackground(False)
        self.strip_body.setAutoFillBackground(False)

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(1, 1)

        self.caption = QLabel()
        caption_font = QFont()
        caption_font.setBold(True)
        caption_font.setPointSizeF(caption_font.pointSizeF() + 1)
        self.caption.setFont(caption_font)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setText("\n".join(t for t in (self.trouble, self.hint) if t))

        right = QVBoxLayout()
        right.setSpacing(8)
        right.addWidget(self.preview, 1)
        right.addWidget(self.caption)
        right.addWidget(self.status)

        inner = QHBoxLayout(card)
        inner.setContentsMargins(INNER_MARGIN, INNER_MARGIN, INNER_MARGIN, INNER_MARGIN)
        inner.setSpacing(INNER_MARGIN)
        inner.addWidget(self.strip)
        inner.addLayout(right, 1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

        self.strip.setFixedWidth(max(TILE_WIDTH * 2, int(self.width() * STRIP_SHARE)))
        self._selected: int | None = None
        self._fitted: tuple[tuple[int, int, int], QPixmap] | None = None

    def _big_width(self) -> int:
        return round(max(self.preview.width(), 400) * self.devicePixelRatioF())

    def _show(self) -> None:
        if not self.entries:
            return
        if self._selected is not None:
            self.tiles[self._selected].set_selected(False)
        self._selected = self.index
        tile = self.tiles[self.index]
        tile.set_selected(True)
        self.caption.setText(self.entries[self.index].get("name", ""))
        self.strip.ensureWidgetVisible(tile, TILE_WIDTH, 0)
        self._paint_preview()

    def _thumb_ready(self, position: int) -> None:
        self.tiles[position].set_pixmap(self.pictures[position])
        if position == self.index:
            self._paint_preview()

    def _big_ready(self) -> None:
        self._paint_preview()

    def _paint_preview(self) -> None:
        picture = self.front_picture()
        if picture is None or picture.isNull():
            self.preview.setText("no preview")
            return
        # The same picture at the same size is the same scaling, and `_show` asks for it on
        # every step of the selection whether or not the picture moved.
        key = (picture.cacheKey(), self.preview.width(), self.preview.height())
        if self._fitted is None or self._fitted[0] != key:
            self._fitted = (key, thumbs.fitted(picture, self.preview.size()))
        self.preview.setPixmap(self._fitted[1])

    def _page_step(self) -> int:
        return max(1, self.strip.viewport().width() // (TILE_WIDTH + TILE_GAP))

    def _say(self, text: str) -> None:
        super()._say(text)
        self.status.setText(text)

    def _apply_at(self, position: int) -> None:
        self._select(position)
        self._apply()


# ---------------------------------------------------------------------- the pages

#: Every number below was measured off the reference this layout copies, and is kept as a fraction
#: of the screen so it holds at any size. On that 1920x1080 screen: the front card was 748 wide, its
#: centre was at x=960 -- the exact middle -- the cards behind stood 78px apart at 91.5% of the
#: front card's height, and the lean was 3.6 degrees.
#:
#: The one departure is the card's shape. The reference card is 1.58:1 on a 1.78:1 screen, so it
#: does not show the crop the desktop would show. Here the card takes **the screen's own
#: proportions** -- it is the screen, shrunk -- so what you are looking at is what you will get.
CARD_SHARE = 0.39
BEHIND_SCALE = 0.915
STEP_SHARE = 0.0406

#: Measured as 3.6 degrees of lean. `shear(-SHEAR, 0)` on a rect centred on the origin is what
#: takes the top to the **right**; the other sign takes it left. Checked by mapping the corners,
#: because reading the sign off the documentation is how it ends up mirrored.
SHEAR = 0.0625

#: How many pages deep each side goes. The reference showed four; five is one more, so the stack
#: does not end exactly where that screenshot happened to stop. It is not a limit on what fits --
#: the window's width is derived from it, so any depth would fit -- it is the number that decides
#: how wide the window is: the outermost page still sits a tenth of the window in from the edge.
DEPTH = 5

#: How much black goes over a page behind, near and far, out of 255. **A scrim and not opacity.**
#: There is no background here -- the window is transparent -- so making a page translucent does
#: not darken it, it lets the desktop through it, and two slivers overlapping compound into a
#: colour nobody chose. Painting the picture solid and laying black over it darkens the same
#: amount on every wallpaper.
#:
#: The reference cannot settle this one: it does not dim at all. It is here because two dark
#: wallpapers side by side have no boundary between them otherwise.
SCRIM_NEAR, SCRIM_FAR = 42, 132

#: The hairline between one page and the next, so two dark wallpapers still read as two pages.
PAGE_EDGE = QColor(0, 0, 0, 120)

#: How far, in logical pixels, a page's clip reaches past its own edge -- and how far the pages
#: in front are pulled in before being taken out of it. Two: an antialiased edge is a pixel of
#: blend either side, and at a scale of 1.2 a pixel and a bit. See `PagesPicker.paintEvent`.
EDGE_PAD = 2.0


class PagesPicker(Picker):
    """The chosen wallpaper in the middle of the screen, the rest leaning away behind it.

    No panel and no background: the window is transparent, and what is between the cards is the
    desktop itself. Which is also why a click there closes -- the thing under the pointer is your
    wallpaper, and clicking your wallpaper means leaving.

    No text either. The only writing is when there is something wrong to say.
    """

    def __init__(self, client, data: dict):
        #: The pages behind, each drawn once at its size with its lean and its hairline, keyed by
        #: which wallpaper and which picture of it. See `paintEvent` for why.
        self._renders: OrderedDict[tuple[int, int], QPixmap] = OrderedDict()
        super().__init__(client, data)
        self.setMouseTracking(True)

    def _measure(self, screen: QSize) -> None:
        """The card and the step, for a screen of this size.

        Its own step rather than part of sizing the window, so a card can be measured against
        something the machine does not have -- which is the only way to look at this layout at a
        size other than this desk's.
        """
        self.card = QSize(round(screen.width() * CARD_SHARE),
                          round(screen.height() * CARD_SHARE))
        self.step = screen.width() * STEP_SHARE

    def _window_size(self) -> QSize:
        """Two measurements from two different rectangles, and that is not an oversight.

        **The card's shape comes from the screen**, because the promise of this layout is that the
        picture is the screen shrunk -- what you are looking at is the crop you will get. Taking it
        from the usable area instead gives the card the shape of the screen *minus the panel*, and
        then the crop is a lie by however tall the panel is.

        **The window is clamped to the usable area**, because that is where a window can be.

        On more than one screen this measures the primary one, while applying reaches every screen
        of the activity. There is no single honest answer on a mixed-aspect desk; the primary one
        is the one whose middle the window is centred on.
        """
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self._measure(QSize(1920, 1080))
            return QSize(1600, 500)
        self._measure(screen.geometry().size())
        available = screen.availableGeometry()
        # Wide enough for the whole fan on both sides, because the **card** has to sit in the
        # middle of the screen and the window is what the compositor centres. The lean adds a
        # little on each side, and a card behind is narrower than the front one but further out.
        reach = max(self.card.width() / 2,
                    DEPTH * self.step + self.card.width() * BEHIND_SCALE / 2)
        width = round(2 * (reach + SHEAR * self.card.height() / 2) + 24)
        height = round(self.card.height() + 24)
        return QSize(min(width, available.width()), min(height, available.height()))

    def _big_width(self) -> int:
        return round(max(self.card.width(), 400) * self.devicePixelRatioF())

    # ---------------------------------------------------------------- geometry

    def _fan(self) -> list[tuple[int, int]]:
        """Every page on screen as (which wallpaper, how far from the front), back to front.

        Negative is to the left and is what comes **before** the selection; positive is to the
        right and comes after. The reference shows only a left-hand stack because the wallpaper
        selected there happened to be the last in the list.
        """
        out = []
        for distance in range(DEPTH, 0, -1):
            for side in (-1, 1):
                position = self.index + side * distance
                if 0 <= position < len(self.entries):
                    out.append((position, side * distance))
        out.append((self.index, 0))
        return out

    def _card_rect(self, offset: int) -> QRectF:
        scale = 1.0 if offset == 0 else BEHIND_SCALE
        width = self.card.width() * scale
        height = self.card.height() * scale
        return QRectF(-width / 2, -height / 2, width, height)

    def _card_transform(self, offset: int) -> QTransform:
        transform = QTransform()
        transform.translate(self.width() / 2 + offset * self.step, self.height() / 2)
        transform.shear(-SHEAR, 0.0)
        return transform

    def _card_polygon(self, offset: int, pad: float = 0.0) -> QPolygonF:
        """Where a page lands on the window, as the parallelogram it is; `pad` grows it."""
        rect = self._card_rect(offset).adjusted(-pad, -pad, pad, pad)
        return self._card_transform(offset).map(QPolygonF(rect))

    def _at(self, point: QPointF) -> int | None:
        # Front to back, because that is the order somebody sees them in: the card on top of the
        # pile is the one their pointer is on, whatever is underneath it.
        for position, offset in reversed(self._fan()):
            if self._card_polygon(offset).containsPoint(point, Qt.FillRule.OddEvenFill):
                return position
        return None

    # ---------------------------------------------------------------- painting

    def _thumb_ready(self, position: int) -> None:
        for key in [k for k in self._renders if k[0] == position]:
            del self._renders[key]
        if abs(position - self.index) <= DEPTH:
            self.update()

    def paintEvent(self, event):  # noqa: N802 — Qt's spelling
        """Every page, back to front, each only where the pages in front leave it bare -- and the
        ones behind copied from a drawing made once, not drawn again.

        **Measured, because the obvious fix was not the fix.** Drawing all eleven pages whole --
        smooth, leaning, antialiased -- took 9.8 to 17 ms a frame at this desk's size (3440x1440
        at scale 1.2), against 10 ms a frame at 100 Hz, so holding an arrow key was a stutter.
        Clipping each page to what shows of it looked like the answer, since five sixths of the fan
        is covered, and it saved a quarter: one page behind cost 1.5 ms whole and 1.0 ms clipped
        to a sliver, and the same page with antialiasing off cost 0.2. The time is in the
        antialiased edges of a leaning rectangle -- the hairline, the scrim's fill, the picture's
        outline -- which the raster engine draws whole and clips afterwards.

        So a page behind is drawn once, at its size, with its lean and its hairline, into a pixmap
        at the screen's own resolution (`_render_behind`), and a frame copies it: an upright copy
        honours the clip and costs a twentieth of a millisecond. The scrim is laid over the copy as
        a fill of the visible region with antialiasing off, which is exact to the pixel and free.
        The page in front is still drawn live, because it changes with every key and again when
        its full-size picture lands. What is kept is a picture of each page, and to the eye it is
        the same fan: compared pixel for pixel against the live drawing, 0.3% differ by more than
        32 levels, all of them on the slanted edges and on sharp detail inside the pages behind --
        a page copied onto the device grid sits a fraction of a pixel from where the live draw
        put it. Measured at this desk's size: 13.3 ms a frame before, 2.5 after.

        The clip regions: each page's own outline grown by `EDGE_PAD`, less the outlines in front
        shrunk by the same, so the antialiased edges survive -- a page's outer edge is still soft,
        and the page in front still blends over the one behind. The scrim's region is the exact
        outline, so it never spills past the picture.
        """
        began = time.perf_counter() if PAINT_TIMES else 0.0
        painter = QPainter(self)
        fan = self._fan()
        covered = QRegion()
        bare: dict[tuple[int, int], QRegion] = {}
        exact: dict[tuple[int, int], QRegion] = {}
        for position, offset in reversed(fan):
            own = QRegion(self._card_polygon(offset, EDGE_PAD).toPolygon())
            bare[(position, offset)] = own.subtracted(covered)
            exact[(position, offset)] = QRegion(self._card_polygon(offset).toPolygon()).subtracted(covered)
            covered = covered.united(QRegion(self._card_polygon(offset, -EDGE_PAD).toPolygon()))
        for position, offset in fan:
            painter.save()
            painter.setClipRegion(bare[(position, offset)])
            if offset == 0:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                self._draw_page(painter, position, offset)
            else:
                self._copy_page(painter, position, offset, exact[(position, offset)])
            painter.restore()
        if self.trouble:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self._draw_trouble(painter)
        painter.end()
        if PAINT_TIMES:
            print(f"paint {(time.perf_counter() - began) * 1000:.2f} ms", file=sys.stderr)

    def _render_behind(self, position: int) -> QPixmap | None:
        """A page behind, drawn once: the picture at the behind size, leaning, with its hairline.

        At the screen's own resolution, so the copy is pixel for pixel. The box is the leaning
        rectangle's bounding box -- the lean adds `SHEAR` times the height to the width -- and the
        page is drawn centred in it, so placing the copy is arithmetic on the page's centre.
        """
        picture = self.pictures[position]
        if picture is None or picture.isNull():
            return None
        key = (position, picture.cacheKey())
        kept = self._renders.get(key)
        if kept is not None:
            self._renders.move_to_end(key)
            return kept
        rect = self._card_rect(1)
        ratio = self.devicePixelRatioF()
        width, height = rect.width() + SHEAR * rect.height(), rect.height()
        render = QPixmap(math.ceil(width * ratio), math.ceil(height * ratio))
        render.setDevicePixelRatio(ratio)
        render.fill(Qt.GlobalColor.transparent)
        painter = QPainter(render)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        transform = QTransform()
        transform.translate(width / 2, height / 2)
        transform.shear(-SHEAR, 0.0)
        painter.setTransform(transform)
        size = QSize(max(1, round(rect.width())), max(1, round(rect.height())))
        painter.drawPixmap(rect, picture, thumbs.crop_box(picture, size))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(PAGE_EDGE, 1))
        painter.drawRect(rect)
        painter.end()
        self._renders[key] = render
        while len(self._renders) > RENDERS_KEPT:
            self._renders.popitem(last=False)
        return render

    def _copy_page(self, painter: QPainter, position: int, offset: int, visible: QRegion) -> None:
        """A page behind: the drawing made once, copied to where it lands, and the scrim over it."""
        render = self._render_behind(position)
        if render is None:
            # Nothing decoded yet, or nothing decodable: the plain page, drawn live as before.
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self._draw_page(painter, position, offset)
            return
        ratio = self.devicePixelRatioF()
        width, height = render.width() / ratio, render.height() / ratio
        # On the device grid, so the copy is a copy and not a resample.
        x = round((self.width() / 2 + offset * self.step - width / 2) * ratio) / ratio
        y = round((self.height() / 2 - height / 2) * ratio) / ratio
        painter.drawPixmap(QPointF(x, y), render)
        distance = (abs(offset) - 1) / max(1, DEPTH - 1)
        painter.setClipRegion(visible)
        painter.fillRect(self.rect(), QColor(0, 0, 0,
                                             round(SCRIM_NEAR + (SCRIM_FAR - SCRIM_NEAR) * distance)))

    def _draw_page(self, painter: QPainter, position: int, offset: int) -> None:
        rect = self._card_rect(offset)
        painter.save()
        painter.setTransform(self._card_transform(offset))
        picture = self.front_picture() if offset == 0 else self.pictures[position]
        if picture is not None and not picture.isNull():
            # From the source rectangle rather than from a cropped copy: this runs for every page
            # on every repaint, and the front one's picture is as wide as the card.
            size = QSize(max(1, round(rect.width())), max(1, round(rect.height())))
            painter.drawPixmap(rect, picture, thumbs.crop_box(picture, size))
        else:
            # Nothing decoded yet, or nothing decodable. A plain page keeps the stack's shape
            # while the queue catches up, which is better than a hole in the middle of it.
            base = self.palette().window().color()
            painter.fillRect(rect, base.lighter(115) if base.lightness() < 128
                             else base.darker(106))

        if offset:
            distance = (abs(offset) - 1) / max(1, DEPTH - 1)
            painter.fillRect(rect, QColor(0, 0, 0,
                                          round(SCRIM_NEAR + (SCRIM_FAR - SCRIM_NEAR) * distance)))

        painter.setBrush(Qt.BrushStyle.NoBrush)
        if offset == 0:
            if self.look["thickness"] > 0:
                pen = QPen(self.look["colour"], self.look["thickness"])
                pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
                # Cosmetic, so the lean cannot make the near-vertical edges thicker than the
                # horizontal ones. The decoration's thickness is a number of real pixels, and that
                # is what it should stay.
                pen.setCosmetic(True)
                painter.setPen(pen)
                painter.drawRect(rect)
        else:
            painter.setPen(QPen(PAGE_EDGE, 1))
            painter.drawRect(rect)
        painter.restore()

    def _draw_trouble(self, painter: QPainter) -> None:
        """The only words this layout ever shows, and only when something is wrong.

        Drawn twice, offset, because it lands on whatever wallpaper happens to be behind it and a
        single colour is unreadable on half of them.
        """
        painter.resetTransform()
        painter.setOpacity(1.0)
        font = QFont()
        font.setBold(True)
        painter.setFont(font)
        top = self.height() / 2 + self.card.height() / 2 + 6
        area = QRectF(24, top, self.width() - 48, max(20.0, self.height() - top))
        flags = (Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
                 | Qt.TextFlag.TextWordWrap)
        painter.setPen(QPen(QColor(0, 0, 0, 170)))
        painter.drawText(area.translated(1, 1), flags, self.trouble)
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(area, flags, self.trouble)

    # ---------------------------------------------------------------- mouse

    def mousePressEvent(self, event):  # noqa: N802 — Qt's spelling
        """One meaning per place the pointer can be.

        A page behind is a sliver of itself, and a click two pixels from the one you meant would
        otherwise set a wallpaper you never looked at. So a click back there only brings that page
        forward, and setting takes a second, deliberate click on the big one in the middle -- where
        your eye already is. The strip is not a counter-example: every card there is whole and the
        same size, so there is no half-hidden case to protect.

        A click on nothing closes, because what is under the pointer there is the desktop.
        """
        position = self._at(event.position())
        if position is None:
            self.close()
        elif position == self.index:
            self._apply()
        else:
            self._select(position)

    def mouseMoveEvent(self, event):  # noqa: N802 — Qt's spelling
        """A hand over a page, an arrow over the desktop.

        With no text and no child widgets there is nothing else to say that these are things you
        can click. Deliberately **not** a preselect: dragging across the stack would ask for a
        full-size decode per sliver it crossed.
        """
        over = self._at(event.position()) is not None
        self.setCursor(Qt.CursorShape.PointingHandCursor if over
                       else Qt.CursorShape.ArrowCursor)

    def _page_step(self) -> int:
        return DEPTH


# ---------------------------------------------------------------------- picking the layout

LAYOUTS = {"pages": PagesPicker, "strip": StripPicker}
DEFAULT_LAYOUT = "pages"


def open_picker(client) -> Picker:
    """The picker the settings ask for, built from one read.

    A function and not a class, because which class it is cannot be known until the daemon has been
    asked -- and asking twice, once to choose and once to fill, would scan the wallpaper folders
    twice for one keypress.
    """
    data = client.wallpapers() or {}
    layout = LAYOUTS.get(str(data.get("layout", DEFAULT_LAYOUT)), LAYOUTS[DEFAULT_LAYOUT])
    return layout(client, data)
