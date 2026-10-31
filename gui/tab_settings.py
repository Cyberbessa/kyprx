"""The Settings tab: what KyprX keeps about itself, and the big changes it can make.

Notifications, the KyprX folder and how it stands with the desk, and -- only while there is
something to say -- what KyprX needs and what is wrong on this machine, with its repairs. Along the
bottom, KyprX's version with *About KyprX…* and *Look for a new version*, and the changes that write
a great deal: *Go back to a copy…*, *Restore KyprX's defaults…*, *Take KyprX off this desk…* and
*Remove KyprX from this computer…*, each asked first in `gui/dialogs.py` with what it would change
listed. *About KyprX…* (`AboutDialog`) holds the projects KyprX is built on as they stand here, and
the projects it works with, the short form of `CREDITS.md`: `CREDITS` is compared with that file by
`scripts/dry-run.sh`, and the file is found at the top of the working tree, the folder above
`gui/`. *Look for a new version* is the one door to a new version: `daemon/update.py check` in a
process of its own, asked only when pressed, its answer put in `UpdateDialog`, and *Update now* run
in a unit of its own (`update_argv` says why).
"""

from __future__ import annotations

import html
import json
import os
import shlex
import subprocess
import sys
import time

from PySide6.QtCore import QProcess, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont, QGuiApplication
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from client import Client
from dialogs import (AboutDialog, ChangesDialog, CopiesDialog, RemoveDialog, RemovedDialog,
                     UpdateDialog)
from widgets import SECTION_HINTS, WARNING_STYLE, Section, note


# ---------------------------------------------------------------------- settings tab

#: Three short lines where there were four paragraphs. Two things it used to say were not true:
#: *the three switches above the tabs* -- there are two switches and a menu up there, and the third
#: setting it means is the notification tick on this very page -- and the preset by name, which
#: is `daemon/defaults.py`'s to say (`COLOURS`), so that it is named in one place and cannot
#: drift here. What it writes in full is in `docs/user-guide/settings.md`.
#:
#: The breaks are `<br>` and not `\n`: this string carries tags, so Qt renders it as rich text,
#: and in rich text a newline is a space. Both of the long texts on this page had that wrong.
RESTORE_QUESTION = (
    "<b>Writes:</b> the appearance, the title bar, the effects and the tiling settings, what a "
    "new window gets, how see-through the windows are, the three settings KyprX keeps about "
    "itself, the wallpaper picker's folder and layout, and the desktop's colours.<br><br>"
    "<b>Leaves alone:</b> the windows you have set by hand, your shortcuts, your wallpaper, "
    "your profiles, and your zone layouts and arrangements.<br><br>"
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

#: The short form of CREDITS.md, for *About KyprX…*: each project, what it is here, who made it,
#: its licence and where it lives. CREDITS.md is the whole record -- authors in full, what each
#: licence asks of KyprX, the notices -- and `scripts/dry-run.sh` checks every name and link here
#: is there too, so the two cannot drift apart without a check failing.
CREDITS = (
    ("Klassy", "the window decoration", "Paul A McAuley, after KDE's Breeze",
     "GPL; its colour schemes LGPL", "https://github.com/paulmcauley/klassy"),
    ("Better Blur DX", "the blur", "xarblu, after taj-ny's Better Blur", "GPL-3.0",
     "https://github.com/xarblu/kwin-effects-better-blur-dx"),
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

#: The tree this window runs from, which *Update now* updates, in a unit of its own.
TOP = os.path.dirname(CREDITS_FILE)
UPDATE_UNIT = "kyprx-update"


def check_argv() -> list[str]:
    """A process of its own: the window never waits on a network."""
    return [sys.executable, os.path.join(TOP, "daemon", "update.py"), "check", "--json"]


def update_argv() -> list[str]:
    """A unit of its own: the update restarts the background service, whose unit holds a window
    opened with the settings key -- and anything that window started. `--wait` gives the status."""
    return ["systemd-run", "--user", "--wait", "--quiet", "--collect", f"--unit={UPDATE_UNIT}",
            "--description=Updating KyprX", "--setenv=GIT_TERMINAL_PROMPT=0",
            "bash", os.path.join(TOP, "install.sh"), "--update"]


def update_failure(since: float, said: str = "") -> str:
    """What a failed update said, and the command that shows every step: `systemd-run`'s own
    words first -- all there is when the unit never started, another update still running in it,
    say -- then the last of the unit's journal."""
    try:
        journal = subprocess.run(["journalctl", "--user", f"--unit={UPDATE_UNIT}",
                                  f"--since=@{int(since)}", "--output=cat", "--no-pager"],
                                 capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        journal = ""
    lines = [line for line in said.splitlines() if line.strip()]
    lines += [line for line in journal.splitlines() if line.strip()][-12:]
    command = f"{shlex.quote(os.path.join(TOP, 'install.sh'))} --update"
    return ("\n".join(lines) + "\n\n" if lines else "") + \
        f"To see every step, run it in a terminal:\n{command}"


def credits_text() -> str:
    """The credits, as rich text: one line per project, its name a link to where it lives."""
    rows = "".join(
        f"<tr><td><a href='{html.escape(url)}'>{html.escape(name)}</a></td>"
        f"<td style='padding-left:12px'>{html.escape(what)}</td>"
        f"<td style='padding-left:12px'>{html.escape(who)}</td>"
        f"<td style='padding-left:12px'>{html.escape(licence)}</td></tr>"
        for name, what, who, licence, url in CREDITS)
    record = QUrl.fromLocalFile(CREDITS_FILE).toString()
    return (f"<table>{rows}</table><p>The tiling is KyprX's own, with ideas from KZones and "
            f"Hyprland and none of their code. KyprX is free software, under the GNU General "
            f"Public License, version 3 or later. Every project, its licence and what that licence "
            f"asks of KyprX: <a href='{html.escape(record)}'>CREDITS.md</a>.</p>")


#: How each project KyprX is built on stands, as the daemon names it (`Requirements`).
NEEDS_WORDS = {"ok": "installed and running", "missing": "not installed",
               "not running": "installed, not running", "too old": "too old"}

#: What the box and *About KyprX…* say when the daemon could not find out what is installed.
NEEDS_UNKNOWN = "KyprX could not find out what is installed here."


def needs_text(needs: list) -> str:
    """Projects KyprX is built on, as a table: a line each -- the name a link to where it lives,
    the version, how it stands -- and under one that is not right, what is wrong and what to do."""
    rows = []
    for n in needs:
        name = html.escape(str(n.get("name") or ""))
        url = html.escape(str(n.get("url") or ""))
        state = str(n.get("state") or "")
        rows.append(f"<tr><td><a href='{url}'>{name}</a></td>"
                    f"<td style='padding-left:12px'>{html.escape(str(n.get('version') or ''))}</td>"
                    f"<td style='padding-left:12px'>{html.escape(NEEDS_WORDS.get(state, state))}"
                    f"</td></tr>")
        if state != "ok":
            rows.append(f"<tr><td colspan='3' style='{WARNING_STYLE}'>"
                        f"{html.escape(str(n.get('detail') or ''))}<br>"
                        f"{html.escape(str(n.get('fix') or ''))}</td></tr>")
    return f"<table>{''.join(rows)}</table>" if rows else NEEDS_UNKNOWN


#: What waits for the next login, said as one line. KyprX's part of the compositor older than the
#: rest of KyprX lacks the keys added since, and tiles as it did or not at all -- and the
#: compositor reads its part again only at login (the head of `kwin-script/contents/ui/main.qml`
#: has the finding), so whatever waits, the one thing to do is the same, and it is said once, with
#: what waits behind it. Switched off and off the desk are choices rather than steps still to take,
#: and the Tiling tab and the band at the top already say them.
LOGIN_LINE = "Part of KyprX starts only at the next login: log out and back in."

#: The tiling's states that wait for the login, as the daemon names them (`tiling_state`), and what
#: each means until then. A part from before an update goes on tiling as it did, and only what is
#: new waits -- the Tiling tab's band says the same (`TILING_OLD_SCRIPT`).
TILING_WAITS = {
    "old-script": "Until then the desktop tiles as it did, and what is new on the Tiling tab "
                  "waits.",
    "no-script": "Until then nothing is tiled: KyprX's part of the compositor has not asked for "
                 "the tiling.",
}

#: The two actions of the compositor script's that hold no key: the daemon invokes them by name,
#: one to ask for the window list and one to have the tiling read its settings again, and nobody
#: presses either. `missing_actions` names them when the script lacks them, and the count of keys
#: that do nothing leaves them out: they are not keys. A part of the compositor too old to have
#: them is said by the tiling's own words instead (`TILING_WAITS`).
KEYLESS_ACTIONS = ("KyprXInventory", "KyprXTiling")

#: One sentence each, behind the mark on each section. The rest -- what the folder holds, when a
#: notification is said -- is in `docs/user-guide/settings.md`.
NOTIFY_HINT = ("Failures -- a title bar refused, a wallpaper or its colour that would not go on, "
               "the KyprX folder not applied. Nothing is said when things go well.")

FOLDER_HINT = ("Everything KyprX controls on this desk, as files you can copy to another "
               "machine, keep in git or edit. KyprX keeps them up to date by itself, and applies "
               "what arrives there by itself -- after keeping a copy of the desk.")

TIDY_TIP = ("Give every rule whose only job is forcing a title bar this app's naming. Rules that "
            "also pin an activity or a desktop keep their names.")


class SettingsTab(QWidget):
    """What this app keeps about itself: how it speaks up, the KyprX folder that carries the setup
    elsewhere, what is wrong on this machine while something is, and the big changes.

    Only what somebody comes here to set or to do is on the page every time. What KyprX needs and
    the Problems box appear while they have something to say -- the band above every tab already
    names a missing project, and its *What to do* opens this page -- and the versions and the
    credits, read once and rarely again, are behind *About KyprX…*.
    """

    #: What the window's footer should say: what a button on this page did, or why it did not.
    says = Signal(str)
    #: *Check again* found out afresh what KyprX needs, so the band above every tab is redrawn.
    looked_again = Signal()

    def __init__(self, client: Client, parent=None):
        super().__init__(parent)
        self.c = client

        tidy = QPushButton("Tidy up rule names")
        tidy.clicked.connect(self._normalize)
        tidy.setToolTip(TIDY_TIP)
        #: Shown only while there is a rule to rename, like the button beside it: greyed, it was
        #: one more control on every visit, for a repair most desks never need.
        tidy.setVisible(False)
        #: The second repair, and one that changes how the desk looks: it gives a title bar back to
        #: every window the decoration's leftover group was hiding one on. Shown only while there
        #: is one, beside the line that says what it is.
        self.bars_back = QPushButton("Give those windows their title bars back")
        self.bars_back.setToolTip("Removes the decoration's leftover [Exceptions] group. A copy of "
                                  "the desk is kept first.")
        self.bars_back.clicked.connect(self._remove_stray)
        self.bars_back.setVisible(False)
        #: An ellipsis, because it asks before it does anything -- as every button on the row it
        #: stands in does.
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
        #: On the row of the changes whose work it undoes, and first on it: the way back is what
        #: somebody looks for after pressing one of the others.
        self.back = QPushButton("Go back to a copy…")
        self.back.clicked.connect(self._go_back)
        self.back.setToolTip("Put the desk back as it was before an earlier change that wrote a "
                             "great deal at once.")
        #: The version this window runs. Its defaults have a version too (`daemon/defaults.py`),
        #: which is a number for the code and the tests and means nothing to anybody reading this.
        self.version = QLabel(f"KyprX {RUNNING or '(version unknown)'}")
        self.version.setEnabled(False)
        about = QPushButton("About KyprX…")
        about.setToolTip("The version of each project KyprX is built on, and who made what it "
                         "works with.")
        about.clicked.connect(self._about)
        #: The one door to a new version, beside the version it would replace. Asked only when
        #: pressed: KyprX never looks by itself (`daemon/update.py`).
        self.look = QPushButton("Look for a new version")
        self.look.setToolTip("Ask which version of KyprX is the newest -- KyprX's public "
                             "repository, or for a clone the branch it follows -- and see how "
                             "this installation is updated. Asked only when pressed.")
        self.look.clicked.connect(self._look_for_update)
        self._looking: QProcess | None = None
        self._updating: QProcess | None = None
        self._update_started = 0.0

        #: Named for what it does rather than for the mechanism. "Notify" said neither what nor
        #: when, and everything the daemon ever announces is a failure -- a window that refuses a
        #: title bar, a wallpaper or its colour that did not go on, a KyprX folder not applied.
        self.notify = QCheckBox("Say when something did not work")
        self.notify.setToolTip("A notification on the desktop, and only when something failed.")
        self.notify.toggled.connect(lambda v: self.c.set_settings(notify=v))
        speaking = Section("Notifications", NOTIFY_HINT)
        speaking_column = QVBoxLayout(speaking)
        speaking_column.addWidget(self.notify)

        #: The KyprX folder: the path, to read and to copy, a door to the file manager, and how
        #: the folder stands with the desk. What travels is no file somebody remembers to export --
        #: it is always there, always current.
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
        file_box = Section("Your KyprX folder", FOLDER_HINT)
        self.file_box = file_box
        file_column = QVBoxLayout(file_box)
        file_column.addLayout(where)
        file_column.addWidget(self.folder_line)

        #: A project KyprX is built on that is not right here: what is wrong, and the command that
        #: puts it right on this system, selectable, and with *Copy the command* beside it -- the
        #: command is said, never run, as everywhere a package manager is involved (`UpdateDialog`).
        #: Hidden while every one is installed and running -- *About KyprX…* lists them all. The
        #: daemon keeps the answer; *Check again* is for after installing or updating one.
        self.needs_box = Section("What KyprX needs", SECTION_HINTS["What KyprX needs"])
        needs_column = QVBoxLayout(self.needs_box)
        self.needs_label = note()
        self.needs_label.setTextFormat(Qt.TextFormat.RichText)
        self.needs_label.setOpenExternalLinks(True)
        self.needs_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        check_again = QPushButton("Check again")
        check_again.setToolTip("Look again for the projects KyprX is built on, after installing "
                               "or updating one.")
        check_again.clicked.connect(self._check_again)
        #: One *Copy the command* per project that is not right and has a command, under *Check
        #: again*; rebuilt with the box (`_say_needs`).
        self.copy_buttons = QVBoxLayout()
        self.copy_buttons.setContentsMargins(0, 0, 0, 0)
        side = QVBoxLayout()
        side.setContentsMargins(0, 0, 0, 0)
        side.addWidget(check_again)
        side.addLayout(self.copy_buttons)
        side.addStretch(1)
        needs_row = QHBoxLayout()
        needs_row.setContentsMargins(0, 0, 0, 0)
        needs_row.addWidget(self.needs_label, 1)
        needs_row.addLayout(side)
        needs_column.addLayout(needs_row)
        self.needs_box.setVisible(False)

        #: What is wrong on this machine, one line each, in a box of its own rather than as a
        #: paragraph of run-on text under everything else -- and only while there is something:
        #: a box saying "nothing to report" on every visit is a box to read for nothing. Built empty
        #: and filled by `reload`: reading the daemon while this page is being constructed would
        #: make opening the window a read before it is on screen.
        self.problems = Section("Problems", SECTION_HINTS["Problems"])
        self.problems_column = QVBoxLayout(self.problems)
        self.problem_lines: list[QLabel] = []
        #: The two repairs this app offers -- *Tidy up rule names*, and the button that gives
        #: title bars back -- in the box with the faults they repair, each shown only while it has
        #: something to do.
        self.tidy = tidy
        tidy_row = QHBoxLayout()
        tidy_row.setContentsMargins(0, 0, 0, 0)
        tidy_row.addWidget(tidy)
        tidy_row.addWidget(self.bars_back)
        tidy_row.addStretch()
        self.problems_column.addLayout(tidy_row)
        self.problems.setVisible(False)

        #: Which KyprX this is, and the door to everything about it that is read rather than set.
        about_row = QHBoxLayout()
        about_row.addWidget(self.version)
        about_row.addWidget(about)
        about_row.addWidget(self.look)
        about_row.addStretch()

        #: The changes that write a great deal, on a row of their own at the foot of the page:
        #: the way back first, then the three that move the desk furthest, in the order they go --
        #: KyprX's defaults, plain KDE, KyprX gone.
        big = QHBoxLayout()
        big.addWidget(self.back)
        big.addStretch()
        big.addWidget(self.restore)
        big.addWidget(self.take_off_button)
        big.addWidget(self.remove_button)

        #: Each box takes the height of what is in it and no more. Measured on screen rather than
        #: chosen: with a group box's own `Preferred` policy in both directions and a word-wrapped
        #: label inside, two boxes took 270 of the window's 720 pixels, height the rest of the page
        #: needs.
        layout = QVBoxLayout(self)
        for box in (speaking, file_box, self.needs_box):
            box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
            layout.addWidget(box)
        layout.addWidget(self.problems)
        layout.addStretch()
        layout.addLayout(about_row)
        layout.addLayout(big)

    def _about(self) -> None:
        # From the daemon's memory: it looks again when this window claims the interface and when
        # *Check again* asks, so opening this costs no look.
        AboutDialog(self, self.version.text(), needs_text(self.c.requirements()),
                    credits_text()).exec()

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

    def _process(self, argv: list[str], done) -> QProcess:
        """Not started; `done(process, status)` at the end, or -1 when it could not start."""
        proc = QProcess(self)
        proc.setProgram(argv[0])
        proc.setArguments(argv[1:])
        proc.finished.connect(lambda code, _status: done(proc, code))
        proc.errorOccurred.connect(
            lambda error: done(proc, -1) if error == QProcess.ProcessError.FailedToStart else None)
        return proc

    def _look_for_update(self) -> None:
        if self._looking is not None:
            return
        self.look.setEnabled(False)
        self.says.emit("Looking for a new version of KyprX…")
        self._looking = proc = self._process(check_argv(), self._looked)
        proc.start()

    def _looked(self, proc, code: int) -> None:
        if self._looking is not proc:
            return
        self._looking = None
        self.look.setEnabled(True)
        out = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
        proc.deleteLater()
        try:
            answer = json.loads(out) if code == 0 else {}
        except ValueError:
            answer = {}
        if not isinstance(answer, dict):
            answer = {}
        state = answer.get("state")
        if state == "current":
            said = str(answer.get("detail") or "this is the newest version")
            self.says.emit(f"{said[:1].upper()}{said[1:]}.")
        elif state == "newer":
            box = UpdateDialog(self, answer, dry_run=bool(self.c.dry_run()))
            if box.exec() == QDialog.DialogCode.Accepted and box.update_now:
                self._update_now()
        else:
            why = answer.get("detail") or "no answer came back"
            self.says.emit(f"Could not find out whether there is a new version: {why}.")

    def _update_now(self) -> None:
        if self._updating is not None:
            return
        self.look.setEnabled(False)
        self.says.emit("Updating KyprX… a window opened with the settings key closes when the "
                       "background service restarts: open it again.")
        self._update_started = time.time()
        self._updating = proc = self._process(update_argv(), self._updated)
        proc.start()

    def _updated(self, proc, code: int) -> None:
        if self._updating is not proc:
            return
        self._updating = None
        self.look.setEnabled(True)
        said = bytes(proc.readAllStandardError()).decode("utf-8", "replace")
        proc.deleteLater()
        if code == 0:
            self.says.emit("KyprX is updated. Close this window and open it again, and log out and "
                           "back in to finish.")
            return
        QMessageBox.warning(self, "The update did not go through",
                            update_failure(self._update_started, said))

    def reload(self) -> None:
        # This tab is a live one: `reload` runs on every change the daemon reports while it is
        # open. `setChecked` emits `toggled`, so without the guard each change would write the
        # setting again and bring on the next change -- a loop the old home of this checkbox, the
        # row above the tabs, was never exposed to.
        self.notify.blockSignals(True)
        self.notify.setChecked(bool((self.c.settings() or {}).get("notify", False)))
        self.notify.blockSignals(False)
        self._say_folder(self.c.folder())
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
        #: What waits for the login (`LOGIN_LINE`): the tiling's step still to take, then the keys
        #: the registry has not got.
        waits = []
        tiling = TILING_WAITS.get(str(d.get("tiling_state") or ""))
        if tiling:
            waits.append(tiling)
        missing = [a for a in d.get("missing_actions") or [] if a not in KEYLESS_ACTIONS]
        if missing:
            # Counted, because it is rarely one: a part of the compositor older than the rest of
            # KyprX lacks every action added since, and the tiling's alone are nineteen.
            waits.append(("One key does nothing until then: " if len(missing) == 1
                          else f"{len(missing)} keys do nothing until then: ")
                         + ", ".join(missing) + ".")
        if waits:
            found.append((LOGIN_LINE, " ".join(waits)))
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
                          f"itself while it is on the desk; the button below removes it now."))
        self.tidy.setVisible(bool(d.get("renamable")))
        self.bars_back.setVisible(stray is not None)
        self._say_problems(found)

    def _say_needs(self, needs: list) -> None:
        """What KyprX needs, while something is not right: a line for each project that is not,
        with what is wrong and what to do -- or the sentence that says nothing could be found out.
        Hidden while every one is installed and running."""
        wrong = [n for n in needs if n.get("state") != "ok"]
        self.needs_label.setText(needs_text(wrong))
        while self.copy_buttons.count():
            gone = self.copy_buttons.takeAt(0).widget()
            if gone is not None:
                gone.deleteLater()
        commands = [n for n in wrong if n.get("command")]
        for n in commands:
            command = str(n["command"])
            copy = QPushButton("Copy the command" if len(commands) == 1
                               else f"Copy the command for {n.get('name')}")
            copy.setToolTip(command)
            copy.clicked.connect(lambda _=False, command=command: self._copy_command(command))
            self.copy_buttons.addWidget(copy)
        self.needs_box.setVisible(bool(wrong) or not needs)

    def _copy_command(self, command: str) -> None:
        QGuiApplication.clipboard().setText(command)
        self.says.emit("The command is on the clipboard: paste it in a terminal.")

    def _check_again(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            needs = self.c.requirements(refresh=True)
        finally:
            QApplication.restoreOverrideCursor()
        self._say_needs(needs)
        wrong = [str(n.get("name")) for n in needs if n.get("state") != "ok"]
        self.says.emit("Looked again: " + (", ".join(wrong) + " still not right." if wrong
                                            else "every one is installed and running."))
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

    def _say_problems(self, found: list) -> None:
        """One line per thing that is wrong, with the machine's own words behind each one, and the
        box shown only while there is one.

        Rebuilt rather than appended to: this runs on every change the daemon reports while the
        page is open, and a box that grows a line each time would be a page that never settles.
        """
        for line in self.problem_lines:
            self.problems_column.removeWidget(line)
            line.setParent(None)
            line.deleteLater()
        self.problem_lines = []
        for text, detail in found:
            line = note(text)
            if detail:
                line.setToolTip(detail)
            self.problem_lines.append(line)
            self.problems_column.insertWidget(len(self.problem_lines) - 1, line)
        self.problems.setVisible(bool(found))

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
