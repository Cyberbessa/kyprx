"""The desktop's colours: the mode, the preset, a colour of your own and how far it soaks in.

`theme` is what the Appearance tab's Colours box draws from, and `set_theme` is the road to a change
of colours, whoever asks -- the box, a profile, *Restore defaults*, a wallpaper handing its colour
over. The one exception is taking KyprX off the desk, which puts KDE's own Breeze on through
`theme.pure_plan` (`daemon/kyprd_offdesk.py`). The applying itself is done by the desktop's own
tools, in the order `daemon/theme.py` explains, each as a session write;
`_colour_came_from_the_wallpaper` says whether the colour being applied is the one the wallpaper
gives, which decides whether the window outline follows it. `_step_name` names each of those steps
for the stopwatch in `daemon/clock.py`.

The daemon's state it reads or writes, all of it created in `Daemon.__init__`: `config`.
"""

from __future__ import annotations

import clock
import kconfig
import klassy
import logs
import previews
import theme
import wallcolour
import wallpaper
import writer


def _step_name(description: str) -> str:
    """The name a session write's description carries, for the stopwatch.

    A description is written to read like the diff it is not -- `--- your own colour`, then the
    tool, then the two values. The first line is the name of the step.
    """
    first = description.splitlines()[0] if description else ""
    return first[4:].strip() if first.startswith("--- ") else "step"


class ThemePart:
    """The desktop's colours, read and changed."""

    # ------------------------------------------------------------ colours

    def theme(self) -> dict:
        """What the desktop is wearing, what there is to choose from, and what is in the way.

        Trouble is a sentence rather than an exception, the same as the wallpaper's: a preset
        whose colour scheme is not installed is a row the interface greys out with the reason on
        it, not a reply the interface has to recover from.

        Each preset carries its own swatch, read out of the scheme's file rather than declared
        anywhere here, so what is drawn is what would be applied.
        """
        now = theme.current()
        #: What the wallpaper would give, so the tab can say whether the colour on screen still
        #: comes from it. Worked out only when the feature is on, because for a video the first
        #: answer costs a second and a half of ffmpeg -- cached after that, per file.
        offered, why = "", ""
        if self.config.auto_colour and now["mode"] in theme.MODES:
            try:
                state = wallpaper.snapshot()
            except wallpaper.WallpaperError as e:
                why = f"the shell did not say what the wallpaper is: {e}"
            else:
                target = wallpaper.showing(state)
                if not target:
                    why = "the shell is not showing a wallpaper this can read"
                else:
                    #: Read from the cache and never worked out here. This method is called to
                    #: draw the Appearance tab, on the thread the window is drawn on -- and a
                    #: video's first answer cost a second and a half of ffmpeg, spent with the
                    #: window sitting there. Now the tab is drawn at once and told again when the
                    #: answer exists.
                    ready = wallcolour.known_colour(target, now["mode"])
                    if ready is None:
                        self.warm_colour(target, now["mode"])
                        why = "working out what colour this wallpaper gives — one moment"
                    else:
                        offered = ready
                        why = wallcolour.trouble(target)
        #: One reading of the decoration's config for both answers below. Two readings were two
        #: chances to disagree about one file, and they took it: one asked the active state only.
        outline = kconfig.KConfig(writer.KLASSYRC)
        return {
            "auto_colour": self.config.auto_colour,
            #: Whether the window outline is set to a style that reads a colour of ours -- either
            #: state, which is the same question `outline_colour` answers with a colour. Only then
            #: can a colour reach it, and the tab says so rather than leaving it to be noticed.
            "outline_follows": klassy.outline_takes_colour_anywhere(outline),
            #: And the colour it is drawn in right now. The tab compares it against `accent` to
            #: tell the two states apart -- wearing the colour the wallpaper handed over, or one of
            #: its own. It is read here and never sent back: the outline is where the colour lands,
            #: never where it comes from.
            "outline_colour": klassy.outline_colour(outline),
            #: The colour the wallpaper offers. Equal to `accent` means the one on screen is still
            #: the wallpaper's; different means somebody has since chosen their own, and that one
            #: stands until the next wallpaper.
            "from_wallpaper": offered,
            "wallpaper_trouble": why,
            "mode": now["mode"],
            "preset": now["preset"],
            "accent": now["accent"],
            "tint": now["tint"],
            "default_tint": theme.DEFAULT_TINT,
            "presets": [{"id": p.id, "name": p.name, "mode": p.mode, "note": p.note,
                         "trouble": theme.available(p), "swatch": theme.swatch(p.scheme)}
                        for p in theme.PRESETS],
            "trouble": theme.invariants(now),
        }

    def set_theme(self, payload: dict, trace=None, from_wallpaper: str | None = "",
                  from_preset: bool = False, preview: bool = False) -> str:
        """Put this mode, this preset and this colour on the desktop, in that order and no other.

        `from_wallpaper` says where the colour came from, and only the window outline reads it: the
        name of the wallpaper that gave it, `""` for "work it out from what is on screen", or
        `None` for a caller that knows this is nobody's wallpaper. It is a Python argument and not
        a field of the payload, so nothing outside this process can set it -- see
        `_colour_came_from_the_wallpaper` for why it is asked rather than believed.

        The read happens **before** the transaction, the same split `set_wallpaper` makes -- and
        here it earns more than it does there. Every step is one of the desktop's own tools, each
        of them a Qt program that repaints the whole session; asking for what is already on screen
        has to cost nothing at all, not merely look like it did.

        `preview` builds the same transaction and returns what it would do in plain words, writing
        nothing -- what the question before *Restore defaults* shows. Empty when nothing would move.
        """
        mode = str(payload.get("mode") or "")
        if mode not in theme.MODES:
            return f"error: {mode or '(none)'} is not a mode"
        named = str(payload.get("preset") or "")
        chosen = theme.preset(named)
        if named and chosen is None:
            return f"error: there is no preset called {named}"
        if chosen is None or chosen.mode != mode:
            chosen = theme.default_preset(mode)
        why = theme.available(chosen)
        if why:
            return f"error: {why}"
        accent = str(payload.get("accent") or "")
        if accent and not theme.is_colour(accent):
            return f"error: {accent} is not a colour"
        try:
            tint = float(payload.get("tint") or 0)
        except (TypeError, ValueError):
            return "error: the tint has to be a number"
        tint = min(max(tint, 0.0), 1.0)
        use_custom = bool(accent) and tint > 0

        now = theme.current()
        #: **The window outline is the wallpaper's to move, and nobody else's.** The direction is
        #: unchanged and still the only one there is -- wallpaper -> the colour -> the outline, and
        #: nothing anywhere reads the outline to decide what the colour is -- but a colour chosen
        #: in the Colours box is yours and stops there. *Take the theme colour*, on the Outline
        #: section, is how an outline is put in step by hand.
        #:
        #: Two conditions, and both carry weight. The colour has to have **moved**, which is what
        #: keeps re-applying what is already on screen free. And it has to be the **wallpaper's**
        #: colour, asked of the cache rather than taken on trust from whoever called -- measured,
        #: that second condition is what a colour typed by hand stops paying: the desktop's own
        #: tools stop the screen for about 1.35 s either way, and the decoration's pair adds about
        #: 1.7 s on top of it whenever the outline moves. Measured in one sitting with twelve
        #: windows open: a wallpaper handing its colour over stopped the screen twice, 1.71 s and
        #: 1.37 s; two colours typed into the box stopped it for 1.36 s and 1.34 s, each with no
        #: second gap.
        moved = bool(accent) and now["accent"] != accent
        outline = moved and self._colour_came_from_the_wallpaper(accent, mode, from_wallpaper)
        #: **A preset chosen puts its own colour on the window outline**, and that is the second
        #: road to the ring. The first, above, is the wallpaper's and is untouched by this. Two
        #: conditions again, and both carry their weight: the preset has to have **moved**, so
        #: re-applying what is already on screen stays free, and somebody has to have **chosen**
        #: it.
        #:
        #: This one is told rather than asked, and the difference from `from_wallpaper` is the
        #: point rather than an inconsistency. That one can be asked because there is a fact
        #: outside this process to consult -- what colour the wallpaper on screen gives. "Somebody
        #: picked a theme" has no such fact anywhere: a profile being loaded, a settings file being
        #: imported and *Restore defaults* all arrive here with a preset that differs from the one
        #: in force, and each of the three carries outline keys of its own, written moments
        #: earlier, that this would throw away -- a profile that does not load, a backup that does
        #: not restore. So it is a Python argument like `from_wallpaper`, nothing outside this
        #: process can set it, and the default is the safe one: a caller that says nothing moves no
        #: outline.
        from_preset = from_preset and now["preset"] != chosen.id
        preset_colour = theme.selection_colour(chosen.scheme) if from_preset else ""

        wanted = {"mode": mode, "preset": chosen.id, "accent": accent, "tint": tint}

        def build(tx):
            # The stopwatch goes on the transaction so that the reloads, which happen inside
            # `commit` rather than here, are timed with everything else.
            tx.trace = trace
            # The derived scheme is written first, inside the transaction, so that a dry run shows
            # it as the diff it would be -- and so that in a real run it is on disk before the
            # tool that applies it runs, which `commit()` guarantees by saving files before it
            # runs anything.
            with clock.step(trace, "scheme"):
                rewritten = theme.ensure_custom(tx, chosen, tint) if use_custom else False
            if outline and klassy.set_outline_colour(tx.klassy, accent):
                # An ordinary file write in the transaction that is already being built -- the
                # decoration's own config is one of the four this app owns.
                #
                # **Both reloads, and both are needed.** The reconfigure makes the decoration
                # re-read klassyrc; the colour cache broadcast makes it rebuild the colours it
                # keeps from what it read. Measured on the screen: with the reconfigure alone a
                # ten-pixel outline in an unmistakable colour did not appear at all -- nought
                # pixels of it in a full-screen capture, and 88,172 once the colour cache signal
                # followed. It is also
                # the expensive half of a wallpaper change -- about 1.8 s of frozen screen for the
                # pair, against a tenth of a second for everything this app computes itself. See
                # `reload.invalidate_colour_cache`.
                tx.reload_kwin = True
                tx.reload_colours = True
            # `elif`, and the precedence is the wallpaper's. In practice the two cannot both be
            # true -- choosing a preset drops the colour of your own, in `ThemeBox._swatch_picked`,
            # so there is no accent left to have moved -- and saying which wins here costs a word,
            # where finding out the day one of them changes costs an afternoon.
            elif preset_colour and klassy.take_outline_colour(tx.klassy, preset_colour):
                # The same pair, for the same measured reason as the branch above.
                tx.reload_kwin = True
                tx.reload_colours = True
            steps = list(theme.plan(now, wanted, scheme_written=rewritten))
            # Before a global theme goes on, the decoration is told its settings already belong to
            # it -- otherwise it loads a bundled preset over every key of its config the moment it
            # notices. See `klassy.LOOK_AND_FEEL`; a switch between dark and light is one.
            klassy.settle_look_and_feel(tx.klassy, theme.package_after(now, wanted))
            for description, action, plain in steps:
                # Each step timed under the name its own description carries, so the log line says
                # which of the desktop's tools took the time rather than that something did.
                tx.session_write(description,
                                 trace.wrap(_step_name(description), action) if trace else action,
                                 plain)
            if steps:
                # The file manager's pictures of folders were drawn in the colour of the day they
                # were made, and are kept until the folder itself changes -- see `previews`. Last,
                # after the tools have put the new colours in force, so what is drawn again is drawn
                # in them; and only when a step above means the colours actually moved, so that
                # re-applying what is on screen stays a transaction with nothing in it.
                kept = previews.folder_previews()
                forget = lambda kept=kept: previews.forget_and_announce(kept)  # noqa: E731
                tx.session_write(previews.describe(kept),
                                 trace.wrap("folder previews", forget) if trace else forget,
                                 previews.plain(kept))

        if preview:
            # Imported here, as `writer` does: the words are only wanted when somebody asks.
            import explain
            tx = writer.Transaction()
            build(tx)
            return explain.preview(tx)
        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001 — the interface says what went wrong, and stays up
            self.log(f"failed on the colours: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        if writer.dry_run() and diff:
            self.log("would have written:\n" + diff)
        return "ok"

    def _colour_came_from_the_wallpaper(self, accent: str, mode: str,
                                        target: str | None = "") -> bool:
        """Is this colour the one the wallpaper gives?

        The whole of the outline rule rests on this question, and it is asked rather than asserted:
        a flag set by whoever calls is a flag somebody forgets, and the flag this replaces was
        forgotten -- only the wallpaper's own path ever set it, so pressing *Take it* moved the
        colour and left the outline on the previous wallpaper's while the tab said it had taken it
        too. A fact the daemon checks cannot be forgotten by a caller, and `scripts/drive.py` can
        exercise the very path the interface uses rather than a flag of its own.

        **The wallpaper being acted on has to be handed in on the picker's own path, because the
        shell cannot be asked there.** The picture goes up *after* the colour, deliberately and
        with a measurement behind it (see `_apply_wallpaper_colour`), so at this moment the shell
        still reports the previous wallpaper. Asked there, it would answer "not from the wallpaper"
        on every single wallpaper change and the outline would follow nothing at all. So: a name
        means that wallpaper, `""` means whatever is on screen -- which is right for a colour taken
        from the Appearance tab, where the picture is already up -- and `None` means a caller that
        knows this is nobody's wallpaper, which is what an imported settings file is, and a
        profile being loaded.

        Read from the cache and never worked out here. `set_theme` runs on the daemon's own loop,
        and a wallpaper whose colour is not known yet is exactly the second and a half of ffmpeg
        that `warm_colour` exists to keep off it -- so an unknown colour answers no, which errs
        towards leaving the outline alone.
        """
        if target is None or not accent or not self.config.auto_colour or mode not in theme.MODES:
            return False
        if not target:
            try:
                target = wallpaper.showing(wallpaper.snapshot())
            except wallpaper.WallpaperError as e:
                self.log(f"could not ask the shell what the wallpaper is: "
                         f"{logs.what(e)}", trouble=True)
                return False
            if not target:
                return False
        return wallcolour.known_colour(target, mode) == accent
