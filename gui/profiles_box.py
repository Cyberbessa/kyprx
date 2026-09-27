"""The Appearance tab's Profiles box: a look kept under a name, and what can be done with one.

`ProfilesBox` lists the profiles the daemon keeps, the one the desktop is wearing in bold, and
saves, updates, renames, deletes and loads them. Loading changes what the page around it shows, so
the box is built with that page and repaints it -- the one box here that reaches into its page.
`look_icon` draws a profile's colours for this list and for the drop-down above the tabs.
"""

from __future__ import annotations

import html

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QIcon, QPainter, QPainterPath, QPen,
                           QPixmap)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QHBoxLayout, QHeaderView,
                               QInputDialog, QLabel, QMessageBox, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from client import Client
from colours_box import scheme_colours
from fields import OUTLINE_STYLES
from form import SettingsPage
from widgets import SECTION_HINTS, Section


# ---------------------------------------------------------------------- profiles

def look_icon(swatch: list, accent: str) -> QIcon:
    """A strip of a profile's colours, for its row: the preset's four, and the colour of its own
    beside them when it has one. Drawn from the same four colours the swatch grid draws."""
    width, height = 48, 16
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    box = QRectF(0.5, 0.5, width - 1.0, height - 1.0)
    bands = scheme_colours(swatch)
    if not bands:
        # The scheme is not on this machine: an outline, rather than a plausible strip in the
        # interface's own colours.
        painter.setPen(QPen(QGuiApplication.palette().mid().color(), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(box, 3, 3)
    else:
        if accent.count(",") == 2:
            bands.append(QColor(*(int(x) for x in accent.split(","))))
        clip = QPainterPath()
        clip.addRoundedRect(box, 3, 3)
        painter.setClipPath(clip)
        band = width / len(bands)
        for i, colour in enumerate(bands):
            painter.fillRect(QRectF(i * band, 0, band + 1, height), colour)
    painter.end()
    return QIcon(pixmap)


def number_words(value) -> str:
    """`2.5` for `"2.50"`, and whatever it was when it is not a number."""
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value or "?")


class ProfilesBox(Section):
    """The profiles: the look under a name, and the five things to do with one.

    Its own reads and writes, the shape `ThemeBox` and `TransparencyRow` take, and for the same
    reason: a profile is not a `(source, group, key)` triple and the form engine has nothing to say
    about it. Loading is the one write here that changes what the boxes and the form beside it
    show -- the strength, the radius and the outline are controls on this very page -- so a load
    clears the form's touched set and repaints the page. The person asked for the profile; a field half edited before that must
    not outlive the request and go back into the file with the next write.

    The row in bold is the profile the desktop is wearing, and the daemon decides that with the
    same comparison a load makes, so the bold row and "loading it changes nothing" are one fact.
    """

    COLUMNS = ["Profile", "Colours", "Opacity", "Frame"]

    def __init__(self, client: Client, page: SettingsPage, parent=None):
        super().__init__("Profiles", SECTION_HINTS["Profiles"], parent)
        self.c = client
        self.page = page
        self._data: dict = {}
        self._entries: list[dict] = []
        self._busy = False

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setFrameShape(QTableWidget.Shape.NoFrame)   # as the other tables
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # The page already scrolls; a table scrolling inside it is a trap for the wheel. So the
        # table takes the height of its rows, and the rows wrap.
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setWordWrap(True)
        self.table.setIconSize(QSize(48, 16))
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for column in range(1, len(self.COLUMNS)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self._sync)
        self.table.itemDoubleClicked.connect(lambda _item: self._load())

        self.save_button = QPushButton("Save what is on the desktop as…")
        self.load_button = QPushButton("Load")
        self.update_button = QPushButton("Update")
        self.rename_button = QPushButton("Rename…")
        self.delete_button = QPushButton("Delete")
        self.save_button.clicked.connect(self._save_as)
        self.load_button.clicked.connect(self._load)
        self.update_button.clicked.connect(self._update)
        self.rename_button.clicked.connect(self._rename)
        self.delete_button.clicked.connect(self._delete)
        self.save_button.setToolTip("Keep what is on the desktop now under a name of your own.")
        self.load_button.setToolTip("Put the selected profile on the desktop. The desktop's own "
                                    "colour tools take a second or two. Double-clicking a row "
                                    "does the same.")
        self.update_button.setToolTip("Overwrite the selected profile with what is on the "
                                      "desktop now.")
        self.rename_button.setToolTip("Give the selected profile another name.")
        self.delete_button.setToolTip("Forget the selected profile. The desktop does not change.")
        #: Enter on a selected row loads it, which is also what the double-click does.
        self.load_button.setDefault(True)
        #: The stretch before *Delete* and not after the row: the one button here that cannot be
        #: undone sits away from the four that can.
        actions = QHBoxLayout()
        for button in (self.save_button, self.load_button, self.update_button,
                       self.rename_button):
            actions.addWidget(button)
        actions.addStretch()
        actions.addWidget(self.delete_button)

        self.line = QLabel()
        self.line.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addLayout(actions)
        layout.addWidget(self.line)

    # ---------------------------------------------------------------- painting it

    def reload(self, data: dict | None = None) -> None:
        """Paint the list from the daemon's answer. One read, and nothing written.

        `data` is the answer the window already has: the strip at the top draws from the same
        `Profiles` call, and that call is the expensive one -- 4 ms empty and about 2 ms more a
        profile, against 0.1 for the settings. Asked for here as well, every change the daemon
        reports would pay for it twice while this tab is open.
        """
        if self._busy:
            return
        self._data = (self.c.profiles() if data is None else data) or {}
        self._entries = [e for e in (self._data.get("profiles") or []) if isinstance(e, dict)]
        selected = self.selected_name()
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        bold = QFont()
        bold.setBold(True)
        dim = self.palette().mid().color()
        for row, entry in enumerate(self._entries):
            self.table.insertRow(row)
            look = entry.get("look") or {}
            colours = look.get("theme") or {}
            cells = [QTableWidgetItem(look_icon(entry.get("swatch") or [],
                                                str(colours.get("accent") or "")),
                                      str(entry.get("name") or ""))]
            cells += [QTableWidgetItem(text) for text in self._summary(entry)]
            for column, item in enumerate(cells):
                if entry.get("current"):
                    item.setFont(bold)
                if entry.get("trouble"):
                    item.setForeground(dim)
                    item.setToolTip(str(entry["trouble"]))
                self.table.setItem(row, column, item)
        self.table.setVisible(bool(self._entries))
        self.table.resizeRowsToContents()
        self._fit()
        if selected:
            self.select(selected)
        self.table.blockSignals(False)
        self._sync()

    def _fit(self) -> None:
        """The height of the rows and the header, and no more -- see the scroll policy above."""
        height = self.table.horizontalHeader().height() + 2
        for row in range(self.table.rowCount()):
            height += self.table.rowHeight(row)
        self.table.setFixedHeight(height)

    def resizeEvent(self, event) -> None:  # noqa: N802 — Qt's spelling
        # The cells wrap, so a narrower window means taller rows, and a height fixed at the last
        # reload would clip the last of them.
        super().resizeEvent(event)
        self.table.resizeRowsToContents()
        self._fit()

    @staticmethod
    def _summary(entry: dict) -> list[str]:
        """The three cells after the name, read out of the look rather than remembered."""
        look = entry.get("look") or {}
        colours = look.get("theme") or {}
        windeco = (look.get("klassy") or {}).get("Windeco") or {}
        outline = (look.get("klassy") or {}).get("WindowOutlineStyle") or {}

        parts = [str(colours.get("mode") or "?").capitalize(),
                 str(entry.get("preset_name") or colours.get("preset") or "(no preset)")]
        accent = str(colours.get("accent") or "")
        tint = float(colours.get("tint") or 0)
        if accent:
            parts.append(f"your colour {accent}"
                         + (f", soaking {int(round(tint * 100))} %" if tint > 0 else ""))
        else:
            parts.append("the preset's own colours")
        theme_words = " · ".join(parts)

        strength = look.get("transparency")
        if strength is None:
            # A profile from before the strength was carried. It reads as "on" whatever the
            # strength is, and *Update with the current look* is how it acquires one.
            strength_words = "as it is"
        elif int(strength) >= 100:
            strength_words = "opaque"
        else:
            strength_words = f"{int(strength)} %"

        styles = dict(OUTLINE_STYLES)
        active = str(outline.get("WindowOutlineStyleActive") or "?")
        inactive = str(outline.get("WindowOutlineStyleInactive") or "?")
        frame_words = (f"radius {number_words(windeco.get('WindowCornerRadius'))} px · outline "
                       f"{number_words(outline.get('WindowOutlineThickness'))} px, "
                       f"{styles.get(active, active)} / {styles.get(inactive, inactive)}")
        return [theme_words, strength_words, frame_words]

    def selected_name(self) -> str:
        item = self.table.item(self.table.currentRow(), 0) if self.table.selectedItems() else None
        return item.text() if item else ""

    def selected(self) -> dict | None:
        name = self.selected_name()
        return next((e for e in self._entries if e.get("name") == name), None) if name else None

    def select(self, name: str) -> None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == name:
                self.table.selectRow(row)
                return

    def _named(self, name: str) -> dict | None:
        """The profile this name means, spelled however it is -- the daemon's own rule."""
        wanted = name.strip().casefold()
        return next((e for e in self._entries
                     if str(e.get("name") or "").casefold() == wanted), None)

    def _sync(self) -> None:
        """The buttons say what can be done with the selected row, and the line says where the
        desktop stands."""
        entry = self.selected()
        current = bool(entry and entry.get("current"))
        trouble = bool(entry and entry.get("trouble"))
        self.load_button.setEnabled(entry is not None and not current and not trouble)
        self.update_button.setEnabled(entry is not None and not current)
        self.rename_button.setEnabled(entry is not None)
        self.delete_button.setEnabled(entry is not None)
        if self._busy:
            return
        if self._data.get("trouble"):
            self.line.setText(html.escape(str(self._data["trouble"])))
            return
        if not self._entries:
            self.line.setText("No profiles yet. <i>Save what is on the desktop as…</i> keeps "
                              "this tab under a name of your own.")
            return
        on = next((e for e in self._entries if e.get("current")), None)
        text = (f"<b>{html.escape(str(on['name']))}</b> is what is on the desktop now." if on
                else "None of these is what is on the desktop now.")
        if trouble:
            text += (f" <b>{html.escape(str(entry['name']))}</b> cannot be loaded here: "
                     f"{html.escape(str(entry['trouble']))}.")
        self.line.setText(text)

    # ---------------------------------------------------------------- doing things

    def _done(self, answer: str) -> None:
        """What the daemon said, or the list again. A refusal stays on the line until the next
        reload; a success is a row appearing, in bold when it is the look on the desktop."""
        if answer:
            self.line.setText(html.escape(answer))
        else:
            self.reload()

    def _sure(self, question: str, detail: str) -> bool:
        """True when the answer was **no**, which is what every caller here wants to know.

        `No` is the default button, on purpose and everywhere in this window: a dialog that goes
        away on Enter should not be one that has just deleted something.
        """
        box = QMessageBox(QMessageBox.Icon.Question, question, detail,
                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        return box.exec() != QMessageBox.StandardButton.Yes

    def _save_as(self) -> None:
        worn = (self._data.get("worn") or {}).get("theme") or {}
        suggested = str(worn.get("preset") or "").replace("-", " ").title()
        name, ok = QInputDialog.getText(self, "Save this profile",
                                        "A name for it:", text=suggested)
        if not ok or not name.strip():
            return
        existing = self._named(name)
        if existing is not None and self._sure(
                "Replace this profile?",
                f"There is already a profile called {existing['name']}. Replace it with what is "
                f"on the desktop now?"):
            return
        self._done(self.c.save_profile(name.strip(), replace=existing is not None))

    def _update(self) -> None:
        entry = self.selected()
        if entry is None or self._sure("Update this profile?",
                                       f"Overwrite {entry['name']} with what is on the desktop "
                                       f"now?"):
            return
        self._done(self.c.save_profile(entry["name"], replace=True))

    def _rename(self) -> None:
        entry = self.selected()
        if entry is None:
            return
        name, ok = QInputDialog.getText(self, "Rename this profile", "A new name for it:",
                                        text=entry["name"])
        if not ok or not name.strip() or name.strip() == entry["name"]:
            return
        self._done(self.c.rename_profile(entry["name"], name.strip()))

    def _delete(self) -> None:
        entry = self.selected()
        if entry is None or self._sure("Delete this profile?",
                                       f"Delete {entry['name']}? The desktop does not change, "
                                       f"and there is no way back."):
            return
        self._done(self.c.delete_profile(entry["name"]))

    def _load(self) -> None:
        entry = self.selected()
        if entry is None or entry.get("trouble") or entry.get("current"):
            return
        self._busy = True
        # The window's line, in the same words the strip uses for the same act. This box's own
        # line says which profile is on, which is a different thing and stays where it is.
        self.page.says.emit(f"Putting <b>{html.escape(entry['name'])}</b> on… the desktop's own "
                            f"tools take a second or two")
        self.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        # One pass of the event loop so the line above is on screen. The call below blocks for as
        # long as the desktop's tools take -- measured, about 1.7 s for a profile that moves the
        # colours and the outline -- and a window that freezes with nothing said is a window that
        # looks broken. Re-entry is what `_busy` is for.
        QApplication.processEvents()
        try:
            answer = self.c.load_profile(entry["name"])
        finally:
            QApplication.restoreOverrideCursor()
            self.setEnabled(True)
            self._busy = False
        self.page.says.emit("" if not answer else html.escape(answer))
        if answer:
            return
        # The load wrote keys this page has controls for. The form refuses to repaint while a field
        # is touched, and here the touched field is the one the person just asked to replace.
        self.page.touched.clear()
        QTimer.singleShot(400, lambda: self.page.load(self.page.c.groups()))
