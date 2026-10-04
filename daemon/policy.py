"""Reading and setting what a window looks like.

Three switches per window, and the default for all of them is the theme: title bar hidden,
outline on, blurred. Everything else in here exists to make those three honest.

Whether a window currently *has* a decoration is read from two signals the compositor gives, and
the table below was measured rather than deduced:

| inset | decorated | reading                                   | what is missing       |
|-------|-----------|-------------------------------------------|-----------------------|
| > 0   | —         | decorated, no override yet                | the override          |
| 0     | yes       | decorated, override already in effect     | nothing               |
| 0     | no        | draws its own title bar                   | rule **and** override |

`inset` is `clientGeometry.y - frameGeometry.y`: how far the decoration pushes the content down.
`decorated` is true only when the compositor made a decoration. The inset is the strong signal and
does not depend on the title bar's opacity; `decorated` covers the case where an override has
already flattened the inset to zero.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import defaults
import effects
import klassy
import rules

#: Window types that never get a title bar of their own to manage.
SKIP_TYPES = ("dock", "desktopWindow", "popupWindow", "splash", "notification", "utility",
              "toolbar", "menu", "dropdownMenu", "popupMenu", "tooltip", "onScreenDisplay",
              "criticalNotification", "appletPopup", "dndIcon")

#: Regex metacharacters that stop a pattern from naming one single class.
_META = set("^$*+?[](){}|\\")


@dataclass
class Window:
    """What the compositor script reports about one window."""

    window_class: str
    resource_name: str = ""
    caption: str = ""
    decorated: bool = False
    inset: float = 0.0
    normal: bool = True
    special: bool = False
    skipped: tuple[str, ...] = ()
    #: The compositor's own handle for this window, which is the only thing that distinguishes
    #: two windows of the same class. The script has always sent it; dropping it here is what let
    #: closing one of three terminals take all three off the list.
    uuid: str = ""

    @classmethod
    def from_report(cls, d: dict) -> "Window":
        return cls(
            window_class=str(d.get("cls", "")),
            resource_name=str(d.get("nm", "")),
            caption=str(d.get("cap", "")),
            decorated=bool(d.get("deco", False)),
            inset=float(d.get("inset", 0)),
            normal=bool(d.get("normal", True)),
            special=bool(d.get("special", False)),
            skipped=tuple(d.get("skipped", ())),
            uuid=str(d.get("uuid", "")),
        )

    def manageable(self) -> bool:
        return bool(self.window_class) and self.normal and not self.special and not self.skipped

    def needs_rule(self) -> bool:
        """Does it draw its own title bar, so the compositor has to be told to decorate it?"""
        return self.inset == 0 and not self.decorated


@dataclass
class Switches:
    """The four things a person chooses about a window that are written *per window*.

    Floating and the geometry animation are chosen per window too, on the same table, and they are
    deliberately **not** here. Both are membership in a list that belongs to the whole compositor
    rather than a property attached to one window, and the difference is not academic: the values
    below are what `apply_defaults` in `daemon/kyprd_windows.py` applies, in one batch, to every
    window it has never seen — which at the first login is all of them. A list write inside that
    batch would make the tiling script re-read itself and tile the screen from scratch, at the
    busiest moment of the session. They go through `set_window_lists` instead, one transaction
    for a batch of rows.

    The values come from `daemon/defaults.py`; this dataclass carries the shape, not the opinion.
    """

    titlebar: bool = defaults.SWITCHES["titlebar"]   # True = a title bar is shown
    outline: bool = defaults.SWITCHES["outline"]
    transparency: bool = defaults.SWITCHES["transparency"]
    blur: bool = defaults.SWITCHES["blur"]


def pattern_class(pattern: str) -> str | None:
    """The class a pattern names, when it names exactly one.

    Recognises the shape this app writes — `(^|\\s)class$`, with dots escaped — and the bare
    literal the decoration's settings app writes. Returns None for a real regex like `brave-*`:
    that names a set, not a window, and rewriting it would reach windows nobody asked about.
    """
    p = pattern
    if p.startswith(r"(^|\s)") and p.endswith("$"):
        p = p[len(r"(^|\s)"):-1]
    elif p.endswith("$"):
        p = p[:-1]
    p = p.replace("\\.", ".").replace("\\-", "-").replace("\\_", "_")
    return None if (set(p) & _META or not p) else p


# ---------------------------------------------------------------- reading

def read_switches(tx, window_class: str, resource_name: str = "",
                  held: bool = False) -> tuple[Switches, str | None]:
    """The four switches as the config files have them, plus the pattern that governs the
    title bar, if any.

    `held` says the window's Transparency tick is being **remembered** rather than deduced --
    `TransparencyPart.held` in `daemon/kyprd_transparency.py` knows when. It exists for the one
    strength where deduction fails: at 100 %, the rule a tick writes (opacity 100, forced) is
    byte for byte what an unticked window reads, so the file cannot tell them apart and the
    reader has to be told.
    """
    overrides = klassy.read(tx.klassy)
    i = klassy.effective(overrides, window_class, resource_name)
    override = overrides[i] if i is not None else None
    return Switches(
        titlebar=not (override is not None and override.hides_titlebar()),
        outline=override.outline() if override is not None else True,
        #: Ticked means something is actually making this window see-through -- whichever rule
        #: that is, or the memory of a tick made while the strength stood at 100. Nothing forcing
        #: an opacity reads as opaque, which is what an undecorated desktop does.
        transparency=held or opacity_of(tx, window_class, resource_name) < rules.FULLY_OPAQUE,
        blur=effects.has_blur(tx.kwin, window_class),
    ), (override.pattern if override else None)


def opacity_of(tx, window_class: str, resource_name: str = "") -> int:
    """What the compositor would draw this window at, in per cent. 100 when nothing says."""
    found = rules.opacity_for(tx.rules, window_class, resource_name)
    return rules.FULLY_OPAQUE if found is None else found


def shared_pattern(pattern: str | None, window_class: str) -> bool:
    """Is this window governed by an entry that also governs other windows?

    It matters because such an entry cannot be changed on one window's behalf. The four Brave web
    apps all run off a single `brave-*` pattern, so turning the outline off for one of them would
    turn it off for all four.
    """
    if pattern is None:
        return False
    named = pattern_class(pattern)
    return named is None or named != window_class


# ---------------------------------------------------------------- writing

def _own_entry(tx, overrides, window: Window):
    """Index of an override that names only this window's class, making one if there is none.

    A new one is **seeded from whatever governs the window today**, so creating it changes
    nothing by itself. That matters when a loose pattern is in play: giving one of the four web
    apps behind `brave-*` its own entry must not quietly reset the other three settings along the
    way.

    Where it goes is a small thing with a visible consequence. The decoration returns the first
    match, so an entry that has to beat a broader pattern must sit ahead of it — but inserting at
    the head renumbers the entire list, and these files get snapshotted and diffed. So it goes to
    the head only when there is something to get ahead of, and to the end otherwise, where it is
    one new group and nothing else moves.
    """
    window_class = window.window_class
    i = klassy.effective(overrides, window_class, window.resource_name)
    if i is not None and not shared_pattern(overrides[i].pattern, window_class):
        return overrides, i
    if i is None:
        overrides.append(klassy.Override(pattern=klassy.pattern_for(window_class)))
        return overrides, len(overrides) - 1
    fresh = dataclasses.replace(overrides[i],
                                pattern=klassy.pattern_for(window_class),
                                extra=dict(overrides[i].extra))
    overrides.insert(0, fresh)
    return overrides, 0


#: The fields of an override that actually change how a window looks. Pattern, match type and
#: program name say *which* window it is, not what happens to it.
_VISIBLE_FIELDS = ("hide_titlebar", "border_override", "border_size", "preset",
                   "opaque_titlebar", "match_titlebar_to_app_color",
                   "prevent_apply_opacity_to_header")


def _looks_same(a, b) -> bool:
    return all(getattr(a, f) == getattr(b, f) for f in _VISIBLE_FIELDS)


def _prune_redundant(tx, overrides, window: Window) -> list:
    """Drop this class's own entry when a broader one already does exactly the same thing.

    Toggling a setting off and back on would otherwise leave an entry behind every time, and the
    list would fill up with rows that change nothing — which is precisely the clutter this app
    exists to spare someone.
    """
    mine = klassy.find(overrides, window.window_class)
    if mine is None:
        return overrides
    rest = overrides[:mine] + overrides[mine + 1:]
    other = klassy.effective(rest, window.window_class, window.resource_name)
    if other is not None and _looks_same(overrides[mine], rest[other]):
        return rest
    if other is None and _looks_same(overrides[mine], klassy.Override(pattern="")):
        # Nothing else governs it and ours says the theme default — but "no entry at all" means
        # a visible title bar, so an entry that hides it is never redundant here.
        return overrides
    return overrides


def _commit(tx, overrides, window: Window | None = None) -> None:
    if window is not None:
        overrides = _prune_redundant(tx, overrides, window)
    klassy.write(tx.klassy, overrides)   # renumbers the whole list, leaving no hole
    tx.reload_kwin = True


def set_titlebar(tx, window: Window, shown: bool) -> None:
    """Hide or show the window's title bar.

    Showing it means this app stops managing the window: its own entry goes, and so does the rule
    that forced a decoration in the first place. That is the honest meaning of "leave it alone",
    and unlike the older idea of ignoring a window, it actually undoes what was done.
    """
    window_class = window.window_class
    overrides = klassy.read(tx.klassy)
    i = klassy.effective(overrides, window_class, window.resource_name)
    hidden_now = i is not None and overrides[i].hides_titlebar()

    if shown:
        # `find_managed` returns a rule only when it speaks for this class alone. A broader one
        # — a `brave-*` covering four web apps — is left exactly as it is: undoing one window is
        # not a licence to change what three others depend on.
        managed = rules.find_managed(tx.rules, window_class, window.resource_name)
        if managed:
            # Only the two keys that forced the title bar. Whatever else is in that rule — an
            # activity, a virtual desktop, an opacity — is somebody's deliberate work and is none
            # of this app's business. The rule itself goes only if nothing is left doing anything.
            rules.release(tx.rules, managed, rules.TITLEBAR_KEYS)
            tx.reload_kwin = True
        mine = klassy.find(overrides, window_class)
        if mine is not None:
            del overrides[mine]
            _commit(tx, overrides)
            overrides = klassy.read(tx.klassy)
        # A loose pattern may still be hiding it. Shadow that with an entry of our own rather
        # than editing the shared one, which would reach windows nobody asked about.
        j = klassy.effective(overrides, window_class, window.resource_name)
        if j is not None and overrides[j].hides_titlebar():
            overrides, idx = _own_entry(tx, overrides, window)
            overrides[idx].hide_titlebar = klassy.TITLEBAR_NEVER
            _commit(tx, overrides, window)
        return

    if not hidden_now:
        overrides, idx = _own_entry(tx, overrides, window)
        overrides[idx].hide_titlebar = klassy.TITLEBAR_ALWAYS
        overrides[idx].border_override = True
        overrides[idx].border_size = klassy.BORDER_NONE
        _commit(tx, overrides, window)

    if window.needs_rule():
        existing = rules.find_for_class(tx.rules, window_class, window.resource_name)
        if existing is None:
            rules.create(tx.rules, rules.force_titlebar(window_class))
            tx.reload_kwin = True
        elif rules.adopt(tx.rules, existing, window_class):
            # Somebody else's rule was already forcing the title bar for this window. Put this
            # app's name on it so it is obvious who relies on it — and nothing else: the rule
            # already does what is needed, and the rest of it is not this app's to touch.
            tx.reload_kwin = True


def set_outline(tx, window: Window, on: bool) -> bool:
    """Keep or drop the theme's window outline for this window.

    The outline is not one of the twelve fields an override can carry, so it goes through the
    override's preset instead: a two-key preset that turns the outline off, and an empty preset
    meaning "inherit the global look". Measured to change the outline and nothing else.
    """
    window_class = window.window_class
    overrides = klassy.read(tx.klassy)
    i = klassy.effective(overrides, window_class, window.resource_name)
    wanted = "" if on else klassy.OUTLINE_OFF_PRESET
    if (i is None and on) or (i is not None and overrides[i].preset == wanted):
        return True
    if not on and klassy.ensure_outline_off_preset(tx.presets):
        tx.reload_kwin = True
    overrides, idx = _own_entry(tx, overrides, window)
    overrides[idx].preset = wanted
    _commit(tx, overrides, window)
    return True


def set_transparency(tx, window: Window, on: bool, strength: int,
                     previous: int | None = None, claim: bool = False) -> bool:
    """Make this window see-through at `strength`, or force it opaque.

    **Unticking writes rather than removes**, and that is the whole of why this is not shaped like
    the blur list. Removing the keys would hand the window back to whatever broader rule is in
    force — on this desk, one that makes every window see-through — so "off" would leave it exactly
    as see-through as before. Forcing 100 is the only thing that means opaque, and it wins for the
    same reason the picker's does: a rule of this app's sits at the head of the list.

    Nothing is written when the window is already at the wanted value, whoever arranged that. A
    window a broad rule already draws at this strength needs no rule of its own, and writing one
    would be this app taking over a line somebody else wrote to say the same thing. That is also
    what keeps applying a window's own settings back to it silent, which `scripts/simulate.sh`
    checks on every row of the table.

    **A window somebody else's rule makes see-through at a number of their own is left at it.**
    The tick means see-through and nothing more; the number is this app's strength, and it reaches
    a window only when the window is being ticked from opaque, when this app already owns its
    rule, or when the window stood at the strength the number is moving *from* -- `previous`,
    which is what moving the strength passes and nothing else does. Measured, on the one window
    nobody must ever see: `xwaylandvideobridge`, the desktop's own screen-sharing helper, hides
    itself behind a rule forcing opacity 0. The column read that as ticked, correctly, and
    re-applying the tick wrote 92 over it -- the helper on screen at 92%, and a batch that changed
    nothing reported as a write by the simulation.

    **`claim` is the one exception, and it is somebody asking.** A number of this window's own,
    chosen for this class on the Windows tab, is not this app's strength arriving at a window that
    happened to be see-through for another reason: it is a person naming this window and this
    number. So it takes the window over from whoever drew it before, the way ticking an opaque
    window does. Nothing else passes it, and it cannot reach an overlay -- `kyprd` refuses those
    before anything is written.
    """
    window_class = window.window_class
    target = max(1, min(rules.FULLY_OPAQUE, int(strength))) if on else rules.FULLY_OPAQUE
    current = opacity_of(tx, window_class, window.resource_name)
    if current == target:
        return True
    uuid = rules.find_owned(tx.rules, window_class, window.resource_name)
    if (on and not claim and uuid is None and current < rules.FULLY_OPAQUE
            and current != previous):
        return True
    wanted = rules.force_opacity(target)
    if uuid is None:
        rules.create(tx.rules, {**rules.for_class(window_class), **wanted})
        tx.reload_kwin = True
        return True
    if rules.apply_policy(tx.rules, uuid, wanted, rules.OPACITY_KEYS):
        tx.reload_kwin = True
    return True


def set_blur(tx, window_class: str, on: bool) -> bool:
    if effects.has_blur(tx.kwin, window_class) == on:
        return True
    if not effects.set_blur(tx.kwin, window_class, on):
        return False
    tx.reload_blur = True
    return True




def apply(tx, window: Window, wanted: Switches,
          strength: int = defaults.TRANSPARENCY) -> None:
    """Bring a window to the requested state, in the order that avoids a flash."""
    set_titlebar(tx, window, wanted.titlebar)
    if not wanted.titlebar:
        set_outline(tx, window, wanted.outline)
    set_transparency(tx, window, wanted.transparency, strength)
    #: Blur rides on the transparency, the way the outline rides on the hidden title bar. The
    #: effect paints a blurred copy of what is behind the window and it is seen **through** the
    #: window — so on an opaque one it is work nobody sees. Left unwritten rather than turned off,
    #: which is what lets the tick come back exactly as it was when the transparency does.
    if wanted.transparency:
        set_blur(tx, window.window_class, wanted.blur)


# ---------------------------------------------------------------- housekeeping

def normalize_rule_names(tx) -> list[tuple[str, str]]:
    """Put this app's name on every title-bar rule it manages. Returns (old, new).

    The person's own name is kept and prefixed, not replaced — see `rules.adopt`. Only the
    `Description` changes; no rule gains or loses a single policy from being adopted.
    """
    renamed = []
    for uuid, window_class, _ in rules.adoptable(tx.rules):
        change = rules.adopt(tx.rules, uuid, window_class)
        if change:
            renamed.append(change)
    if renamed:
        tx.reload_kwin = True
    return renamed


def diagnostics(tx) -> dict:
    return {
        "overrides": len(klassy.read(tx.klassy)),
        "orphan_overrides": klassy.orphans(tx.klassy),
        "rules": len(rules.read(tx.rules)),
        "orphan_rules": rules.orphans(tx.rules),
        "renamable": [c for _, c, _ in rules.adoptable(tx.rules)],
        "blur_mode": effects.blur_mode(tx.kwin),
        "blur_enabled": effects.plugin_enabled(tx.kwin, effects.BLUR_PLUGIN),
        "tiling_enabled": effects.plugin_enabled(tx.kwin, effects.TILING_PLUGIN),
        "geometry_enabled": effects.plugin_enabled(tx.kwin, effects.GEOMETRY_PLUGIN),
    }


#: Window classes never touched on their own. Desktop furniture — a launcher overlay, the shell,
#: a screen recorder bridge — is not an application window, and giving one a forced title bar is
#: at best useless and at worst disruptive. They stay listed and stay editable by hand; what they
#: do not get is the default applied to them unasked.
#:
#: The list is close to the one the tiling script keeps for the same reason, which is a decent
#: sign it is the right shape.
AUTO_SKIP = [
    "krunner", "plasmashell", "org.kde.plasmashell", "ksplashqml", "spectacle",
    "org.kde.spectacle", "xwaylandvideobridge", "kwin_wayland", "ksmserver-logout-greeter",
    "org.kde.polkit-kde-authentication-agent-1", "kded5", "kded6", "kruler", "org.kde.kruler",
    # This app's own overlays, all of them, by the shape of their class rather than one by one.
    # They are frameless on purpose, so none is ever a window to manage — and a window nobody
    # manages must not be judged as one that refuses to be managed.
    #
    # A pattern and not a list, because the list was measured to be the wrong shape: a second
    # overlay was added and its class was not put here, so it got the defaults like any new
    # window. The rule that forces a title bar is what makes the compositor **decorate** it, and
    # then a window meant to be nothing but what it paints came up with the decoration's outline
    # drawn around the whole of it and its panel behind. The settings window's own class is
    # `kyprx`, with no dash, so it cannot be caught by this.
    "kyprx-*",
    "gamescope", "Gamescope", "steam_app_*", "plasma-interactiveconsole",
]


def auto_skip(window_class: str) -> bool:
    from fnmatch import fnmatch
    return any(fnmatch(window_class, p) for p in AUTO_SKIP)
