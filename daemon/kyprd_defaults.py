"""*Restore KyprX's defaults*: every value `daemon/defaults.py` declares, put back in one go. And
the question the settings window asks the first time it opens on an install whose first start put
nothing of KyprX's look on: put it on, or keep the person's own.

The title bar's settings among them, which no tab writes any more, and this app's own settings and
colours. `restore_defaults` says what it leaves alone -- windows set by hand, shortcuts, profiles --
and why its three writes come in the order they do. A preview builds the change and throws it away.
`look_offer` says whether the question is due and what the look would change; `answer_look` takes
the answer.

The daemon's state it reads or writes, all of it created in `Daemon.__init__`: `config`, `state`.
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
        the most expensive kind of surprise. It does not touch shortcuts either -- a key is
        somebody's choice, the tiling's among them, and rebinding them is not restoring anything.
        Nor the arrangements, nor the profiles: what somebody built or kept under a name is
        theirs, not an opinion of this app's.

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
        wanted = self.transparency_targets(previous) if strength != previous else []
        was_paused = self.config.paused
        restored = Config.from_dict(asdict(self.config))
        restored.defaults = Defaults()
        restored.transparency = strength
        restored.paused = defaults.OWN["paused"]
        restored.notify = defaults.OWN["notify"]
        restored.auto_colour = defaults.OWN["auto_colour"]
        restored.wallpaper = dict(defaults.WALLPAPER)
        held = None

        def build(tx):
            nonlocal held
            note_reloads(tx, write_declared(tx, defaults.SETTINGS))
            write_declared_colours(tx, defaults.BUTTON_COLOURS)
            self.strike_transparency(tx, wanted, strength, previous)
            # The ticks the restore leaves behind. At the declared strength -- below 100, where
            # every tick is deducible from the rule it was just written into -- that is an empty
            # list, which is the restore putting the held ticks back where deduction can find
            # them; were the declared strength ever 100, the windows the restore struck would be
            # the ones the list has to hold. Worked out in the build and never before it, for the
            # reason `ticks_at_100` gives.
            held = (self.ticks_at_100(
                        tx, {w.window_class: (True, w.resource_name) for w in wanted},
                        self.config.ticked_at_100)
                    if self.at_full(strength) else [])

        if preview:
            import explain
            tx = writer.Transaction()
            build(tx)
            if held is not None:
                restored.ticked_at_100 = held
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
        if held is not None:
            restored.ticked_at_100 = held
            self.keep_ticks(held)
        self.config = restored
        self.config.save()
        if was_paused:
            # The catching-up `SetSettings` does when that switch goes back on: every window that
            # waited while new windows were being left alone gets the defaults now.
            self.apply_defaults()
        answer = self.set_theme(dict(defaults.COLOURS), from_wallpaper=None)
        # KyprX's look is on now, and colours that went on have said so already. When they failed
        # it was still asked for, so the question about it -- still due when this is pressed
        # before the settings window ever asked, or answered *Keep my look* before -- is answered
        # by it all the same.
        self.state.look_went_on()
        if answer.startswith("error"):
            return ("partial: everything went back but the colours, which did not: "
                    + answer[len("error: "):])
        return "ok"

    # ------------------------------------------------------------ KyprX's look, the first time

    def _look_build(self, tx) -> None:
        """The outline half of KyprX's look, which `set_theme` does not write: amber round the
        active window, as `defaults.SETTINGS` declares it."""
        note_reloads(tx, write_declared(tx, defaults.LOOK_OUTLINE))

    def look_offer(self) -> dict:
        """Whether the settings window, opening, asks about KyprX's look -- `due` -- and what
        putting it on would change, in plain words -- `changes`, "" unless due. Writes nothing.

        Due only on an install whose first start put nothing of the look on and that was not asked
        since (`state.LOOK_DUE`), and never while KyprX is off the desk, which is KDE's own look
        on purpose. The words are worked out the way a dry run works them out: the outline's keys
        on a transaction that is never committed, then `set_theme`'s own preview of the colours --
        the global theme, the scheme, the panel's style and the accent -- with no line that is
        only a refusal, as `restore_defaults` filters its preview."""
        due = self.state.look == state.LOOK_DUE and not self.state.off
        if not due:
            return {"due": False, "changes": ""}
        import explain
        tx = writer.Transaction()
        self._look_build(tx)
        lines = [explain.preview(tx),
                 self.set_theme(dict(defaults.COLOURS), from_wallpaper=None, preview=True)]
        return {"due": True,
                "changes": "\n".join(line for line in lines
                                     if line and not line.startswith("error"))}

    def answer_look(self, take: bool) -> str:
        """The answer to the question `look_offer` says is due: "ok", "partial: …" or "error: …".
        Either answer is remembered in `state.json`, so the question is not asked again.

        **Keep** (`take` false) changes nothing on the desk: the person's own look stays, and the
        Colours box says so instead of warning about it (`ThemePart.theme`, `kept_own_look`).

        **Take** puts KyprX's look on, in the order `restore_defaults` keeps and for its reasons --
        a copy of the desk first, and nothing at all without one, so *Go back to a copy…* puts back
        what KyprX writes (not a global theme or colours of the desk's own, which a copy does not
        record: KNOWN-ISSUES says so); then the amber outline, in a transaction of its own; then
        the colours through
        `set_theme`, with `from_preset` left off so the outline just written stands. A failure in
        the colours alone answers `partial:`, and the answer is still remembered: the person said
        yes, and the Colours box is where the colours are put right. Refused while KyprX is off
        the desk, whose look is KDE's own until *Put my setup back*.
        """
        if not take:
            self.state.look = state.LOOK_OWN
            self.state.save()
            self.log("kept the desk's own look: KyprX's was offered, and declined")
            return "ok"
        if self.state.off:
            return "error: KyprX is off this desk; Put my setup back first"
        if not self.take_snapshot("before putting KyprX's look on"):
            return "error: a copy of the desk could not be kept first, so nothing was changed"
        try:
            diff = writer.run(self._look_build)
        except Exception as e:  # noqa: BLE001
            self.log(f"could not put KyprX's outline on: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        if writer.dry_run() and diff:
            self.log("would have written:\n" + diff)
        answer = self.set_theme(dict(defaults.COLOURS), from_wallpaper=None)
        # Colours that went on have answered it already (`State.look_went_on`); saved again only
        # when they did not.
        if self.state.look != state.LOOK_KYPRX:
            self.state.look = state.LOOK_KYPRX
            self.state.save()
        if answer.startswith("error"):
            return ("partial: the window outline went on, but the colours did not: "
                    + answer[len("error: "):])
        return "ok"
