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
            desk["shortcuts"] = self._keys_now()
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

        `preview` writes nothing and returns what would change, in plain words. A copy of a later
        shape is refused before anything is read (`snapshot.why_not`); one of an earlier shape goes
        back for what it knew, a group that came after it left as it is (`snapshot.SINCE`).
        """
        why = snapshot.why_not(desk)
        if why:
            return f"error: {why}"
        files = desk.get("files") or {}
        shape = snapshot.shape_of(desk)
        target = Config.from_dict(desk.get("config"))
        # Which screen the colour comes from is this computer's, and a copy -- one from before the
        # choice existed, or one carried from another machine -- does not get to move it.
        target.colour_screen = self.config.colour_screen
        profiles_wanted = desk.get("profiles")
        state_wanted = desk.get("state") or {}
        colours = desk.get("colours") or {}

        def build(tx):
            snapshot.restore_files(tx, files, COLOUR_CACHED_GROUPS, shape)

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
            if self._colours_kept(colours):
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
        # What the copy owes, and nothing owed since: going back to the copy kept before a folder
        # arrived takes back the keys that arrival was still waiting to put on, too. A dry run
        # changes nothing, and owes nothing either (`_restore_shortcuts`).
        if not writer.dry_run():
            self.state.owed_keys = {}
        self.state.save()
        trouble: list[str] = []
        if isinstance(profiles_wanted, list):
            refused = self.profiles.replace(profiles_wanted)
            if refused:
                trouble.append(f"the profiles did not come back: {refused}")
        trouble.extend(self._restore_shortcuts(desk.get("shortcuts")))
        if self._colours_kept(colours):
            answer = self.set_theme(dict(colours), from_wallpaper=None)
            if answer.startswith("error"):
                trouble.append(f"the colours did not come back: {answer[len('error: '):]}")
        trouble.extend(self._restore_wallpaper(desk.get("wallpaper")))
        self._look_again_soon()
        if trouble:
            self.log("put the copy back, except: " + "; ".join(trouble))
            return "partial: " + "; ".join(trouble)
        return "ok"

    @staticmethod
    def _colours_kept(colours: dict) -> bool:
        """Whether a copy's colours are ones it can put back: a mode, and a preset of KyprX's. A
        desk that wore no preset -- another global theme, or a scheme of its own under Klassy's --
        is recorded with an empty one, and `set_theme` would read that as the mode's default,
        Longive for dark: KyprX's look, put on by going back to a desk that did not wear it. So
        those colours are left as the desk has them (KNOWN-ISSUES says what that leaves)."""
        return colours.get("mode") in theme.MODES and bool(colours.get("preset"))

    def _keys_now(self) -> dict[str, list[list[int]]]:
        """Every key of the fixed shortcut list as the desk holds it, by `shortcuts.qualified`
        name: the registry's, and for an action keys are owed to (`State.owed_keys`) the owed ones
        -- what the desk holds once the action is there to take them. Described any other way, an
        action KyprX's compositor script has not registered yet would read as having no keys, then
        as having its defaults, and the KyprX folder would be written with them over the keys it
        brought. Raises `dbus.DBusException` when the registry cannot be asked."""
        held = {a["key"]: a["keys"] for a in shortcuts.bindings()}
        held.update({k: [list(s) for s in v] for k, v in self.state.owed_keys.items()})
        return held

    def _restore_shortcuts(self, copied, preview: bool = False) -> list[str]:
        """The fixed list's keys as the copy has them. Returns what could not be put back -- or,
        with `preview`, what would change.

        Every sequence of each action, exactly: going back means all of them. A key another action holds now is left alone and said:
        from Plasma 6.7 the registry would keep it on both, and the one registered first would win.

        **An action not there yet is owed its keys** (`State.owed_keys`), which go on once it is
        (`FolderPart.pay_owed_keys`): one of KyprX's own that the registry does not have -- its
        compositor script registers them as it loads, which on a package install is after the
        first start applied the KyprX folder, measured in the sandbox's folder scenario -- and any
        action at all while the registry cannot be asked. Any other action the registry does not
        have is somebody else's this desk lacks, and is passed over. A dry run owes nothing.
        """
        if not isinstance(copied, dict):
            return []
        out = []
        owing = False
        for key, keys in sorted(copied.items()):
            component, action = shortcuts.unqualified(str(key))
            name = shortcuts.qualified(component, action)
            wanted = sorted(seq for seq in (key_sequence(k) for k in keys or []) if seq)
            try:
                held = shortcuts.keys_of(action, component)
                taken = [seq for seq in wanted if seq not in held
                         and shortcuts.holders(seq, exclude=(component, action))]
            except KeyError:
                if component == shortcuts.KWIN_COMPONENT and action in shortcuts.SCRIPT_ACTIONS:
                    owing = self._owe(name, action, component, wanted, preview,
                                      "once KyprX's compositor script has registered it",
                                      out) or owing
                continue
            except dbus.DBusException:
                owing = self._owe(name, action, component, wanted, preview,
                                  "once the desktop's shortcut registry answers", out) or owing
                continue
            if not preview and not writer.dry_run():
                # Put on now, so nothing owed from before is put on over it later.
                owing = self.state.owed_keys.pop(name, None) is not None or owing
            if held == wanted:
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
        if owing:
            self.state.save()
        return out

    def _owe(self, name: str, action: str, component: str, wanted: list, preview: bool,
             when: str, out: list[str]) -> bool:
        """Keys for an action not there yet: said in a preview, reported in a dry run, and owed
        otherwise (`State.owed_keys`). True when what is owed changed."""
        words = f"the keys of {action} ({component}): {shortcuts.keys_text(wanted)}, {when}"
        if preview:
            out.append("  " + words)
            return False
        if writer.dry_run():
            writer.report("would set " + words)
            return False
        if self.state.owed_keys.get(name) == wanted:
            return False
        self.state.owed_keys[name] = [list(s) for s in wanted]
        self.log(f"holding {words}")
        return True

    def _restore_wallpaper(self, copied, preview: bool = False) -> list[str]:
        """The wallpaper of every activity the copy has, as it has it. Returns what could not be
        put back -- or, with `preview`, what would change.

        **Activity by activity, and only into the same activity.** Found by its id when it is
        still there -- a copy put back on the machine it was taken on -- and otherwise by its name,
        which is what a folder carried to another machine has. An activity the copy names and this
        desk does not have is said, and one this desk has and the copy does not name is left alone.

        **Screen by screen, when the copy can say which screen each wallpaper was on**
        (`_on_their_screens`). A copy of the desk names each desktop by the shell's own id, which
        holds on the machine it was taken on; the KyprX folder, which is carried to other
        machines, names each screen by its number. Each wallpaper goes back on its own screen, and
        a screen the copy does not name is left as it is: a folder written on a computer with one
        screen, applied on one with two, sets the first screen and leaves the second alone. A
        screen the copy names and this desk does not have is skipped, and said in the log only --
        a folder shared with a computer with fewer screens would otherwise say it on every arrival.

        **A copy that cannot say** -- a folder written before its screens were numbered, or a copy
        from another machine -- goes back the way it always did: the first desktop's wallpaper on
        every desktop, unless the primary screen already shows it, and screens that differed are
        said. Judged by every screen instead, such a folder would write its first screen's
        wallpaper over the others on every arrival. Nothing is recoloured from it: the colours come
        back on their own.
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
            pairs, missing = _on_their_screens(desktops, now)
            for row in missing if not preview else []:
                self.log(f"{now.get('name')}: a wallpaper for screen "
                         f"{wallpaper.screen_number(row) + 1} was left out -- this desk has no "
                         f"such screen in that activity")
            if pairs:
                self._restore_screens(pairs, now, steps, out)
            elif not missing:
                self._restore_the_old_way(desktops, now, steps, out)
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

    @staticmethod
    def _wallpaper_of(row: dict, now: dict, out: list[str]) -> tuple[str, str] | None:
        """The mode and the target one copied desktop asks for, or None when it asks for nothing
        this app sets here. A file that is not there is said, and asks for the plugin alone."""
        plugin = str(row.get("plugin"))
        if plugin not in wallpaper.PLUGINS.values():
            return None
        mode = "video" if plugin == wallpaper.VIDEO_PLUGIN else "image"
        if mode == "video" and not wallpaper.plugin_installed(wallpaper.VIDEO_PLUGIN):
            said = (f"{now.get('name')}: the wallpaper was left as it is -- the video plugin is "
                    f"not installed here")
            if said not in out:
                out.append(said)
            return None
        target = wallpaper.current_target(mode, {"desktops": [row]})
        if target and not os.path.exists(wallpaper.to_path(target)):
            out.append(f"{now.get('name')}: the wallpaper was left as it is -- "
                       f"{wallpaper.to_path(target)} is not there")
            target = ""
        return mode, target

    def _restore_screens(self, pairs, now: dict, steps: list, out: list[str]) -> None:
        """Each copied desktop's wallpaper on the screen of the desktop here it was matched to,
        and the video's pause, which is the activity's, from the first video among them."""
        where = now.get("activity")
        for row, mine in pairs:
            asked = self._wallpaper_of(row, now, out)
            view = wallpaper.on_screen_number(now, wallpaper.screen_number(mine))
            if asked is None or view is None:
                continue
            mode, target = asked
            change = (wallpaper.plan(mode, target, view, activity=where) if target
                      else wallpaper.plugin_plan(mode, view, activity=where))
            if change:
                steps.append((change, now.get("name")))
        videos = [row for row, _ in pairs if str(row.get("plugin")) == wallpaper.VIDEO_PLUGIN]
        pause = str(videos[0].get("pause") or "") if videos else ""
        if pause in wallpaper.PAUSE_MODES and wallpaper.plugin_installed(wallpaper.VIDEO_PLUGIN):
            paused = wallpaper.pause_plan(pause, now, activity=where)
            if paused:
                steps.append((paused, now.get("name")))

    def _restore_the_old_way(self, desktops: list[dict], now: dict, steps: list,
                             out: list[str]) -> None:
        """A copy that cannot say which screen is which: the first desktop's wallpaper on every
        desktop, unless the primary screen already shows it -- what this app always did."""
        where = now.get("activity")
        first = desktops[0]
        asked = self._wallpaper_of(first, now, out)
        if asked is None:
            return
        mode, target = asked
        # Judged by the primary screen alone, the way this was always judged; the screens of this
        # desk that show something else keep it, which is the point of a screen of its own.
        primary = wallpaper.on_screen_number(now, 0)
        if primary is not None:
            judged = (wallpaper.plan(mode, target, primary, activity=where) if target
                      else wallpaper.plugin_plan(mode, primary, activity=where))
            if judged is None:
                return
        change = (wallpaper.plan(mode, target, now, activity=where) if target
                  else wallpaper.plugin_plan(mode, now, activity=where))
        if change:
            steps.append((change, now.get("name")))
        pause = str(first.get("pause") or "")
        if mode == "video" and pause in wallpaper.PAUSE_MODES:
            paused = wallpaper.pause_plan(pause, now, activity=where)
            if paused:
                steps.append((paused, now.get("name")))
        if change and len({(str(d.get("plugin")), str(d.get("image")), str(d.get("last")))
                           for d in desktops}) > 1:
            out.append(f"{now.get('name')}: the screens had different wallpapers; the first "
                       f"screen's went on all of them")


def _on_their_screens(desktops: list[dict], now: dict) -> tuple[list, list]:
    """Each copied desktop with the desktop of `now` it belongs on, and the copied desktops that
    name a screen `now` does not have.

    By the shell's own id first, which a copy of the desk carries and which holds on the machine
    it was taken on -- a copy made before its rows carried their screen is found this way too --
    and then by the screen's number, which the KyprX folder carries. A desktop here is given at
    most one, and only one with a screen of its own can be written to on its own. A copy whose
    desktops are found neither way gets two empty lists, and `_restore_wallpaper` puts it back the
    way it always did.
    """
    here = [d for d in now.get("desktops") or [] if isinstance(d, dict)]
    taken: set[int] = set()
    pairs, missing = [], []
    for row in desktops:
        found = None
        if row.get("id"):
            found = next((i for i, d in enumerate(here) if i not in taken
                          and str(d.get("id") or "") == str(row["id"])), None)
        number = wallpaper.screen_number(row)
        if found is None and number >= 0:
            found = next((i for i, d in enumerate(here) if i not in taken
                          and wallpaper.screen_number(d) == number), None)
            if found is None:
                missing.append(row)
        if found is not None and wallpaper.screen_number(here[found]) >= 0:
            taken.add(found)
            pairs.append((row, here[found]))
    return pairs, missing
