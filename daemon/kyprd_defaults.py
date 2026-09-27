"""*Restore KyprX's defaults*: every value `daemon/defaults.py` declares, put back in one go.

The title bar's settings among them, which no tab writes any more, and this app's own settings and
colours. `restore_defaults` says what it leaves alone -- windows set by hand, shortcuts, profiles --
and why its three writes come in the order they do. A preview builds the change and throws it away.

The daemon's state it reads or writes, all of it created in `Daemon.__init__`: `config`.
"""

from __future__ import annotations

from dataclasses import asdict

import defaults
import logs
import state
import writer
from declared import note_reloads, write_declared, write_declared_colours
from state import Config, Defaults


class DefaultsPart:
    """Putting back what KyprX declares."""

    # ------------------------------------------------------------ KyprX's defaults

    def restore_defaults(self, preview: bool = False) -> str:
        """Put every declared setting back -- this app's own among them, and the colours.

        What it deliberately does **not** do is as much of the promise as what it does. It does not
        touch a window somebody set by hand: those choices live in the config files as facts, and a
        button called "restore defaults" that quietly undid a dozen deliberate decisions would be
        the most expensive kind of surprise. It does not touch shortcuts either -- the tiling keys
        belong to the tiling script, not to this app, and rebinding them is not restoring anything.
        Nor the profiles: a look somebody kept under a name is theirs, not an opinion of this app's.

        **A copy of the desk first**, and nothing at all without one: this writes every value this
        app has an opinion about, and *Go back* on the Settings tab is how that is undone. `preview`
        writes nothing -- not even the copy -- and returns what would change, in plain words.

        **Three writes and not one**, in the order `apply_look` keeps and for the same reasons.

        The declared keys and the strength's restrike share a transaction, so the decoration and
        every window rule go up on one compositor reconfigure rather than two.

        This app's own settings are saved next, before the colours, so that a failure among the
        desktop's tools leaves the file where it was asked to be rather than halfway.

        The colours go last, through `set_theme`, which stops the screen for a second or two on its
        own -- and with `from_preset` left at its default, which is not an omission. This is not
        somebody choosing a theme: the outline's colour is declared above, in `SETTINGS`, and a
        preset putting its own there would throw that declaration away every time this is pressed.

        Run twice it writes nothing the second time, because every key already reads the way the
        declaration wants and `write_declared` skips those. The exception is the strength, which is
        held in memory: the first call moves it, and from the second on there is nothing to
        restrike. `scripts/drive.py` compares the second call with the third for that reason.
        """
        previous = int(self.config.transparency)
        strength = defaults.TRANSPARENCY
        # Read before anything is written, for the reason `transparency_targets` gives: a read
        # inside the transaction that writes would have each row see the half-finished work of the
        # row before it.
        wanted = self.transparency_targets() if strength != previous else []
        was_paused = self.config.paused
        restored = Config.from_dict(asdict(self.config))
        restored.defaults = Defaults()
        restored.transparency = strength
        restored.paused = defaults.OWN["paused"]
        restored.notify = defaults.OWN["notify"]
        restored.auto_colour = defaults.OWN["auto_colour"]
        restored.wallpaper = dict(defaults.WALLPAPER)

        def build(tx):
            note_reloads(tx, write_declared(tx, defaults.SETTINGS))
            write_declared_colours(tx, defaults.BUTTON_COLOURS)
            self.strike_transparency(tx, wanted, strength, previous)

        if preview:
            import explain
            tx = writer.Transaction()
            build(tx)
            lines = [explain.preview(tx),
                     explain.own_preview(state.CONFIG_PATH, asdict(self.config),
                                         asdict(restored))]
            if was_paused and self.pending():
                lines.append(f"  the {len(self.pending())} window(s) that waited while new "
                             f"windows were left alone get the defaults")
            lines.append(self.set_theme(dict(defaults.COLOURS), from_wallpaper=None,
                                        preview=True))
            return "\n".join(line for line in lines if line and not line.startswith("error"))

        if not self.take_snapshot("before restoring KyprX's defaults"):
            return "error: a copy of the desk could not be kept first, so nothing was changed"
        self.leave_off()
        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001
            self.log(f"could not restore the defaults: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        if diff and wanted:
            self.log(f"{'would set ' if writer.dry_run() else ''}"
                     f"transparency={strength}% on up to {len(wanted)} window(s)")
        if writer.dry_run() and diff:
            self.log("would have written:\n" + diff)
        self.config = restored
        self.config.save()
        if was_paused:
            # The catching-up `SetSettings` does when that switch goes back on: every window that
            # waited while new windows were being left alone gets the defaults now.
            self.apply_defaults()
        answer = self.set_theme(dict(defaults.COLOURS), from_wallpaper=None)
        if answer.startswith("error"):
            return ("partial: everything went back but the colours, which did not: "
                    + answer[len("error: "):])
        return "ok"
