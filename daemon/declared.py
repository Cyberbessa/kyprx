"""Writing the settings KyprX declares, and only where they do not already read that way.

`daemon/defaults.py` says what KyprX wants; this writes a slice of it into a transaction, skipping
every key that already reads as wanted -- the file's value, or what the program that owns the key
ships when the file says nothing -- and says which groups moved, so that `note_reloads` can ask for
the reloads those need and no others. Everything here takes the transaction it works on and keeps
nothing of its own.
"""

from __future__ import annotations

import effects
import kconfig
import klassy
from kwin_config import DECORATION_GROUP, DECORATION_SCHEMA, WINDOWS_DEFAULTS, WINDOWS_GROUP


#: Which file and group each source of the declared settings lives in. The interface's vocabulary
#: on one side, the config files on the other, in the one place both are named together.
_SOURCES = {
    "klassy": None,                      # group comes from the declaration itself
    "decoration": DECORATION_GROUP,
    "windows": WINDOWS_GROUP,
    "blur": effects.BLUR_GROUP,
    "geometry": effects.GEOMETRY_GROUP,
    "tiling": effects.TILING_GROUP,
}


def shipped_defaults() -> dict:
    """What every setting reads as when the file says nothing, from whoever ships it.

    One shape for all of them -- source, group, key, with an empty group for the sources that are
    a single flat section. `Groups()` flattens it back out for the wire, because the interface
    reads `klassy_defaults` nested and the rest flat, and changing that is a change to both ends
    for no gain.

    Reading these is what makes an untouched control tell the truth, and it is also what stops a
    default being *written*: a key that is absent and already reads the way this app wants needs
    no line in anybody's config file.
    """
    return {
        "klassy": klassy.defaults(),
        "decoration": {"": kconfig.schema_defaults(DECORATION_SCHEMA).get(DECORATION_GROUP, {})},
        "windows": {"": WINDOWS_DEFAULTS},
        "blur": {"": effects.BLUR_DEFAULTS},
        "geometry": {"": effects.GEOMETRY_DEFAULTS},
        "tiling": {"": effects.TILING_DEFAULTS},
    }


def effective_value(tx, shipped: dict, source: str, group: str, key: str) -> str | None:
    """What this key reads as today: the file's value or, when the key is not in the file, what
    the program that owns it ships. None when neither says -- a key nobody wrote and nothing
    declares a default for.

    The one definition of "already reads that way". It decides whether a declared default is
    written (`write_declared`), and it is what a profile captures off the desktop
    (`Daemon.worn_look`) -- so a look taken and compared by the same reading is one whose "on the
    desktop now" and "loading it would write nothing" are the same fact. A `[$d]` marker in the
    file -- the key with nothing after it -- means the default too.
    """
    cfg = tx.klassy if source == "klassy" else tx.kwin
    real_group = group if source == "klassy" else _SOURCES[source]
    current = cfg.get(real_group, key)
    if current is None or current is kconfig.NO_VALUE:
        current = (shipped.get(source) or {}).get(group, {}).get(key)
    return None if current is None else str(current)


def write_declared(tx, tree: dict) -> set[tuple[str, str]]:
    """Write a slice of `defaults.SETTINGS`, and say which (source, group) actually moved.

    The group and not only the source, because what has to be reloaded afterwards depends on it:
    one Klassy group carries colours the decoration keeps in a cache of its own, and the rest do
    not. See `note_reloads`.

    **A key is skipped when it already reads the way the declaration wants**, where "already
    reads" means the file's value or, if the key is not in the file, what the theme itself ships.
    Skipping is not an optimisation. Writing a value a key already has would fill three shared
    config files with lines nobody chose -- and it would take away the `. default` marker that
    tells you nothing has been written for a setting yet.
    """
    shipped = shipped_defaults()
    moved: set[tuple[str, str]] = set()
    for source, groups in tree.items():
        for group, entries in groups.items():
            for key, wanted in entries.items():
                if source == "plugins":
                    if effects.plugin_enabled(tx.kwin, key) != bool(wanted):
                        effects.set_plugin_enabled(tx.kwin, key, bool(wanted))
                        moved.add((source, group))
                    continue
                if effective_value(tx, shipped, source, group, key) == str(wanted):
                    continue
                cfg = tx.klassy if source == "klassy" else tx.kwin
                cfg.set(group if source == "klassy" else _SOURCES[source], key, wanted)
                moved.add((source, group))
    return moved


def write_declared_colours(tx, tree: dict) -> bool:
    """Take away the button-colour overrides this app has declared it does not want.

    A separate function from `write_declared` because these do not live as a key in a group: all
    nine slots of one button share a single JSON value, and taking one out means reading that
    value, dropping the slot and writing the rest back.

    Both states, active and inactive. The inactive twin is as invisible as the active one now that
    the controls are gone, and leaving half an override behind would be the worst of the two.

    A named role from the decoration's own vocabulary is removed like any other. That is a real
    consequence and not an oversight: a declared default means this app has an opinion about the
    slot, and "shown, never rewritten" was the right rule while the slot was on screen to be shown.
    """
    changed = False
    for button, slots in tree.items():
        if button not in klassy.BUTTONS:
            continue
        for active in (True, False):
            current = dict(klassy.button_colours(tx.klassy, button, active=active))
            wanted = {k: v for k, v in current.items()
                      if not (k in slots and slots[k] is None)}
            if wanted == current:
                continue
            klassy.set_button_colours(tx.klassy, button, wanted, active=active)
            changed = True
    if changed:
        tx.reload_kwin = True
        # Button colours live in a cache the ordinary reconfigure does not touch.
        tx.reload_colours = True
    return changed


#: Which reload each source needs. The tiler is the disruptive one -- reloading it rearranges
#: every window on screen -- which is why it is a source of its own rather than part of the
#: general reconfigure.
#: The Klassy groups whose values the decoration keeps in a colour cache that the ordinary
#: reconfigure does not touch. Writing one of these and asking only for the reconfigure leaves the
#: decoration drawing the colour it had -- the control saying one thing and the window another,
#: which is the one thing a control here may never do. Found by the owner, on a border that stayed
#: the wallpaper's pink after being set to orange.
#:
#: **Three groups, and the rest measured out rather than assumed.** The corner radius is in
#: `Windeco` and carries no colour: written with the cheap reload alone it took effect on the
#: screen (the four corners of a full-screen window moved by 4.91 of 255), and asking for the
#: colour cache as well changed nothing further -- 0.00 against the frame before it. So the
#: expensive half is asked for where colours are and nowhere else, which is about 650 ms of frozen
#: screen that an Apply about a margin or a radius no longer pays.
#:
#: The whole of `WindowOutlineStyle` stays in, thickness included, and that was measured rather
#: than assumed too: `WindowOutlineThickness` written from 2.25 to 6 with the cheap reload alone
#: left 28,029 outline-coloured pixels on screen where there had been 28,029 -- the decoration
#: keeps the outline's thickness in the same cache as its colour. So the group cannot be
#: narrowed to its two colour keys without the thickness control lying.
#:
#: **`TitleBarOpacity` is the third, measured the same way.** A dialog of a class nobody manages,
#: over a backdrop switched between magenta and green, compared bar against body: with
#: `TitleBarOpacityActive=30` written and the reconfigure alone, the bar stayed opaque; the colour
#: signal alone after it did not move it either; the pair, as `writer` sends them, did (the bar let
#: through 71 % of the backdrop). So a change to the bar's opacity needs the colour cache like a
#: change to the outline's colour does.
COLOUR_CACHED_GROUPS = {"WindowOutlineStyle", "ButtonColors", "TitleBarOpacity"}


def note_reloads(tx, moved) -> None:
    """`moved` is a set of (source, group) pairs -- see `write_declared`."""
    sources = {source for source, _ in moved}
    if sources & {"klassy", "decoration", "windows", "plugins", "geometry"}:
        tx.reload_kwin = True
    if any(source == "klassy" and group in COLOUR_CACHED_GROUPS for source, group in moved):
        tx.reload_colours = True
    if "blur" in sources:
        tx.reload_blur = True
    if "tiling" in sources:
        tx.reload_tiling = True
