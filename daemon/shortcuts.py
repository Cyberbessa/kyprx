"""Global shortcuts, through `org.kde.kglobalaccel`.

Shortcuts are the one thing here that must **not** be edited as a file. The compositor serves the
shortcut registry itself and rewrites the whole thing on its way out, so writing that file while a
session is running produces no error and no effect: the previous state comes back at logout. The
D-Bus interface is the only honest door.

Keys travel as plain integers, the way Qt encodes a key plus its modifiers — `Meta+Shift+F` is
`0x10000000 | 0x02000000 | 0x46`. They are passed through untouched: turning them into something
readable is `QKeySequence`'s job, and that lives on the interface side. The one exception is
`key_text`, a small table of its own for the daemon's log, which has no Qt to ask -- a dry run that
said `would bind [419430418]` told nobody anything.

**On Plasma 6.7 the registry refuses nothing.** Earlier versions dropped a combination another
action already held and handed back an empty slot in its place. From 6.7 on, `setKeys` stores
whatever it is given and only says so in a debug category that is off, so two actions can hold the
same keys -- and when they are pressed, the action registered **first** (the lowest serial, kept in
`~/.local/state/kglobalshortcutsstaterc`) is the one that runs. Read in the kglobalacceld sources
for 6.7 and confirmed on this desk: nothing in the registry says no any more. So a conflict is found
by asking who holds the keys, `holders`, before binding, and a binding is checked by reading back
what was stored.

The three lists below are **fixed on purpose**. The component publishes dozens of actions nobody
binds; what makes a shortcut core is that someone chose it.

**The cheatsheet key is in those lists like everything else**, and that is the whole of what it
took to make it work. Two earlier shapes registered it from this process: a component of this
app's own, and a desktop entry of its own. Both were accepted by the registry and neither was ever
grabbed — the key was bound and pressing it did nothing. What the tiling script does instead is
call `registerShortcut` from inside the compositor, and those keys work. So the cheatsheet does
that too: `kwin-script/contents/code/main.js` registers it, the action lands in the compositor's
own component, and from here it is one more row with no special case anywhere.
"""

from __future__ import annotations

import dbus

SERVICE = "org.kde.kglobalaccel"
PATH = "/kglobalaccel"
IFACE = "org.kde.KGlobalAccel"
COMPONENT_IFACE = "org.kde.kglobalaccel.Component"
#: What the registry says when any key of any action changed.
SHORTCUTS_CHANGED = "yourShortcutsChanged"

#: The component every compositor script's actions belong to. It is also the default everywhere
#: below: an action named without a component is one of the compositor's.
KWIN_COMPONENT = "kwin"

#: The same component, by the path the registry serves it at: what `invoke` calls.
KWIN_COMPONENT_PATH = "/component/kwin"

#: KRunner's, which is a desktop entry rather than a compositor script. It is here because it is
#: the one key outside the compositor that a tiling setup is used with constantly, and a cheatsheet
#: that leaves it out is a cheatsheet somebody has to remember something in spite of.
KRUNNER_COMPONENT = "org.kde.krunner.desktop"

#: KGlobalAccel::NoAutoloading — set the key now and do not let the component's own defaults
#: reload over it. It is the flag the shortcuts settings module uses.
NO_AUTOLOADING = 4

#: The cheatsheet action, registered by the compositor script — see `main.js`. Named here so the
#: list below and the script cannot drift apart.
CHEATSHEET_ACTION = "KyprXCheatsheet"

#: The action that opens this app's own settings window, registered by the same script and for the
#: same reason.
SETTINGS_ACTION = "KyprXSettings"

#: And the wallpaper picker's, same script, same reason.
WALLPAPER_ACTION = "KyprXWallpaper"

#: Claims this app made under earlier names, kept only so their keys can be given back. These
#: spellings are deliberately the old ones — that is the whole point of the list.
#:
#: Not housekeeping. Up to Plasma 6.6 a combination another component still held was refused to
#: whoever asked next; from 6.7 it is accepted by both, and the older claim -- registered first -- is
#: the one the key runs. Either way, leaving these in place is exactly how the new registration
#: fails while looking fine.
#:
#: The first four are two abandoned shapes of the cheatsheet key: a component of this app's own,
#: and a pair of desktop entries. The last two are the app's previous name, and they are the ones
#: that matter on an existing install — the compositor registered them in its own component and
#: they hold `Meta+/` until somebody asks for it back.
LEGACY_CLAIMS = [
    ("cybe-kde", "showCheatsheet"),
    ("cybe-kde.desktop", "Cheatsheet"),
    ("cybe-kde.desktop", "_launch"),
    ("cybe-kde-cheatsheet.desktop", "_launch"),
    (KWIN_COMPONENT, "CybeKdeCheatsheet"),
    (KWIN_COMPONENT, "CybeKdeInventory"),
]


#: The tiling actions with a key bound. Krohnkite's own spelling, typo included:
#: `KrohnkitegrowWidth` really does start its second word in lower case.
#:
#: The two layout keys are last and belong together: everything above them moves a window inside
#: the arrangement, and those two change the arrangement itself -- which is the order in which the
#: Tiling tab's *Layouts* numbers mean anything, since that is the cycle these two walk.
TILING_ACTIONS = [
    "KrohnkiteFocusUp", "KrohnkiteFocusDown", "KrohnkiteFocusLeft", "KrohnkiteFocusRight",
    "KrohnkiteShiftUp", "KrohnkiteShiftDown", "KrohnkiteShiftLeft", "KrohnkiteShiftRight",
    "KrohnkiteGrowHeight", "KrohnkiteShrinkHeight", "KrohnkitegrowWidth", "KrohnkiteShrinkWidth",
    "KrohnkiteToggleFloat",
    "KrohnkiteNextLayout", "KrohnkitePreviousLayout",
]

#: The window-management actions that go with a tiling setup.
WINDOW_ACTIONS = [
    "Window Close", "Window Minimize", "Window Maximize", "Show Desktop",
    "Switch One Desktop to the Left", "Switch One Desktop to the Right",
    "Overview", "ExposeAll", "Walk Through Windows",
]

#: The desktop's own launcher. `_launch` is the generic action name every desktop entry publishes,
#: which is exactly why the component has to travel with it — on its own the name means nothing.
LAUNCHER_ACTIONS = ["_launch"]

#: This app's own, registered by the compositor script.
KYPRX_ACTIONS = [CHEATSHEET_ACTION, SETTINGS_ACTION, WALLPAPER_ACTION]

#: The one the script registers with no key: the daemon invokes it to ask for the window list.
INVENTORY_ACTION = "KyprXInventory"

#: Every action the compositor script registers. The registry keeps an action, and its keys, after
#: the script that registered it is gone -- an inactive entry, and a key nobody else can take --
#: so removing KyprX from a computer unregisters these once the script is unloaded.
SCRIPT_ACTIONS = [INVENTORY_ACTION] + KYPRX_ACTIONS

#: Each group is a column on the cheatsheet, and each row carries the component it belongs to.
GROUPS = [
    ("Tiling", [(KWIN_COMPONENT, a) for a in TILING_ACTIONS]),
    ("Window management", [(KWIN_COMPONENT, a) for a in WINDOW_ACTIONS]
     + [(KRUNNER_COMPONENT, a) for a in LAUNCHER_ACTIONS]),
    ("KyprX", [(KWIN_COMPONENT, a) for a in KYPRX_ACTIONS]),
]


def qualified(component: str, action_id: str) -> str:
    """One string naming an action across components, for the places that need a dictionary key.

    A bare name means the compositor's component. That is not a shortcut taken to save typing: it
    is what keeps every settings file written before this existed readable, without a version gate and
    without a migration.
    """
    return action_id if component == KWIN_COMPONENT else f"{component}/{action_id}"


def unqualified(key: str) -> tuple[str, str]:
    """The component and action a `qualified` string names."""
    component, slash, action = key.partition("/")
    return (component, action) if slash else (KWIN_COMPONENT, key)


# ---------------------------------------------------------------- keys as words

#: Qt's modifier bits, in the order `QKeySequence` prints them -- which is also how the shortcut
#: registry spells them in its own file, `Meta+Alt+Left`.
MODIFIERS = ((0x10000000, "Meta"), (0x04000000, "Ctrl"), (0x08000000, "Alt"),
             (0x02000000, "Shift"))
#: The keypad bit, which says which physical key made the stroke and is not a modifier anybody
#: holds down. Qt keeps it; the name leaves it out, as `QKeySequence` does.
KEYPAD = 0x20000000
KEY_MASK = 0x01FFFFFF

#: The named keys, spelled as `QKeySequence(..., PortableText)` spells them. Everything printable
#: is its own character; F-keys are a range; the rest a key nobody binds prints as its number.
_NAMED = {
    0x01000000: "Esc", 0x01000001: "Tab", 0x01000002: "Backtab", 0x01000003: "Backspace",
    0x01000004: "Return", 0x01000005: "Enter", 0x01000006: "Ins", 0x01000007: "Del",
    0x01000008: "Pause", 0x01000009: "Print", 0x0100000A: "SysReq", 0x0100000B: "Clear",
    0x01000010: "Home", 0x01000011: "End", 0x01000012: "Left", 0x01000013: "Up",
    0x01000014: "Right", 0x01000015: "Down", 0x01000016: "PgUp", 0x01000017: "PgDown",
    0x01000020: "Shift", 0x01000021: "Ctrl", 0x01000022: "Meta", 0x01000023: "Alt",
    0x01000024: "CapsLock", 0x01000025: "NumLock", 0x01000026: "ScrollLock",
    0x01000055: "Menu", 0x01001103: "AltGr", 0x20: "Space",
    0x01000070: "Volume Down", 0x01000071: "Volume Mute", 0x01000072: "Volume Up",
    0x01000080: "Media Play", 0x01000081: "Media Stop", 0x01000082: "Media Previous",
    0x01000083: "Media Next", 0x01000085: "Media Pause", 0x01000086: "Toggle Media Play/Pause",
    0x01000061: "Back", 0x01000062: "Forward", 0x01000064: "Refresh", 0x01000092: "Search",
    0x010000A0: "Launch Mail", 0x010000B2: "Monitor Brightness Up",
    0x010000B3: "Monitor Brightness Down", 0x010000B4: "Keyboard Light On/Off",
    0x010000B5: "Keyboard Brightness Up", 0x010000B6: "Keyboard Brightness Down",
    0x010000B7: "Power Off", 0x010000CB: "Calculator", 0x01000108: "Hibernate",
    0x01000113: "Microphone Mute",
}


def _one_key(combined: int) -> str:
    key = combined & KEY_MASK
    words = [name for bit, name in MODIFIERS if combined & bit]
    if key in _NAMED:
        words.append(_NAMED[key])
    elif 0x01000030 <= key <= 0x01000052:
        words.append(f"F{key - 0x01000030 + 1}")
    elif 0x21 <= key <= 0x7E:
        words.append(chr(key))
    elif key:
        words.append(f"key {key:#x}")
    return "+".join(words) or "nothing"


def key_text(keys: list[int]) -> str:
    """One key sequence as words -- `Meta+Alt+Left` -- or `none` for no key at all.

    For the daemon's log and nothing else. The interface has `QKeySequence` and uses it; this is
    what lets a dry run name the keys it would have bound instead of printing the integers."""
    steps = [int(k) for k in (keys or []) if int(k)]
    return ", ".join(_one_key(k) for k in steps) if steps else "none"


def keys_text(sequences: list[list[int]]) -> str:
    """Every sequence an action carries, as words: `Meta+F / Meta+PgUp`, or `none`."""
    shown = [key_text(s) for s in sequences if s]
    return " / ".join(shown) if shown else "none"


# ---------------------------------------------------------------- keys as words, both ways

#: `words` names a keypad key this way, and `from_words` reads it back. `key_text` leaves the
#: keypad out, which is right for a line in a log and wrong for a file a key is read back from:
#: `Meta+1` and the keypad's `Meta+1` are two keys, and a folder that turned one into the other
#: would rebind it on every apply.
KEYPAD_WORD = "Num"
_BY_NAME = {name.lower(): code for code, name in _NAMED.items()}
_MODIFIER_BITS = {name.lower(): bit for bit, name in MODIFIERS}


def word(combined: int) -> str:
    """One step of a key sequence as words, losing nothing: `Meta+Alt+Left`, `Meta+Num+1`,
    `Ctrl++` for the plus key itself, `key 0x1000137` for a key with no name."""
    key = combined & KEY_MASK
    words = [name for bit, name in MODIFIERS if combined & bit]
    if combined & KEYPAD:
        words.append(KEYPAD_WORD)
    if key in _NAMED:
        words.append(_NAMED[key])
    elif 0x01000030 <= key <= 0x01000052:
        words.append(f"F{key - 0x01000030 + 1}")
    elif 0x21 <= key <= 0x7E:
        words.append(chr(key))
    else:
        words.append(f"key {key:#x}")
    return "+".join(words)


def words(sequence: list[int]):
    """A key sequence as the KyprX folder writes it: one string for a key pressed once -- what
    nearly every shortcut is -- and a list of strings for a sequence of several presses."""
    steps = [word(int(k)) for k in sequence if int(k)]
    return steps[0] if len(steps) == 1 else steps


def from_word(text: str) -> int:
    """The step `word` wrote. Raises ValueError on anything it would not have written, so a
    hand-edited file with a typo is refused by name rather than bound to the wrong key."""
    text = str(text).strip()
    if not text:
        raise ValueError("an empty key")
    if text == "+":
        mods, key = "", "+"
    elif text.endswith("++"):
        mods, key = text[:-2], "+"
    else:
        mods, _, key = text.rpartition("+")
    combined = 0
    for mod in [m for m in mods.split("+") if m]:
        if mod.lower() == KEYPAD_WORD.lower():
            combined |= KEYPAD
        elif mod.lower() in _MODIFIER_BITS:
            combined |= _MODIFIER_BITS[mod.lower()]
        else:
            raise ValueError(f"{mod!r} is not a modifier (Meta, Ctrl, Alt, Shift or Num)")
    lowered = key.lower()
    if lowered in _BY_NAME:
        return combined | _BY_NAME[lowered]
    if lowered.startswith("key "):
        return combined | int(lowered[4:], 16)
    if len(lowered) > 1 and lowered[0] == "f" and lowered[1:].isdigit() and 1 <= int(lowered[1:]) <= 35:
        return combined | (0x01000030 + int(lowered[1:]) - 1)
    if len(key) == 1 and 0x21 <= ord(key.upper()) <= 0x7E:
        return combined | ord(key.upper())
    raise ValueError(f"{key!r} is not a key name")


def from_words(value) -> list[int]:
    """The sequence `words` wrote -- a string for one press, a list for several."""
    steps = [value] if isinstance(value, str) else list(value or [])
    return [from_word(step) for step in steps]


def _iface():
    return dbus.Interface(dbus.SessionBus().get_object(SERVICE, PATH), IFACE)


def invoke(action: str, component_path: str = KWIN_COMPONENT_PATH) -> None:
    """Run an action by its name, as its key would. It returns as soon as the action has fired and
    nothing is answered: how the daemon asks the compositor script for the window list
    (`request_inventory` in `daemon/kyprd_windows.py`). A `dbus.DBusException` is the caller's."""
    component = dbus.SessionBus().get_object(SERVICE, component_path)
    dbus.Interface(component, COMPONENT_IFACE).invokeShortcut(action)


def _component_actions(component: str) -> dict[str, list[str]]:
    """Every action id of a component, keyed by its unique name."""
    raw = _iface().allActionsForComponent([component, "", "", ""])
    out = {}
    for action in raw:
        ident = [str(x) for x in action]
        if len(ident) >= 2:
            out[ident[1]] = ident
    return out


def _sequences(iface, ident: list[str]) -> list[list[int]]:
    """Every key sequence bound to an action, in a fixed order.

    The signature is `a(ai)`: an array of one-member structs, each holding the steps of one
    sequence. Unused steps come back as zeros. Reading **all** of them matters — two of the
    window actions carry a second binding, and writing back only the first would silently drop it.

    **Sorted**, and that is a correction. From Plasma 6.7 the registry keeps an action's keys as
    an unordered set and hands them back in its hash order, which a restart of the compositor can
    change. The interface calls the first one the action's key -- the one Edit replaces and Remove
    takes away -- so an unsorted list made that "first" a coin toss on the actions carrying two.
    Replacing and removing now go by value as well (`rebind`), so the order only decides which one
    is shown first; sorted, it at least shows the same one every time.
    """
    try:
        raw = iface.shortcutKeys(ident)
    except dbus.DBusException:
        return []
    out = []
    for seq in raw:
        steps = [int(k) for k in seq[0] if k]
        if steps:
            out.append(steps)
    return sorted(out)


def bindings(chosen: dict | None = None) -> list[dict]:
    """The fixed lists, with friendly names and every key each action has.

    `chosen` maps a `qualified` action to the one key sequence that should appear on the
    cheatsheet, for the actions that carry more than one. It arrives as a whole sequence rather
    than as a position in the list, because a position is only meaningful until the desktop
    reorders or drops one — and KRunner really does carry three here.

    The chosen sequence comes back as `show`, **beside** `keys` and never reordering it.
    `set_primary` and the interface's edit both mean "sequence zero" literally, so moving the
    choice to the front would rebind a key nobody asked to rebind.
    """
    iface = _iface()
    chosen = chosen or {}
    known: dict[str, dict[str, list[str]]] = {}
    out = []
    for group, actions in GROUPS:
        for component, action in actions:
            if component not in known:
                known[component] = _component_actions(component)
            ident = known[component].get(action)
            if ident is None:
                continue
            keys = _sequences(iface, ident)
            want = chosen.get(qualified(component, action))
            # Falls back to the first without touching what was stored. A key can be momentarily
            # unbound — while somebody is editing it, say — and throwing the choice away over that
            # would mean the cheatsheet quietly forgetting a decision.
            show = want if want in keys else (keys[0] if keys else [])
            out.append({
                "group": group,
                "component": component,
                "id": action,
                "key": qualified(component, action),
                "name": ident[3] if len(ident) > 3 else action,
                "keys": keys,
                "show": show,
            })
    return out


def primary_key(action_id: str, component: str = KWIN_COMPONENT) -> list[int]:
    """The action's first key sequence, or empty if it has none or does not exist.

    Unlike `bindings()` this asks about one action by id, whatever list it is or is not in — which
    is what makes it usable on an action being retired.
    """
    ident = _component_actions(component).get(action_id)
    if ident is None:
        return []
    sequences = _sequences(_iface(), ident)
    return sequences[0] if sequences else []


def exists(action_id: str, component: str = KWIN_COMPONENT) -> bool:
    """Is this action registered at all?

    Asked about the compositor script's own actions, this answers whether the script has been
    loaded since the action was added to it. A script only re-reads itself when it is unloaded and
    loaded again -- not when its `Enabled` key is flipped, measured in `daemon/reload.py` -- so an
    action added to `main.js` does not exist until that happens.
    """
    try:
        return action_id in _component_actions(component)
    except dbus.DBusException:
        return False


class Refused(Exception):
    """The registry stored something other than what was asked. The message says what, in words."""


def ident_of(action_id: str, component: str = KWIN_COMPONENT) -> list[str]:
    """The registry's own id for an action: component, action and both friendly names."""
    ident = _component_actions(component).get(action_id)
    if ident is None:
        raise KeyError(action_id)
    return ident


def keys_of(action_id: str, component: str = KWIN_COMPONENT) -> list[list[int]]:
    """Every key sequence an action holds now, sorted. A read."""
    return _sequences(_iface(), ident_of(action_id, component))


def holders(sequence: list[int], exclude: tuple[str, str] | None = None) -> list[dict]:
    """Every action that holds this key sequence now, whoever registered it. A read.

    The registry's own answer to "who has this key", which is the question KDE's shortcut
    settings ask before binding. On 6.7 nothing else will ask it: the registry stores a key two
    actions share without a word, and the one registered first is the one that runs.

    The shapes are the registry's, read by introspection and measured on this desk: the argument
    is one sequence, `(ai)`, and the match type wrapped as `(i)` -- 0 is "equal" -- and the answer
    is one `(ssssssaiai)` per holder: its action, its name, its component and that component's
    name, then the context twice, then keys. Meta+Alt+Right answered KrohnkiteFocusRight, Meta+F
    answered Window Maximize, and Meta+Alt+Left answered nothing.

    `exclude` is `(component, action)` of the action being bound: holding its own key is not a
    conflict. Sorted, so that the same desk always answers in the same words.
    """
    steps = [int(k) for k in (sequence or []) if int(k)]
    if not steps:
        return []
    key = dbus.Struct((dbus.Array([dbus.Int32(k) for k in steps], signature="i"),),
                      signature="ai")
    raw = _iface().globalShortcutsByKey(key, dbus.Struct((dbus.Int32(0),), signature="i"))
    out = []
    for info in raw:
        action, name, component, component_name = (str(info[i]) for i in range(4))
        if exclude is not None and (component, action) == tuple(exclude):
            continue
        out.append({"component": component, "id": action, "name": name or action,
                    "component_name": component_name or component})
    return sorted(out, key=lambda h: (h["component"], h["id"]))


def set_primary(action_id: str, keys: list[int],
                component: str = KWIN_COMPONENT) -> list[list[int]]:
    """Replace an action's first key sequence, keeping any others it has.

    What a settings file being imported uses: it carries one sequence per action and means "this is
    the action's key". Returns what the registry stored. On 6.7 that is whatever was asked --
    nothing is refused any more -- and on earlier versions a combination already taken elsewhere
    came back as an empty slot, which is dropped here.
    """
    iface = _iface()
    ident = ident_of(action_id, component)
    existing = _sequences(iface, ident)
    wanted = ([keys] if keys else []) + existing[1:]
    return _write(iface, ident, wanted)


def set_keys(action_id: str, sequences: list[list[int]],
             component: str = KWIN_COMPONENT) -> list[list[int]]:
    """Make an action hold exactly these key sequences, and return what the registry stored.

    What putting a copy of the desk back uses: the copy says every key the action had, and going
    back means all of them, not the first. Whoever else holds one of them now is the caller's to
    ask first -- see `holders` -- because from Plasma 6.7 nothing here would say no.
    """
    wanted = sorted([int(k) for k in seq if int(k)] for seq in sequences if seq)
    return sorted(_write(_iface(), ident_of(action_id, component), wanted))


def rebind(action_id: str, old: list[int], new: list[int],
           component: str = KWIN_COMPONENT) -> list[list[int]]:
    """Put `new` where `old` was, and leave every other key the action has exactly as it is.

    **By value, not by position.** The interface names the key it is replacing -- the one it shows
    first -- and that is the one replaced, whatever order the registry hands its keys back in (see
    `_sequences`). An empty `old` adds `new`; an empty `new` takes `old` away, which is *Remove*.

    **And checked.** What the registry stored is compared with what was asked, and a difference
    raises `Refused` with the difference in words. It used to be enough that the answer was not
    empty -- which it never is on an action with a second key -- so "ok" came back for a key that
    had not gone in.
    """
    old = [int(k) for k in (old or []) if int(k)]
    new = [int(k) for k in (new or []) if int(k)]
    iface = _iface()
    ident = ident_of(action_id, component)
    existing = _sequences(iface, ident)
    wanted = [s for s in existing if s != old]
    if new and new not in wanted:
        wanted.append(new)
    got = sorted(_write(iface, ident, wanted))
    if new and new not in got:
        raise Refused(f"the desktop did not keep {key_text(new)} for {ident[3] or action_id}")
    if old and old != new and old in got:
        raise Refused(f"the desktop kept {key_text(old)} on {ident[3] or action_id}")
    return got


def take_from(holder: dict, sequence: list[int]) -> list[list[int]]:
    """Take one key sequence away from another action. Returns the keys it had before.

    Through `setForeignShortcutKeys`, which is what KDE's own shortcut settings do to another
    application's action: the same stored change as `setShortcutKeys` with no autoloading, and a
    signal to the program that owns the action, so its own copy of the key follows rather than
    going stale. It answers nothing, so what was stored is read back.
    """
    sequence = [int(k) for k in sequence if int(k)]
    iface = _iface()
    ident = ident_of(holder["id"], holder["component"])
    before = _sequences(iface, ident)
    iface.setForeignShortcutKeys(ident, _payload([s for s in before if s != sequence]),
                                 signature="asa(ai)")
    if sequence in _sequences(iface, ident):
        raise Refused(f"{holder.get('name') or holder['id']} kept {key_text(sequence)}")
    return before


def give_back(holder: dict, keys: list[list[int]]) -> None:
    """Put an action's keys back as they were, after a take-over whose second half failed."""
    iface = _iface()
    iface.setForeignShortcutKeys(ident_of(holder["id"], holder["component"]), _payload(keys),
                                 signature="asa(ai)")


def unblock() -> None:
    """Lift the suspension of every global shortcut, whoever asked for it. See
    `watch_interface` in `daemon/kyprd_shortcuts.py` for when, and for the one thing it can do that
    nobody wants."""
    _iface().blockGlobalShortcuts(False)


def _payload(sequences: list[list[int]]):
    return dbus.Array(
        [dbus.Struct((dbus.Array([dbus.Int32(k) for k in seq], signature="i"),), signature="ai")
         for seq in sequences],
        signature="(ai)")


def _write(iface, ident: list[str], sequences: list[list[int]]) -> list[list[int]]:
    """Store these keys on the action and hand back what the registry says it stored.

    An empty slot in the answer is what versions before 6.7 put where they refused a key; it is
    dropped, so a refusal reads as the key missing rather than as an empty key being present.
    """
    got = iface.setShortcutKeys(ident, _payload(sequences), dbus.UInt32(NO_AUTOLOADING),
                                signature="asa(ai)u")
    return [steps for steps in ([int(k) for k in s[0] if k] for s in got) if steps]


# ---------------------------------------------------------------- giving old claims back

def legacy_claims_held() -> list[tuple[str, str]]:
    """The old claims that are still registered, for a dry run to name. A read.

    Releasing them is done blind on every start, which costs six calls and nothing else; saying
    so is not blind, and a dry run that announced a release on every start whether or not there
    was anything left to release was saying something untrue.
    """
    held = []
    for component, action in LEGACY_CLAIMS:
        try:
            if action in _component_actions(component):
                held.append((component, action))
        except dbus.DBusException:
            continue
    return held


def script_actions_held() -> list[str]:
    """The compositor script's actions the registry holds, for a dry run to name. A read."""
    try:
        held = _component_actions(KWIN_COMPONENT)
    except dbus.DBusException:
        return []
    return [action for action in SCRIPT_ACTIONS if action in held]


def unregister_script_actions() -> list[str]:
    """Take the compositor script's actions out of the registry, keys and all. The ones that were
    there and went, in order."""
    iface = _iface()
    gone = []
    for action in SCRIPT_ACTIONS:
        try:
            if iface.unregister(KWIN_COMPONENT, action):
                gone.append(action)
        except dbus.DBusException:
            continue
    return gone


def release_legacy_claims() -> None:
    """Give back the keys the earlier shapes of this shortcut were holding.

    Without this the new registration finds the combination taken by something that does nothing
    with it — which is exactly how the first two attempts failed.
    """
    iface = _iface()
    for component, action in LEGACY_CLAIMS:
        try:
            iface.unregister(component, action)
        except dbus.DBusException:
            pass
