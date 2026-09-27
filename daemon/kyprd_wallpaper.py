"""The wallpaper: what the picker lists, changing it, pausing a video, and the colour it hands the
desktop.

Nothing here opens the shell's config: `daemon/wallpaper.py` asks the shell to read and write it,
and which plugin draws the desktop is read from there every time rather than kept. While the
wallpaper hands its colour to the desktop, a change of wallpaper is answered at once and finished a
moment later, picture and colour together, so the picker does not wait for either: the colour is
worked out on a thread of its own, ahead of time when the picker asks for it (`warm_colour`), and
put on the desktop through `set_theme`. The watch on the shell's config and on the activity in use
keeps an open window from showing something a second out of date, and brings the KyprX folder into
step when the plugin changed.

The daemon's state it reads or writes, all of it created in `Daemon.__init__`: `config`, `manager`,
`_colour_deadline`, `_colour_next`, `_colour_owed`, `_colour_running`, `_colour_timer`,
`_colour_trace`, `_colour_wanted`, `_plugin_mode`, `_plugin_timer`, `_plugin_watch`,
`_wallpaper_change`.
"""

from __future__ import annotations

import os
import threading
import time

import dbus
from gi.repository import Gio, GLib

import clock
import logs
import theme
import wallcolour
import wallpaper
import writer
from state import WALLPAPER_MODES
from wallpaper import VIDEO_PLUGIN_FIXED


#: How long a wallpaper change waits before the desktop is recoloured after it, in milliseconds.
#:
#: The whole of this is so that the picker's call can be answered at once instead of at the end.
#: It used to be answered last, and the overlay stayed on screen for every second of it: measured
#: at 1.3 s for a picture and **up to 5 s for a video**, which is what "the picker freezes" was.
#:
#: Short, because nobody is waiting on it and it only has to outlive a double press. Long enough
#: that arrowing through a folder and pressing Enter three times costs one recolour rather than
#: three -- the same reasoning as the inventory's settle in `daemon/kyprd_windows.py`, and the
#: same three mechanics: restart on each request, a deadline so a stream cannot postpone for ever,
#: and the timer handle as the flag that says one is armed.
COLOUR_SETTLE_MS = 250

#: The furthest a stream of wallpaper changes may push that out, in milliseconds.
MAX_COLOUR_SETTLE_MS = 1500

#: How long the shell's config has to stand still before the wallpaper plugin is read again, in
#: milliseconds. The shell rewrites that file for reasons of its own -- one was seen seconds after
#: an activity switch -- and the video plugin writes its playback position into it when the shell
#: quits; none of that is this app's business, and a burst of it is read once.
PLUGIN_SETTLE_MS = 300


class WallpaperPart:
    """The wallpaper, and the colour it gives."""

    # ------------------------------------------------------------ the wallpaper

    def wallpapers(self) -> dict:
        """Everything the picker draws itself from, and everything the Wallpaper tab reports.

        A read from end to end, so it happens in dry run too — asking the shell what it is showing
        is a call into it, not a change to it, which is the same line the window inventory is on.

        Trouble is reported as a sentence rather than raised. There are three ordinary ways for
        this to have nothing to show — no shell on the bus, a plugin that is not installed, a
        folder that is not mounted — and a picker that says which one is far more use than one
        that fails to open.
        """
        paper = self.config.wallpaper or {}
        #: Not a setting of this app's, and it stopped being one: which kind of wallpaper the
        #: picker lists is whichever plugin the activity in use is wearing, read back every time.
        #: See `wallpaper.mode_of`. The value below is only ever the answer when there is no shell
        #: on the bus to ask.
        mode = WALLPAPER_MODES[0]
        version = wallpaper.plugin_version(wallpaper.VIDEO_PLUGIN)
        out = {
            "mode": mode,
            "layout": paper.get("layout", "pages"),
            "video_plugin": wallpaper.plugin_installed(wallpaper.VIDEO_PLUGIN),
            "video_plugin_version": version,
            "video_plugin_outdated": wallpaper.version_below(version, VIDEO_PLUGIN_FIXED),
            #: When the video plugin pauses, as its own number, and the words for each number. The
            #: Wallpaper tab draws its menu from these rather than from a copy of its own.
            "pause": "",
            "pause_modes": dict(wallpaper.PAUSE_MODES),
            "video_dir": paper.get("video_dir", ""),
            "video_dir_present": False,
            "rotates": False,
            "activity": "",
            "desktops": 0,
            "current": "",
            "entries": [],
            "trouble": "",
        }
        try:
            state = wallpaper.snapshot()
        except wallpaper.WallpaperError as e:
            out["trouble"] = str(e)
            return out
        mode = wallpaper.mode_of(state) or mode
        out["mode"] = mode
        video_dir = out["video_dir"] or wallpaper.default_video_dir(state)
        out.update(
            activity=state.get("activity", ""),
            desktops=len(state.get("desktops") or []),
            pause=wallpaper.pause_mode(state) if out["video_plugin"] else "",
            video_dir=video_dir,
            video_dir_present=bool(video_dir) and os.path.isdir(video_dir),
            rotates=wallpaper.rotates(state),
            current=wallpaper.current_target(mode, state),
            entries=wallpaper.catalogue(mode, video_dir, state),
        )
        if mode == "video" and not out["video_plugin"]:
            out["trouble"] = ("the Smart Video Wallpaper Reborn plugin is not installed, "
                              "so there is nothing to play a video with")
        elif mode == "video" and not out["video_dir_present"]:
            out["trouble"] = f"the video folder is not there right now: {video_dir or '(none)'}"
        return out

    def set_wallpaper_mode(self, mode: str) -> str:
        """Put this kind of wallpaper on the activity in use.

        The other half of one arrangement rather than a setting of its own: the picker lists what
        the desktop is wearing, so choosing what it lists **is** choosing what the desktop wears.
        Each plugin keeps its own config under its own group, so switching brings back whatever
        that plugin last had -- which is what the desktop's own dialog does.
        """
        if mode not in WALLPAPER_MODES:
            return f"error: {mode or '(none)'} is not a kind of wallpaper"
        if mode == "video" and not wallpaper.plugin_installed(wallpaper.VIDEO_PLUGIN):
            return ("error: the Smart Video Wallpaper Reborn plugin is not installed, "
                    "so there is nothing to play a video with")
        try:
            state = wallpaper.snapshot()
        except wallpaper.WallpaperError as e:
            self.log(f"could not ask the shell what it is showing: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        change = wallpaper.plugin_plan(mode, state)
        if change is None:
            return "ok"        # already that, so nothing to do and nothing for a watch to echo

        def build(tx):
            tx.session_write(*change)

        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001 — the interface says what went wrong, and stays up
            self.log(f"failed on the wallpaper plugin: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        if writer.dry_run() and diff:
            self.log("would have written:\n" + diff)
        else:
            # What the watch will read in 300 ms is this app's own write, and it is not news:
            # without this the same change was announced twice, once here and once by the watch,
            # and every open interface redrew itself twice for it.
            self._plugin_mode = mode
        return "ok"

    def set_video_pause(self, value: str) -> str:
        """Make the video wallpaper pause the way the Wallpaper tab asks, on the activity in use.

        The plugin's own setting, `PauseMode`, and nothing else: this app never chooses it by
        itself. The owner was shown what playing all the time costs -- measured on this desk with a
        4K video at 60 frames a second, the graphics card's video decoder busy 14 % of the time,
        the shell and the compositor near 8 % and 9 % of one core, the GPU near 10 % -- and chose
        a control over a default. Asking for what is already so writes nothing.
        """
        value = str(value or "")
        if value not in wallpaper.PAUSE_MODES:
            return f"error: {value or '(none)'} is not one of the video plugin's pause settings"
        if not wallpaper.plugin_installed(wallpaper.VIDEO_PLUGIN):
            return ("error: the Smart Video Wallpaper Reborn plugin is not installed, "
                    "so there is no video to pause")
        try:
            state = wallpaper.snapshot()
        except wallpaper.WallpaperError as e:
            self.log(f"could not ask the shell what it is showing: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        change = wallpaper.pause_plan(value, state)
        if change is None:
            return "ok"

        def build(tx):
            tx.session_write(*change)

        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001 — the interface says what went wrong, and stays up
            self.log(f"failed on the video's pause setting: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        if writer.dry_run() and diff:
            self.log("would have written:\n" + diff)
        return "ok"

    def watch_the_desktop(self) -> None:
        """Notice a wallpaper plugin changed by somebody other than this app.

        Two events, neither of them a poll. The shell's own config file, because *Desktop and
        Wallpaper* is where somebody would change this; and the activity in use, because the
        plugin is a choice **per activity** and switching activity changes the answer without
        changing a single file.

        The guarantee is not here. The daemon is started by the desktop and not at login, so this
        cannot catch what happened before it came up -- what makes the two sides agree is that the
        value is derived on every read. This only saves a window that is already open from showing
        something a second out of date.

        The file is watched with a wait, because the shell rewrites it for reasons of its own --
        seconds after an activity switch, among others -- and a burst of those would otherwise wake
        this once per write for a value that has not moved. And nothing is announced unless the answer is
        actually different -- which, with the value derived rather than stored, is also the reason
        a change made here cannot come back round as a change of somebody else's.
        """
        try:
            appletsrc = Gio.File.new_for_path(
                os.path.expanduser(wallpaper.APPLETSRC))
            self._plugin_watch = appletsrc.monitor_file(Gio.FileMonitorFlags.NONE, None)
            self._plugin_watch.connect("changed", lambda *_: self._plugin_maybe_moved())
        except Exception as e:  # noqa: BLE001 — a failed watch never stops the daemon
            self.log(f"could not watch the shell's config: {logs.what(e)}", trouble=True)
        try:
            dbus.SessionBus().add_signal_receiver(
                lambda *_: self._plugin_maybe_moved(),
                signal_name=wallpaper.ACTIVITY_CHANGED,
                dbus_interface=wallpaper.ACTIVITIES_IFACE)
        except dbus.DBusException as e:
            self.log(f"could not listen for the activity changing: {logs.what(e)}", trouble=True)

    def _plugin_maybe_moved(self) -> None:
        # The wallpaper is a part of the KyprX folder too.
        self.folder_soon()
        if self._plugin_timer is not None:
            GLib.source_remove(self._plugin_timer)
        self._plugin_timer = GLib.timeout_add(PLUGIN_SETTLE_MS, self._plugin_settled)

    def _plugin_settled(self) -> bool:
        self._plugin_timer = None
        try:
            now = wallpaper.mode_of(wallpaper.snapshot())
        except wallpaper.WallpaperError:
            return False          # the shell will be asked again the next time anything reads
        if now and self._plugin_mode and now != self._plugin_mode:
            self.log(f"the desktop is showing {now} wallpapers now")
            self.manager.changed()
        self._plugin_mode = now
        return False

    def set_wallpaper(self, target: str) -> str:
        """Put this wallpaper on every screen of the activity in use, and on no other.

        The read happens **before** the transaction and not inside it, which is the same split
        `set_switches` makes and for a second reason besides: it is what lets a wallpaper that is
        already on screen produce no transaction at all, and so no change to report.
        """
        if not target:
            return "error: no wallpaper was named"
        try:
            state = wallpaper.snapshot()
        except wallpaper.WallpaperError as e:
            self.log(f"could not ask the shell what it is showing: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        #: What this wallpaper **is**, rather than what the desktop is wearing. Both were wrong
        #: before in opposite directions: a mode kept in this app's settings could disagree with
        #: the desktop, and the desktop's own answer can have moved on between the picker opening
        #: and Enter being pressed -- the plugin is a choice per activity, and an activity switched
        #: in between had this writing an image into the video plugin's list.
        mode = wallpaper.mode_for(target)
        if mode == "video" and not wallpaper.plugin_installed(wallpaper.VIDEO_PLUGIN):
            return ("error: the Smart Video Wallpaper Reborn plugin is not installed, "
                    "so there is nothing to play the video with")
        change = wallpaper.plan(mode, target, state)
        # **The picture travels with the colour, and that is deliberate.** Everything above is a
        # read: what the shell is showing, and whether this wallpaper can be shown at all. The
        # write itself is handed to the deferred half along with the colour, so the two land
        # together rather than a picture first and a frozen screen half a second later.
        #
        # Measured, and it is what this is for: recolouring stops the compositor for about 1.3 s,
        # and in that time nothing on the screen moves -- not the pointer, and not a video that has
        # just started playing. Written here, the video played for about 0.6 s, stopped dead, and
        # came back. Written there, the screen holds still and what comes out of it is a wallpaper
        # already settled. The price, measured too: the picture arrives about two seconds after
        # the key, most of it inside the pause.
        #
        # The colour is asked for **whether or not the picture itself moved**: switching the
        # feature on while a wallpaper is already up has to work, and so does picking again the one
        # that is already there.
        if self.config.auto_colour:
            self._colour_soon(target, change)
            return "ok"
        if change is not None:
            # Nothing to wait for, so nothing to wait with: with the colour left alone, the only
            # write there is happens here and the picture changes at once.
            def build(tx):
                tx.session_write(*change)

            try:
                diff = writer.run(build)
            except Exception as e:  # noqa: BLE001 — the interface says what went wrong, and stays up
                self.log(f"failed on the wallpaper: {logs.what(e)}", trouble=True)
                return f"error: {e}"
            if writer.dry_run() and diff:
                self.log("would have written:\n" + diff)
        return "ok"

    def _colour_soon(self, target: str, change=None) -> None:
        """Ask for this wallpaper and its colour shortly, and only for this one.

        Restarted rather than queued: arrowing through a folder and pressing Enter four times
        should recolour the desktop once, for the fourth. The deadline is what stops a stream of
        them postponing it for ever. Both rules, and the trick of using the timer handle as the
        flag that says one is armed, are lifted whole from `_settle_then_look` in
        `daemon/kyprd_windows.py`.

        `change` is the write that puts the picture up, or None when it is already up. It is kept
        beside the target and restarted with it, so four Enters in a row set one wallpaper -- the
        fourth -- instead of four.
        """
        self._colour_wanted = target
        self._wallpaper_change = change
        now = time.monotonic()
        if self._colour_timer is None:
            self._colour_deadline = now + MAX_COLOUR_SETTLE_MS / 1000
        elif now >= self._colour_deadline:
            return                      # as late as it is allowed to be; let the armed one fire
        else:
            GLib.source_remove(self._colour_timer)
        self._colour_timer = GLib.timeout_add(COLOUR_SETTLE_MS, self._colour_due)

    def _colour_due(self) -> bool:
        """The deferred half. Nobody is waiting on this, which is why it has to speak for itself.

        The picker used to report a failure by staying open with a line across it. It is long gone
        by the time this runs, so a failure goes to the log and, when notifications are on, to the
        desktop -- there is no third place for it to be seen.
        """
        self._colour_timer = None
        target, self._colour_wanted = self._colour_wanted, ""
        change, self._wallpaper_change = self._wallpaper_change, None
        if not target:
            return False
        if not self.config.auto_colour:
            # Switched off between the picker's call and this. The picture still has to land --
            # it is what somebody asked for, and the colour was only ever the half that follows.
            if change is not None:
                self._put_the_picture_up(change)
            return False
        mode = theme.current()["mode"]
        if mode in theme.MODES and wallcolour.known_colour(target, mode) is None:
            # Not worked out yet: the picker warms it as the selection settles, so this is an
            # Enter that beat the settle, or a wallpaper set from somewhere else. Waited for
            # rather than worked out here -- on the loop it held every other caller for up to a
            # second and a half of ffmpeg. `_colour_done` applies it the moment it lands.
            self._colour_owed = (target, mode, change)
            self.warm_colour(target, mode)
            return False
        self._apply_wallpaper_colour(target, change)
        return False

    def _apply_wallpaper_colour(self, target: str, change) -> None:
        """The deferred half proper: colour, files, reload, and the picture last of all."""
        trace = clock.Trace("the wallpaper and its colour")
        answer = self.take_wallpaper_colour(target, trace)
        # **The picture last, after the reload has been asked for.** The reload is a request, not
        # the work: it returns in a millisecond and the compositor then stops the screen for more
        # than a second. Asking the shell for the wallpaper here puts its own second of work inside
        # that pause -- so what comes out of the pause is the new wallpaper, already going, instead
        # of a video that started, stopped dead and came back. Measured both ways.
        if change is not None:
            with trace.step("the picture"):
                self._put_the_picture_up(change)
        self.log(trace.line())
        if answer.startswith("error"):
            self.log(f"the wallpaper's colour did not go through: {answer}")
            self.notify_failure("The wallpaper's colour could not be applied.")
        # The tab is drawn from `Theme`, and by now it says something different from what it said
        # when this method's caller was answered.
        self.manager.changed()

    def _put_the_picture_up(self, change) -> bool:
        """Ask the shell for the wallpaper itself, in a transaction of its own.

        Its own, because a wallpaper that did not change and a colour that did not take are two
        different pieces of news: rolled into one transaction, the first would be invisible
        whenever the second was refused.
        """
        def build(tx):
            tx.session_write(*change)

        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001 — nobody is waiting; say it where it can be read
            self.log(f"failed on the wallpaper: {logs.what(e)}", trouble=True)
            self.notify_failure("The wallpaper could not be changed.")
            return False
        if writer.dry_run() and diff:
            self.log("would have written:\n" + diff)
        return True

    def warm_colour(self, target: str, mode: str) -> None:
        """Work a wallpaper's colour out with nobody waiting, and say so when it is known.

        **On a thread of its own, one at a time, and only the latest asking is kept.** It used to
        run on the loop when the loop was next idle, and that was measured to be the picker's
        stutter: it costs about a tenth of a second for a picture and up to a second and a half
        for a video, and for that long the daemon answered nobody -- the picker's next call, the
        settings window, the compositor script's report of a new window all sat in the queue
        behind ffmpeg. Arrowing across a folder queued one of these per stop, eighty-six deep.

        So the extraction runs beside the loop, and a request that arrives while one is running
        replaces the one waiting rather than joining a queue: whatever the selection is resting on
        *now* is the answer worth having. The thread touches the filesystem, GdkPixbuf and ffmpeg
        and nothing of this daemon's; it hands the answer back through the loop.

        Anyone who then asks is told by `ColourReady`, which names the wallpaper and nothing else,
        so that the one control drawn from it redraws and no other. Nothing is written but the
        cache entry.
        """
        if not target or (target, mode) == self._colour_running:
            return
        self._colour_next = (target, mode)
        self._colour_pump()

    def _colour_pump(self) -> None:
        """Start the waiting extraction, if there is one and nothing is running."""
        if self._colour_running is not None or self._colour_next is None:
            return
        self._colour_running, self._colour_next = self._colour_next, None
        target, mode = self._colour_running
        self._colour_trace = clock.Trace(
            f"working out the colour of {os.path.basename(target.rstrip('/'))}")
        threading.Thread(target=self._colour_work, args=(target, mode), daemon=True).start()

    def _colour_work(self, target: str, mode: str) -> None:
        """On the worker thread: the extraction, and the one call that hands it back."""
        began = time.monotonic()
        trouble = ""
        try:
            found = wallcolour.colour_of(target, mode)
        except Exception as e:  # noqa: BLE001 -- the loop must always hear back
            found, trouble = "", str(e)
        GLib.idle_add(self._colour_done, target, mode, found, trouble, time.monotonic() - began)

    def _colour_done(self, target: str, mode: str, found: str, trouble: str,
                     seconds: float) -> bool:
        """Back on the loop: log it, tell whoever asked, apply what was waiting on it, go again."""
        trace, self._colour_trace = self._colour_trace, None
        self._colour_running = None
        if trace is not None:
            trace.note("extract (beside the loop)", seconds)
            self.log(trace.line())
        if trouble:
            self.log(f"the colour of {os.path.basename(target.rstrip('/'))} could not be "
                     f"worked out: {trouble}")
        # Told whether or not a colour was found: "nothing to take" is an answer too now, and the
        # tab's "one moment" line is waiting to say why.
        self.manager.ColourReady(target)
        owed = self._colour_owed
        if owed is not None and owed[0] == target:
            self._colour_owed = None
            self._apply_wallpaper_colour(target, owed[2])
        elif owed is not None and self._colour_next is None:
            # Something else was asked for in between and took the slot; the change that is
            # waiting is what somebody pressed Enter on, so it goes next.
            self._colour_next = (owed[0], owed[1])
        self._colour_pump()
        return False

    def take_wallpaper_colour(self, target: str, trace=None) -> str:
        """Hand this wallpaper's colour to the desktop, as a colour of your own.

        Deliberately by calling `set_theme` rather than by planning the same steps again here. The
        two would have to stay in step through the derived scheme, the bounce and the order they
        go in, and a second copy of that is a second thing to get wrong -- the
        cost is one more transaction rather than one, which fails legibly and can simply be redone.

        The strength is never extracted. It is whatever is already set, or this app's own 25% the
        first time, and it stays somebody's own choice.
        """
        now = theme.current()
        if now["mode"] not in theme.MODES:
            return "ok"
        with clock.step(trace, "extract"):
            colour = wallcolour.colour_of(target, now["mode"])
        if not colour:
            why = wallcolour.trouble(target)
            self.log(f"no colour taken from the wallpaper{': ' + why if why else ''}")
            return "ok"
        chosen = theme.preset(now["preset"]) or theme.default_preset(now["mode"])
        #: The wallpaper's name goes down with the colour, and that is not the old flag: `set_theme`
        #: still checks that the colour really is that wallpaper's, and the argument does not exist
        #: on the bus, so no caller out there can forget it. It is handed down rather than read
        #: because the shell cannot answer it here -- see `_colour_came_from_the_wallpaper`.
        return self.set_theme({"mode": now["mode"], "preset": chosen.id, "accent": colour,
                               "tint": now["tint"] or theme.DEFAULT_TINT}, trace,
                              from_wallpaper=target)
