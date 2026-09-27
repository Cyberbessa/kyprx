"""The daemon's side of global shortcuts: the keys it binds and the keys it hands back.

It gives back the cheatsheet key that earlier shapes of this app held, and binds a key for the
Shortcuts tab -- refusing one another action already holds unless the tab asked to take it. When
the settings window leaves the bus it lifts every suspension of the desktop's shortcuts, which
undoes one a row listening for keys left behind. This part makes no call to the shortcut registry
itself: every one of the daemon's is in `daemon/shortcuts.py`.

The daemon's state it reads or writes, all of it created in `Daemon.__init__`: `interface_owner`,
`_interface_watch`.
"""

from __future__ import annotations

import dbus

import logs
import shortcuts
import writer


class ShortcutsPart:
    """Binding keys, and giving the desktop its keys back."""

    # ------------------------------------------------------------ global shortcuts

    def release_legacy_shortcut_claims(self) -> None:
        """Give back the cheatsheet key that earlier shapes of this app were holding.

        The shortcut is the compositor script's now — registered there the way the tiling script
        registers its own, which is the one way that demonstrably gets a key grabbed. Two earlier
        shapes claimed it from here instead: a component of this app's own, which came back
        inactive and so was never grabbed, and a desktop entry of its own, which the registry
        accepted and the compositor still ignored.

        What matters is that they let go. Up to Plasma 6.6 a combination another component still
        held was refused to the script; from 6.7 both keep it and the older claim is the one the key
        runs. Either way the key goes on doing nothing, for a third reason.
        """
        if writer.dry_run():
            # Named, and only when there is one: announcing a release on every start whether or
            # not anything was left to release was a dry run saying something untrue.
            try:
                held = shortcuts.legacy_claims_held()
                spectacle = shortcuts.spectacle_conflict_held()
            except dbus.DBusException:
                held, spectacle = [], []
            if held:
                writer.report("would release the old claims on the cheatsheet key: "
                              + ", ".join(f"{c}/{a}" for c, a in held))
            if spectacle:
                writer.report("would release Meta+R from Spectacle RecordRegion for the wallpaper picker")
            return
        try:
            shortcuts.release_legacy_claims()
            shortcuts.release_spectacle_conflict()
        except dbus.DBusException as e:
            self.log(f"could not release legacy shortcut claims: "
                     f"{logs.what(e)}", trouble=True)

    def rebind_shortcut(self, component: str, action: str, old: list[int], new: list[int],
                        take: bool = False) -> str:
        """Put `new` where `old` was on one action, as one write through `writer`.

        **Checked before and after.** Before: a key another action holds is refused, naming it,
        unless `take` says to take it over -- on Plasma 6.7 the registry itself refuses nothing and
        keeps a shared key on both actions, running the one registered first, so this is the only
        place a conflict can be seen at all. After: `shortcuts.rebind` reads back what was stored
        and raises when it is not what was asked. It used to be enough for the answer not to be
        empty, which it never is on an action with a second key.

        A key the action already holds is never a conflict with itself, even when a second action
        holds it too: nothing about this action's keys is changing, and a desk that already has
        such a pair must still be able to put a key back where it was.

        Taking over goes through the same transaction as the bind, as one session write: the key
        is taken from its holder first, then bound, and if the bind fails the holder gets its keys
        back. In dry run none of it happens, and the report names both halves.
        """
        try:
            ident = shortcuts.ident_of(action, component)
            held = shortcuts.keys_of(action, component)
            owners = ([] if not new or new in held
                      else shortcuts.holders(new, exclude=(component, action)))
        except KeyError:
            return f"error: there is no action {action} in {component}"
        except dbus.DBusException as e:
            return f"error: {e}"
        name = ident[3] or action
        if owners and not take:
            return (f"error: {shortcuts.key_text(new)} is used by "
                    + ", ".join(f"{h['name']} ({h['component_name']})" for h in owners))
        kept = [s for s in held if s != old]
        after = sorted(kept + ([new] if new and new not in kept else []))
        if after == held and not owners:
            return "ok"                 # already so: nothing to write and nothing to say

        def act():
            taken = []
            try:
                for holder in owners:
                    taken.append((holder, shortcuts.take_from(holder, new)))
                shortcuts.rebind(action, old, new, component)
            except Exception:
                for holder, keys in reversed(taken):
                    try:
                        shortcuts.give_back(holder, keys)
                    except dbus.DBusException as e:
                        self.log(f"{holder['name']} could not have its keys put back: "
                                 f"{logs.what(e)}", trouble=True)
                raise

        description = (f"--- the keys of {name}\n+++ kglobalaccel\n"
                       f"-{shortcuts.keys_text(held)}\n+{shortcuts.keys_text(after)}\n")
        plain = f"the keys of {name} ({component}): {shortcuts.keys_text(held)} → " \
                f"{shortcuts.keys_text(after)}"
        if owners:
            plain += (f", after taking {shortcuts.key_text(new)} away from "
                      + ", ".join(f"{h['name']} ({h['component_name']})" for h in owners))

        def build(tx):
            tx.session_write(description, act, plain)

        try:
            diff = writer.run(build)
        except shortcuts.Refused as e:
            self.log(f"{name}: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        except (KeyError, dbus.DBusException) as e:
            self.log(f"failed on the keys of {name}: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        if writer.dry_run() and diff:
            # A marker of its own, as before: a shortcut is not a config file, and the scripts
            # read "would have written" as one.
            self.log("would have bound:\n" + diff)
        return "ok"

    def watch_interface(self, owner: str | None) -> None:
        """Hand the desktop its shortcuts back if the settings window goes away mid-capture.

        While a row on the Shortcuts tab listens for keys, every global shortcut on the desktop is
        suspended, and the window lifts that on its way out. Killed rather than closed, it never
        did -- and a desktop with every shortcut dead, the one that opens this window included, is
        the worst state this app can leave behind. So when the window's connection leaves the bus
        the daemon lifts the suspension itself: a call that does nothing when nothing is
        suspended, made in dry run too, because it puts the desktop back rather than changing it.

        One thing it can do that nobody wants, noted rather than solved: another program listening
        for keys at that very moment -- the desktop's own shortcut settings -- would lose its
        suspension along with this one.
        """
        if self._interface_watch is not None:
            self._interface_watch.remove()
            self._interface_watch = None
        if not owner:
            return

        def moved(new_owner: str) -> None:
            if new_owner:
                return          # called once straight away, with the window still there
            if self.interface_owner == owner:
                self.interface_owner = None
            try:
                shortcuts.unblock()
            except dbus.DBusException as e:
                self.log(f"could not hand the desktop its shortcuts back: "
                         f"{logs.what(e)}", trouble=True)

        try:
            self._interface_watch = dbus.SessionBus().watch_name_owner(owner, moved)
        except dbus.DBusException as e:
            self.log(f"could not watch the settings window: {logs.what(e)}", trouble=True)
