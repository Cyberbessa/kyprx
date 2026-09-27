"""Keeping the KyprX folder and the desk agreed, a few seconds after either one changes.

A change on the desk -- made here or in another program, noticed by watching the four config files,
the shortcut registry and the shell's config -- is mirrored into the folder; a change that arrived
in the folder -- a copy, a `git pull`, an edit -- is merged three ways with the desk and applied.
`daemon/folder.py` decides which side a change came from and what is merged, and
`daemon/kyprd_desk.py` describes and applies the desk; this is the timing and the order between
them, and the one place that knows whether the session is ready for an arrival. The stray
`[Exceptions]` group Klassy's own settings leave behind is removed first on every pass, while KyprX
is on the desk, so the folder never records it; and the decoration's per-window list is written
compactly when somebody else wrote it last (`compact_overrides`).

The daemon's state it reads or writes: `manager`, `state`, `_folder_base_mem`,
`_folder_holding`, `_folder_said`, `_folder_state`, `_folder_timer`, `_folder_waiting_since`,
`_stray_held` and `_compact_held`, created in `Daemon.__init__`, and `_folder_watches`, which
`watch_the_folder` creates.
"""

from __future__ import annotations

import os
import time

import dbus
from gi.repository import Gio, GLib

import clock
import folder
import klassy
import logs
import shortcuts
import snapshot
import wallpaper
import writer


class FolderPart:
    """The folder and the desk, brought into step."""

    # -- keeping folder and desk agreed

    #: How long after a change on the desk the folder is written, in milliseconds. Long enough that
    #: dragging a number is one write, short enough that a commit made a moment later has it.
    FOLDER_SETTLE_MS = 2500
    #: How long the folder's own files have to stand still before what arrived there is applied,
    #: in seconds. A copy or a checkout writes file after file; half of one is never applied.
    FOLDER_QUIET_S = 3
    #: How long an arrival waits for the shortcut registry and the shell, which may come up after
    #: this daemon at the start of a session, before it applies without the parts they carry.
    FOLDER_SESSION_WAIT_S = 60

    def folder_soon(self, delay_ms: int | None = None) -> None:
        """Keep folder and desk agreed a moment from now -- one timer, started again by each
        request, so a burst of changes is one pass."""
        if self._folder_timer is not None:
            GLib.source_remove(self._folder_timer)
        self._folder_timer = GLib.timeout_add(delay_ms or self.FOLDER_SETTLE_MS, self._folder_due)

    def _folder_due(self) -> bool:
        self._folder_timer = None
        # The pass that runs at every start and after every change to the decoration's config, so
        # the one that finds the leftover group -- and first, so what the folder records is the
        # desk without it.
        try:
            self.clear_stray_exceptions()
        except Exception as e:  # noqa: BLE001 — a repair that fails is said; the pass goes on
            self.log(f"could not look for the decoration's leftover [Exceptions] group: "
                     f"{logs.what(e)}", trouble=True)
        try:
            self.compact_overrides()
        except Exception as e:  # noqa: BLE001 — the list still works in its long form
            self.log(f"could not write the decoration's per-window list compactly: "
                     f"{logs.what(e)}", trouble=True)
        try:
            self.folder_sync()
        except Exception as e:  # noqa: BLE001 — the folder is a mirror; the daemon stays up
            self.log(f"could not bring the KyprX folder and the desk into step: "
                     f"{logs.what(e)}", trouble=True)
            self._folder_state = {"state": "problem", "problems": [str(e)]}
        return False

    def _base(self) -> dict | None:
        """The last agreement. A dry run starts from the real one on disk -- the folder a real run
        left is not something that "arrived" -- and keeps whatever it would have agreed since in
        memory, never on disk."""
        if writer.dry_run() and self._folder_base_mem is not None:
            return self._folder_base_mem
        return folder.load_base()

    def _keep_base(self, base: dict) -> None:
        if writer.dry_run():
            self._folder_base_mem = base
        else:
            folder.save_base(base)

    def _session_ready(self, target: dict) -> bool:
        """Can every door the parts in `target` go through be reached right now?"""
        bus = dbus.SessionBus()
        needs = []
        if "shortcuts" in target:
            needs.append(shortcuts.SERVICE)
        if "wallpaper" in target:
            needs.append(wallpaper.SHELL if hasattr(wallpaper, "SHELL") else "org.kde.plasmashell")
        try:
            return all(bus.name_has_owner(n) for n in needs)
        except dbus.DBusException:
            return False

    def folder_sync(self) -> None:
        """One pass of keeping the KyprX folder and the desk agreed. See `daemon/folder.py`.

        What arrived in the folder is dealt with first, and only then is the desk written into it:
        a write the other way round would put the desk over a change nobody has applied yet.
        """
        if self._off_desk():
            return
        texts, unreadable = folder.read_texts()
        base = self._base()
        arrived = folder.arrivals(texts, base)
        if arrived or unreadable:
            busy = folder.git_busy()
            if busy:
                self._folder_state = {"state": "waiting",
                                      "detail": f"git is in the middle of {busy} in the "
                                                f"repository around the folder"}
                self.folder_soon(self.FOLDER_QUIET_S * 1000)
                return
            youngest = max((os.path.getmtime(os.path.join(folder.PATH, n)) for n in arrived
                            if os.path.exists(os.path.join(folder.PATH, n))), default=0)
            if time.time() - youngest < self.FOLDER_QUIET_S:
                self._folder_state = {"state": "waiting",
                                      "detail": "the folder's files are still changing"}
                self.folder_soon(self.FOLDER_QUIET_S * 1000)
                return
            areas, fmt, problems = folder.parse(texts)
            problems = unreadable + problems + (self.folder_problems(areas) if not problems else [])
            if problems:
                self._folder_problem(problems)
                return
            self._folder_arrival(texts, arrived, areas, fmt, base)
            return
        self._folder_mirror(texts, base)

    def _folder_problem(self, problems: list[str]) -> None:
        """A folder that cannot be applied: nothing is applied, nothing in it is written over, and
        it is said -- once for each different set of problems, not on every pass."""
        self._folder_state = {"state": "problem", "problems": problems}
        if problems != self._folder_said:
            self._folder_said = list(problems)
            self.log("the KyprX folder cannot be applied, so nothing was applied and nothing in "
                     "it is written over: " + "; ".join(problems))
            self.notify_failure("The KyprX folder was not applied\n" + problems[0]
                                + (f" (and {len(problems) - 1} more)" if len(problems) > 1 else ""))
        self._folder_holding = False

    def _folder_arrival(self, texts: dict, arrived: list[str], areas: dict, fmt: int,
                        base: dict | None) -> None:
        target, conflicts, whole = folder.arrival_target(arrived, areas, base, self.describe())
        if target and not self._session_ready(target):
            waited = time.time() - (self._folder_waiting_since or time.time())
            self._folder_waiting_since = self._folder_waiting_since or time.time()
            if waited < self.FOLDER_SESSION_WAIT_S:
                self._folder_state = {"state": "waiting",
                                      "detail": "the desktop's shortcut registry or shell is not "
                                                "up yet"}
                self._folder_holding = True
                self.folder_soon(3000)
                return
        self._folder_waiting_since = None
        if writer.dry_run():
            words, _ = self.apply_areas(target, preview=True)
            key = (tuple(arrived), words)
            if key != self._folder_said:
                self._folder_said = key
                writer.report("a changed KyprX folder arrived (" + ", ".join(arrived) + "); a real "
                              "run would keep a copy of the desk and apply it:\n"
                              + (words or "  nothing would change on the desk"))
            self._folder_state = {"state": "arrived", "detail": "dry run: reported, not applied",
                                  "files": arrived}
            self._folder_holding = False
            return
        extra = {n: texts[n] for n in arrived if n in texts}
        copy = self.take_snapshot("before applying what arrived in the KyprX folder", pinned=whole)
        if not copy:
            self._folder_problem(["a copy of the desk could not be kept first, so nothing was "
                                  "applied"])
            return
        if extra:
            try:
                target_dir = os.path.join(snapshot.DIRECTORY, copy, "folder")
                os.makedirs(target_dir, exist_ok=True)
                for n, t in extra.items():
                    with open(os.path.join(target_dir, n), "w", encoding="utf-8") as fh:
                        fh.write(t)
            except OSError as e:
                self.log(f"could not keep the arrived files beside the copy: "
                         f"{logs.what(e)}", trouble=True)
        trace = clock.Trace("applied what arrived in the KyprX folder")
        with trace.step("apply"):
            answer, trouble = self.apply_areas(target)
        self.log(trace.line())
        if answer.startswith("error"):
            self._folder_problem([f"applying it failed, and the desk may be half changed -- "
                                  f"Go back to a copy... puts it back: {answer[len('error: '):]}"])
            return
        if fmt < folder.FORMAT:
            texts = dict(texts, **folder.texts_of(areas), **{folder.MANIFEST: folder.render(
                folder.manifest())})
            for n, t in folder.texts_of(areas).items():
                folder.write_text(n, t)
            folder.write_text(folder.MANIFEST, folder.render(folder.manifest()))
        self._keep_base({"folder": dict(texts), "desk": self.describe()})
        self._folder_state = {"state": "applied", "when": time.strftime("%H:%M"),
                              "files": arrived, "conflicts": conflicts, "trouble": trouble,
                              "snapshot": copy}
        self.log(f"applied what arrived in the KyprX folder ({', '.join(arrived)}); a copy of the "
                 f"desk from before is {copy}"
                 + (f"; the folder won over the desk on {', '.join(conflicts)}" if conflicts
                    else "")
                 + (f"; not applied: {'; '.join(trouble)}" if trouble else ""))
        if trouble:
            self.notify_failure("Part of the KyprX folder was not applied\n" + trouble[0])
        self._folder_said = None
        if self._folder_holding:
            self._folder_holding = False
            self.request_inventory()
        # The signal alone, not `changed`: the folder was just brought into step, and asking for
        # another pass would be a pass with nothing to do.
        self.manager.Changed()

    def _folder_mirror(self, texts: dict, base: dict | None) -> None:
        """Write the desk into the folder -- the parts the desk changed since the last agreement,
        a file that is missing, and on the first pass all of it."""
        trace = clock.Trace("brought the KyprX folder into step")
        with trace.step("describe the desk"):
            desk = self.describe()
        writes, agreed = folder.mirror_plan(texts, base, desk, writer.dry_run())
        if writer.dry_run():
            said = tuple(sorted(writes))
            if writes and said != self._folder_said:
                self._folder_said = said
                writer.report("would have saved the KyprX folder's " + ", ".join(sorted(writes))
                              + " -- held back, like every other file in a dry run")
        else:
            with trace.step("write"):
                for name, text in writes.items():
                    folder.write_text(name, text)
                folder.ensure_extras()
            if writes:
                self.log(f"wrote the KyprX folder's {', '.join(sorted(writes))}")
                # Timed, and said only when there was something to write: a pass that finds the
                # folder already in step is most passes, and a line for each would bury the log.
                self.log(trace.line())
        self._keep_base(agreed)
        if self._folder_state.get("state") not in ("applied",) or writes:
            self._folder_state = dict(self._folder_state, state=(
                "applied" if self._folder_state.get("state") == "applied" and not writes
                else "in step"))

    def _off_desk(self) -> bool:
        """KyprX taken off the desk: the folder keeps the setup and is neither written nor
        applied until it is put back. See `take_off`."""
        return bool(self.state.off)

    def folder_status(self) -> dict:
        return {"path": folder.PATH, "snapshots": snapshot.DIRECTORY,
                "dry_run": writer.dry_run(), **self._folder_state,
                **({"state": "off", "off": True, "off_copy": self.state.off.get("copy", "")}
                   if self._off_desk() else {})}

    def watch_the_folder(self) -> None:
        """Notice what would put the KyprX folder and the desk out of step, wherever it comes from.

        The folder itself, for a copy, a `git pull` or an edit -- and after that the wait is long,
        `FOLDER_QUIET_S`, because a checkout writes file after file. The four config files this
        app writes, because the decoration's own dialog and the desktop's settings write them too,
        and a folder that heard only about this app's changes would fall behind and later undo the
        rest. The shortcut registry's own signal, for a key changed in the desktop's settings. The
        shell's config is watched already, for the wallpaper plugin, and asks too.

        None of it is the guarantee -- a pass also runs at every start and before the folder is
        opened from the Settings tab. It is what keeps the folder minutes rather than days behind.
        """
        self._folder_watches = []
        quiet = self.FOLDER_QUIET_S * 1000
        for path, delay in ((os.path.realpath(folder.PATH), quiet), (writer.KLASSYRC, None),
                            (writer.PRESETSRC, None), (writer.KWINRULESRC, None),
                            (writer.KWINRC, None)):
            try:
                handle = Gio.File.new_for_path(path)
                watch = (handle.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
                         if path == os.path.realpath(folder.PATH)
                         else handle.monitor_file(Gio.FileMonitorFlags.NONE, None))
                watch.connect("changed", lambda *_, d=delay: self.folder_soon(d))
                self._folder_watches.append(watch)
            except Exception as e:  # noqa: BLE001 — a failed watch never stops the daemon
                self.log(f"could not watch {path}: {logs.what(e)}", trouble=True)
        try:
            dbus.SessionBus().add_signal_receiver(
                lambda *_: self.folder_soon(), signal_name=shortcuts.SHORTCUTS_CHANGED,
                dbus_interface=shortcuts.IFACE)
        except dbus.DBusException as e:
            self.log(f"could not listen for shortcuts changing: {logs.what(e)}", trouble=True)

    # -- the decoration's leftover group

    def remove_stray_exceptions(self) -> str:
        """Take the decoration's leftover `[Exceptions]` group out of its config, after keeping a
        copy of the desk. Every window with no override of its own then has the decoration's own
        defaults again -- a title bar, where the group was hiding it. "ok" or "error: ..."."""
        if klassy.STRAY_EXCEPTIONS not in writer.Transaction().klassy.groups:
            return "ok"
        if not self.take_snapshot("before removing the decoration's leftover Exceptions group"):
            return "error: a copy of the desk could not be kept first, so nothing was changed"

        def build(tx):
            tx.klassy.delete_group(klassy.STRAY_EXCEPTIONS)
            tx.reload_kwin = True
            tx.reload_colours = True

        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001
            return f"error: {e}"
        if writer.dry_run() and diff:
            self.log("would have written:\n" + diff)
        self.manager.changed()
        return "ok"

    def compact_overrides(self) -> None:
        """Write the decoration's per-window list with windows set alike sharing one entry, when
        it is not written that way -- see `klassy.MERGED` for why, and for what was measured.

        Every write this app makes to the list already does it; this is for a list somebody else
        wrote last: a copy of the desk from before, put back exactly as it was, or rows added in
        the decoration's own settings. It runs where `clear_stray_exceptions` runs and follows its
        rules: not while KyprX is off the desk, and said once when it cannot be written. What any
        window gets does not change, so nothing is reloaded and no copy of the desk is kept first
        -- like every other rewrite of the list, each of which renumbers the whole of it."""
        if self._off_desk() or not klassy.compact(writer.Transaction().klassy):
            self._compact_held = False
            return
        if self._compact_held:
            return
        try:
            diff = writer.run(lambda tx: klassy.compact(tx.klassy))
        except Exception as e:  # noqa: BLE001 — said once; the list still works as it is
            self._compact_held = True
            self.log(f"could not write the decoration's per-window list compactly: {logs.what(e)}",
                     trouble=True)
            return
        if writer.dry_run():
            self._compact_held = True
            if diff:
                self.log("would have written the decoration's per-window list with windows set "
                         "alike sharing one entry:\n" + diff)
        elif diff:
            self.log("wrote the decoration's per-window list with windows set alike sharing one "
                     "entry; nothing on screen changes")

    def clear_stray_exceptions(self) -> None:
        """Remove the leftover group wherever it turns up, without being asked: while it is there
        the Windows tab's *title bar* switch does nothing -- see `klassy.STRAY_EXCEPTIONS`. Not
        while KyprX is off the desk, when this app does nothing by itself; and said once when it
        cannot go -- a dry run, a write that failed -- rather than on every pass that finds it.

        Measured, so this is known not to chase the decoration round in circles: the group does not
        come back when the decoration reloads, and one put back by hand was gone 2.7 s later, the
        file byte for byte what the first removal left."""
        if self._off_desk() or klassy.STRAY_EXCEPTIONS not in writer.Transaction().klassy.groups:
            self._stray_held = False
            return
        if self._stray_held:
            return
        answer = self.remove_stray_exceptions()
        self._stray_held = writer.dry_run() or answer != "ok"
        if answer != "ok":
            self.log(f"could not remove the decoration's leftover [Exceptions] group: {answer}")
        elif not writer.dry_run():
            self.log("removed the decoration's leftover [Exceptions] group, which was hiding the "
                     "title bar of every window without a setting of its own")
