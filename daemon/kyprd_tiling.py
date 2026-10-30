"""KyprX's own tiling as the daemon serves it: the answer the compositor script asks for, the state
the settings window shows, and the key that switches automatic tiling.

**The answer** (`tiling_answer`) is what `Tiling()` on `/Windows` returns. The compositor script
asks for it when it loads, at every `KyprXInventory`, and at every `KyprXTiling` the daemon invokes
after a write (`reload.tell_tiler`), and applies it only when its text differs from the last one it
applied. It is read from disk -- `kwinrc` as saved, and whether KyprX is off the desk as
`state.json` says -- in a dry run too, so the engine is told what the desk really is. The one thing
a dry run changes in the engine is said in the answer (`dryRun`): it makes and removes no desktop,
because the compositor writes `kwinrc [Desktops]` the moment one comes or goes. `tiling.resolve`
reads the group; whether KyprX is off the desk is read here, because it is not in the group.

**The automatic-tiling key** (`toggle_automatic_tiling`) is what `ToggleAutomaticTiling()` on
`/Windows` does: the compositor script's Toggle Automatic Tiling key asks for it, and this writes
`autoTiling` the other way, the one key in the group, as the Tiling tab's box does. The engine
switches only when the answer after that write reaches it -- never by itself, which the next
answer would undo -- so a dry run, which writes nothing and tells the tiling nothing, switches
nothing either.

The daemon's state it reads or writes, all of it created in `Daemon.__init__`: `manager`, `state`
(`off`), `_script_version`.
"""

from __future__ import annotations

import json
import os

import about
import effects
import kconfig
import state
import tiling
import writer
from kyprd_names import SCRIPT_PLUGIN

def installed_script_version() -> str:
    """The version of the compositor script installed here (`KPlugin.Version` in its
    `metadata.json`): the one in the first data folder the compositor looks in, else the one in
    this tree's `kwin-script/`, else "".

    What the version the running script says is held against. The compositor keeps what it
    compiled of a declarative script for the whole session (the head of
    `kwin-script/contents/ui/main.qml` has the finding), so after an update the script running is
    the one from before until the next login, and the Tiling tab says so ("old-script").
    """
    for path in (about.data_path(f"kwin/scripts/{SCRIPT_PLUGIN}/metadata.json"),
                 os.path.join(about.TOP, "kwin-script", "metadata.json")):
        if not path:
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                return str(((json.load(fh) or {}).get("KPlugin") or {}).get("Version") or "")
        except (OSError, ValueError, AttributeError):
            continue
    return ""


class TilingPart:
    """KyprX's tiling: what the engine is told, what the window is told, and the key."""

    # ------------------------------------------------------------ the answer

    def tiling_answer(self, version: str) -> dict:
        """What `Tiling(version)` answers the compositor script: `tiling.resolve` of the group as
        saved, with `tiling` false while KyprX is off the desk.

        `version` is the script's own (`SCRIPT_VERSION` in its `main.qml`), kept for the state the
        settings window shows.
        """
        self._script_version = str(version or "")
        reading = self._tiling_reading()
        answer = tiling.resolve(reading["group"], off=reading["off"])
        # Whether this daemon writes nothing. The one thing a dry run changes in the engine: it
        # makes and removes no desktop, because the compositor writes `kwinrc [Desktops]` the
        # moment one comes or goes, and that write goes through no door of this app's
        # (`kwin-script/contents/code/engine.mjs`, the overflow).
        answer["dryRun"] = writer.dry_run()
        return answer

    def tiling_state_now(self, kwin=None) -> str:
        """Where the tiling stands, for the settings window: one of `tiling.STATES`.

        Read the way `tiling_answer` reads, from disk, so the window says what the engine is
        doing. `kwin` is `kwinrc` when the caller has it loaded already.
        """
        reading = self._tiling_reading(kwin)
        return tiling.state_of(reading["group"], off=reading["off"],
                               script_version=self._script_version,
                               tree_version=installed_script_version() or self._script_version)

    def tiling_on_now(self, kwin=None) -> bool:
        """Whether KyprX's engine is tiling, as `tiling_answer` would say it -- the Windows tab's
        rows and `Diagnostics` ask, so a tick in the Float column is offered only where it does
        something. `kwin` as for `tiling_state_now`."""
        reading = self._tiling_reading(kwin)
        return tiling.runs(reading["group"], off=reading["off"])

    @staticmethod
    def _tiling_reading(kwin=None) -> dict:
        """Everything the answer and the state are read from: the group as saved, and whether KyprX
        is off the desk as `state.json` says."""
        kwin = kwin if kwin is not None else kconfig.KConfig(writer.KWINRC)
        return {"group": dict(kwin.groups.get(effects.TILING_GROUP, {})),
                "off": bool(state.saved_off())}

    # ------------------------------------------------------------ the automatic-tiling key

    def toggle_automatic_tiling(self) -> str:
        """Automatic tiling switched the other way, for the compositor script's Toggle Automatic
        Tiling key: `autoTiling` in `[Script-kyprx]` read as the engine reads it
        (`tiling.value_of`, so a key that is absent reads on) and written as its opposite, `true`
        or `false`, in one transaction through `writer`, with the tiling told to ask for its
        settings again (`reload.tell_tiler`). The answer to that call is what switches it in the
        engine, and what has the engine's name card say so (`autoSaid` in `engine.mjs`). The
        Tiling tab's box follows at the `Changed` this ends with, and the KyprX folder with it.

        "ok", or "error: ..." with the reason, which the script does not read and the log says:
        refused while KyprX is off the desk -- *Put my setup back* comes first -- and while KyprX's
        engine is not tiling (`tiling_on_now`), with the tiling switched off. There the key would
        change a setting nothing acts on, and the engine, not tiling, says nothing.

        A dry run writes nothing and tells the tiling nothing, so the engine never switches and
        no card shows: the log says what would have been written.
        """
        if self.state.off or state.saved_off():
            self.log("automatic tiling was not switched by its key: KyprX is off this desk")
            return "error: KyprX is off this desk"
        if not self.tiling_on_now():
            self.log("automatic tiling was not switched by its key: KyprX's tiling is not running")
            return "error: KyprX's tiling is not running"
        switched: dict[str, bool] = {}

        def build(tx):
            # `writer.run` builds again from the start when somebody else wrote the file meanwhile.
            switched.clear()
            group = dict(tx.kwin.groups.get(effects.TILING_GROUP, {}))
            on = not tiling.value_of(group, "autoTiling")
            tx.kwin.set(effects.TILING_GROUP, "autoTiling", "true" if on else "false")
            tx.reload_tiling = True
            switched["on"] = on

        diff = writer.run(build)
        words = "on" if switched.get("on") else "off"
        if writer.dry_run():
            self.log(f"would have switched automatic tiling {words} by its key")
            if diff:
                self.log("would have written:\n" + diff)
            return "ok"
        self.log(f"automatic tiling switched {words} by its key")
        self.manager.changed()
        return "ok"
