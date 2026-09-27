"""The Settings tab: what KyprX keeps about itself, and the big changes it can make.

Notifications, the door to the decoration's own settings, the KyprX folder and how it stands with
the desk, what is wrong on this machine and its repairs, and the changes that write a great deal:
applying a backup file, and *Restore defaults*, *Take KyprX off this desk* and *Go back to a
copy...*, each of those three asked first in `gui/dialogs.py` with what it would change listed. Also
the projects KyprX works with, the short form of `CREDITS.md`: `CREDITS` is compared with that file
by `scripts/dry-run.sh`, and the file is found at the top of the working tree, the folder above
`gui/`.
"""

from __future__ import annotations

import html
import json
import os

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont, QGuiApplication
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from client import Client
from decoration import TITLEBAR_BUTTON_TIP, open_decoration_settings
from dialogs import ChangesDialog, CopiesDialog, RemoveDialog, RemovedDialog
from widgets import SECTION_HINTS, WARNING_STYLE, Section, note


# ---------------------------------------------------------------------- settings tab

#: Three short lines where there were four paragraphs. Two things it used to say were not true:
#: *the three switches above the tabs* -- there are two switches and a menu up there, and the third
#: setting it means is the notification tick on this very page -- and the preset by name, which
#: `daemon/defaults.py` deliberately leaves unnamed so that the mode's own default is resolved in
#: one place. What it writes in full is in `docs/user-guide/settings.md`.
#:
#: The breaks are `<br>` and not `\n`: this string carries tags, so Qt renders it as rich text,
#: and in rich text a newline is a space. Both of the long texts on this page had that wrong.
RESTORE_QUESTION = (
    "<b>Writes:</b> the appearance, the title bar, the effects and the tiling settings, what a "
    "new window gets, how see-through the windows are, the three settings KyprX keeps about "
    "itself, the wallpaper picker's folder and layout, and the desktop's colours.<br><br>"
    "<b>Leaves alone:</b> the windows you have set by hand, your shortcuts, your wallpaper and "
    "your profiles.<br><br>"
    "A copy of the desk is kept first, and <i>Go back to a copy…</i> on this page puts it back. "
    "Below is exactly what would change.")

#: The question before taking KyprX off the desk. What it does is the owner's "pure KDE": said in
#: three lines, with what it keeps, and the way back named before anything is written.
TAKE_OFF_QUESTION = (
    "<b>Puts KDE back as KDE has it:</b> the decoration, the blur, the tiling and focus on their own "
    "defaults; KyprX's keys taken out of every window rule and decoration override; tiling, "
    "Better Blur and the window animation switched off; and KDE's own Breeze global theme.<br><br>"
    "<b>Then KyprX stops:</b> new windows are left alone, and your KyprX folder is kept exactly "
    "as it is.<br><br>"
    "A copy of the desk is kept first and never thrown away, and <i>Put my setup back</i> restores "
    "it. Below is exactly what would change.")

#: The short form of CREDITS.md, for the Settings tab: each project, what it is here, who made it,
#: its licence and where it lives. CREDITS.md is the whole record -- authors in full, what each
#: licence asks of KyprX, the notices -- and `scripts/dry-run.sh` checks every name and link here
#: is there too, so the two cannot drift apart without a check failing.
CREDITS = (
    ("Klassy", "the window decoration", "Paul A McAuley, after KDE's Breeze",
     "GPL; its colour schemes LGPL", "https://github.com/paulmcauley/klassy"),
    ("Better Blur DX", "the blur", "xarblu, after taj-ny's Better Blur", "GPL-3.0",
     "https://github.com/xarblu/kwin-effects-better-blur-dx"),
    ("Krohnkite", "the tiling", "Vjatcheslav V. Kolchkov, after Eon S. Jeon's Kröhnkite", "MIT",
     "https://github.com/anametologin/krohnkite"),
    ("Geometry Change", "the window animation", "Peter Fajdiga", "GPL-3.0",
     "https://github.com/peterfajdiga/kwin4_effect_geometry_change"),
    ("Smart Video Wallpaper Reborn", "video wallpapers", "Luis Bocanegra, with Rog131 and adhe",
     "GPL-2.0-or-later",
     "https://github.com/luisbocanegra/plasma-smart-video-wallpaper-reborn"),
    ("Catppuccin", "a colour palette", "Catppuccin", "MIT",
     "https://github.com/catppuccin/catppuccin"),
    ("Nord", "a colour palette", "Sven Greb", "MIT", "https://github.com/nordtheme/nord"),
    ("Gruvbox", "a colour palette", "Pavel Pertsev (morhetz)", "MIT/X11",
     "https://github.com/morhetz/gruvbox"),
    ("Dracula", "a colour palette", "Dracula Theme", "MIT",
     "https://github.com/dracula/dracula-theme"),
    ("Solarized", "a colour palette", "Ethan Schoonover", "MIT",
     "https://github.com/altercation/solarized"),
    ("Rosé Pine", "a colour palette", "Rosé Pine", "MIT",
     "https://github.com/rose-pine/rose-pine-theme"),
)

#: Where the whole record is: at the top of the working tree, the folder above `gui/`, found from
#: this file's real path. This file is loaded from the working tree beside `gui/kyprx.py`, which is
#: what the installed `kyprx` is a link to.
CREDITS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                            "CREDITS.md")

#: This installation's version, in the same folder and for the same reason as CREDITS.md:
#: `daemon/about.py` reads the same file, and says why it is a file.
VERSION_FILE = os.path.join(os.path.dirname(CREDITS_FILE), "VERSION")


def app_version() -> str:
    """The version on disk beside the interface's code, or "" when its file is not there."""
    try:
        with open(VERSION_FILE, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


#: The version this window runs, read once when it starts: after an update the file is the new one
#: and this process is still the old one. See `daemon/about.py`, which does the same.
RUNNING = app_version()


def credits_text() -> str:
    """The Credits box, as rich text: one line per project, its name a link to where it lives."""
    rows = "".join(
        f"<tr><td><a href='{html.escape(url)}'>{html.escape(name)}</a></td>"
        f"<td style='padding-left:12px'>{html.escape(what)}</td>"
        f"<td style='padding-left:12px'>{html.escape(who)}</td>"
        f"<td style='padding-left:12px'>{html.escape(licence)}</td></tr>"
        for name, what, who, licence, url in CREDITS)
    record = QUrl.fromLocalFile(CREDITS_FILE).toString()
    return (f"<table>{rows}</table><p>KyprX is free software, under the GNU General Public "
            f"License, version 3 or later. Every project, its licence and what that licence asks "
            f"of KyprX: <a href='{html.escape(record)}'>CREDITS.md</a>.</p>")


#: One sentence each, behind the mark on each section. The rest -- what a backup file carries,
#: what applying one replaces, what a notification is -- is in `docs/user-guide/settings.md`.
NOTIFY_HINT = ("Failures only: a title bar refused, a wallpaper or a colour that would not "
               "apply. Nothing is said when things go well.")

FOLDER_HINT = ("Everything KyprX controls on this desk, as files you can copy to another "
               "machine, keep in git or edit. KyprX keeps them up to date by itself, and applies "
               "what arrives there by itself -- after keeping a copy of the desk.")


class SettingsTab(QWidget):
    """What this app keeps about itself: how it speaks up, where the decoration's own settings
    are, the KyprX folder that carries the setup elsewhere, what is wrong on this machine, and its
    defaults.

    The first two arrived from the strip across the top of the window, which is now the three
    things somebody comes here to *do*. These are two things set once, and a thing set once
    belongs on a page rather than in front of every tab.
    """

    #: What the window's footer should say. Export, import and the repair used to answer with a
    #: dialog or with nothing at all.
    says = Signal(str)
    #: *Check again* found out afresh what KyprX needs, so the band above every tab is redrawn.
    looked_again = Signal()

    def __init__(self, client: Client, parent=None):
        super().__init__(parent)
        self.c = client

        load = QPushButton("Apply a backup file from an earlier version…")
        tidy = QPushButton("Tidy up rule names")
        load.clicked.connect(self._import)
        tidy.clicked.connect(self._normalize)
        #: The second repair, and one that changes how the desk looks: it gives a title bar back to
        #: every window the decoration's leftover group was hiding one on. Shown only while there
        #: is one, beside the line that says what it is.
        self.bars_back = QPushButton("Give those windows their title bars back")
        self.bars_back.setToolTip("Removes the decoration's leftover [Exceptions] group. A copy of "
                                  "the desk is kept first.")
        self.bars_back.clicked.connect(self._remove_stray)
        self.bars_back.setVisible(False)
        load.setToolTip("A settings file exported by KyprX before the folder existed. A copy of the "
                        "desk is kept first.")
        tidy.setToolTip("Give every rule whose only job is forcing a title bar this app's "
                        "naming. Rules that also pin an activity or a desktop keep their names.")
        #: An ellipsis, because it asks before it does anything -- the same convention the two
        #: buttons above follow.
        self.restore = QPushButton("Restore KyprX's defaults…")
        self.restore.clicked.connect(self._restore)
        self.restore.setToolTip("KyprX's defaults cannot be edited — only put back. A copy of "
                                "the desk is kept first.")
        #: The other big action, beside the first: *Restore* puts KyprX's opinion on the desk,
        #: this takes KyprX off it -- two different things, and the owner asked for both.
        self.take_off_button = QPushButton("Take KyprX off this desk…")
        self.take_off_button.clicked.connect(self._take_off)
        self.take_off_button.setToolTip("Put KDE back on its own defaults and Breeze theme, and "
                                        "stop KyprX -- a copy of the desk is kept first.")
        #: The last of the big changes, and the one that ends with KyprX gone from this computer's
        #: settings: asked in `RemoveDialog`, whose two questions have no answer chosen.
        self.remove_button = QPushButton("Remove KyprX from this computer…")
        self.remove_button.clicked.connect(self._remove)
        self.remove_button.setToolTip("Take back what KyprX keeps and what only it used, then show "
                                      "the command that removes its files. Asks two questions "
                                      "first.")
        #: Beside the button whose work it undoes, and before it: the way back is what somebody
        #: looks for after pressing the other one.
        self.back = QPushButton("Go back to a copy…")
        self.back.clicked.connect(self._go_back)
        self.back.setToolTip("Put the desk back as it was before an earlier change that wrote a "
                             "great deal at once.")
        #: The version of those defaults, which `daemon/defaults.py` says is shown here and which
        #: nothing showed. It is read once, when this page is first painted.
        self.version = QLabel()
        self.version.setEnabled(False)

        #: Named for what it does rather than for the mechanism. "Notify" said neither what nor
        #: when, and all three things the daemon ever announces are failures -- a window that
        #: refuses a title bar, a wallpaper that did not change, a colour that did not apply.
        self.notify = QCheckBox("Say when something did not work")
        self.notify.setToolTip("A notification on the desktop, and only when something failed.")
        self.notify.toggled.connect(lambda v: self.c.set_settings(notify=v))
        speaking = Section("Notifications", NOTIFY_HINT)
        speaking_column = QVBoxLayout(speaking)
        speaking_column.addWidget(self.notify)

        #: The same door as the one on the Appearance tab, and now the same words on it. Two names
        #: for one destination is a thing to learn for nothing.
        decoration_button = QPushButton("Title bar settings…")
        decoration_button.setToolTip(TITLEBAR_BUTTON_TIP)
        decoration_button.clicked.connect(open_decoration_settings)
        #: Kept so the window can close this door during a dry run -- see `DRY_RUN_DOOR_TIP`.
        self.door = decoration_button
        decoration_row = QHBoxLayout()
        decoration_row.setContentsMargins(0, 0, 0, 0)
        decoration_row.addWidget(decoration_button)
        decoration_row.addStretch()
        decoration_holder = QWidget()
        decoration_holder.setLayout(decoration_row)
        decoration = Section("The window decoration",
                             SECTION_HINTS["The window decoration"])
        decoration_column = QVBoxLayout(decoration)
        decoration_column.addWidget(decoration_holder)

        #: The KyprX folder, where the backup file used to be: the path, to read and to copy, a
        #: door to the file manager, and how the folder stands with the desk. What travels is no
        #: longer a file somebody remembers to export -- it is always there, always current.
        self.folder_path = QLabel()
        self.folder_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        mono = QFont("monospace")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.folder_path.setFont(mono)
        copy_path = QPushButton("Copy")
        copy_path.setToolTip("Put the folder's path on the clipboard.")
        copy_path.clicked.connect(self._copy_folder_path)
        open_folder = QPushButton("Open the folder")
        open_folder.setToolTip("Bring the folder up to date with the desk, then open it in the "
                               "file manager.")
        open_folder.clicked.connect(self._open_folder)
        where = QHBoxLayout()
        where.setContentsMargins(0, 0, 0, 0)
        where.addWidget(self.folder_path, 1)
        where.addWidget(copy_path)
        where.addWidget(open_folder)
        #: How the folder stands, in a sentence -- rebuilt on every change the daemon reports.
        self.folder_line = note()
        self.folder_line.setTextFormat(Qt.TextFormat.PlainText)
        carry = QHBoxLayout()
        carry.setContentsMargins(0, 0, 0, 0)
        carry.addWidget(self.back)
        carry.addWidget(load)
        carry.addStretch()
        file_box = Section("Your KyprX folder", FOLDER_HINT)
        self.file_box = file_box
        file_column = QVBoxLayout(file_box)
        file_column.addLayout(where)
        file_column.addWidget(self.folder_line)
        file_column.addLayout(carry)

        #: The five projects KyprX is built on, one line each: installed or not, the version, and
        #: whether the desktop runs it -- and for each one that is not right, what is wrong and the
        #: command that puts it right on this system, selectable so it can be copied. The daemon
        #: keeps the answer; *Check again* is for after installing or updating one.
        self.needs_box = Section("What KyprX needs", SECTION_HINTS["What KyprX needs"])
        needs_column = QVBoxLayout(self.needs_box)
        self.needs_label = note()
        self.needs_label.setTextFormat(Qt.TextFormat.RichText)
        self.needs_label.setOpenExternalLinks(True)
        self.needs_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        check_again = QPushButton("Check again")
        check_again.setToolTip("Look again for the five projects, after installing or updating "
                               "one.")
        check_again.clicked.connect(self._check_again)
        needs_row = QHBoxLayout()
        needs_row.setContentsMargins(0, 0, 0, 0)
        needs_row.addWidget(self.needs_label, 1)
        needs_row.addWidget(check_again, 0, Qt.AlignmentFlag.AlignTop)
        needs_column.addLayout(needs_row)

        #: What is wrong on this machine, one line each, in a box of its own rather than as a
        #: paragraph of run-on text under everything else. Built empty and filled by `reload`:
        #: reading the daemon while this page is being constructed would make opening the window a
        #: read before it is on screen.
        self.problems = Section("Problems", SECTION_HINTS["Problems"])
        self.problems_column = QVBoxLayout(self.problems)
        self.problem_lines: list[QLabel] = []
        #: The two repairs this app offers -- *Tidy up rule names*, and the button that gives
        #: title bars back, shown only while it has something to do -- in the box with the faults
        #: they repair rather than at the bottom of the page next to the button that rewrites
        #: everything.
        self.tidy = tidy
        tidy_row = QHBoxLayout()
        tidy_row.setContentsMargins(0, 0, 0, 0)
        tidy_row.addWidget(tidy)
        tidy_row.addWidget(self.bars_back)
        tidy_row.addStretch()
        self.problems_column.addLayout(tidy_row)

        #: Last on the page and the only thing on it that is not about this desk: who made what
        #: KyprX works with, under which licence. The links open in the browser; CREDITS.md opens
        #: in whatever opens a text file.
        self.credits = Section("Credits", SECTION_HINTS["Credits"])
        credits_column = QVBoxLayout(self.credits)
        credits_label = note(credits_text())
        credits_label.setTextFormat(Qt.TextFormat.RichText)
        credits_label.setOpenExternalLinks(True)
        credits_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        credits_column.addWidget(credits_label)

        #: Alone on its row and pushed to the far side: it writes every value this app has an
        #: opinion about, and putting it next to the buttons that only read a file would be an
        #: invitation.
        repairs = QHBoxLayout()
        repairs.addWidget(self.version)
        repairs.addStretch()
        repairs.addWidget(self.take_off_button)
        repairs.addWidget(self.restore)
        repairs.addWidget(self.remove_button)

        #: Side by side, and each taking the height of what is in it and no more. Both of those
        #: were measured on screen rather than chosen: stacked, with a group box's own `Preferred`
        #: policy in both directions and a word-wrapped label inside, the two of them took 270 of
        #: the window's 720 pixels, height the rest of the page needs.
        settled = QHBoxLayout()
        for box in (speaking, decoration):
            box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
            settled.addWidget(box, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(settled)
        file_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        layout.addWidget(file_box)
        self.needs_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        layout.addWidget(self.needs_box)
        layout.addWidget(self.problems)
        layout.addWidget(self.credits)
        layout.addStretch()
        layout.addLayout(repairs)

    def _restore(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            changes = self.c.restore_preview()
        finally:
            QApplication.restoreOverrideCursor()
        box = ChangesDialog(self, "Restore KyprX's defaults?", RESTORE_QUESTION, changes,
                            "Restore the defaults")
        if box.exec() != QDialog.DialogCode.Accepted:
            return
        self.says.emit("Keeping a copy of the desk, then putting KyprX's defaults back… the "
                       "desktop's own tools take a second or two")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            answer = self.c.restore_defaults()
        finally:
            QApplication.restoreOverrideCursor()
        if not answer:
            self.says.emit("KyprX's defaults are back. Go back to a copy… undoes it.")
        elif answer.startswith("partial"):
            self.says.emit("Only part of it went in: " + answer.removeprefix("partial:").strip()
                           + " Go back to a copy… undoes the rest.")
        else:
            self.says.emit("That did not go through: " + answer.removeprefix("error:").strip())
        self.reload()

    def _take_off(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            changes = self.c.take_off_preview()
        finally:
            QApplication.restoreOverrideCursor()
        box = ChangesDialog(self, "Take KyprX off this desk?", TAKE_OFF_QUESTION, changes,
                            "Take KyprX off")
        if box.exec() != QDialog.DialogCode.Accepted:
            return
        self.says.emit("Keeping a copy of the desk, then taking KyprX off… the desktop's own "
                       "tools take a few seconds")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            answer = self.c.take_off()
        finally:
            QApplication.restoreOverrideCursor()
        if not answer:
            self.says.emit("KyprX is off this desk. Put my setup back, at the top of the window, "
                           "undoes it.")
        else:
            self.says.emit("That did not go through: " + answer.removeprefix("error:").strip())
        self.reload()

    def _go_back(self) -> None:
        listing = (self.c.snapshots() or {}).get("snapshots") or []
        if not listing:
            self.says.emit("There is no copy of the desk yet: one is kept before each change that "
                           "writes a great deal at once.")
            return
        box = CopiesDialog(self, self.c, listing)
        if box.exec() != QDialog.DialogCode.Accepted or not box.chosen():
            return
        self.says.emit("Keeping a copy of the desk as it is, then going back… the desktop's own "
                       "tools take a second or two")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            answer = self.c.go_back(box.chosen())
        finally:
            QApplication.restoreOverrideCursor()
        if not answer:
            self.says.emit("The desk is back as it was. The copy of how it was a moment ago is "
                           "first in the list, if you want that back.")
        elif answer.startswith("partial"):
            self.says.emit("Most of it came back, but: " + answer.removeprefix("partial:").strip())
        else:
            self.says.emit("That did not go through: " + answer.removeprefix("error:").strip())
        self.reload()

    def _remove(self) -> None:
        folder = str((self.c.folder() or {}).get("path") or "~/.config/kyprx")
        box = RemoveDialog(self, self.c, folder.replace(os.path.expanduser("~"), "~", 1))
        if box.exec() != QDialog.DialogCode.Accepted or box.answers() is None:
            return
        self.says.emit("Taking KyprX off this computer… the desktop's own tools take a few "
                       "seconds")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            answer = self.c.remove(*box.answers())
        finally:
            QApplication.restoreOverrideCursor()
        if answer.get("answer") != "ok":
            self.says.emit("That did not go through: "
                           + str(answer.get("answer") or "no answer").removeprefix("error:").strip())
            self.reload()
            return
        RemovedDialog(self, answer).exec()
        if self.c.gone:
            # Nothing may be sent any more (see `Client.gone`), and this window has nothing left
            # to show: close it.
            QApplication.quit()
            return
        self.reload()

    def reload(self) -> None:
        # This tab is a live one: `reload` runs on every change the daemon reports while it is
        # open. `setChecked` emits `toggled`, so without the guard each change would write the
        # setting again and bring on the next change -- a loop the old home of this checkbox, the
        # row above the tabs, was never exposed to.
        self.notify.blockSignals(True)
        self.notify.setChecked(bool((self.c.settings() or {}).get("notify", False)))
        self.notify.blockSignals(False)
        self._say_folder(self.c.folder())
        if not self.version.text():
            # Read once: it changes when this app is updated, not while it is open. The daemon has
            # sent it since the defaults were declared, and nothing has ever shown it.
            version = (self.c.groups() or {}).get("kyprx_defaults_version")
            if version is not None:
                self.version.setText(f"KyprX {RUNNING or '(version unknown)'} · its "
                                     f"defaults, version {version}")
        self._say_needs(self.c.requirements())
        d = self.c.diagnostics()
        if not d:
            return
        #: The compositor script first when it is missing or off, and not in the middle of a list:
        #: it does not mean one thing is wrong, it means nothing on the Windows tab is real.
        found: list[tuple[str, str]] = []
        if not d.get("script_installed"):
            found.append(("KyprX cannot see your windows: its part of the compositor is not "
                          "installed.",
                          "Installing the KyprX package again puts it back." if d.get("from_package")
                          else "install.sh is what puts it there."))
        elif not d.get("script_enabled"):
            found.append(("KyprX cannot see your windows: its part of the compositor is switched "
                          "off.", "The desktop's own settings are where scripts are switched on."))
        if d.get("missing_actions"):
            found.append(("One key is not registered yet, so it does nothing.",
                          "Not registered: " + ", ".join(d["missing_actions"])))
        if d.get("orphan_overrides"):
            found.append(("Some per-window settings were written where the decoration cannot see "
                          "them.", f"Past a gap in the numbering: {d['orphan_overrides']}"))
        if d.get("orphan_rules"):
            found.append((f"{len(d['orphan_rules'])} window rule(s) are outside the active list.",
                          "They do nothing until the desktop's own rules dialog is opened."))
        if d.get("renamable"):
            found.append((f"{len(d['renamable'])} window rule(s) could take KyprX's naming.",
                          "Tidy up rule names does it."))
        stray = d.get("stray_exceptions")
        if stray is not None:
            found.append(("Every window without a setting of its own is drawn with its title bar "
                          "hidden, by a group the decoration's own settings left behind.",
                          f"klassyrc [Exceptions], HideTitleBar={stray.get('hide_titlebar') or '?'}: "
                          f"the decoration reads it as its global setting. KyprX removes it by "
                          f"itself while it is on the desk; the button beside Tidy up rule names "
                          f"removes it now."))
        self.bars_back.setVisible(stray is not None)
        self._say_problems(found, d)

    def _say_needs(self, needs: list) -> None:
        """The five projects, as a table: a line each, and under one that is not right, what is
        wrong and what to do."""
        words = {"ok": "installed and running", "missing": "not installed",
                 "not running": "installed, not running", "too old": "too old"}
        rows = []
        for n in needs:
            name = html.escape(str(n.get("name") or ""))
            url = html.escape(str(n.get("url") or ""))
            state = str(n.get("state") or "")
            rows.append(f"<tr><td><a href='{url}'>{name}</a></td>"
                        f"<td style='padding-left:12px'>{html.escape(str(n.get('version') or ''))}</td>"
                        f"<td style='padding-left:12px'>{html.escape(words.get(state, state))}</td>"
                        f"</tr>")
            if state != "ok":
                rows.append(f"<tr><td colspan='3' style='{WARNING_STYLE}'>"
                            f"{html.escape(str(n.get('detail') or ''))}<br>"
                            f"{html.escape(str(n.get('fix') or ''))}</td></tr>")
        self.needs_label.setText(f"<table>{''.join(rows)}</table>" if rows
                                 else "KyprX could not find out what is installed here.")

    def _check_again(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            needs = self.c.requirements(refresh=True)
        finally:
            QApplication.restoreOverrideCursor()
        self._say_needs(needs)
        wrong = [str(n.get("name")) for n in needs if n.get("state") != "ok"]
        self.says.emit("Looked again: " + (", ".join(wrong) + " still not right." if wrong
                                            else "all five are installed and running."))
        self.looked_again.emit()

    def _say_folder(self, status: dict) -> None:
        """The folder's path, and how it stands with the desk, in a sentence or two."""
        path = str(status.get("path") or "")
        self.folder_path.setText(path.replace(os.path.expanduser("~"), "~", 1) if path else "")
        self.folder_path.setToolTip(path)
        state = status.get("state")
        if status.get("dry_run"):
            text = ("Dry run: the folder is not written, and a change arriving in it is only "
                    "reported.")
        elif state == "waiting":
            text = f"Waiting before applying what arrived: {status.get('detail', '')}."
        elif state == "problem":
            problems = status.get("problems") or []
            text = ("What is in the folder cannot be applied, so nothing was applied and nothing "
                    "in it is written over: " + "; ".join(problems))
        elif state == "applied":
            text = (f"Applied what arrived in the folder at {status.get('when', '')} "
                    f"({', '.join(status.get('files') or [])}). A copy of the desk from before "
                    f"was kept — Go back to a copy… undoes it.")
            if status.get("conflicts"):
                text += (" Where the folder and the desk had both changed something, the folder "
                         "won: " + ", ".join(status["conflicts"]) + ".")
            if status.get("trouble"):
                text += " Not applied: " + "; ".join(status["trouble"]) + "."
        else:
            text = "In step with the desk."
        self.folder_line.setText(text)
        self.folder_line.setStyleSheet(WARNING_STYLE if state == "problem" else "")

    def _copy_folder_path(self) -> None:
        QGuiApplication.clipboard().setText(self.folder_path.toolTip())
        self.says.emit("The folder's path is on the clipboard.")

    def _open_folder(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            status = self.c.sync_folder()
        finally:
            QApplication.restoreOverrideCursor()
        self._say_folder(status)
        path = str(status.get("path") or "")
        if path and os.path.isdir(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            self.says.emit("The folder is not there yet: KyprX writes it a moment after it starts.")

    def _say_problems(self, found: list, d: dict) -> None:
        """One line per thing that is wrong, with the machine's own words behind each one.

        Rebuilt rather than appended to: this runs on every change the daemon reports while the
        page is open, and a box that grows a line each time would be a page that never settles.
        """
        for line in self.problem_lines:
            self.problems_column.removeWidget(line)
            line.setParent(None)
            line.deleteLater()
        self.problem_lines = []
        for text, detail in found or [("Nothing to report.", "")]:
            line = note(text)
            if detail:
                line.setToolTip(detail)
            self.problem_lines.append(line)
            self.problems_column.insertWidget(len(self.problem_lines) - 1, line)
        # The counts are not a problem, so they are not a line. They are what the box is about.
        self.problems.set_hint(
            f"{SECTION_HINTS['Problems']} It knows about {d.get('overrides', 0)} per-window "
            f"setting(s) and {d.get('rules', 0)} window rule(s).")
        self.tidy.setEnabled(bool(d.get("renamable")))
        if not d.get("renamable"):
            self.tidy.setToolTip("Every rule already carries KyprX's naming.")
        else:
            self.tidy.setToolTip("Give every rule whose only job is forcing a title bar this "
                                 "app's naming. Rules that also pin an activity or a desktop "
                                 "keep their names.")

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Apply a backup file",
                                              os.path.expanduser("~"), "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
            if not isinstance(json.loads(content), dict):
                raise ValueError("not an object")
        except OSError as e:
            QMessageBox.warning(self, "That file could not be read",
                                f"{html.escape(path)}: {html.escape(e.strerror or str(e))}.")
            return
        except (UnicodeDecodeError, ValueError):
            # The exception's own words name a line and a column of a file nobody wrote by hand.
            QMessageBox.warning(self, "That is not a settings file",
                                "It could not be read. A settings file is one an earlier KyprX "
                                "wrote, with its <i>Export to a file…</i> button.")
            return
        box = QMessageBox(QMessageBox.Icon.Question, "Apply this backup file?",
                          "This writes over the settings on this machine, and replaces your "
                          "profiles with the ones in the file. Your wallpaper is left alone. A "
                          "copy of the desk is kept first.",
                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        if box.exec() != QMessageBox.StandardButton.Yes:
            return
        self.says.emit("Keeping a copy of the desk, then applying the file…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            done = self.c.import_settings(content)
        finally:
            QApplication.restoreOverrideCursor()
        # On a refusal the client has already put the daemon's reason on the line; a sentence here
        # would cover it.
        if done:
            self.says.emit("Applied. Go back to a copy… undoes it.")

    def _remove_stray(self) -> None:
        box = QMessageBox(QMessageBox.Icon.Question, "Give those windows their title bars back?",
                          "Removes the group the decoration's own settings left behind, which it "
                          "reads as a global setting that hides the title bar of every window "
                          "with no setting of its own. Those windows get their title bars back. A "
                          "copy of the desk is kept first.",
                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        if box.exec() != QMessageBox.StandardButton.Yes:
            return
        done = self.c.remove_stray_exceptions()
        if done:  # a refusal's reason is already on the line
            self.says.emit("Done. Go back to a copy… undoes it.")
        self.reload()

    def _normalize(self) -> None:
        """Rename what can be renamed, and say how much in the window's own line.

        It used to answer with a dialog listing every old and new name in the app's own spelling,
        which is a wall of machine text for an act nobody needs the detail of.
        """
        renamed = self.c.normalize()
        self.says.emit(f"{len(renamed)} rule(s) renamed." if renamed else "Nothing to rename.")
        self.reload()
