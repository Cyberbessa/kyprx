"""The Shortcuts tab: the fixed list of shortcuts that make a tiling setup usable, and editing them.

Every key is bound through the daemon, which asks the shortcut registry and refuses one another
action holds unless the tab asks to take it. The one call this window makes to the registry itself
is `ShortcutBlock`'s: while a row listens for keys, every global shortcut on the desktop is
suspended -- counted, so two rows listening at once hand them back only when both are done, and
released whichever way the window closes. `ShortcutRow` turns what was pressed into the registry's
key codes, which is where the arithmetic on Qt's key bits lives.
"""

from __future__ import annotations

import html

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtDBus import QDBusConnection, QDBusInterface
from PySide6.QtGui import QFont, QKeySequence
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QHBoxLayout, QHeaderView,
                               QKeySequenceEdit, QLabel, QMessageBox, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from cheatsheet import action_label, key_text
from client import Client
from widgets import Choice, note


KROHNKITE_DOCS = "https://github.com/anametologin/krohnkite#readme"


# ---------------------------------------------------------------------- shortcuts

class ShortcutBlock:
    """The desktop's shortcuts, suspended while anything here is capturing a key.

    Counted rather than a plain flag, because two rows can be in edit mode at once: the one that
    leaves first would otherwise hand the desktop's shortcuts back while the other is still
    waiting for a key. Leaving them blocked is the worse of the two faults, so `release_all` runs
    on the way out no matter which way the window closes.
    """

    _held = 0

    @classmethod
    def _tell(cls, blocked: bool) -> None:
        QDBusInterface("org.kde.kglobalaccel", "/kglobalaccel", "org.kde.KGlobalAccel",
                       QDBusConnection.sessionBus()).call("blockGlobalShortcuts", blocked)

    @classmethod
    def hold(cls) -> None:
        cls._held += 1
        if cls._held == 1:
            cls._tell(True)

    @classmethod
    def release(cls) -> None:
        if cls._held == 0:
            return
        cls._held -= 1
        if cls._held == 0:
            cls._tell(False)

    @classmethod
    def release_all(cls) -> None:
        if cls._held:
            cls._held = 0
            cls._tell(False)


#: What a row says when its capture stops because the window lost the keyboard. On this desk focus
#: follows the mouse: a pointer that drifts off the window takes the keys with it, and the editor
#: used to give up with no word at all -- the keys landed in another window, the row sat on
#: *Cancel*, and every shortcut on the desktop stayed suspended.
FOCUS_LOST_TOLD = ("{name}: stopped listening, because this window lost the keyboard -- with "
                   "focus following the mouse, keep the pointer over this window while you press "
                   "the keys.")

#: And when the key pressed was AltGr. On the Brazilian layout the right Alt is AltGr, which Qt
#: records as a key of its own rather than as Alt -- so Meta and the right Alt and Left captured as
#: Meta+AltGr, and the arrow was dropped.
ALTGR_TOLD = ("{name}: the right Alt is AltGr on this keyboard layout, and a shortcut cannot use "
              "it. Press the left Alt instead.")

#: The keys that are fine on their own: F-keys, and the special keys -- volume, media, brightness,
#: launchers -- that type nothing. Anything else without Meta, Ctrl or Alt would stop reaching
#: every application once it is a shortcut for the whole desktop, so it is asked about first.
F_KEYS = range(0x01000030, 0x01000053)
SPECIAL_KEYS_FROM = 0x01000060
MODIFIER_BITS = 0x10000000 | 0x04000000 | 0x08000000
KEY_BITS = 0x01FFFFFF


class ShortcutRow(QWidget):
    """One shortcut: what it is bound to now, and two ways to change it on purpose.

    Editing is a mode you enter and can leave. That matters here more than in most editors,
    because entering it suspends every global shortcut on the desktop.

    *Remove* is the other way, and it is not the same as binding nothing: an action can carry a
    second key, and removing takes the first away and leaves the rest alone.

    **Leaving the mode is the row's job, not the editor's**, and every way out is one this row
    handles before the editor sees the key. The editor -- Qt's own -- records Esc as a key like any
    other, so the Esc that was promised to cancel bound Esc instead; it ends on Tab with nothing;
    and it gives up in silence when the window loses the keyboard. See `eventFilter`.
    """

    #: (component, action, the key being replaced, the key replacing it) -- by value, because on
    #: Plasma 6.7 the order an action's keys come back in is not a fact about anything.
    rebound = Signal(str, str, list, list)
    chose = Signal(str, list)
    #: Entered or left the mode that suspends every shortcut on the desktop. The tab says so.
    editing = Signal()
    #: A line for the window's footer: why a capture stopped, when it stopped by itself.
    told = Signal(str)

    def __init__(self, action: dict, parent=None):
        super().__init__(parent)
        self.action_id = action["id"]
        self.component = action.get("component", "kwin")
        self.action_key = action.get("key", action["id"])
        self.name = action_label(action.get("name") or action["id"])
        self.keys = action["keys"]
        self._editing = False

        self.label = QLabel()
        self.label.setMinimumWidth(96)
        self.editor = QKeySequenceEdit()
        self.editor.setMaximumSequenceLength(1)
        self.editor.setVisible(False)
        self.editor.keySequenceChanged.connect(self._captured)
        self.editor.installEventFilter(self)
        self.button = QPushButton("Edit")
        self.button.setMaximumWidth(72)
        self.button.setToolTip("Press it, then press the keys you want. Esc leaves this one as "
                               "it was.")
        self.button.clicked.connect(self._toggle)
        self.remove_button = QPushButton("Remove")
        self.remove_button.setMaximumWidth(80)
        self.remove_button.setToolTip("Take this key away. A second key, if there is one, stays.")
        self.remove_button.clicked.connect(self._remove)

        #: Only for the actions that carry more than one combination, and only about the card —
        #: nothing here rebinds anything. The desktop gives KRunner three keys, and the first one
        #: it lists is the dedicated Search key, which is not the one most keyboards have.
        self.on_card = None
        if len(self.keys) > 1:
            self.on_card = Choice()
            self.on_card.setToolTip("Which of these appears on the cheatsheet")
            for sequence in self.keys:
                self.on_card.addItem(key_text(sequence), sequence)
            shown = action.get("show") or self.keys[0]
            index = self.on_card.findData(shown)
            self.on_card.setCurrentIndex(index if index >= 0 else 0)
            self.on_card.currentIndexChanged.connect(self._chose)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.label)
        row.addWidget(self.editor)
        row.addStretch()
        if self.on_card is not None:
            row.addWidget(QLabel("on the card:"))
            row.addWidget(self.on_card)
        row.addWidget(self.button)
        row.addWidget(self.remove_button)
        self._show_current()

    def _chose(self) -> None:
        self.chose.emit(self.action_key, list(self.on_card.currentData() or []))

    def _show_current(self) -> None:
        text = " / ".join(key_text(k) for k in self.keys) or "not bound"
        self.label.setText(text)
        self.label.setEnabled(bool(self.keys))
        # Hidden and not greyed on a row with no key. A dead button on every unbound action was
        # the loudest thing on this tab, and it offered to take away something that is not there.
        self.remove_button.setVisible(bool(self.keys) and not self._editing)

    def _toggle(self) -> None:
        self.stop() if self._editing else self.start()

    def start(self) -> None:
        self._editing = True
        ShortcutBlock.hold()
        self.label.setVisible(False)
        self.editor.setVisible(True)
        self.editor.clear()
        self.editor.setFocus(Qt.FocusReason.OtherFocusReason)
        self.button.setText("Cancel")
        self.remove_button.setVisible(False)
        self.editing.emit()

    def stop(self) -> None:
        """Leave edit mode without changing anything."""
        if not self._editing:
            return
        self._editing = False
        ShortcutBlock.release()
        self.editor.setVisible(False)
        self.label.setVisible(True)
        self.button.setText("Edit")
        self._show_current()
        self.editing.emit()

    def eventFilter(self, watched, event):  # noqa: N802 — Qt's spelling
        """Every way out of listening, caught before Qt's editor turns it into a key.

        * **Esc, Tab and Shift+Tab on their own cancel.** The editor records Esc as a shortcut and
          ends on Tab with nothing, so the Esc the tooltip promised would cancel bound Esc as a key
          for the whole desktop -- after which *Remove* is the obvious next click, and the action
          is left with no key at all. With Meta, Ctrl or Alt held they are ordinary keys.
        * **AltGr is refused, saying why.** See `ALTGR_TOLD`.
        * **Losing the keyboard stops listening, saying why** -- unless it went to this row's own
          *Cancel*, which is somebody cancelling and does that itself. See `FOCUS_LOST_TOLD`.
        """
        if watched is self.editor and self._editing:
            kind = event.type()
            if kind == QEvent.Type.KeyPress:
                key = event.key()
                held = event.modifiers() & (Qt.KeyboardModifier.ControlModifier
                                            | Qt.KeyboardModifier.AltModifier
                                            | Qt.KeyboardModifier.MetaModifier)
                if key in (Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab) and not held:
                    self.stop()
                    self.told.emit(f"{html.escape(self.name)}: left as it was.")
                    return True
                if (key == Qt.Key.Key_AltGr
                        or event.modifiers() & Qt.KeyboardModifier.GroupSwitchModifier):
                    self.stop()
                    self.told.emit(ALTGR_TOLD.format(name=html.escape(self.name)))
                    return True
            elif kind == QEvent.Type.FocusOut:
                if QApplication.focusWidget() is not self.button:
                    self.stop()
                    self.told.emit(FOCUS_LOST_TOLD.format(name=html.escape(self.name)))
        return super().eventFilter(watched, event)

    def _captured(self, sequence: QKeySequence) -> None:
        if not self._editing or sequence.isEmpty():
            return
        combined = sequence[0].toCombined()
        self.stop()
        key = combined & KEY_BITS
        if key == int(Qt.Key.Key_AltGr.value):
            self.told.emit(ALTGR_TOLD.format(name=html.escape(self.name)))
            return
        if not combined & MODIFIER_BITS and key not in F_KEYS and key < SPECIAL_KEYS_FROM:
            shown = html.escape(key_text([combined]))
            box = QMessageBox(QMessageBox.Icon.Question, "Use a key on its own?",
                              f"<b>{shown}</b> on its own would become a shortcut for the whole "
                              f"desktop, and stop reaching every application while "
                              f"<b>{html.escape(self.name)}</b> holds it.<br><br>Use it anyway?",
                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
            box.setDefaultButton(QMessageBox.StandardButton.No)
            if box.exec() != QMessageBox.StandardButton.Yes:
                self.told.emit(f"{html.escape(self.name)}: left as it was.")
                return
        old = self.keys[0] if self.keys else []
        self.keys = [[combined]] + [k for k in self.keys if k != old]
        self._show_current()
        self.rebound.emit(self.component, self.action_id, old, [combined])

    def _remove(self) -> None:
        if not self.keys:
            return
        old = self.keys[0]
        self.keys = self.keys[1:]
        self._show_current()
        self.rebound.emit(self.component, self.action_id, old, [])


class ShortcutsTab(QWidget):
    """The shortcuts that make a tiling setup usable, in one fixed list.

    Fixed on purpose: the compositor publishes dozens of actions nobody binds, and what makes a
    shortcut core is that someone chose it. Editing goes straight through the shortcut registry —
    the file it lives in is rewritten by the compositor at logout, so writing that would be a
    change that quietly undoes itself.

    The cheatsheet's own key is a row here like any other. It used to be a control of its own
    above the table, wired to an action name the daemon did not answer to, so pressing *Edit* on
    it could only ever fail.
    """

    #: A line for the window's footer: what changed, or why nothing did.
    says = Signal(str)

    def __init__(self, client: Client, parent=None):
        super().__init__(parent)
        self.c = client
        self.table = QTableWidget(0, 2)
        self.table.setFrameShape(QTableWidget.Shape.NoFrame)   # as the Windows tab's, same reason
        self.table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        # The action names are short and of known length; the keys, their editor and two buttons
        # are what needs the room. Stretching the names instead left the controls crushed against
        # the right edge with half the window blank beside a one-word label.
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        self.rows: list[ShortcutRow] = []

        #: One line and the one link on this tab. What used to be here as well -- that an action
        #: with a second key keeps it, what *Remove* takes away, what *on the card* decides -- is
        #: on the buttons themselves, where somebody about to press one will actually read it.
        line = note(f'Press <b>Edit</b>, then the keys you want. The tiling actions come from '
                    f'<a href="{KROHNKITE_DOCS}">the tiling script</a>; the rest are the '
                    f'desktop\'s own.')
        line.setOpenExternalLinks(True)

        #: The one genuinely dangerous state this window can be in, and nothing on screen used to
        #: say so: while a row is listening, every shortcut on the desktop is suspended.
        self.capturing = QLabel("<b>Listening for keys.</b> The desktop's own shortcuts are "
                                "paused while this row waits.")
        self.capturing.setWordWrap(True)
        self.capturing.setVisible(False)

        layout = QVBoxLayout(self)
        layout.addWidget(line)
        layout.addWidget(self.capturing)
        layout.addWidget(self.table)

    def reload(self) -> None:
        if any(row._editing for row in self.rows):
            return          # someone is in the middle of pressing a key
        data = self.c.shortcuts()
        self.rows = []
        actions = data.get("actions") or []
        rows = []
        group = None
        for action in actions:
            if action["group"] != group:
                group = action["group"]
                rows.append(("header", group, None))
            rows.append(("action", action_label(action["name"]), action))
        self.table.setRowCount(len(rows))
        for i, (kind, label, action) in enumerate(rows):
            item = QTableWidgetItem(label)
            if kind == "header":
                font = QFont()
                font.setBold(True)
                item.setFont(font)
                self.table.setItem(i, 0, item)
                self.table.setItem(i, 1, QTableWidgetItem(""))
                self.table.setCellWidget(i, 1, None)
                continue
            self.table.setItem(i, 0, item)
            row = ShortcutRow(action)
            extra = action["keys"][1:]
            if extra:
                row.setToolTip("also bound to " + ", ".join(key_text(k) for k in extra))
            row.rebound.connect(self._bind)
            row.chose.connect(self._choose)
            row.editing.connect(self._say_capturing)
            row.told.connect(self.says)
            self.rows.append(row)
            self.table.setCellWidget(i, 1, row)
        self.table.resizeRowsToContents()

    def _bind(self, component: str, action_id: str, old: list[int], new: list[int]) -> None:
        """Bind it -- asking first when another action holds the key -- and say what changed.

        **Asked, because nothing else will.** On Plasma 6.7 the shortcut registry keeps a key two
        actions share without a word, and when it is pressed runs the one registered first. So
        before binding, the daemon is asked who holds the key, and a holder is named: *Use it
        here* takes it away from them and binds it here, in one change; *Cancel* leaves both
        as they were. That is what the desktop's own shortcut settings do.

        The row paints the new key before the answer comes back, which is right -- the alternative
        is a row that does nothing for as long as the bus takes. When the answer is no, or when
        this is a dry run and nothing was bound, the row is read back from the registry, so it
        never goes on printing a key that is not there. And the footer says what changed, *Remove*
        included: a key that disappeared in one click used to leave no trace at all.
        """
        row = next((r for r in self.rows if (r.component, r.action_id) == (component, action_id)),
                   None)
        name = html.escape(row.name if row else action_id)
        owners: list = []
        if new:
            owners = self.c.shortcut_holders(component, action_id, new)
            if owners is None:
                self.reload()
                return
            if owners:
                who = html.escape(", ".join(f"{h.get('name')} ({h.get('component_name')})"
                                            for h in owners))
                box = QMessageBox(QMessageBox.Icon.Question, "That key is already in use",
                                  f"<b>{html.escape(key_text(new))}</b> is used by {who}."
                                  f"<br><br>Use it for <b>{name}</b> instead? It is taken away "
                                  f"from {who}. Kept on both, only one of them would run.",
                                  QMessageBox.StandardButton.Yes
                                  | QMessageBox.StandardButton.Cancel, self)
                box.button(QMessageBox.StandardButton.Yes).setText("Use it here")
                box.setDefaultButton(QMessageBox.StandardButton.Cancel)
                if box.exec() != QMessageBox.StandardButton.Yes:
                    self.says.emit(f"{name}: left as it was.")
                    self.reload()
                    return
        done = self.c.rebind_shortcut(component, action_id, old, new, take=bool(owners))
        if done:
            self.says.emit(f"{name}: {html.escape(key_text(old) or 'none')} → "
                           f"{html.escape(key_text(new) or 'none')}")
        if not done or self.c.dry_run():
            self.reload()

    def _choose(self, action_key: str, keys: list[int]) -> None:
        self.c.set_cheatsheet_key(action_key, keys)

    def _say_capturing(self) -> None:
        """The band above the table, while any row is waiting for a key."""
        self.capturing.setVisible(any(row._editing for row in self.rows))

    def stop_editing(self) -> None:
        """Make sure no row is left holding the desktop's shortcuts hostage.

        Called when this tab is left as well as when the window closes. A desk whose every key is
        dead, with nothing on screen but one button somewhere reading *Cancel*, is the worst state
        this window can walk away from.
        """
        for row in self.rows:
            row.stop()
        ShortcutBlock.release_all()
        self.capturing.setVisible(False)
