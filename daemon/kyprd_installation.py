"""This installation of KyprX: what it needs on this machine, and taking it off the machine.

**What it needs.** The four projects KyprX is built on are checked by `daemon/requirements.py`; this
part keeps the answer, because two of the four cost a question to the package manager each --
measured on this desk, about 45 ms for the whole check, 40 of them the two questions -- and the
settings window asks on every tab it opens. It is worked out again when a settings window claims
the interface -- somebody opening KyprX is the moment something may have been installed since --
and whenever the Settings tab's *Check again* asks for it.

**A new version.** A package manager replaces the files under a running daemon, a running window
and a running compositor script; each goes on as the version it started as. `Diagnostics` reports
the version this daemon runs beside the one on disk, and a window that is newer than the daemon
offers to restart it. The daemon does not restart itself when a window opens: a window opened
with the settings key runs inside the daemon's unit, and would close with it the moment it
appeared. The first start of a version that is not the one that ran here last
(`note_the_version`) has the compositor load KyprX's script again, whose file may have changed
with the rest, and says so in the log -- which takes in a new script only where the session has
not run KyprX's declarative one yet; anywhere else the new script runs from the next login, and
the Tiling tab says so. What changed in the format of KyprX's own files is brought up to date by
`daemon/migrate.py` at every start, as it always is.

**Taking it off the machine.** A package manager removes the files a package installed and nothing
else: it runs as root, for every user, and never opens anybody's settings -- nor should it. So
removing KyprX starts here, as the user whose settings they are, and ends with the command that
removes the package, said rather than run. Two things are asked, never assumed: whether KDE is put
back as KDE has it (*Take KyprX off this desk…*, which keeps a copy of the desk first), and whether
the KyprX folder, with the setup and the copies in it, is kept. Everything else that is only
KyprX's goes -- the switch and the load of its compositor script, its tiling's settings with the
zone layouts and arrangements in them, the overlays' two rules and their entries in the blur's list,
its actions in the shortcut registry and the keys on them, its colour scheme when the desktop is not
wearing it, and its memory of this machine and its caches. The four projects stay: they are
programs of their own, and whether each goes is the package manager's business, which removes only
what it installed for KyprX.

The daemon's state it reads or writes, all of it created in `Daemon.__init__`: `_needs`, `config`,
`state` (`app_version`, and `off` in memory only after a removal).
"""

from __future__ import annotations

import os
import shutil

import about
import effects
import explain
import klassy
import logs
import reload as reloader
import requirements
import rules
import shortcuts
import snapshot
import state
import theme
import wallcolour
import writer
from kyprd_names import OVERLAY_CLASSES, OVERLAYS, SCRIPT_PLUGIN

#: This app's derived caches: the colours taken out of wallpapers and the picker's pictures, both
#: under one folder (`daemon/wallcolour.py`, `gui/thumbs.py`).
CACHE_ROOT = os.path.dirname(os.path.dirname(wallcolour.CACHE_DIR))

#: Two files the desktop writes in KyprX's name, which nothing of KyprX's writes and nothing else
#: removes; both were found on this desk after every road of removing KyprX had been read. What
#: KDE's file dialog remembers for an application goes in a file named after it, where every
#: program's state goes (`<name>staterc`) -- for KyprX, whose name is "KyprX" (`gui/kyprx.py`), the
#: folders last opened from the Wallpaper tab. And the shell keeps a cache of each Plasma style it
#: has worn, named after the style (`plasma_theme_<name>.kcache`, 17 MB of KyprX's here). Both
#: follow the XDG variables, as the desktop that writes them does.
STATE_CONFIG = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state"),
                            "KyprXstaterc")
STYLE_CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
                           f"plasma_theme_{theme.STYLE}.kcache")


class InstallationPart:
    """What KyprX needs here, kept between questions; and KyprX taken off this computer."""

    def needs(self, refresh: bool = False) -> list[dict]:
        """Each of the four projects as it stands, from memory unless `refresh` or never asked.

        A check that fails is said once and answered with nothing, rather than taking the settings
        window's every read down with it: an empty list reads as "nothing known to be wrong".
        """
        if self._needs is None or refresh:
            try:
                self._needs = requirements.check()
            except Exception as e:  # noqa: BLE001 -- a check that fails must not fail the reads
                self.log(f"could not check what KyprX needs: {logs.what(e)}", trouble=True)
                self._needs = []
            wrong = [n["name"] for n in self._needs if n["state"] != requirements.OK]
            if wrong:
                self.log("missing or not running: " + ", ".join(wrong))
        return self._needs

    # ------------------------------------------------------------ a new version

    def note_the_version(self) -> None:
        """Remember which version of KyprX runs here, and on the first start of another one, have
        the compositor load KyprX's script again: a package update replaced its file, and the
        compositor goes on running the one it loaded until the script is unloaded and loaded again
        or the session ends (measured: see `daemon/reload.py`). The very first start has nothing
        to reload -- `switch_the_script_on` has just loaded it, or `install.sh` did.

        **What the reload can and cannot bring**, both measured in a nested KWin. It is what loads
        KyprX's declarative script in place of the plain JavaScript one an earlier version ran:
        that first switch under the same id is read fresh -- once the compositor has been up for
        about a minute, since until then it goes by the list of packages it read as it started. A
        declarative script the session has already loaded is another matter: the compositor keeps
        what it compiled of it for the whole session, and loading it again runs the old code
        again. So a later version of it is finished by logging out and back in, which the Tiling
        tab asks for when the script's version is not the one installed ("old-script"). The reload
        stays for the first case, and costs the second nothing it would not have cost anyway."""
        now, last = about.RUNNING, self.state.app_version
        if not now or now == last:
            return
        if last:
            self.log(f"updated from {last} to {now}")
            if writer.dry_run():
                writer.report("would have the compositor load KyprX's script again, for the new "
                              "version")
            else:
                try:
                    reloader.reload_script(SCRIPT_PLUGIN)
                except Exception as e:  # noqa: BLE001 -- the old script runs until the next login
                    self.log(f"could not have the compositor load KyprX's script again: "
                             f"{logs.what(e)}", trouble=True)
        self.state.app_version = now
        self.state.save()

    # ------------------------------------------------------------ taking KyprX off this computer

    @staticmethod
    def _only_kyprx(tx) -> None:
        """What only KyprX uses in other programs' files: the compositor script's switch, the
        settings of its tiling, the overlays' placement rules and the names
        `ensure_overlay_placement` gives them in the blur's list, and its way of writing the
        decoration's per-window list -- the entries stay, one group each (`klassy.spread`). Nobody
        else's rule or list entry is touched.

        The tiling's group goes whole, the zone layouts and arrangements and the float list with
        it: nothing but KyprX's own engine reads it. Nothing is told to read it again either -- the
        engine is in the script unloaded below, and a call into it now could only reach a script
        that is gone, or wake this daemon again on its way out."""
        klassy.spread(tx.klassy)
        if tx.kwin.get(effects.PLUGINS_GROUP, f"{SCRIPT_PLUGIN}Enabled") is not None:
            tx.kwin.delete_key(effects.PLUGINS_GROUP, f"{SCRIPT_PLUGIN}Enabled")
        for _, _, _, description, _ in OVERLAYS:
            uuid = rules.find_described(tx.rules, description)
            if uuid:
                # Every key of it: the rule is this app's from its name to its last key.
                rules.release(tx.rules, uuid, list(tx.rules.groups.get(uuid, {})))
                tx.reload_kwin = True
        tx.kwin.delete_group(effects.TILING_GROUP)
        blurred = effects.blur_classes(tx.kwin)
        if OVERLAY_CLASSES & set(blurred):
            effects.set_blur_classes(tx.kwin, [c for c in blurred if c not in OVERLAY_CLASSES])
            tx.reload_blur = True
        # Out of the running compositor, before the reconfigure: with its switch gone, the
        # reconfigure does not load it back. See `daemon/reload.py` for why unloading is needed.
        tx.session_write(f"unloadScript {SCRIPT_PLUGIN}\n",
                         lambda: reloader.unload_script(SCRIPT_PLUGIN),
                         "KyprX's watcher inside the compositor is unloaded")
        tx.reload_kwin = True

    def _own_folders(self, keep_folder: bool) -> list[tuple[str, str]]:
        """Each folder of this app's that goes, with what it holds."""
        out = [(os.path.dirname(state.CONFIG_PATH), "what KyprX remembers about this computer"),
               (CACHE_ROOT, "the wallpaper pictures and colours KyprX worked out")]
        if not keep_folder:
            out.append((snapshot.FOLDER, "your KyprX folder, with the copies of the desk"))
        return out

    @staticmethod
    def _own_files(putting_kde_back: bool) -> list[tuple[str, str]]:
        """Each file the desktop keeps in KyprX's name that goes (`STATE_CONFIG`, `STYLE_CACHE`),
        with what it holds. The style's cache only when the panel is not wearing the style -- or
        will not be, with KDE put back first: the shell reads it while it does, as KyprX's own
        colour scheme is kept while the desktop wears it. `install.sh --uninstall` takes both
        either way, once the style's own files are gone."""
        worn = theme.current().get("style") == theme.STYLE and not putting_kde_back
        out = [(STATE_CONFIG, "the folders KDE's file dialog last opened for KyprX")]
        if not worn:
            out.append((STYLE_CACHE, "Plasma's cache of KyprX's panel style"))
        return out

    @staticmethod
    def _remove_folder(path: str) -> str:
        """Remove one of this app's folders, and say what happened; "" when there was nothing.

        A link goes and what it points to stays: a KyprX folder linked into a dotfiles repository
        is somebody's repository. A folder that is itself a git repository is left, and said: the
        owner keeps the KyprX folder that way, and deleting a repository is not this app's call.
        """
        if os.path.islink(path):
            os.unlink(path)
            return f"removed the link {explain.home(path)}; what it points to is kept"
        if not os.path.exists(path):
            return ""
        if os.path.exists(os.path.join(path, ".git")):
            return f"kept {explain.home(path)}: it is a git repository, so removing it is yours"
        shutil.rmtree(path)
        return f"removed {explain.home(path)}"

    def remove_preview(self, revert: bool, keep_folder: bool) -> str:
        """What `remove_kyprx` would do, in the words a dry run uses. Writes nothing."""
        parts = []
        if revert and not self._off_desk():
            parts.append("Putting KDE back as KDE has it, as Take KyprX off this desk does:\n"
                         + self.take_off(preview=True))
        tx = writer.Transaction()
        self._only_kyprx(tx)
        parts.append("Taking away what only KyprX used:\n" + explain.preview(tx))
        held = shortcuts.script_actions_held()
        if held:
            parts.append("Out of the shortcut registry: " + ", ".join(held))
        custom = theme.custom_path()
        if os.path.exists(custom):
            worn = theme.current().get("scheme") == theme.CUSTOM and not revert
            parts.append(f"{'Kept, because the desktop is wearing it' if worn else 'Removed'}: "
                         f"KyprX's own colour scheme, {explain.home(custom)}")
        gone = [f"  {explain.home(p)} -- {what}"
                for p, what in self._own_folders(keep_folder) + self._own_files(revert)
                if os.path.lexists(p)]
        if gone:
            parts.append("Removed:\n" + "\n".join(gone))
        if keep_folder:
            parts.append(f"Kept: your KyprX folder, {explain.home(snapshot.FOLDER)}")
        parts.append("Left installed: " + ", ".join(p.name for p in requirements.PROJECTS))
        return "\n\n".join(p for p in parts if p.strip())

    def remove_kyprx(self, revert: bool, keep_folder: bool) -> dict:
        """Take KyprX off this computer, as far as this user's files go. See the module docstring.

        The answer says what was done, what was kept and the command that finishes the job. After
        a real removal the daemon stops, a moment after answering: anything it did afterwards --
        a folder pass, a window reported -- would put back part of what was just taken away. It is
        not started again unless somebody opens KyprX, which is the only thing that still can.
        """
        done: list[str] = []
        kept: list[str] = []
        if revert and not self._off_desk():
            answer = self.take_off()
            if answer.startswith("error"):
                return {"answer": answer}
            done.append("KDE is back as KDE has it; the copy of the desk from before is kept in "
                        "the KyprX folder")
        try:
            diff = writer.run(self._only_kyprx)
        except Exception as e:  # noqa: BLE001 -- said, and nothing after it is done
            self.log(f"could not take KyprX's own entries away: {logs.what(e)}", trouble=True)
            return {"answer": f"error: {e}"}
        if diff and writer.dry_run():
            self.log("would take away what only KyprX used:\n" + diff)
        done.append("KyprX's compositor script is switched off and unloaded, and its tiling's "
                    "settings and the overlays' rules are gone")
        if writer.dry_run():
            held = shortcuts.script_actions_held()
            if held:
                writer.report("would unregister KyprX's shortcuts: " + ", ".join(held))
        else:
            try:
                gone = shortcuts.unregister_script_actions()
            except Exception as e:  # noqa: BLE001 -- a key left registered is said, not fatal
                self.log(f"could not unregister KyprX's shortcuts: {logs.what(e)}", trouble=True)
                gone = []
            if gone:
                done.append("KyprX's keys are out of the shortcut registry")
        custom = theme.custom_path()
        if os.path.exists(custom):
            if theme.current().get("scheme") == theme.CUSTOM:
                kept.append(f"KyprX's own colour scheme, {explain.home(custom)}: the desktop is "
                            f"wearing it")
            elif writer.dry_run():
                writer.report(f"would remove {explain.home(custom)}")
            else:
                os.remove(custom)
                done.append(f"removed KyprX's own colour scheme, {explain.home(custom)}")
        for path, what in self._own_folders(keep_folder):
            if writer.dry_run():
                if os.path.lexists(path):
                    writer.report(f"would remove {explain.home(path)} ({what})")
                continue
            try:
                said = self._remove_folder(path)
            except OSError as e:
                self.log(f"could not remove {path}: {logs.what(e)}", trouble=True)
                kept.append(f"{explain.home(path)}: {e.strerror or e}")
                continue
            if said.startswith("kept"):
                kept.append(said)
            elif said:
                done.append(said)
        for path, what in self._own_files(revert):
            if not os.path.lexists(path):
                continue
            if writer.dry_run():
                writer.report(f"would remove {explain.home(path)} ({what})")
                continue
            try:
                os.remove(path)
            except OSError as e:
                self.log(f"could not remove {path}: {logs.what(e)}", trouble=True)
                kept.append(f"{explain.home(path)}: {e.strerror or e}")
                continue
            done.append(f"removed {explain.home(path)} ({what})")
        if keep_folder:
            kept.append(f"your KyprX folder, {explain.home(snapshot.FOLDER)}: install KyprX again, "
                        f"here or anywhere, and it is applied")
        names = [p.name for p in requirements.PROJECTS]
        kept.append(", ".join(names[:-1]) + f" and {names[-1]}: programs of their own")
        if not writer.dry_run():
            # In memory only -- the file is gone: nothing of the desk is touched again, and the
            # folder is neither written nor applied, for the moment this process has left.
            self.state.off = {"removed": True}
            self.config.paused = True
            self.log("KyprX was taken off this computer; stopping")
            self.quit_soon()
        return {"answer": "ok", "done": done, "kept": kept, "command": about.removal_command(),
                "then": about.removal_after(), "dry_run": writer.dry_run()}
