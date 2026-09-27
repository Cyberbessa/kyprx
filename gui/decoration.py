"""The window decoration's own settings, and the door to them.

The title bar is set in the decoration's own dialog, not here, and what is changed there stays.
`open_decoration_settings` opens that dialog by whichever door this desktop has -- Klassy's own
settings app, or its page in System Settings -- and `TitleBarBox` is the Appearance tab's box that
says so and holds the button. The Settings tab has the same button, and during a dry run the window
closes both, because the decoration's dialog saves for real.
"""

from __future__ import annotations

import shutil
import subprocess

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from widgets import SECTION_HINTS, Section


# ---------------------------------------------------------------------- title bar

#: One line. What KyprX's own title bar default is -- the glyphs, the opacity, the spacing, the
#: button colours -- is declared in `daemon/defaults.py` and described for the user in
#: `docs/user-guide/appearance.md#title-bar`, and *Restore KyprX's defaults* is what puts it back;
#: a settings window is not where a list of declared values belongs.
TITLEBAR_NOTE = ("The title bar is the decoration's own settings, and what you change there "
                 "stays.")

#: The decoration's dialog cannot be opened on a chosen tab -- read in its source: no argument,
#: no environment variable, no tab remembered between runs -- so the button says where to click
#: rather than promising to land there.
TITLEBAR_BUTTON_TIP = ("Opens the decoration's own settings. The title bar is its Titlebar tab, "
                       "one click in: the dialog cannot be asked to open on it.")


def open_decoration_settings() -> None:
    """The decoration's own dialog, by whichever door this desktop has."""
    for candidate in ("klassy-settings", "systemsettings"):
        if shutil.which(candidate):
            subprocess.Popen([candidate] if candidate == "klassy-settings"
                             else [candidate, "kcm_klassydecoration"])
            return


class TitleBarBox(Section):
    """The last section of the Appearance tab: a line and a door, and no control.

    Nothing here reads the daemon and nothing writes. The section exists to say where the title
    bar is changed, and to open that place. A box rather than a `Field` because the form engine
    has no kind for a button.
    """

    def __init__(self, parent=None):
        super().__init__("Title bar", SECTION_HINTS["Title bar"], parent)
        note = QLabel(TITLEBAR_NOTE)
        note.setWordWrap(True)
        button = QPushButton("Title bar settings…")
        button.setToolTip(TITLEBAR_BUTTON_TIP)
        button.clicked.connect(open_decoration_settings)
        #: Kept so the window can close this door during a dry run -- see `DRY_RUN_DOOR_TIP`.
        self.door = button
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(button)
        row.addStretch()
        holder = QWidget()
        holder.setLayout(row)
        layout = QVBoxLayout(self)
        layout.addWidget(note)
        layout.addWidget(holder)
