"""The `kwinrc` groups this app manages: blur, the geometry animation, tiling, and the plugin
switches that turn the first two on.

**Blur.** Its per-window half is the `WindowClasses` key — a string with **one class per line**
(`kconfig.py` escapes the newline as `\\n`) — read together with `BlurMatching` and
`BlurNonMatching`. Those two booleans decide which way the list points, which is why `blur_mode()`
exists: under one setting a name in the list turns blur on, under the other it turns blur off.

**Tiling.** KyprX's own engine keeps its settings in `[Script-kyprx]`, under the keys
`daemon/tiling.py` names, with lists comma-separated. The daemon is the only reader: the compositor
script asks the daemon for them resolved, and the daemon tells it to ask again after a write
(`tiling.py` says why), so a write here reloads nothing in the compositor. `floatingClass` is where
a window class goes to float rather than be tiled. It is edited a row at a time on the Windows tab,
through `set_window_lists` in `daemon/kyprd_windows.py`, and never through the batch that runs at
login: it is one list for the whole desktop rather than something a window has.
"""

from __future__ import annotations

import tiling

BLUR_GROUP = "Effect-better-blur-dx"
GEOMETRY_GROUP = "Effect-kwin4_effect_geometry_change"
TILING_GROUP = "Script-kyprx"
PLUGINS_GROUP = "Plugins"

BLUR_PLUGIN = "better_blur_dx"
GEOMETRY_PLUGIN = "kwin4_effect_geometry_change"

#: Where each one is installed, which is how `daemon/requirements.py` finds it. The blur is compiled,
#: a file in the folder Qt looks for plugins in; the geometry animation is a package of scripts, a
#: folder under a data folder, whose `metadata.json` also carries its version.
BLUR_PLUGIN_FILE = f"kwin/effects/plugins/{BLUR_PLUGIN}.so"
GEOMETRY_METADATA = f"kwin/effects/{GEOMETRY_PLUGIN}/metadata.json"

#: The one per-window list in each group that the Windows tab edits a row at a time: the windows
#: the blur is for (newline-separated), the ones the geometry animation leaves out, and the ones
#: the tiler leaves floating (both comma-separated).
BLUR_LIST = "WindowClasses"
GEOMETRY_LIST = "ExcludedWindowClasses"
TILING_FLOAT_LIST = "floatingClass"

#: Defaults from Better Blur DX's own schema, so the interface can say what is untouched.
BLUR_DEFAULTS = {
    "BlurStrength": "15", "NoiseStrength": "5", "Brightness": "100", "Saturation": "150",
    "Contrast": "100", "ForceContrastParams": "false", "CornerRadius": "0",
    "WindowClasses": "", "BlurMatching": "true", "BlurNonMatching": "false",
    "BlurDecorations": "false", "BlurMenus": "false", "BlurDocks": "false",
}

GEOMETRY_DEFAULTS = {"Duration": "250", "ExcludedWindowClasses": "krunner,yakuake"}

#: What each key of the tiling group reads as when it is missing: the engine's own defaults, which
#: `daemon/tiling.py` holds, under the name the interface and `declared.py` read every program's
#: defaults by. The same dict, not a copy.
TILING_DEFAULTS = tiling.DEFAULTS

INCLUDE_LIST = "include"   # BlurMatching=true,  BlurNonMatching=false — the list turns blur ON
EXCLUDE_LIST = "exclude"   # BlurMatching=false, BlurNonMatching=true  — the list turns blur OFF
BLUR_EVERYTHING = "all"
BLUR_NOTHING = "none"


# ---------------------------------------------------------------- plugins

#: Two rules read a switch in `[Plugins]`, and they differ on a value written by hand; every KDE
#: tool writes `true` or `false`, which both read alike. `plugin_enabled` reads the word `true`
#: alone as on (`kconfig.get_bool`), and so is stricter than either (KNOWN-ISSUES has what that
#: costs).
#:
#: KConfig's own rule (`KConfigGroup::readEntry` for a bool), which an effect's switch is read
#: through: `false`, `no`, `off` and `0` are off, in any case and with spaces either side, and any
#: other text is on, an empty value included. Measured with `kreadconfig6 --type bool` on files
#: written for it: `yes`, `on`, `1`, `2`, `maybe` and a key with nothing after its `=` read on;
#: `false`, `FALSE`, `No`, `Off` and ` 0` read off; and a key that is absent, or `[$d]`, reads as
#: the default the reader asked for. Not measured on an effect itself.
#:
#: And how the compositor decides whether to load a script, `kyprxEnabled` among them: KWin 6.7.5's
#: `Scripting::queryScriptsToLoad` loads a script whose `<id>Enabled` text gives true to
#: `QVariant(value).toBool()`, and goes by the script's metadata when the key is absent. Measured in
#: this system's own Qt 6.11, through its library: only an empty text, `0` and `false` in any case
#: give false -- `no`, `off`, `00`, `2` and `maybe` give true -- and the text is not trimmed: ` 0`
#: gives true. KConfig trims a value before the compositor sees it (measured with `kreadconfig6`:
#: ` 0 ` in the file reads back as `0`).
def plugin_enabled(cfg, plugin: str, default: bool = False) -> bool:
    return cfg.get_bool(PLUGINS_GROUP, f"{plugin}Enabled", default)


def set_plugin_enabled(cfg, plugin: str, enabled: bool) -> None:
    cfg.set(PLUGINS_GROUP, f"{plugin}Enabled", enabled)


# ---------------------------------------------------------------- blur

def blur_mode(cfg) -> str:
    matching = cfg.get_bool(BLUR_GROUP, "BlurMatching", True)
    non_matching = cfg.get_bool(BLUR_GROUP, "BlurNonMatching", False)
    if matching and non_matching:
        return BLUR_EVERYTHING
    if not matching and not non_matching:
        return BLUR_NOTHING
    return INCLUDE_LIST if matching else EXCLUDE_LIST


def blur_classes(cfg) -> list[str]:
    raw = cfg.get(BLUR_GROUP, "WindowClasses", "") or ""
    return [line.strip() for line in raw.split("\n") if line.strip()]


def set_blur_classes(cfg, classes: list[str]) -> None:
    if classes:
        cfg.set(BLUR_GROUP, "WindowClasses", "\n".join(classes))
    else:
        cfg.delete_key(BLUR_GROUP, "WindowClasses")


def has_blur(cfg, window_class: str) -> bool:
    """Does a window of this class get blurred as things stand?"""
    if not plugin_enabled(cfg, BLUR_PLUGIN):
        return False
    mode = blur_mode(cfg)
    if mode == BLUR_EVERYTHING:
        return True
    if mode == BLUR_NOTHING:
        return False
    listed = window_class in blur_classes(cfg)
    return listed if mode == INCLUDE_LIST else not listed


def blur_is_per_window(cfg) -> bool:
    return plugin_enabled(cfg, BLUR_PLUGIN) and blur_mode(cfg) in (INCLUDE_LIST, EXCLUDE_LIST)


def set_blur(cfg, window_class: str, on: bool) -> bool:
    """Add or remove the class from the list so it ends up in the requested state.

    Returns False when the current mode leaves no room to decide per window (`all` or `none`):
    the list is inert then, and touching it would be a lie. What has to change in that case is
    the pair of booleans, and that is a global choice — the Blur tab's, not a table row's.
    """
    mode = blur_mode(cfg)
    if mode in (BLUR_EVERYTHING, BLUR_NOTHING):
        return False
    classes = blur_classes(cfg)
    should_be_listed = on if mode == INCLUDE_LIST else not on
    if should_be_listed and window_class not in classes:
        classes.append(window_class)
    elif not should_be_listed and window_class in classes:
        classes.remove(window_class)
    set_blur_classes(cfg, classes)
    return True


# ---------------------------------------------------------------- geometry animation

def geometry_excluded(cfg) -> list[str]:
    raw = cfg.get(GEOMETRY_GROUP, "ExcludedWindowClasses",
                  GEOMETRY_DEFAULTS["ExcludedWindowClasses"]) or ""
    return [x.strip() for x in raw.split(",") if x.strip()]


def set_geometry_excluded(cfg, classes: list[str]) -> None:
    cfg.set(GEOMETRY_GROUP, "ExcludedWindowClasses", ",".join(classes))


# ---------------------------------------------------------------- tiling

def tiling_list(cfg, key: str) -> list[str]:
    """One of the tiling group's comma-separated lists, read the way the engine reads it
    (`tiling.entries`). A key with no value (`[$d]`) is an empty list: read as text, the marker
    it is held as stopped this at its first `split`."""
    return tiling.entries(cfg.get(TILING_GROUP, key))


def set_tiling_list(cfg, key: str, values: list[str]) -> None:
    if values:
        cfg.set(TILING_GROUP, key, ",".join(values))
    else:
        cfg.delete_key(TILING_GROUP, key)


def ensure_tiling_list_entry(cfg, key: str, value: str) -> bool:
    """Make sure a comma-separated tiling list contains this entry. True if it had to be added.

    Used for each overlay's window class -- the cheatsheet's and the wallpaper picker's -- and it
    is deliberately a belt as well as braces. An overlay already stays out of the tiling without any
    config at all, twice over: its class is in the list the engine never tiles
    (`tiling.BUILTIN_IGNORE`, through `policy.AUTO_SKIP`), and it is fixed-size, which the engine
    never tiles either. This entry is what keeps it floating on the day someone takes both of those
    away. Written only when missing, because every write to this group has the daemon tell the
    engine to read its settings again.
    """
    values = tiling_list(cfg, key)
    if value in values:
        return False
    set_tiling_list(cfg, key, values + [value])
    return True


