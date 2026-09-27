"""The interface's side of the conversation with the daemon.

QtDBus rather than the daemon's own bindings, because it folds into Qt's event loop: the daemon's
`Changed` signal arrives as a Qt signal, with no parallel loop and no thread.

Everything travels as JSON in a string. That is deliberate — the window table grows a field every
time there is a new idea, and a typed D-Bus signature would mean changing both ends each time.
"""

from __future__ import annotations

import json

from PySide6.QtCore import SLOT, QObject, Signal, Slot
from PySide6.QtDBus import (QDBusConnection, QDBusInterface, QDBusMessage,
                            QDBusServiceWatcher)

SERVICE = "org.cyberbessa.KyprX"
IFACE = "org.cyberbessa.KyprX.Manager"
PATH = "/Manager"


class Client(QObject):
    changed = Signal()
    #: A wallpaper's colour is known now -- the daemon's `ColourReady`, with the wallpaper's name.
    colour_ready = Signal(str)
    failed = Signal(str)
    #: The daemon answering was replaced, and this is what the window now has in front of it:
    #: `dry` whether the one answering is in dry run, `held` whether this window has stopped
    #: sending anything because the dry run it was opened on is over.
    mode_changed = Signal(bool, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bus = QDBusConnection.sessionBus()
        self.iface = QDBusInterface(SERVICE, PATH, IFACE, self.bus)
        #: Whether the daemon answering is in dry run, asked once and then again every time the
        #: daemon is replaced -- never assumed to stay what it was. See `reclaim_on_restart`.
        self._dry: bool | None = None
        #: Set when this window was opened on a dry run and the daemon doing it went away. From
        #: then on nothing is sent: the next call would start the real daemon by activation, and
        #: every change after it would be written for real under a band that said nothing is.
        self.held = False
        #: Set once KyprX has been taken off this computer. From then on nothing is sent, not even
        #: a goodbye: the daemon stops a moment after answering, any call after that would start it
        #: again by activation, and a daemon's first start switches the compositor script back on.
        self.gone = False
        # The slot goes in Qt's SLOT() spelling. The documented signature asks for bytes, but only
        # the string SLOT() returns is accepted — bytes raise ValueError.
        self.bus.connect(SERVICE, PATH, IFACE, "Changed", self, SLOT("_onChanged()"))
        self.bus.connect(SERVICE, PATH, IFACE, "ColourReady", self,
                         SLOT("_onColourReady(QString)"))

    # ------------------------------------------------------------ plumbing

    def available(self) -> bool:
        """Ask the daemon something and see whether it answers.

        Not `isValid()`: that reports false here even when every call goes through, and a real
        call has the side effect that matters — it activates the daemon if it is not running.
        """
        reply = self.iface.call("DryRun")
        if reply.errorName() == "org.freedesktop.DBus.Error.ServiceUnknown":
            # KyprX installed during this session. The session bus here, dbus-broker, reads its
            # activation files when it starts and when asked to, and never watches their folders
            # (its manual, dbus-broker-launch(1)), so until a logout the name is unknown to it and
            # nothing can start the daemon. Asking it to read them again is what a program that
            # adds one is expected to do; then the call is made once more.
            self.bus.interface().call("ReloadConfig")
            reply = self.iface.call("DryRun")
        return not reply.errorName()

    @Slot()
    def _onChanged(self):
        self.changed.emit()

    @Slot(str)
    def _onColourReady(self, target):
        self.colour_ready.emit(str(target))

    def _reply(self, method: str, *args) -> tuple:
        """Call the daemon, and say both what came back and whether anything did.

        Two separate questions, and collapsing them is what made this wrong twice over. Failure is
        the bus saying so — not a reply with nothing in it, because a method that returns nothing
        sends a perfectly good empty reply, and reading that as failure made every clean quit
        report "no answer from the daemon" from the one method whose job is to say goodbye. But a
        caller that only gets the value cannot tell an empty success from a real failure either,
        which is why `delivered` is returned beside it.
        """
        if self.gone:
            return None, False
        if self.held:
            self.failed.emit("The dry run has ended, so this window sends nothing. Close it and "
                             "open it again to go on.")
            return None, False
        reply = self.iface.call(method, *args)
        if reply.type() == QDBusMessage.MessageType.ErrorMessage:
            self.failed.emit(f"{method}: {reply.errorMessage() or reply.errorName()}")
            return None, False
        arguments = reply.arguments()
        return (arguments[0] if arguments else None), True

    def _call(self, method: str, *args):
        value, _ = self._reply(method, *args)
        return value

    def _json(self, method: str, *args):
        raw = self._call(method, *args)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            self.failed.emit(f"{method}: unreadable answer")
            return None

    def _ok(self, method: str, *args) -> bool:
        """Did the daemon take the change?

        Two ways to answer no, and both have to count: the bus never delivered the call, or the
        daemon answered with a message beginning "error". Reading only the second meant a daemon
        that had died reported every write as having worked.
        """
        value, delivered = self._reply(method, *args)
        if not delivered:
            return False
        if isinstance(value, str) and value.startswith("error"):
            self.failed.emit(value)
            return False
        return True

    # ------------------------------------------------------------ API

    def dry_run(self) -> bool:
        """Whether the daemon answering is in dry run. Asked once and remembered; the answer is
        asked again only when the daemon is replaced, which is the one way it can change."""
        if self._dry is None:
            self._dry = bool(self._call("DryRun"))
        return self._dry

    def windows(self) -> list[dict]:
        return self._json("Windows") or []

    def settings(self) -> dict:
        return self._json("Settings") or {}

    def set_settings(self, **fields) -> bool:
        return self._ok("SetSettings", json.dumps(fields))

    def set_switch(self, window_class: str, name: str, value: bool) -> bool:
        return self._ok("SetSwitch", window_class, name, value)

    def set_switches(self, data: dict) -> bool:
        """`{class: {switch: bool}}` — one call, one transaction, one compositor reload."""
        return self._ok("SetSwitches", json.dumps(data))

    def set_window_lists(self, data: dict) -> bool:
        """`{"float": {class: bool}, "animate": {class: bool}}` — one call for a whole batch."""
        return self._ok("SetWindowLists", json.dumps(data))

    def wallpapers(self) -> dict:
        return self._json("Wallpapers") or {}

    def set_wallpaper_mode(self, mode: str) -> bool:
        """Put that kind of wallpaper on the activity in use. What the picker lists follows."""
        return self._ok("SetWallpaperMode", json.dumps({"mode": mode}))

    def prepare_colour(self, target: str) -> bool:
        """Ask for this wallpaper's colour to be worked out now. Does nothing visible, and makes
        choosing it later a file read rather than a run of ffmpeg.

        Sent and not waited for. The reply is "ok" and nobody reads it, and waiting for it was
        measured to be the picker's stutter: a call that blocks until the daemon answers sits
        behind whatever the daemon is doing, and it was doing the previous wallpaper's ffmpeg --
        a tenth of a second for a picture, half a second for a video, once per stop.
        """
        # `asyncCallWithArgumentList`, not `asyncCall`: in this PySide the latter takes the method
        # name alone and raises on an argument -- found on screen, with the picker's settle raising
        # on every stop while the simulation's picker closed too soon to reach it.
        self.iface.asyncCallWithArgumentList("PrepareColour", [json.dumps({"target": target})])
        return True

    def set_video_pause(self, value: str) -> bool:
        """When the video wallpaper pauses: the video plugin's own setting, `"0"` to `"3"`."""
        return self._ok("SetVideoPause", json.dumps({"pause": value}))

    def set_wallpaper(self, target: str) -> bool:
        """Put this wallpaper on every screen of the activity in use. Nothing else is touched."""
        return self._ok("SetWallpaper", json.dumps({"target": target}))

    def theme(self) -> dict:
        return self._json("Theme") or {}

    def set_theme(self, data: dict) -> bool:
        """`{"mode", "preset", "accent", "tint"}` — the desktop's colours, windows and panel."""
        return self._ok("SetTheme", json.dumps(data))

    def groups(self) -> dict:
        return self._json("Groups") or {}

    def set_groups(self, data: dict) -> bool:
        return self._ok("SetGroups", json.dumps(data))

    def shortcuts(self) -> dict:
        return self._json("Shortcuts") or {"actions": [], "cheatsheet": []}

    def set_shortcut(self, action: str, keys: list[int],
                     component: str = "kwin") -> bool:
        return self._ok("SetShortcutIn", component, action, keys)

    def shortcut_holders(self, component: str, action: str, keys: list[int]) -> list | None:
        """The other actions that hold these keys now, or None when the daemon did not say."""
        raw = self._call("ShortcutHolders", json.dumps(
            {"component": component, "action": action, "keys": keys}))
        if not isinstance(raw, str) or raw.startswith("error"):
            if isinstance(raw, str):
                self.failed.emit(raw)
            return None
        try:
            found = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return found if isinstance(found, list) else None

    def rebind_shortcut(self, component: str, action: str, old: list[int], new: list[int],
                        take: bool = False) -> bool:
        """`new` in place of `old`, by value; with `take`, taken from its holder first."""
        return self._ok("RebindShortcut", json.dumps(
            {"component": component, "action": action, "old": old, "new": new, "take": take}))

    def set_cheatsheet_key(self, action_key: str, keys: list[int]) -> bool:
        """Which of an action's combinations the card shows. Rebinds nothing."""
        return self._ok("SetCheatsheetKey", action_key, keys)

    def restore_defaults(self) -> str:
        """Put KyprX's defaults back, after a copy of the desk. "" when all of it went in, the
        daemon's sentence otherwise -- "partial: …" names what did not."""
        return self._partial("RestoreDefaults")

    def folder(self) -> dict:
        """Where the KyprX folder is, and how it stands with the desk."""
        return self._json("Folder") or {}

    def sync_folder(self) -> dict:
        """Bring the folder and the desk into step now, and say how they stand."""
        return self._json("SyncFolder") or {}

    def take_off_preview(self) -> str:
        """What taking KyprX off this desk would change, in plain words. Writes nothing."""
        return self._call("TakeOffPreview") or ""

    def take_off(self) -> str:
        """Take KyprX off this desk. "" when done, the daemon's sentence otherwise."""
        return self._partial("TakeOff")

    def remove_preview(self, revert: bool, keep_folder: bool) -> str:
        """What taking KyprX off this computer would do, for the two answers. Writes nothing."""
        return self._call("RemovePreview", json.dumps({"revert": revert,
                                                       "keep_folder": keep_folder})) or ""

    def remove(self, revert: bool, keep_folder: bool) -> dict:
        """Take KyprX off this computer. The daemon's answer: `answer`, and `done`, `kept`,
        `command` and `dry_run` when it went through. Unless in a dry run, nothing is sent after
        it (`gone`)."""
        answer = self._json("Remove", json.dumps({"revert": revert,
                                                  "keep_folder": keep_folder})) or {}
        if answer.get("answer") == "ok" and not answer.get("dry_run"):
            self.gone = True
        return answer

    def put_back(self) -> str:
        """Put the setup back after KyprX was taken off. "" when all of it came back."""
        return self._partial("PutBack")

    def restore_preview(self) -> str:
        """What *Restore defaults* would change, in plain words. Writes nothing."""
        return self._call("RestorePreview") or ""

    def snapshots(self) -> dict:
        """Every copy of the desk, newest first, and the folder they live in."""
        return self._json("Snapshots") or {}

    def go_back_preview(self, name: str) -> str:
        """What going back to this copy would change, or "error: …"."""
        return self._call("GoBackPreview", name) or ""

    def go_back(self, name: str) -> str:
        """Put a copy of the desk back. "" when all of it came back, the sentence otherwise."""
        return self._partial("GoBack", name)

    def _partial(self, method: str, *args) -> str:
        """`_answer`, for the calls that can half succeed: "partial: …" is neither the change
        refused nor the change made, and the caller has to say which parts."""
        value, delivered = self._reply(method, *args)
        if not delivered:
            return f"{method}: no answer from the daemon"
        if isinstance(value, str) and value.startswith(("error", "partial")):
            if value.startswith("error"):
                self.failed.emit(value)
            return value
        return ""

    def diagnostics(self) -> dict:
        return self._json("Diagnostics") or {}

    def requirements(self, refresh: bool = False) -> list:
        """The five projects KyprX is built on, each as it stands here. `refresh` looks again."""
        return self._json("Requirements", refresh) or []

    def remove_stray_exceptions(self) -> bool:
        """Take the decoration's leftover [Exceptions] group away, after a copy of the desk."""
        return self._ok("RemoveStrayExceptions")

    def normalize(self) -> list:
        return self._json("Normalize") or []

    def export_settings(self) -> str:
        return self._call("ExportSettings") or ""

    def import_settings(self, text: str) -> bool:
        return self._ok("ImportSettings", text)

    def _answer(self, method: str, *args) -> str:
        """The daemon's refusal as a sentence, or "" when it took the change.

        `_ok` for a caller with a line of its own to put the sentence on. The footer still hears
        about it through `failed`, as it does for every other call.
        """
        value, delivered = self._reply(method, *args)
        if not delivered:
            return f"{method}: no answer from the daemon"
        if isinstance(value, str) and value.startswith("error"):
            self.failed.emit(value)
            return value.removeprefix("error:").strip() or value
        return ""

    def set_own_transparency(self, window_class: str, strength: int | None) -> str:
        """Give one window class a transparency of its own, or take it away with None. It
        reaches the window at once. "" when done, otherwise why not."""
        return self._answer("SetOwnTransparency",
                            json.dumps({"class": window_class, "strength": strength}))

    def profiles(self) -> dict:
        """Every profile kept, and the look the desktop is wearing."""
        return self._json("Profiles") or {}

    def save_profile(self, name: str, replace: bool = False) -> str:
        """Keep the look on the desktop under this name. "" when done, else why not."""
        return self._answer("SaveProfile", json.dumps({"name": name, "replace": replace}))

    def load_profile(self, name: str) -> str:
        """Put that profile on the desktop. Blocks for as long as the desktop's tools take."""
        return self._answer("LoadProfile", json.dumps({"name": name}))

    def rename_profile(self, name: str, to: str) -> str:
        return self._answer("RenameProfile", json.dumps({"name": name, "to": to}))

    def delete_profile(self, name: str) -> str:
        return self._answer("DeleteProfile", json.dumps({"name": name}))

    def refresh(self) -> None:
        self._call("Refresh")

    def claim_interface(self) -> bool:
        """Become *the* open settings window. False means one is already open and was raised.

        Deliberately not through `_ok`: the only answer that should stop a window opening is the
        daemon saying another one is already there. A daemon that cannot be reached is a reason to
        open anyway — refusing would leave somebody with no window at all over a fault that has
        nothing to do with them.
        """
        value, delivered = self._reply("ClaimInterface")
        return bool(value) if delivered and value is not None else True

    def release_interface(self) -> None:
        self._call("ReleaseInterface")

    def on_raise(self, receiver, slot) -> None:
        """Hear the daemon asking this window to come forward."""
        self.bus.connect(SERVICE, PATH, IFACE, "Raise", receiver, slot)

    def reclaim_on_restart(self) -> None:
        """Claim the interface again whenever the daemon is replaced.

        The claim lives in the daemon, so a daemon that restarts forgets it — and then the next
        interface to start is told it may open, beside the one that is already there. The daemon
        cannot fix that on its own: it has no memory of who was holding the claim before it
        existed. The window that is still open is the only thing that knows, so it says so again.
        """
        self._watcher = QDBusServiceWatcher(
            SERVICE, self.bus, QDBusServiceWatcher.WatchModeFlag.WatchForOwnerChange, self)
        self._watcher.serviceOwnerChanged.connect(self._owner_changed)

    def _owner_changed(self, _name: str, _old: str, new: str) -> None:
        """The daemon was replaced. Claim the window again, and ask again whether it is a dry run.

        **The second half is the correction.** Whether it is a dry run used to be asked once, when
        the window was built. A dry-run daemon that goes away -- its terminal closed is enough --
        is replaced by the real one the moment anything calls, because activation starts the
        unit, and the unit has no dry run. The window went on saying "Nothing is written" over a
        daemon writing every change for real.

        So a window opened on a dry run stops sending the moment its daemon leaves the bus, and
        stays stopped unless what comes back is a dry run again. Asking the one that came back is
        a call to a name that has an owner, which starts nothing.
        """
        if self.gone:
            return
        was_dry = bool(self._dry)
        if not new:
            if was_dry:
                self.held = True
                self.mode_changed.emit(True, True)
            return
        self.held = False
        reply = self.iface.call("DryRun")
        now_dry = (reply.type() != QDBusMessage.MessageType.ErrorMessage
                   and bool(reply.arguments() and reply.arguments()[0]))
        self._dry = now_dry
        if was_dry and not now_dry:
            self.held = True
            self.mode_changed.emit(False, True)
            return
        self.claim_interface()
        self.mode_changed.emit(now_dry, False)
