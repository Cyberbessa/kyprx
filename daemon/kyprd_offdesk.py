"""*Take KyprX off this desk*, and *Put my setup back*: plain KDE for a while, with the setup kept.

Taking it off keeps a copy of the desk that is never pruned, deletes what KyprX wrote rather than
writing anything of its own, and puts KDE's own Breeze on; putting it back restores that copy. While
it is off, `state.json` says so, new windows are left alone, and the KyprX folder is neither written
nor applied. MAP.md has what exactly is deleted; the methods have why.

The daemon's state it reads or writes, all of it created in `Daemon.__init__`: `config`, `state`.
"""

from __future__ import annotations

import os
from dataclasses import asdict

import defaults
import effects
import folder
import klassy
import logs
import rules
import snapshot
import state
import theme
import writer
from declared import _SOURCES


class OffDeskPart:
    """KyprX off the desk, and back on."""

    # ------------------------------------------------------------ taking KyprX off the desk

    #: The keys of a decoration override this app writes for a window, and what "not hiding"
    #: reads as -- what taking KyprX off leaves behind when somebody else's settings share an entry.
    KYPRX_OVERRIDE_KEYS = ("HideTitleBar", "ExceptionBorder", "BorderSize", "ExceptionPreset")

    def take_off(self, preview: bool = False) -> str:
        """Take KyprX off this desk: pure KDE, the owner's choice -- see `defaults.TAKE_OFF_PLUGINS`.

        **Only what is this app's goes.** Every key `defaults.SETTINGS` declares is deleted, so the
        decoration, the blur, the animation, the tiling and focus are each back on their own
        defaults. From every window rule, this app's keys -- the forced title bar and the opacity
        -- and a rule left doing nothing goes; one with somebody's activity or desktop in it stays.
        From every decoration override that is a window's own entry, this app's keys, and an entry
        left with nothing of anybody else's goes; the preset that drops the outline goes after them.
        The windows this app speaks for leave the three per-window lists. The three plugins it
        switches on are switched off. Then KDE's own Breeze global theme, with no colour of this
        app's, keeping every other choice the global theme would have taken (`theme.pure_plan`).

        **And then KyprX stops.** New windows are left alone, and the KyprX folder is frozen --
        neither written nor applied -- so it keeps the setup. A copy of the desk is kept first and
        never pruned: *Put my setup back* restores it exactly, then applies whatever arrived in the
        folder meanwhile. `preview` writes nothing and returns what would change.
        """
        managed = self.managed_classes()
        declared = defaults.SETTINGS

        def build(tx):
            for group, keys in declared["klassy"].items():
                for key in keys:
                    tx.klassy.delete_key(group, key)
            # The button colours are not touched: this app declares only that there should be no
            # override on three buttons, and never writes one -- so there is nothing of its own there
            # to take away, and whatever is there is somebody's.
            kept = []
            for entries in klassy.read_groups(tx.klassy):
                if self._own_entry_class(entries, managed):
                    others = {k: v for k, v in entries.items()
                              if k not in self.OVERRIDE_COLUMNS
                              and str(v) != self.OVERRIDE_SHIPPED.get(k)}
                    if not others:
                        continue
                    entries = dict(entries, HideTitleBar=str(klassy.TITLEBAR_NEVER),
                                   ExceptionBorder="false", ExceptionPreset="")
                kept.append(entries)
            if kept != klassy.read_groups(tx.klassy):
                klassy.write_groups(tx.klassy, kept, together=False)
            # One group per entry, as the decoration's own settings write it: what is left is
            # somebody's, and KyprX's way of writing the list is not (`klassy.spread`).
            klassy.spread(tx.klassy)
            own_preset = klassy.PRESET_PREFIX + klassy.OUTLINE_OFF_PRESET
            if not any(g.get("ExceptionPreset") == klassy.OUTLINE_OFF_PRESET for g in kept):
                tx.presets.delete_group(own_preset)
            for source, groups in declared.items():
                if source in ("klassy", "plugins"):
                    continue
                for _, keys in groups.items():
                    for key in keys:
                        tx.kwin.delete_key(_SOURCES[source], key)
            for _, group, list_key in self.KWIN_PARTS:
                if not list_key or tx.kwin.get(group, list_key) is None:
                    continue
                values, sep = self._split_list(tx.kwin.get(group, list_key), list_key)
                left = [v for v in values if v not in managed]
                if left != values:
                    if left:
                        tx.kwin.set(group, list_key, sep.join(left))
                    else:
                        tx.kwin.delete_key(group, list_key)
            for plugin in defaults.TAKE_OFF_PLUGINS:
                if effects.plugin_enabled(tx.kwin, plugin):
                    effects.set_plugin_enabled(tx.kwin, plugin, False)
            for uuid, entries in rules.read(tx.rules):
                if str(entries.get("Description", "")).startswith(rules.PREFIX):
                    rules.release(tx.rules, uuid, rules.TITLEBAR_KEYS + rules.OPACITY_KEYS)
            tx.reload_kwin = tx.reload_colours = tx.reload_blur = tx.reload_tiling = True
            now = theme.current()
            # As before any global theme: see `klassy.LOOK_AND_FEEL`. Without it the decoration
            # rewrote its whole config when Breeze went on, and again, over the copy just put back,
            # when *Put my setup back* brought Klassy's theme back.
            klassy.settle_look_and_feel(tx.klassy, theme.pure_package(now))
            for step in theme.pure_plan(now):
                tx.session_write(*step)

        if preview:
            import explain
            tx = writer.Transaction()
            build(tx)
            paused = dict(asdict(self.config), paused=True)
            lines = [explain.preview(tx),
                     explain.own_preview(state.CONFIG_PATH, asdict(self.config), paused)]
            return "\n".join(x for x in lines if x)

        if self._off_desk():
            return "error: KyprX is already off this desk"
        copy = self.take_snapshot("before taking KyprX off this desk", pinned=True)
        if not copy:
            return "error: a copy of the desk could not be kept first, so nothing was changed"
        self._folder_due()      # the folder carries the setup as it is, before it is frozen
        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001
            self.log(f"could not take KyprX off the desk: {logs.what(e)}", trouble=True)
            return (f"error: {e} -- part of it may have gone through; Put my setup back, or Go "
                    f"back to a copy…, puts the desk back")
        if writer.dry_run() and diff:
            self.log("would have written:\n" + diff)
        self.config.paused = True
        self.config.save()
        self.state.off = {"copy": copy}
        self.state.save()
        self.log(f"{'would have taken' if writer.dry_run() else 'took'} KyprX off this desk; the "
                 f"copy of the desk from before is {copy}")
        return "ok"

    def put_back(self) -> str:
        """Put the setup back after `take_off`: the copy kept before it, exactly -- the decoration,
        every rule, the colours, the global theme, whether new windows were being adjusted --
        and then the KyprX folder unfrozen, so whatever arrived in it meanwhile is applied the way
        any arrival is. A copy of the desk as it is now is kept first, like every big change."""
        copy = (self.state.off or {}).get("copy", "")
        desk = snapshot.load(copy)
        trouble = snapshot.why_not(desk)
        if trouble:
            return f"error: the copy taken before KyprX was taken off cannot be put back: {trouble}"
        if not self.take_snapshot("before putting the setup back"):
            return "error: a copy of the desk could not be kept first, so nothing was changed"
        answer = self.restore_desk(desk)
        if answer.startswith("error"):
            return answer
        self.state.off = {}
        self.state.save()
        self._folder_due()
        return answer

    def leave_off(self) -> None:
        """Something else put KyprX back on the desk -- *Restore defaults*, going back to a copy,
        a backup file. The folder is unfrozen, and first kept whole beside the newest copy of the
        desk: from here on the daemon writes the desk into it again, and the setup it kept while
        KyprX was off must not be written over without a copy."""
        if not self.state.off:
            return
        texts, _ = folder.read_texts()
        newest = next((c["name"] for c in snapshot.listing() if not c["in_memory"]), "")
        if texts and newest and not writer.dry_run():
            try:
                kept = os.path.join(snapshot.DIRECTORY, newest, "folder")
                os.makedirs(kept, exist_ok=True)
                for name, text in texts.items():
                    with open(os.path.join(kept, name), "w", encoding="utf-8") as fh:
                        fh.write(text)
            except OSError as e:
                self.log(f"could not keep the folder beside {newest}: {logs.what(e)}", trouble=True)
        self.state.off = {}
        self.state.save()
