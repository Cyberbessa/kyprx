"""What a change would do, in plain words -- the half of a dry run written to be read by a person.

The unified diff a dry run has always printed is exact, and it is for machines: `scripts/drive.py`
reads it line by line, and so does anybody who wants the bytes. It is also close to unreadable to
anyone who does not know KConfig. A section header falls three lines outside the hunk, so a key
shows up with no group. A window rule is named by a random UUID. A decoration override added at
the head renumbers every override after it, so adding one window reads as the whole list changing.
And the diff never says what the desktop would do *after* the write -- stop the screen, lay out
every tiled window again -- because none of that is in a file.

So a dry run says the same thing first in these words: which file, which setting, what it was and
what it would be, and then what the desktop would do next. `writer.Transaction.commit` prints it
through `writer.report`, before the caller prints the diff.

**The words are held to five rules, and each one protects a check in `scripts/drive.py`** that
reads the same log:

* Every line after the first is indented. The driver counts diff lines that start with `+`, and a
  sentence that happened to start with one would be counted as a written key.
* No key or group is ever printed by its raw name -- a key nobody gave a label is spelled out in
  lower-case words instead -- and neither are the outline styles' raw values. The driver proves a
  change left the outline alone by the absence of `WindowOutline` in the log, and the same for
  `opacityactive` and `WindowCornerRadius`.
* None of the markers the scripts look for appears here: `would have written`, `would have saved`,
  `would have bound`, `the wallpaper of activity`.
* The same change always reads the same way: sorted, with no timings and no UUIDs, and the folder
  previews counted only on the line the driver already knows to set aside. `RestoreDefaults` run
  twice has to print the same text twice.
* Nothing says "could not", "failed on" or "did not go through": `scripts/simulate.sh` reads those
  as the daemon reporting trouble.
"""

from __future__ import annotations

import json
import os
import re

import effects
import kconfig
import klassy

INDENT = "  "

HEADER = "NOTHING WAS CHANGED. Had this been for real:"

#: Where each line starts. Two levels are all this needs: the file, and what changes in it.
FILE, CHANGE = INDENT, INDENT * 2


def home(path: str) -> str:
    """A path with the home directory written as `~`: shorter, the same on every machine, and
    naming nobody's home. The documentation writes every path under the home directory the same
    way."""
    root = os.path.expanduser("~")
    if path == root or path.startswith(root + os.sep):
        return "~" + path[len(root):]
    return path


def _words(name: str) -> str:
    """A key nobody gave a label, spelled out rather than printed raw: `ShowOutlineOnHover` reads
    `show outline on hover`. Raw names are what the driver searches the log for."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", name)
    return spaced.replace("_", " ").lower().strip()


# ---------------------------------------------------------------- the vocabulary

#: The files a transaction can write, by base name.
FILES = {
    "klassyrc": "Title bar and window decoration (Klassy)",
    "windecopresetsrc": "Klassy's presets",
    "kwinrulesrc": "Window rules",
    "kwinrc": "The window manager's settings",
}

#: `kwinrc`'s groups this app writes.
KWIN_GROUPS = {
    effects.TILING_GROUP: "Tiling (Krohnkite)",
    effects.BLUR_GROUP: "Blur",
    effects.GEOMETRY_GROUP: "Window animation",
    effects.PLUGINS_GROUP: "Effects and scripts",
    "Windows": "Window focus",
    "org.kde.kdecoration2": "Window borders",
}

#: The decoration's groups this app writes.
KLASSY_GROUPS = {
    "Windeco": "Title bar and frame",
    "WindowOutlineStyle": "The window outline",
    "TitleBarOpacity": "Title bar opacity",
    "TitleBarSpacing": "Title bar spacing",
    "ButtonBehaviour": "Title bar buttons",
    "ButtonColors": "Title bar button colours",
    "ButtonSizing": "Title bar button sizes",
}

#: What each key is called here. Several files share a key name with different meanings only in
#: theory; in practice every name below means one thing wherever this app writes it.
KEYS = {
    # tiling
    "screenGapTop": "gap at the top of the screen",
    "screenGapBottom": "gap at the bottom of the screen",
    "screenGapLeft": "gap at the left of the screen",
    "screenGapRight": "gap at the right of the screen",
    "screenGapBetween": "gap between windows",
    "floatingClass": "windows that always float",
    "floatingTitle": "window titles that always float",
    "ignoreClass": "windows the tiler ignores",
    "ignoreTitle": "window titles the tiler ignores",
    "ignoreScreen": "screens the tiler ignores",
    "tilingClass": "windows that are always tiled",
    "adjustLayout": "resizing a window adjusts the layout",
    "adjustLayoutLive": "the layout follows the resize as it happens",
    "keepTilingOnDrag": "a dragged window stays tiled",
    "floatUtility": "utility windows float",
    "preventMinimize": "tiled windows cannot be minimised",
    "preventProtrusion": "windows are kept inside their tile",
    "monocleMaximize": "the monocle layout maximises",
    "newWindowPosition": "where a new window goes",
    "limitTileWidth": "tile width is limited",
    "limitTileWidthRatio": "tile width limit",
    "noTileBorder": "tiles have no border",
    # blur
    "BlurStrength": "strength",
    "NoiseStrength": "noise",
    "CornerRadius": "corner radius of the blur",
    "Brightness": "brightness",
    "Saturation": "saturation",
    "Contrast": "contrast",
    "ForceContrastParams": "contrast settings forced",
    "WindowClasses": "the list of windows",
    "BlurMatching": "windows in the list are blurred",
    "BlurNonMatching": "windows not in the list are blurred",
    "BlurDecorations": "blur behind title bars",
    "BlurMenus": "blur behind menus",
    "BlurDocks": "blur behind panels",
    # window animation
    "Duration": "length in milliseconds",
    "ExcludedWindowClasses": "windows that are not animated",
    # focus
    "FocusPolicy": "focus",
    "NextFocusPrefersMouse": "focus goes to the window under the pointer",
    "DelayFocusInterval": "focus delay in milliseconds",
    "FocusStealingPreventionLevel": "focus stealing prevention",
    "SeparateScreenFocus": "each screen keeps its own focus",
    # borders
    "BorderSize": "border size",
    "BorderSizeAuto": "the decoration picks the border size",
    # title bar and frame
    "WindowCornerRadius": "corner radius",
    "ButtonIconStyle": "button icons",
    "ButtonShape": "button shape",
    "MatchTitleBarToApplicationColor": "title bar in the application's colour",
    "DrawTitleBarSeparator": "line under the title bar",
    "BoldTitle": "bold title",
    "UnderlineTitle": "underlined title",
    "DrawBackgroundGradient": "gradient on the title bar",
    "ColorizeWindowOutlineWithButton": "the outline takes the colour of the button under the "
                                       "pointer",
    "RoundAllCornersWhenNoBorders": "every corner rounded when there is no border",
    "DrawBorderOnMaximizedWindows": "border on maximised windows",
    "UseTitleBarColorForAllBorders": "the title bar's colour on every border",
    # the outline
    "WindowOutlineThickness": "thickness",
    "WindowOutlineStyleActive": "style, focused window",
    "WindowOutlineStyleInactive": "style, other windows",
    "WindowOutlineCustomColorActive": "colour, focused window",
    "WindowOutlineCustomColorInactive": "colour, other windows",
    "WindowOutlineCustomColorOpacityActive": "opacity of that colour, focused window",
    "WindowOutlineAccentColorOpacityActive": "opacity of the accent colour, focused window",
    # title bar opacity
    "TitleBarOpacityActive": "focused window",
    "TitleBarOpacityInactive": "other windows",
    "OverrideTitleBarOpacityActive": "overrides the colour scheme, focused window",
    "OverrideTitleBarOpacityInactive": "overrides the colour scheme, other windows",
    "OpaqueMaximizedTitleBars": "opaque when maximised",
    "BlurTransparentTitleBars": "blur behind a see-through title bar",
    "ApplyOpacityToHeader": "the opacity reaches the application's own header",
    # title bar spacing
    "TitleBarTopMargin": "above the title",
    "TitleBarBottomMargin": "below the title",
    "TitleBarLeftMargin": "at the left end",
    "TitleBarRightMargin": "at the right end",
    "TitleSidePadding": "beside the title",
    # buttons
    "ButtonBackgroundOpacityActive": "background opacity, focused window",
    "ButtonBackgroundOpacityInactive": "background opacity, other windows",
}

#: The plugins `[Plugins]` switches, by the name before `Enabled`.
PLUGINS = {
    effects.TILING_PLUGIN: "the tiling script",
    effects.BLUR_PLUGIN: "the blur effect",
    effects.GEOMETRY_PLUGIN: "the window animation",
    "kyprx": "KyprX's watcher inside the compositor",
    "blur": "KDE's own blur",
}

#: The keys that hold a list, and what separates the items.
LISTS = {
    (effects.TILING_GROUP, "floatingClass"): ",", (effects.TILING_GROUP, "floatingTitle"): ",",
    (effects.TILING_GROUP, "ignoreClass"): ",", (effects.TILING_GROUP, "ignoreTitle"): ",",
    (effects.TILING_GROUP, "ignoreScreen"): ",", (effects.TILING_GROUP, "tilingClass"): ",",
    (effects.BLUR_GROUP, "WindowClasses"): "\n",
    (effects.GEOMETRY_GROUP, "ExcludedWindowClasses"): ",",
}

#: The outline's seven styles, as the decoration's own dialog names them. Their raw spelling
#: carries `WindowOutline`, which the driver reads as the outline having been written.
OUTLINE_STYLES = {
    "WindowOutlineNone": "no outline",
    "WindowOutlineContrast": "contrast",
    "WindowOutlineShadowColor": "the shadow colour",
    "WindowOutlineAccentColor": "the accent colour",
    "WindowOutlineAccentWithContrast": "the accent colour, with contrast",
    "WindowOutlineCustomColor": "a colour of your own",
    "WindowOutlineCustomWithContrast": "a colour of your own, with contrast",
}

LAYOUT_NAMES = dict(effects.LAYOUTS)


def value_text(value) -> str:
    """One value, as a person would say it."""
    if value is None:
        return "not set"
    if value is kconfig.NO_VALUE:
        return "the default"
    text = str(value)
    if text in OUTLINE_STYLES:
        return OUTLINE_STYLES[text]
    if text.lower() == "true":
        return "on"
    if text.lower() == "false":
        return "off"
    if text == "":
        return "empty"
    return text if len(text) <= 60 else text[:57] + "..."


def _change(label: str, before, after) -> str:
    return f"{label}: {value_text(before)} → {value_text(after)}"


def _list_change(label: str, before, after, sep: str) -> str:
    def items(v):
        return [x.strip() for x in str(v or "").split(sep) if x.strip()] if v not in (
            None, kconfig.NO_VALUE) else []
    old, new = items(before), items(after)
    added = [x for x in new if x not in old]
    gone = [x for x in old if x not in new]
    parts = []
    if added:
        parts.append("adds " + ", ".join(added))
    if gone:
        parts.append("takes out " + ", ".join(gone))
    return f"{label}: " + ("; ".join(parts) if parts else "the same items, in another order")


def _key_line(group: str, key: str, before, after) -> str:
    if (group, key) in LISTS:
        return _list_change(KEYS.get(key, _words(key)), before, after, LISTS[(group, key)])
    if group == effects.PLUGINS_GROUP and key.endswith("Enabled"):
        plugin = key[:-len("Enabled")]
        return _change(f"switched on: {PLUGINS.get(plugin, _words(plugin))}", before, after)
    if key.endswith("LayoutOrder"):
        name = LAYOUT_NAMES.get(key, _words(key[:-len("LayoutOrder")]))

        def place(v):
            if v in (None, kconfig.NO_VALUE):
                return "the tiler's own place"
            return "out of the cycle" if str(v).strip() == "0" else f"place {v}"
        return f"{name} in the layout cycle: {place(before)} → {place(after)}"
    if key.startswith("ButtonOverrideColors"):
        rest = key[len("ButtonOverrideColors"):]
        state = "focused window" if rest.startswith("Active") else "other windows"
        button = rest[len("Active"):] if rest.startswith("Active") else rest[len("Inactive"):]
        said = {True: "a colour of its own", False: "the colour scheme's"}
        return (f"{_words(button)} button colours, {state}: "
                f"{said[bool(before) and before is not kconfig.NO_VALUE]} → "
                f"{said[bool(after) and after is not kconfig.NO_VALUE]}")
    label = KEYS.get(key)
    if label is None:
        label = _words(key)
        if key.endswith("Active") and not label.endswith("focused window"):
            label = _words(key[:-len("Active")]) + ", focused window"
        elif key.endswith("Inactive"):
            label = _words(key[:-len("Inactive")]) + ", other windows"
    return _change(label, before, after)


def _group_lines(group: str, old: dict, new: dict) -> list[str]:
    lines = []
    for key in sorted(set(old) | set(new)):
        before, after = old.get(key), new.get(key)
        if before == after:
            continue
        lines.append(_key_line(group, key, before, after))
    return lines


# ---------------------------------------------------------------- per file

def _generic(old: dict, new: dict, names: dict) -> list[str]:
    out = []
    for group in sorted(set(old) | set(new)):
        lines = _group_lines(group, old.get(group, {}), new.get(group, {}))
        if not lines:
            continue
        title = names.get(group) or _words(group.replace(kconfig.SEP, " "))
        out.append(f"{title}:")
        out.extend(INDENT + line for line in lines)
    return out


def _exception_name(pattern: str) -> str:
    import policy
    named = policy.pattern_class(pattern or "")
    return named or f"the windows matching {pattern!r}"


def _exception_facts(entries: dict) -> str:
    facts = []
    hide = str(entries.get("HideTitleBar", "0"))
    facts.append("title bar hidden" if hide == "1" else "title bar shown" if hide == "0"
                 else f"title bar rule {hide}")
    if str(entries.get("ExceptionBorder", "false")).lower() == "true":
        facts.append("no border" if str(entries.get("BorderSize", "0")) == "0"
                     else f"border size {entries.get('BorderSize')}")
    preset = str(entries.get("ExceptionPreset", "") or "")
    facts.append("outline off" if preset == "KyprX No Outline"
                 else f"preset {preset!r}" if preset else "outline on")
    if str(entries.get("Enabled", "true")).lower() == "false":
        facts.append("switched off")
    return ", ".join(facts)


def _klassy(old: dict, new: dict) -> list[str]:
    """The decoration's file: its settings by group, and its per-window overrides by window.

    Overrides are matched by the pattern they carry, never by their number, because the number is
    only a position: adding one window at the head renumbers every override after it. And one per
    window, as `klassy.listed` reads them: a group holding several windows set alike is said
    window by window."""
    def overrides(groups):
        return [(entries.get(klassy.PATTERN, ""), entries) for entries in klassy.listed(groups)]

    def written(groups):
        return {g: e for g, e in groups.items() if re.match(r"^Windeco Exception \d+$", g)}

    def settings(groups):
        return {g: e for g, e in groups.items() if not re.match(r"^Windeco Exception \d+$", g)}

    out = _generic(settings(old), settings(new), KLASSY_GROUPS)
    before, after = overrides(old), overrides(new)
    was = {pattern: entries for pattern, entries in before}
    now = {pattern: entries for pattern, entries in after}
    lines = []
    for pattern in sorted(set(was) | set(now)):
        name = _exception_name(pattern)
        if pattern not in was:
            lines.append(f"{name}: a new override -- {_exception_facts(now[pattern])}")
        elif pattern not in now:
            lines.append(f"{name}: its override is taken away (it was: "
                         f"{_exception_facts(was[pattern])})")
        elif _exception_facts(was[pattern]) != _exception_facts(now[pattern]):
            lines.append(f"{name}: {_exception_facts(was[pattern])} → "
                         f"{_exception_facts(now[pattern])}")
        elif was[pattern] != now[pattern]:
            lines.append(f"{name}: a detail of its override changes")
    # Renumbered means an override present on both sides sits at another number afterwards --
    # which is what one added at the head, or one taken out in the middle, does to all the rest.
    position_before = {pattern: i for i, (pattern, _) in enumerate(before)}
    position_after = {pattern: i for i, (pattern, _) in enumerate(after)}
    moved = any(position_before[p] != position_after[p]
                for p in position_before if p in position_after)
    if lines or moved:
        out.append("Overrides for single windows:")
        out.extend(INDENT + line for line in lines)
        if moved:
            out.append(INDENT + "(the list is renumbered to keep it in order -- that alone "
                                "changes nothing on screen)")
    elif written(old) != written(new):
        out.append("Overrides for single windows:")
        out.append(INDENT + "(the same list, written as a different number of entries -- that "
                            "alone changes nothing on screen)")
    return out


def _presets(old: dict, new: dict) -> list[str]:
    out = []
    for group in sorted(set(old) | set(new)):
        if not group.startswith("Windeco Preset "):
            continue
        name = group[len("Windeco Preset "):]
        if group not in old:
            out.append(f"preset {name!r} is added")
        elif group not in new:
            out.append(f"preset {name!r} is taken away")
        elif old[group] != new[group]:
            out.append(f"preset {name!r} changes")
    return out


RULE_POLICIES = {"1": "leave alone", "2": "force", "6": "force for now"}


def _rule_facts(entries: dict) -> dict[str, str]:
    """What a window rule does, in the terms this app writes rules in: one sentence per thing it
    decides, keyed by that thing, so that a rule that changes can be said fact by fact."""
    facts = {}
    if str(entries.get("noborderrule", "")) in ("2", "6"):
        facts["title bar"] = ("forces a title bar"
                              if str(entries.get("noborder", "false")).lower() == "false"
                              else "forces no title bar")
    for key, label in (("opacityactive", "focused"), ("opacityinactive", "not focused")):
        if key in entries and str(entries.get(key + "rule", "")) in ("2", "6"):
            facts[f"opaque when {label}"] = f"{entries[key]} % opaque when {label}"
    if str(entries.get("placementrule", "")) in ("2", "6"):
        facts["placement"] = ("opens in the middle of the screen"
                              if str(entries.get("placement")) == "5"
                              else f"placement {entries.get('placement')}")
    return facts


def _rule_change(was: dict, now: dict) -> str:
    """Only what moves in a rule that stays. The whole rule on both sides of an arrow buries the
    one fact that changed among the ones that did not."""
    before, after = _rule_facts(was), _rule_facts(now)
    said = []
    for topic in dict.fromkeys([*before, *after]):
        b, a = before.get(topic), after.get(topic)
        if b == a:
            continue
        if a is None:
            said.append(f"no longer {b}")
        elif b is None:
            said.append(f"now {a}")
        elif topic.startswith("opaque"):
            said.append(f"{topic}: {b.split(' %')[0]} % → {a.split(' %')[0]} %")
        else:
            said.append(f"{b} → {a}")
    return "; ".join(said)


def _rules(old: dict, new: dict) -> list[str]:
    """The window rules, each by the name it carries -- never by its UUID, which a dry run makes
    up afresh every time and which says nothing to anybody."""
    uuid = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

    def order(groups):
        return [u for u in str((groups.get("General") or {}).get("rules", "") or "").split(",")
                if u]

    def name(entries):
        return str(entries.get("Description") or entries.get("wmclass") or "a rule with no name")

    lines = []
    first_after = order(new)[:1]
    for u in sorted({g for g in set(old) | set(new) if uuid.match(g)},
                    key=lambda g: name(new.get(g) or old.get(g) or {})):
        was, now = old.get(u), new.get(u)
        if was is None:
            facts = "; ".join(_rule_facts(now).values()) or "it does nothing yet"
            place = ", first in the list" if [u] == first_after else ""
            lines.append(f"new rule {name(now)!r}{place}: {facts}")
        elif now is None:
            lines.append(f"rule {name(was)!r} is taken away")
        elif was != now:
            moved = _rule_change(was, now)
            if moved:
                lines.append(f"rule {name(now)!r}: {moved}")
            elif name(was) != name(now):
                lines.append(f"rule {name(was)!r} is renamed {name(now)!r}")
            else:
                lines.append(f"rule {name(now)!r}: a detail changes")
    kept = [u for u in order(old) if u in order(new)]
    if kept != [u for u in order(new) if u in order(old)]:
        lines.append("the order of the rules changes")
    return lines


def _scheme(path: str, old: dict, new: dict) -> list[str]:
    """A colour scheme this app writes: the chosen preset's, with a colour of your own in it."""
    general_new = new.get("General", {})
    preset = general_new.get("KyprXPreset") or "a preset"
    try:
        soaked = f", soaked in at {round(float(general_new.get('TintFactor')) * 100)} %"
    except (TypeError, ValueError):
        soaked = ""
    if not old:
        return [f"a colour scheme of KyprX's own is written: {preset}'s colours with your "
                f"colour{soaked}"]
    changed = sum(1 for g in set(old) | set(new)
                  for k in set(old.get(g, {})) | set(new.get(g, {}))
                  if old.get(g, {}).get(k) != new.get(g, {}).get(k))
    return [f"rewritten from {preset}'s colours with your colour{soaked} "
            f"({changed} value(s) move)"]


def file_lines(path: str, old: dict, new: dict) -> list[str]:
    """What changes in one file, as indented lines under its name. Old and new are group maps."""
    base = os.path.basename(path)
    if base == "klassyrc":
        lines = _klassy(old, new)
    elif base == "windecopresetsrc":
        lines = _presets(old, new)
    elif base == "kwinrulesrc":
        lines = _rules(old, new)
    elif base.endswith(".colors"):
        lines = _scheme(path, old, new)
    elif base == "kwinrc":
        lines = _generic(old, new, KWIN_GROUPS)
    else:
        lines = _generic(old, new, {})
    title = FILES.get(base) or (f"Colour scheme {base[:-len('.colors')]}"
                                if base.endswith(".colors") else base)
    head = FILE + f"{title} ({home(path)})"
    if not lines:
        return [head, CHANGE + "rewritten in the layout the desktop's own tools use, "
                               "with no setting changed"]
    return [head] + [CHANGE + line for line in lines]


# ---------------------------------------------------------------- a whole transaction

def _step(description: str, plain: str) -> str:
    """One change asked of another process. Its own plain words, or else the step's name read out
    of the description, which is shaped like a diff: `--- what`, `+++ tool`, `-was`, `+now`."""
    if plain:
        return plain
    lines = description.splitlines()
    if len(lines) >= 4 and lines[0].startswith("--- ") and lines[1].startswith("+++ "):
        # The wallpaper's heading is a marker the driver looks for, and must stay the diff's.
        what = lines[0][4:].strip().replace("the wallpaper of activity", "the wallpaper, activity")
        return (f"{what}: {lines[2][1:].strip()} → {lines[3][1:].strip()} "
                f"(by {lines[1][4:].strip()})")
    return lines[0].lstrip("-+ ").strip() if lines else ""


RELOADS = (
    ("reload_tiling", "restart the tiling script -- every tiled window is laid out again"),
    ("reload_kwin", "re-read its window rules and the decoration -- the screen stops for about "
                    "0.6 s"),
    ("reload_colours", "rebuild the colours the decoration keeps -- about 0.65 s more with the "
                       "screen stopped"),
    ("reload_blur", "reload the blur effect"),
)


def transaction(tx) -> str:
    """Everything one transaction would do, as a person would say it."""
    lines = [HEADER]
    for path, cfg in tx.dirty_files():
        before = kconfig.KConfig(path)
        lines.extend(file_lines(path, before.groups, cfg.groups))
    steps = [s for s in (_step(d, p) for d, p in tx.session_steps()) if s]
    if steps:
        lines.append(FILE + "The desktop would be asked to:")
        lines.extend(CHANGE + s for s in steps)
    # The tiler's reload carries the compositor's with it (`writer.Transaction.commit`), so both
    # sentences are said when either flag asks for the second.
    flags = {name: bool(getattr(tx, name, False)) for name, _ in RELOADS}
    flags["reload_kwin"] = flags["reload_kwin"] or flags["reload_tiling"]
    after = [said for name, said in RELOADS if flags[name]]
    if after:
        lines.append(FILE + "Then the desktop would:")
        lines.extend(CHANGE + s for s in after)
    return "\n".join(lines)


def preview(tx) -> str:
    """What a transaction would do, in a dry run's words but without its heading: for a question
    asked before anything is written, where nothing has been held back yet. Empty when the
    transaction would do nothing."""
    if not tx.plan():
        return ""
    return "\n".join(transaction(tx).splitlines()[1:])


# ---------------------------------------------------------------- this app's own files

OWN_FILES = {
    "config.json": "KyprX's own settings",
    "profiles.json": "KyprX's profiles",
    "state.json": "what KyprX remembers about your windows",
}

CONFIG_KEYS = {
    "notify": "say when something did not work",
    "auto_colour": "colour from the wallpaper",
    "transparency": "opacity of see-through windows",
}

DEFAULT_SWITCHES = {
    "titlebar": "a new window keeps its title bar",
    "outline": "a new window gets the outline",
    "transparency": "a new window is see-through",
    "blur": "a new window is blurred",
}


def _yes(value) -> str:
    return "yes" if value else "no"


def _config_changes(before: dict, after: dict) -> list[str]:
    out = []
    if before.get("paused") != after.get("paused"):
        out.append(f"new windows are adjusted: {_yes(not before.get('paused'))} → "
                   f"{_yes(not after.get('paused'))}")
    for key, label in CONFIG_KEYS.items():
        if before.get(key) != after.get(key):
            if key == "transparency":
                out.append(f"{label}: {before.get(key, 'not set')} % → {after.get(key)} %")
            else:
                out.append(_change(label, before.get(key), after.get(key)))
    own_b, own_a = before.get("own_transparency") or {}, after.get("own_transparency") or {}
    for cls in sorted(set(own_b) | set(own_a)):
        if own_b.get(cls) != own_a.get(cls):
            was = f"{own_b[cls]} %" if cls in own_b else "none of its own"
            now = f"{own_a[cls]} %" if cls in own_a else "none of its own"
            out.append(f"opacity of {cls}: {was} → {now}")
    def_b, def_a = before.get("defaults") or {}, after.get("defaults") or {}
    for key in sorted(set(def_b) | set(def_a)):
        if def_b.get(key) != def_a.get(key):
            label = DEFAULT_SWITCHES.get(key, f"a new window: {_words(key)}")
            out.append(f"{label}: {_yes(def_b.get(key))} → {_yes(def_a.get(key))}")
    keys_b, keys_a = before.get("cheatsheet_keys") or {}, after.get("cheatsheet_keys") or {}
    if keys_b != keys_a:
        import shortcuts
        for action in sorted(set(keys_b) | set(keys_a)):
            if keys_b.get(action) != keys_a.get(action):
                out.append(f"the key the cheatsheet shows for {action}: "
                           f"{shortcuts.key_text(keys_b.get(action) or [])} → "
                           f"{shortcuts.key_text(keys_a.get(action) or [])}")
    paper_b, paper_a = before.get("wallpaper") or {}, after.get("wallpaper") or {}
    for key, label in (("video_dir", "video folder"), ("image_dir", "pictures folder"), ("layout", "wallpaper picker layout")):
        if paper_b.get(key) != paper_a.get(key):
            out.append(_change(label, paper_b.get(key) or "none", paper_a.get(key) or "none"))
    return out


def _state_changes(before: dict, after: dict) -> list[str]:
    out = []
    for key, label in (("seen", "windows KyprX has met"),
                       ("refuses_ssd", "applications that refuse a title bar")):
        was, now = set(before.get(key) or []), set(after.get(key) or [])
        if was != now:
            parts = []
            if now - was:
                parts.append("adds " + ", ".join(sorted(now - was)))
            if was - now:
                parts.append("takes out " + ", ".join(sorted(was - now)))
            out.append(f"{label}: " + "; ".join(parts))
    if bool(before.get("off")) != bool(after.get("off")):
        out.append(f"KyprX is off this desk: {_yes(before.get('off'))} → {_yes(after.get('off'))}")
    if before.get("version") != after.get("version"):
        out.append(_change("version", before.get("version"), after.get("version")))
    if before.get("app_version") != after.get("app_version"):
        out.append(_change("the version of KyprX that ran here last", before.get("app_version"),
                           after.get("app_version")))
    return out


def _profile_changes(before: dict, after: dict) -> list[str]:
    """By name only. A look carries the outline's and the corner's own keys, and the driver reads
    those names in the log as the decoration having been written."""
    def by_name(d):
        return {str(e.get("name")): e.get("look") for e in (d.get("profiles") or [])
                if isinstance(e, dict)}
    was, now = by_name(before), by_name(after)
    out = []
    for name in sorted(set(was) | set(now)):
        if name not in was:
            out.append(f"profile {name!r} is kept")
        elif name not in now:
            out.append(f"profile {name!r} is deleted")
        elif json.dumps(was[name], sort_keys=True) != json.dumps(now[name], sort_keys=True):
            out.append(f"profile {name!r} is updated")
    if list(was) != list(now) and set(was) == set(now):
        out.append("the profiles change order")
    return out


def own_file(path: str, before: dict, after: dict) -> str:
    """What saving one of this app's own files would change, or "" when nothing would.

    Compared with the file on disk, every time -- never with what an earlier dry-run save said.
    `scripts/drive.py` runs `RestoreDefaults` twice from the same settings and requires the two to
    print the same thing; a comparison with the previous save would print it once."""
    base = os.path.basename(path)
    if base == "config.json":
        lines = _config_changes(before, after)
    elif base == "state.json":
        lines = _state_changes(before, after)
    elif base == "profiles.json":
        lines = _profile_changes(before, after)
    else:
        lines = [f"{_words(k)} changes" for k in sorted(set(before) | set(after))
                 if before.get(k) != after.get(k)]
    if not lines:
        return ""
    title = OWN_FILES.get(base, base)
    return "\n".join([f"would have saved {title} ({home(path)}):"]
                     + [CHANGE + line for line in lines])


def own_preview(path: str, before: dict, after: dict) -> str:
    """`own_file`, as a question asked before anything is saved rather than a dry run's report:
    the same lines under a heading that names the file and nothing else."""
    lines = own_file(path, before, after).splitlines()
    if not lines:
        return ""
    base = os.path.basename(path)
    return "\n".join([FILE + f"{OWN_FILES.get(base, base)} ({home(path)})"] + lines[1:])
