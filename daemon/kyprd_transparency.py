"""How see-through windows are: the one strength every ticked window shares, and a window's
own number.

Opacity is four keys of a window rule, and somebody else's rule may already say something about a
window -- a broad one covering every window, or the screen-sharing helper hiding itself at 0. What
a window reads now is read the way the compositor reads it (`rules.opacity_for`), and nothing is
written where that is already what was asked for; `policy.set_transparency` has the rule.
`own_allowed` says which windows may have a number of their own at all: not the ones this app
never manages, and not its own overlays.

The daemon's state it reads or writes, all of it created in `Daemon.__init__`: `config`, `state`.
"""

from __future__ import annotations

import logs
import policy
import rules
import writer
from kyprd_names import OVERLAY_CLASSES
from state import own_strength


class TransparencyPart:
    """The shared strength, and each window's own."""

    def transparency_targets(self) -> list:
        """Every window the strength reaches: seen, not one this app refuses to manage, and
        see-through now -- whoever made it so.

        **It reaches windows this app has no rule for yet**, and that is a correction rather than a
        detail. The restrike used to rewrite only the rules already carrying an opacity, out of a
        scruple about taking over a line somebody else wrote — and on a desk where every window is
        see-through because of one broad rule written by hand, that made the control do nothing
        anybody could see. Measured: moving it wrote thirteen windows, not one of which was on
        screen. Owning the number means owning a rule for each window the number applies to, and
        that is what was asked for.

        Windows this app does not manage are skipped, the same list `apply_defaults` skips: the
        shell, the overlays, the compositor's own. A rule for those would be this app managing
        something it has always refused to manage.

        **So is every window with a number of its own**, and this is the one place that has to
        say so: every road that moves the strength -- the control, a profile, *Restore defaults*,
        a settings file -- asks here which windows it reaches. It cannot be left to
        `policy.set_transparency` noticing a window is not at the old number: a class whose own
        number happens to equal the strength it is moving from would stand exactly where a window
        the strength owns stands, and would move with it.

        Read on a transaction of its own, before anything is written, for the reason
        `set_switches` gives: reading inside the transaction that writes would have each row see
        the half-finished work of the row before it. Only a list of candidates, too:
        `policy.set_transparency` judges each one again from the file it is about to write, which
        is what keeps a retry after a `WriteConflict` correct.
        """
        reading = writer.Transaction()
        open_now = self.by_class()
        wanted = []
        for window_class in sorted(self.state.seen):
            if policy.auto_skip(window_class) or window_class in self.config.own_transparency:
                continue
            w = open_now.get(window_class) or policy.Window(window_class=window_class)
            if policy.opacity_of(reading, window_class,
                                 w.resource_name) < rules.FULLY_OPAQUE:
                wanted.append(w)
        return wanted

    @staticmethod
    def strike_transparency(tx, wanted: list, strength: int, previous: int) -> None:
        """Write `strength` on every window in `wanted`, into a transaction somebody else commits.

        The two numbers travel side by side on purpose. `previous` is what a window has to stand
        at to be this app's to move -- `policy.set_transparency` leaves a window somebody else's
        rule draws at a number of their own alone, and reads `previous` to tell the two apart --
        and a pair that could be swapped in silence would move the wrong windows in silence. Says
        nothing itself: whoever commits the transaction says what was struck.
        """
        for w in wanted:
            policy.set_transparency(tx, w, True, strength, previous)

    def restrike_transparency(self, previous: int) -> str:
        """Write the strength again on every window that stood at the one it is moving from.

        The number is one setting shared by every ticked row without a number of its own, so
        changing it has to reach them all — and in one transaction, because every one of these
        ends in a compositor reconfigure.
        Which windows is `transparency_targets`; the writes are `strike_transparency`, kept apart
        so that a profile being loaded can make the same writes inside the transaction that
        carries its decoration keys, and stop the screen once rather than twice.

        Nothing is written for a window already at the wanted value, so putting the number back
        where it was costs nothing, and the windows a broad rule already draws at that value are
        left alone. So is a window somebody else's rule draws at a number that is neither: the
        screen-sharing helper that hides itself at 0 is see-through, and is nobody's to move --
        see `policy.set_transparency`, which is where `previous` is read.
        """
        wanted = self.transparency_targets()
        if not wanted:
            return "ok"

        def build(tx):
            self.strike_transparency(tx, wanted, self.config.transparency, previous)

        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001
            self.log(f"failed on the transparency: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        if diff:
            self.log(f"{'would set ' if writer.dry_run() else ''}"
                     f"transparency={self.config.transparency}% on {len(wanted)} window(s)")
            if writer.dry_run():
                self.log("would have written:\n" + diff)
        return "ok"

    @staticmethod
    def own_allowed(window_class: str) -> bool:
        """May this class have a number of its own?

        Not for the windows this app never manages, the list `apply_defaults` and
        `transparency_targets` already leave out -- and here it is not courtesy. A number is
        written with `claim`, into a rule at the head of the list, so it would win over whatever
        drew the window before: the screen-sharing helper hides itself behind a rule forcing 0,
        and a number given to it would put it on screen; one given to the shell would make the
        panel and the desktop see-through. Nor for this app's own overlays, which are not managed
        as windows at all -- the picker is pinned opaque on purpose (`rules.overlay_placement`
        says why).
        """
        return (bool(window_class) and window_class not in OVERLAY_CLASSES
                and not policy.auto_skip(window_class))

    def strength_for(self, window_class: str) -> int:
        """How see-through this window is when its Transparency is ticked: its own number when it
        has one, the strength every other ticked window shares when it has not.

        Every write of a window's switches asks this rather than reading the strength, and that is
        not tidiness. Re-applying a row re-applies all four of its switches, transparency among
        them -- so a row whose outline was ticked would otherwise have its own number written
        over with the strength, by a click in another column.
        """
        return self.config.own_transparency.get(window_class, self.config.transparency)

    def set_own_transparency(self, window_class: str, strength) -> str:
        """Give one window class a number of its own, change it, or take it away (`None`).

        **Given, the window is made see-through at it** -- ticked, if it was opaque. The Windows
        tab offers a number only on a ticked row, so from there the tick never moves; a caller
        naming an opaque window is asking to see through it, and a number that waited for a tick
        before doing anything would be a call that does nothing. It is written with `claim`, for
        the reason `policy.set_transparency` gives.

        **Taken away, the window goes back to the strength** if it is see-through, and stays
        opaque if it is not: removing a number is not ticking anything. It is moved the way the
        strength moves a window, with the old number as `previous`, so a window somebody else's
        rule has taken over since is left to them.

        The setting is kept before the window is written, in the order `SetSettings` keeps and
        for its reason: a write that fails leaves the list saying what was asked, and asking again
        writes it -- the call does not stop early because the list already holds the number.

        The class is **not** marked as seen. A number can be given to an application that has not
        been opened yet, and seen is what stops the defaults reaching a window the first time it
        opens; the list is what keeps it on screen in the meantime.

        Refused for the windows this app never manages -- `own_allowed` says which, and why a
        number there is worse than useless.
        """
        window_class = str(window_class or "").strip()
        if not window_class:
            return "error: no window class"
        if not self.own_allowed(window_class):
            return (f"error: {window_class} is one of the desktop's own windows, which KyprX "
                    f"leaves alone")
        if strength is not None:
            strength = own_strength(strength)
            if strength is None:
                return "error: a window's own transparency is a whole number from 1 to 99"
        owned = dict(self.config.own_transparency)
        before = owned.get(window_class)
        if strength is None and before is None:
            return "ok"
        window = self.by_class().get(window_class) or policy.Window(window_class=window_class)
        see_through = policy.opacity_of(writer.Transaction(), window_class,
                                        window.resource_name) < rules.FULLY_OPAQUE
        if strength is None:
            owned.pop(window_class)
        else:
            owned[window_class] = strength
        self.config.own_transparency = owned
        self.config.save()

        def build(tx):
            if strength is not None:
                policy.set_transparency(tx, window, True, strength, claim=True)
            elif see_through and rules.find_owned(tx.rules, window_class, window.resource_name):
                # Only a rule of this app's is moved back. With none, the number never had to be
                # written -- a broad rule of somebody's already drew the window at it -- and what
                # draws it now is theirs, exactly as it was before the number was given.
                policy.set_transparency(tx, window, True, self.config.transparency,
                                        previous=before)

        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001
            self.log(f"failed on {window_class}'s own transparency: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        self.log(f"{window_class}: {'would give it ' if writer.dry_run() else ''}own transparency "
                 + (f"{strength}%" if strength is not None
                    else f"removed, back to {self.config.transparency}%"))
        if diff and writer.dry_run():
            self.log("would have written:\n" + diff)
        self._look_again_soon()
        return "ok"

    def restrike_own(self, before: dict) -> str:
        """After the whole list of own numbers was replaced -- a settings file being imported --
        write every class whose number came, went or moved.

        Only the ones that are see-through now. The file has already put each window's tick where
        it says, and a number arriving with it is how see-through a ticked window is, not a tick:
        a window the same file says is opaque stays opaque. That is the difference from
        `set_own_transparency`, where somebody is asking for this one window by name.
        """
        after = self.config.own_transparency
        moved = [c for c in sorted(set(before) | set(after)) if before.get(c) != after.get(c)]
        if not moved:
            return "ok"
        reading = writer.Transaction()
        open_now = self.by_class()
        rows = []
        for window_class in moved:
            w = open_now.get(window_class) or policy.Window(window_class=window_class)
            if policy.opacity_of(reading, window_class, w.resource_name) < rules.FULLY_OPAQUE:
                rows.append((w, before.get(window_class), after.get(window_class)))

        def build(tx):
            for w, was, now in rows:
                if now is not None:
                    policy.set_transparency(tx, w, True, now, claim=True)
                elif rules.find_owned(tx.rules, w.window_class, w.resource_name):
                    # See `set_own_transparency`: only a rule of this app's goes back.
                    policy.set_transparency(tx, w, True, self.config.transparency, previous=was)

        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001
            self.log(f"failed on the windows' own transparency: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        if diff:
            self.log(f"{'would set ' if writer.dry_run() else ''}own transparency on "
                     f"{len(rows)} window(s)")
            if writer.dry_run():
                self.log("would have written:\n" + diff)
        return "ok"
