"""The windows: knowing which are open, giving a new one KyprX's defaults, and the Windows tab.

The compositor script says a window moved, and that is a trigger rather than the truth -- a window's
class may not be final yet and its decoration may not exist -- so the daemon waits for things to
settle and then asks for the whole list (`request_inventory`), no more often than
`MIN_INVENTORY_GAP` allows. A class it has never seen gets the defaults of *Adjust new windows*,
once (`apply_defaults`); `check_applied` looks afterwards for an application that refused its title
bar. The Windows tab's rows are `table`; its ticks are `set_switches` for the switches written per
window (`SWITCHES`) and `set_window_lists` for the two that are memberships of one of the
compositor's lists, in one transaction per batch because writing the tiler's list re-tiles the
screen.

The daemon's state it reads or writes, all of it created in `Daemon.__init__`: `config`, `migrated`,
`state`, `windows`, `_deferred`, `_folder_holding`, `_last_inventory`, `_last_report`, `_settle`,
`_settle_deadline`.
"""

from __future__ import annotations

import time
from dataclasses import asdict

import dbus
from gi.repository import GLib

import effects
import logs
import policy
import shortcuts
import writer
from kyprd_names import LIST_SWITCHES, OVERLAY_CLASSES, SWITCHES


#: How long to wait between the notice and the picture. Covers a late class and a decoration
#: still being built.
SETTLE_MS = 700

#: Hard floor between two inventory runs, in seconds. Asking the compositor to walk every window
#: is not free; without a floor a bug upstream of here can make this a tight loop.
#:
#: A request inside the floor is **deferred, not dropped**. Dropping it is what the first version
#: did, and it threw away exactly the request that mattered: in a burst of new windows the last
#: one is the one with the accurate picture, and it is also the one most likely to land inside the
#: floor.
MIN_INVENTORY_GAP = 0.4

#: The furthest the settle timer may be pushed out by a stream of new windows, in milliseconds.
#: Without it, an application opening one window after another postpones the inventory for as long
#: as it keeps going.
MAX_SETTLE_MS = 3000

#: The compositor script's action for "re-read the window list". Addressed by name, through the
#: shortcut registry — see `kwin-script/contents/code/main.js` for why it is not a script load.
INVENTORY_ACTION = shortcuts.INVENTORY_ACTION


class WindowsPart:
    """The open windows, new ones, and the Windows tab's rows."""

    def by_class(self) -> dict[str, policy.Window]:
        """One window per class — the shape everything downstream wants.

        Derived on demand. There are tens of windows at most, and doing it here means there is
        nothing to keep in step.
        """
        out: dict[str, policy.Window] = {}
        for window in self.windows.values():
            if window.window_class:
                out[window.window_class] = window
        return out

    def request_inventory(self) -> None:
        """Ask the compositor script to re-read every window. The answer arrives as `Report`.

        **Through the shortcut registry, by name.** The obvious way — load a one-shot script,
        `run()` it, unload it — was measured to be silently broken: the compositor numbers scripts
        by the size of its own list, so the id it hands back is reused after any unload, the new
        script's object path is already taken by a live one, and `run()` lands on somebody else's
        script with no error anywhere. See `kwin-script/contents/code/main.js`.

        Rate limited, and a request inside the floor is **deferred**, not dropped.
        """
        now = time.monotonic()
        waited = now - self._last_inventory
        if waited < MIN_INVENTORY_GAP:
            if self._deferred is None:
                delay = int((MIN_INVENTORY_GAP - waited) * 1000) + 10
                self._deferred = GLib.timeout_add(delay, self._deferred_inventory)
            return
        self._last_inventory = now
        try:
            shortcuts.invoke(INVENTORY_ACTION)
        except dbus.DBusException as e:
            self.log(f"could not ask the compositor for the window list: {logs.what(e)} — "
                     f"is the compositor script installed and switched on?", trouble=True)
            return
        if writer.dry_run():
            # The one thing dry run does not hold back, and it should say so. Reading the
            # compositor is a call into it; nothing is written either way.
            self.log("asked the compositor for the window list — reading it is not a write")
        # Nothing answers this call: `invokeShortcut` returns as soon as the action fires, and the
        # picture comes back later on `/Windows`. Silence is therefore a real outcome and worth a
        # line, because silence is exactly what the broken version produced for months.
        # The deadline is bound to *this* request. Sharing one field across requests meant a
        # second ask moved the goalposts for the first one's timer, which then reported silence
        # that had not happened — twice in the same second, in the log.
        GLib.timeout_add(2000, lambda asked=now: self._inventory_arrived(asked))

    def _deferred_inventory(self) -> bool:
        self._deferred = None
        self.request_inventory()
        return False

    def _inventory_arrived(self, asked: float) -> bool:
        if self._last_report < asked:
            self.log("asked the compositor for the window list and nothing came back")
        return False

    def _settle_then_look(self) -> None:
        """Wait for things to stop moving, but not for ever.

        The timer restarts on every new window, which is what makes the picture accurate. The
        deadline is what stops an application that opens a window a second from postponing the
        inventory until it finishes.
        """
        now = time.monotonic()
        if self._settle is None:
            self._settle_deadline = now + MAX_SETTLE_MS / 1000
        elif now >= self._settle_deadline:
            return                      # already as late as it is allowed to be; let it fire
        else:
            GLib.source_remove(self._settle)
        self._settle = GLib.timeout_add(SETTLE_MS, self._settled)

    def _settled(self) -> bool:
        self._settle = None
        self.request_inventory()
        return False

    def _look_again_soon(self, delay: int = 600) -> None:
        GLib.timeout_add(delay, lambda: (self.request_inventory(), False)[1])

    # ------------------------------------------------------------ deciding

    def _candidates(self) -> list[policy.Window]:
        return [w for c, w in self.by_class().items()
                if w.manageable() and not policy.auto_skip(c) and c not in self.state.seen]

    def pending(self) -> list[policy.Window]:
        """Windows never seen before **that the defaults would actually change**.

        The second half matters on a desktop that is already set up by hand: without it, the very
        first run would announce every window as waiting when almost none of them needs anything.
        """
        tx = writer.Transaction()
        wanted = policy.Switches(**asdict(self.config.defaults))
        out = []
        for w in self._candidates():
            current, _ = self.switches_of(tx, w.window_class, w.resource_name)
            if current != wanted:
                out.append(w)
        return out

    def apply_defaults(self) -> None:
        if not self.migrated:
            # Without the remembered state every open window looks new, and this would write the
            # defaults over every choice the user has made. Nothing is worth that.
            return
        if self._folder_holding:
            # A folder that arrived is waiting to be applied, and it may say what these windows
            # are. They are looked at again once it has gone in -- `_folder_arrival` asks.
            return
        candidates = self._candidates()
        if not candidates:
            return
        waiting = self.pending()
        if self.config.paused:
            if waiting:
                self.log(f"paused, {len(waiting)} window(s) waiting: "
                         f"{', '.join(w.window_class for w in waiting)}")
            return
        wanted = policy.Switches(**asdict(self.config.defaults))
        if waiting:
            # One transaction for the whole batch, not one per window. At the next login every
            # window is new at once, and applying them one at a time would mean a dozen file
            # rewrites and a dozen compositor reloads back to back, at the moment the session is
            # busiest. That shape is what took a session down during development.
            def build(tx):
                for w in waiting:
                    policy.apply(tx, w, wanted, self.strength_for(w.window_class))
                nonlocal held
                if self.at_full():
                    # At 100 a new window's tick writes nothing -- the default already reads like
                    # it -- so the batch is what the held list has to remember.
                    held = self.ticks_at_100(
                        tx, {w.window_class: (wanted.transparency, w.resource_name)
                             for w in waiting},
                        self.config.ticked_at_100)

            held = None
            try:
                diff = writer.run(build)
            except Exception as e:  # noqa: BLE001
                self.log(f"failed on the batch of {len(waiting)}: {logs.what(e)}", trouble=True)
                return
            self.log(f"{'would set' if writer.dry_run() else 'set'} up {len(waiting)} window(s): "
                     f"{', '.join(w.window_class for w in waiting)}")
            if writer.dry_run() and diff:
                self.log("would have written:\n" + diff)
            if held is not None:
                self.keep_ticks(held)
            self._look_again_soon()
        for w in candidates:
            self.state.mark_seen(w.window_class)
        self.state.save()

    def apply_to(self, window_class: str, wanted: policy.Switches) -> str:
        window = self.by_class().get(window_class) or policy.Window(window_class=window_class)
        held = None

        def build(tx):
            policy.apply(tx, window, wanted, self.strength_for(window.window_class))
            nonlocal held
            if self.at_full():
                # One window's switches written at 100: its tick, wanted or not, may not be
                # deducible from what was written -- `ticks_at_100` keeps the ones that are not.
                held = self.ticks_at_100(
                    tx, {window.window_class: (wanted.transparency, window.resource_name)},
                    self.config.ticked_at_100)

        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001
            self.log(f"failed on {window_class}: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        if diff:
            self.log(f"{window_class}: titlebar={'shown' if wanted.titlebar else 'hidden'} "
                     f"outline={'on' if wanted.outline else 'off'} "
                     f"transparency={'on' if wanted.transparency else 'off'} "
                     f"blur={'on' if wanted.blur else 'off'}")
            if writer.dry_run():
                self.log("would have written:\n" + diff)
        if held is not None:
            self.keep_ticks(held)
        self._look_again_soon()
        return "ok"

    def set_switch(self, window_class: str, name: str, value: bool) -> str:
        return self.set_switches({window_class: {name: value}})

    def set_switches(self, wanted: dict) -> str:
        """`{class: {switch: bool}}`, applied in one transaction.

        One transaction for however many rows moved, rather than one each. Every write here ends
        in a compositor reconfigure, and ticking four rows in a row used to ask for four of them —
        the same shape `apply_defaults` already avoids for the login batch.

        What is wanted is read first and applied second, deliberately: reading inside the
        transaction that writes would have each row see the half-finished work of the row before
        it. The reading goes through `switches_of`, so a tick held at 100 % is read as the tick it
        is rather than deduced away -- otherwise re-applying such a row would read it unticked and
        write it unticked, and the tick would be gone.
        """
        reading = writer.Transaction()
        open_now = self.by_class()
        rows = []
        touched: dict = {}
        for window_class, changes in wanted.items():
            window = open_now.get(window_class) or policy.Window(window_class=window_class)
            current, _ = self.switches_of(reading, window_class, window.resource_name)
            for name, value in changes.items():
                if name not in SWITCHES:
                    return f"error: unknown switch {name}"
                setattr(current, name, bool(value))
            rows.append((window, current))
            touched[window_class] = (current.transparency, window.resource_name)

        held = None

        def build(tx):
            for window, switches in rows:
                policy.apply(tx, window, switches, self.strength_for(window.window_class))
            nonlocal held
            if self.at_full():
                # At 100 the tick a row writes reads like no tick at all, so what the rows end at
                # is what the held list has to remember -- including the ticks it must let go.
                held = self.ticks_at_100(tx, touched, self.config.ticked_at_100)

        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001
            self.log(f"failed on {', '.join(wanted)}: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        if diff:
            for window, switches in rows:
                self.log(f"{window.window_class}: "
                         f"titlebar={'shown' if switches.titlebar else 'hidden'} "
                         f"outline={'on' if switches.outline else 'off'} "
                         f"transparency={'on' if switches.transparency else 'off'} "
                         f"blur={'on' if switches.blur else 'off'}")
            if writer.dry_run():
                self.log("would have written:\n" + diff)
        if held is not None:
            self.keep_ticks(held)
        for window_class in wanted:
            self.state.mark_seen(window_class)
        self.state.save()
        self._look_again_soon()
        return "ok"

    def set_window_lists(self, wanted: dict) -> str:
        """Add or remove window classes from the two lists the last table columns stand for.

        One transaction for the whole batch, and that is the point of the method existing at all.
        Writing the tiler's list makes the tiling script re-read itself, and a script that has just
        started tiles the screen from scratch. Doing that once per ticked row would have the
        windows rearrange five times over while somebody sets five of them to float.

        An overlay's own class is refused rather than silently re-added later: the daemon puts
        those back on every start, so removing one here would be a change that undoes itself.
        """
        def build(tx):
            floating = effects.tiling_list(tx.kwin, effects.TILING_FLOAT_LIST)
            after = list(floating)
            for window_class, on in (wanted.get("float") or {}).items():
                if window_class in OVERLAY_CLASSES and not on:
                    self.log(f"{window_class} is one of this app's overlays and has to float; "
                             f"leaving it in the list")
                    continue
                if on and window_class not in after:
                    after.append(window_class)
                elif not on and window_class in after:
                    after.remove(window_class)
            if after != floating:
                effects.set_tiling_list(tx.kwin, effects.TILING_FLOAT_LIST, after)
                tx.reload_tiling = True

            excluded = effects.geometry_excluded(tx.kwin)
            left = list(excluded)
            for window_class, on in (wanted.get("animate") or {}).items():
                if on and window_class in left:
                    left.remove(window_class)
                elif not on and window_class not in left:
                    left.append(window_class)
            if left != excluded:
                effects.set_geometry_excluded(tx.kwin, left)
                tx.reload_kwin = True

        try:
            diff = writer.run(build)
        except Exception as e:  # noqa: BLE001
            self.log(f"failed on the window lists: {logs.what(e)}", trouble=True)
            return f"error: {e}"
        if diff:
            for name in LIST_SWITCHES:
                for window_class, on in (wanted.get(name) or {}).items():
                    self.log(f"{window_class}: {name}={'yes' if on else 'no'}")
            if writer.dry_run():
                self.log("would have written:\n" + diff)
        # Marked seen for the same reason a switch does it: a class somebody has decided something
        # about stays in the table after its window closes, so the decision can be undone.
        for name in LIST_SWITCHES:
            for window_class in (wanted.get(name) or {}):
                self.state.mark_seen(window_class)
        self.state.save()
        return "ok"

    def check_applied(self) -> None:
        """Did the setup take? When it did not, say why.

        Forcing a title bar only works on an app that negotiates decorations with the compositor.
        One that draws its own and refuses the server's never negotiates, so the rule sits there
        doing nothing. Without this check the app would report a window as set up when nothing
        about it changed, which is worse than not having tried.
        """
        tx = writer.Transaction()
        changed = False
        for window_class, w in self.by_class().items():
            if not w.manageable() or window_class not in self.state.seen:
                continue
            current, _ = self.switches_of(tx, window_class, w.resource_name)
            if current.titlebar:
                refuses = False
            else:
                refuses = w.needs_rule()
            if self.state.set_refuses_ssd(window_class, refuses):
                changed = True
                if refuses:
                    self.log(f"{window_class}: the rule did not take — this app draws its own "
                             f"title bar and refuses the server's. The switch is inside it.")
                    self.notify_failure(
                        f"{window_class}\nThis app refuses a server-side decoration: it draws its "
                        f"own title bar. Look for a title bar option in its own settings.")
        if changed:
            self.state.save()

    # ------------------------------------------------------------ the table

    def table(self) -> list[dict]:
        tx = writer.Transaction()
        blur_per_window = effects.blur_is_per_window(tx.kwin)
        # Read once for the whole table rather than once per row: both are a string split, and a
        # table of thirty windows would otherwise do sixty of them for one answer each.
        floating = effects.tiling_list(tx.kwin, effects.TILING_FLOAT_LIST)
        excluded = effects.geometry_excluded(tx.kwin)
        tiling_on = effects.plugin_enabled(tx.kwin, effects.TILING_PLUGIN)
        geometry_on = effects.plugin_enabled(tx.kwin, effects.GEOMETRY_PLUGIN)
        rows = []
        open_now = self.by_class()
        for window_class in sorted(set(open_now) | self.state.seen):
            w = open_now.get(window_class)
            switches, pattern = self.switches_of(
                tx, window_class, w.resource_name if w else "")
            shared = policy.shared_pattern(pattern, window_class)
            status = ""
            if window_class in self.state.refuses_ssd:
                status = "refuses"
            elif policy.auto_skip(window_class):
                # Before the closed test: a system window stays one while it is closed. Labelled
                # "closed", it had the tab offering an opacity menu that `own_allowed` refuses, and
                # the simulation counting it among the ticks a move to 100 % keeps, though
                # `transparency_targets` never reaches it -- measured: 15 expected, 13 kept.
                status = "system"
            elif w is None:
                status = "closed"
            elif shared:
                status = "shared"
            rows.append({
                "class": window_class,
                "title": w.caption if w else "",
                "open": w is not None,
                # Whether this app has met the class (`state.seen`): the only windows a move of
                # the strength reaches (`transparency_targets`). A dialog or a popup with a class
                # of its own is open and never met, yet reads ticked under a broad rule; a reader
                # counting the ticks the strength owns needs this to leave it out -- measured in
                # memory: the simulation's count took one such window in, the daemon kept none.
                "seen": window_class in self.state.seen,
                "manageable": w.manageable() if w else True,
                "skipped": list(w.skipped) if w else [],
                "titlebar": switches.titlebar,
                "outline": switches.outline,
                "transparency": switches.transparency,
                "blur": switches.blur,
                #: What this window is actually drawn at, and the strength a tick would use.
                #: Both, because they are two different facts: the first can come from a rule
                #: somebody wrote by hand, the second is this app's own number -- the window's
                #: own, when it has one, which `own_strength` says apart from the shared one.
                "opacity": policy.opacity_of(tx, window_class, w.resource_name if w else ""),
                "transparency_strength": self.strength_for(window_class),
                "own_strength": self.config.own_transparency.get(window_class),
                "pattern": pattern or "",
                "shared": shared,
                "blur_per_window": blur_per_window,
                # Inverted once, here, and never again: the effect keeps a list of what it must
                # *not* animate, and the column asks whether it does. Inverting in the interface
                # instead would mean two places knowing the polarity and one of them being wrong.
                "float": window_class in floating,
                "animate": window_class not in excluded,
                "tiling_enabled": tiling_on,
                "geometry_enabled": geometry_on,
                # An overlay floats because a window rule and this list say so, and the daemon
                # puts both back every time it starts. A tick that undoes itself on the next start
                # is worse than no tick, so the interface is told not to offer one.
                "float_locked": window_class in OVERLAY_CLASSES,
                # One of this app's own windows. The three switches do not apply to it: it is not
                # managed like an application, and the daemon takes that treatment back off on
                # every start -- so a tick here would be a tick that undoes itself, and an empty
                # box would read as "this window has a title bar", which it has not.
                "overlay": window_class in OVERLAY_CLASSES,
                "status": status,
            })
        return rows
