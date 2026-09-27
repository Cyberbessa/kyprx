"""The names this app goes by, where every file of the daemon reads them from.

The bus names the daemon answers on, its overlays' window classes and titles, and the per-window
switches of the Windows tab. Each is a lookup key somewhere outside this repository -- the bus, the
compositor's placement rules, the tiler's float list, the settings file -- and nothing reports a
miss. The interface keeps copies that have to agree with these: the classes in `gui/kyprx.py`, the
titles in `gui/cheatsheet.py` and `gui/picker.py`. `SWITCHES` names the four switches whose
defaults `daemon/defaults.py` declares under the same name.
"""

from __future__ import annotations

import klassy
import rules


SERVICE = "org.cyberbessa.KyprX"
WINDOWS_IFACE = "org.cyberbessa.KyprX.Windows"
MANAGER_IFACE = "org.cyberbessa.KyprX.Manager"

#: KyprX's own compositor script: its id in `kwin-script/metadata.json`, which is also the name of
#: its folder under `kwin/scripts/` and of its switch, `kwinrc [Plugins] kyprxEnabled`. Spelled
#: again in `install.sh` (`PLUGIN_ID`), which runs before any of this is installed.
SCRIPT_PLUGIN = "kyprx"

#: The overlay's window class and title, which is how the compositor is told where to put it and
#: how the tiler is told to leave it alone. Both have to agree with `gui/kyprx.py` — the class
#: is the desktop file name the interface sets, the title is the one the overlay sets.
CHEATSHEET_CLASS = "kyprx-cheatsheet"
CHEATSHEET_TITLE = "KyprX shortcuts"

#: The wallpaper picker's, by the same rules and for the same reasons.
WALLPAPER_CLASS = "kyprx-wallpaper"
WALLPAPER_TITLE = "KyprX wallpapers"

#: Every overlay this app opens: the flag that starts it, its window class, its title, and the
#: description of the rule that keeps it centred. One table, because everything that used to be
#: written once for the cheatsheet has to happen for each of them -- the placement rule, the
#: tiler's float list, closing the one already open, collecting the one that exited. A second
#: overlay added by copying those out is a second overlay that gets three of the four.
#: The last field is whether the window has to be fully opaque. Only the picker does, and only
#: because it is a preview: a desktop-wide transparency rule is a taste, but a picture with eight
#: per cent of the window behind it mixed in is a picture that lies about what you are choosing.
OVERLAYS = (
    ("--cheatsheet", CHEATSHEET_CLASS, CHEATSHEET_TITLE, rules.CHEATSHEET_RULE, False),
    ("--wallpaper", WALLPAPER_CLASS, WALLPAPER_TITLE, rules.WALLPAPER_RULE, True),
)

#: Their window classes, for the two places that ask "is this one of ours?"
OVERLAY_CLASSES = frozenset(window_class for _, window_class, _, _, _ in OVERLAYS)

#: The same overlays, spelled as the decoration spells them in an override's pattern. The settings
#: file is filtered through this in both directions: an overlay managed as a window is exactly
#: what `daemon/policy.py` refuses to do and takes back off on every start, and a backup is no
#: reason for it to arrive on another machine.
OVERLAY_PATTERNS = frozenset(klassy.pattern_for(c) for c in OVERLAY_CLASSES)

#: The four a person chooses about a window that are genuinely *written per window* — the title
#: bar and the outline in a decoration override, the transparency in a compositor rule, the blur as
#: a name in the blur effect's list. `policy.apply` writes them, and they are the settings file's
#: vocabulary for a window row.
SWITCHES = ("titlebar", "outline", "transparency", "blur")

#: The other two columns of the same table, which are not switches at all: each is membership in
#: one comma-separated list that belongs to the whole compositor. They are kept apart from the
#: four above for a measured reason — the list ones must never be written from
#: `apply_defaults`, which runs over every unseen window in one batch at login, because the
#: tiler's list cannot be written without the tiler re-reading itself and tiling the screen from
#: scratch. `set_window_lists` is their path, and it does a whole batch of rows in one
#: transaction — so a batch costs one rearrangement rather than one per row.
LIST_SWITCHES = ("float", "animate")
