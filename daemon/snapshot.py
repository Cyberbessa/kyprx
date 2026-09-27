"""A copy of everything this app writes, taken before anything big, and put back exactly.

*Restore defaults*, taking KyprX off the desk, applying a folder that arrived, and going back to
an earlier copy all write a great deal at once -- the decoration, every window's rule, the colours.
Each of them first keeps a copy of the desk as it stood, and *Go back* puts that copy back. What
this module guarantees is the word **exactly**: going back is not "apply the old settings on top
of the new ones", it is the files as they were, for the part of them this app writes.

**Raw, not described.** A copy is the groups and keys of the four config files as they are on
disk, not this app's reading of them. A reading is what the KyprX folder carries -- one fact per
window, readable, portable -- and a reading has to be applied through the same logic that decides
where a rule goes and whether a window needs one; putting that back cannot be exact, because the
logic is making choices. The raw groups make no choice, so they come back byte for byte.

**Which part is this app's**, file by file, and the lines are drawn where the rest of the app
already draws them:

* `klassyrc` -- every group but `[Global]`, which is the decoration's bookkeeping about this
  machine (the settings file has always left it out for that reason). The whole file is otherwise
  what the Appearance tab and the per-window overrides write.
* `windecopresetsrc` -- the preset groups. Every one in the copy comes back as it was; one that
  appeared since is removed only if it is this app's own, because the decoration re-imports its
  bundled presets on an upgrade and records that in `[Global]`, and a bundled preset removed here
  would never come back.
* `kwinrc` -- the five groups this app has controls in, whole, and the three plugin switches it
  turns on. Nothing else: that file belongs to the whole desktop.
* `kwinrulesrc` -- **a rule is put back when it is this app's in the copy or now**, and otherwise
  left exactly as it is. That one sentence covers every case that matters: a rule this app made
  since the copy goes; one it made that somebody deleted comes back; a rule of somebody else's that
  this app adopted since (renamed and given a key of its own) goes back to how it was; and a rule
  somebody wrote in the desktop's own dialog after the copy was taken is not this app's, then or
  now, and stays.

The rest of a copy is not in a config file: this app's own settings, profiles and memory of
windows, the colours, the keys of the fixed shortcut list, and the wallpaper. Those are put back by
the daemon, through the same doors that write them normally -- see `restore_desk` in
`daemon/kyprd_copies.py`.

**Where copies live** is the KyprX folder's `snapshots/`, one directory each, named by when and
why, so a copy can be read, copied elsewhere or deleted by hand. The twenty newest are kept, plus
any copy marked as one never to lose (the one taken before KyprX is taken off the desk). In dry
run nothing is written: the copy is kept in the daemon's memory for its lifetime, like every other
change a dry run makes, so *Go back* can still be tried there.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil

import kconfig
import klassy

#: Bumped when the shape of a copy changes. A copy of a later shape is refused rather than half
#: read: putting back half a desk is exactly what a copy exists to prevent.
FORMAT = 1

#: The KyprX folder. `KYPRX_FOLDER`, when set in the environment of the process that imports this,
#: puts the folder -- and the copies of the desk in its `snapshots/` -- somewhere else. Nothing in
#: this repository sets it; `folder.BASE` stays where it is either way.
FOLDER = os.environ.get("KYPRX_FOLDER") or os.path.expanduser("~/.config/kyprx")
DIRECTORY = os.path.join(FOLDER, "snapshots")
FILE = "desk.json"

#: How many copies are kept. A copy is taken before an action that writes a lot, which is a few a
#: week at most, so twenty is weeks of going back -- and a copy is a few dozen kilobytes.
KEEP = 20

#: The decoration's own bookkeeping about this install. Never carried, never put back.
KLASSY_SKIP = frozenset({"Global"})

#: The compositor's groups this app has controls in. Named by the daemon, which owns the names --
#: see `configure`.
KWIN_GROUPS: tuple[str, ...] = ()
PLUGIN_KEYS: tuple[str, ...] = ()
PLUGINS_GROUP = "Plugins"

#: The rules this app calls its own: `rules.PREFIX` (`KyprX: `) and the two overlays' rules, whose
#: names start with the app's name without the colon on purpose (see `rules.find_owned`).
OWN_RULE = "KyprX"


def configure(kwin_groups, plugin_keys) -> None:
    """Tell this module which compositor groups and plugin switches are this app's. Called once by
    the daemon, which already names them for its own use; two lists of the same names would be two
    lists to keep in step."""
    global KWIN_GROUPS, PLUGIN_KEYS
    KWIN_GROUPS = tuple(kwin_groups)
    PLUGIN_KEYS = tuple(plugin_keys)


# ---------------------------------------------------------------- values in and out of JSON

def _plain(entries: dict) -> dict:
    """A group as JSON can hold it. KConfig's `[$d]` marker -- a key with no value -- is `null`."""
    return {k: (None if v is kconfig.NO_VALUE else str(v)) for k, v in entries.items()}


def _raw(entries: dict) -> dict:
    return {str(k): (kconfig.NO_VALUE if v is None else str(v)) for k, v in entries.items()}


def _groups(cfg, keep) -> dict:
    return {g: _plain(e) for g, e in cfg.groups.items() if keep(g)}


def ours(entries: dict) -> bool:
    return str(entries.get("Description", "")).startswith(OWN_RULE)


# ---------------------------------------------------------------- taking a copy

def capture_files(tx) -> dict:
    """The part of the four config files this app writes, raw. A read."""
    kwin = tx.kwin
    order = [u for u in (tx.rules.get("General", "rules", "") or "").split(",") if u]
    return {
        "klassyrc": _groups(tx.klassy, lambda g: g not in KLASSY_SKIP),
        "windecopresetsrc": _groups(tx.presets, lambda g: g.startswith(klassy.PRESET_PREFIX)),
        "kwinrc": _groups(kwin, lambda g: g in KWIN_GROUPS),
        "plugins": {k: kwin.get(PLUGINS_GROUP, k) for k in PLUGIN_KEYS
                    if kwin.get(PLUGINS_GROUP, k) is not None
                    and kwin.get(PLUGINS_GROUP, k) is not kconfig.NO_VALUE},
        "kwinrulesrc": {"order": order,
                        "rules": {u: _plain(tx.rules.groups[u]) for u in order
                                  if u in tx.rules.groups}},
    }


# ---------------------------------------------------------------- putting it back

def _set_group(cfg, group: str, entries: dict) -> bool:
    """Make one group exactly this. True if it changed."""
    wanted = _raw(entries)
    if cfg.groups.get(group) == wanted:
        return False
    cfg.groups[group] = wanted
    return True


def restore_files(tx, files: dict, colour_groups=frozenset()) -> list[str]:
    """Put the copied part of the four files back, exactly, into a transaction somebody else
    commits. Returns what moved, as short phrases, and sets the reloads the change needs.

    `colour_groups` are the decoration's groups kept in the colour cache the ordinary reconfigure
    does not touch -- `declared.COLOUR_CACHED_GROUPS`, with the measurement beside it.
    """
    moved: list[str] = []

    # The decoration: every group but its bookkeeping, both ways.
    cfg = tx.klassy
    wanted = files.get("klassyrc") or {}
    touched: set[str] = set()
    for group in [g for g in cfg.groups if g not in KLASSY_SKIP and g not in wanted]:
        cfg.delete_group(group)
        touched.add(group)
    for group, entries in wanted.items():
        if group not in KLASSY_SKIP and _set_group(cfg, group, entries):
            touched.add(group)
    if touched:
        moved.append("the decoration's settings")
        tx.reload_kwin = True
        if touched & set(colour_groups):
            tx.reload_colours = True

    # The decoration's presets: the copy's back as they were, and only this app's own removed.
    cfg = tx.presets
    wanted = files.get("windecopresetsrc") or {}
    own = klassy.PRESET_PREFIX + klassy.OUTLINE_OFF_PRESET
    changed = False
    if own in cfg.groups and own not in wanted:
        cfg.delete_group(own)
        changed = True
    for group, entries in wanted.items():
        if group.startswith(klassy.PRESET_PREFIX) and _set_group(cfg, group, entries):
            changed = True
    if changed:
        moved.append("the decoration's presets")
        tx.reload_kwin = True

    # The compositor: this app's groups whole, and its three plugin switches.
    cfg = tx.kwin
    wanted = files.get("kwinrc") or {}
    reloads: set[str] = set()
    for group in KWIN_GROUPS:
        if group in wanted:
            if _set_group(cfg, group, wanted[group]):
                reloads.add(group)
        elif group in cfg.groups:
            cfg.delete_group(group)
            reloads.add(group)
    switches = files.get("plugins") or {}
    for key in PLUGIN_KEYS:
        now = cfg.get(PLUGINS_GROUP, key)
        if key in switches:
            if now != str(switches[key]):
                cfg.set(PLUGINS_GROUP, key, str(switches[key]))
                reloads.add(PLUGINS_GROUP)
        elif now is not None:
            cfg.delete_key(PLUGINS_GROUP, key)
            reloads.add(PLUGINS_GROUP)
    if reloads:
        moved.append("the window manager's settings")
        tx.reload_kwin = True
        if any("blur" in g for g in reloads) or PLUGINS_GROUP in reloads:
            tx.reload_blur = True
        if any("krohnkite" in g for g in reloads) or PLUGINS_GROUP in reloads:
            tx.reload_tiling = True

    # The window rules: this app's in the copy or now, exactly; everybody else's, untouched.
    if _restore_rules(tx.rules, files.get("kwinrulesrc") or {}):
        moved.append("the window rules")
        tx.reload_kwin = True
    return moved


def _restore_rules(cfg, copied: dict) -> bool:
    copied_order = [str(u) for u in copied.get("order") or []]
    copied_rules = {str(u): e for u, e in (copied.get("rules") or {}).items()}
    now_order = [u for u in (cfg.get("General", "rules", "") or "").split(",") if u]
    changed = False
    keep: set[str] = set()
    for uuid in set(copied_rules) | set(now_order):
        was = copied_rules.get(uuid)
        now = cfg.groups.get(uuid) if uuid in now_order else None
        if was is not None and (ours(was) or (now is not None and ours(now))):
            changed = _set_group(cfg, uuid, was) or changed
            keep.add(uuid)
        elif now is not None and ours(now):
            cfg.delete_group(uuid)
            changed = True
        elif now is not None:
            keep.add(uuid)
    order = ([u for u in copied_order if u in keep]
             + [u for u in now_order if u in keep and u not in copied_order])
    if order != now_order:
        cfg.set("General", "rules", ",".join(order))
        cfg.set("General", "count", len(order))
        changed = True
    return changed


# ---------------------------------------------------------------- where copies are kept

#: Copies taken in a dry run, kept for the daemon's lifetime and never written. See the module note.
_IN_MEMORY: dict[str, dict] = {}


def _slug(why: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", why.lower()).strip("-")[:48] or "copy"


def save(desk: dict, why: str, *, pinned: bool = False, dry_run: bool = False,
         extra_files: dict | None = None) -> str:
    """Keep a copy of the desk. Returns its name.

    `extra_files` are files to keep beside it, by name -- a folder that arrived, say, kept whole
    before anything replaces it. Written first and the desk last, so a directory holding a
    `desk.json` is always a complete copy.
    """
    now = datetime.datetime.now()
    stamp = now.strftime("%Y-%m-%d_%H%M%S")
    name = f"{stamp}_{_slug(why)}"
    existing = set(_IN_MEMORY) | (set(os.listdir(DIRECTORY)) if os.path.isdir(DIRECTORY) else set())
    base, n = name, 2
    while name in existing:
        name, n = f"{base}-{n}", n + 1
    record = dict(desk, meta={"format": FORMAT, "why": why, "when": now.isoformat(timespec="seconds"),
                              "pinned": pinned})
    if dry_run:
        _IN_MEMORY[name] = record
        return name
    path = os.path.join(DIRECTORY, name)
    os.makedirs(path, exist_ok=True)
    for file_name, text in (extra_files or {}).items():
        target = os.path.join(path, "folder", file_name)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(text)
    tmp = os.path.join(path, FILE + ".new")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, os.path.join(path, FILE))
    prune()
    return name


def load(name: str) -> dict | None:
    """A copy by name, or None when there is none that can be read. A copy of a later shape reads
    as None too, with the reason in `why_not`."""
    if name in _IN_MEMORY:
        return _IN_MEMORY[name]
    if not name or "/" in name or name.startswith("."):
        return None
    try:
        with open(os.path.join(DIRECTORY, name, FILE), encoding="utf-8") as fh:
            found = json.load(fh)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return found if isinstance(found, dict) else None


def why_not(desk: dict | None) -> str:
    """Why a copy cannot be put back, or "" when it can."""
    if not isinstance(desk, dict):
        return "that copy is gone, or cannot be read"
    try:
        shape = int((desk.get("meta") or {}).get("format", 0))
    except (TypeError, ValueError):
        shape = 0
    if shape > FORMAT:
        return "that copy was taken by a newer KyprX, and this one cannot put it back whole"
    if shape < 1:
        return "that copy does not say what shape it is, so it is not put back"
    return ""


def listing() -> list[dict]:
    """Every copy, newest first: name, when, why, pinned, and whether it lives only in memory."""
    out = []
    names = set(os.listdir(DIRECTORY)) if os.path.isdir(DIRECTORY) else set()
    for name in sorted(names | set(_IN_MEMORY), reverse=True):
        desk = load(name)
        meta = (desk or {}).get("meta") or {}
        if not meta:
            continue
        out.append({"name": name, "when": str(meta.get("when", "")), "why": str(meta.get("why", "")),
                    "pinned": bool(meta.get("pinned")), "in_memory": name in _IN_MEMORY,
                    "trouble": why_not(desk)})
    return out


def prune() -> list[str]:
    """Remove the oldest copies beyond `KEEP`, never a pinned one. Returns what went."""
    kept = [c for c in listing() if not c["in_memory"]]
    unpinned = [c for c in kept if not c["pinned"]]
    gone = []
    for copy in unpinned[KEEP:]:
        shutil.rmtree(os.path.join(DIRECTORY, copy["name"]), ignore_errors=True)
        gone.append(copy["name"])
    return gone
