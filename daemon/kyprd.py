#!/usr/bin/env python3
"""KyprX's daemon.

The compositor script tells it a window appeared; it works out what that window should look like,
writes it, and asks for a reload. The interface talks to it over the same bus.

It is D-Bus activated — the first message from the compositor script wakes it, through a systemd
unit named in the activation file. The unit is not enabled and has no install target: systemd
never starts it by itself. The compositor script does, at login: its last line sends the inventory
of the windows already open (`Report("inventory", …)`) as soon as the compositor loads it, and
that message wakes the daemon. After that a new window or the interface wakes it if it is not
running, and it stays up for the rest of the session -- one was seen running for over two hours.
What the unit buys is a name — something to stop and restart, instead of hunting the process down
and killing it, which races the very activation it is trying to stop.

Two objects:

* `/Windows` — only the compositor script talks here, and by these names: `Report(reason, json)`
  when a window moves, and `ShowCheatsheet()`, `ShowWallpaper()` and `ShowSettings()` when one of
  their keys is pressed.
* `/Manager` — the interface's API, in `daemon/kyprd_api.py`.

On waiting: `windowAdded` arrives too early. The window's class may not be final yet and its
decoration may not exist. So the script's message is a trigger, not the truth: the daemon lets
things settle and then runs a one-shot inventory to get an accurate picture before deciding.

Run with `--dry-run` to exercise everything against real config without writing a byte.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

#: The folder this file really is in, every link resolved -- which is where Python looks for its
#: modules anyway. Not the folder of the link it was started through: that is `~/.local/bin` or
#: `/usr/bin`, and a `.py` file there named like one of these modules would have been imported
#: instead of it.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import effects  # noqa: E402
import logs  # noqa: E402
import migrate  # noqa: E402
import policy  # noqa: E402
import previews  # noqa: E402
import profiles  # noqa: E402
import reload as reloader  # noqa: E402
import rules  # noqa: E402
import snapshot  # noqa: E402
import writer  # noqa: E402
from kwin_config import DECORATION_GROUP, WINDOWS_GROUP  # noqa: E402
from kyprd_api import Manager  # noqa: E402
from kyprd_copies import CopiesPart  # noqa: E402
from kyprd_defaults import DefaultsPart  # noqa: E402
from kyprd_desk import DeskPart  # noqa: E402
from kyprd_folder import FolderPart  # noqa: E402
from kyprd_installation import InstallationPart  # noqa: E402
from kyprd_names import (CHEATSHEET_CLASS, CHEATSHEET_TITLE, OVERLAYS,  # noqa: E402
                         SCRIPT_PLUGIN, SERVICE, WINDOWS_IFACE)
from kyprd_offdesk import OffDeskPart  # noqa: E402
from kyprd_profiles import ProfilesPart  # noqa: E402
from kyprd_settingsfile import SettingsFilePart  # noqa: E402
from kyprd_shortcuts import ShortcutsPart  # noqa: E402
from kyprd_theme import ThemePart  # noqa: E402
from kyprd_transparency import TransparencyPart  # noqa: E402
from kyprd_wallpaper import WallpaperPart  # noqa: E402
from kyprd_windows import WindowsPart  # noqa: E402
from state import Config, State  # noqa: E402

#: The compositor's groups and plugin switches that a copy of the desk carries and puts back --
#: the five this app has controls in and the three plugins it turns on. See `daemon/snapshot.py`.
snapshot.configure(
    (DECORATION_GROUP, WINDOWS_GROUP, effects.BLUR_GROUP, effects.GEOMETRY_GROUP,
     effects.TILING_GROUP),
    tuple(f"{p}Enabled" for p in (effects.BLUR_PLUGIN, effects.GEOMETRY_PLUGIN,
                                  effects.TILING_PLUGIN)))

#: The main loop, for the one thing that ends it from inside: KyprX taken off this computer
#: (`InstallationPart.remove_kyprx`). Set by `main`.
_LOOP = None

#: Where the interface is, for the one thing the daemon starts rather than answers: the overlay.
#: The installed name first, so a normal installation uses the link on the path; the working tree
#: second, so an uninstalled checkout still works.
GUI_PATHS = [
    os.path.expanduser("~/.local/bin/kyprx"),
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "gui", "kyprx.py"),
]


def _gui_command() -> list[str] | None:
    """How to start the interface, as a command. None when it cannot be found at all."""
    found = shutil.which("kyprx")
    if found:
        return [found]
    for p in GUI_PATHS:
        if os.path.exists(p):
            return [sys.executable, os.path.abspath(p)]
    return None


# The daemon is one object, written in several files. Each `...Part` it inherits is a plain class in
# a `kyprd_<topic>.py` file beside this one, holding the methods of one topic: no __init__ and no
# D-Bus methods of its own. So the daemon's state is created below, in the order the comments
# explain -- all of it but `_folder_watches`, which `watch_the_folder` creates when this calls it --
# and the four methods the compositor script calls by name are declared on this class. A method of a
# part runs on this object like any other, reaching the rest of the daemon through `self`.
# `scripts/dry-run.sh` step 18 holds the parts to that shape, and refuses a name defined in two of
# them, or in one of them and here: Python would use the first it found and ignore the other.
class Daemon(ShortcutsPart, ProfilesPart, DefaultsPart, OffDeskPart, SettingsFilePart, CopiesPart,
             ThemePart, WallpaperPart, TransparencyPart, WindowsPart, DeskPart, FolderPart,
             InstallationPart, dbus.service.Object):
    def __init__(self, bus, name):
        #: Before the first file is read. An install made under this app's previous name keeps its
        #: state and settings under the old paths, and left the old name inside config files that
        #: belong to other programs; `migrate` brings both across. False means it could not move
        #: the remembered state, and then no window is touched this start — see `apply_defaults`.
        self.migrated = migrate.run(self.log, CHEATSHEET_CLASS, CHEATSHEET_TITLE)
        self.config = Config.load()
        #: A number of its own for a window this app never manages can only have come from a file
        #: edited by hand, and it is dropped on reading rather than obeyed -- `own_allowed` says
        #: what obeying it would do.
        refused = sorted(c for c in self.config.own_transparency if not self.own_allowed(c))
        if refused:
            self.log(f"ignoring an own transparency for {', '.join(refused)}: "
                     f"windows KyprX leaves alone")
            self.config.own_transparency = {c: n for c, n in self.config.own_transparency.items()
                                            if c not in refused}
        #: The same for the held ticks, and for the same reason: a window this app leaves alone
        #: cannot be ticked by it, so one on the list can only have come from a file edited by
        #: hand -- and a tick held for it would put it back on the desk the next time the strength
        #: came down. Kept in memory only, like the numbers above: the next save writes the
        #: pruned list.
        stray = [c for c in self.config.ticked_at_100 if not self.own_allowed(c)]
        if stray:
            self.log(f"ignoring a held tick for {', '.join(stray)}: windows KyprX leaves alone")
            self.config.ticked_at_100 = [c for c in self.config.ticked_at_100 if c not in stray]
        self.state = State()
        #: The looks kept under a name. Read once like the two above, written through the same
        #: door, and held to the same promise in dry run -- see `daemon/profiles.py`.
        self.profiles = profiles.Profiles()
        if self.profiles.unreadable:
            self.log(self.profiles.unreadable)
        #: Every window that is open, by the compositor's own handle for it.
        #:
        #: One dict, and keyed by the handle rather than by the window class, because the handle
        #: is the only thing that tells two windows of one application apart. The table is still
        #: one row per class — an override is per class, so two windows of one class have one
        #: answer between them — but that view is derived in `by_class()` when something needs it,
        #: not stored alongside this and kept in step with it. Two structures that have to agree
        #: are two structures that eventually do not.
        self.windows: dict[str, policy.Window] = {}
        self._settle = None
        self._settle_deadline = 0.0
        #: The wallpaper whose colour is still owed, and the timer that will go and get it. Only
        #: ever one of each: a second wallpaper replaces the first rather than queueing behind it.
        self._colour_wanted = ""
        self._colour_timer = None
        self._colour_deadline = 0.0
        self._deferred = None
        self._last_inventory = 0.0
        self._last_report = 0.0
        #: Each overlay's process, by the flag that starts it, so there is one to close and one
        #: to collect. See `_show_overlay`.
        self._overlays: dict[str, subprocess.Popen] = {}
        #: Settings windows this daemon started, kept apart from the overlay because they are
        #: handled the other way round: a second settings window is not closed from here, it asks
        #: the one already open to come forward and then quits on its own (`ClaimInterface`).
        #: What it still needs is collecting — the child is started in a session of its own, which
        #: does not reparent it, so this process remains its parent and has to reap it. Not
        #: hypothetical: the same omission left a defunct overlay sitting there for twenty-five
        #: minutes before anyone noticed.
        self._windows: list[subprocess.Popen] = []
        #: The bus connection of the settings window that is open, if one is. A connection and
        #: not a flag: see `Manager.ClaimInterface`.
        self.interface_owner: str | None = None
        #: The watch on that connection, which hands the desktop its shortcuts back if the window
        #: goes while a row is listening for keys. See `watch_interface`.
        self._interface_watch = None
        #: The wallpaper plugin watch: the monitor itself, the wait after an event, and the last
        #: answer -- which a fresh reading is compared against, so that nothing is announced twice
        #: and a file touched for somebody else's reasons announces nothing at all. Empty until the
        #: first reading, so the first event settles the value rather than reporting it as news.
        #: See `watch_the_desktop`.
        self._plugin_watch = None
        self._plugin_timer = None
        self._plugin_mode = ""
        #: The wallpaper whose colour is being worked out right now, on a thread of its own, the
        #: one asked for while that ran -- only the latest is kept -- and the stopwatch on the
        #: running one. See `warm_colour`.
        self._colour_running: tuple[str, str] | None = None
        self._colour_next: tuple[str, str] | None = None
        self._colour_trace = None
        #: A wallpaper change waiting for its colour to be known before it is applied: the
        #: target, its mode and the write that puts the picture up. See `_colour_due`.
        self._colour_owed: tuple[str, str, object] | None = None
        #: The write that puts the chosen wallpaper up, waiting for the deferred half to run it
        #: beside the colour. See `set_wallpaper`.
        self._wallpaper_change = None
        self._name = name
        #: The KyprX folder: the one timer that brings it and the desk into step, what the last
        #: pass found (for the Settings tab), what was last said about it (so a problem is said
        #: once), the agreement a dry run keeps in memory instead of on disk, and whether new
        #: windows are held back while something that arrived waits to be applied.
        self._folder_timer = None
        self._folder_state: dict = {"state": "in step"}
        self._folder_said = None
        self._folder_base_mem: dict | None = None
        self._folder_holding = False
        self._folder_waiting_since: float | None = None
        #: The decoration's leftover group was found and could not be removed, and that was said.
        #: See `clear_stray_exceptions`.
        self._stray_held = False
        #: The same for the decoration's list written in its long form: said once, in a dry run or
        #: when the write failed, rather than on every pass. See `compact_overrides`.
        self._compact_held = False
        #: What KyprX needs on this machine, as `requirements.check` last found it; None until
        #: somebody asks. See `InstallationPart.needs`.
        self._needs: list[dict] | None = None
        dbus.service.Object.__init__(self, bus, "/Windows")
        self.manager = Manager(bus, self)
        self.release_legacy_shortcut_claims()
        self.ensure_overlay_placement()
        #: Before the first inventory, and that order is the point: on a new machine with a copied
        #: folder, what the folder says about each window has to be on the desk before a window is
        #: treated as new and given the defaults. `apply_defaults` waits while it is held.
        self._folder_due()
        self.switch_the_script_on()
        self.note_the_version()
        self.request_inventory()
        self.watch_the_desktop()
        self.watch_the_folder()
        #: Every colour change looks through the file manager's previews before it starts, and the
        #: first look reads all of them -- up to a second, measured. Done now, beside the loop, so
        #: no change waits for it (`previews._seen`).
        previews.remember()
        GLib.timeout_add_seconds(5, self._reap_tick)

    # ------------------------------------------ stopping

    def quit_soon(self) -> None:
        """Leave the main loop half a second from now: time for the answer being sent to arrive.
        Only ever after KyprX was taken off this computer; nothing else stops this daemon but the
        session ending."""
        def stop():
            if _LOOP is not None:
                _LOOP.quit()
            return False
        GLib.timeout_add(500, stop)

    # ------------------------------------------ the compositor script

    def switch_the_script_on(self) -> None:
        """Switch KyprX's compositor script on, the first time KyprX runs on this desk.

        A package puts the script where the compositor finds it, and leaves it off: switching it
        on changes this user's desktop, and a package manager runs as root, for every user of the
        machine, at a moment nobody chose KyprX. So the first start here does it. This daemon only
        starts when something asks for it on the bus, and while the script is off the only thing
        that can ask is the settings window somebody has just opened -- that is the choice.
        `install.sh` switches the script on itself, and then there is nothing left to do here.

        Only a key that is not there at all is set. `false` is somebody's decision -- the
        desktop's own KWin Scripts page writes it -- and the Settings tab says the script is off
        rather than this undoing it on every start. The reconfigure is what loads a script that
        has become enabled (measured: see `daemon/reload.py`), and the script's first act once
        loaded is to report every open window here.
        """
        def build(tx):
            key = f"{SCRIPT_PLUGIN}Enabled"
            if tx.kwin.get(effects.PLUGINS_GROUP, key) is None:
                effects.set_plugin_enabled(tx.kwin, SCRIPT_PLUGIN, True)
                tx.reload_kwin = True
            for plugin in (effects.BLUR_PLUGIN, effects.TILING_PLUGIN, effects.GEOMETRY_PLUGIN):
                pkey = f"{plugin}Enabled"
                if tx.kwin.get(effects.PLUGINS_GROUP, pkey) is None:
                    effects.set_plugin_enabled(tx.kwin, plugin, True)
                    tx.reload_kwin = True

        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001 -- the Settings tab says the script is off instead
            self.log(f"could not switch KyprX's compositor script on: {logs.what(e)}",
                     trouble=True)
            return
        if diff and writer.dry_run():
            self.log("would switch KyprX's compositor script and required plugins on, the first start on this "
                     "desk:\n" + diff)
        elif diff:
            self.log("switched KyprX's compositor script and required plugins on: the first start on this desk")

    # ------------------------------------------ the overlays and the settings window

    def ensure_overlay_placement(self) -> None:
        """Put back the two things that keep every overlay floating and centred, on each start.

        Neither is something this app should own once and forget. A window rule is editable in
        the desktop's own rules dialog and deletable with one click; the tiler's float list is a
        comma-separated string anybody may tidy. Both are cheap to check and written only when
        they have actually gone, so the usual start writes nothing at all — which matters for the
        float list, whose every write costs a restart of the tiler and a re-tile of the screen.

        **One transaction for all the overlays, not one each**, and that is the whole reason this
        loops rather than being called twice. Writing the float list makes the tiling script
        re-read itself, and a script that has just started tiles the screen from scratch. Two
        transactions on the one start where both entries are missing would do that twice.
        """
        def build(tx):
            wrote_rule = wrote_float = False
            for _, window_class, title, description, opaque in OVERLAYS:
                # `owned` carries the opacity keys only for the overlay that asks for them, so a
                # rule this app did not pin the opacity of never has its opacity taken away.
                owned = (rules.PLACEMENT_KEYS + rules.OPACITY_KEYS if opaque
                         else rules.PLACEMENT_KEYS)
                wrote_rule |= rules.ensure(
                    tx.rules, description,
                    rules.overlay_placement(window_class, title, description, opaque),
                    owned)
                wrote_float |= effects.ensure_tiling_list_entry(
                    tx.kwin, effects.TILING_FLOAT_LIST, window_class)
                self._unmanage(tx, window_class, blurred=not opaque)
            # `or tx.reload_kwin`, because taking a rule off an overlay sets that flag itself and
            # assigning over it is how the compositor is left holding a decoration this has just
            # removed -- until something else reconfigures it, which may be the next login.
            tx.reload_kwin = tx.reload_kwin or wrote_rule or wrote_float
            tx.reload_tiling = wrote_float

        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001 — a missing overlay rule never stops the daemon
            self.log(f"could not check the overlay placement: {logs.what(e)}", trouble=True)
            return
        if diff and writer.dry_run():
            self.log("would put the overlays' placement back, or take off them something they "
                     "should never have had:\n" + diff)
        elif diff:
            self.log("the overlays' placement was put back, or something they should never have "
                     "had was taken off them")

    def _show_overlay(self, flag: str, what: str) -> str:
        """Start one of the overlays, and make sure there is only ever one of it.

        Two things this has to do that the obvious version does not.

        **Close the one already open.** An overlay normally closes itself when it loses focus,
        but pressing the key twice in quick succession beats that: the second press lands before
        the first window has been mapped and focused, so the first never loses a focus it never
        had. Without this, holding the key down leaves a process per repeat.

        **Reap the one that exited.** The child is started in its own session, which does not
        reparent it — this process is still its parent and still has to collect it. Nothing did,
        so every closed overlay left a defunct process sitting there until the next press. That
        was measured, not imagined: one had been there twenty-five minutes.
        """
        self._reap_overlay(flag, close_it=True)
        command = _gui_command()
        if command is None:
            self.log(f"cannot show {what}: the interface was not found")
            return "error: the interface was not found"
        self._overlays[flag] = subprocess.Popen(command + [flag],
                                                start_new_session=True,
                                                stdout=subprocess.DEVNULL,
                                                stderr=subprocess.DEVNULL)
        return "ok"

    @staticmethod
    def _unmanage(tx, window_class: str, blurred: bool = False) -> None:
        """Take the per-window treatment back off an overlay's class, and keep it off.

        An overlay is not an application window. `policy.AUTO_SKIP` says so, and anything this app
        ever wrote for one it wrote by mistake -- but the mistake is worth spelling out, because it
        was made twice and looked reasonable both times.

        **Asking for the title bar to be hidden is what puts one there.** These windows come up
        undecorated on Wayland; hiding the bar is the app's two-ended trick, and its first end is a
        rule telling the compositor to decorate the window. Do that to an overlay and three things
        follow, all of them measured on screen: the decoration draws its outline around the
        **window** rather than around what the window painted, so a mostly transparent picker ends
        up inside an orange rectangle; the decoration's panel shows through the transparent parts;
        and -- the one that survives even with the outline switched off -- **the theme's shadow is
        drawn around the whole window**, which on a picker whose window is far bigger than its
        pictures is a grey halo around nothing.

        **The blur is not the same answer for both overlays, and it follows the same field the
        rest of this table does.** The effect is usually set to blur everything *except* what is
        listed, so a window is kept out of it by being named there -- and `set_blur` puts it in or
        takes it out whichever way round the effect is set.

        A window pinned **fully opaque** is left out: blur is painted behind a window and seen
        through it, so on an opaque one it is work nobody sees. That is the picker, and the reason
        it is pinned opaque in the first place is that it shows pictures.

        The cheatsheet is the other case and gets the blur. Its window is exactly the card it
        paints -- fixed to its own `sizeHint`, with no margin around it -- so there is no expanse
        of transparent window for a blurred rectangle to appear behind, which is the trap this
        avoided when both were treated the same. The four rounded corners are the only transparent
        part, and the blur is rounded to the same radius: the Appearance tab writes the window's
        corner and the blur's corner from one control, for exactly this kind of mismatch.

        Written only when there is something to change, which on every ordinary start is nothing at
        all. The undoing of the rest is `set_titlebar(..., shown=True)`, which is already what
        "stop managing this window" means everywhere else in this app.
        """
        policy.set_titlebar(tx, policy.Window(window_class=window_class), True)
        policy.set_blur(tx, window_class, blurred)

    def show_cheatsheet(self) -> str:
        return self._show_overlay("--cheatsheet", "the cheatsheet")

    def show_wallpaper(self) -> str:
        return self._show_overlay("--wallpaper", "the wallpaper picker")

    def show_settings(self) -> str:
        """Open the settings window. One is enough, and the interface enforces that itself.

        Unlike the overlay, nothing is closed first: a second interface asks the one already open
        to come forward and then leaves, which is the behaviour somebody pressing the key twice
        actually wants.
        """
        command = _gui_command()
        if command is None:
            self.log("cannot open the settings window: the interface was not found")
            return "error: the interface was not found"
        self._reap_windows()
        self._windows.append(subprocess.Popen(command,
                                              start_new_session=True,
                                              stdout=subprocess.DEVNULL,
                                              stderr=subprocess.DEVNULL))
        return "ok"

    def _reap_windows(self) -> None:
        """Collect the settings windows that have closed. Never asks one to go."""
        for child in list(self._windows):
            if child.poll() is not None:
                child.wait()
                self._windows.remove(child)

    def _reap_overlay(self, flag: str, close_it: bool = False) -> None:
        """Collect one overlay's process, asking it to go first if it has not."""
        child = self._overlays.get(flag)
        if child is None:
            return
        if child.poll() is None:
            if not close_it:
                return
            child.terminate()
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=2)
        else:
            child.wait()
        self._overlays.pop(flag, None)

    # ------------------------------------------------------------ plumbing

    @staticmethod
    def log(msg: str, trouble: bool = False) -> None:
        """The daemon's one voice. `trouble` is for a failure: it is marked as an error in the
        journal (`daemon/logs.py`), so `journalctl --user -u kyprd -p err` lists failures alone."""
        prefix = "kyprd [dry run]" if writer.dry_run() else "kyprd"
        logs.emit(f"{prefix}: {msg}", trouble)

    def notify_failure(self, body: str) -> None:
        """Say on the desktop that something did not work, when notifications are on.

        In dry run the words go to the log instead of the screen. Two of the three calls used to
        reach the screen from a dry run, which is a real change to the desktop made by a run that
        promises none -- and one whose cause, in dry run, is usually the dry run itself.
        """
        if not self.config.notify:
            return
        if writer.dry_run():
            writer.report(f"would show a notification: {body}")
            return
        try:
            reloader.notify("KyprX", body)
        except Exception:  # noqa: BLE001 — a notification that fails is not worth a crash
            pass

    def _reap_tick(self) -> bool:
        """Collect whatever this daemon started and that has closed on its own. Costs a `waitpid`
        every few seconds."""
        for flag in list(self._overlays):
            self._reap_overlay(flag)
        self._reap_windows()
        return True

    # ------------------------------------------------------------ the compositor script

    @dbus.service.method(WINDOWS_IFACE, in_signature="", out_signature="s")
    def ShowCheatsheet(self):
        """The compositor script's end of the cheatsheet key.

        Here rather than on `/Manager` because this is the object the script talks to, and the
        script is the only caller. Nothing is written, so dry run has nothing to hold back — a
        window opening is not a change to anything.
        """
        try:
            return self.show_cheatsheet()
        except Exception as e:  # noqa: BLE001 — a D-Bus method that raises is a dead compositor
            # The caller is a compositor script. An exception crossing the bus there is not an
            # error message, it is a script that stops running — and this one is also the window
            # watcher. Nothing this method can hit is worth that.
            self.log(f"could not show the cheatsheet: {logs.what(e)}", trouble=True)
            return f"error: {e}"

    @dbus.service.method(WINDOWS_IFACE, in_signature="", out_signature="s")
    def ShowSettings(self):
        """The compositor script's end of the settings key. Opens a window; writes nothing."""
        try:
            return self.show_settings()
        except Exception as e:  # noqa: BLE001 — a D-Bus method that raises is a dead compositor
            self.log(f"could not open the settings window: {logs.what(e)}", trouble=True)
            return f"error: {e}"

    @dbus.service.method(WINDOWS_IFACE, in_signature="", out_signature="s")
    def ShowWallpaper(self):
        """The compositor script's end of the wallpaper key. Opens a window; writes nothing."""
        try:
            return self.show_wallpaper()
        except Exception as e:  # noqa: BLE001 — a D-Bus method that raises is a dead compositor
            self.log(f"could not open the wallpaper picker: {logs.what(e)}", trouble=True)
            return f"error: {e}"

    @dbus.service.method(WINDOWS_IFACE, in_signature="ss", out_signature="")
    def Report(self, reason, payload):
        try:
            reported = json.loads(str(payload))
        except json.JSONDecodeError:
            self.log("unreadable report", trouble=True)
            return

        reason = str(reason)
        self._last_report = time.monotonic()

        if reason == "gone":
            for entry in reported:
                uuid = str(entry.get("uuid", ""))
                if uuid:
                    self.windows.pop(uuid, None)
                else:
                    # A report old enough not to carry a handle cannot say *which* window went,
                    # so the class is the only honest reading.
                    window_class = str(entry.get("cls", ""))
                    for handle in [h for h, w in self.windows.items()
                                   if w.window_class == window_class]:
                        self.windows.pop(handle, None)
            self.manager.changed()
            return

        if reason == "inventory":
            # The one report that is a complete picture, so it is the one that may replace rather
            # than merge. Anything the compositor no longer lists is gone, whatever was believed.
            self.windows = {}

        for raw in reported:
            w = policy.Window.from_report(raw)
            if w.window_class and w.uuid:
                self.windows[w.uuid] = w

        if reason in ("appeared", "class"):
            # Too early to trust the picture; wait and ask for an accurate one.
            self._settle_then_look()
            return

        self.check_applied()
        self.apply_defaults()
        self.manager.changed()


def main() -> int:
    writer.set_dry_run("--dry-run" in sys.argv[1:])
    if writer.dry_run():
        # Before the daemon exists, so that the passes it makes as it comes up -- the one-off
        # renames, the overlays' placement -- are said in plain words like everything after them.
        writer.set_reporter(Daemon.log)
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()

    # Claim the name FIRST, and refuse to queue for it. This is the only thing standing between
    # one daemon and a hundred: `BusName` waits in line by default, so a second instance does not
    # fail — it sits there, alive, talking to the compositor. Asking about the current owner
    # instead races, because several activations can look at once and all see it free.
    try:
        name = dbus.service.BusName(SERVICE, bus, do_not_queue=True)
    except dbus.exceptions.NameExistsException:
        if writer.dry_run():
            # Not the same situation at all, and it must not read like it. Someone asking for a
            # dry run is asking for a guarantee; standing down leaves the running daemon writing
            # for real while the request looks like it was honoured. Measured the hard way: an
            # interface left open re-activates the real daemon in the gap after it is killed, and
            # then every "dry run" change lands on disk.
            print("kyprd: REFUSING to start in dry run — another daemon holds the name and "
                  "it is writing for real.\n"
                  "           Close the interface first, then stop the daemon, then start this.",
                  file=sys.stderr)
            return 1
        # Exit cleanly: a failure here would have the bus try to start yet another one.
        print("kyprd: another daemon already holds the name — leaving it to it")
        return 0

    global _LOOP
    Daemon(bus, name)
    Daemon.log("up" + (" — dry run, nothing will be written" if writer.dry_run() else ""))
    _LOOP = GLib.MainLoop()
    _LOOP.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
