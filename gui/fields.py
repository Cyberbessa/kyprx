"""The settings the Appearance, Effects and Tiling tabs edit, as data: which program's key each
control writes, and how.

Each `Field` names a source -- the decoration, the compositor, one of its plugins -- a group and a
key in that program's own spelling, the kind of control that edits it, and the one sentence that
says what it does; the tables are those three tabs' forms, section by section, and a section's
one-sentence hint is in `SECTION_HINTS` (`gui/widgets.py`), under the section's title. The daemon
writes what these name as it is (`SetGroups`), so this is where most of the window's knowledge of
other programs' keys lives, and `tests/test_field_keys.py` checks every key here against the
schema its program installs, where it installs one -- and the tiler's against the table of keys
`daemon/tiling.py` keeps, because the tiler is KyprX's own and installs no schema. Some are spelled
again elsewhere: `gui/tab_appearance.py` (the outline's keys, and Better Blur's `CornerRadius`,
which it writes to follow the decoration's corner), `gui/tab_tiling.py` (the compositor's focus
keys, and the tiler's that grey others), `gui/tiling_value.py` (the tiler's `arrangements`, one
JSON value rather than a field, which `gui/arrangements_box.py` and `gui/zone_layouts_box.py`
edit), `gui/profiles_box.py` (a profile's summary), `gui/kyprx.py` (the Effects tab's plugin ids)
and `gui/cheatsheet.py` (the keys its card reads) -- none of those is checked by that test. No Qt
here, so it can be read without a display.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------- settings schema

@dataclass
class Field:
    """One editable setting.

    `source` says which config the daemon should write it to, `group` which section within it.
    The names and the value spellings come from the decoration's own preset file, which is
    written by the installed version — upstream has since renamed some of these keys, so its
    schema is the wrong thing to read.

    `also` is for the decoration's paired keys. Several of its settings exist twice, once for the
    active window and once for the inactive one, and its own dialog keeps them locked together by
    default. Writing both from one control is the same promise with one row instead of two — the
    alternative doubles this form for a distinction nobody wants to make.
    """

    source: str
    group: str
    key: str
    label: str
    kind: str = "text"       # bool | int | float | choice | color | text | list
    low: float = 0
    high: float = 100
    step: float = 1
    suffix: str = ""
    choices: list[tuple[str, str]] = field(default_factory=list)
    #: What the setting does, in a sentence or two: the tooltip of its name and of its control,
    #: and on the Tiling tab the sentence behind the mark after its name as well (`marks` in
    #: `SettingsPage`).
    hint: str = ""
    also: list[str] = field(default_factory=list)
    #: For a `choice` whose options each set **several keys to different values** — which is what
    #: the desktop's own focus policy control is. Six options, four of them one setting and two of
    #: them that setting plus a second switch. `also` cannot express it: that writes one value to
    #: several keys, and this writes a different value to each.
    writes: dict[str, dict[str, str]] = field(default_factory=dict)


OUTLINE_STYLES = [
    ("WindowOutlineNone", "None"),
    ("WindowOutlineShadowColor", "Shadow colour"),
    ("WindowOutlineContrast", "Contrast"),
    ("WindowOutlineAccentColor", "Accent colour"),
    ("WindowOutlineAccentWithContrast", "Accent with contrast"),
    ("WindowOutlineCustomColor", "Custom colour"),
    ("WindowOutlineCustomWithContrast", "Custom with contrast"),
]

#: The two of the seven that read a colour of ours. The decoration's own list, and the same pair
#: `daemon/klassy.py` keeps -- written out here rather than asked for, because this is only ever
#: used to decide which of two controls on this very page to fill in.
OUTLINE_CUSTOM_STYLES = ("WindowOutlineCustomColor", "WindowOutlineCustomWithContrast")

#: The corner radius is the only number on this page that two things read, and it is the one
#: people notice when they disagree: the decoration rounds the window and the blur effect rounds
#: what it blurs behind it, and a mismatch shows as a bright sliver in each corner. So this page
#: writes both, and the Effects tab no longer asks.
CORNER_RADIUS_NOTE = "The blur's corner follows it, or the blur shows past the rounded corner."

#: The two of the seven styles that read an accent rather than a colour of their own. Beside
#: `OUTLINE_CUSTOM_STYLES` and for the same job: deciding which of the rows on this page are doing
#: anything, so the rest can be greyed instead of sitting there offering to set a value nothing
#: reads.
OUTLINE_ACCENT_STYLES = ("WindowOutlineAccentColor", "WindowOutlineAccentWithContrast")

APPEARANCE_FIELDS = [
    ("Window", [
        Field("klassy", "Windeco", "WindowCornerRadius", "Corner radius", "float",
              0, 30, 0.5, " px", hint=CORNER_RADIUS_NOTE),
        Field("klassy", "WindowOutlineStyle", "WindowOutlineThickness", "Outline", "float",
              0, 10, 0.25, " px", hint="How thick the ring around a window is."),
        Field("klassy", "WindowOutlineStyle", "WindowOutlineStyleActive", "Focused window",
              "choice", choices=OUTLINE_STYLES,
              hint="Where the ring around the window you are using takes its colour from."),
        Field("klassy", "WindowOutlineStyle", "WindowOutlineCustomColorActive",
              "Its custom colour", "color",
              hint="The colour the ring wears while the style above is one of the custom ones."),
        Field("klassy", "WindowOutlineStyle", "WindowOutlineCustomColorOpacityActive",
              "Its opacity", "int", 0, 100, 1, " %",
              hint="How solid that custom colour is drawn."),
        Field("klassy", "WindowOutlineStyle", "WindowOutlineAccentColorOpacityActive",
              "Its accent opacity", "int", 0, 100, 1, " %",
              hint="How solid the ring is drawn while it takes the accent colour."),
        Field("klassy", "WindowOutlineStyle", "WindowOutlineStyleInactive", "Other windows",
              "choice", choices=OUTLINE_STYLES,
              hint="Where the ring around every other window takes its colour from."),
        Field("klassy", "WindowOutlineStyle", "WindowOutlineCustomColorInactive",
              "Their custom colour", "color",
              hint="The colour those rings wear while the style above is one of the custom ones."),
    ]),
]

#: Which windows the blur reaches, as one question with four answers rather than as two switches
#: whose combination somebody has to work out. The four are exactly the four the daemon already
#: tells apart -- see `blur_mode` in `daemon/effects.py` -- and the pair of keys behind them is
#: unchanged, which is what `Field.writes` is for.
#:
#: Two of the four take the Windows tab's Blur column out of the conversation altogether, and the
#: column says so itself when they are in force.
BLUR_TARGETS = [
    ("listed", "Only the windows ticked on the Windows tab"),
    ("unlisted", "Every window except the ones unticked there"),
    ("all", "Every window"),
    ("none", "No window"),
]

BLUR_TARGET_KEYS = {
    "listed": {"BlurMatching": "true", "BlurNonMatching": "false"},
    "unlisted": {"BlurMatching": "false", "BlurNonMatching": "true"},
    "all": {"BlurMatching": "true", "BlurNonMatching": "true"},
    "none": {"BlurMatching": "false", "BlurNonMatching": "false"},
}

EFFECTS_FIELDS = [
    ("Blur", [
        Field("blur", "", "BlurMatching", "Which windows", "choice", choices=BLUR_TARGETS,
              writes=BLUR_TARGET_KEYS,
              hint="Which windows are blurred behind, and whether the Windows tab decides it."),
        Field("blur", "", "BlurDecorations", "Window frames", "bool",
              hint="Blur behind the frame around a window as well as behind the window."),
        Field("blur", "", "BlurMenus", "Menus", "bool", hint="Blur behind menus as they open."),
        Field("blur", "", "BlurDocks", "Panels", "bool", hint="Blur behind the desktop's panels."),
        Field("blur", "", "BlurStrength", "Strength", "int", 1, 15,
              hint="How far the blur spreads what is behind the window."),
        Field("blur", "", "NoiseStrength", "Noise", "int", 0, 20,
              hint="Grain mixed into the blur, which hides the banding a smooth blur can show."),
        Field("blur", "", "Brightness", "Brightness", "int", 0, 200, 1, " %",
              hint="Lightens or darkens what shows through the window."),
        Field("blur", "", "Saturation", "Saturation", "int", 0, 300, 1, " %",
              hint="How strong the colours behind the window come through."),
        Field("blur", "", "Contrast", "Contrast", "int", 0, 200, 1, " %",
              hint="How far apart the light and dark parts behind the window are drawn."),
    ]),
    ("Window animation", [
        Field("geometry", "", "Duration", "Duration", "int", 0, 2000, 10, " ms",
              hint="How long a window takes to settle when it is moved or resized."),
    ]),
]

#: The desktop's focus policy, as its own settings present it: six options that are really four
#: policies and one extra switch. The labels are KDE's, verbatim — a second vocabulary for the
#: same setting would be a second thing to learn.
FOCUS_POLICIES = [
    ("click", "Click to focus",
     {"FocusPolicy": "ClickToFocus", "NextFocusPrefersMouse": "false"}),
    ("click-mouse", "Click to focus (mouse precedence)",
     {"FocusPolicy": "ClickToFocus", "NextFocusPrefersMouse": "true"}),
    ("follows", "Focus follows mouse",
     {"FocusPolicy": "FocusFollowsMouse", "NextFocusPrefersMouse": "false"}),
    ("follows-mouse", "Focus follows mouse (mouse precedence)",
     {"FocusPolicy": "FocusFollowsMouse", "NextFocusPrefersMouse": "true"}),
    ("under", "Focus under mouse",
     {"FocusPolicy": "FocusUnderMouse", "NextFocusPrefersMouse": "false"}),
    ("strictly-under", "Focus strictly under mouse",
     {"FocusPolicy": "FocusStrictlyUnderMouse", "NextFocusPrefersMouse": "false"}),
]

#: The two the desktop itself warns about: they break the window switcher, and with a tiling
#: script that also navigates by keyboard, they break that too.
FOCUS_DISCOURAGED = ("under", "strictly-under")

FOCUS_STEALING_LEVELS = [
    ("0", "None — a new window always takes focus"),
    ("1", "Low"),
    ("2", "Medium"),
    ("3", "High"),
    ("4", "Extreme — nothing takes focus unless you give it"),
]

#: Measured against the compositor's source: it overrides these rather than honouring them, so a
#: control left enabled would show a number the compositor has already discarded. These are what a
#: greyed control's name says instead of its own sentence (`TilingPage._follow_focus_policy`).
FOCUS_DELAY_NOTE = "Ignored while the policy is one of the click-to-focus ones."
FOCUS_STEALING_NOTE = ("Forced to None while the policy is one of the under-mouse ones — the "
                       "compositor does this itself.")

#: Where a new window lands, as four answers rather than as a number between nought and three with
#: the meanings hidden in a tooltip. The values are what `[Script-kyprx] newWindowPosition` holds,
#: in the tiler's fill order: 0 puts the window last, 1 first -- in the master zone -- and 2 and 3
#: beside the window that has the focus. Nought is the tiler's default.
NEW_WINDOW_POSITIONS = [
    ("0", "At the end of the layout"),
    ("1", "As the master window"),
    ("2", "Before the focused window"),
    ("3", "After the focused window"),
]

#: What a window that opens does when its screen already has a window in every zone of the
#: arrangement's last layout -- the fifth on Balanced, whose last layout has four zones. The values
#: are what `[Script-kyprx] newWindowOverflow` holds: 0 a desktop of its own, made for it; 1
#: floating in the middle of the screen; 2 squeezed in, the last zone split in half along its
#: longer side for it and again for each window more -- the cascade, which a window that comes back
#: to a full screen, from being minimised, from floating or from another screen, gets whatever this
#: says. One is the tiler's default and KyprX's.
NEW_WINDOW_OVERFLOW = [
    ("0", "Open it on a new desktop"),
    ("1", "Let it float over the others"),
    ("2", "Squeeze it in by splitting the last zone"),
]

#: Where that desktop is made, as `[Script-kyprx] newDesktopPosition` holds it. 0, the default and
#: the owner's choice, after the last desktop: the desktops already there keep their numbers, and
#: the keys that go to a desktop by its number keep going where they went. 1 straight after the one
#: the window came from, which moves the desktops after it one place along for as long as it is
#: there.
NEW_DESKTOP_POSITIONS = [
    ("0", "After your desktops"),
    ("1", "Right after the one it came from"),
]

#: Focus first, because it is the one on this tab that decides how the desktop *feels* rather than
#: how it is arranged: with nothing overlapping, the pointer is how you move between windows, and
#: everything below is arrangement. The owner asked for it there.
#:
#: What happens to a window as it opens is under *Automatic tiling*, beside its switch -- where it
#: goes, what it does when no zone is left, where the desktop it then gets is made, whether a
#: dialog floats -- because none of it does anything while the switch is off, and the tab greys it
#: with the switch (`TilingPage.FOLLOWS`). The names on screen are there too, though they work in
#: both modes: with it on, the layout keys move between arrangements, and with it off between the
#: zone layouts a drag offers, and the card names either.
#:
#: Every key under `tiling` is one of `[Script-kyprx]`, KyprX's own tiler's, and the daemon tells
#: the tiler to read them again when one is written -- no restart, no compositor reload. The zone
#: layouts and the arrangements are one key of the same group, edited by the two boxes between
#: *Automatic tiling* and *Gaps* (`gui/arrangements_box.py`, `gui/zone_layouts_box.py`).
TILING_FIELDS = [
    ("Focus", [
        Field("windows", "", "FocusPolicy", "Window activation policy", "choice",
              choices=[(v, label) for v, label, _ in FOCUS_POLICIES],
              writes={v: keys for v, _, keys in FOCUS_POLICIES},
              hint="What it takes for a window to become the one you are typing into."),
        Field("windows", "", "DelayFocusInterval", "Delay focus by", "int", 0, 3000, 100, " ms",
              hint="How long the pointer rests on a window before that window takes the focus."),
        Field("windows", "", "FocusStealingPreventionLevel", "Focus stealing prevention",
              "choice", choices=FOCUS_STEALING_LEVELS,
              hint="Whether a window that opens takes the focus from the one you are using."),
        Field("windows", "", "SeparateScreenFocus", "Separate screen focus", "bool",
              hint="Each screen remembers its own focused window. Needs a second monitor."),
    ]),
    ("Automatic tiling", [
        Field("tiling", "", "autoTiling", "Automatic tiling", "bool",
              hint="Windows are laid out by the arrangement as they open and close. Off, they "
                   "stay where they are put, and a window dragged through the bar at the top of "
                   "the screen, or with Shift held, is offered the zones to drop it in. "
                   "Toggle Automatic Tiling, Meta+T unless you changed it, switches it too."),
        Field("tiling", "", "showOsd", "Show names on screen", "bool",
              hint="A card in the middle of the screen that names what Next Layout or Previous "
                   "Layout moves to -- the arrangement, or with automatic tiling off the zone "
                   "layout -- says that Toggle Automatic Tiling switched automatic tiling on or "
                   "off, and names the desktop a window is sent to when the arrangement is full."),
        Field("tiling", "", "newWindowPosition", "Where a new window goes", "choice",
              choices=NEW_WINDOW_POSITIONS,
              hint="Where a window that has just opened is put in the layout."),
        Field("tiling", "", "newWindowOverflow", "When the arrangement is full", "choice",
              choices=NEW_WINDOW_OVERFLOW,
              hint="What a window that opens does when its screen already has a window in every "
                   "zone of the arrangement's last layout, as a fifth one does on Balanced. A "
                   "window that comes back from being minimised, from floating or from another "
                   "screen is always squeezed in."),
        Field("tiling", "", "newDesktopPosition", "Where a new desktop goes", "choice",
              choices=NEW_DESKTOP_POSITIONS,
              hint="Where that new desktop is made. After your desktops, the keys that go to a "
                   "desktop by its number keep going to the same one; right after the one the "
                   "window came from, the desktops after it move one place along while it is "
                   "there. KyprX removes it once it is empty and you have left it."),
        Field("tiling", "", "floatUtility", "Float utility windows", "bool",
              hint="Dialogs, and the small windows an application opens beside itself, are left "
                   "where they are put."),
        Field("tiling", "", "adjustLayoutLive", "Neighbours follow while you drag an edge", "bool",
              hint="Dragging a tiled window's edge resizes the windows beside it as you go, "
                   "rather than when you let go."),
    ]),
    ("Gaps", [
        Field("tiling", "", "screenGapTop", "Top", "int", 0, 200, 1, " px",
              hint="The space left between the top of the screen and the windows."),
        Field("tiling", "", "screenGapBottom", "Bottom", "int", 0, 200, 1, " px",
              hint="The space left between the bottom of the screen and the windows."),
        Field("tiling", "", "screenGapLeft", "Left", "int", 0, 200, 1, " px",
              hint="The space left between the left edge of the screen and the windows."),
        Field("tiling", "", "screenGapRight", "Right", "int", 0, 200, 1, " px",
              hint="The space left between the right edge of the screen and the windows."),
        Field("tiling", "", "screenGapBetween", "Between windows", "int", 0, 200, 1, " px",
              hint="The space left between one window and the next."),
    ]),
    ("Never tiled", [
        Field("tiling", "", "floatingTitle", "Floating window titles", "list",
              hint="Windows whose title contains one of these are left where they are put."),
        Field("tiling", "", "ignoreClass", "Ignored window classes", "list",
              hint="Applications the tiler does not touch at all. KyprX's own list applies as "
                   "well, whatever is here: the desktop's shell and launcher, the lock and "
                   "log-out screens, screenshots, Yakuake, KyprX's overlays, games through Steam "
                   "or gamescope, and a few more."),
        Field("tiling", "", "ignoreTitle", "Ignored window titles", "list",
              hint="Windows whose title contains one of these are not tiled at all."),
        Field("tiling", "", "ignoreScreen", "Ignored screens", "list",
              hint="Screens the tiler leaves alone, by the name the desktop gives them, such as "
                   "DP-1."),
    ]),
]
