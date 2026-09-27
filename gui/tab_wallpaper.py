"""The Wallpaper tab: which kind of wallpaper the picker lists, how the picker looks, where the
videos are, and when a video pauses.

Which kind is listed is not a setting of this app's: it is the wallpaper plugin the activity in use
is wearing, read from the shell every time the page is drawn, and choosing here changes that plugin.
The picker's layout and the videos' folder are this app's own settings, written through
`SetSettings`; the pause is the video plugin's own setting, written only when it is changed here.
The picker itself is `gui/picker.py`.
"""

from __future__ import annotations

import os

from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QRadioButton, QVBoxLayout, QWidget)

from cheatsheet import key_text
from client import Client
from widgets import SECTION_HINTS, Choice, Section, warning


#: What each of the two picker layouts looks like, said on the radio itself rather than in a
#: paragraph under both of them. Everything the two have in common -- the same list, the same
#: keys, the same way of setting a wallpaper -- is worth saying once, in the section's own line.
PICKER_LAYOUTS = {
    "pages": ("Pages", "over the desktop, the chosen one in the middle and the rest behind it"),
    "strip": ("Strip", "a column of thumbnails beside one big picture, in a panel"),
}


class WallpaperTab(QWidget):
    """Which kind of wallpaper the picker lists, and where the videos are.

    A plain widget and not a `SettingsPage`, because these live in this app's own config and go
    through `SetSettings` — the form engine is for the decoration and compositor groups.

    **What the picker lists is the exception, and it is not a setting at all.** It is the wallpaper
    plugin the activity in use is wearing, read from the shell every time this page is drawn, and
    choosing here changes that plugin. So the two sides cannot drift apart: there is no second
    value to keep in step, and changing it in *Desktop and Wallpaper* shows up here instead of
    being overwritten by something this app remembered.
    """

    def __init__(self, client: Client, parent=None):
        super().__init__(parent)
        self.c = client
        self._loading = False

        # Radio buttons and not tick boxes: it is one choice out of two, and they are exclusive
        # by being children of the same box.
        self.images = QRadioButton("Pictures — the wallpapers KDE knows about")
        self.videos = QRadioButton("Videos — played by Smart Video Wallpaper Reborn")
        self.images.setToolTip("The picker lists the pictures the desktop already knows about.")
        self.videos.setToolTip("The picker lists the videos in the folder below, and the plugin "
                               "plays the one you choose.")
        # `toggled` and not `clicked`, so arrowing through them with the keyboard applies what it
        # shows -- until now the dot moved and nothing happened, which is a control stating
        # something untrue. It takes the argument, because `toggled` fires on the one being
        # unticked as well, and unticking *Videos* would otherwise set the mode to pictures.
        self.images.toggled.connect(lambda on: on and self._set_mode("image"))
        self.videos.toggled.connect(lambda on: on and self._set_mode("video"))

        # A second box, so these two are exclusive among themselves and not among the four.
        self.pages = QRadioButton("{} — {}".format(*PICKER_LAYOUTS["pages"]))
        self.strip = QRadioButton("{} — {}".format(*PICKER_LAYOUTS["strip"]))
        self.pages.setToolTip("No panel of its own, and the border round it is the window "
                              "outline's.")
        self.strip.setToolTip("A panel wearing the decoration's own background and corner.")
        self.pages.toggled.connect(lambda on: on and self._set_layout("pages"))
        self.strip.toggled.connect(lambda on: on and self._set_layout("strip"))

        self.image_folder = QLineEdit()
        self.image_folder.setPlaceholderText("where the pictures are")
        self.image_folder.editingFinished.connect(self._image_folder_typed)
        self.image_choose = QPushButton("Choose…")
        self.image_choose.setToolTip("Pick the folder the pictures are in.")
        self.image_choose.clicked.connect(self._choose_image)
        image_folder_row = QHBoxLayout()
        image_folder_row.addWidget(QLabel("Pictures folder"))
        image_folder_row.addWidget(self.image_folder, 1)
        image_folder_row.addWidget(self.image_choose)

        self.folder = QLineEdit()
        self.folder.setPlaceholderText("where the videos are")
        self.folder.editingFinished.connect(self._folder_typed)
        self.choose = QPushButton("Choose…")
        self.choose.setToolTip("Pick the folder the videos are in.")
        self.choose.clicked.connect(self._choose)
        choose = self.choose
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Video folder"))
        folder_row.addWidget(self.folder, 1)
        folder_row.addWidget(choose)

        #: When the video plugin pauses the video: its own setting, drawn from the words the
        #: daemon sends and written back through it. Nothing here chooses it by itself.
        self.pause = Choice()
        self.pause.setToolTip(PAUSE_TIP)
        self.pause.currentIndexChanged.connect(self._set_pause)
        pause_row = QHBoxLayout()
        pause_row.addWidget(QLabel("Pause the video"))
        pause_row.addWidget(self.pause, 1)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.warning = warning()

        box = Section("Picker", SECTION_HINTS["Picker"] + " A wallpaper you choose reaches "
                      "every screen of the activity you are in, and no other.")
        form = QVBoxLayout(box)
        form.addWidget(self.images)
        form.addLayout(image_folder_row)
        form.addWidget(self.videos)
        form.addLayout(folder_row)
        form.addLayout(pause_row)

        looks = Section("Layout", SECTION_HINTS["Layout"] + " Both show the same wallpapers and "
                        "answer the same keys.")
        looks_form = QVBoxLayout(looks)
        looks_form.addWidget(self.pages)
        looks_form.addWidget(self.strip)

        layout = QVBoxLayout(self)
        layout.addWidget(self.warning)
        layout.addWidget(box)
        layout.addWidget(looks)
        layout.addWidget(self.summary)
        layout.addStretch()

    # ---------------------------------------------------------------- reading

    def reload(self) -> None:
        """Paint the tab from the shell's own answer. Nothing here writes.

        Every widget is blocked while it is painted. That is what makes the radios safe to drive
        from `toggled`: `setChecked` emits, and a tab that wrote on its way up is the one thing
        `scripts/simulate.sh` is built to catch.
        """
        self._loading = True
        data = self.c.wallpapers()
        mode = data.get("mode", "image")
        videos = bool(data.get("video_plugin"))
        for widget, checked in ((self.images, mode == "image"), (self.videos, mode == "video")):
            widget.blockSignals(True)
            widget.setChecked(checked)
            widget.blockSignals(False)
        self.videos.setEnabled(videos)
        if not videos:
            self.videos.setToolTip("Smart Video Wallpaper Reborn is not installed.")
        if not self.image_folder.hasFocus():
            self.image_folder.setText(data.get("image_dir", ""))
        self.image_folder.setEnabled(mode == "image")
        self.image_choose.setEnabled(mode == "image")
        # Not while somebody is typing in it: this runs on every change the daemon reports, and any
        # window opening used to wipe a folder half typed.
        if not self.folder.hasFocus():
            self.folder.setText(data.get("video_dir", ""))
        # The folder belongs to the videos and greys with them. It is kept either way -- switching
        # back to videos shows it again exactly as it was.
        self.folder.setEnabled(videos and mode == "video")
        self.choose.setEnabled(videos and mode == "video")
        # The plugin's own words, in its own order, and the one in force selected -- painted with
        # the signal blocked, so drawing the tab never writes the plugin's default into its file.
        modes = data.get("pause_modes") or {}
        self.pause.blockSignals(True)
        self.pause.clear()
        for value in sorted(modes, key=int):
            self.pause.addItem(modes[value], value)
        found = self.pause.findData(str(data.get("pause") or ""))
        self.pause.setCurrentIndex(found if found >= 0 else -1)
        self.pause.blockSignals(False)
        self.pause.setEnabled(videos and mode == "video" and found >= 0)
        chosen = data.get("layout", "pages")
        for widget, checked in ((self.pages, chosen != "strip"), (self.strip, chosen == "strip")):
            widget.blockSignals(True)
            widget.setChecked(checked)
            widget.blockSignals(False)

        # The activity's own name is a number the shell keeps for itself, and it meant nothing to
        # anybody reading it. How many screens is worth saying only when there is more than one.
        screens = int(data.get("desktops", 0) or 0)
        parts = [f"{len(data.get('entries') or [])} to choose from"]
        if screens > 1:
            parts.append(f"{screens} screens")
        parts.append(f"opens with {self._key()}")
        self.summary.setText(" · ".join(parts))

        trouble = [data.get("trouble")] if data.get("trouble") else []
        if not data.get("video_plugin"):
            trouble.append("Smart Video Wallpaper Reborn is not installed, so the picker can only "
                           "offer pictures.")
        if data.get("rotates"):
            trouble.append("the video plugin is set to change the wallpaper by itself, so a video "
                           "chosen here will not stay. Its own settings are where that is turned "
                           "off; this app does not touch it.")
        if data.get("video_plugin") and data.get("video_plugin_outdated"):
            trouble.append(f"Smart Video Wallpaper Reborn {data.get('video_plugin_version')} is "
                           f"installed. 2.15.0 fixes how it pauses and plays again on this "
                           f"Plasma; it comes from Get New Plugins in Desktop and Wallpaper, or "
                           f"from the plugin's own page.")
        self.warning.setText("\n".join(t for t in trouble if t))
        self.warning.setVisible(bool(trouble))
        self._loading = False

    def _key(self) -> str:
        """Which key opens the picker, asked rather than written down here.

        It is a row on the Shortcuts tab like any other and can be rebound there, so printing the
        default would be printing something that stopped being true the moment somebody did.
        """
        for action in self.c.shortcuts().get("actions") or []:
            if action.get("id") == "KyprXWallpaper":
                shown = action.get("show") or (action["keys"][0] if action["keys"] else [])
                return key_text(shown) if shown else "no key yet"
        return "no key yet — install.sh has not reloaded the compositor script"

    # ---------------------------------------------------------------- writing

    def _send(self, **fields) -> None:
        if self._loading:
            return
        current = self.c.settings().get("wallpaper") or {}
        self.c.set_settings(wallpaper={**current, **fields})

    def _set_mode(self, mode: str) -> None:
        """Not through `_send`: this is a change to the desktop, not to this app's own settings.

        The radio is put back from what the shell answers rather than left where the click left
        it — so a change the desktop refuses, or one it has nothing to switch to, shows as the
        radio going back rather than as a control quietly disagreeing with the screen.
        """
        if self._loading:
            return
        self.c.set_wallpaper_mode(mode)
        self.reload()

    def _set_layout(self, layout: str) -> None:
        if self._loading:
            return
        self._send(layout=layout)
        self.reload()

    def _set_pause(self) -> None:
        """Not through `_send` either: it is the video plugin's own setting, which the daemon asks
        the shell to change, and the menu is painted back from what the shell then answers."""
        if self._loading or self.pause.currentIndex() < 0:
            return
        self.c.set_video_pause(str(self.pause.currentData()))
        self.reload()

    def _image_folder_typed(self) -> None:
        typed = self.image_folder.text().strip()
        if self._loading or typed == (self.c.settings().get("wallpaper") or {}).get("image_dir"):
            return
        self._send(image_dir=typed)
        self.reload()

    def _choose_image(self) -> None:
        start = self.image_folder.text().strip() or os.path.expanduser("~")
        chosen = QFileDialog.getExistingDirectory(self, "Where the pictures are", start)
        if chosen:
            self.image_folder.setText(chosen)
            self._send(image_dir=chosen)
            self.reload()

    def _folder_typed(self) -> None:
        """`editingFinished` fires when the focus leaves as well as on Enter, so a folder nobody
        touched would be written back every time somebody clicked away from it."""
        typed = self.folder.text().strip()
        if self._loading or typed == (self.c.settings().get("wallpaper") or {}).get("video_dir"):
            return
        self._send(video_dir=typed)
        self.reload()

    def _choose(self) -> None:
        start = self.folder.text().strip() or os.path.expanduser("~")
        chosen = QFileDialog.getExistingDirectory(self, "Where the videos are", start)
        if chosen:
            self.folder.setText(chosen)
            self._send(video_dir=chosen)
            self.reload()


#: What pausing is for, with the cost of never doing it -- measured on this desk rather than
#: guessed: a 4K video at 60 frames a second, with the graphics card decoding it.
PAUSE_TIP = ("The video plugin's own setting: when it stops the video to save the machine the "
             "work. Playing all the time costs, measured with a 4K video at 60 frames a second, "
             "the graphics card's video decoder busy about 14 % of the time, the shell and the "
             "compositor about 8 % and 9 % of one processor core, and the graphics card about "
             "10 % -- more behind a maximised window, whose see-through blur is then redrawn "
             "every frame. With KyprX's see-through windows a paused video shows through them.")
