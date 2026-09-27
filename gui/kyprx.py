#!/usr/bin/env python3
"""KyprX — windows, decoration, blur and tiling in one place.

Widgets rather than QML: the desktop's own widget style is the decoration theme itself, so the
window comes out looking like everything else without a line of theming. All the logic lives in
the daemon; nothing here writes to a config file.

What is deliberately **not** here: the whole surface of the decoration's settings. That belongs to
its own settings app, and reimplementing it would create a second truth for every field. What is
here is what gets changed together — the per-window choices, and the handful of global settings
that govern the look as a whole.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

from PySide6.QtCore import SLOT, QSize, Qt, QTimer, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QTabWidget, QVBoxLayout, QWidget)

#: The folder this file really is in, not that of the link it was started through -- see the same
#: line in `daemon/kyprd.py`.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from cheatsheet import Cheatsheet  # noqa: E402
from client import Client  # noqa: E402
from decoration import TITLEBAR_BUTTON_TIP  # noqa: E402
from dialogs import ChangesDialog  # noqa: E402
from fields import EFFECTS_FIELDS  # noqa: E402
from form import PluginPage, SettingsPage  # noqa: E402
from picker import open_picker  # noqa: E402
from tab_appearance import AppearancePage  # noqa: E402
from tab_settings import SettingsTab  # noqa: E402
from tab_shortcuts import ShortcutBlock, ShortcutsTab  # noqa: E402
from tab_tiling import TilingPage  # noqa: E402
from tab_wallpaper import WallpaperTab  # noqa: E402
from tab_windows import WindowsTab  # noqa: E402
from top_strip import TopStrip  # noqa: E402
from widgets import DANGER_STYLE, WARNING_STYLE, warning  # noqa: E402
import tab_settings  # noqa: E402

#: This app's own icon, its PNGs in the working tree: one per size, so that a small title or task
#: bar gets the size made for it rather than a big one squeezed. `realpath` because the interface
#: runs through a link in ~/.local/bin, and the icon is beside the real file, not the link.
ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                        "share", "icons", "hicolor")
ICON_SIZES = (16, 22, 24, 32, 48, 64, 128, 256, 512)


def app_icon() -> QIcon:
    icon = QIcon()
    for size in ICON_SIZES:
        path = os.path.join(ICON_DIR, f"{size}x{size}", "apps", "kyprx.png")
        if os.path.exists(path):
            icon.addFile(path, QSize(size, size))
    return icon

#: The overlays this app can be started as, by the flag that starts one: the window class it takes
#: and what opens it. A table rather than a chain of `if`s, because each entry has to agree with
#: `daemon/kyprd_names.py:OVERLAYS` and a list is easier to keep beside another list.
#:
#: The wallpaper entry is a **function**, not a class, because which of its two layouts to build
#: is a setting and is only known after the daemon has been asked. It is called the same way, so
#: nothing below has to know the difference.
OVERLAYS = {
    "--cheatsheet": ("kyprx-cheatsheet", Cheatsheet),
    "--wallpaper": ("kyprx-wallpaper", open_picker),
}


# ---------------------------------------------------------------------- main window

#: What the band says while the daemon is in dry run. It says where the words went, because
#: "written down" without a where sent people looking in this window for them.
DRY_RUN_BAND = ("<b>Dry run.</b> Nothing is written. Every change you make is written down "
                "instead, in plain words, where <i>kyprd --dry-run</i> is running -- the "
                "terminal it was started from, or the journal.")

#: And when the dry run this window was opened on is over.
DRY_RUN_OVER = ("<b>The dry run is over.</b> The daemon that was only writing things down has "
                "gone, and the one that answers now writes for real -- so this window has stopped "
                "sending anything. Close it and open it again to go on.")

#: The doors to the decoration's own settings, when this window is on a dry run. That program is
#: not this app: it writes its own file and reloads the compositor itself, and a dry run cannot
#: hold any of it back.
DRY_RUN_DOOR_TIP = ("Closed during a dry run: the decoration's own settings save for real, and a "
                    "dry run cannot hold that back.")


#: The band across the window while KyprX is off the desk.
OFF_BAND = ("<b>KyprX is off this desk.</b> New windows are left alone, and your setup is kept — "
            "in the KyprX folder and in the copy of the desk taken before.")


#: The tabs, in order: the attribute on `MainWindow`, the label, and the names the command line
#: accepts for it. Two lists used to say this — a name-to-index dict and the tuple that built the
#: tabs — and they had to agree with nothing checking that they did.
#:
#: The old spellings are kept as extra names. `border` and `profile` were tab names for as long as
#: this app has had a command line -- `profile` the Settings tab's, while the export was the only
#: profile there was -- and a launcher or an alias still passing one of them would otherwise land
#: on the Windows tab with nothing said — `TABS.get` has no way to complain. The profiles live on
#: the Appearance tab now, and that is where `profile` and `profiles` both land; so does
#: `titlebar`, which was a tab of its own, and now names the section at the bottom of Appearance
#: that points at the decoration's dialog.
#:
#: A fourth thing in each row: the line the tab itself carries, said before the click rather than
#: after it. It costs no room on screen, which is what makes it the cheapest of these.
TAB_ORDER = [
    ("windows", "Windows", ("windows",),
     "One row per window: which of KyprX's treatments each one gets."),
    ("appearance", "Appearance", ("appearance", "titlebar", "border", "profiles", "profile"),
     "The desktop's colours, and what every window's frame looks like."),
    ("effects", "Effects", ("effects",),
     "Blur behind windows, and the movement they make when they are moved."),
    ("wallpaper", "Wallpaper", ("wallpaper", "wallpapers"),
     "What the wallpaper key offers you, and how it looks when it opens."),
    ("tiling", "Tiling", ("tiling",),
     "How windows are laid out, the space between them, and how focus moves."),
    ("shortcuts", "Shortcuts", ("shortcuts",),
     "Every key KyprX and the tiler answer to, and what each one does."),
    ("settings_tab", "Settings", ("settings",),
     "What KyprX keeps about itself: the backup file, and its own defaults."),
]

TABS = {name: i for i, (_, _, names, _hint) in enumerate(TAB_ORDER) for name in names}


class MainWindow(QWidget):
    def __init__(self, client: Client, tab: str = "windows"):
        super().__init__()
        self.c = client
        self.setWindowTitle("KyprX")
        # Read from the file rather than asked of the icon theme, for the reason `copy_icon`
        # records: outside a graphical session `QIcon.fromTheme` returns nothing at all. The theme
        # is only the fallback for a tree without the file, and the one `fromTheme` this app allows
        # itself, because nothing depends on the answer: a window with no icon is still a window.
        icon = app_icon()
        self.setWindowIcon(icon if not icon.isNull() else QIcon.fromTheme("kyprx"))
        self.resize(1000, 720)
        #: Narrower than this and the four presets no longer fit side by side -- the grid does not
        #: wrap, it clips -- and the widest row of the forms loses its menu off the edge. There was
        #: no minimum at all, so the window could be dragged smaller than its own contents.
        self.setMinimumSize(820, 560)

        self.banner = warning()
        #: While KyprX is off the desk: the one sentence that explains everything else on screen
        #: doing nothing, and the way back, above every tab rather than on one of them.
        off_text = warning(OFF_BAND)
        off_text.setTextFormat(Qt.TextFormat.RichText)
        put_back = QPushButton("Put my setup back")
        put_back.setToolTip("Restore the copy of the desk kept before KyprX was taken off, then "
                            "apply whatever arrived in the KyprX folder meanwhile.")
        put_back.clicked.connect(self._put_back)
        off_row = QHBoxLayout()
        off_row.setContentsMargins(0, 0, 0, 0)
        off_row.addWidget(off_text, 1)
        off_row.addWidget(put_back)
        self.off_band = QWidget()
        self.off_band.setLayout(off_row)
        self.off_band.setVisible(False)
        self._off_copy = ""

        #: When one of the five projects KyprX is built on is missing or not running: which ones,
        #: and the way to what to do about it. Above every tab, because one missing project breaks
        #: something on several -- each tab it breaks also says so on itself.
        self.needs_text = warning()
        what_to_do = QPushButton("What to do")
        what_to_do.setToolTip("Open the Settings tab, which says what is wrong and how to put it "
                              "right on this system.")
        what_to_do.clicked.connect(lambda: self.tabs.setCurrentWidget(self.settings_tab))
        needs_row = QHBoxLayout()
        needs_row.setContentsMargins(0, 0, 0, 0)
        needs_row.addWidget(self.needs_text, 1)
        needs_row.addWidget(what_to_do)
        self.needs_band = QWidget()
        self.needs_band.setLayout(needs_row)
        self.needs_band.setVisible(False)

        #: After an update while KyprX ran: this window and the background service are different
        #: versions. A newer window offers to restart the service; an older one can only be closed
        #: and opened again. See `_check_versions`.
        self.update_text = warning()
        self.restart_service = QPushButton("Restart the background service")
        self.restart_service.setToolTip("Starts the background service again, as the version now "
                                        "installed. A window opened with the settings key closes "
                                        "with it; open it again.")
        self.restart_service.clicked.connect(self._restart_service)
        update_row = QHBoxLayout()
        update_row.setContentsMargins(0, 0, 0, 0)
        update_row.addWidget(self.update_text, 1)
        update_row.addWidget(self.restart_service)
        self.update_band = QWidget()
        self.update_band.setLayout(update_row)
        self.update_band.setVisible(False)

        #: What is always on screen, and it is deliberately the three things somebody comes here
        #: to do rather than the three this app has to configure. `Notify` and the door to the
        #: decoration's own settings went to the Settings tab, which is where a thing set once
        #: belongs.
        self.strip = TopStrip(client)
        self.strip.says.connect(self._say)
        self.strip.loaded.connect(self._look_loaded)
        self.strip.auto_changed.connect(lambda on: self.appearance.colours.set_auto(on))
        #: The looks are painted on a settle rather than on the spot, and the reason is a pair
        #: of numbers. Measured over the bus against a daemon on this desk, 25 calls each with the
        #: round trip subtracted: `Settings` costs 0.1 ms and `Profiles` 4.0 ms with no profile
        #: kept, 5.5 with one, 9.9 with three and 16.2 with six -- about 2 ms a profile, because
        #: working out what the desktop is wearing means parsing the decoration's 38 KB schema and
        #: six config files, and drawing each profile means reading its colour scheme.
        #:
        #: The line at the bottom of the window reads the cheap one on every change the daemon
        #: reports, and the daemon reports one per window appearing -- so a login, or a workspace
        #: full of windows closing, is dozens of them back to back, answered on the loop that also
        #: serves the compositor. Restarting this timer collapses that burst into one read.
        self._looks_pending = QTimer(self)
        self._looks_pending.setSingleShot(True)
        self._looks_pending.setInterval(250)
        self._looks_pending.timeout.connect(self._paint_looks)

        self.windows = WindowsTab(client)
        self.windows.copied.connect(self._say)
        #: Until when the footer is saying something of its own. Without it, the daemon's next
        #: "something changed" — which arrives within a second of any write — wipes the line, and
        #: a confirmation nobody can read is not a confirmation.
        self._status_until = 0.0
        self.appearance = AppearancePage(client)
        self.effects = PluginPage(EFFECTS_FIELDS, client,
                                  [("better_blur_dx", "Blur windows", "Blur"),
                                   ("kwin4_effect_geometry_change",
                                    "Animate windows as they move and resize",
                                    "Window animation")])
        self.tiling = TilingPage(client)
        self.wallpaper = WallpaperTab(client)
        self.shortcuts = ShortcutsTab(client)
        self.shortcuts.says.connect(self._say)
        self.settings_tab = SettingsTab(client)
        self.settings_tab.says.connect(self._say)
        self.settings_tab.looked_again.connect(self._header)
        #: The three pages that write by themselves say what they wrote in the window's own line,
        #: the road `TopStrip` and the Windows table already take.
        self.forms = (self.appearance, self.effects, self.tiling)
        for page in self.forms:
            page.says.connect(self._say)

        self.tabs = QTabWidget()
        for index, (attribute, label, _names, hint) in enumerate(TAB_ORDER):
            self.tabs.addTab(getattr(self, attribute), label)
            self.tabs.setTabToolTip(index, hint)
        self.tabs.currentChanged.connect(self._tab_changed)

        #: The window's one voice: what is happening now, what has just happened, and what the
        #: daemon refused. Three things write here and the order between them is in `_say`.
        #:
        #: Two lines of height are reserved whether or not there is anything to say. It used to
        #: take no height at all until it had a line, so everything above it jumped at the exact
        #: moment somebody was reading a confirmation -- and now that every change applies by
        #: itself, that moment is every edit. A minimum rather than a fixed height: a long line on
        #: a narrow window grows rather than being cut in half.
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.status.setMinimumHeight(2 * self.status.fontMetrics().lineSpacing())

        #: The separator the strip already wears, at the other end and for the same reason: it is
        #: what makes the line below read as the window's own rather than as the end of whichever
        #: tab is open.
        rule = QFrame()
        rule.setFrameShape(QFrame.Shape.HLine)
        rule.setFrameShadow(QFrame.Shadow.Sunken)

        layout = QVBoxLayout(self)
        layout.addWidget(self.banner)
        layout.addWidget(self.update_band)
        layout.addWidget(self.needs_band)
        layout.addWidget(self.off_band)
        layout.addWidget(self.strip)
        layout.addWidget(self.tabs)
        layout.addWidget(rule)
        layout.addWidget(self.status)

        self.tabs.setCurrentIndex(TABS.get(tab, 0))
        #: The tabs that show the state of things, as opposed to a form waiting on Apply. Only
        #: these follow the daemon's "something changed": repainting a form on a signal is what
        #: made every checkbox snap back to where it was.
        self.live_tabs = (self.windows, self.shortcuts, self.settings_tab, self.wallpaper)
        client.changed.connect(self.on_changed)
        client.colour_ready.connect(self.on_colour_ready)
        client.failed.connect(self._failed)
        client.mode_changed.connect(self._mode_changed)
        self._mode_changed(client.dry_run(), False)
        # The daemon asks the compositor for an inventory and the answer comes back
        # asynchronously; a second later the table reflects what is really there.
        QTimer.singleShot(1200, self.load_current)
        self.load_current()

    def _check_versions(self) -> None:
        """Say when this window and the background service are not the same version of KyprX.

        Asked when the window opens and every time the daemon is replaced (`_mode_changed`), which
        is what a restart is. Only a window newer than the service offers the restart, and never
        over a dry run: a service started by hand in dry run is not the unit a restart starts.
        """
        if self.c.held or self.c.gone:
            return
        running = str((self.c.diagnostics() or {}).get("version") or "")
        mine = tab_settings.RUNNING
        if not running or not mine or running == mine:
            self.update_band.setVisible(False)
            return

        def parts(version: str) -> list[int]:
            return [int(p) if p.isdigit() else 0 for p in version.split(".")]

        newer = parts(mine) > parts(running)
        if newer:
            self.update_text.setText(f"KyprX {mine} is installed, and the background service is "
                                     f"still {running}. Restart it to use {mine}.")
        else:
            self.update_text.setText(f"This window is KyprX {mine}, and the background service "
                                     f"is {running}. Close this window and open it again.")
        self.update_text.setVisible(True)
        self.restart_service.setVisible(newer and not self.c.dry_run())
        self.update_band.setVisible(True)

    def _restart_service(self) -> None:
        """`systemctl --user restart kyprd`: the unit, never the process -- see AGENTS.md."""
        try:
            subprocess.Popen(["systemctl", "--user", "restart", "kyprd"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as e:
            self._say(f"The background service could not be restarted: {e}")
            return
        self._say("Restarting the background service… ")

    def _mode_changed(self, dry: bool, held: bool) -> None:
        """Say which daemon this window is talking to, every time that can have changed.

        Decided once, when the window was built, this went on saying "Nothing is written" after
        the dry-run daemon had gone and the real one had been started in its place by the very
        next call -- see `Client._owner_changed`, which is what now stops the window sending.
        """
        self._check_versions()
        if held:
            self.banner.setText(DRY_RUN_OVER)
            self.banner.setStyleSheet(DANGER_STYLE)
            self.banner.setVisible(True)
        elif dry:
            self.banner.setText(DRY_RUN_BAND)
            self.banner.setStyleSheet(WARNING_STYLE)
            self.banner.setVisible(True)
        else:
            self.banner.setVisible(False)
        for door in (self.appearance.title_bar.door, self.settings_tab.door):
            door.setEnabled(not (dry or held))
            door.setToolTip(DRY_RUN_DOOR_TIP if (dry or held) else TITLEBAR_BUTTON_TIP)

    def keyPressEvent(self, event):  # noqa: N802 — Qt's spelling
        """Escape closes the window, as it closes the other two this app opens with a key.

        Not while a shortcut row is listening: there Escape already means *leave that key as it
        was*, and it is handled by the row itself.
        """
        if event.key() == Qt.Key.Key_Escape and not any(row._editing
                                                        for row in self.shortcuts.rows):
            self.close()
            return
        super().keyPressEvent(event)

    @Slot()
    def raise_window(self):
        """Somebody started a second interface. Come forward instead of letting them open one."""
        # Clear only the minimised bit. `showNormal()` also clears maximised and full screen, so
        # launching the app again would un-maximise the window somebody had maximised.
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):  # noqa: N802 — Qt's spelling
        # Leaving the desktop's shortcuts blocked because a window closed mid-edit would be a
        # worse fault than the one the edit mode fixes.
        self.shortcuts.stop_editing()
        # And send whatever was ticked in the last fraction of a second. The table collects ticks
        # for a moment before writing them; closing inside that moment used to throw them away
        # with no sign that anything had been lost.
        self.windows.flush(closing=True)
        for page in self.forms:
            page.flush()
        super().closeEvent(event)

    def _say(self, message: str) -> None:
        """Put a line of this app's own in the footer, and keep it there long enough to read.

        Painted immediately: the calls that follow one of these block the event loop for as long
        as the compositor takes, so a line left to the next paint would appear after the thing it
        was warning about had already finished.

        **Three things write this line, and this is the order between them.** `_header` writes the
        standing state of the desktop and is the quiet one: it stands down for six seconds for
        anything said here. This is the loud one -- a confirmation, or a slow change announced
        before the call that freezes the window. A refusal comes through here too (`_failed`),
        which is precisely what it did not do before.

        And the six seconds now end by themselves. `_header` is what puts the standing line back,
        and it used to run only when something else happened to call it, so on a settled desktop a
        confirmation sat there for the rest of the session.
        """
        # In a dry run every one of these lines describes something that did not happen, and it
        # has to say so on the line itself: the band at the top is out of sight by the time the
        # eye is down here, and "Imported." read as a fact.
        if message and self.c.dry_run() and not self.c.held:
            message = f"<b>Dry run</b> -- nothing was written: {message}"
        self.status.setText(message)
        self.status.repaint()
        self._status_until = time.monotonic() + 6 if message else 0.0
        if message:
            QTimer.singleShot(6100, self._header)

    def _failed(self, message: str) -> None:
        """The daemon refused something, said in words somebody can do something about.

        Through `_say`, so a refusal is held the six seconds a confirmation is held. It used to be
        written straight into the line with no hold at all -- and the daemon says "something
        changed" within a second of every write, so the one line most worth reading was the one
        most likely to be wiped before anybody read it.

        The method name goes with it. `gui/client.py` puts `SetGroups: ` in front of whatever the
        bus said, which names a call this window never mentions anywhere else.
        """
        text = str(message).strip()
        if text.lower().startswith("error:"):
            text = text[len("error:"):].strip()
        else:
            head, _, rest = text.partition(": ")
            if rest and head.isalnum():
                text = rest
        self._say(text or "That did not go through.")

    def _paint_looks(self) -> None:
        """One `Profiles` read, and everything that draws from it.

        The table on the Appearance tab is painted from the same answer rather than asking again:
        the read is the expensive one, and the two must agree about which look is on -- that fact
        is what the bold row means.
        """
        data = self.c.profiles() or {}
        self.strip.set_looks(data)
        if self.tabs.currentWidget() is self.appearance:
            self.appearance.profiles.reload(data)

    def _look_loaded(self) -> None:
        """A look went on from the strip, and it wrote three things the Appearance tab has
        controls for — the strength, the corner radius and the outline.

        The form refuses to repaint while a field is touched, and here the touched field is the
        one whose value was just asked to be replaced. `ProfilesBox._load` does exactly this after
        its own load, and for the same reason.
        """
        self.appearance.touched.clear()
        QTimer.singleShot(400, lambda: self.appearance.load(self.c.groups()))

    def on_changed(self) -> None:
        """The daemon says the world moved. Only the live tabs care."""
        self._header()
        self._looks_pending.start()
        current = self.tabs.currentWidget()
        if current in self.live_tabs:
            current.reload()
        elif current is self.appearance:
            # The colour box, and through its `reloaded` signal the two things on the form that
            # depend on it -- the outline's swatch and the button that fills it. Never the rest of
            # the form: this page is kept out of `live_tabs` because repainting a form under
            # somebody's hands throws their edit away, and a field already touched is skipped even
            # among those two. The box has a refusal of its own for when a write of its is pending.
            self.appearance.colours.load(self.c.theme())
            # The profiles are painted by `_paint_looks`, which the strip needs anyway --
            # their bold row is "the look on the desktop now", a fact that any change on any tab
            # can move. The strength a loaded profile moves is this box's own.
            self.appearance.transparency.reload()

    def on_colour_ready(self, _target: str) -> None:
        """A wallpaper's colour is known now, and only the colour box draws from that.

        Its own slot rather than `on_changed`, because that one redraws the live tab -- and on the
        Wallpaper tab a redraw is a scan of every folder and a question to the shell, which used
        to happen once per stop of the picker's selection, for one line on the Appearance tab.
        """
        if self.tabs.currentWidget() is self.appearance:
            self.appearance.colours.load(self.c.theme())

    def _tab_changed(self, _index: int) -> None:
        """Leaving a tab is leaving whatever it had half done.

        The shortcut editor is the one that matters: entering it suspends every shortcut on the
        desktop, and until now only closing the window gave them back. Walking away from the tab
        with a row still listening left a desk whose keys were all dead and nothing on screen
        saying why.
        """
        self.shortcuts.stop_editing()
        # And whatever was still settling on the page being left goes now. A change somebody made
        # and then walked away from is still a change they made.
        for page in self.forms:
            page.flush()
        self.load_current()

    def _put_back(self) -> None:
        """The way back from *Take KyprX off this desk*: the copy kept before it, shown first."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            changes = self.c.go_back_preview(self._off_copy) if self._off_copy else ""
        finally:
            QApplication.restoreOverrideCursor()
        if changes.startswith("error"):
            self._say("The copy of the desk kept before KyprX was taken off cannot be put back: "
                      + changes.removeprefix("error:").strip()
                      + " Go back to a copy…, on the Settings tab, lists the others.")
            return
        box = ChangesDialog(self, "Put your setup back?",
                            "Restores the desk exactly as it was before KyprX was taken off, and "
                            "then applies whatever arrived in your KyprX folder meanwhile. A copy "
                            "of the desk as it is now is kept first. Below is exactly what would "
                            "change.", changes, "Put it back")
        if box.exec() != QDialog.DialogCode.Accepted:
            return
        self._say("Putting your setup back… the desktop's own tools take a few seconds")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            answer = self.c.put_back()
        finally:
            QApplication.restoreOverrideCursor()
        if not answer:
            self._say("Your setup is back, and KyprX is on the desk again.")
        elif answer.startswith("partial"):
            self._say("Most of it came back, but: " + answer.removeprefix("partial:").strip())
        else:
            self._say("That did not go through: " + answer.removeprefix("error:").strip())
        self.load_current()

    def load_current(self) -> None:
        """Read everything the visible tab needs. Called when a tab opens, not on a signal."""
        self._header()
        self._looks_pending.start()
        current = self.tabs.currentWidget()
        if hasattr(current, "reload"):
            current.reload()
        elif isinstance(current, SettingsPage):
            current.load(self.c.groups())

    def _header(self) -> None:
        """The strip, and the line at the bottom that says what it means right now.

        One read of the settings for both: the strip is painted from what was read here rather
        than reading again, because this runs on every tab change and on every change the daemon
        reports.

        The quiet voice of the three, and it gives way: while the window is saying something of
        its own the line below is left alone. See `_say`.
        """
        settings = self.c.settings()
        self.strip.reload(settings)
        folder_status = self.c.folder()
        self._off_copy = str(folder_status.get("off_copy") or "")
        self.off_band.setVisible(bool(folder_status.get("off")))
        # From the daemon's memory: it looks again when this window claims the interface, and when
        # the Settings tab's *Check again* asks, so this read costs nothing on every change.
        wrong = [str(n.get("name")) for n in self.c.requirements() if n.get("state") != "ok"]
        self.needs_text.setText("KyprX is missing part of what it is built on: "
                                + ", ".join(wrong) + "." if wrong else "")
        self.needs_band.setVisible(bool(wrong))

        if time.monotonic() < self._status_until:
            return
        # The control says "Adjust new windows" now, so the line under it says the same thing the
        # same way round. "Paused" was a word for a state nothing on screen is called any more.
        waiting = settings.get("waiting") or []
        if settings.get("paused") and waiting:
            self.status.setText(f"New windows are being left alone. {len(waiting)} waiting: "
                                + ", ".join(waiting[:5]) + ("…" if len(waiting) > 5 else ""))
        elif settings.get("paused"):
            self.status.setText("New windows are being left alone. Tick <i>Adjust new "
                                "windows</i> to catch them up.")
        else:
            self.status.setText("")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("KyprX")
    # Killed rather than closed, the window used to skip everything it does on the way out -- and
    # one of those things is handing the desktop its shortcuts back if a row was listening for
    # keys. So the two signals a session and a script send are turned into an ordinary quit. Python
    # only runs a signal handler when it gets control back, so a timer gives it some: a no-op
    # four times a second, which is what the PySide documentation recommends for exactly this.
    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    ticker = QTimer()
    ticker.timeout.connect(lambda: None)
    ticker.start(250)
    # Each overlay gets a window class of its own, and that is not cosmetic. They are frameless by
    # design, so to anything looking at window geometry it is an application that draws its own
    # title bar — and sharing a class with the settings window made the daemon conclude that
    # *this app* refuses a server-side decoration, and say so in the interface. A separate class
    # also lets the compositor's placement rule match on the class instead of on a title string.
    overlay = next((flag for flag in sys.argv[1:] if flag in OVERLAYS), None)
    window_class, widget = OVERLAYS.get(overlay, ("kyprx", None))
    app.setDesktopFileName(window_class)
    client = Client()
    if not client.available():
        # The one message somebody sees when nothing else works, so it says what to do rather than
        # naming a background process and a shell script to somebody who runs neither.
        QMessageBox.critical(None, "KyprX is not running",
                             "The part of KyprX that does the work did not answer, so there is "
                             "nothing to show. Installing it again is what puts it back: run "
                             "install.sh from the KyprX folder.")
        return 1
    if widget is not None:
        sheet = widget(client)
        sheet.show()
        sheet.activateWindow()
        return app.exec()
    # One settings window, and no more. The second one to start asks the first to come forward
    # and then leaves: two of them subscribe to the same changes and write back over each other,
    # and the shortcut editor's suspend-everything is desktop-wide, so whichever closes first
    # hands the desktop its shortcuts back while the other is still waiting for a key.
    if not client.claim_interface():
        return 0
    tab = sys.argv[1].lower() if len(sys.argv) > 1 else "windows"
    if tab not in TABS:
        # It opens on the first tab either way, as it always has. What it no longer does is go
        # there in silence -- `TABS.get` has no way to complain, so this is the complaint.
        print(f"kyprx: there is no tab called {tab!r}; opening "
              f"{TAB_ORDER[0][1]}. The names are: {', '.join(sorted(TABS))}", file=sys.stderr)
    window = MainWindow(client, tab)
    # Whatever happens to the window, the desktop gets its shortcuts back. Closing already does
    # this; quitting some other way — a session ending, a crash of the window and not the app —
    # did not, and a desktop with every shortcut suspended is a worse fault than the one the edit
    # mode exists to fix.
    app.aboutToQuit.connect(ShortcutBlock.release_all)
    app.aboutToQuit.connect(client.release_interface)
    client.on_raise(window, SLOT("raise_window()"))
    client.reclaim_on_restart()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
