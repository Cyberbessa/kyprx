"""The `kwinrc` groups this app manages: blur, the geometry animation, tiling, and the plugin
switches that turn each of them on.

**Blur.** Its per-window half is the `WindowClasses` key — a string with **one class per line**
(`kconfig.py` escapes the newline as `\\n`) — read together with `BlurMatching` and
`BlurNonMatching`. Those two booleans decide which way the list points, which is why `blur_mode()`
exists: under one setting a name in the list turns blur on, under the other it turns blur off.

**Tiling.** Krohnkite keeps list values comma-separated. `floatingClass` is where a window class
goes to be left alone by the tiler. It is edited a row at a time on the Windows tab, through
`set_window_lists` in `daemon/kyprd_windows.py` and never through the batch that runs at login:
writing it makes the script re-read itself, and a script that has just started tiles the screen
from scratch.
"""

from __future__ import annotations

BLUR_GROUP = "Effect-better-blur-dx"
GEOMETRY_GROUP = "Effect-kwin4_effect_geometry_change"
TILING_GROUP = "Script-krohnkite"
PLUGINS_GROUP = "Plugins"

BLUR_PLUGIN = "better_blur_dx"
GEOMETRY_PLUGIN = "kwin4_effect_geometry_change"
TILING_PLUGIN = "krohnkite"

#: Where each one is installed, which is how `daemon/requirements.py` finds it. The blur is compiled,
#: a file in the folder Qt looks for plugins in; the other two are packages of scripts, each a
#: folder under a data folder, whose `metadata.json` also carries its version.
BLUR_PLUGIN_FILE = f"kwin/effects/plugins/{BLUR_PLUGIN}.so"
GEOMETRY_METADATA = f"kwin/effects/{GEOMETRY_PLUGIN}/metadata.json"
TILING_METADATA = f"kwin/scripts/{TILING_PLUGIN}/metadata.json"

#: The one per-window list in each plugin's group that the Windows tab edits a row at a time: the
#: windows the blur is for (newline-separated), the ones the geometry animation leaves out, and
#: the ones the tiler leaves where they are put (both comma-separated).
BLUR_LIST = "WindowClasses"
GEOMETRY_LIST = "ExcludedWindowClasses"
TILING_FLOAT_LIST = "floatingClass"

#: Defaults from Better Blur DX's own schema, so the interface can say what is untouched and the
#: exported settings file need not carry a key nobody changed.
BLUR_DEFAULTS = {
    "BlurStrength": "15", "NoiseStrength": "5", "Brightness": "100", "Saturation": "150",
    "Contrast": "100", "ForceContrastParams": "false", "CornerRadius": "0",
    "WindowClasses": "", "BlurMatching": "true", "BlurNonMatching": "false",
    "BlurDecorations": "false", "BlurMenus": "false", "BlurDocks": "false",
}

GEOMETRY_DEFAULTS = {"Duration": "250", "ExcludedWindowClasses": "krunner,yakuake"}

#: Krohnkite's own defaults for the keys the interface exposes.
TILING_DEFAULTS = {
    "screenGapTop": "0", "screenGapBottom": "0", "screenGapLeft": "0", "screenGapRight": "0",
    "screenGapBetween": "0", "tileLayoutOrder": "1", "monocleLayoutOrder": "2",
    "threeColumnLayoutOrder": "3", "spiralLayoutOrder": "4", "quarterLayoutOrder": "5",
    "stackedLayoutOrder": "6", "columnsLayoutOrder": "7", "spreadLayoutOrder": "8",
    "floatingLayoutOrder": "9", "stairLayoutOrder": "10", "binaryTreeLayoutOrder": "11",
    "cascadeLayoutOrder": "12", "adjustLayout": "true", "adjustLayoutLive": "true",
    "keepTilingOnDrag": "true", "floatUtility": "true", "preventMinimize": "false",
    "preventProtrusion": "true", "monocleMaximize": "true", "newWindowPosition": "0",
    "limitTileWidth": "false", "limitTileWidthRatio": "1.6", "noTileBorder": "false",
    "floatingClass": "", "floatingTitle": "", "ignoreClass": "", "ignoreTitle": "",
    "ignoreScreen": "", "tilingClass": "",
}

#: The layouts Krohnkite can rotate through, in the order the Tiling tab shows their boxes: the
#: three KyprX puts in the cycle first, in that order, and the rest after them in the order the
#: tiler names them. Order value 0 takes a layout out of the rotation.
#:
#: This is where a box sits and nothing more. Which of two layouts sharing a number comes first is
#: the tiler's own list order -- the numbers in `TILING_DEFAULTS` above, which count along it --
#: and the tab breaks ties by those, not by this.
LAYOUTS = [
    ("spiralLayoutOrder", "Spiral"), ("quarterLayoutOrder", "Quarter"),
    ("binaryTreeLayoutOrder", "Binary tree"),
    ("tileLayoutOrder", "Tile"), ("monocleLayoutOrder", "Monocle"),
    ("threeColumnLayoutOrder", "Three column"), ("stackedLayoutOrder", "Stacked"),
    ("columnsLayoutOrder", "Columns"), ("spreadLayoutOrder", "Spread"),
    ("floatingLayoutOrder", "Floating"), ("stairLayoutOrder", "Stair"),
    ("cascadeLayoutOrder", "Cascade"),
]

#: The highest order number the tiler accepts. Anything above it, or anything that is not a whole
#: number, the tiler throws away and uses its own default for that layout instead (Krohnkite's
#: `validateNumber(…, 0, 12)`).
LAYOUT_ORDER_MAX = 12

INCLUDE_LIST = "include"   # BlurMatching=true,  BlurNonMatching=false — the list turns blur ON
EXCLUDE_LIST = "exclude"   # BlurMatching=false, BlurNonMatching=true  — the list turns blur OFF
BLUR_EVERYTHING = "all"
BLUR_NOTHING = "none"


# ---------------------------------------------------------------- plugins

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
    raw = cfg.get(TILING_GROUP, key, "") or ""
    return [x.strip() for x in raw.split(",") if x.strip()]


def set_tiling_list(cfg, key: str, values: list[str]) -> None:
    if values:
        cfg.set(TILING_GROUP, key, ",".join(values))
    else:
        cfg.delete_key(TILING_GROUP, key)


def layout_order(cfg) -> dict[str, int]:
    """Every layout's order number as the tiler will read it, key by key.

    The file's value where it has a usable one, and the tiler's own default everywhere else: a key
    that is absent, empty (`[$d]`, which reads back as something other than a string), not a whole
    number, or outside 0..12. That is the tiler's rule rather than a tidier one of this app's, and
    it has to be, because the answer is compared against orders the tiler would actually walk.
    """
    out = {}
    for key, _ in LAYOUTS:
        shipped = int(TILING_DEFAULTS[key])
        raw = cfg.get(TILING_GROUP, key)
        try:
            value = int(raw.strip()) if isinstance(raw, str) else shipped
        except ValueError:
            value = shipped
        out[key] = value if 0 <= value <= LAYOUT_ORDER_MAX else shipped
    return out


def ensure_tiling_list_entry(cfg, key: str, value: str) -> bool:
    """Make sure a comma-separated tiling list contains this entry. True if it had to be added.

    Used for each overlay's window class -- the cheatsheet's and the wallpaper picker's -- and it
    is deliberately a belt as well as braces. An overlay already floats without any config at all:
    it is fixed-size, and the tiler floats anything it cannot resize. This entry is what keeps it
    floating on the day someone takes the fixed size away — or swaps the tiler for one that reads
    the same list. Written only when missing, because writing this group at all makes the tiler
    re-read itself and rearrange every window on screen.
    """
    values = tiling_list(cfg, key)
    if value in values:
        return False
    set_tiling_list(cfg, key, values + [value])
    return True


