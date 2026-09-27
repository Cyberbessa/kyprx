"""The settings file: KyprX's whole setup as one JSON file, the backup an earlier version's
*Export to a file...* button wrote.

`import_settings` is what the Settings tab's *Apply a backup file* runs, once the API has kept a
copy of the desk: it writes the file back through the same doors the tabs use, part by part.
`export_settings` still writes the file, over the API, and `SETTINGS_VERSIONS` lists every shape
of it this version reads. The KyprX folder is how the setup travels now; its code is in
`daemon/kyprd_desk.py` and `daemon/kyprd_folder.py`.

The daemon's state it reads or writes, all of it created in `Daemon.__init__`: `config`,
`profiles`, `state`.
"""

from __future__ import annotations

from dataclasses import asdict

import dbus

import effects
import klassy
import policy
import shortcuts
import theme
import writer
from declared import COLOUR_CACHED_GROUPS
from kwin_config import DECORATION_GROUP, WINDOWS_GROUP
from kyprd_names import OVERLAY_PATTERNS, SWITCHES
from state import WALLPAPER_LAYOUTS, Defaults, key_sequence, own_strengths


#: What the settings file calls the compositor's `[Windows]` group. **Not** the same word the
#: interface uses for it, and that is the whole point: the file already had a `windows` key
#: holding the per-window choices, and reusing the word put two entries of that name in one dict
#: literal. The second silently won, and every export lost the per-window rows it exists to carry.
EXPORT_WINDOW_BEHAVIOUR = "window_behaviour"


class SettingsFilePart:
    """Writing the setup out as one file, and reading it back in."""

    # ------------------------------------------------------------ the settings file

    def export_settings(self) -> dict:
        tx = writer.Transaction()
        return {
            "version": 6,
            "windows": [{k: r[k] for k in ("class", *SWITCHES)}
                        for r in self.table()
                        if not r["titlebar"] or not r["blur"] or not r["outline"]
                        or not r["transparency"]],
            "button_colours": {b: klassy.button_colours(tx.klassy, b) for b in klassy.BUTTONS
                               if klassy.button_colours(tx.klassy, b)},
            "defaults": asdict(self.config.defaults),
            #: The strength ticked windows share, and whether the app speaks up. Both are
            #: settings of this app's own with a control on screen, and both were missing: a file
            #: carrying `transparency: true` for a dozen windows and no number meant two machines
            #: drawing the same windows see-through at two different strengths.
            #:
            #: `paused` is deliberately not here. It is not a setting, it is what you untick while
            #: you are changing something by hand — and a backup that arrived with new windows
            #: being left alone would look like an app that is broken.
            "transparency": int(self.config.transparency),
            #: The windows with a number of their own. A window's tick is in `windows` above; this
            #: is how see-through it is when ticked, where that is not the strength.
            "own_transparency": dict(self.config.own_transparency),
            "notify": bool(self.config.notify),
            #: **Every group of the decoration's file**, and not only the seven this app has
            #: controls in, so a setting changed in the decoration's own dialog travels even when
            #: it lands somewhere this app has never heard of. It overlaps `button_colours` above,
            #: which is the same keys read back as per-button objects — the overlap is harmless,
            #: and it is what makes the inactive overrides travel, which they did not before.
            #:
            #: Two kinds are left out. The per-window exceptions have a block of their own below,
            #: because their indices have to be rewritten rather than merged, and the
            #: `Default Windeco Exception N` beside them ship with the package and are nobody's to
            #: carry. And `[Global]` is the decoration's bookkeeping about *this machine* — which
            #: bundled presets it has already imported, which look-and-feel its settings came from
            #: — so carrying it across would stop the decoration importing its own presets there.
            "klassy": {g: dict(entries) for g, entries in tx.klassy.groups.items()
                       if "Windeco Exception" not in g and g != "Global"},
            #: The per-window overrides whole, every key of them: the ones this app writes and the
            #: ones somebody typed into the decoration's dialog — an opaque bar, a border size, a
            #: preset pointed at. The four columns in `windows` above are this app's *reading* of
            #: these and are what rebuilds the compositor's rules; this is the file itself.
            #:
            #: This app's own overlays are dropped. An overlay managed as a window puts the
            #: theme's shadow round a picker that is mostly transparent, which is the whole reason
            #: `daemon/policy.py` refuses to manage one and takes it back off on every start.
            #: Raw, as `klassy.read_groups` says: a backup that came back re-spelled is a backup
            #: that shows as a diff on an import which changed nothing.
            "klassy_exceptions": [g for g in klassy.read_groups(tx.klassy)
                                  if g.get("ExceptionWindowPropertyPattern")
                                  not in OVERLAY_PATTERNS],
            #: The decoration's presets, minus `[Global]` for the reason above. One made in its own
            #: dialog is somebody's setting like any other; the one this app writes is put back by
            #: the daemon whether it travels or not.
            "klassy_presets": {g: dict(entries) for g, entries in tx.presets.groups.items()
                               if g.startswith(klassy.PRESET_PREFIX)},
            #: The profiles, exactly as `daemon/profiles.py` keeps them. Until now this was the one
            #: file this app owns with no way out of the machine at all.
            "profiles": [{"name": e["name"], "look": e["look"]} for e in self.profiles.entries],
            "decoration": dict(tx.kwin.groups.get(DECORATION_GROUP, {})),
            EXPORT_WINDOW_BEHAVIOUR: dict(tx.kwin.groups.get(WINDOWS_GROUP, {})),
            "blur": dict(tx.kwin.groups.get(effects.BLUR_GROUP, {})),
            "geometry": dict(tx.kwin.groups.get(effects.GEOMETRY_GROUP, {})),
            "tiling": dict(tx.kwin.groups.get(effects.TILING_GROUP, {})),
            "plugins": {p: effects.plugin_enabled(tx.kwin, p)
                        for p in (effects.BLUR_PLUGIN, effects.GEOMETRY_PLUGIN,
                                  effects.TILING_PLUGIN)},
            #: Keyed by `shortcuts.qualified`, so a bare name still means the compositor's own
            #: component and every settings file written before this app knew about components reads
            #: exactly as it did.
            #:
            #: **Every sequence an action carries**, not the first alone. KRunner arrives with
            #: three and two of the window actions carry a second, and a file that recorded one of
            #: them recorded the wrong number of them. What the import *writes* is still the first,
            #: through `shortcuts.set_primary`, which keeps whatever else the action has — a second
            #: key is usually the desktop's own, and rebinding it is not restoring anything.
            "shortcuts": {a["key"]: a["keys"] for a in shortcuts.bindings() if a["keys"]},
            "cheatsheet_keys": dict(self.config.cheatsheet_keys),
            #: The picker's own settings -- its layout, what it lists, where. **Not** which
            #: wallpaper is on screen: that is a per-activity fact in somebody else's config, and
            #: a settings file restored from a backup changing your wallpaper would be a nasty surprise.
            "wallpaper": dict(self.config.wallpaper),
            #: The **choice**, and not the identifiers it resolves to. A look-and-feel package
            #: name, a scheme file and a Plasma style mean nothing on a machine that has none of
            #: them, whereas "dark, Nord, this colour" degrades to a sentence saying that preset is
            #: not installed here. An export is for carrying a desktop to another machine.
            "theme": {**{k: theme.current()[k] for k in ("mode", "preset", "accent", "tint")},
                      #: Grouped with the colours here even though it sits at the top of
                      #: `config.json`, because that is what it is about. The two layouts do not
                      #: have to match, and the file reads better for the one it has.
                      "auto": self.config.auto_colour},
        }

    #: Version 6 is the one that stops leaving things out, and it is still the same shape of
    #: addition: an older file simply has none of the new blocks, and each of them is skipped when
    #: it is absent. What it adds is the strength, whether the app speaks up, the profiles, the
    #: decoration's groups outside the seven this app has controls in, the per-window exceptions
    #: whole, and its presets — and it widens `shortcuts` from one combination per action to all of
    #: them, which is why that one is read below in a way that takes either shape.
    #:
    #: Version 5 adds the Transparency column, and is the same shape of addition again: a window
    #: in an older file simply has no transparency in it, which reads as ticked — the value a
    #: window gets the first time it is seen.
    #:
    #: Settings file versions this app can read. **2 is still read**, because an export is a backup
    #: and refusing to read yesterday's is the one thing a backup must never do. What version 3
    #: adds is the compositor's window-behaviour group under a name of its own; a version 2 file
    #: simply has none, and everything else about it is unchanged. Version 4 adds the wallpaper
    #: picker's settings, and is the same shape of addition: an older file simply has none, and
    #: a version 4 file written before the picker had two layouts has no layout in it, which
    #: reads as the default. That is why this is not bumped every time that block grows a key.
    SETTINGS_VERSIONS = (2, 3, 4, 5, 6)

    def import_settings(self, settings: dict) -> str:
        if settings.get("version") not in self.SETTINGS_VERSIONS:
            return "error: unknown settings file version"
        # A version 2 file written by a version of this app that had the duplicate-key bug
        # carries a dict where the per-window list belongs. Reading it as a list would crash
        # halfway through the import, with the config half written.
        if not isinstance(settings.get("windows", []), list):
            return ("error: this settings file was written by a version with a known fault and lost "
                    "its per-window choices — the rest of it is still importable by hand")

        def build(tx):
            for group, entries in (settings.get("klassy") or {}).items():
                for key, value in entries.items():
                    tx.klassy.set(group, key, value)
            for group, key_source in ((DECORATION_GROUP, "decoration"),
                                      (WINDOWS_GROUP, EXPORT_WINDOW_BEHAVIOUR),
                                      (effects.BLUR_GROUP, "blur"),
                                      (effects.GEOMETRY_GROUP, "geometry"),
                                      (effects.TILING_GROUP, "tiling")):
                for key, value in (settings.get(key_source) or {}).items():
                    tx.kwin.set(group, key, value)
            for plugin, enabled in (settings.get("plugins") or {}).items():
                effects.set_plugin_enabled(tx.kwin, plugin, bool(enabled))
            for button, slots in (settings.get("button_colours") or {}).items():
                if button in klassy.BUTTONS:
                    klassy.set_button_colours(tx.klassy, button, slots)
            listed = settings.get("klassy_exceptions")
            if isinstance(listed, list):
                #: **Replaced, not merged**, which is what a backup means: a list that kept an
                #: override the file does not carry is not the list that was saved. Through
                #: `klassy.write_groups`, so the indices come out contiguous from zero -- the
                #: decoration's read loop stops at the first hole and everything past it
                #: disappears with no error at all -- and raw, and only when it differs from the
                #: list the file holds, read the way `klassy.read_groups` reads it: so "importing
                #: the settings that were just exported must produce an empty diff" holds whichever
                #: way the file keeps the list, one group per window or neighbours set alike
                #: together (`klassy.MERGED`), which is `compact_overrides`'s to change and not an
                #: import's.
                #:
                #: Anything written for one of this app's own overlays is dropped on the way in as
                #: well as on the way out. The daemon takes those off at every start, but only at
                #: a start, and until then a picker restored from a backup comes up decorated: the
                #: theme's outline round the *window* rather than round what it painted, the
                #: decoration's panel through its transparent parts, and its shadow around the
                #: whole of a window far larger than the pictures in it.
                wanted = [g for g in listed if isinstance(g, dict)
                          and g.get(klassy.PATTERN) not in OVERLAY_PATTERNS]
                if wanted != klassy.read_groups(tx.klassy):
                    klassy.write_groups(tx.klassy, wanted)
            #: The decoration's own presets, added rather than replaced -- the opposite of the list
            #: above, and for the opposite reason: an override names a preset, so one this machine
            #: has and the file does not is one a window here may be pointing at. Only groups under
            #: the preset prefix, so a `[Global]` in a hand-edited file cannot get in -- see the
            #: note beside it in `export_settings`.
            for group, entries in (settings.get("klassy_presets") or {}).items():
                if str(group).startswith(klassy.PRESET_PREFIX):
                    for key, value in (entries or {}).items():
                        tx.presets.set(group, key, value)
            if listed or settings.get("klassy_presets"):
                #: Whatever arrived, this app's own two-key preset has to exist: an override
                #: pointing at a preset that is not there is a window that silently keeps the
                #: outline it was meant to lose.
                klassy.ensure_outline_off_preset(tx.presets)
            tx.reload_kwin = True
            tx.reload_blur = True
            #: The outline's group and the button colours live in a cache the ordinary reconfigure
            #: does not invalidate -- `COLOUR_CACHED_GROUPS`, with the measurement beside it. This
            #: asked about the button colours alone, which meant a settings file that moved the
            #: outline's colour and carried no button colours left the decoration drawing the
            #: colour it already had: the file saying one thing and the window another until
            #: something else happened to reconfigure it.
            tx.reload_colours = bool(settings.get("button_colours")) or bool(
                COLOUR_CACHED_GROUPS & set(settings.get("klassy") or {}))
            tx.reload_tiling = bool(settings.get("tiling"))

        # Logged like every other write, and for the same reason: in dry run the log line is the
        # only trace a change leaves, so a writer that stays quiet is a writer nobody can check.
        diff = writer.run(build)
        if writer.dry_run() and diff:
            self.log("would have written:\n" + diff)

        if settings.get("defaults"):
            self.config.defaults = Defaults.from_dict(settings["defaults"])
            self.config.save()
        # The number goes in **before** the windows below and the restrike comes **after** them,
        # and both halves of that order matter. `apply_to` writes each window's opacity from
        # `config.transparency`, so a strength read afterwards would reach the file and not the
        # windows the same file just described; and a restrike run first would write every ticked
        # window once here and again a moment later, for one change.
        previous = int(self.config.transparency)
        if "transparency" in settings:
            try:
                self.config.transparency = min(max(int(settings["transparency"]), 1), 100)
            except (TypeError, ValueError):
                pass
        if "notify" in settings:
            self.config.notify = bool(settings["notify"])
        #: **Replaced, not merged**, like the profiles and the decoration's overrides: a list that
        #: kept a number the file does not carry is not the list that was saved. Before the rows,
        #: so each window the file names is written at its own number rather than at the strength
        #: and then again. A file with no such block -- anything written before there was one --
        #: leaves the list alone, which is what reading yesterday's backup has to mean.
        own_before = dict(self.config.own_transparency)
        if isinstance(settings.get("own_transparency"), dict):
            self.config.own_transparency = {
                c: n for c, n in own_strengths(settings["own_transparency"]).items()
                if self.own_allowed(c)}
        if ("transparency" in settings or "notify" in settings
                or self.config.own_transparency != own_before):
            self.config.save()
        for entry in settings.get("windows") or []:
            window_class = entry.get("class")
            if window_class:
                self.apply_to(window_class, policy.Switches(
                    **{k: bool(entry.get(k, True)) for k in SWITCHES}))
                self.state.mark_seen(window_class)
        if self.config.transparency != previous:
            # After the rows, so a window the file named is written once at the new number rather
            # than at the old one and then again. What is left for this is every other ticked
            # window -- the ones the file did not name, reached exactly as moving the control
            # reaches them.
            self.restrike_transparency(previous)
        # Last, so a window whose number the file took away goes to the strength the file brought.
        self.restrike_own(own_before)
        listed = settings.get("shortcuts")
        for action, keys in sorted((listed if isinstance(listed, dict) else {}).items()):
            component, action_id = shortcuts.unqualified(str(action))
            # A version 5 file carries one sequence here, a list of ints; a version 6 file
            # carries the list of them. Both have to read, because refusing yesterday's backup
            # is the one thing a backup must never do.
            sequence = key_sequence(keys[0] if keys and isinstance(keys[0], list) else keys)
            if not sequence:
                continue
            try:
                held = shortcuts.keys_of(action_id, component)
            except (KeyError, dbus.DBusException):
                continue
            after = sorted([sequence] + held[1:])
            if after == held:
                # Already so, which on the machine the file came from is every action: nothing is
                # written, and a dry run has nothing to say about it.
                continue
            if writer.dry_run():
                # Said in words and with nothing written. It used to skip this whole block in dry
                # run without a line, so importing a backup there left out every shortcut it
                # would have rebound.
                writer.report(f"would set the keys of {action_id} ({component}): "
                              f"{shortcuts.keys_text(held)} → {shortcuts.keys_text(after)}")
                continue
            try:
                shortcuts.set_primary(action_id, sequence, component)
            except (KeyError, dbus.DBusException):
                pass
        chosen = settings.get("cheatsheet_keys")
        if isinstance(chosen, dict):
            self.config.cheatsheet_keys = {str(k): keys for k, v in chosen.items()
                                           if (keys := key_sequence(v)) is not None}
            self.config.save()
        paper = settings.get("wallpaper")
        if isinstance(paper, dict):
            # Every key of this dict, and not the two that existed when it was written. Rebuilding
            # it from a list of names is how importing the settings -- including some exported seconds
            # earlier -- quietly reset a setting nobody had touched. Neither script could see it:
            # in dry run the file is never written, so there is no diff to notice.
            # A `mode` in a file written before the picker started reading the plugin is
            # ignored on purpose, and so is one written after: which kind of wallpaper the desktop
            # shows is not this app's to restore from a backup, any more than the wallpaper itself
            # is -- see the note beside this block in `export_settings`.
            layout = str(paper.get("layout", WALLPAPER_LAYOUTS[0]))
            self.config.wallpaper = {
                "video_dir": str(paper.get("video_dir", "")),
                "image_dir": str(paper.get("image_dir", "")),
                "layout": layout if layout in WALLPAPER_LAYOUTS else WALLPAPER_LAYOUTS[0],
            }
            self.config.save()
        colours = settings.get("theme")
        if isinstance(colours, dict):
            # Key by key with a fallback each, for the reason written on the wallpaper block above
            # -- and here with one more of its own: a preset this machine does not have must mean
            # "leave the colours alone", never the first row of the table.
            now = theme.current()
            if "auto" in colours:
                self.config.auto_colour = bool(colours["auto"])
                self.config.save()
            mode = str(colours.get("mode") or now["mode"] or "")
            named = str(colours.get("preset") or "")
            if mode in theme.MODES and (not named or theme.preset(named)):
                #: `from_wallpaper=None`: whatever colour an imported file carries, it is not one a
                #: wallpaper is handing over now -- and the outline the file carries has just
                #: been written from its own block above. A restore that overwrote it would be a
                #: backup that does not restore.
                self.set_theme({"mode": mode,
                                "preset": named or now["preset"],
                                "accent": str(colours.get("accent") or ""),
                                "tint": colours.get("tint") or 0}, from_wallpaper=None)
        listed = settings.get("profiles")
        if isinstance(listed, list):
            # Said rather than returned as an error: every other block of this file has already
            # been written by now, and refusing the whole import over the profiles would leave a
            # machine half restored with nothing to show for it. In dry run the list moves in
            # memory and never reaches disk, like every file of this app's.
            why = self.profiles.replace(listed)
            if why:
                self.log(f"the profiles in the settings file were not taken: {why}")
        self.state.save()
        return "ok"
