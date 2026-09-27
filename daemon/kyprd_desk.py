"""The desk as the KyprX folder describes it, and a folder's description put back on the desk.

`describe` turns everything KyprX controls into the folder's parts -- one file each for settings,
profiles, windows, the decoration, the compositor, shortcuts, colours and the wallpaper -- and
`apply_areas` makes the desk what a set of those parts says: the compositor's files in one
transaction, this app's own settings and profiles next, then the keys, the colours and the
wallpaper, each through its own door. `folder_problems` reads a folder that changed from outside
before any of it is applied: one problem, and nothing is. When a pass runs, what it compares and
what is merged three ways is `daemon/folder.py` and `daemon/kyprd_folder.py`.

The daemon's state it reads or writes, all of it created in `Daemon.__init__`: `config`, `profiles`,
`state`.
"""

from __future__ import annotations

import os
from dataclasses import asdict

import dbus

import effects
import folder
import klassy
import logs
import policy
import profiles
import rules
import shortcuts
import snapshot
import state
import theme
import wallpaper
import writer
from declared import COLOUR_CACHED_GROUPS
from kwin_config import DECORATION_GROUP, WINDOWS_GROUP
from kyprd_names import OVERLAY_CLASSES, OVERLAY_PATTERNS
from state import WALLPAPER_LAYOUTS, Config, Defaults, own_strength


class DeskPart:
    """The desk described as the folder's parts, and applied from them."""

    # ------------------------------------------------------------ the KyprX folder

    def managed_classes(self) -> set[str]:
        """Every window class this app speaks for: met or open, and not one it leaves alone."""
        return {c for c in (set(self.by_class()) | self.state.seen)
                if c and c not in OVERLAY_CLASSES and not policy.auto_skip(c)}

    def _new_window_row(self, new_windows=None) -> dict:
        """What a window the folder does not list stands at: what a new window gets, floating
        nowhere, animated, and with no number of its own."""
        d = new_windows if new_windows is not None else {
            "hide_title_bar": not self.config.defaults.titlebar,
            "outline": self.config.defaults.outline,
            "transparency": self.config.defaults.transparency,
            "blur": self.config.defaults.blur}
        return {**d, "float": False, "animate": True}

    def describe(self) -> dict:
        """The desk, part by part, as the KyprX folder writes it. A part that cannot be read right
        now -- the shortcut registry or the shell not up yet -- is `None`, and a part that is
        `None` is never written: an unreadable part is not an empty one."""
        tx = writer.Transaction()
        c = self.config
        out: dict = {}
        out["settings"] = {
            "notify": bool(c.notify),
            "colour_from_wallpaper": bool(c.auto_colour),
            "opacity": int(c.transparency),
            "new_windows": {"hide_title_bar": not c.defaults.titlebar,
                            "outline": bool(c.defaults.outline),
                            "transparency": bool(c.defaults.transparency),
                            "blur": bool(c.defaults.blur)},
            "cheatsheet_shows": {k: shortcuts.words(v)
                                 for k, v in sorted(c.cheatsheet_keys.items()) if v},
        }
        out["profiles"] = {"version": profiles.VERSION,
                           "profiles": [{"name": e["name"], "look": e["look"]}
                                        for e in self.profiles.entries]}
        managed = self.managed_classes()
        out["windows"] = {"windows": self._window_rows(tx, managed)}
        out["decoration"] = self._decoration_part(tx, managed)
        out["kwin"] = self._kwin_part(tx, managed)
        try:
            out["shortcuts"] = {"keys": {a["key"]: [shortcuts.words(k) for k in a["keys"]]
                                         for a in shortcuts.bindings()}}
        except dbus.DBusException:
            out["shortcuts"] = None
        now = theme.current()
        out["colours"] = {"mode": now["mode"], "preset": now["preset"],
                          "own_colour": now["accent"] or "", "tint": now["tint"]}
        out["wallpaper"] = self._wallpaper_part()
        return out

    #: The keys of a decoration override that are this app's columns -- which window it is, and
    #: whether its bar is hidden and its outline drawn -- and the values the rest ship at. Anything
    #: beyond those, on a window's own entry, travels in its row as `decoration`.
    OVERRIDE_COLUMNS = frozenset({
        "ExceptionWindowPropertyPattern", "ExceptionWindowPropertyType",
        "ExceptionProgramNamePattern", "HideTitleBar", "ExceptionBorder", "BorderSize",
        "ExceptionPreset", "Enabled"})
    OVERRIDE_SHIPPED = {"OpaqueTitleBar": "false", "ExceptionMatchTitleBarToApplicationColor": "false",
                        "PreventApplyOpacityToHeader": "false"}

    @staticmethod
    def _own_entry_class(entries: dict, managed: set) -> str:
        """The class a decoration override is this app's per-window entry for, or "" when it is
        somebody else's kind of entry -- a pattern for several windows, or for a window this app has
        never met."""
        pattern = str(entries.get("ExceptionWindowPropertyPattern", ""))
        named = policy.pattern_class(pattern)
        return named if named and named in managed and pattern == klassy.pattern_for(named) else ""

    def _window_rows(self, tx, managed: set) -> dict:
        """Every window that differs from what a new window gets, with the seven columns of the
        Windows tab -- and, where its title bar is hidden, whether its application draws its own
        bar, which is the fact that decides whether a rule is needed for it on another machine."""
        open_now = self.by_class()
        floating = set(effects.tiling_list(tx.kwin, effects.TILING_FLOAT_LIST))
        excluded = set(effects.geometry_excluded(tx.kwin))
        per_window_blur = effects.blur_is_per_window(tx.kwin)
        default = self._new_window_row()
        extras = {}
        for entries in klassy.read_groups(tx.klassy):
            named = self._own_entry_class(entries, managed)
            if named:
                more = {k: snapshot._plain({k: v})[k] for k, v in entries.items()
                        if k not in self.OVERRIDE_COLUMNS
                        and str(v) != self.OVERRIDE_SHIPPED.get(k)}
                if more:
                    extras[named] = more
        rows = {}
        for window_class in sorted(managed):
            w = open_now.get(window_class)
            switches, _ = policy.read_switches(tx, window_class, w.resource_name if w else "")
            row = {"hide_title_bar": not switches.titlebar, "outline": bool(switches.outline),
                   "transparency": bool(switches.transparency),
                   "blur": bool(switches.blur) if per_window_blur else default["blur"],
                   "float": window_class in floating, "animate": window_class not in excluded}
            own = self.config.own_transparency.get(window_class)
            if row == default and own is None and window_class not in extras:
                continue
            if own is not None:
                row["opacity"] = int(own)
            if row["hide_title_bar"]:
                row["draws_own_title_bar"] = (w.needs_rule() if w else rules.find_managed(
                    tx.rules, window_class) is not None)
            if window_class in extras:
                row["decoration"] = extras[window_class]
            rows[window_class] = row
        return rows

    def _decoration_part(self, tx, managed: set) -> dict:
        """The decoration's settings: every group of its file but its bookkeeping and the override
        list, the overrides that are not a window's own entry (those are rows), and the presets any
        override points at -- never the ones it bundles, which are this machine's."""
        groups = tx.klassy.groups
        listed = [g for g in klassy.read_groups(tx.klassy)
                  if g.get("ExceptionWindowPropertyPattern") not in OVERLAY_PATTERNS]
        named = {str(g.get("ExceptionPreset") or "") for g in listed} - {"",
                                                                          klassy.OUTLINE_OFF_PRESET}
        return {
            "settings": {g: snapshot._plain(e) for g, e in groups.items()
                         if g not in self.KLASSY_NOT_CARRIED and "Windeco Exception" not in g},
            "overrides": [snapshot._plain(g) for g in listed
                          if not self._own_entry_class(g, managed)],
            "presets": {klassy.PRESET_PREFIX + n: snapshot._plain(
                tx.presets.groups[klassy.PRESET_PREFIX + n]) for n in sorted(named)
                if klassy.PRESET_PREFIX + n in tx.presets.groups},
        }

    #: The compositor's groups the folder carries, by the name its file gives them, and the one
    #: per-window list inside each that the rows stand for.
    KWIN_PARTS = (("decoration", DECORATION_GROUP, None), ("window_behaviour", WINDOWS_GROUP, None),
                  ("blur", effects.BLUR_GROUP, effects.BLUR_LIST),
                  ("animation", effects.GEOMETRY_GROUP, effects.GEOMETRY_LIST),
                  ("tiling", effects.TILING_GROUP, effects.TILING_FLOAT_LIST))
    KWIN_PLUGINS = (("tiling", effects.TILING_PLUGIN), ("blur", effects.BLUR_PLUGIN),
                    ("animation", effects.GEOMETRY_PLUGIN))

    @staticmethod
    def _split_list(raw, key: str) -> tuple[list[str], str]:
        sep = "\n" if key == effects.BLUR_LIST else ","
        return [x.strip() for x in str(raw or "").split(sep) if x.strip()], sep

    def _kwin_part(self, tx, managed: set) -> dict:
        """The compositor's five groups this app has controls in, whole, with the windows this app
        speaks for taken out of the three per-window lists -- their rows say it -- and which of the
        three plugins are on."""
        out = {}
        for name, group, list_key in self.KWIN_PARTS:
            entries = snapshot._plain(tx.kwin.groups.get(group, {}))
            if list_key and entries.get(list_key) is not None:
                values, sep = self._split_list(entries[list_key], list_key)
                entries[list_key] = sep.join(v for v in values if v not in managed)
            out[name] = entries
        out["plugins"] = {name: effects.plugin_enabled(tx.kwin, plugin)
                          for name, plugin in self.KWIN_PLUGINS}
        return out

    def _wallpaper_part(self) -> dict | None:
        """The wallpaper of every activity, by the activity's name and by the path of each
        screen's file, when a video pauses, and the picker's two choices. `None` when the shell
        cannot be asked.

        Every activity and not the one in use: an activity switch would otherwise rewrite this
        file, and on a second machine sharing the folder it would put one activity's wallpaper on
        another. By name, because an activity's id is this machine's."""
        try:
            found = wallpaper.snapshot_all()
        except wallpaper.WallpaperError:
            return None
        import explain
        activities: dict = {}
        for activity in found:
            screens = []
            for desktop in activity.get("desktops") or []:
                plugin = str(desktop.get("plugin") or "")
                kind = {wallpaper.IMAGE_PLUGIN: "image",
                        wallpaper.VIDEO_PLUGIN: "video"}.get(plugin, plugin)
                target = str(desktop.get("image") if kind == "image" else desktop.get("last")
                             if kind == "video" else "") or ""
                screen = {"kind": kind,
                          "file": explain.home(wallpaper.to_path(target)) if target else ""}
                if kind == "video" and str(desktop.get("pause") or "") in wallpaper.PAUSE_MODES:
                    screen["pause"] = str(desktop.get("pause"))
                screens.append(screen)
            name = str(activity.get("name") or activity.get("activity") or "")
            key, n = name, 2
            while key in activities:
                key, n = f"{name} #{n}", n + 1
            activities[key] = {"on_screen": screens}
        video_dir = str(self.config.wallpaper.get("video_dir") or "")
        image_dir = str(self.config.wallpaper.get("image_dir") or "")
        return {"activities": activities,
                "picker": {"layout": self.config.wallpaper.get("layout", "pages"),
                           "video_folder": explain.home(video_dir) if video_dir else "",
                           "image_folder": explain.home(image_dir) if image_dir else ""}}

    # -- what is wrong with a folder, before anything is applied

    def folder_problems(self, areas: dict) -> list[str]:
        """Everything in these parts that could not be applied, one sentence each. Checked before
        anything is written, and one problem means nothing is: half a setup is exactly what the
        folder must never leave on a desk. A preset or a wallpaper file this machine does not have
        is not a problem here -- that part is skipped and said, the rest goes in."""
        out = []

        def need(ok, where, what):
            if not ok:
                out.append(f"{where}: {what}")

        s = areas.get("settings")
        if s is not None:
            where = folder.FILES["settings"]
            for key in ("notify", "colour_from_wallpaper"):
                need(key not in s or isinstance(s[key], bool), where, f"{key} has to be true or false")
            need("opacity" not in s or (isinstance(s["opacity"], int) and 1 <= s["opacity"] <= 100),
                 where, "opacity has to be a whole number from 1 to 100")
            nw = s.get("new_windows", {})
            need(isinstance(nw, dict) and all(isinstance(v, bool) for v in nw.values()), where,
                 "new_windows has to hold true or false for each switch")
            for action, keys in (s.get("cheatsheet_shows") or {}).items():
                try:
                    shortcuts.from_words(keys)
                except ValueError as e:
                    out.append(f"{where}: the key shown for {action}: {e}")
        p = areas.get("profiles")
        if p is not None:
            listed = p.get("profiles")
            need(isinstance(listed, list), folder.FILES["profiles"], "profiles has to be a list")
            for entry in listed if isinstance(listed, list) else []:
                try:
                    profiles.normalise((entry or {}).get("look"))
                except (ValueError, AttributeError) as e:
                    out.append(f"{folder.FILES['profiles']}: profile "
                               f"{(entry or {}).get('name')!r}: {e}")
        w = areas.get("windows")
        if w is not None:
            rows = w.get("windows")
            need(isinstance(rows, dict), folder.FILES["windows"], "windows has to be an object")
            for cls, row in (rows if isinstance(rows, dict) else {}).items():
                if not isinstance(row, dict):
                    out.append(f"{folder.FILES['windows']}: {cls} is not an object")
                    continue
                for key in ("hide_title_bar", "outline", "transparency", "blur", "float",
                            "animate", "draws_own_title_bar"):
                    need(key not in row or isinstance(row[key], bool), folder.FILES["windows"],
                         f"{cls}: {key} has to be true or false")
                need("opacity" not in row or own_strength(row["opacity"]) is not None,
                     folder.FILES["windows"], f"{cls}: opacity has to be a whole number from 1 to 99")
        d = areas.get("decoration")
        if d is not None:
            need(isinstance(d.get("settings", {}), dict) and isinstance(d.get("overrides", []), list)
                 and isinstance(d.get("presets", {}), dict), folder.FILES["decoration"],
                 "settings and presets have to be objects, overrides a list")
        k = areas.get("kwin")
        if k is not None:
            need(all(isinstance(k.get(n, {}), dict) for n, _, _ in self.KWIN_PARTS)
                 and isinstance(k.get("plugins", {}), dict), folder.FILES["kwin"],
                 "every group has to be an object")
        sc = areas.get("shortcuts")
        if sc is not None:
            for action, keys in (sc.get("keys") or {}).items():
                for sequence in keys if isinstance(keys, list) else [keys]:
                    try:
                        shortcuts.from_words(sequence)
                    except ValueError as e:
                        out.append(f"{folder.FILES['shortcuts']}: {action}: {e}")
        col = areas.get("colours")
        if col is not None:
            need(col.get("mode") in theme.MODES, folder.FILES["colours"],
                 f"mode has to be one of {', '.join(theme.MODES)}")
            need(not col.get("own_colour") or theme.is_colour(str(col["own_colour"])),
                 folder.FILES["colours"], "own_colour is not a colour")
        return out

    # -- applying

    def apply_areas(self, target: dict, preview: bool = False) -> tuple[str, list[str]]:
        """Apply parts of the folder to the desk, each exactly as it says. Returns ("ok" or
        "error: …", what did not go in) -- or, with `preview`, the plain words and nothing else.

        The compositor's files first, in one transaction: the decoration, the compositor's groups
        and every window, so the screen stops once. This app's own settings and profiles next.
        Then the keys, the colours and the wallpaper, each through its own door. Every window this
        app speaks for is brought to its row, or to what a new window gets when the folder does
        not list it -- that is what "the folder is the setup" means for a window.
        """
        c = self.config
        s = target.get("settings")
        rows_part = target.get("windows")
        windows_touched = any(k in target for k in ("settings", "windows", "decoration", "kwin"))
        rows = (rows_part or {}).get("windows") if rows_part is not None else None
        if rows is None:
            rows = self.describe_windows_only()
        new_windows = (s or {}).get("new_windows") if s is not None else None
        #: The row an unlisted window is brought to. The folder's own new-window switches only when
        #: its window rows come with them: the rows were written against those switches, so the two
        #: are one fact. A new-window switch arriving on its own is what *new* windows get, and moves
        #: no window that is already here -- the same as changing it on the Settings tab.
        default_row = self._new_window_row(
            {**self._new_window_row(), **new_windows} if new_windows and rows_part is not None
            else None)
        strength = int((s or {}).get("opacity", c.transparency)) if s is not None else int(
            c.transparency)
        previous = int(c.transparency)
        restrike = self.transparency_targets() if strength != previous else []
        reading = writer.Transaction()
        managed = self.managed_classes() | set(rows)
        open_now = self.by_class()
        draws_own = {cls: (bool(rows[cls].get("draws_own_title_bar"))
                           if cls in rows and "draws_own_title_bar" in rows[cls]
                           else open_now[cls].needs_rule() if cls in open_now
                           else rules.find_managed(reading.rules, cls) is not None)
                     for cls in managed}
        own = {cls: int(r["opacity"]) for cls, r in rows.items() if "opacity" in r}

        def build(tx):
            before = {n: {g: dict(e) for g, e in getattr(tx, n).groups.items()}
                      for n in ("klassy", "presets", "kwin", "rules")}
            if "decoration" in target:
                self._apply_decoration(tx, target["decoration"], managed)
            if "kwin" in target:
                self._apply_kwin(tx, target["kwin"], managed)
            if windows_touched:
                self._apply_windows(tx, rows, default_row, managed, open_now, draws_own, own,
                                    strength)
                if restrike:
                    self.strike_transparency(tx, restrike, strength, previous)
            moved = {n: {g for g in set(before[n]) | set(getattr(tx, n).groups)
                         if before[n].get(g) != getattr(tx, n).groups.get(g)}
                     for n in before}
            if moved["klassy"] or moved["presets"] or moved["rules"]:
                tx.reload_kwin = True
            if moved["klassy"] & COLOUR_CACHED_GROUPS:
                tx.reload_colours = True
            if moved["kwin"]:
                tx.reload_kwin = True
            if effects.BLUR_GROUP in moved["kwin"] or effects.PLUGINS_GROUP in moved["kwin"]:
                tx.reload_blur = True
            if effects.TILING_GROUP in moved["kwin"] or effects.PLUGINS_GROUP in moved["kwin"]:
                tx.reload_tiling = True

        wanted_config = Config.from_dict(asdict(c))
        if s is not None:
            wanted_config.notify = bool(s.get("notify", c.notify))
            wanted_config.auto_colour = bool(s.get("colour_from_wallpaper", c.auto_colour))
            wanted_config.transparency = strength
            if new_windows:
                wanted_config.defaults = Defaults(
                    titlebar=not default_row["hide_title_bar"], outline=default_row["outline"],
                    transparency=default_row["transparency"], blur=default_row["blur"])
            wanted_config.cheatsheet_keys = {str(k): shortcuts.from_words(v) for k, v in
                                             (s.get("cheatsheet_shows") or {}).items()}
        if rows_part is not None:
            wanted_config.own_transparency = {k: v for k, v in own.items() if self.own_allowed(k)}
        paper = target.get("wallpaper")
        if paper is not None and isinstance(paper.get("picker"), dict):
            picker = paper["picker"]
            layout = str(picker.get("layout") or "pages")
            folder_path = str(picker.get("video_folder") or "")
            image_folder_path = str(picker.get("image_folder") or "")
            wanted_config.wallpaper = {
                "layout": layout if layout in WALLPAPER_LAYOUTS else "pages",
                "video_dir": os.path.expanduser(folder_path) if folder_path else "",
                "image_dir": os.path.expanduser(image_folder_path) if image_folder_path else ""}

        if preview:
            import explain
            tx = writer.Transaction()
            if windows_touched or "decoration" in target or "kwin" in target:
                build(tx)
            lines = [explain.preview(tx), explain.own_preview(state.CONFIG_PATH, asdict(c),
                                                                asdict(wanted_config))]
            if target.get("profiles") is not None:
                lines.append(explain.own_preview(
                    profiles.PATH, {"profiles": [{"name": e["name"], "look": e["look"]}
                                                 for e in self.profiles.entries]},
                    {"profiles": target["profiles"].get("profiles") or []}))
            if target.get("shortcuts") is not None:
                lines.extend(self._restore_shortcuts(self._keys_of(target["shortcuts"]),
                                                     preview=True))
            if target.get("colours") is not None:
                lines.append(self.set_theme(self._colours_of(target["colours"]),
                                            from_wallpaper=None, preview=True))
            if paper is not None:
                lines.extend(self._restore_wallpaper(self._paper_of(paper), preview=True))
            return "\n".join(x for x in lines if x and not x.startswith("error")), []

        trouble: list[str] = []
        if windows_touched or "decoration" in target or "kwin" in target:
            try:
                diff = writer.run(build)
            except Exception as e:  # noqa: BLE001 — nothing was written; the caller says so
                self.log(f"could not apply the KyprX folder: {logs.what(e)}", trouble=True)
                return f"error: {e}", []
            if writer.dry_run() and diff:
                self.log("would have written:\n" + diff)
            for cls in rows:
                self.state.mark_seen(cls)
            self.state.save()
        if wanted_config != c:
            self.config = wanted_config
            self.config.save()
        if target.get("profiles") is not None:
            refused = self.profiles.replace(target["profiles"].get("profiles") or [])
            if refused:
                trouble.append(f"the profiles did not go in: {refused}")
        if target.get("shortcuts") is not None:
            trouble.extend(self._restore_shortcuts(self._keys_of(target["shortcuts"])))
        if target.get("colours") is not None:
            colours = self._colours_of(target["colours"])
            if colours["preset"] and theme.preset(colours["preset"]) is None:
                trouble.append(f"the colours were left as they are: this machine has no preset "
                               f"called {colours['preset']}")
            else:
                answer = self.set_theme(colours, from_wallpaper=None)
                if answer.startswith("error"):
                    trouble.append(f"the colours did not go in: {answer[len('error: '):]}")
        if paper is not None:
            trouble.extend(self._restore_wallpaper(self._paper_of(paper)))
        self._look_again_soon()
        return "ok", trouble

    def describe_windows_only(self) -> dict:
        tx = writer.Transaction()
        return self._window_rows(tx, self.managed_classes())

    @staticmethod
    def _keys_of(part: dict) -> dict:
        return {k: [shortcuts.from_words(seq) for seq in (v if isinstance(v, list) else [v])]
                for k, v in (part.get("keys") or {}).items()}

    @staticmethod
    def _colours_of(part: dict) -> dict:
        return {"mode": str(part.get("mode") or ""), "preset": str(part.get("preset") or ""),
                "accent": str(part.get("own_colour") or ""), "tint": part.get("tint") or 0}

    @staticmethod
    def _paper_of(part: dict) -> dict | None:
        """The folder's wallpaper part in the shape `_restore_wallpaper` reads -- the shell's own,
        activity by activity, by name. A screen drawn by a plugin this app does not set -- a
        slideshow, a plain colour -- leaves its activity to the desktop."""
        wanted = part.get("activities")
        if not isinstance(wanted, dict):
            return None
        activities = []
        for name, entry in sorted(wanted.items()):
            screens = (entry or {}).get("on_screen") if isinstance(entry, dict) else None
            if not isinstance(screens, list) or not screens:
                continue
            desktops = []
            for screen in screens:
                kind = str((screen or {}).get("kind") or "")
                if kind not in wallpaper.PLUGINS:
                    desktops = []
                    break
                path = os.path.expanduser(str((screen or {}).get("file") or ""))
                url = "file://" + path if path else ""
                desktops.append({"plugin": wallpaper.PLUGINS[kind],
                                 "image": url if kind == "image" else "",
                                 "last": url if kind == "video" else "",
                                 "pause": str((screen or {}).get("pause") or "")})
            if desktops:
                activities.append({"name": str(name).split(" #")[0], "desktops": desktops})
        return {"activities": activities} if activities else None

    #: The decoration's groups the folder neither carries nor touches: its record of which global
    #: theme its settings came from, which is this machine's, and the leftover `[Exceptions]` group
    #: its own settings code writes, which hides every title bar it can reach (`klassy.
    #: STRAY_EXCEPTIONS`) -- carried, it would do that on every machine the folder went to.
    KLASSY_NOT_CARRIED = frozenset({"Global", klassy.STRAY_EXCEPTIONS})

    def _apply_decoration(self, tx, part: dict, managed: set) -> None:
        cfg = tx.klassy
        wanted = part.get("settings") or {}
        for group in [g for g in cfg.groups if g not in self.KLASSY_NOT_CARRIED
                      and "Windeco Exception" not in g and g not in wanted]:
            cfg.delete_group(group)
        for group, entries in wanted.items():
            if group not in self.KLASSY_NOT_CARRIED and "Windeco Exception" not in group:
                snapshot._set_group(cfg, group, entries)
        for group, entries in (part.get("presets") or {}).items():
            if str(group).startswith(klassy.PRESET_PREFIX):
                snapshot._set_group(tx.presets, group, entries)
        current = [snapshot._plain(g) for g in klassy.read_groups(cfg)]
        theirs = [g for g in current if not self._own_entry_class(g, managed)
                  and g.get("ExceptionWindowPropertyPattern") not in OVERLAY_PATTERNS]
        wanted_list = [snapshot._plain(g) for g in part.get("overrides") or []
                       if isinstance(g, dict)
                       and g.get("ExceptionWindowPropertyPattern") not in OVERLAY_PATTERNS]
        if theirs != wanted_list:
            own = [g for g in current if self._own_entry_class(g, managed)]
            klassy.write_groups(cfg, [snapshot._raw(g) for g in wanted_list + own])

    def _apply_kwin(self, tx, part: dict, managed: set) -> None:
        cfg = tx.kwin
        for name, group, list_key in self.KWIN_PARTS:
            if name not in part:
                continue
            wanted = dict(part[name] or {})
            kept_raw = cfg.groups.get(group, {}).get(list_key) if list_key else None
            if list_key:
                current, sep = self._split_list(kept_raw, list_key)
                theirs, _ = self._split_list(wanted.get(list_key), list_key)
                edited = [v for v in current if v in managed or v in theirs]
                edited += [v for v in theirs if v not in edited and v not in managed]
                if edited == current:
                    if kept_raw is None:
                        wanted.pop(list_key, None)
                    else:
                        wanted[list_key] = kept_raw
                elif edited:
                    wanted[list_key] = sep.join(edited)
                else:
                    wanted.pop(list_key, None)
            if wanted:
                snapshot._set_group(cfg, group, wanted)
            elif group in cfg.groups:
                cfg.delete_group(group)
        for name, plugin in self.KWIN_PLUGINS:
            on = (part.get("plugins") or {}).get(name)
            if isinstance(on, bool) and effects.plugin_enabled(cfg, plugin) != on:
                effects.set_plugin_enabled(cfg, plugin, on)

    def _apply_windows(self, tx, rows: dict, default_row: dict, managed: set, open_now: dict,
                       draws_own: dict, own: dict, strength: int) -> None:
        """Bring every window this app speaks for to its row, or to the new-window row."""
        floating = effects.tiling_list(tx.kwin, effects.TILING_FLOAT_LIST)
        excluded = effects.geometry_excluded(tx.kwin)
        float_after, excluded_after = list(floating), list(excluded)
        for cls in sorted(managed):
            row = {**default_row, **rows.get(cls, {})}
            window = open_now.get(cls) or policy.Window(window_class=cls,
                                                        decorated=not draws_own.get(cls, False))
            switches = policy.Switches(titlebar=not row["hide_title_bar"], outline=row["outline"],
                                       transparency=row["transparency"], blur=row["blur"])
            policy.apply(tx, window, switches, own.get(cls, strength))
            if row["transparency"] and cls in own and self.own_allowed(cls):
                policy.set_transparency(tx, window, True, own[cls], claim=True)
            if row["hide_title_bar"]:
                # The window's own entry carries exactly the row's other decoration settings: the
                # ones it lists, and the ones this app writes at the values the decoration ships.
                more = row.get("decoration") if isinstance(row.get("decoration"), dict) else {}
                overrides = klassy.read_groups(tx.klassy)
                for i, entries in enumerate(overrides):
                    if entries.get("ExceptionWindowPropertyPattern") == klassy.pattern_for(cls):
                        merged = {k: v for k, v in entries.items()
                                  if k in self.OVERRIDE_COLUMNS
                                  or self.OVERRIDE_SHIPPED.get(k) == str(v)}
                        merged.update({k: str(v) for k, v in more.items()})
                        if merged != dict(entries):
                            overrides[i] = merged
                            klassy.write_groups(tx.klassy, overrides)
                        break
            if row["float"] and cls not in float_after:
                float_after.append(cls)
            elif not row["float"] and cls in float_after:
                float_after.remove(cls)
            if not row["animate"] and cls not in excluded_after:
                excluded_after.append(cls)
            elif row["animate"] and cls in excluded_after:
                excluded_after.remove(cls)
        if float_after != floating:
            effects.set_tiling_list(tx.kwin, effects.TILING_FLOAT_LIST, float_after)
        if excluded_after != excluded:
            effects.set_geometry_excluded(tx.kwin, excluded_after)
