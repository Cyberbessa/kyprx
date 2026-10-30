"""The questions the window asks before a change that writes a great deal.

`ChangesDialog` asks one -- *Restore defaults*, *Take KyprX off this desk*, *Put my setup back* --
with the daemon's own list of what would change underneath, in the words a dry run uses, and the
safe answer as the default. `CopiesDialog` lists the copies of the desk, newest first, and shows
what going back to the one selected would change. `RemoveDialog` asks the two questions removing
KyprX from this computer needs, with nothing chosen for either, and `RemovedDialog` says what was
done and the command that finishes it. `UpdateDialog` says a newer KyprX is out and how this
installation takes it: *Update now* for a working tree, the command to copy for a package. And
`AboutDialog`, which asks nothing: which KyprX this is, what it is built on and who made what it
works with.
"""

from __future__ import annotations

import html

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QDialogButtonBox, QGroupBox,
                               QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPlainTextEdit,
                               QPushButton, QRadioButton, QVBoxLayout)

from client import Client
from widgets import note


#: What the list under a question says when the list is empty. Said rather than left blank: an
#: empty box under "exactly what would change" reads as the list having failed to arrive.
NOTHING_CHANGES = "Nothing would change: everything already reads this way."


class ChangesDialog(QDialog):
    """A question asked before a big write, with what it would change listed underneath.

    The list is the daemon's own, worked out the way a dry run works it out and written in the same
    words, so what is shown is what would be written rather than a description of the button. The
    safe answer is the default one, as it was for the plain question this replaces.
    """

    def __init__(self, parent, title: str, question: str, changes: str, go: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        asked = note(question)
        asked.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(asked)
        listing = QPlainTextEdit(changes.strip("\n") or NOTHING_CHANGES)
        listing.setReadOnly(True)
        mono = QFont("monospace")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        listing.setFont(mono)
        listing.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        listing.setMinimumSize(640, 280)
        layout.addWidget(listing, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.go = buttons.addButton(go, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class CopiesDialog(QDialog):
    """The copies of the desk, newest first, and what going back to the one selected would change.

    One list and one box under it, rather than a menu: which copy to go back to is decided by
    reading what it would change, and a menu would make that a second step behind each entry.
    """

    def __init__(self, parent, client: Client, listing: list[dict]):
        super().__init__(parent)
        self.c = client
        self.setWindowTitle("Go back to a copy of the desk")
        layout = QVBoxLayout(self)
        layout.addWidget(note(
            "A copy is kept before every change that writes a great deal at once. Going back "
            "puts the desk back exactly as it was then — and keeps a copy of it as it is now, so "
            "going back can be undone too."))
        self.copies = QListWidget()
        for copy in listing:
            when = copy.get("when", "").replace("T", " ")
            shown = f"{when}  —  {copy.get('why', '')}"
            if copy.get("in_memory"):
                shown += "  (dry run: in memory only)"
            if copy.get("trouble"):
                shown += f"  ({copy['trouble']})"
            item = QListWidgetItem(shown)
            item.setData(Qt.ItemDataRole.UserRole, copy.get("name", ""))
            if copy.get("trouble"):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.copies.addItem(item)
        layout.addWidget(self.copies)
        self.changes = QPlainTextEdit()
        self.changes.setReadOnly(True)
        mono = QFont("monospace")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.changes.setFont(mono)
        self.changes.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.changes.setMinimumSize(640, 220)
        self.changes.setPlaceholderText("Choose a copy to see what going back to it would change.")
        layout.addWidget(self.changes, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.go = buttons.addButton("Go back to this copy", QDialogButtonBox.ButtonRole.AcceptRole)
        self.go.setEnabled(False)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.copies.currentItemChanged.connect(self._chosen)

    def chosen(self) -> str:
        item = self.copies.currentItem()
        return str(item.data(Qt.ItemDataRole.UserRole)) if item else ""

    def _chosen(self, item, _previous=None) -> None:
        name = str(item.data(Qt.ItemDataRole.UserRole)) if item else ""
        if not name:
            self.go.setEnabled(False)
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            text = self.c.go_back_preview(name)
        finally:
            QApplication.restoreOverrideCursor()
        refused = text.startswith("error")
        self.changes.setPlainText(text.removeprefix("error:").strip() if refused
                                  else (text.strip("\n") or NOTHING_CHANGES))
        self.go.setEnabled(not refused)


def _mono() -> QFont:
    font = QFont("monospace")
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


#: The paragraph about the projects KyprX is built on, said before anything is chosen: removing
#: KyprX never removes them, and whether the package manager does is its own rule, not a guess of
#: this app's.
THEIRS = ("Klassy, Better Blur DX, Geometry Change and Smart Video Wallpaper Reborn are programs "
          "of their own, and KyprX does not remove them. When you remove the KyprX package, your "
          "package manager also removes the ones it installed only for KyprX, and asks first; the "
          "ones you installed yourself stay.")


class RemoveDialog(QDialog):
    """Removing KyprX from this computer: two questions, nothing chosen for either, and what the
    answers would do once both are given.

    **Asked, never assumed.** Whether KDE is put back as KDE has it, and whether the KyprX folder
    is kept, are the owner's to say, so neither has an answer ticked and *Remove KyprX* cannot be
    pressed until both have one. Cancel is the default button, as on every question here.
    """

    def __init__(self, parent, client: Client, folder: str):
        super().__init__(parent)
        self.c = client
        self.setWindowTitle("Remove KyprX from this computer?")
        layout = QVBoxLayout(self)
        layout.addWidget(note(
            "KyprX takes back what it keeps and what only it used: its switch and its part inside "
            "the compositor, with the tiling; its keys; the rules that place its overlays; and "
            "what it remembers about this computer. Then it gives you the command that removes "
            "its files."))

        self.revert = QButtonGroup(self)
        desk = QGroupBox("Your desktop")
        desk_column = QVBoxLayout(desk)
        back = QRadioButton("Put KDE back as KDE has it -- Breeze, each program on its own "
                            "defaults, and no tiling of KyprX's. A copy of the desk is kept "
                            "first.")
        stay = QRadioButton("Leave it as it is now. Windows keep the look KyprX gave them, and "
                            "the desktop behaves as KyprX set it -- focus follows the mouse, among "
                            "the rest; its panel style and colour presets go with its files.")
        for answer, button in ((True, back), (False, stay)):
            self.revert.addButton(button, int(answer))
            desk_column.addWidget(button)
        layout.addWidget(desk)

        self.keep = QButtonGroup(self)
        kept = QGroupBox(f"Your KyprX folder, {folder}")
        kept_column = QVBoxLayout(kept)
        keep = QRadioButton("Keep it: your setup and the copies of the desk. Install KyprX again, "
                            "here or on another computer, and it is applied.")
        drop = QRadioButton("Remove it, and the copies of the desk in it -- the one kept just now "
                            "as well. A folder that is a git repository is left for you to remove.")
        for answer, button in ((True, keep), (False, drop)):
            self.keep.addButton(button, int(answer))
            kept_column.addWidget(button)
        layout.addWidget(kept)

        layout.addWidget(note(THEIRS))

        self.listing = QPlainTextEdit("Answer both questions to see exactly what would change.")
        self.listing.setReadOnly(True)
        self.listing.setFont(_mono())
        self.listing.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.listing.setMinimumSize(640, 220)
        layout.addWidget(self.listing, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.go = buttons.addButton("Remove KyprX", QDialogButtonBox.ButtonRole.AcceptRole)
        self.go.setEnabled(False)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.revert.idToggled.connect(self._answered)
        self.keep.idToggled.connect(self._answered)

    def answers(self) -> tuple[bool, bool] | None:
        """(revert, keep_folder), or None while either question is unanswered."""
        if self.revert.checkedId() < 0 or self.keep.checkedId() < 0:
            return None
        return bool(self.revert.checkedId()), bool(self.keep.checkedId())

    def _answered(self, _id: int, on: bool) -> None:
        answers = self.answers()
        if not on or answers is None:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            changes = self.c.remove_preview(*answers)
        finally:
            QApplication.restoreOverrideCursor()
        self.listing.setPlainText(changes.strip("\n") or NOTHING_CHANGES)
        self.go.setEnabled(not changes.startswith("error"))


class RemovedDialog(QDialog):
    """What removing KyprX did, what it kept, and the command that removes its files -- to read,
    select and copy. KyprX does not run it: removing a package is the package manager's, with the
    administrator's password, and on some systems a restart."""

    def __init__(self, parent, answer: dict):
        super().__init__(parent)
        dry = bool(answer.get("dry_run"))
        self.setWindowTitle("Dry run: KyprX was not removed" if dry
                            else "KyprX is off this computer's settings")
        layout = QVBoxLayout(self)
        done = "".join(f"<li>{html.escape(line)}</li>" for line in answer.get("done") or [])
        kept = "".join(f"<li>{html.escape(line)}</li>" for line in answer.get("kept") or [])
        text = ("<b>Nothing was written.</b> In a real run, this is what would be done:"
                if dry else "<b>Done:</b>")
        said = note(f"{text}<ul>{done}</ul><b>Kept:</b><ul>{kept}</ul>"
                    f"To finish, remove KyprX's files{' (in a real run)' if dry else ''}:")
        said.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(said)
        self.command = QLabel(str(answer.get("command") or ""))
        self.command.setFont(_mono())
        self.command.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        copy = QPushButton("Copy the command")
        copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.command.text()))
        row = QHBoxLayout()
        row.addWidget(self.command, 1)
        row.addWidget(copy)
        layout.addLayout(row)
        if answer.get("then"):
            layout.addWidget(note(str(answer["then"])))
        if not dry:
            layout.addWidget(note("This window closes when you close this message. Opening KyprX "
                                  "again before its files are removed brings it back on, with its "
                                  "look, as on a new install. The keys KyprX took from other "
                                  "actions stay without one: System Settings, under Shortcuts, "
                                  "gives each its key back."))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


#: What *Update now* does, said before it is pressed.
UPDATE_NOW_TEXT = ("Update now installs it over this one and restarts KyprX's background service. "
                   "A KyprX window opened with its key closes then: open it again. KyprX's part "
                   "inside the compositor is the new version from the next login.")


def _plain(text: str) -> QLabel:
    """A wrapped line of plain text: a path or a branch name is never read as markup."""
    label = note(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    return label


class UpdateDialog(QDialog):
    """A newer KyprX, and how this installation takes it: *Update now* for a working tree, which
    `install.sh --update` updates in place; the command to copy for a package (KyprX never runs a
    package manager) or for a working tree in a dry run; and for a working tree that cannot be
    updated by itself, the reason alone. `update_now` says whether *Update now* closed it."""

    def __init__(self, parent, answer: dict, dry_run: bool = False):
        super().__init__(parent)
        self.update_now = False
        self.command: QLabel | None = None
        latest = str(answer.get("latest") or "")
        tree = answer.get("kind") in ("clone", "release")
        self.setWindowTitle(f"KyprX {latest} is out" if latest
                            else "New changes for this working tree")
        layout = QVBoxLayout(self)
        layout.addWidget(_plain(f"{answer.get('detail') or 'There is a new version'}. Updating "
                                f"keeps your setup: nothing has to be removed first."))
        if tree and answer.get("can_update") and not dry_run:
            layout.addWidget(_plain(UPDATE_NOW_TEXT))
            buttons = QDialogButtonBox()
            go = buttons.addButton("Update now", QDialogButtonBox.ButtonRole.AcceptRole)
            buttons.addButton("Not now", QDialogButtonBox.ButtonRole.RejectRole)
            go.clicked.connect(self._go)
        elif tree and not dry_run:
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        else:
            lead = ("This window is on a dry run, so it updates nothing. In a terminal, this "
                    "updates it:" if tree else
                    "Your system's package manager updates KyprX. KyprX does not run it for you:")
            layout.addWidget(_plain(lead))
            command = str(answer.get("command") or "")
            self.command = QLabel(command)
            self.command.setTextFormat(Qt.TextFormat.PlainText)
            self.command.setFont(_mono())
            if len(command) > 80:
                # Arch's is one line of 170 characters (`ARCH_LINE` in daemon/update.py):
                # unwrapped, it opened this window 1374 pixels wide, and wrapped to the width the
                # rest of the window takes, it ran to six lines. Wrapped at a terminal's 80
                # columns it takes three, and it is still copied as the one line it is.
                self.command.setWordWrap(True)
                self.command.setMinimumWidth(self.command.fontMetrics().horizontalAdvance("x" * 80))
            self.command.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            copy = QPushButton("Copy the command")
            copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.command.text()))
            row = QHBoxLayout()
            row.addWidget(self.command, 1)
            row.addWidget(copy)
            layout.addLayout(row)
            if answer.get("then"):
                layout.addWidget(_plain(str(answer["then"])))
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _go(self) -> None:
        self.update_now = True
        self.accept()


class AboutDialog(QDialog):
    """*About KyprX…* on the Settings tab: this KyprX's version, the projects it is built on as
    they stand here, and the projects it works with, from `CREDITS.md`.

    Put together by the tab (`gui/tab_settings.py`, `needs_text` and `credits_text`), so nothing is
    read here. Behind a button rather than on the page: it is read once and rarely again, and a
    page somebody opens to change something should show what can be changed.
    """

    def __init__(self, parent, version: str, needs: str, credits: str):
        super().__init__(parent)
        self.setWindowTitle("About KyprX")
        layout = QVBoxLayout(self)
        title = QLabel(f"<b>{html.escape(version)}</b>")
        layout.addWidget(title)
        for heading, text in (("What KyprX is built on", needs), ("Credits", credits)):
            box = QGroupBox(heading)
            column = QVBoxLayout(box)
            label = note(text)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setOpenExternalLinks(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            column.addWidget(label)
            layout.addWidget(box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
