"""Profiles, from the daemon's side: the look the desktop is wearing, and putting one on.

A look is what `daemon/profiles.py` keeps under a name -- the transparency every ticked window
shares, the decoration's corner radius and outline, the blur's radius, and the colours. `worn_look`
reads each of those as it reads now, the file's value or what the program ships, which is the same
reading `apply_look` compares against before it writes, so "this is the look on the desktop" and
"loading it would write nothing" are one fact. The list of profiles itself, and saving, renaming and
deleting them, is `daemon/profiles.py` and the API in `daemon/kyprd_api.py`.

The daemon's state it reads or writes, all of it created in `Daemon.__init__`: `config`.
"""

from __future__ import annotations

import logs
import profiles
import theme
import writer
from declared import effective_value, note_reloads, shipped_defaults, write_declared


class ProfilesPart:
    """The look on the desktop, and putting a profile's on."""

    # ------------------------------------------------------------ looks

    def worn_look(self) -> dict:
        """The look the desktop is wearing, in the shape a profile keeps.

        Every value is the effective one -- `daemon/profiles.py` says why -- and a key with no
        value anywhere is left out rather than kept as nothing. Read off a throwaway transaction
        the way `Groups()` reads, and never through `export_settings()`: that walks every window
        ever seen and asks the shortcut registry about every action, and this is called to draw a
        list that every `Changed` redraws.
        """
        tx = writer.Transaction()
        shipped = shipped_defaults()
        look: dict = {"klassy": {}, "blur": {}, "theme": {}}
        for group, keys in profiles.KLASSY.items():
            for key in keys:
                value = effective_value(tx, shipped, "klassy", group, key)
                if value is not None:
                    look["klassy"].setdefault(group, {})[key] = value
        for key in profiles.BLUR:
            value = effective_value(tx, shipped, "blur", "", key)
            if value is not None:
                look["blur"][key] = value
        #: The strength ticked windows share -- a number of this app's, not a key in any file, so
        #: it is read where it is kept. The windows' own numbers are not part of a look: they
        #: belong to those windows, and a profile loaded leaves them where they are.
        look["transparency"] = int(self.config.transparency)
        now = theme.current()
        look["theme"] = {"mode": now["mode"], "preset": now["preset"], "accent": now["accent"],
                         # No colour of your own means nothing soaking in, which is how
                         # `set_theme` reads a tint too.
                         "tint": float(now["tint"]) if now["accent"] else 0.0,
                         "auto": False}
        return look

    def apply_look(self, look: dict) -> str:
        """Put this look on the desktop: the decoration, the blur and the windows' opacity in one
        transaction, the wallpaper's say over the colour switched off, and then the colours.

        Refused, before anything is written, when it cannot go on here -- a preset this machine
        does not have is the ordinary case. Importing the settings finds that out after its files
        are written and says nothing; a load says so first.

        **Only what differs is written**, by the same writer that puts a declared default in place:
        a key that already reads as the look asks is skipped, so loading the look that is on
        costs nothing and leaves no line in a file that did not have one. What moved decides the
        reload -- the decoration's colour cache is thrown away only when the outline did, so a
        load that moves the radius alone pays the cheap reload, the measurement beside
        `COLOUR_CACHED_GROUPS`.

        **The strength goes into the same transaction**, and that is why `restrike_transparency`
        (`daemon/kyprd_transparency.py`) is in two pieces: every rule it writes and every decoration
        key go up on one compositor reconfigure, so a load that moves the radius and the strength
        together stops the screen once. Measured with `scripts/stall.py`, ten windows open and
        thirty-nine drawn at the strength: a load that differs in the strength alone stops the
        screen once, for about 0.6 s, and one that differs in the strength and the radius stops it
        once, for about the same. The number itself is saved first -- the order `SetSettings`
        keeps, so that a load which fails halfway leaves the number ahead of the windows, which
        asking again puts right -- and `previous` is the number before the load, which is what
        decides which windows are this app's to move.

        The colours go last and through `set_theme`, with `from_wallpaper=None`: whatever colour a
        profile carries is not one a wallpaper is handing over now, and the outline the profile
        carries has just been written from its own block -- a load that overwrote it would be a
        profile that does not load. Two transactions rather than one, the way importing the
        settings does it: the decoration's pair of reloads and the desktop's own colour tools are
        each a stop of the screen, and merging the transactions would not merge the stops.
        Measured the same way, a load that moves the colours and the outline stops it twice: about
        1.4 s for the decoration's pair and 1.3 s for the desktop's colour tools.
        """
        why = profiles.trouble(look)
        if why:
            return f"error: {why}"
        look = profiles.normalise(look)
        previous = int(self.config.transparency)
        strength = int(look.get("transparency", previous))
        wanted = []
        if strength != previous:
            # In dry run this is in memory and stays there, which is what lets the simulation read
            # it back.
            self.config.transparency = strength
            self.config.save()
            wanted = self.transparency_targets()

        def build(tx):
            note_reloads(tx, write_declared(tx, profiles.tree(look)))
            # `set_transparency` asks for the reconfigure itself when it writes a rule.
            self.strike_transparency(tx, wanted, strength, previous)

        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001 -- the interface says what went wrong, and stays up
            self.log(f"failed on the look: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        if diff and wanted:
            self.log(f"{'would set ' if writer.dry_run() else ''}"
                     f"transparency={strength}% on up to {len(wanted)} window(s)")
        if writer.dry_run() and diff:
            self.log("would have written:\n" + diff)
        if self.config.auto_colour:
            # Before the colours, so that a failure among the tools below still leaves the switch
            # where a loaded profile wants it. In dry run this is in memory and stays there.
            self.config.auto_colour = False
            self.config.save()
        return self.set_theme({k: look["theme"][k] for k in profiles.THEME}, from_wallpaper=None)
