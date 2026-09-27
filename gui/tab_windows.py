"""The Windows tab: one row per window class this desk has seen, and a column for each choice about
it.

The rows are the daemon's `table`; ticking a box sends the change a moment later, rows ticked
together as one batch, because two of the columns (Float and Animate) are memberships of one of the
compositor's lists and writing the tiler's list re-tiles the screen. The Opacity column's menu gives
one window a number of its own. *Find a window...* asks the compositor itself which window was
clicked -- `queryWindowInfo` on `/KWin`, read through a slot typed `QVariantMap`, the one way this
PySide decodes the answer -- which is the one call this tab makes without the daemon.
"""

from __future__ import annotations

import html
from urllib.parse import quote, unquote

from PySide6.QtCore import SLOT, QEvent, QRectF, QSize, Qt, QTimer, Signal, Slot
from PySide6.QtDBus import QDBusConnection, QDBusError, QDBusMessage
from PySide6.QtGui import (QActionGroup, QColor, QFont, QGuiApplication, QIcon, QKeySequence,
                           QPainter, QPen, QPixmap, QShortcut)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QFrame, QHBoxLayout,
                               QHeaderView, QInputDialog, QLabel, QLineEdit, QMenu, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from client import Client


# ---------------------------------------------------------------------- windows tab

def copy_icon(ink: QColor, size: int = 14) -> QIcon:
    """Two overlapping sheets — the copy glyph, drawn rather than asked of an icon theme.

    Drawn for the same reason the keycaps are: nothing in this app is allowed to depend on which
    icon theme is installed. Measured the cheap way — outside a graphical session `QIcon.fromTheme`
    returns nothing at all, so a themed icon would make this affordance invisible in exactly the
    place the simulation looks at it.
    """
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(ink, 1.1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    unit = size / 14.0
    painter.drawRoundedRect(QRectF(1 * unit, 1 * unit, 8 * unit, 10 * unit), 1.5, 1.5)
    painter.drawRoundedRect(QRectF(4.5 * unit, 3.5 * unit, 8 * unit, 10 * unit), 1.5, 1.5)
    painter.end()
    return QIcon(pixmap)


#: How far into the name cell the copy mark reaches: the glyph itself and the breathing room the
#: style leaves around it. A click inside this copies; anywhere else in the cell selects the row,
#: which is what clicking a name looks like it should do.
MARK_WIDTH = 24

COLUMNS = ["Window class", "Hide title bar", "Outline", "Transparency", "Opacity", "Blur",
           "Float", "Animate", "Status", "Title"]

#: One line per column, on the header, where it is permanent and true of every row. The cells keep
#: only what is true of *their* row -- why this one is greyed, what this one is actually drawn at.
COLUMN_HINTS = [
    "The application, as the compositor names it. Click the mark to copy it.",
    "Take the title bar off this window and let the theme draw the rest.",
    "Draw the theme's thin ring around it. Only while the title bar is hidden.",
    "Let the desktop show through it. How far through is the next column.",
    "How solid it is while it is see-through, 100 % being opaque. A dot is the number on the "
    "Appearance tab; click a number to give one window its own.",
    "Blur whatever is behind it. Only shows through a see-through window.",
    "Leave this window where it is put instead of tiling it.",
    "Let it animate when it is moved or resized.",
    "Why KyprX cannot manage this window, when it cannot.",
    "The title of the window that is open now.",
]
(COL_CLASS, COL_TITLEBAR, COL_OUTLINE, COL_TRANSPARENCY, COL_OPACITY, COL_BLUR, COL_FLOAT,
 COL_ANIMATE, COL_STATUS, COL_TITLE) = range(10)

#: The columns written per window, through the decoration override, the window rule and the blur
#: list.
SWITCH_COLUMNS = {COL_TITLEBAR: "titlebar", COL_OUTLINE: "outline",
                  COL_TRANSPARENCY: "transparency", COL_BLUR: "blur"}

#: Transparency sits **before** blur because blur is seen through it: the effect paints a blurred
#: copy of whatever is behind the window, and on an opaque window nothing of it shows. Reading the
#: row left to right is reading the dependency -- see-through at all, then how much, then what is
#: painted behind it.
TRANSPARENCY_HELP = (
    "Whether the desktop shows through the window, forced by a compositor window rule. Unticking "
    "forces it fully opaque — which is not the same as writing nothing, because a rule that makes "
    "every window see-through would then still be in charge. How far through is the next column.")

BLUR_NEEDS_TRANSPARENCY = (
    "Blur is painted behind the window and seen through it, so on an opaque window there is "
    "nothing of it to see. Tick Transparency and this comes back exactly as it was.")

#: The columns that are membership in one list belonging to the whole compositor. They go the
#: other way round to the daemon — see `LIST_SWITCHES` there — because writing the tiler's list
#: costs a restart of the tiler and a re-tile of every window.
LIST_COLUMNS = {COL_FLOAT: "float", COL_ANIMATE: "animate"}

#: What the three per-window switches show for one of this app's own windows, and why.
OVERLAY_CELL = "\u2014"
OVERLAY_HELP = "One of KyprX's own windows. It has no title bar to hide."

FLOAT_HELP = ("A persistent rule: the tiler leaves this window where it is put. Not the same as "
              "the toggle-float key, which lasts until the window closes.")
ANIMATE_HELP = "Whether the geometry animation plays when this window is moved or resized."

STATUS_TEXT = {
    "refuses": "app refuses",
    "closed": "not open",
    "system": "system window",
    "shared": "shared pattern",
}

REFUSES_HELP = (
    "This app draws its own title bar and refuses the compositor's, so the rule has nothing to "
    "force and the override has nothing to attach to. The switch is inside the app itself — in "
    "the Firefox family, the option to use the system title bar. Change it there, reopen the "
    "window and come back.")


#: How long *Find a window…* waits for the click, in milliseconds. Long, because the wait is a
#: person finding a window. When it runs out this window stops waiting, but the compositor does not:
#: the pointer stays a crosshair until something is clicked or Esc is pressed, and that answer then
#: goes nowhere.
PICK_TIMEOUT_MS = 120_000

#: What the compositor answers when the pick ends without a window, by the error it sends.
PICK_REFUSALS = {
    "org.kde.KWin.Error.UserCancel": "Nothing picked.",
    "org.kde.KWin.Error.InvalidWindow": "That is part of the desktop rather than a window. "
                                        "Try another.",
}

#: The numbers the Opacity menu offers, most solid first. Round steps, because the difference
#: between two neighbours has to be visible on screen to be worth a line in a menu; anything else
#: is *Other…*. The strength on the Appearance tab is left out of them, because it already has the
#: first line of the menu to itself.
OPACITY_PRESETS = (95, 90, 85, 80, 75, 70)

OPACITY_SHARED = ("The number on the Appearance tab, which every see-through window without one "
                  "of its own shares. Click to give this window its own.")
OPACITY_OWN = ("This window's own number: the one on the Appearance tab does not reach it. Click "
               "to change it, or to put it back on the Appearance tab's.")
OPACITY_NEEDS_TRANSPARENCY = ("Opaque while Transparency is unticked. Tick it and this number "
                              "comes back.")
OPACITY_SYSTEM = ("One of the desktop's own windows. KyprX leaves how solid it is to whoever set "
                  "it: the screen-sharing helper, for one, hides itself at 0.")


def dot_icon(ink: QColor, selected_ink: QColor, size: int = 14) -> QIcon:
    """The dot that means "the value that applies here is the shared one", as a table-cell icon.

    The same mark and the same meaning as `Dot` in front of a setting nothing has been written
    for: in the Opacity column it is the strength on the Appearance tab, reaching this window
    because nothing of its own has been written for it. Drawn, for the reason `copy_icon` is.

    Twice: the grey of `Dot` all but vanished on the selected row's highlight, which is the one
    row somebody is looking at, so the selected state is drawn in the highlight's own text colour.
    """
    icon = QIcon()
    for colour, mode in ((ink, QIcon.Mode.Normal), (selected_ink, QIcon.Mode.Selected)):
        pixmap = QPixmap(QSize(size, size))
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(colour)
        painter.drawEllipse(QRectF(size / 2 - 2.5, size / 2 - 2.5, 5.0, 5.0))
        painter.end()
        icon.addPixmap(pixmap, mode)
    return icon


def blank_icon(size: int = 14) -> QIcon:
    """Nothing, the size of `dot_icon`, so a number with no dot lines up with one that has it."""
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    return QIcon(pixmap)


class WindowsTab(QWidget):
    copied = Signal(str)

    def __init__(self, client: Client, parent=None):
        super().__init__(parent)
        self.c = client
        self.rows: list[dict] = []
        self._loading = False
        #: Ticks waiting to be sent, and the timer that sends them. Ticking four rows in a row
        #: used to be four writes and four compositor reloads; with the float column it would also
        #: be four reloads of the tiler, and a tiler that has just reloaded tiles the screen from
        #: scratch — so the windows would visibly rearrange four times over. Collected and sent as
        #: one batch instead, the same shape `ThemeBox` uses for a drag along its strength control.
        self._queued_switches: dict[str, dict[str, bool]] = {}
        self._queued_lists: dict[str, dict[str, bool]] = {}
        self._batch = QTimer(self)
        self._batch.setSingleShot(True)
        self._batch.setInterval(400)
        self._batch.timeout.connect(lambda: self.flush())
        #: Set while a batch is going out. The call blocks for as long as the compositor takes,
        #: and the daemon says "something changed" in the middle of it.
        self._busy = False
        #: A repaint that was refused while ticks were waiting, and is owed once they have gone.
        self._missed = False

        self._copy_icon = copy_icon(self.palette().windowText().color())
        #: The ink `Dot` uses, so the mark reads as the same mark it is on every other tab.
        self._dot_icon = dot_icon(self.palette().mid().color(),
                                  self.palette().highlightedText().color())
        self._blank_icon = blank_icon()
        #: Every row, whatever the filters show, and the two things the Opacity column reads: the
        #: strength on the Appearance tab and the windows with a number of their own.
        self._everything: list[dict] = []
        self._strength = 100
        self._own: dict[str, int] = {}

        self.table = QTableWidget(0, len(COLUMNS))
        # No frame, for the reason the page's scroll area has none: focused, the style paints it in
        # the theme's focus colour. The table keeps its focus -- the arrows and Ctrl+C need it.
        self.table.setFrameShape(QTableWidget.Shape.NoFrame)
        # Each column says what it is, permanently, from the header. It used to be said on the
        # cells instead -- and only on the rows where the box was greyed out, so hovering the same
        # column on two windows gave a lecture on one and silence on the other.
        for i, (name, hint) in enumerate(zip(COLUMNS, COLUMN_HINTS)):
            item = QTableWidgetItem(name)
            item.setToolTip(hint)
            self.table.setHorizontalHeaderItem(i, item)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        for i in range(len(COLUMNS) - 1):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_TITLE, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self._toggled)
        self.table.itemSelectionChanged.connect(self._selection)
        self.table.itemClicked.connect(self._clicked)
        #: The Opacity menu opens from the right button as well as the left, and from the keyboard
        #: -- Enter, F2 or the menu key on that column, through `eventFilter`.
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.installEventFilter(self)
        #: Where the last click landed inside the table. `itemClicked` says which item was
        #: clicked and not where, and the answer matters here: the mark copies and the rest of the
        #: cell selects. Read from the click itself rather than from `QCursor.pos()`, which on
        #: Wayland is whatever this application last saw rather than where the pointer is.
        self._pressed_at = None
        self.table.viewport().installEventFilter(self)
        #: What the comment above this table promised and the code never did: Ctrl+C on the
        #: selected row. A view has no copy action of its own.
        copy = QShortcut(QKeySequence(QKeySequence.StandardKey.Copy), self.table)
        copy.activated.connect(self._copy_selected)

        # Both filters the same way round, so ticking either shows more rather than one showing
        # more and the other fewer.
        self.only_open = QCheckBox("Only open windows")
        self.only_open.setChecked(True)
        self.only_open.setToolTip("Hide the windows that are not open right now. Their settings "
                                  "are kept either way.")
        self.only_open.toggled.connect(self.reload)
        self.show_system = QCheckBox("System windows")
        self.show_system.setToolTip("Show the desktop's own windows: the panel, the shell, "
                                    "KyprX's own.")
        self.show_system.toggled.connect(self.reload)

        #: Thirty rows is enough that finding one by eye is work. It writes nothing -- it decides
        #: which of the rows are drawn, and nothing else.
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("filter")
        self.filter.setToolTip("Show only the windows whose name or title contains this.")
        self.filter.setClearButtonEnabled(True)
        self.filter.setMaximumWidth(220)
        self.filter.textChanged.connect(self.reload)

        self.detail = QLabel("—")
        self.detail.setWordWrap(True)
        self.detail.setMinimumHeight(2 * self.detail.fontMetrics().lineSpacing())
        self.detail.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        #: Clicking a window on screen to find its row, which is quicker than reading thirty class
        #: names -- and the only way at all when the class looks nothing like the application's
        #: name, which is often. It selects the row, so it serves every column.
        self.find = QPushButton("Find a window…")
        self.find.setToolTip("Turns the pointer into a crosshair: click a window and its row is "
                             "selected here. Esc cancels.")
        self.find.clicked.connect(self._find)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("Show"))
        filters.addWidget(self.only_open)
        filters.addWidget(self.show_system)
        filters.addStretch()
        filters.addWidget(self.find)
        filters.addWidget(self.filter)

        #: Which windows have a number of their own, in one line under the table: the overview the
        #: column cannot give while it is filtered or scrolled, and a way to each of them.
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.TextFormat.RichText)
        self.summary.linkActivated.connect(lambda href: self.reveal(unquote(href)))

        #: A strip under the table rather than the bottom half of a splitter. The splitter could be
        #: dragged shut, and with nothing but a label in it the first thing lost on a short window
        #: was the only plain-language line on the tab.
        rule = QFrame()
        rule.setFrameShape(QFrame.Shape.HLine)
        rule.setFrameShadow(QFrame.Shadow.Sunken)

        layout = QVBoxLayout(self)
        layout.addLayout(filters)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.summary)
        layout.addWidget(rule)
        layout.addWidget(self.detail)

    def reload(self) -> None:
        """Repaint the table, and ask the compositor for a fresh picture while we are at it.

        Refuses while ticks are waiting to be sent: repainting then would draw the daemon's answer
        over boxes somebody has just ticked and is still ticking, and the batch would go out
        against a table that no longer looks like what was asked for.

        The refresh is the point. The daemon's window list only ever changed when the compositor
        volunteered something, so opening this tab with the daemon already running re-read exactly
        the same list it had before — however stale. The answer comes back asynchronously and
        `MainWindow` already re-reads a second later, so this call is what makes that second read
        worth anything.
        """
        if self._batch.isActive() or self._busy:
            # Refused, and remembered: `flush` runs it again afterwards. It used to be refused and
            # forgotten, so a window that opened while somebody was ticking boxes simply was not
            # in the table until something else happened.
            self._missed = True
            return
        self._missed = False
        self.c.refresh()
        previous = self.selected_class()
        self._loading = True
        everything = self.c.windows()
        settings = self.c.settings()
        self._everything = everything
        self._strength = int(settings.get("transparency") or 100)
        self._own = {str(k): int(v) for k, v in (settings.get("own_transparency") or {}).items()}
        wanted = self.filter.text().strip().casefold()
        self.rows = [r for r in everything
                     if (self.show_system.isChecked() or r["status"] != "system")
                     and (not self.only_open.isChecked() or r["open"])
                     and (not wanted or wanted in r["class"].casefold()
                          or wanted in str(r.get("title") or "").casefold())]
        self.table.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            self._fill(i, r)
        self._loading = False
        self._summarise()
        if previous:
            self.select(previous)
        elif self.rows and self.table.currentRow() < 0:
            self.table.selectRow(0)
        self._selection()

    def _fill(self, i: int, r: dict) -> None:
        name = QTableWidgetItem(r["class"])
        #: The mark is on every row, always. It was tried on the row under the pointer only, and
        #: that is an affordance nobody can find: it appears where the pointer already is, so it
        #: can only be seen by somebody who has already gone looking for it.
        name.setIcon(self._copy_icon)
        name.setToolTip("Click the mark to copy this name. Ctrl+C copies the selected row.")
        if r["status"] == "system":
            name.setForeground(QColor(128, 128, 128))
        self.table.setItem(i, COL_CLASS, name)

        checks = {COL_TITLEBAR: not r["titlebar"], COL_OUTLINE: r["outline"],
                  COL_TRANSPARENCY: r["transparency"], COL_BLUR: r["blur"],
                  COL_FLOAT: r["float"], COL_ANIMATE: r["animate"]}
        for column, checked in checks.items():
            item = QTableWidgetItem()
            if r.get("overlay") and column in (COL_TITLEBAR, COL_OUTLINE,
                                               COL_TRANSPARENCY, COL_BLUR):
                # A dash rather than an empty box, because an empty box is a statement and it
                # would be the wrong one: these windows have no title bar to hide. They are this
                # app's own, they are never managed as applications, and the daemon takes that
                # treatment back off every time it starts.
                item.setText(OVERLAY_CELL)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                item.setForeground(QColor(128, 128, 128))
                item.setToolTip(OVERLAY_HELP)
                self.table.setItem(i, column, item)
                continue
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
                          | Qt.ItemFlag.ItemIsSelectable)
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            if column == COL_OUTLINE and r["titlebar"]:
                item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                item.setToolTip("The outline follows an override, which only exists while the "
                                "title bar is hidden")
            if column == COL_TRANSPARENCY:
                item.setToolTip(TRANSPARENCY_HELP)
            if column == COL_BLUR and not r["blur_per_window"]:
                item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                item.setToolTip("Blur is set globally right now — the per-window list decides "
                                "nothing. See the Effects tab.")
            # Greyed rather than unticked, so the answer is kept rather than thrown away. Nothing
            # is written for blur while the transparency is off, so the tick that comes back is
            # the one that was there.
            elif column == COL_BLUR and not r["transparency"]:
                item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                item.setToolTip(BLUR_NEEDS_TRANSPARENCY)
            if column == COL_FLOAT:
                item.setToolTip(FLOAT_HELP)
                if r.get("float_locked"):
                    item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                    item.setToolTip("One of this app's own windows. It has to float, and the "
                                    "daemon puts it back in the list every time it starts.")
                elif not r.get("tiling_enabled", True):
                    item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                    item.setToolTip("Tiling is switched off, so nothing is tiled and nothing "
                                    "floats. The Tiling tab has a button that switches it on.")
            if column == COL_ANIMATE:
                item.setToolTip(ANIMATE_HELP)
                if not r.get("geometry_enabled", True):
                    item.setFlags(Qt.ItemFlag.ItemIsSelectable)
                    item.setToolTip("The geometry animation is switched off altogether. "
                                    "See the Effects tab.")
            self.table.setItem(i, column, item)
        self.table.setItem(i, COL_OPACITY, self._opacity_cell(r))

        status = QTableWidgetItem(STATUS_TEXT.get(r["status"], ""))
        if r["status"] == "refuses":
            # Bold, and no colour of its own. It used to be painted in the warning band's orange,
            # which is a colour chosen against that band's black text rather than against a table
            # the desktop's own scheme paints -- pale orange on white in a light one. Bold is
            # enough to tell it from the other three, and it cannot come out unreadable.
            f = QFont()
            f.setBold(True)
            status.setFont(f)
        self.table.setItem(i, COL_STATUS, status)
        self.table.setItem(i, COL_TITLE, QTableWidgetItem(r["title"]))

    def _toggled(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        column = item.column()
        row = self.rows[item.row()]
        checked = item.checkState() == Qt.CheckState.Checked
        if column in SWITCH_COLUMNS:
            name = SWITCH_COLUMNS[column]
            # The title bar column reads as "hide it", so the stored switch is the other way round.
            value = (not checked) if name == "titlebar" else checked
            self._queued_switches.setdefault(row["class"], {})[name] = value
        elif column in LIST_COLUMNS:
            self._queued_lists.setdefault(LIST_COLUMNS[column], {})[row["class"]] = checked
        else:
            return
        self._batch.start()

    # ------------------------------------------------------------ the Opacity column

    def _opacity_cell(self, r: dict) -> QTableWidgetItem:
        """How solid this window is while it is see-through, and whether that is its own number.

        **The number is shown on every row, opaque ones included**, greyed there the way the Blur
        column greys: it is the number that comes back when Transparency is ticked, and a cell
        that went blank would be a cell that forgot it. The owner asked for that in as many words.

        The dot is the strength on the Appearance tab reaching this window; no dot, its own. A
        window a rule of somebody's draws at another number shows that number, without a dot --
        a tick that implies a number the window does not have is the table stating something
        untrue, which is the one thing the tables in this app are not allowed to do.
        """
        item = QTableWidgetItem()
        if r.get("overlay"):
            item.setText(OVERLAY_CELL)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(Qt.ItemFlag.ItemIsSelectable)
            item.setForeground(QColor(128, 128, 128))
            item.setToolTip(OVERLAY_HELP)
            return item
        own = r.get("own_strength")
        comes_back = int(own) if own is not None else self._strength
        at = int(r.get("opacity") or 100)
        ticked = bool(r.get("transparency"))
        elsewhere = ticked and at != comes_back
        shown = at if elsewhere else comes_back
        active = ticked and r.get("status") != "system"
        item.setText(f"{shown} %" + (" \u25be" if active else ""))
        item.setIcon(self._dot_icon if own is None and not elsewhere else self._blank_icon)
        if r.get("status") == "system":
            item.setToolTip(OPACITY_SYSTEM)
        elif not ticked:
            item.setToolTip(OPACITY_NEEDS_TRANSPARENCY)
        elif elsewhere:
            item.setToolTip(f"Drawn at {at} % by a window rule that was not written here. Click "
                            f"to give it a number of its own, which takes it over.")
        else:
            item.setToolTip(OPACITY_SHARED if own is None else OPACITY_OWN)
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled if active
                      else Qt.ItemFlag.ItemIsSelectable)
        return item

    def _opacity_menu(self, r: dict) -> QMenu:
        """The choices for one window: the shared number, a few round ones, or any other.

        A menu rather than a number to type, because a menu is one click and a choice nobody has
        to spell -- and it writes once, where a box written as it settles would write on every
        number on the way. Each line writes the moment it is chosen, like everything else here.
        """
        menu = QMenu(self)
        group = QActionGroup(menu)
        own = r.get("own_strength")
        shared = menu.addAction(f"Same as the others — {self._strength} %")
        shared.setCheckable(True)
        shared.setChecked(own is None)
        shared.setToolTip("The number on the Appearance tab.")
        group.addAction(shared)
        shared.triggered.connect(lambda _=False: self.set_opacity(r, None))
        menu.addSeparator()
        numbers = [n for n in OPACITY_PRESETS if n != self._strength]
        if own is not None and int(own) not in numbers:
            numbers = sorted(set(numbers) | {int(own)}, reverse=True)
        for number in numbers:
            action = menu.addAction(f"{number} %")
            action.setCheckable(True)
            action.setChecked(own is not None and int(own) == number)
            group.addAction(action)
            action.triggered.connect(lambda _=False, n=number: self.set_opacity(r, n))
        menu.addSeparator()
        other = menu.addAction("Other…")
        other.triggered.connect(lambda _=False: self._other_opacity(r))
        return menu

    def _open_opacity_menu(self, row: int) -> None:
        if not (0 <= row < len(self.rows)):
            return
        item = self.table.item(row, COL_OPACITY)
        if item is None or not item.flags() & Qt.ItemFlag.ItemIsEnabled:
            return
        menu = self._opacity_menu(self.rows[row])
        rect = self.table.visualItemRect(item)
        menu.exec(self.table.viewport().mapToGlobal(rect.bottomLeft()))
        menu.deleteLater()

    def _other_opacity(self, r: dict) -> None:
        start = r.get("own_strength")
        start = min(int(start if start is not None else self._strength), 99)
        number, ok = QInputDialog.getInt(
            self, "Opacity",
            f"How solid {r['class']} is while it is see-through, from 1 to 99 %.\n"
            f"100 % is opaque: for that, untick its Transparency instead.",
            start, 1, 99, 1)
        if ok:
            self.set_opacity(r, number)

    def set_opacity(self, r: dict, number: int | None) -> None:
        """Give this window its own number, or `None` to put it back on the shared one. Written
        at once, and the line at the bottom says what went in and what it replaced."""
        name = r["class"]
        own = r.get("own_strength")
        if number == own:
            return
        was = int(own) if own is not None else self._strength
        now = number if number is not None else self._strength
        # Ticks still waiting go first, so one queued a moment ago cannot land after this.
        self.flush()
        if self._busy:
            return
        self._busy = True
        self.copied.emit(f"{name}: opacity {was} % → {now} %…")
        self.table.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            why = self.c.set_own_transparency(name, number)
        finally:
            QApplication.restoreOverrideCursor()
            self.table.setEnabled(True)
            self._busy = False
        if why:
            self.copied.emit("")
            QMessageBox.warning(self, "Opacity not changed", why)
        else:
            self.copied.emit(f"{name}: opacity {was} % → {now} %"
                             + (", the Appearance tab's" if number is None else ""))
        if self._missed:
            self.reload()

    def _summarise(self) -> None:
        """The line under the table: which windows have a number of their own, each a link to
        its row, and what every other one is at."""
        if not self._own:
            self.summary.setText(
                f"Every see-through window is drawn at {self._strength} %, the number on the "
                f"Appearance tab. Click a number under Opacity to give one window its own.")
            return
        known = {r["class"] for r in self._everything}
        parts = []
        for name, number in sorted(self._own.items(), key=lambda pair: pair[0].casefold()):
            label = html.escape(name)
            parts.append(f'<a href="{quote(name)}">{label}</a> {number} %' if name in known
                         else f"{label} {number} %")
        self.summary.setText(f"Own opacity: {', '.join(parts)}. Every other see-through window "
                             f"is at {self._strength} %, the Appearance tab's.")

    def reveal(self, window_class: str) -> bool:
        """Select this class's row, widening the filters just as far as it takes to show it.

        What *Find a window…* and the links under the table both need: the row somebody asked for
        may be hidden by the filter text, by *Only open windows* or by *System windows*, and a
        selection that silently failed would look like the window is not here at all.
        """
        row = next((r for r in self._everything if r["class"] == window_class), None)
        if row is None:
            self.reload()
            row = next((r for r in self._everything if r["class"] == window_class), None)
        if row is None:
            return False
        widened = False
        wanted = self.filter.text().strip().casefold()
        if wanted and wanted not in window_class.casefold() \
                and wanted not in str(row.get("title") or "").casefold():
            self.filter.blockSignals(True)
            self.filter.clear()
            self.filter.blockSignals(False)
            widened = True
        # Each box only ever widened: ticking *System windows* shows more, and so does unticking
        # *Only open windows*.
        for box, state, needed in ((self.show_system, True, row["status"] == "system"),
                                   (self.only_open, False, not row["open"])):
            if needed and box.isChecked() != state:
                box.blockSignals(True)
                box.setChecked(state)
                box.blockSignals(False)
                widened = True
        if widened:
            self.reload()
        self.select(window_class)
        row_index = self.table.currentRow()
        if 0 <= row_index < len(self.rows) and self.rows[row_index]["class"] == window_class:
            self.table.scrollToItem(self.table.item(row_index, COL_CLASS))
            self.table.setFocus()
            return True
        return False

    def _find(self) -> None:
        """Ask the compositor which window gets clicked, the way its own window-rules dialog does.

        **Asked with `callWithCallback` and a slot typed `QVariantMap`, and that was measured.**
        The answer is a dictionary on the bus (`a{sv}`), and this PySide cannot read one out of a
        pending call: `QDBusPendingCallWatcher` hands back a `QDBusArgument` whose entries come out
        as `None` -- tried on `getWindowInfo`, which answers in the same shape. Given a slot that
        names the type, Qt decodes the map itself and it arrives as a `dict`, and a refusal
        arrives on the error slot. Asynchronous either way, which it has to be: the call is
        answered only when somebody clicks.
        """
        message = QDBusMessage.createMethodCall("org.kde.KWin", "/KWin", "org.kde.KWin",
                                                "queryWindowInfo")
        if not QDBusConnection.sessionBus().callWithCallback(
                message, self, SLOT("_found(QVariantMap)"),
                SLOT("_find_failed(QDBusError,QDBusMessage)"), PICK_TIMEOUT_MS):
            self.copied.emit("The desktop did not take the request.")
            return
        self.find.setEnabled(False)
        self.copied.emit("Click the window you mean. Esc cancels.")

    @Slot("QVariantMap")
    def _found(self, info) -> None:
        self.find.setEnabled(True)
        name = str((info or {}).get("resourceClass") or "").strip()
        if not name:
            self.copied.emit("The desktop did not say which application that is.")
            return
        self.window().raise_()
        self.window().activateWindow()
        self.copied.emit(f"Found: {name}" if self.reveal(name)
                         else f"{name} is not a window this table lists.")

    @Slot(QDBusError, QDBusMessage)
    def _find_failed(self, error, _message) -> None:
        self.find.setEnabled(True)
        self.copied.emit(PICK_REFUSALS.get(error.name(),
                                           f"Nothing picked: {error.message() or error.name()}"))

    def flush(self, closing: bool = False) -> None:
        """Send everything that was ticked since the last send.

        One call for the switches and one for the lists, whatever was ticked — so the tiler
        re-reads itself once for the whole batch rather than once per row, and the screen
        rearranges once rather than once per row.

        **And say so while it happens.** Both calls block until the compositor has taken them, and
        a tick in the *Float* column re-tiles every window on the screen; this was the one write of
        that size in the window that went out with nothing said at all. Not while the window is
        closing, though: a line nobody can read is not worth an extra pass of the event loop on a
        window that has already been asked to go away.
        """
        self._batch.stop()
        switches, lists = self._queued_switches, self._queued_lists
        self._queued_switches, self._queued_lists = {}, {}
        if not switches and not lists:
            return
        if self._busy:
            return
        self._busy = True
        rows = len(set(switches) | {c for kind in lists.values() for c in kind})
        if not closing:
            self.copied.emit(f"Applying to {rows} window{'s' if rows != 1 else ''}…")
            self.table.setEnabled(False)
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents()
        taken = False
        try:
            # A list, not `and`: both go out whatever the first one answered.
            taken = all([self.c.set_switches(switches) if switches else True,
                         self.c.set_window_lists(lists) if lists else True])
        finally:
            if not closing:
                QApplication.restoreOverrideCursor()
                self.table.setEnabled(True)
                # Cleared only when both were taken. A refusal is already on the line, put there
                # by the client, and clearing it here unconditionally erased the reason the same
                # instant it appeared.
                if taken:
                    self.copied.emit("")
            self._busy = False
        # A refusal repaints from the daemon too, or the boxes go on showing ticks the desk
        # never took.
        if (self._missed or not taken) and not closing:
            self.reload()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 -- Qt's spelling
        if watched is self.table.viewport() and event.type() == QEvent.Type.MouseButtonPress:
            self._pressed_at = event.position().toPoint()
        if (watched is self.table and event.type() == QEvent.Type.KeyPress
                and self.table.currentColumn() == COL_OPACITY
                and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_F2,
                                    Qt.Key.Key_Menu)):
            self._open_opacity_menu(self.table.currentRow())
            return True
        return super().eventFilter(watched, event)

    def _clicked(self, item: QTableWidgetItem) -> None:
        if item.column() == COL_OPACITY:
            self._open_opacity_menu(item.row())
        else:
            self._maybe_copy(item)

    def _context_menu(self, at) -> None:
        item = self.table.itemAt(at)
        if item is not None and item.column() == COL_OPACITY:
            self._open_opacity_menu(item.row())

    def _copy(self, window_class: str) -> None:
        QGuiApplication.clipboard().setText(window_class)
        self.copied.emit(f"Copied: {window_class}")

    def _copy_selected(self) -> None:
        window_class = self.selected_class()
        if window_class:
            self._copy(window_class)

    def _maybe_copy(self, item: QTableWidgetItem) -> None:
        """Copy the class, but only from the mark itself.

        Clicking the first column is also how a row is selected, so copying on any click in it
        meant reading about a window took whatever was on the clipboard away. The mark is where
        the pointer already is when it shows; the rest of the cell selects, as it looks like it
        should.
        """
        if item.column() != COL_CLASS or not (0 <= item.row() < len(self.rows)):
            return
        rect = self.table.visualItemRect(item)
        at = self._pressed_at
        if at is None or not (rect.left() <= at.x() <= rect.left() + MARK_WIDTH):
            return
        self._copy(self.rows[item.row()]["class"])

    def selected_class(self) -> str | None:
        row = self.table.currentRow()
        return self.rows[row]["class"] if 0 <= row < len(self.rows) else None

    def select(self, window_class: str) -> None:
        for i, r in enumerate(self.rows):
            if r["class"] == window_class:
                self.table.selectRow(i)
                return

    def _selection(self) -> None:
        """The line under the table: the window, and only what is worth saying about it.

        It used to say four things in the app's own vocabulary and say them always -- including
        "governed by" and the name of the pattern, which on almost every row is the window's own
        name printed a second time. Now each clause appears only when it is not the ordinary case.
        """
        row = self.table.currentRow()
        if not (0 <= row < len(self.rows)):
            self.detail.setText("Nothing selected." if self.rows
                                else "No window matches what is shown above.")
            return
        r = self.rows[row]
        if r["status"] == "refuses":
            self.detail.setText(f"<b>{r['class']}</b> · {REFUSES_HELP}")
            return
        parts = [f"<b>{r['class']}</b>"]
        if not r["pattern"]:
            parts.append("KyprX has not set this one up yet")
        elif r["pattern"] != r["class"]:
            parts.append(f"set up under the name <code>{r['pattern']}</code>")
        if r["shared"]:
            parts.append("that name covers other windows too, so changing this one here gives it "
                         "an entry of its own")
        if r["skipped"]:
            parts.append("left alone because it is: " + ", ".join(r["skipped"]))
        if r.get("own_strength") is not None:
            parts.append(f"its own opacity, {r['own_strength']} %, which the Appearance tab's "
                         f"does not reach")
        if not r["open"]:
            parts.append("not open right now")
        self.detail.setText(" · ".join(parts))
