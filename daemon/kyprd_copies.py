"""Copies of the desk: taken before every change that writes a great deal at once, and put back by
*Go back to a copy...* on the Settings tab.

`capture_desk` gathers what a copy holds -- the part of the four config files this app writes, its
own settings, profiles and memory of windows, the colours, the shortcuts and the wallpaper --
`take_snapshot` keeps it through `daemon/snapshot.py`, and `restore_desk` puts one back, through the
same doors the tabs use for everything that is not a file. The KyprX folder's code borrows
`_restore_shortcuts` and `_restore_wallpaper` from here.

The daemon's state it reads or writes, all of it created in `Daemon.__init__`: `config`, `profiles`,
`state`.
"""

from __future__ import annotations

import os
from dataclasses import asdict

import dbus

import logs
import profiles
import shortcuts
import snapshot
import state
import theme
import wallpaper
import writer
from declared import COLOUR_CACHED_GROUPS
from state import Config, key_sequence


class CopiesPart:
    """Keeping a copy of the desk, and going back to one."""

    # ------------------------------------------------------------ copies of the desk

    def capture_desk(self) -> dict:
        """Everything a copy of the desk holds -- see `daemon/snapshot.py`. A read.

        The four config files' part raw, and the rest read through the door that writes it: this
        app's own settings, profiles and memory of windows, the colours, every key of the fixed
        shortcut list, and the wallpaper. A part the session cannot be asked about right now -- the
        shortcut registry or the shell not up yet -- is `None`, and `None` is put back as nothing:
        a copy that cannot say what the wallpaper was must not say there was none.
        """
        now = theme.current()
        desk = {
            "files": snapshot.capture_files(writer.Transaction()),
            "config": asdict(self.config),
            "profiles": [{"name": e["name"], "look": e["look"]} for e in self.profiles.entries],
            "state": {"seen": sorted(self.state.seen),
                      "refuses_ssd": sorted(self.state.refuses_ssd)},
            "colours": {k: now[k] for k in ("mode", "preset", "accent", "tint")},
        }
        try:
            desk["shortcuts"] = {a["key"]: a["keys"] for a in shortcuts.bindings()}
        except dbus.DBusException:
            desk["shortcuts"] = None
        try:
            desk["wallpaper"] = {"activities": wallpaper.snapshot_all()}
        except wallpaper.WallpaperError:
            desk["wallpaper"] = None
        return desk

    def take_snapshot(self, why: str, pinned: bool = False) -> str:
        """Keep a copy of the desk as it stands, before something big. Returns its name, or "" when
        it could not be kept -- and then the caller changes nothing: a big change with no way back
        is exactly what the copy exists to prevent.

        In dry run it is kept in memory for the daemon's lifetime and nothing is written, so going
        back to it can be tried there too.
        """
        try:
            name = snapshot.save(self.capture_desk(), why, pinned=pinned,
                                 dry_run=writer.dry_run())
        except OSError as e:
            self.log(f"could not keep a copy of the desk {why}: {logs.what(e)}", trouble=True)
            return ""
        if writer.dry_run():
            # Without the name, which carries the time: the same change has to read the same way
            # every time it is asked for, and `scripts/drive.py` runs *Restore* twice to see that.
            writer.report(f"would have kept a copy of the desk {why} -- held in memory for as "
                          f"long as this daemon runs, and never written")
        else:
            self.log(f"kept a copy of the desk {why}: {name}")
        return name

    def restore_desk(self, desk: dict, preview: bool = False) -> str:
        """Put a copy of the desk back, exactly. "ok", an "error: ..." with nothing written, or a
        "partial: ..." naming what did not come back.

        **In the order every big write here keeps.** The four files in one transaction, so the
        decoration and every window rule go up on one reconfigure. This app's own files next, so a
        failure among the desktop's tools leaves them where they were asked to be. Then the keys,
        the colours -- which stop the screen for a second or two -- and the wallpaper last, each
        through its own door. The colours are put back with `from_wallpaper=None`: the outline's
        colour is in the files, already back as it was, and must not be moved by the colour.

        `preview` writes nothing and returns what would change, in plain words.
        """
        why = snapshot.why_not(desk)
        if why:
            return f"error: {why}"
        files = desk.get("files") or {}
        target = Config.from_dict(desk.get("config"))
        profiles_wanted = desk.get("profiles")
        state_wanted = desk.get("state") or {}
        colours = desk.get("colours") or {}

        def build(tx):
            snapshot.restore_files(tx, files, COLOUR_CACHED_GROUPS)

        if preview:
            import explain
            tx = writer.Transaction()
            build(tx)
            lines = [explain.preview(tx),
                     explain.own_preview(state.CONFIG_PATH, asdict(self.config), asdict(target))]
            if isinstance(profiles_wanted, list):
                lines.append(explain.own_preview(
                    profiles.PATH,
                    {"profiles": [{"name": e["name"], "look": e["look"]}
                                  for e in self.profiles.entries]},
                    {"profiles": profiles_wanted}))
            lines.append(explain.own_preview(
                state.STATE_PATH,
                {"seen": sorted(self.state.seen), "refuses_ssd": sorted(self.state.refuses_ssd)},
                {"seen": sorted(state_wanted.get("seen") or []),
                 "refuses_ssd": sorted(state_wanted.get("refuses_ssd") or [])}))
            if colours.get("mode") in theme.MODES:
                lines.append(self.set_theme(dict(colours), from_wallpaper=None, preview=True))
            lines.extend(self._restore_shortcuts(desk.get("shortcuts"), preview=True))
            lines.extend(self._restore_wallpaper(desk.get("wallpaper"), preview=True))
            return "\n".join(line for line in lines if line and not line.startswith("error"))

        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001 — nothing was written; the caller says so
            self.log(f"could not put the copy back: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        if writer.dry_run() and diff:
            self.log("would have written:\n" + diff)
        self.config = target
        self.config.save()
        self.state.seen = {str(c) for c in state_wanted.get("seen") or []}
        self.state.refuses_ssd = {str(c) for c in state_wanted.get("refuses_ssd") or []}
        self.state.save()
        trouble: list[str] = []
        if isinstance(profiles_wanted, list):
            refused = self.profiles.replace(profiles_wanted)
            if refused:
                trouble.append(f"the profiles did not come back: {refused}")
        trouble.extend(self._restore_shortcuts(desk.get("shortcuts")))
        if colours.get("mode") in theme.MODES:
            answer = self.set_theme(dict(colours), from_wallpaper=None)
            if answer.startswith("error"):
                trouble.append(f"the colours did not come back: {answer[len('error: '):]}")
        trouble.extend(self._restore_wallpaper(desk.get("wallpaper")))
        self._look_again_soon()
        if trouble:
            self.log("put the copy back, except: " + "; ".join(trouble))
            return "partial: " + "; ".join(trouble)
        return "ok"

    def _restore_shortcuts(self, copied, preview: bool = False) -> list[str]:
        """The fixed list's keys as the copy has them. Returns what could not be put back -- or,
        with `preview`, what would change.

        Every sequence of each action, exactly, rather than the first alone as a settings file
        does: going back means all of them. A key another action holds now is left alone and said:
        from Plasma 6.7 the registry would keep it on both, and the one registered first would win.
        """
        if not isinstance(copied, dict):
            return []
        out = []
        for key, keys in sorted(copied.items()):
            component, action = shortcuts.unqualified(str(key))
            wanted = sorted(seq for seq in (key_sequence(k) for k in keys or []) if seq)
            try:
                held = shortcuts.keys_of(action, component)
                if held == wanted:
                    continue
                taken = [seq for seq in wanted if seq not in held
                         and shortcuts.holders(seq, exclude=(component, action))]
            except (KeyError, dbus.DBusException):
                continue
            if taken:
                out.append(f"{action} was not given {shortcuts.keys_text(taken)}, which another "
                           f"action holds now")
                continue
            words = (f"the keys of {action} ({component}): {shortcuts.keys_text(held)} → "
                     f"{shortcuts.keys_text(wanted)}")
            if preview:
                out.append("  " + words)
                continue
            if writer.dry_run():
                writer.report("would set " + words)
                continue
            try:
                shortcuts.set_keys(action, wanted, component)
            except (KeyError, dbus.DBusException) as e:
                out.append(f"{action}'s keys did not come back: {e}")
        return out

    def _restore_wallpaper(self, copied, preview: bool = False) -> list[str]:
        """The wallpaper of every activity the copy has, as it has it. Returns what could not be
        put back -- or, with `preview`, what would change.

        **Activity by activity, and only into the same activity.** Found by its id when it is
        still there -- a copy put back on the machine it was taken on -- and otherwise by its name,
        which is what a folder carried to another machine has. An activity the copy names and this
        desk does not have is said, and one this desk has and the copy does not name is left alone.

        Within an activity the first desktop answers for it, as it does everywhere this app reads
        the wallpaper, and every desktop is given it: the shell's write reaches all of them. An
        activity whose screens wore different pictures is put back with the first on all of them,
        and says so. Nothing is recoloured from it: the colours come back on their own.
        """
        if not isinstance(copied, dict):
            return []
        wanted = copied.get("activities")
        if not isinstance(wanted, list):
            # A copy that knew only the activity in use.
            wanted = [{"desktops": copied.get("desktops") or []}] if copied.get("desktops") else []
        if not wanted:
            return []
        try:
            here = wallpaper.snapshot_all()
        except wallpaper.WallpaperError as e:
            return [f"the wallpaper did not come back: {e}"]
        out: list[str] = []
        steps = []
        for activity in wanted:
            desktops = [d for d in activity.get("desktops") or [] if isinstance(d, dict)]
            if not desktops:
                continue
            name = str(activity.get("name") or "")
            now = (next((a for a in here if a.get("activity") == activity.get("activity")), None)
                   if activity.get("activity") else None)
            if now is None and name:
                now = next((a for a in here if a.get("name") == name), None)
            if now is None and "name" not in activity:
                now = next((a for a in here if a.get("current")), None)
            if now is None:
                out.append(f"there is no activity called {name} here, so its wallpaper was not put "
                           f"on")
                continue
            where = now.get("activity")
            first = desktops[0]
            mode = "video" if str(first.get("plugin")) == wallpaper.VIDEO_PLUGIN else "image"
            if str(first.get("plugin")) not in wallpaper.PLUGINS.values():
                continue
            if mode == "video" and not wallpaper.plugin_installed(wallpaper.VIDEO_PLUGIN):
                out.append(f"{now.get('name')}: the wallpaper was left as it is -- the video "
                           f"plugin is not installed here")
                continue
            target = wallpaper.current_target(mode, {"desktops": desktops})
            if target and not os.path.exists(wallpaper.to_path(target)):
                out.append(f"{now.get('name')}: the wallpaper was left as it is -- "
                           f"{wallpaper.to_path(target)} is not there")
                target = ""
            change = (wallpaper.plan(mode, target, now, activity=where) if target
                      else wallpaper.plugin_plan(mode, now, activity=where))
            if change:
                steps.append((change, now.get("name")))
            pause = str(first.get("pause") or "")
            if mode == "video" and pause in wallpaper.PAUSE_MODES:
                paused = wallpaper.pause_plan(pause, now, activity=where)
                if paused:
                    steps.append((paused, now.get("name")))
            if len({(str(d.get("plugin")), str(d.get("image")), str(d.get("last")))
                    for d in desktops}) > 1:
                out.append(f"{now.get('name')}: the screens had different wallpapers; the first "
                           f"screen's went on all of them")
        if preview:
            # The shell's own words say "this activity"; which one is said in front of them.
            return [f"  {name}: {plain}" for (_, _, plain), name in steps] + out
        if steps:
            def build(tx):
                for step, _ in steps:
                    tx.session_write(*step)

            try:
                diff = writer.run(build)
            except Exception as e:  # noqa: BLE001
                return out + [f"the wallpaper did not come back: {e}"]
            if writer.dry_run() and diff:
                self.log("would have written:\n" + diff)
        return out
