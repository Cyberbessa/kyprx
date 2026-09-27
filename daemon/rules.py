"""KWin window rules, in `kwinrulesrc`.

File shape: one group per rule, named with a UUID, plus a `[General]` holding `rules=` (the UUID
list, **in precedence order**) and `count=`.

Three decisions, and the third is the one that matters most:

- **A new rule goes to the front.** KWin's `WindowRules::checkNoBorder` returns the first rule
  that matches, so whatever sits at the head wins.

- **Nothing is removed by sweeping.** Only the groups named are touched; a UUID group missing
  from `rules=` is reported by `orphans()` and never deleted. It is inert config someone may
  still be keeping.

- **This app owns two keys in a rule and nothing else.** A rule can carry any of KWin's eighty-odd
  properties — an activity, a virtual desktop, a size, an opacity, a shortcut — and all of them are
  somebody's deliberate work. So writing is a **merge**: the two keys go in, every other key is
  left exactly as it was. And undoing takes those two keys **out**, deleting the rule only when
  nothing of anybody's is left in it.

  This is not theoretical tidiness. Before, writing was `delete_group` followed by a rewrite of
  five keys, and undoing was `delete_group` outright — so a rule that also pinned an activity and
  a desktop lost both the moment its window was unmanaged. On this machine one rule is in exactly
  that shape.
"""

from __future__ import annotations

import re
import uuid as _uuid

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

#: `Description` of the rules this app owns. It is what shows up in KDE's own rules editor.
PREFIX = "KyprX: "

#: KWin rule policies, as written in `<key>rule=`
DONT_AFFECT = 1
FORCE = 2

#: `wmclassmatch`, and `titlematch`, which share one vocabulary
MATCH_UNIMPORTANT = 0
MATCH_EXACT = 1
MATCH_SUBSTRING = 2
MATCH_REGEX = 3

#: What the compositor reads when a rule leaves a key out -- its own schema, `rulesettings.kcfg`
#: in the KWin sources: every string match defaults to `UnimportantMatch`, so a rule with no
#: `wmclassmatch` applies to **every** window whatever its `wmclass` says, and every property's
#: policy defaults to `UnusedForceRule`, so an `opacityactive` with no `opacityactiverule` does
#: nothing. This file read both the other way round -- a missing match type as exact, a missing
#: policy as forced -- which is how a rule written in the desktop's own dialog to make every window
#: see-through would have read as reaching one window, or none. Every rule this app writes names
#: both, so its own rules never depended on the defaults.
DEFAULT_MATCH = MATCH_UNIMPORTANT
UNUSED = 0

#: The overlays' own rules. They are not per-window rules: they force no title bar on anything,
#: they only say where an overlay opens. Each is kept under a description of its own so
#: `find_owned` — which looks for `PREFIX + window class` — can never collide with them.
#:
#: Two constants and not one name built from the class, because a description is a **lookup key**
#: on an install that already exists. Changing the spelling of one strands the rule that is there
#: and costs a pass in `migrate.py` to find it again; adding a second costs nothing.
CHEATSHEET_RULE = "KyprX cheatsheet overlay"
WALLPAPER_RULE = "KyprX wallpaper overlay"

#: `Placement::Policy` from the compositor's `options.h`. **Centred is 5.**
#:
#: Worth the note because the wrong number is a rule that applies cleanly and does something else.
#: Up to KWin 5.24 `Cascade` held slot 5 and centred was 6; `Cascade` was then removed and every
#: value after it moved down one. On 6.x, **6 is the top-left corner**. The value has been 5 from
#: 5.27 onwards, which is every version this app can run against.
PLACEMENT_CENTERED = 5

#: Keys that select which windows a rule applies to, as opposed to what it does to them.
_MATCHERS = {"wmclass", "wmclassmatch", "wmclasscomplete", "title", "titlematch", "types",
             "windowrole", "windowrolematch", "clientmachine", "clientmachinematch",
             "tag", "tagmatch", "hastransientparent", "hastransientparentmatch",
             "Description", "description"}

#: The keys this app writes, per purpose. Everything outside these is somebody else's and is
#: never written, never deleted, never reordered.
TITLEBAR_KEYS = ("noborder", "noborderrule")
PLACEMENT_KEYS = ("placement", "placementrule")

#: The four keys that pin a window's opacity, active and inactive. **This is what "transparency"
#: is**, on this desktop and in this app: the compositor draws the window at that percentage, and
#: everything behind it shows through. The decoration's own opacity settings are about the title
#: bar alone, which a window managed here does not have.
#:
#: Written for the wallpaper picker, where the reason is in `overlay_placement`, and per window
#: for the Transparency column.
OPACITY_KEYS = ("opacityactive", "opacityactiverule", "opacityinactive", "opacityinactiverule")

#: Fully opaque, as KWin counts it: a percentage.
FULLY_OPAQUE = 100


def new_uuid() -> str:
    return str(_uuid.uuid4())


def read(cfg) -> list[tuple[str, dict[str, str]]]:
    """The rules in `[General] rules=` order, each as (uuid, raw entries).

    Returning raw entries is deliberate: a rule can carry dozens of keys this app knows nothing
    about — activity, desktop, opacity, size, position — and rewriting it through a typed model
    would drop whatever did not fit.
    """
    order = [u for u in (cfg.get("General", "rules", "") or "").split(",") if u]
    return [(u, cfg.groups[u]) for u in order if u in cfg.groups]


def orphans(cfg) -> list[str]:
    """UUID groups absent from `[General] rules=` — inert, and never removed from here."""
    order = set((cfg.get("General", "rules", "") or "").split(","))
    return sorted(g for g in cfg.groups if UUID_RE.match(g) and g not in order)


def class_of(entries: dict[str, str]) -> str:
    """The window class a rule matches.

    KDE writes `wmclass` two ways. Plain, when you type the class yourself. And "whole class"
    (`wmclasscomplete=true`), when the rule came from *Detect window properties*: then the value
    is `resourceName resourceClass`, and a Wayland app's resource name is empty — which is what
    produces the `wmclass=\\sdiscord` entries. Either way the class is the last token.
    """
    raw = entries.get("wmclass", "")
    if str(entries.get("wmclasscomplete", "false")).lower() == "true":
        parts = [p for p in raw.split(" ") if p]
        return parts[-1] if parts else ""
    return raw.strip()


def policies(entries: dict[str, str]) -> set[str]:
    """The `<key>rule=` keys present — that is, everything the rule actually does."""
    return {k for k in entries if k.endswith("rule") and k not in _MATCHERS}


def forces_titlebar(entries: dict[str, str]) -> bool:
    """Does this rule force the window to have a title bar?"""
    return (entries.get("noborderrule") == str(FORCE)
            and str(entries.get("noborder", "false")).lower() == "false")


def single_purpose(entries: dict[str, str]) -> bool:
    """Is forcing the title bar the *only* thing this rule does?"""
    return policies(entries) == {"noborderrule"}


def adoptable(cfg) -> list[tuple[str, str, str]]:
    """Rules that force a title bar and do not yet carry this app's name.

    Returns (uuid, window class, current description).

    This deliberately **does not** skip a rule that also pins an activity or a desktop, and that
    is a change. It used to, because adopting meant replacing the name with the window class and
    removing meant deleting the whole group — so a rule with somebody's work in it was safer left
    unnamed. Neither is true any more: adopting keeps the name and only prefixes it, and removing
    takes out two keys. With the destruction gone, the reason to leave rules unmanaged goes too.
    """
    out = []
    for uuid, entries in read(cfg):
        if not forces_titlebar(entries):
            continue
        current = entries.get("Description", "")
        if current.startswith(PREFIX):
            continue
        out.append((uuid, class_of(entries), current))
    return out


def matches(entries: dict[str, str], window_class: str, resource_name: str = "") -> bool:
    """Would KWin apply this rule to this window, going by its class alone?

    Worth doing properly rather than comparing strings: one of the rules here matches
    `brave-*` as a regex and covers four different window classes. A plain equality test would
    miss it and the app would write a second, redundant rule for every one of them.

    Title, role and window type are not considered — a rule narrowed by those may still not
    apply, so a true answer here means "covered as far as the class goes".
    """
    raw = entries.get("wmclass", "")
    whole = str(entries.get("wmclasscomplete", "false")).lower() == "true"
    policy = str(entries.get("wmclassmatch", DEFAULT_MATCH))
    if policy == str(MATCH_UNIMPORTANT):
        return True                       # the class does not matter to this rule at all
    if whole and policy == str(MATCH_EXACT) and not resource_name:
        # A "whole class" rule carries `resourceName resourceClass`, and the resource name only
        # comes from a window that is open. Asked about a window that is not, comparing the two
        # halves can only fail — so compare the half that is known. Measured: a window whose
        # settings were changed while it was closed got a **second** rule written beside the one
        # already there, because the existing one named a resource nobody could see any more.
        return class_of(entries) == window_class
    target = f"{resource_name} {window_class}" if whole else window_class
    if policy == str(MATCH_REGEX):
        try:
            return bool(re.search(raw, target))
        except re.error:
            return False
    if policy == str(MATCH_SUBSTRING):
        return raw in target
    return raw.strip() == target.strip()


def find_for_class(cfg, window_class: str, resource_name: str = "") -> str | None:
    """UUID of a rule that already forces a title bar for this class, whoever wrote it."""
    for uuid, entries in read(cfg):
        if forces_titlebar(entries) and matches(entries, window_class, resource_name):
            return uuid
    return None


def names_only(entries: dict[str, str], window_class: str) -> bool:
    """Does this rule speak for this window class **and no other**?

    The test is the matcher, not the match: an exact `wmclass` naming this class covers one
    class, while a regex like `brave-*` or a substring covers a family of them.

    Without this, undoing one window took a rule that several windows relied on. Measured on a
    real config: one rule named `brave-*` matched four separate web apps, and unticking the title
    bar on any one of them deleted the rule, the matcher somebody wrote by hand, and the forced
    title bar on the other three. The override side of this app has had the same guard from the
    start; the rule side did not.
    """
    if str(entries.get("wmclassmatch", DEFAULT_MATCH)) != str(MATCH_EXACT):
        return False
    return class_of(entries) == window_class


def find_managed(cfg, window_class: str, resource_name: str = "") -> str | None:
    """UUID of the rule this app manages for this class, and for this class alone.

    Four conditions, all of them necessary. It carries this app's name, it forces a title bar, it
    matches this window, and it speaks for no other window class. The name alone used to be the
    test, and it was both too narrow — a rule renamed to `KyprX: brave-*` can never be found
    again, because no window has that class — and too broad, because a rule keeps the name long
    after somebody has added their own policies to it.
    """
    for uuid, entries in read(cfg):
        if (entries.get("Description", "").startswith(PREFIX)
                and forces_titlebar(entries)
                and matches(entries, window_class, resource_name)
                and names_only(entries, window_class)):
            return uuid
    return None


def find_owned(cfg, window_class: str, resource_name: str = "") -> str | None:
    """UUID of the rule this app owns for this class, whatever that rule happens to do.

    `find_managed` with one condition dropped: it need not force a title bar. That condition is
    right where it is — releasing the title bar must never touch a rule that is not forcing one —
    and wrong here, because a window whose application negotiates decorations properly never needed
    that key and can still carry a transparency of this app's.

    The overlays' rules cannot be reached through this: their descriptions are `KyprX cheatsheet
    overlay` and `KyprX wallpaper overlay`, neither of which begins with `KyprX: `. That is the
    whole reason those two constants are spelled the way they are.
    """
    for uuid, entries in read(cfg):
        if (entries.get("Description", "").startswith(PREFIX)
                and matches(entries, window_class, resource_name)
                and names_only(entries, window_class)):
            return uuid
    return None


def opacity_for(cfg, window_class: str, resource_name: str = "") -> int | None:
    """The opacity the compositor would force on this window, or None when nothing does.

    It walks the list in `[General] rules=` order and stops at the first rule that sets the key,
    because that is what KWin does. Looking only at this app's own rule would be easier and would
    lie: a rule somebody wrote by hand making every window slightly see-through is as real as one
    written here, and the Transparency column has to say so rather than drawing an empty box over
    a window that is plainly translucent.

    `Do not affect` is skipped — it is the one policy that means "this rule has nothing to say
    about the opacity", and reading it as a value would stop the walk on a rule that does nothing.
    So is a rule with no policy at all: the compositor reads that as unused (see `UNUSED`).
    """
    for _, entries in read(cfg):
        if "opacityactive" not in entries:
            continue
        if str(entries.get("opacityactiverule", UNUSED)) in (str(UNUSED), str(DONT_AFFECT)):
            continue
        if not matches(entries, window_class, resource_name):
            continue
        try:
            return int(entries["opacityactive"])
        except (TypeError, ValueError):
            return None
    return None


def find_described(cfg, description: str) -> str | None:
    """UUID of the rule carrying exactly this description, whoever wrote it."""
    for uuid, entries in read(cfg):
        if entries.get("Description") == description:
            return uuid
    return None


def for_class(window_class: str) -> dict[str, str]:
    """The half of a rule that says which window it is about, and nothing about what to do to it.

    Separated out because two different things now start a rule of this app's — forcing a title
    bar, and forcing an opacity — and a window that needs the second without the first is
    ordinary. Two copies of the matcher would be two spellings of a lookup key, which `MAP.md`
    warns about: nothing reports a miss.
    """
    return {
        "Description": PREFIX + window_class,
        "wmclass": window_class,
        "wmclassmatch": str(MATCH_EXACT),
    }


def force_titlebar(window_class: str) -> dict[str, str]:
    """A brand-new rule that makes a client-side decorated window accept a server-side decoration.

    `noborder=false` with `noborderrule=2` is "No titlebar and frame -> Force -> No": it forces
    the window to **have** a title bar, which is what gives the decoration something to style.
    Hiding that bar again is the override's job, not this one's.
    """
    return {**for_class(window_class), "noborder": "false", "noborderrule": str(FORCE)}


def force_opacity(percent: int) -> dict[str, str]:
    """The four keys that force a window's opacity, both states at the same value.

    Both, because a window that fades when it loses focus is a window whose transparency is a
    focus indicator, and that is a different setting from the one being offered. One number, one
    answer.
    """
    value = str(max(1, min(FULLY_OPAQUE, int(percent))))
    return {"opacityactive": value, "opacityactiverule": str(FORCE),
            "opacityinactive": value, "opacityinactiverule": str(FORCE)}


def overlay_placement(window_class: str, title: str, description: str,
                      opaque: bool = False) -> dict[str, str]:
    """A brand-new rule that opens one of this app's overlays in the middle of the screen.

    It has to be a rule, and that is not a preference. A Wayland client cannot place its own
    window: the protocol has no call for it, and Qt discards the coordinates — measured, a
    `move()` on a top-level ends up at the corner of the screen. The compositor decides, and a
    rule is how you tell the compositor.

    Matched on the **class**, which the overlay has to itself. It used to match on the title,
    because the overlay shared a class with the settings window — and sharing that class had a
    worse consequence than an awkward matcher: a frameless window makes the whole class look like
    an application that draws its own title bar.

    One thing deliberately absent: `position`. A forced position marks the window as already
    placed, and then `placement` is never consulted at all — the two cancel rather than combine.

    **`opaque` pins the window at full opacity, and only the wallpaper picker asks for it.** A
    desktop-wide rule that makes every window slightly see-through is somebody's taste and is none
    of this app's business — except on the one window whose whole job is to show what a picture
    looks like. Eight per cent of whatever happens to be behind it, mixed into the picture, is not
    a preview. The cheatsheet is left alone: it shows keys, not pictures, and the taste applies.

    This works because a new rule goes to the head of the list and KWin answers with the first
    rule that matches — so this one is asked before the broad one. A rule of this app's that
    somebody has since moved below the broad one would stop winning, which is the same precedence
    the forced title bar has always depended on.
    """
    entries = {
        "Description": description,
        "placement": str(PLACEMENT_CENTERED),
        "placementrule": str(FORCE),
        "title": title,
        "titlematch": str(MATCH_UNIMPORTANT),
        "wmclass": window_class,
        "wmclassmatch": str(MATCH_EXACT),
    }
    if opaque:
        entries.update({
            "opacityactive": str(FULLY_OPAQUE),
            "opacityactiverule": str(FORCE),
            "opacityinactive": str(FULLY_OPAQUE),
            "opacityinactiverule": str(FORCE),
        })
    return entries


# ---------------------------------------------------------------- writing, without trampling

def create(cfg, entries: dict[str, str]) -> str:
    """Write a rule that did not exist and put it at the head of the list. Returns its UUID.

    Only ever called with a UUID nobody is using, so writing every key is safe here — and it is
    the *only* place that is true.
    """
    uuid = new_uuid()
    for key, value in entries.items():
        cfg.set(uuid, key, value)
    order = [u for u in (cfg.get("General", "rules", "") or "").split(",") if u]
    _write_order(cfg, [uuid] + order)
    return uuid


def apply_policy(cfg, uuid: str, policy: dict[str, str], owned) -> bool:
    """Put this app's keys into an existing rule and leave everything else alone.

    `owned` is what this app is allowed to touch. A key in `owned` that the new policy does not
    mention is removed — that is how a setting this app used to write stops being written — and
    every key outside `owned` is not read, not written and not reordered.

    Returns True when something actually changed, so a caller can skip a reload it does not need.
    """
    entries = cfg.groups.get(uuid)
    if entries is None:
        return False
    changed = False
    for key in owned:
        if key not in policy and key in entries:
            cfg.delete_key(uuid, key)
            changed = True
    for key, value in policy.items():
        if entries.get(key) != str(value):
            cfg.set(uuid, key, value)
            changed = True
    return changed


def ensure(cfg, description: str, entries: dict[str, str], owned) -> bool:
    """Make sure the rule with this description exists and carries this app's keys.

    Cheap enough to check on every start, which is the point: a rule someone deleted by hand — or
    lost with a restored backup — comes back on its own rather than staying quietly absent. And
    when it is still there, only this app's keys are compared and only they are written, so a
    person's additions to it survive the check.
    """
    uuid = find_described(cfg, description)
    if uuid is None:
        create(cfg, entries)
        return True
    return apply_policy(cfg, uuid, {k: v for k, v in entries.items() if k in owned}, owned)


def release(cfg, uuid: str, owned) -> bool:
    """Take this app's keys out of a rule. Returns True if the rule itself was removed.

    The rule goes only when nothing is left that does anything: no policy key from anyone. A rule
    holding somebody's activity, desktop or opacity stays, minus the part that was this app's.

    Its name is left as it is. Renaming it back would be guessing at what it used to be called,
    and a wrong guess is worse than a name with this app's prefix on a rule it no longer touches.
    """
    entries = cfg.groups.get(uuid)
    if entries is None:
        return False
    for key in owned:
        cfg.delete_key(uuid, key)
    if policies(cfg.groups.get(uuid, {})):
        return False                      # it still does something — somebody else's something
    cfg.delete_group(uuid)
    order = [u for u in (cfg.get("General", "rules", "") or "").split(",") if u and u != uuid]
    _write_order(cfg, order)
    return True


def adopt(cfg, uuid: str, window_class: str) -> tuple[str, str] | None:
    """Put this app's name on a rule it manages. Returns (old, new) when it renamed something.

    The person's own name is kept and merely prefixed — `(A1W1)Telegram` becomes
    `KyprX: (A1W1)Telegram`. Replacing it with the window class, which is what this used to do,
    throws away the only thing in a rule that says *why* it exists. A name the desktop generated
    itself carries no such meaning, so that one is replaced by the class, which is more useful.
    """
    entries = cfg.groups.get(uuid)
    if entries is None:
        return None
    current = entries.get("Description", "")
    if current.startswith(PREFIX):
        return None
    generated = not current or current.startswith("Window settings for ")
    new = PREFIX + (window_class if generated else current)
    cfg.set(uuid, "Description", new)
    return (current, new)


def _write_order(cfg, order: list[str]) -> None:
    cfg.set("General", "rules", ",".join(order))
    cfg.set("General", "count", len(order))
