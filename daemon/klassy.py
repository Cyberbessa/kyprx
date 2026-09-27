"""Klassy's window-specific overrides, in `klassy/klassyrc`.

Three measured facts govern this module:

1. **Indices must be contiguous from 0.** Klassy's read loop is
   `for (int i = 0; config->hasGroup(exceptionGroupName(i)); ++i)` — it stops at the first hole,
   and everything past it disappears with no error at all. That is why `write()` rewrites the
   whole list.

2. **Matching is a partial regex against `resourceName + " " + resourceClass`.** A `^class$`
   pattern never matches when the resource name is not empty. The right anchor is at the end —
   see `pattern_for()`.

3. **An override inherits the global settings and layers twelve fields on top.** The window
   outline is not one of them, which is why per-window outline goes through a preset instead —
   see `OUTLINE_OFF_PRESET`.

And a consequence of 2: Klassy returns the **first** override that matches, so list order is
meaningful and `write()` preserves it.

4. **Every group in the list costs every window, on every reload.** Klassy re-reads the whole list
   once per window it decorates, so the screen stands still for windows times groups. The file
   therefore keeps neighbours that are set alike in one group, and this module reads that group
   back as the entries it was made from -- see `MERGED`. The rest of the app never sees the
   difference.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import kconfig

#: Klassy's window decoration as the compositor names it -- the `library` key of `kwinrc
#: [org.kde.kdecoration2]` and the decoration the compositor reports drawing with -- and its plugin
#: file, under the folder Qt looks for plugins in. How KyprX tells whether Klassy is there and
#: running: `daemon/requirements.py`.
DECORATION = "org.kde.klassy"
DECORATION_PLUGIN_FILE = "org.kde.kdecoration3/org.kde.klassy.so"

GROUP_RE = re.compile(r"^Windeco Exception (\d+)$")
PRESET_PREFIX = "Windeco Preset "

#: `ExceptionWindowPropertyType`
BY_CLASS = 0
BY_TITLE = 1

#: `HideTitleBar` — enum: Never, Always, Maximized, AnyMaximization, KeptBehind,
#: AnyMaximizationOrKeptBehind
TITLEBAR_NEVER = 0
TITLEBAR_ALWAYS = 1

#: `BorderSize` — enum: None, NoSides, Tiny, Normal, Large, VeryLarge, Huge, VeryHuge, Oversized
BORDER_NONE = 0
BORDER_SIZES = ["None", "No sides", "Tiny", "Normal", "Large",
                "Very large", "Huge", "Very huge", "Oversized"]

#: The preset a window points at when its outline is turned off.
#:
#: Two keys, and only two. Measured: a preset holding just the outline style makes the outline
#: disappear and changes nothing else — 12048 outline pixels gone, 12101 pixels different in
#: total, all of them the ring and its antialiasing. So this preset is not a snapshot of the
#: global settings, never goes stale when those change, and never needs regenerating.
OUTLINE_OFF_PRESET = "KyprX No Outline"
OUTLINE_OFF_KEYS = {
    "WindowOutlineStyleActive": "WindowOutlineNone",
    "WindowOutlineStyleInactive": "WindowOutlineNone",
}


# ---------------------------------------------------------------- what the decoration defaults to

#: The decoration's own schema, installed with it. It is the authority on what every setting is
#: when the file says nothing, and reading it is the difference between a checkbox that tells the
#: truth and one that does not. The parsing itself lives in `kconfig`, next to the file format.
SCHEMA = "/usr/share/config.kcfg/klassy-decoration.kcfg"

#: The decoration's groups this app reads and writes. One place reads this list: `Manager.Groups`
#: in `daemon/kyprd_api.py`, which sends each group to the interface. `explain.KLASSY_GROUPS` names
#: the same seven again, each with its label for a dry run's lines.
KLASSY_GROUPS = ("Windeco", "TitleBarOpacity", "TitleBarSpacing", "WindowOutlineStyle",
                 "ButtonSizing", "ButtonBehaviour", "ButtonColors")


def defaults() -> dict[str, dict[str, str]]:
    return kconfig.schema_defaults(SCHEMA)


def pattern_for(window_class: str) -> str:
    """A pattern matching exactly this window class, and nothing else.

    Anchored at the end because the class is the last token of `resourceName + " " + resourceClass`,
    and that `$` is what keeps `steam` from also catching `steam_app_3609080`. Open at the start
    only as far as a space or the start of the string, so that a class that merely ends in the name
    -- `notsteam` -- is not caught either.
    """
    return r"(^|\s)" + re.escape(window_class) + "$"


@dataclass
class Override:
    """One window-specific override.

    The fields are the twelve Klassy writes. `extra` keeps any key a future version adds, so a
    round trip through here does not drop it.
    """

    pattern: str
    property_type: int = BY_CLASS
    program_pattern: str = ""
    hide_titlebar: int = TITLEBAR_ALWAYS
    border_override: bool = True
    border_size: int = BORDER_NONE
    preset: str = ""
    enabled: bool = True
    opaque_titlebar: bool = False
    match_titlebar_to_app_color: bool = False
    prevent_apply_opacity_to_header: bool = False
    extra: dict[str, str] = field(default_factory=dict)

    _KEYS = {
        "ExceptionWindowPropertyPattern": "pattern",
        "ExceptionWindowPropertyType": "property_type",
        "ExceptionProgramNamePattern": "program_pattern",
        "HideTitleBar": "hide_titlebar",
        "ExceptionBorder": "border_override",
        "BorderSize": "border_size",
        "ExceptionPreset": "preset",
        "Enabled": "enabled",
        "OpaqueTitleBar": "opaque_titlebar",
        "ExceptionMatchTitleBarToApplicationColor": "match_titlebar_to_app_color",
        "PreventApplyOpacityToHeader": "prevent_apply_opacity_to_header",
    }

    @classmethod
    def from_group(cls, entries: dict[str, str]) -> "Override":
        def b(v):
            return str(v).lower() == "true"

        known = set(cls._KEYS)
        return cls(
            pattern=entries.get("ExceptionWindowPropertyPattern", ""),
            property_type=int(entries.get("ExceptionWindowPropertyType", 0) or 0),
            program_pattern=entries.get("ExceptionProgramNamePattern", ""),
            hide_titlebar=int(entries.get("HideTitleBar", 0) or 0),
            border_override=b(entries.get("ExceptionBorder", "false")),
            border_size=int(entries.get("BorderSize", 0) or 0),
            preset=entries.get("ExceptionPreset", ""),
            enabled=b(entries.get("Enabled", "true")),
            opaque_titlebar=b(entries.get("OpaqueTitleBar", "false")),
            match_titlebar_to_app_color=b(
                entries.get("ExceptionMatchTitleBarToApplicationColor", "false")),
            prevent_apply_opacity_to_header=b(
                entries.get("PreventApplyOpacityToHeader", "false")),
            extra={k: v for k, v in entries.items() if k not in known},
        )

    def to_group(self) -> dict[str, str]:
        def s(v):
            return "true" if v is True else "false" if v is False else str(v)

        out = {k: s(getattr(self, attr)) for k, attr in self._KEYS.items()}
        out.update(self.extra)
        return out

    def hides_titlebar(self) -> bool:
        return self.hide_titlebar == TITLEBAR_ALWAYS

    def borderless(self) -> bool:
        return self.border_override and self.border_size == BORDER_NONE

    def outline(self) -> bool:
        """Does this window still draw the theme's window outline?"""
        return self.preset != OUTLINE_OFF_PRESET


def read(cfg) -> list[Override]:
    """Read the list the way Klassy reads it: contiguous from 0, stopping at the first hole -- one
    entry per window pattern, whether or not the file keeps several of them in one group (see
    `MERGED`)."""
    return [Override.from_group(group) for group in read_groups(cfg)]


def orphans(cfg) -> list[int]:
    """Indices written past a hole — present in the file and invisible to Klassy.

    Reported, not repaired on sight: the repair happens the next time the list is written, where
    it is one renumbering rather than a write of its own.
    """
    return [i for pos, (i, _) in enumerate(_numbered(cfg)) if i != pos]


def _numbered(cfg) -> list[tuple[int, str]]:
    """Every `Windeco Exception N` group, by index. Includes the ones past a hole."""
    return sorted((int(m.group(1)), g) for g in cfg.groups if (m := GROUP_RE.match(g)))


def write(cfg, overrides: list[Override]) -> None:
    """Rewrite the whole list, contiguous from 0, in the order given.

    **Anything stranded past a hole is carried over, not dropped.** This used to delete every
    `Windeco Exception N` group and write back only what it was handed — and since `read()`
    deliberately stops at the first hole, exactly the way Klassy does, a single missing index
    meant every entry after it was read by nobody and then deleted by this. Renumbering them onto
    the end repairs the hole as a side effect, which is the outcome Klassy's own settings produce
    too, and it does it without losing a line.

    Leaves `Default Windeco Exception N` alone: those ship with the package.
    """
    _write_groups(cfg, [o.to_group() for o in overrides])


def read_groups(cfg) -> list[dict]:
    """The list as the raw groups it is in the file, read the way Klassy reads it.

    For the settings file, and raw on purpose: **every key**, spelled as it is written. `read`
    above answers with `Override`s, which is the right shape for this app's own writing -- eleven
    named fields and `extra` for whatever a future version adds -- and the wrong shape for a
    **backup**, because a round trip through it re-spells what it read: `Enabled` goes out through
    `bool` and comes back `true`, `HideTitleBar` through `int`. Those happen to be the same strings
    the decoration writes today, and that is a promise nobody made for tomorrow.

    One entry per window pattern: a group that holds several (`MERGED`) comes back as the entries
    it was written from, so a backup, the KyprX folder and every rule in `daemon/policy.py` see the
    same list whichever way the file keeps it.
    """
    return listed(cfg.groups)


def listed(groups: dict) -> list[dict]:
    """`read_groups` on the groups of a file rather than on the file: the list, contiguous from 0,
    one entry per window pattern. For `daemon/explain.py`, which is handed groups and no file."""
    out, i = [], 0
    while (group := groups.get(f"Windeco Exception {i}")) is not None:
        parts = split_pattern(group.get(PATTERN))
        if parts is None:
            out.append(dict(group))
        else:
            out.extend({**group, PATTERN: part} for part in parts)
        i += 1
    return out


def write_groups(cfg, groups: list[dict], together: bool = True) -> None:
    """Rewrite the whole list from raw groups, contiguous from 0, in the order given.

    The other half of `read_groups`, and everything the list demands is `write`'s and shared rather
    than copied: contiguous from zero because the decoration stops reading at the first hole, the
    order kept because the first match wins, and anything stranded past a hole carried onto the end
    rather than dropped. Neighbours set alike go into the file as one group -- see `MERGED` --
    unless `together` is False, which writes one group per entry, the way the decoration's own
    settings do (`spread`).
    """
    _write_groups(cfg, [dict(g) for g in groups], together)


def _write_groups(cfg, groups: list[dict], together: bool = True) -> None:
    existing = _numbered(cfg)
    visible = 0
    for position, (index, _) in enumerate(existing):
        if index != position:
            break
        visible = position + 1
    stranded = [dict(cfg.groups[group]) for _, group in existing[visible:]]
    if together:
        groups = merged(groups)

    for _, group in existing:
        cfg.delete_group(group)
    for i, entries in enumerate(groups):
        for key, value in entries.items():
            cfg.set(f"Windeco Exception {i}", key, value)
    for j, entries in enumerate(stranded):
        for key, value in entries.items():
            cfg.set(f"Windeco Exception {len(groups) + j}", key, value)


# ---------------------------------------------------------------- windows set alike, as one group

#: The key a group's window pattern is in.
PATTERN = "ExceptionWindowPropertyPattern"

#: What opens each window's pattern inside a group that holds several: a regex comment naming this
#: app, then a group of the pattern's own. A group whose windows are set alike is written with one
#: of these per window, joined with `|`, and read back as the entries it was made from.
#:
#: **Why the file keeps the list this way: the decoration pays for every group, on every window,
#: every time it reloads.** Klassy 6.7.3 re-reads its whole list of overrides from the file once
#: for each window it decorates -- `Decoration::reconfigureMain` calls `SettingsProvider::
#: reconfigure()`, which builds and loads a full set of settings per group -- and it does that
#: when the compositor reconfigures, when the colour-cache signal arrives and when the colour
#: scheme changes, which is all three of the reloads a wallpaper that hands its colour over sets
#: off. So the time the screen stands still grows with windows open times groups in the list --
#: and the list only ever grows, one group for each application this app has met. Measured in a
#: compositor of its own (`kwin_wayland --virtual` on a bus of its own, the decoration and
#: this desk's config copied in, 21 plain windows), in processor time spent by the compositor's
#: main thread, the file written by `write_groups` exactly as it is here:
#:
#:     groups in the list        53, as the desk had them    3, neighbours set alike merged
#:     colour scheme applied     2.6 s                       0.25 s
#:     reconfigure               1.90 s                      0.15 s
#:     colour-cache signal       1.96 s                      0.14 s
#:
#: On the desk itself, with those 53 groups and 20 decorated windows open, a reconfigure alone
#: froze the screen for 1.65 s (`scripts/stall.py`), where `reload.invalidate_colour_cache` had
#: recorded about 630 ms with fewer windows open; the daemon's stopwatch for a wallpaper change
#: had gone from 1.3 to 2 s to between 2.5 and 4.3 s.
#:
#: What a window gets does not change, and that was measured too, in the same compositor: the
#: height of every window's title bar, the same in both runs, with a window no group names as the
#: control -- its bar was there in both, so the probe was reading something. It follows from how
#: the list is read: the first group that matches wins, so neighbours with the same settings
#: behave as one group whose pattern matches whatever any of theirs did.
MERGED = "(?#KyprX)(?:"
_JOIN = ")|" + MERGED

#: What a pattern must not do to be joined to another: refer to a group by number or name
#: (joining renumbers the groups, and two patterns naming the same group do not compile together),
#: or carry the marker itself.
_REFERS = re.compile(r"\\[1-9gk]|\(\?(?:P|&|R|\(|\||'|<(?![=!])|[+-]?\d)|\(\?#KyprX\)")


def mergeable(pattern) -> bool:
    """Can this pattern be joined to a neighbour's without changing what either matches?

    Checked with Python's regex engine where the decoration uses PCRE2, which is why the test is
    narrow: a pattern Python cannot compile is left on its own, and one the two engines might
    read differently -- a reference to a group, an empty pattern (which the decoration skips, and
    which joined would match every window) -- is never joined."""
    if not isinstance(pattern, str) or not pattern or _REFERS.search(pattern):
        return False
    try:
        re.compile(pattern)
        re.compile(f"(?:{pattern})|(?:x)")
    except re.error:
        return False
    return True


def split_pattern(pattern) -> list[str] | None:
    """The window patterns a merged group was written from, or None when it is not one."""
    if not isinstance(pattern, str) or not pattern.startswith(MERGED) or not pattern.endswith(")"):
        return None
    parts = pattern[len(MERGED):-1].split(_JOIN)
    if len(parts) < 2 or not all(mergeable(p) for p in parts):
        return None
    return parts


def merged(groups: list[dict]) -> list[dict]:
    """The list as it goes into the file: each run of neighbours whose every key but the pattern
    is the same, as one group. Only neighbours, never across another group: that is what keeps
    which group wins for every window exactly what it was."""
    out: list[dict] = []
    run: list[str] = []
    for group in groups:
        pattern = group.get(PATTERN)
        alike = (out and run and mergeable(pattern)
                 and {k: v for k, v in out[-1].items() if k != PATTERN}
                 == {k: v for k, v in group.items() if k != PATTERN})
        if alike:
            run.append(pattern)
            out[-1][PATTERN] = MERGED + _JOIN.join(run) + ")"
        else:
            out.append(dict(group))
            run = [pattern] if mergeable(pattern) else []
    return out


def compact(cfg) -> bool:
    """Put the list in the file the way `write_groups` would write it, when it is not. True if
    that changed the file's groups.

    For a list this app did not write last: an old copy of the desk put back, or rows added in the
    decoration's own settings. Nothing any window gets changes, so nothing needs reloading."""
    now = [dict(cfg.groups[g]) for g in _visible(cfg)]
    if merged(read_groups(cfg)) == now:
        return False
    write_groups(cfg, read_groups(cfg))
    return True


def spread(cfg) -> bool:
    """Write the list one group per entry again, when it is not. True if that changed the file's
    groups.

    For KyprX leaving the desk: the way of writing the list is KyprX's, and a decoration's file
    left with KyprX's markers in it would be something of KyprX's left behind. Nothing any window
    gets changes."""
    entries = read_groups(cfg)
    if [dict(cfg.groups[g]) for g in _visible(cfg)] == entries:
        return False
    write_groups(cfg, entries, together=False)
    return True


def _visible(cfg) -> list[str]:
    """The groups the decoration reads: contiguous from 0, up to the first hole."""
    out = []
    while f"Windeco Exception {len(out)}" in cfg.groups:
        out.append(f"Windeco Exception {len(out)}")
    return out


def find(overrides: list[Override], window_class: str) -> int | None:
    """Index of the override whose pattern is exactly what this app would write for the class."""
    target = pattern_for(window_class)
    for i, override in enumerate(overrides):
        if override.pattern == target:
            return i
    return None


def effective(overrides: list[Override], window_class: str, resource_name: str = "") -> int | None:
    """Index of the override Klassy would apply to this window, emulating its matching.

    Reproduces three measured things: the target is `resourceName + " " + resourceClass`, the
    pattern is a **partial** regex, and the **first** match wins. Without this, an override typed
    by hand in Klassy's settings — which writes a bare literal — would look like it did not exist.
    """
    target = f"{resource_name} {window_class}"
    for i, override in enumerate(overrides):
        if not override.enabled or override.property_type != BY_CLASS:
            continue
        try:
            if re.search(override.pattern, target):
                return i
        except re.error:
            continue  # an invalid pattern in the file would not match for Klassy either
    return None


# ---------------------------------------------------------------- around a global theme

#: Where the decoration notes which global theme its settings came from. When the global theme in
#: force stops matching it, the decoration loads a bundled preset over the whole of its config the
#: next time it reads it -- measured: the compositor's log said `Preset, "Klassy" loaded...` the
#: moment KDE's Breeze theme was swapped back for Klassy's, and every key this app had put back a
#: second earlier was gone again, the per-window list renumbered, and the `[Exceptions]` group below
#: rewritten.
LOOK_AND_FEEL = ("Global", "LookAndFeelSet")

#: A group the decoration's own settings code leaves behind -- the last per-window override it
#: wrote, under the name of the schema group that describes one -- and then reads back as if it
#: were the global setting, because the schema puts that group in the same skeleton as every other.
#: So `HideTitleBar=Always` there hides the title bar of **every** window that has no override of
#: its own, including the ones this app says keep theirs: the Windows tab shows a title bar by
#: leaving the window with no override of this app's (`policy.set_titlebar`), so with the group
#: there that switch did nothing. Measured with a window of a class nobody had an override for: no
#: title bar with the group in the file, a bar 41 px high without it. It is nobody's setting -- the
#: schema has `HideTitleBar` only for a per-window override -- so this app never carries it
#: anywhere, and removes it wherever it finds it (`Daemon.clear_stray_exceptions`).
STRAY_EXCEPTIONS = "Exceptions"


def settle_look_and_feel(cfg, package: str) -> bool:
    """Note, before a global theme is applied, that the decoration's settings already belong to it.
    True if it wrote. Nothing is loaded over them then -- see `LOOK_AND_FEEL`."""
    group, key = LOOK_AND_FEEL
    if not package or cfg.get(group, key) == package:
        return False
    cfg.set(group, key, package)
    return True


# ---------------------------------------------------------------- presets

def ensure_outline_off_preset(presets_cfg) -> bool:
    """Make sure the no-outline preset exists. Returns True if it had to be written.

    Cheap enough to check every time: two keys. Klassy re-imports its bundled presets on upgrade,
    keyed off `[Global] BundledWindecoPresetsImportedVersion`, so a group under our own name
    should survive — and if it ever does not, this puts it back.
    """
    group = PRESET_PREFIX + OUTLINE_OFF_PRESET
    if all(presets_cfg.get(group, k) == v for k, v in OUTLINE_OFF_KEYS.items()):
        return False
    for key, value in OUTLINE_OFF_KEYS.items():
        presets_cfg.set(group, key, value)
    return True


def preset_names(presets_cfg) -> list[str]:
    return sorted(g[len(PRESET_PREFIX):] for g in presets_cfg.groups
                  if g.startswith(PRESET_PREFIX))


# ---------------------------------------------------------------- the window outline

OUTLINE_GROUP = "WindowOutlineStyle"

#: The two outline styles that read a colour of ours. Of the seven the decoration offers, the rest
#: read the palette -- `WindowOutlineAccentColor` takes its Highlight, `WindowOutlineContrast` its
#: WindowText -- or draw nothing at all. Writing a colour for one of those would be writing a value
#: that nothing ever reads, and then saying it had been applied.
OUTLINE_CUSTOM_STYLES = ("WindowOutlineCustomColor", "WindowOutlineCustomWithContrast")

#: The style a preset's own colour is put on, by `take_outline_colour`. `WindowOutlineCustomColor`
#: and not the other of the pair: `WindowOutlineCustomWithContrast` mixes the colour with the
#: window's text colour, so the ring would not be the colour the preset's card showed -- which is
#: the whole of what a preset putting its colour there promises. `daemon/defaults.py` declares this
#: same string for the active state, and the two have to agree; each says so.
OUTLINE_CHOSEN_STYLE = "WindowOutlineCustomColor"

#: What the decoration draws when the file says nothing, from its own schema. It matters here: this
#: desktop has no `WindowOutlineStyleInactive` in the file at all, so an inactive window is already
#: on Contrast and takes no colour of ours -- and the two states have to be asked about separately
#: for that reason.
OUTLINE_DEFAULT_STYLE = "WindowOutlineContrast"

OUTLINE_STYLE_KEYS = {True: "WindowOutlineStyleActive", False: "WindowOutlineStyleInactive"}
OUTLINE_COLOUR_KEYS = {True: "WindowOutlineCustomColorActive",
                       False: "WindowOutlineCustomColorInactive"}


def outline_takes_colour(cfg, active: bool = True) -> bool:
    """Does the outline in this state read a colour of ours, or one of the palette's?"""
    style = cfg.get(OUTLINE_GROUP, OUTLINE_STYLE_KEYS[active], OUTLINE_DEFAULT_STYLE)
    return str(style) in OUTLINE_CUSTOM_STYLES


def outline_takes_colour_anywhere(cfg) -> bool:
    """Does either state read a colour of ours?

    The question `outline_colour` answers with a colour, asked as a yes or no -- and it has to be
    this one rather than the active state alone. Asked only of the active state it disagreed with
    the colour beside it: a desktop that keeps a custom colour on the *inactive* outline alone was
    told the outline takes no colour of ours, next to the colour it takes.
    """
    return any(outline_takes_colour(cfg, active) for active in (True, False))


def outline_colour(cfg) -> str:
    """The colour the outline is actually drawn in, or "" when its style reads none.

    The active state answers first: it is the one somebody looks at, and the one the Appearance
    tab shows. Only if that state draws from the palette is the inactive one asked, so a desktop
    that keeps a custom colour on the inactive state alone still reports it rather than nothing.
    Non-empty exactly when `outline_takes_colour_anywhere` is true.
    """
    for active, key in ((True, OUTLINE_COLOUR_KEYS[True]), (False, OUTLINE_COLOUR_KEYS[False])):
        if outline_takes_colour(cfg, active):
            return str(cfg.get(OUTLINE_GROUP, key, "") or "")
    return ""


def set_outline_colour(cfg, colour: str) -> bool:
    """Put this colour on whichever of the two states actually reads one.

    True only when a value **moved**, which is not the same as "a state reads a colour" and the
    difference is expensive. The caller turns both reloads on from this answer, and those two are
    the pair that stops the screen for well over a second -- 1.34 s when it was first measured,
    1.71 s with twelve windows open. Answering yes for a state already holding this very colour
    buys all of that for nothing. A dry run cannot catch it either: the file is unchanged, so the
    diff is empty and the reload it would still ask for is invisible.
    """
    wrote = False
    for active, key in OUTLINE_COLOUR_KEYS.items():
        if outline_takes_colour(cfg, active) and str(cfg.get(OUTLINE_GROUP, key, "")) != colour:
            cfg.set(OUTLINE_GROUP, key, colour)
            wrote = True
    return wrote


def take_outline_colour(cfg, colour: str) -> bool:
    """Put this colour on the active window's outline, and its style on one that reads a colour.

    `set_outline_colour` above will not do, and the difference is the whole reason there are two.
    That one writes only where a style **already** reads a colour, which is right for a wallpaper
    handing its colour over: a desktop left on Contrast asked for nothing and gets nothing. This is
    the other case -- a preset was chosen, and choosing one is asking for its colours, the ring
    round the window included. Of the seven styles only two read a colour of ours, so on the other
    five the colour on its own would be a value nothing ever reads, written next to a claim that it
    had been applied.

    **From any of the seven, `WindowOutlineNone` included**, and that was the decision rather than
    the easy reading of it: a ring switched off is a ring that comes back wearing the new theme's
    colour. The style it lands on is `OUTLINE_CHOSEN_STYLE` even when the one it leaves also reads
    a colour, so what ends up round the window is the preset's colour and not a mixture of it.

    **The active state only.** The inactive one ships on Contrast, which is a state somebody may
    have chosen, and an unfocused window wearing the theme's colour as loudly as the focused one is
    not what the ring is for. Its colour key is left where it is too.

    True only when a value **moved**, for the reason `set_outline_colour` gives at length: the
    caller turns the colour cache's reload on from this answer, and that pair is the well over a
    second of frozen screen. A dry run cannot catch a yes that should have been a no -- the file is
    unchanged either way, and the reload it would still ask for leaves no diff at all.
    """
    wrote = False
    style_key, colour_key = OUTLINE_STYLE_KEYS[True], OUTLINE_COLOUR_KEYS[True]
    if str(cfg.get(OUTLINE_GROUP, style_key, OUTLINE_DEFAULT_STYLE)) != OUTLINE_CHOSEN_STYLE:
        cfg.set(OUTLINE_GROUP, style_key, OUTLINE_CHOSEN_STYLE)
        wrote = True
    if str(cfg.get(OUTLINE_GROUP, colour_key, "") or "") != colour:
        cfg.set(OUTLINE_GROUP, colour_key, colour)
        wrote = True
    return wrote


# ---------------------------------------------------------------- button colours

BUTTON_COLOURS_GROUP = "ButtonColors"

#: The buttons that accept a colour override. The three at the front are the ones this app has an
#: opinion about (`daemon/defaults.py`); the rest exist so a value written by the decoration's own
#: settings is read back and carried through an export rather than dropped.
BUTTONS = ["Close", "Maximize", "Minimize", "Menu", "ApplicationMenu", "ContextHelp",
           "Shade", "KeepAbove", "KeepBelow", "OnAllDesktops", "ExcludeFromCapture"]

#: `<Element><State>` is the key inside the JSON. Nine combinations exist; this app speaks for
#: three of them -- the icon and the outline at rest, the background under the pointer -- and only
#: to say there should be no override there.
ELEMENTS = ["Icon", "Background", "Outline"]
STATES = ["Normal", "Hover", "Press"]


def _colour_key(button: str, active: bool = True) -> str:
    return f"ButtonOverrideColors{'Active' if active else 'Inactive'}{button}"


def button_colours(cfg, button: str, active: bool = True) -> dict:
    """The override for one button, as `{'<Element><State>': <colour spec>}`.

    An absent or empty value means no override: the decoration decides, and that is the state to
    return to rather than a colour of our own.
    """
    import json as _json

    raw = cfg.get(BUTTON_COLOURS_GROUP, _colour_key(button, active), "") or ""
    if not raw.strip():
        return {}
    try:
        return _json.loads(raw)
    except _json.JSONDecodeError:
        return {}


def set_button_colours(cfg, button: str, slots: dict, active: bool = True) -> None:
    """Write the override for one button. An empty mapping removes the key entirely.

    Removing rather than writing `{}` matters: the decoration treats a non-empty string as "there
    is an override here", so an empty object would still count as one.
    """
    import json as _json

    key = _colour_key(button, active)
    if slots:
        cfg.set(BUTTON_COLOURS_GROUP, key,
                _json.dumps(slots, separators=(",", ":"), sort_keys=True))
        return
    cfg.delete_key(BUTTON_COLOURS_GROUP, key)
    # Clearing the last override should leave the file as it was, not as it was plus an empty
    # section. A group with nothing in it is still a diff.
    if not cfg.groups.get(BUTTON_COLOURS_GROUP):
        cfg.delete_group(BUTTON_COLOURS_GROUP)


def colour_to_rgba(spec) -> tuple[int, int, int, int] | None:
    """A colour spec from the file, as (r, g, b, opacity%), when it is an explicit colour.

    Returns None for the named forms — `["White"]`, `["NegativeFullySaturated", 60]` — which name
    a role in the decoration's own vocabulary rather than a colour. Those are shown as they are
    and left alone: guessing at the full list of role names would be inventing a vocabulary.
    """
    if not isinstance(spec, list) or not spec:
        return None
    if isinstance(spec[0], str):
        return None
    if len(spec) == 3:
        r, g, b = (int(x) for x in spec)
        return r, g, b, 100
    if len(spec) == 4:
        a, r, g, b = (int(x) for x in spec)
        return r, g, b, a
    return None


def rgba_to_colour(r: int, g: int, b: int, opacity: int = 100) -> list[int]:
    """The form the decoration writes: three numbers when opaque, alpha first when not."""
    return [r, g, b] if opacity >= 100 else [opacity, r, g, b]


def colour_label(spec) -> str:
    """How to describe a spec that this app will not edit."""
    if isinstance(spec, list) and spec and isinstance(spec[0], str):
        return spec[0] + (f" at {spec[1]}%" if len(spec) > 1 else "")
    return ""
