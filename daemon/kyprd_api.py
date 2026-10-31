"""The settings window's API: the object at /Manager, and every method the window calls on it.

Most methods take and return JSON in a string -- one shape, and no D-Bus signature to change every
time a table grows a field -- and answer `ok`, `error: <sentence>` or `partial: <sentence>`, which
is what `gui/client.py` reads. Most hand their work to the `Daemon` they were built with and say
the desk changed; the settings tabs' groups are read and written here (`Groups`, `SetGroups`,
`Normalize`), and so are this app's own settings (`Settings`, `SetSettings`, `SetCheatsheetKey`)
and `Diagnostics`. Two signals tell the window about changes it did not make, `Changed` and
`ColourReady`; the third, `Raise`, asks a window already open to come forward.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING

import dbus
import dbus.service

import about
import defaults
import effects
import folder
import klassy
import policy
import profiles
import reload as reloader
import shortcuts
import snapshot
import theme
import tiling
import writer
from declared import note_reloads, shipped_defaults, write_declared
from klassy import KLASSY_GROUPS
from kwin_config import DECORATION_GROUP, WINDOWS_GROUP
from kyprd_names import LIST_SWITCHES, MANAGER_IFACE, SCRIPT_PLUGIN
from state import (Defaults, all_screens, colour_screen, kde_wallpapers, saved_off, strip_text,
                   wallpaper_layout)

if TYPE_CHECKING:
    # The daemon's class, for the annotation only. Never imported for real: kyprd.py runs as the
    # program itself, and importing it would run it a second time as a module of its own.
    from kyprd import Daemon


class Manager(dbus.service.Object):
    """The interface's API. Anything with fields goes in and out as JSON in a string — one shape,
    and no D-Bus signature to change every time the table grows a field. The rest is plain: `GoBack`
    and `GoBackPreview` take a copy's name, `SetShortcut`, `SetShortcutIn` and `SetCheatsheetKey`
    take a key list, `SetSwitch` takes a class, a switch and a boolean, and the reads take nothing.
    The calls that change something answer in words -- "ok", "partial: …", "error: …" -- and
    `DryRun` answers a boolean."""

    def __init__(self, bus, daemon: Daemon):
        self.d = daemon
        dbus.service.Object.__init__(self, bus, "/Manager")

    @dbus.service.signal(MANAGER_IFACE)
    def Changed(self):
        pass

    def changed(self) -> None:
        """Say something changed, and bring the KyprX folder into step a moment later -- the one
        door every method that writes goes out through, so no write is ever left out of the
        folder."""
        self.Changed()
        self.d.folder_soon()

    @dbus.service.signal(MANAGER_IFACE, signature="s")
    def ColourReady(self, target):
        """A wallpaper's colour has been worked out, or found wanting -- see `warm_colour`.

        Narrower than `Changed` on purpose. The colour box on the Appearance tab is the one thing
        drawn from it, and the broadcast it replaced had every live tab redraw: the Wallpaper tab
        re-scanned every folder and asked the shell a question, once per stop of the picker's
        selection, for an answer that changed one line somewhere else.
        """

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="b")
    def DryRun(self):
        return writer.dry_run()

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def Windows(self):
        return json.dumps(self.d.table())

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def Settings(self):
        return json.dumps({"paused": self.d.config.paused,
                           "notify": self.d.config.notify,
                           "auto_colour": self.d.config.auto_colour,
                           #: The screen the colour comes from, "" for the primary. The window
                           #: draws the choice from `Screens`, which says which screens there are.
                           "colour_screen": self.d.config.colour_screen,
                           "transparency": self.d.config.transparency,
                           #: Read here and written through `SetOwnTransparency`, never through
                           #: `SetSettings`: a number reaches a window the moment it is set, and
                           #: the interface sends `Settings` back to that one whole.
                           "own_transparency": dict(self.d.config.own_transparency),
                           #: Read-only, and for showing rather than choosing: which windows'
                           #: ticks are being remembered while the strength stands at 100 %, where
                           #: a tick cannot be deduced from the rules. It is written by the
                           #: writes that make it true -- ticking, the strength's moves -- and
                           #: there is nothing for a caller to ask for here.
                           "ticked_at_100": list(self.d.config.ticked_at_100),
                           "defaults": asdict(self.d.config.defaults),
                           #: The switches each window keeps as set by hand, which the Windows
                           #: tab's column boxes leave alone; read-only, written by the ticks that
                           #: make it true (`set_switches`).
                           "kept": dict(self.d.config.kept or {}),
                           #: Whether KyprX is off the desk, where a column's box is refused.
                           "off": bool(self.d.state.off or saved_off()),
                           #: The picker's choices, and nothing derived from them. Working
                           #: out which folder that means, and what is in it, is `Wallpapers'`
                           #: job — this one is called to draw a header several times a second.
                           "wallpaper": dict(self.d.config.wallpaper),
                           "waiting": [w.window_class for w in self.d.pending()]})

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def TilingSwitch(self):
        """Automatic tiling for the strip above the tabs: `TilingPart.tiling_switch`. Written
        through `SetGroups` with `autoTiling` alone and no `enforce`, so the strip changes that one
        key and nothing else."""
        return json.dumps(self.d.tiling_switch())

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def Desktops(self):
        """The desktops the Tiling tab offers an arrangement for (`TilingPart.desktops_now`):
        `{"desktops": [{"number", "id", "name"}]}`, or `{"desktops": null}` when the compositor
        cannot be asked. The arrangement each starts on is `desktopArrangements` in `Groups`."""
        return json.dumps({"desktops": self.d.desktops_now()})

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def SetSettings(self, payload):
        d = json.loads(str(payload))
        was_paused = self.d.config.paused
        auto_was, screen_was = self.d.config.auto_colour, self.d.config.colour_screen
        if "paused" in d:
            self.d.config.paused = bool(d["paused"])
        if "notify" in d:
            self.d.config.notify = bool(d["notify"])
        if "auto_colour" in d:
            # A bool and nothing else. Ticking it takes no colour until the next wallpaper, and
            # unticking it puts none back: it decides how the *next* colour is chosen, and changes
            # nothing that is on screen -- the window outline included. Clear, beside the colour,
            # is what takes a colour off.
            self.d.config.auto_colour = bool(d["auto_colour"])
        if "colour_screen" in d:
            self.d.config.colour_screen = colour_screen(d["colour_screen"])
        strength_moved = False
        if "transparency" in d:
            try:
                strength = min(max(int(d["transparency"]), 1), 100)
            except (TypeError, ValueError):
                strength = self.d.config.transparency
            strength_moved = strength != self.d.config.transparency
            was_strength = self.d.config.transparency
            self.d.config.transparency = strength
        if "defaults" in d:
            self.d.config.defaults = Defaults.from_dict(d["defaults"])
        if "wallpaper" in d:
            # Read key by key rather than taken whole, so a caller sending back everything
            # `Settings` gave it — which is what the interface does — cannot store a field this
            # app does not own, and an unknown layout cannot make the picker open nothing.
            paper = d["wallpaper"] or {}
            held = self.d.config.wallpaper or {}
            self.d.config.wallpaper = {
                "video_dir": str(paper.get("video_dir", held.get("video_dir", ""))),
                "image_dir": str(paper.get("image_dir", held.get("image_dir", ""))),
                "layout": wallpaper_layout(paper.get("layout", held.get("layout"))),
                # A block without a switch is one written before it existed, or the interface
                # sending back the keys it read: either way the value held now stands.
                "strip_text": strip_text(paper, held.get("strip_text")),
                "all_screens": all_screens(paper, held.get("all_screens")),
                "kde_wallpapers": kde_wallpapers(paper, held.get("kde_wallpapers")),
            }
            # A `mode` sent here is not stored and not silently dropped either: it is a change to
            # the desktop rather than a setting of this app's, and `SetWallpaperMode` is the door
            # for it. Answering it here as well would put the write in two places.
        self.d.config.save()
        if strength_moved:
            # Written before the windows are told, so that a failure halfway leaves the number and
            # the windows disagreeing in the direction that can be put right by asking again.
            self.d.restrike_transparency(was_strength)
        if was_paused and not self.d.config.paused:
            self.d.apply_defaults()
        if self.d.config.colour_screen != screen_was and auto_was and self.d.config.auto_colour:
            # Only while the colour was coming from a wallpaper and still is: the switch being
            # flicked on in the same breath -- which putting the settings back after *Restore
            # defaults* does -- takes no colour, the same as flicking it on alone.
            self.d.follow_colour_screen(screen_was)
        self.changed()
        return "ok"

    @dbus.service.method(MANAGER_IFACE, in_signature="ssb", out_signature="s")
    def SetSwitch(self, window_class, name, value):
        r = self.d.set_switch(str(window_class), str(name), bool(value))
        self.changed()
        return r

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def SetSwitches(self, payload):
        """`{class: {switch: bool}}` — several windows' switches in one transaction."""
        r = self.d.set_switches(json.loads(str(payload)))
        self.changed()
        return r

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def SetColumn(self, payload):
        """`{"switch": str, "value": bool}` -- a column's box on the Windows tab: that switch for
        every window met but those keeping it as set by hand, and for every new window, in one
        transaction. See `WindowsPart.set_column`."""
        try:
            d = json.loads(str(payload))
        except json.JSONDecodeError as e:
            return f"error: {e}"
        if not isinstance(d, dict) or not isinstance(d.get("switch"), str) \
                or not isinstance(d.get("value"), bool):
            return "error: expected a switch's name and true or false"
        r = self.d.set_column(d["switch"], d["value"])
        self.changed()
        return r

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def SetOwnTransparency(self, payload):
        """`{"class": str, "strength": int | null}` — one window's own number, or null to take
        it away. See `Daemon.set_own_transparency`."""
        try:
            d = json.loads(str(payload))
        except json.JSONDecodeError as e:
            return f"error: {e}"
        if not isinstance(d, dict):
            return "error: expected an object"
        r = self.d.set_own_transparency(d.get("class"), d.get("strength"))
        self.changed()
        return r

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def SetWindowLists(self, payload):
        """`{"float": {class: bool}, "animate": {class: bool}}`, applied as one batch."""
        d = json.loads(str(payload))
        r = self.d.set_window_lists({k: (d.get(k) or {}) for k in LIST_SWITCHES})
        self.changed()
        return r

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def Wallpapers(self):
        """What there is to choose from, what is on screen now, and what is in the way."""
        return json.dumps(self.d.wallpapers())

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def Screens(self, payload):
        """`{"names": ["HDMI-A-1", ...]}` -- the outputs the window knows of -- answered with the
        screen each is now, whether it is the primary, and the wallpaper it shows; with how many
        screens the shell counts and the screen the colour comes from. A read.

        The names come from the window because nothing else here can list them: the shell can
        only say which screen a name it is given is (`wallpaper.snapshot`)."""
        try:
            asked = json.loads(str(payload))
            names = [str(n) for n in (asked.get("names") or []) if n] if isinstance(asked, dict) \
                else []
        except (json.JSONDecodeError, TypeError):
            names = []
        return json.dumps(self.d.screens(names))

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def PrepareColour(self, payload):
        """`{"target": "file://..."}` — work this wallpaper's colour out now, before it is wanted.

        Answered at once; the work runs on a thread of its own, beside the loop (`warm_colour`).
        The picker calls it as the selection settles, so that by the time somebody presses Enter
        the answer is a file read rather than a run of ffmpeg. Nothing is applied and nothing is
        written but the cache.
        """
        if not self.d.config.auto_colour:
            return "ok"        # nothing will ever ask, so nothing is worth working out
        target = str(json.loads(str(payload)).get("target", ""))
        mode = theme.current()["mode"]
        if target and mode in theme.MODES:
            self.d.warm_colour(target, mode)
        return "ok"

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def SetWallpaperMode(self, payload):
        """`{"mode": "image" | "video"}` — put that kind of wallpaper on the activity in use.

        The picker is not told what to list; it reads what the desktop is wearing. So this is the
        whole of the other direction, and there is no second value anywhere to keep in step.
        """
        r = self.d.set_wallpaper_mode(str(json.loads(str(payload)).get("mode", "")))
        self.changed()
        return r

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def SetVideoPause(self, payload):
        """`{"pause": "0" | "1" | "2" | "3"}` -- when the video wallpaper pauses, the plugin's own
        setting, on every desktop of the activity in use. See `Daemon.set_video_pause`."""
        try:
            d = json.loads(str(payload))
        except json.JSONDecodeError as e:
            return f"error: {e}"
        r = self.d.set_video_pause(str((d if isinstance(d, dict) else {}).get("pause", "")))
        self.changed()
        return r

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def SetWallpaper(self, payload):
        """`{"target": "file://...", "screen": "HDMI-A-1"}` — on the activity in use, and no other.

        `screen` is an output's name, and the wallpaper goes on that screen alone; without one it
        goes on every screen of the activity. The other activity keeps its own either way, which is
        the whole reason the script asks the shell for `desktopsForActivity(currentActivity())`
        rather than for every desktop there is.
        """
        d = json.loads(str(payload))
        r = self.d.set_wallpaper(str(d.get("target", "")), str(d.get("screen") or ""))
        self.changed()
        return r

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def Theme(self):
        """The desktop's colours: the mode, the preset, a colour of your own, and what is
        missing."""
        return json.dumps(self.d.theme())

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def SetTheme(self, payload):
        """`{"mode": "dark", "preset": "nord", "accent": "203,166,247", "tint": 0.25}`.

        Asking for what is already on screen does nothing and says so with silence. That is not a
        nicety: the desktop's own tool answers "already set" and exits successfully, so a redundant
        step would look like it worked while the palette it was meant to change stayed put.
        """
        #: The only caller that passes `from_preset`, and the only one that should: this is the
        #: Colours box, which is somebody choosing. See `set_theme` for why the others -- a
        #: profile, the KyprX folder, *Restore defaults* -- must not.
        r = self.d.set_theme(json.loads(str(payload)), from_preset=True)
        self.changed()
        return r

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def Groups(self):
        """Every group the settings tabs read, what each one defaults to, and this app's own
        opinion about all of it.

        Three kinds of thing in one reply, and they are not the same kind. The bare names are what
        the config files say. The `_defaults` names are what the decoration and the compositor say
        applies when the file is silent -- without those the interface drew every unset switch off,
        including the ones that ship on, and then wrote that false reading the moment anyone
        touched it. And `kyprx_defaults` is this app's declaration, sent for whoever asks --
        nothing in the interface shows it today -- and nothing on a form may edit it.

        The tiling is KyprX's own, so its reply carries what only this app can say about it: the
        zone layouts and arrangements as the daemon reads them (`tiling_arrangements`: what the
        stored value means, whether the file stores any, and what is wrong with what it stores),
        and where the tiling stands (`tiling_state`, read the way the engine's own answer is). What
        the value means is always version 2 -- the upgrade of one stored in version 1
        (`tiling.arrangements_of`) -- so the window reads one shape whatever the file holds, and
        the file keeps what it holds until something is edited. Its `tiling_defaults` carry KyprX's
        own zone layouts and arrangements as their canonical text, in version 2 as well.
        """
        tx = writer.Transaction()
        shipped = shipped_defaults()
        group = dict(tx.kwin.groups.get(effects.TILING_GROUP, {}))
        arrangements, stored, problem = tiling.arrangements_of(group)
        return json.dumps({
            "klassy": {g: dict(tx.klassy.groups.get(g, {})) for g in KLASSY_GROUPS},
            "klassy_defaults": shipped["klassy"],
            "decoration": dict(tx.kwin.groups.get(DECORATION_GROUP, {})),
            "decoration_defaults": shipped["decoration"][""],
            "windows": dict(tx.kwin.groups.get(WINDOWS_GROUP, {})),
            "windows_defaults": shipped["windows"][""],
            "blur": dict(tx.kwin.groups.get(effects.BLUR_GROUP, {})),
            "blur_defaults": shipped["blur"][""],
            "blur_mode": effects.blur_mode(tx.kwin),
            "geometry": dict(tx.kwin.groups.get(effects.GEOMETRY_GROUP, {})),
            "geometry_defaults": shipped["geometry"][""],
            #: Text only: a key with no value (`[$d]`) means its default, the same as no key, and
            #: is the one thing in a group JSON cannot carry as it is.
            "tiling": {k: v for k, v in group.items() if isinstance(v, str)},
            "tiling_defaults": shipped["tiling"][""],
            "tiling_arrangements": {"value": arrangements, "stored": stored, "problem": problem},
            "tiling_state": self.d.tiling_state_now(tx.kwin),
            "plugins": {p: effects.plugin_enabled(tx.kwin, p)
                        for p in (effects.BLUR_PLUGIN, effects.GEOMETRY_PLUGIN)},
            "kyprx_defaults": defaults.SETTINGS,
            #: So that each tab can say when what it sets has nothing to act on -- see `Requirements`.
            "needs": self.d.needs(),
        })

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def SetGroups(self, payload):
        """What a settings tab changed, plus the defaults that tab is responsible for.

        `enforce` names pages, and the values come from `daemon/defaults.py` rather than from the
        interface. That is deliberate: a setting that left the interface has no control to read it
        back from, so the interface has no business carrying its value. Enforcing here also means
        it is exercised by `scripts/drive.py`, which never runs the interface at all.

        The enforced keys are written **first** and the tab's own keys after, so a control that is
        still on screen always wins over a declaration -- they never overlap today, and the order
        makes a future overlap harmless rather than baffling.

        **The zone layouts and arrangements are checked before anything is written** and written as
        their one canonical text, in the version they came in (`tiling.canonical`): version 2 from
        the window, which sends nothing else, and version 1 from a script that still writes it.
        What the window built and what a script hand-wrote are the same text when they are the
        same value, and a value that breaks a rule answers `error: <sentence>` with nothing written
        at all. A value the file already holds in other words -- spelt by hand, or in the other
        version, which is how a desk keeps its version-1 text until somebody edits on the Tiling
        tab -- is left in those words (`_tiling_value_alike`, as the KyprX folder and the settings
        file leave them): sending back what `Groups` just read -- the file's own text, or what it
        means in version 2 -- must write nothing, and rewriting somebody's text to say the same
        thing is a write nobody asked for. `null` in their place takes the key away, which is
        KyprX's own zone layouts and arrangements back -- after a copy of the desk, because they
        are somebody's work and nothing else keeps them. A `null` for any other tiling key takes
        that key away too, back to its default.
        """
        d = json.loads(str(payload))
        given = {source: dict(d.get(source) or {}) for source in
                 ("decoration", "windows", "blur", "geometry", "tiling")}
        if "arrangements" in given["tiling"]:
            if given["tiling"]["arrangements"] is None:
                stored = writer.Transaction().kwin.groups.get(effects.TILING_GROUP, {})
                if ("arrangements" in stored and not self.d.take_snapshot(
                        "before KyprX's zone layouts and arrangements")):
                    return ("error: a copy of the desk could not be kept first, so nothing was "
                            "changed")
            else:
                try:
                    given["tiling"]["arrangements"] = tiling.canonical(
                        given["tiling"]["arrangements"])
                except tiling.ArrangementsError as e:
                    return f"error: {e}"
        if given["tiling"].get("desktopArrangements") is not None:
            # Checked before anything is written, and written as its one canonical text; empty,
            # it takes the key away, which is every desktop on the first in the rotation again.
            try:
                given["tiling"]["desktopArrangements"] = tiling.canonical_desktops(
                    given["tiling"]["desktopArrangements"])
            except tiling.DesktopsError as e:
                return f"error: {e}"

        def build(tx):
            moved = set()
            for page in (d.get("enforce") or []):
                moved |= write_declared(tx, defaults.slice_for(str(page)))
            for group, entries in (d.get("klassy") or {}).items():
                for key, value in entries.items():
                    tx.klassy.set(group, key, value)
            for group, source in ((DECORATION_GROUP, "decoration"),
                                  (WINDOWS_GROUP, "windows"),
                                  (effects.BLUR_GROUP, "blur"),
                                  (effects.GEOMETRY_GROUP, "geometry"),
                                  (effects.TILING_GROUP, "tiling")):
                for key, value in given[source].items():
                    held = tx.kwin.get(group, key)
                    if source == "tiling" and value is None:
                        tx.kwin.delete_key(group, key)
                    elif (source == "tiling" and key in ("arrangements", "desktopArrangements")
                          and isinstance(held, str)
                          and self.d._tiling_value_alike(key, held, value)):
                        # The one value made over before it gets here -- it is canonical by now --
                        # so without this a text spelt by hand, or one in version 1, sent back as
                        # `Groups` read it would be rewritten to say the same at every apply.
                        continue
                    else:
                        tx.kwin.set(group, key, value)
            for plugin, enabled in (d.get("plugins") or {}).items():
                effects.set_plugin_enabled(tx.kwin, plugin, bool(enabled))
            # The geometry animation belongs in this list and was missing: its group was written
            # and nothing ever re-read it, so changing the duration did nothing until the next
            # reconfigure somebody else asked for. An empty diff still reloads nothing at all --
            # `writer.Transaction.commit` returns before the reload block when there is no change.
            # The Klassy groups by name, because the reload they need depends on which they are;
            # every other source is one flat section and carries an empty group name.
            note_reloads(tx, moved
                         | {("klassy", group) for group in (d.get("klassy") or {})}
                         | {(s, "") for s in ("decoration", "windows", "plugins",
                                              "geometry", "blur", "tiling") if d.get(s)})

        diff = writer.run(build)
        if writer.dry_run() and diff:
            self.d.log("would have written:\n" + diff)
        self.changed()
        return "ok"

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def RestoreDefaults(self):
        """`Daemon.restore_defaults`: "ok", "partial: …" or "error: …". A copy of the desk is kept
        first, and the newest entry of `Snapshots` is it."""
        answer = self.d.restore_defaults()
        self.changed()
        return answer

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def RestorePreview(self):
        """What *Restore defaults* would change, in plain words. Writes nothing; "" when it would
        change nothing."""
        return self.d.restore_defaults(preview=True)

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def LookOffer(self):
        """`{"due": bool, "changes": str}`: whether the settings window, opening, is to ask about
        KyprX's look, and what putting it on would change, in plain words (`look_offer`). Writes
        nothing; `changes` is "" unless due."""
        return json.dumps(self.d.look_offer())

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def AnswerLook(self, payload):
        """`{"take": true}` keeps a copy of the desk and puts KyprX's look on; `{"take": false}`
        keeps the desk's own. Either is remembered, so the question is not asked again
        (`answer_look`). "ok", "partial: …" or "error: …". Only putting the look on changes the
        desk, so only that says so."""
        try:
            d = json.loads(str(payload))
        except json.JSONDecodeError as e:
            return f"error: {e}"
        take = d.get("take") if isinstance(d, dict) else None
        if not isinstance(take, bool):
            return "error: say take: true or false"
        answer = self.d.answer_look(take)
        if take and not answer.startswith("error"):
            self.changed()
        return answer

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def Snapshots(self):
        """Every copy of the desk, newest first, as JSON: name, when, why, whether it is one never
        to be thrown away, whether it lives only in a dry run's memory, and why it cannot be put
        back when it cannot."""
        return json.dumps({"snapshots": snapshot.listing(), "folder": snapshot.DIRECTORY})

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def GoBackPreview(self, name):
        """What going back to this copy would change, in plain words; "error: …" when it cannot."""
        desk = snapshot.load(str(name))
        trouble = snapshot.why_not(desk)
        return f"error: {trouble}" if trouble else self.d.restore_desk(desk, preview=True)

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def GoBack(self, name):
        """Put this copy of the desk back, after keeping a copy of the desk as it is now -- so going
        back is itself something to go back from."""
        desk = snapshot.load(str(name))
        trouble = snapshot.why_not(desk)
        if trouble:
            return f"error: {trouble}"
        if not self.d.take_snapshot(f"before going back to {name}"):
            return "error: a copy of the desk could not be kept first, so nothing was changed"
        self.d.leave_off()
        answer = self.d.restore_desk(desk)
        self.changed()
        return answer

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def TakeOffPreview(self):
        """What taking KyprX off this desk would change, in plain words. Writes nothing."""
        return self.d.take_off(preview=True)

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def TakeOff(self):
        """`Daemon.take_off`. "ok", or "error: …"."""
        answer = self.d.take_off()
        self.changed()
        return answer

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def PutBack(self):
        """`Daemon.put_back`. "ok", "partial: …" or "error: …"."""
        answer = self.d.put_back()
        self.changed()
        return answer

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def Folder(self):
        """Where the KyprX folder is, and what the last pass found: in step, waiting (and for
        what), applied (when, which files, what the folder won over the desk, what did not go in,
        and the copy kept before), or a problem (and which)."""
        return json.dumps(self.d.folder_status())

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def DescribeFolder(self):
        """The KyprX folder as the desk would write it right now, file by file, as JSON. A read:
        what a pass would write, whether or not it will."""
        return json.dumps(folder.texts_of(self.d.describe()))

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def PreviewFolder(self, payload):
        """What applying these folder files -- `{file: text}`, the shape `DescribeFolder` answers
        with -- would change on the desk, in plain words. Writes nothing. "error: …" with every
        problem when the files cannot be applied. Applied whole, as a new machine would."""
        try:
            texts = json.loads(str(payload))
        except json.JSONDecodeError as e:
            return f"error: {e}"
        if not isinstance(texts, dict):
            return "error: the files have to be an object of names and texts"
        areas, _, problems = folder.parse({str(k): str(v) for k, v in texts.items()})
        problems = problems or self.d.folder_problems(areas)
        if problems:
            return "error: " + "; ".join(problems)
        words, _ = self.d.apply_areas(areas, preview=True)
        return words

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def SyncFolder(self):
        """Bring the folder and the desk into step now, rather than in a moment -- what the Settings
        tab asks before it opens the folder, so what is opened is the desk as it is."""
        self.d._folder_due()
        return json.dumps(self.d.folder_status())

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def Shortcuts(self):
        """Every action of the fixed lists with its keys (`shortcuts.bindings`), and `screen`: the
        screen the compositor counts as active (`reload.active_output`), "" when it cannot say.
        The cheatsheet opens there, centred by its rule, and lays itself out for that screen's
        height before it is shown -- the reason the picker is told the same, in `Wallpapers`."""
        return json.dumps({"actions": shortcuts.bindings(self.d.config.cheatsheet_keys),
                           "screen": reloader.active_output()})

    @dbus.service.method(MANAGER_IFACE, in_signature="sai", out_signature="s")
    def SetShortcut(self, action, keys):
        """Rebind one of the compositor's own actions. Kept as it was, and delegating."""
        return self.SetShortcutIn(shortcuts.KWIN_COMPONENT, action, keys)

    @dbus.service.method(MANAGER_IFACE, in_signature="ssai", out_signature="s")
    def SetShortcutIn(self, component, action, keys):
        """Rebind an action in any component: `keys` in place of the key it shows first.

        The component travels in an argument of its own rather than glued to the name: action
        names already contain spaces — "Walk Through Windows" — and nothing promises one will
        never contain a slash.

        A key another action holds is refused here, naming the holder -- the interface asks first
        and comes through `RebindShortcut` to take it over. On Plasma 6.7 nothing else refuses it:
        the registry would keep it on both actions and run the one registered first.
        """
        try:
            held = shortcuts.keys_of(str(action), str(component))
        except (KeyError, dbus.DBusException) as e:
            return f"error: {e}"
        r = self.d.rebind_shortcut(str(component), str(action), held[0] if held else [],
                                   [int(k) for k in keys], take=False)
        self.changed()
        return r

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def ShortcutHolders(self, payload):
        """`{"component", "action", "keys": [int]}` -> the actions that hold those keys now,
        other than this one, as a list. A read, and so the same in dry run: it is what lets a dry
        run say that a key would have been taken from somebody."""
        try:
            d = json.loads(str(payload))
            keys = [int(k) for k in d.get("keys") or []]
            exclude = (str(d.get("component") or shortcuts.KWIN_COMPONENT), str(d.get("action")))
            return json.dumps(shortcuts.holders(keys, exclude=exclude))
        except (ValueError, TypeError, AttributeError, dbus.DBusException) as e:
            return f"error: {e}"

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def RebindShortcut(self, payload):
        """`{"component", "action", "old": [int], "new": [int], "take": bool}` -- put `new` where
        `old` was, by value. With `take`, first take `new` away from whatever other action holds
        it. See `Daemon.rebind_shortcut`."""
        try:
            d = json.loads(str(payload))
            old = [int(k) for k in d.get("old") or []]
            new = [int(k) for k in d.get("new") or []]
        except (ValueError, TypeError, AttributeError) as e:
            return f"error: {e}"
        r = self.d.rebind_shortcut(str(d.get("component") or shortcuts.KWIN_COMPONENT),
                                   str(d.get("action") or ""), old, new, bool(d.get("take")))
        self.changed()
        return r

    @dbus.service.method(MANAGER_IFACE, in_signature="sai", out_signature="s")
    def SetCheatsheetKey(self, action_key, keys):
        """Which of an action's combinations the cheatsheet shows. Nothing is rebound.

        An empty list forgets the choice, which puts the action back on whatever the desktop lists
        first.
        """
        chosen = dict(self.d.config.cheatsheet_keys)
        wanted = [int(k) for k in keys]
        if wanted:
            chosen[str(action_key)] = wanted
        else:
            chosen.pop(str(action_key), None)
        self.d.config.cheatsheet_keys = chosen
        self.d.config.save()
        self.changed()
        return "ok"

    @dbus.service.method(MANAGER_IFACE, in_signature="b", out_signature="s")
    def Requirements(self, refresh):
        """The four projects KyprX is built on, each as it stands here: installed or not, its
        version, whether the compositor runs it, and what to do when something is wrong. From
        memory unless `refresh` -- see `InstallationPart.needs`. Writes nothing."""
        return json.dumps(self.d.needs(refresh=bool(refresh)))

    @staticmethod
    def _removal_answers(payload) -> tuple[bool, bool] | str:
        """The two answers removing KyprX needs, `revert` and `keep_folder`, or the sentence that
        refuses: both are asked, and a missing one is not taken to mean anything."""
        try:
            d = json.loads(str(payload))
        except json.JSONDecodeError as e:
            return f"error: {e}"
        if not isinstance(d, dict) or not all(isinstance(d.get(k), bool)
                                              for k in ("revert", "keep_folder")):
            return "error: both questions have to be answered: revert and keep_folder"
        return d["revert"], d["keep_folder"]

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def RemovePreview(self, payload):
        """What taking KyprX off this computer would do, for the two answers in the JSON
        `{"revert": bool, "keep_folder": bool}`. Writes nothing."""
        answers = self._removal_answers(payload)
        if isinstance(answers, str):
            return answers
        return self.d.remove_preview(*answers)

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def Remove(self, payload):
        """Take KyprX off this computer, as far as this user's files go
        (`InstallationPart.remove_kyprx`). JSON: `answer`, and when it went through, `done`,
        `kept`, `command` and `dry_run`. Unless in a dry run, the daemon stops a moment after
        answering, and `Changed` is not sent: a window reading again would start it again."""
        answers = self._removal_answers(payload)
        if isinstance(answers, str):
            return json.dumps({"answer": answers})
        result = self.d.remove_kyprx(*answers)
        if writer.dry_run():
            self.changed()
        return json.dumps(result)

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def Diagnostics(self):
        """What the Settings tab's Problems box is drawn from: the counts and orphans of the
        rules and overrides, the compositor script and its actions, the versions, the theme's
        trouble, and where KyprX's tiling stands (`tiling_state`, read like the engine's answer).
        A read."""
        tx = writer.Transaction()
        d = policy.diagnostics(tx, self.d.tiling_on_now(tx.kwin))
        d["dry_run"] = writer.dry_run()
        #: In every folder the compositor looks in, the user's first: a package puts the script
        #: under the system's prefix, `install.sh` under the user's own.
        d["script_installed"] = bool(about.data_path(
            f"kwin/scripts/{SCRIPT_PLUGIN}/metadata.json"))
        d["script_enabled"] = effects.plugin_enabled(tx.kwin, SCRIPT_PLUGIN)
        #: The version this daemon runs, and the one on disk: they differ after an update, until
        #: the daemon starts again. The window compares the first with its own.
        d["version"] = about.RUNNING
        d["version_on_disk"] = about.version()
        d["from_package"] = about.from_package()
        #: Every action of the compositor script's that the registry has not got, rather than a
        #: field per action: all of them, the keyless two the daemon invokes included -- the
        #: tiling's settings reach it through one of those. An action added to the script does not
        #: exist until the compositor has loaded that version of it, and the compositor keeps what
        #: it compiled of a declarative script for the whole session, so after an update that is
        #: the next login (the head of `kwin-script/contents/ui/main.qml` has the finding).
        #: Reported rather than repaired: nothing a daemon can do inside the session loads it
        #: sooner. One read of the registry for all of them, not one each.
        held = set(shortcuts.script_actions_held())
        d["missing_actions"] = [a for a in shortcuts.SCRIPT_ACTIONS if a not in held]
        d["tiling_state"] = self.d.tiling_state_now(tx.kwin)
        d["outline_preset"] = (klassy.PRESET_PREFIX + klassy.OUTLINE_OFF_PRESET
                               in tx.presets.groups)
        #: Reported, never repaired. Putting these back means applying the global theme, which
        #: rewrites six files in `kdedefaults` including the cursor and splash defaults -- that is
        #: somebody pressing Apply on the Appearance tab, not a daemon coming up.
        d["theme_trouble"] = theme.invariants(theme.current())
        d["theme_ok"] = not d["theme_trouble"]
        #: The decoration's leftover `[Exceptions]` group, and what it does to every window with no
        #: override of its own. The daemon removes it by itself (`clear_stray_exceptions`), so it
        #: is reported only when it could not: a dry run, KyprX off the desk, a write that failed.
        stray = tx.klassy.groups.get(klassy.STRAY_EXCEPTIONS)
        d["stray_exceptions"] = ({"hide_titlebar": str(stray.get("HideTitleBar", ""))}
                                 if stray is not None else None)
        return json.dumps(d)

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def RemoveStrayExceptions(self):
        """The Problems box's button, for when the daemon could not remove the decoration's
        leftover group by itself. See `Daemon.remove_stray_exceptions`."""
        return self.d.remove_stray_exceptions()

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def Normalize(self):
        renamed = []

        def build(tx):
            renamed.extend(policy.normalize_rule_names(tx))

        diff = writer.run(build)
        if writer.dry_run() and diff:
            self.d.log("would have written:\n" + diff)
        self.changed()
        return json.dumps(renamed)

    # ------------------------------------------------------------ profiles

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def Profiles(self):
        """Every profile kept: its look, whether it is the look on the desktop now, and whether it
        can be put there. Beside them, the look the desktop is wearing -- what saving would keep.

        `current` is the same comparison a load makes, on the same reading of the desktop, so the
        line under the list and the load itself cannot contradict each other.
        """
        worn = self.d.worn_look()
        out = []
        for entry in self.d.profiles.entries:
            look = entry["look"]
            why = profiles.trouble(look)
            chosen = theme.preset(str((look.get("theme") or {}).get("preset") or ""))
            out.append({"name": entry["name"], "look": look, "trouble": why,
                        "current": not why and profiles.is_on(look, worn),
                        "preset_name": chosen.name if chosen else "",
                        "swatch": theme.swatch(chosen.scheme) if chosen else []})
        return json.dumps({"profiles": out, "worn": worn,
                           "trouble": self.d.profiles.unreadable})

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def SaveProfile(self, payload):
        """`{"name": "…", "replace": false}` -- keep the look the desktop is wearing under a name.

        A `look` may be handed in instead, checked and typed first. The interface never does;
        `scripts/drive.py` does, because in dry run the desktop's look never changes and a profile
        that differs from it is the only positive control there is.

        Refused when the desktop's colours are not one of the presets: a look with no preset
        would land on the mode's own default when loaded, and could never read as the one on.
        """
        d = json.loads(str(payload))
        if "look" in d:
            try:
                look = profiles.normalise(d["look"])
            except ValueError as e:
                return f"error: {e}"
        else:
            now = theme.current()
            if now["mode"] not in theme.MODES:
                return ("error: the global theme is not one of Klassy's, so there is no look to "
                        "keep -- pick a mode under Colours first")
            if not now["preset"]:
                return ("error: the colours on the desktop are not one of the presets -- pick one "
                        "under Colours first")
            look = self.d.worn_look()
        r = self.d.profiles.put(str(d.get("name") or ""), look, bool(d.get("replace")))
        if r:
            return r
        self.changed()
        return "ok"

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def LoadProfile(self, payload):
        """`{"name": "…"}` -- put that profile on the desktop. See `Daemon.apply_look`."""
        name = str(json.loads(str(payload)).get("name") or "")
        entry = self.d.profiles.get(name)
        if entry is None:
            return f"error: there is no profile called {name.strip() or '(nothing)'}"
        self.d.log(f"loading the profile {entry['name']}")
        r = self.d.apply_look(entry["look"])
        self.changed()
        return r

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def RenameProfile(self, payload):
        """`{"name": "…", "to": "…"}`. The look is untouched."""
        d = json.loads(str(payload))
        r = self.d.profiles.rename(str(d.get("name") or ""), str(d.get("to") or ""))
        if r:
            return r
        self.changed()
        return "ok"

    @dbus.service.method(MANAGER_IFACE, in_signature="s", out_signature="s")
    def DeleteProfile(self, payload):
        """`{"name": "…"}`. Nothing on the desktop changes."""
        r = self.d.profiles.delete(str(json.loads(str(payload)).get("name") or ""))
        if r:
            return r
        self.changed()
        return "ok"

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="s")
    def Refresh(self):
        self.d.request_inventory()
        return "ok"

    @dbus.service.signal(MANAGER_IFACE, signature="")
    def Raise(self):
        """Asked for when a second interface starts: the one already open should come forward.

        A signal rather than a call, because the daemon does not know who is listening — nought,
        one or, for the moment it takes the second one to quit, two.
        """

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="b",
                         sender_keyword="sender")
    def ClaimInterface(self, sender=None):
        """Register as *the* open interface. False means one is already open and was told to come
        forward, so the caller should quit rather than put a second window on screen.

        Two settings windows are not a cosmetic duplication: each subscribes to the daemon's
        changes and writes back, so a colour picked in one races a colour picked in the other, and
        the shortcut editor's suspend-everything is desktop-wide — whichever window closes first
        hands the desktop its shortcuts back while the other is still waiting for a key.

        **The claim is the caller's connection, not a flag.** A flag would be set by an interface
        that was then killed rather than closed, and would stay set for the life of the daemon —
        locking every later interface out of a window it is entitled to. A connection cannot lie
        about being gone: the bus forgets it the moment the process does.
        """
        holder = self.d.interface_owner
        if holder and holder != sender and self._on_the_bus(holder):
            self.Raise()
            return False
        self.d.interface_owner = str(sender) if sender else None
        self.d.watch_interface(self.d.interface_owner)
        #: Somebody opening KyprX is when something may have been installed since the last look.
        self.d.needs(refresh=True)
        return True

    @dbus.service.method(MANAGER_IFACE, in_signature="", out_signature="",
                         sender_keyword="sender")
    def ReleaseInterface(self, sender=None):
        if self.d.interface_owner == str(sender):
            self.d.interface_owner = None

    @staticmethod
    def _on_the_bus(unique_name: str) -> bool:
        try:
            bus = dbus.SessionBus().get_object("org.freedesktop.DBus", "/org/freedesktop/DBus")
            return bool(dbus.Interface(bus, "org.freedesktop.DBus").NameHasOwner(unique_name))
        except dbus.DBusException:
            return False
