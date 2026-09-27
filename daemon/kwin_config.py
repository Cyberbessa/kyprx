"""The compositor's own settings that KyprX reads and writes: its focus behaviour and its decoration.

Two groups of `kwinrc` that belong to KWin itself rather than to a plugin -- the plugins' groups are
in `daemon/effects.py`. What the compositor reads when a key is absent comes from its own schema.
"""

from __future__ import annotations


#: The compositor's window-behaviour settings — the Focus half of them is on the Tiling page,
#: because focus is what decides whether a tiled screen feels like one.
WINDOWS_GROUP = "Windows"

#: The compositor's decoration schema, for the settings the Appearance page borrows from it.
DECORATION_SCHEMA = "/usr/share/config.kcfg/kwindecorationsettings.kcfg"
DECORATION_GROUP = "org.kde.kdecoration2"

#: What the compositor uses when the file is silent, from its own schema. `SeparateScreenFocus`
#: is the one worth naming: it flipped to **on** in Plasma 6, so an absent key means the opposite
#: of what it meant before, and a reading that assumed "absent is off" would be wrong.
WINDOWS_DEFAULTS = {
    "FocusPolicy": "ClickToFocus",
    "NextFocusPrefersMouse": "false",
    "DelayFocusInterval": "300",
    "FocusStealingPreventionLevel": "1",
    "SeparateScreenFocus": "true",
}
