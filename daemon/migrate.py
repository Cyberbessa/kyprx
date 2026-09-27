"""The one-off passes that bring an install up to date, each run once, gated on the version
stamped in `state.json`: bringing an install made under this app's previous name across (below
version 3), putting KyprX's layout order in place where nobody had chosen one (below 4),
moving the title bar's opacity keys to the names the decoration reads (below 5), moving this
app's own two files out of what became the KyprX folder (below 6), and applying default settings
including Longive theme and 7.5 corner radius (below 7).

The first of them is most of this file.

**The name is a lookup key, not a label.** A rule this app owns is found by
`Description.startswith(rules.PREFIX)`; a window's outline is read back by comparing a preset name
to `klassy.OUTLINE_OFF_PRESET` by string equality. Rename either and nothing raises: the app
simply stops recognising work it did itself, and starts reporting the opposite of what is on
screen. Every entry below exists because some lookup would otherwise miss.

Four of them would fail in ways worth naming, because none of them announces itself:

* **The remembered state.** `seen` is what stops the defaults being applied to a class twice. Lose
  it and the first inventory treats every open window as new and reapplies the theme to all of
  them in one transaction, undoing every per-window choice that differed from it. Losing
  `config.json` at the same time resets `paused`, which is the last thing that could have stopped
  it. This is why a failure to move those directories cancels the rest of the start.
* **The overlay's rule.** `rules.ensure()` only rewrites the keys it owns, and `wmclass` is not
  one of them — so a renamed window class leaves that rule matching nothing for ever. The overlay
  stops being centred, and `policy.AUTO_SKIP` stops recognising it, at which point the daemon
  judges its own frameless window to be an application refusing a server-side decoration.
* **The shortcut.** Up to Plasma 6.6 a combination another component held was refused to whoever
  asked next; from 6.7 both keep it, and the older claim is the one the key runs. The old action
  stays registered, holding the key, and the new registration succeeds and grabs nothing — see `shortcuts.LEGACY_CLAIMS`, which is where the old names are given back.
* **The compositor script.** Its id is its directory name and its `<id>Enabled` key. Leave the old
  ones in place beside the new and the same script loads twice under two ids, reporting every
  window twice. That half is `install.sh`'s, since it is the half that installs.

Each pass is deletable in one commit once no install can still be below the version that gates it
-- all but the cache sweep in `_move_dirs`, which is gated on existence rather than on the version
and goes whenever the directories it sweeps can no longer exist anywhere.
"""

from __future__ import annotations

import json
import os
import shutil

import declared
import defaults
import effects
import klassy
import logs
import rules
import shortcuts
import theme
import writer
import profiles
import snapshot
from kyprd_names import SCRIPT_PLUGIN
from state import CONFIG_PATH, LEGACY_CONFIG_PATH, STATE_PATH, STATE_VERSION

CONFIG_DIR = os.path.expanduser("~/.config/kyprx")
STATE_DIR = os.path.expanduser("~/.local/state/kyprx")

OLD_CONFIG_DIR = os.path.expanduser("~/.config/cybe-kde")
OLD_STATE_DIR = os.path.expanduser("~/.local/state/cybe-kde")
OLD_CACHE_DIR = os.path.expanduser("~/.cache/cybe-kde")

#: A derived cache of a feature this app no longer has: the button icons the interface rendered
#: for its icon-style menu, one set per style, through the decoration's own generator. Nothing
#: builds or reads it any more, so it is swept when found rather than left as a folder nobody
#: can explain.
BUTTON_ICONS_DIR = os.path.expanduser("~/.cache/kyprx/button-icons")

#: What each name used to be. Nothing here spells a *current* name that another module owns:
#: the cheatsheet's class and title are passed in by the daemon, which holds them, and the rest
#: come from `rules` and `klassy`. The one exception is the interface's own window class, which
#: is its desktop file name and belongs to `gui/kyprx.py` — out of reach from here.
OLD_RULE_PREFIX = "CYBE-KDE: "
OLD_CHEATSHEET_RULE = "CYBE-KDE cheatsheet overlay"
OLD_CHEATSHEET_CLASS = "cybe-kde-cheatsheet"
OLD_CHEATSHEET_TITLE = "CYBE-KDE shortcuts"
OLD_OUTLINE_OFF_PRESET = "CYBE-KDE No Outline"
OLD_GUI_CLASS = "cybe-kde"
OLD_CHEATSHEET_ACTION = "CybeKdeCheatsheet"

#: The interface's window class today — `app.setDesktopFileName` in `gui/kyprx.py`.
GUI_CLASS = "kyprx"


def _state_version() -> int:
    """The version stamped in `state.json`, or 0 when there is nothing to read.

    A fresh install answers 0 and runs the pass, which finds nothing and stamps the version. That
    is cheaper than a second way of asking whether this is a new install.
    """
    try:
        with open(STATE_PATH, encoding="utf-8") as fh:
            return int(json.load(fh).get("version", 0))
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        return 0


def _stamp_version(log) -> None:
    if writer.dry_run():
        log(f"would have stamped state.json at version {STATE_VERSION}")
        return
    try:
        with open(STATE_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"seen": [], "refuses_ssd": []}
    data["version"] = STATE_VERSION
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".new"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, STATE_PATH)


def _move_dirs(log) -> bool:
    """Bring the two private directories across, and sweep the caches nothing reads. False means
    the rest of the start must not run.

    Idempotent by existence rather than by version: the version itself lives in one of the files
    being moved, so it cannot be the thing that decides whether to move them. The sweep is gated
    the same way, and for a second reason: it runs before the version gate below, so a cache that
    stops being read after an install was stamped is still swept, without a bump that would run
    the renaming pass again for nothing.
    """
    ok = True
    for old, new, what in ((OLD_STATE_DIR, STATE_DIR, "remembered state"),
                           (OLD_CONFIG_DIR, CONFIG_DIR, "settings")):
        if not os.path.isdir(old) or os.path.exists(new):
            continue
        if writer.dry_run():
            log(f"would have moved the {what} from {old} to {new}")
            continue
        try:
            os.makedirs(os.path.dirname(new), exist_ok=True)
            os.rename(old, new)
            log(f"moved the {what} to {new}")
        except OSError as e:
            log(f"COULD NOT move the {what} from {old} to {new}: {logs.what(e)}", trouble=True)
            ok = False

    # Two derived caches nothing reads any more. A `rmtree` outside a transaction, and that is
    # allowed here for one reason: neither is one of the files `writer` guards, and neither is
    # watched by `scripts/simulate.sh`. Held back in dry run all the same.
    for stale, what in ((OLD_CACHE_DIR, "generated icons under the previous name"),
                        (BUTTON_ICONS_DIR, "button icons the interface no longer draws")):
        if not os.path.isdir(stale):
            continue
        if writer.dry_run():
            log(f"would have deleted the {what} in {stale}")
        else:
            shutil.rmtree(stale, ignore_errors=True)
    return ok


def _rename_seen_class(log, cheatsheet_class: str) -> None:
    """The app's own interface is a window like any other, and it was in `seen` under its old
    class. Left alone it would be a stranger under the new one, and get the defaults applied."""
    try:
        with open(STATE_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return
    seen = data.get("seen") or []
    swaps = {OLD_GUI_CLASS: GUI_CLASS, OLD_CHEATSHEET_CLASS: cheatsheet_class}
    renamed = sorted({swaps.get(c, c) for c in seen})
    if renamed == sorted(seen):
        return
    if writer.dry_run():
        log("would have renamed this app's own window classes in the seen list")
        return
    data["seen"] = renamed
    tmp = STATE_PATH + ".new"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, STATE_PATH)
    log("renamed this app's own window classes in the seen list")


def _rewrite_configs(tx, cheatsheet_class: str, cheatsheet_title: str) -> None:
    """Every old name this app left in somebody else's config file, brought up to date.

    Built to be handed to `writer.run`, so it is rebuilt from scratch if another writer gets there
    first, and writes nothing at all under `--dry-run`.
    """
    # Rules, by Description. Rewritten in place and never through `rules.adopt`, which prefixes
    # rather than replaces: it would turn `CYBE-KDE: firefox` into `KyprX: CYBE-KDE: firefox`.
    for uuid, entries in rules.read(tx.rules):
        description = entries.get("Description", "")
        if description.startswith(OLD_RULE_PREFIX):
            tx.rules.set(uuid, "Description",
                         rules.PREFIX + description[len(OLD_RULE_PREFIX):])
        elif description == OLD_CHEATSHEET_RULE:
            tx.rules.set(uuid, "Description", rules.CHEATSHEET_RULE)
            # `wmclass` is outside the keys that rule owns, so nothing else will ever correct it.
            if entries.get("wmclass") == OLD_CHEATSHEET_CLASS:
                tx.rules.set(uuid, "wmclass", cheatsheet_class)
            if entries.get("title") == OLD_CHEATSHEET_TITLE:
                tx.rules.set(uuid, "title", cheatsheet_title)

    # The decoration's per-window overrides: the preset a window points at, and the pattern that
    # matches this app's own interface window.
    old_pattern = klassy.pattern_for(OLD_GUI_CLASS)
    for group, entries in list(tx.klassy.groups.items()):
        if not group.startswith("Windeco Exception "):
            continue
        if entries.get("ExceptionPreset") == OLD_OUTLINE_OFF_PRESET:
            tx.klassy.set(group, "ExceptionPreset", klassy.OUTLINE_OFF_PRESET)
        if entries.get("ExceptionWindowPropertyPattern") == old_pattern:
            tx.klassy.set(group, "ExceptionWindowPropertyPattern",
                          klassy.pattern_for(GUI_CLASS))

    # The preset itself. The old group is dropped rather than left: it is not dead weight, it is
    # an entry the decoration keeps offering in its own preset list.
    old_group = klassy.PRESET_PREFIX + OLD_OUTLINE_OFF_PRESET
    if old_group in tx.presets.groups:
        klassy.ensure_outline_off_preset(tx.presets)
        tx.presets.delete_group(old_group)

    # The tiler's float list, which is append-only: nothing but this removes an entry.
    floating = (tx.kwin.get(effects.TILING_GROUP, effects.TILING_FLOAT_LIST, "") or "")
    if OLD_CHEATSHEET_CLASS in [v.strip() for v in floating.split(",")]:
        kept = [v.strip() for v in floating.split(",")
                if v.strip() and v.strip() != OLD_CHEATSHEET_CLASS]
        kept.append(cheatsheet_class)
        tx.kwin.set(effects.TILING_GROUP, effects.TILING_FLOAT_LIST, ",".join(dict.fromkeys(kept)))
        tx.reload_tiling = True

    # One reconfigure covers the rule, the override and the preset the override points at — the
    # same signal the rest of the app leans on, and it applies to windows already on screen.
    if tx.rules.dirty() or tx.klassy.dirty() or tx.presets.dirty():
        tx.reload_kwin = True


def _restore_cheatsheet_key(log) -> None:
    """Carry a customised cheatsheet key over to the renamed action.

    The key lives in the registry under the action's id, so a renamed action is a new action with
    nothing bound but its hard-coded default.

    The order of the three steps is the whole of it, and each one is only possible in its slot:
    the old key can be read only while the old action still holds it, the new action cannot be
    given a combination another action is still holding, and the old action stops holding it only
    once its claim is released. The daemon releases the same claims again a moment later — asking
    twice costs nothing, and having it happen here is what makes the middle step exist at all.
    """
    if writer.dry_run():
        log("would have carried the cheatsheet key over to the renamed action")
        return
    try:
        old_key = shortcuts.primary_key(OLD_CHEATSHEET_ACTION)
    except Exception as e:  # noqa: BLE001 — the registry is not worth failing a start over
        log(f"could not read the old cheatsheet key: {logs.what(e)}", trouble=True)
        return
    if not old_key:
        return
    try:
        shortcuts.release_legacy_claims()
        if not shortcuts.primary_key(shortcuts.CHEATSHEET_ACTION):
            log("the renamed cheatsheet action is not registered yet — its default key applies "
                "once the compositor script has run")
            return
        got = shortcuts.set_primary(shortcuts.CHEATSHEET_ACTION, old_key)
        log("carried the cheatsheet key over" if got else
            "the compositor refused the old cheatsheet key — its default applies")
    except Exception as e:  # noqa: BLE001
        log(f"could not carry the cheatsheet key over: {logs.what(e)}", trouble=True)


#: KyprX's own layout order before `defaults.VERSION` 4, as the tiler reads it: Quarter, Monocle,
#: Tile and on to Cascade, every layout in the cycle. Written out here rather than kept in
#: `defaults.py`, because it is not an opinion any more -- it is a fact about what installs made
#: before then may still be wearing, and the only thing that reads it is the pass below.
PREVIOUS_LAYOUT_ORDER = {
    "quarterLayoutOrder": 1, "monocleLayoutOrder": 2, "tileLayoutOrder": 3,
    "threeColumnLayoutOrder": 4, "stackedLayoutOrder": 5, "binaryTreeLayoutOrder": 6,
    "columnsLayoutOrder": 7, "spreadLayoutOrder": 8, "floatingLayoutOrder": 9,
    "stairLayoutOrder": 10, "spiralLayoutOrder": 11, "cascadeLayoutOrder": 12,
}


def new_layout_order(kwin) -> bool:
    """Put KyprX's layout order on a desk still wearing an order nobody chose. True if it wrote.

    **Nobody chose** means one of exactly two orders, compared as the tiler reads them
    (`effects.layout_order`): the tiler's own, which is what a desk has before anything writes a
    number, and KyprX's previous one, which is what *Restore defaults* wrote until the default
    moved. Any other order is somebody's -- one number moved on the Tiling tab is enough -- and is
    left exactly as it is. The owner asked for that in as many words: a new default must not
    silently overwrite an order that was arranged.

    Only the keys that read differently are written, the rule `declared.write_declared` keeps, and
    the order is the one declared in `defaults.SETTINGS` rather than a second copy of it here.
    Takes the config itself rather than a transaction, so `scripts/dry-run.sh` can hand it one
    that exists only in memory.
    """
    now = effects.layout_order(kwin)
    shipped = {key: int(effects.TILING_DEFAULTS[key]) for key in now}
    if now not in (shipped, PREVIOUS_LAYOUT_ORDER):
        return False
    declared = defaults.SETTINGS["tiling"][""]
    wrote = False
    for key, value in now.items():
        wanted = int(declared[key])
        if value != wanted:
            kwin.set(effects.TILING_GROUP, key, str(wanted))
            wrote = True
    return wrote


def _layout_pass(tx) -> None:
    """`new_layout_order`, shaped for `writer.run`. The tiler re-reads itself only when it is
    reloaded, and a tiler that reloads tiles the screen again -- once, here."""
    if new_layout_order(tx.kwin):
        tx.reload_tiling = True


#: The title bar's opacity keys as this app used to spell them, and as the decoration spells them.
#: `defaults.py` declared the state first -- `ActiveTitleBarOpacity` -- and the decoration's
#: schema puts it last, so *Restore defaults* wrote four keys that nothing ever read and the bar
#: stayed at whatever alpha the colour scheme gave it. The note beside the declaration has the
#: measurement.
TITLE_BAR_OPACITY_GROUP = "TitleBarOpacity"
STALE_TITLE_BAR_KEYS = {
    "ActiveTitleBarOpacity": "TitleBarOpacityActive",
    "InactiveTitleBarOpacity": "TitleBarOpacityInactive",
    "OverrideActiveTitleBarOpacity": "OverrideTitleBarOpacityActive",
    "OverrideInactiveTitleBarOpacity": "OverrideTitleBarOpacityInactive",
}


def rename_title_bar_keys(klassy_cfg) -> bool:
    """Carry each stale spelling over to the one the decoration reads. True if it wrote.

    A value under the stale name is what *Restore defaults* meant to write, so it moves across --
    unless the right name already holds a value, which is then somebody's (the decoration's own
    dialog writes that one) and wins. Either way the stale key goes: nothing reads it, and a key
    nothing reads is a key that makes the file lie about what is on screen. Takes the config
    itself rather than a transaction, so `scripts/dry-run.sh` can hand it one that exists only in
    memory.
    """
    wrote = False
    for stale, right in STALE_TITLE_BAR_KEYS.items():
        value = klassy_cfg.get(TITLE_BAR_OPACITY_GROUP, stale)
        if value is None:
            continue
        if klassy_cfg.get(TITLE_BAR_OPACITY_GROUP, right) is None:
            klassy_cfg.set(TITLE_BAR_OPACITY_GROUP, right, value)
        klassy_cfg.delete_key(TITLE_BAR_OPACITY_GROUP, stale)
        wrote = True
    return wrote


def _title_bar_pass(tx) -> None:
    """`rename_title_bar_keys`, shaped for `writer.run`. The opacity is part of the palette the
    decoration builds for a window, so the colour cache is invalidated along with the ordinary
    reconfigure -- the same pair a change to the outline's colour needs."""
    if rename_title_bar_keys(tx.klassy):
        tx.reload_kwin = True
        tx.reload_colours = True


def move_working_copies(log) -> bool:
    """Take this app's own settings and profiles out of `~/.config/kyprx/`, which is now the KyprX
    folder, to the daemon's working copies beside `state.json`. True when there was nothing to do
    or it all went; False leaves the version unstamped, so the next start tries again -- and until
    then `state.Config.load` and `profiles.Profiles` read the old place, so nothing reads as lost.

    **Nothing is lost on any road.** Both files are first copied whole into a folder under
    `snapshots/`, named for when and why. Then each is copied to its new place, read back and
    compared byte for byte, and only then removed from the old one. A working copy already there is
    never written over -- it is newer than the one being moved -- and the old one is still kept in
    that snapshot folder before it goes.

    `profiles.json` is left where it is when the folder already carries a `kyprx.json`: then it is
    the folder's own copy of the profiles, written by a KyprX on another machine or put back from a
    repository, and the folder is what applies it. `config.json` is never a name the folder uses.
    """
    moving = [(os.path.basename(LEGACY_CONFIG_PATH), LEGACY_CONFIG_PATH, CONFIG_PATH)]
    if not os.path.exists(os.path.join(snapshot.FOLDER, "kyprx.json")):
        moving.append((os.path.basename(profiles.LEGACY_PATH), profiles.LEGACY_PATH, profiles.PATH))
    found = {}
    for name, old, _ in moving:
        if os.path.isfile(old):
            try:
                with open(old, "rb") as fh:
                    found[name] = fh.read()
            except OSError as e:
                log(f"COULD NOT read {old} to move it: {logs.what(e)}", trouble=True)
                return False
    if not found:
        return True
    if writer.dry_run():
        log(f"would have moved {', '.join(sorted(found))} from {CONFIG_DIR} to {STATE_DIR}, "
            f"keeping a copy of each under {snapshot.DIRECTORY}")
        return True
    import datetime
    kept = os.path.join(snapshot.DIRECTORY,
                        datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
                        + "_before-the-folder-existed", "folder")
    try:
        os.makedirs(kept, exist_ok=True)
        for name, data in found.items():
            with open(os.path.join(kept, name), "wb") as fh:
                fh.write(data)
        for name, old, new in moving:
            if name not in found:
                continue
            if not os.path.exists(new):
                os.makedirs(os.path.dirname(new), exist_ok=True)
                tmp = new + ".new"
                with open(tmp, "wb") as fh:
                    fh.write(found[name])
                os.replace(tmp, new)
                with open(new, "rb") as fh:
                    if fh.read() != found[name]:
                        log(f"COULD NOT move {old}: the copy at {new} does not read back the same")
                        return False
            os.remove(old)
    except OSError as e:
        log(f"COULD NOT move this app's own files out of {CONFIG_DIR}: "
            f"{logs.what(e)}", trouble=True)
        return False
    log(f"moved {', '.join(sorted(found))} to {STATE_DIR}; the originals are kept in {kept}")
    return True


#: What an install's passes may rewrite, kept whole before they run: the four config files KyprX
#: writes, and its own files beside `state.json`.
KEPT_BEFORE_PASSES = (writer.KLASSYRC, writer.PRESETSRC, writer.KWINRULESRC, writer.KWINRC,
                      CONFIG_PATH, STATE_PATH, profiles.PATH)


def keep_before_passes(log, version: int) -> bool:
    """Before the passes an existing install is due, keep every file they may rewrite, byte for
    byte, under `snapshots/<time>_before-bringing-this-install-up-to-date/files/`. True when that
    was done or there was nothing to keep; False stops the passes, which then run on a later start.

    For an update: a new version whose files are in a new shape brings a pass, and a pass that goes
    wrong on somebody's desk must have something to go back to. A copy of the desk proper cannot be
    taken here -- the daemon's own settings are read after the passes, which is the order they need
    -- so this is the files themselves, as the one kept when the working files moved is; like that
    one, *Go back to a copy…* does not list it, and putting it back is copying the files back. A
    new install (version 0) has nothing of its own to keep.
    """
    if version == 0:
        return True
    present = [p for p in KEPT_BEFORE_PASSES if os.path.isfile(p)]
    if writer.dry_run():
        log(f"would have kept {len(present)} file(s) under {snapshot.DIRECTORY} before bringing "
            f"this install from version {version} up to {STATE_VERSION}")
        return True
    import datetime
    kept = os.path.join(snapshot.DIRECTORY,
                        datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
                        + "_before-bringing-this-install-up-to-date", "files")
    try:
        os.makedirs(kept, exist_ok=True)
        for path in present:
            shutil.copy2(path, os.path.join(kept, os.path.basename(path)))
    except OSError as e:
        log(f"COULD NOT keep a copy before bringing this install up to date, so it is not: "
            f"{logs.what(e)}", trouble=True)
        return False
    log(f"kept {len(present)} file(s) in {kept} before bringing this install from version "
        f"{version} up to {STATE_VERSION}")
    return True


def _bootstrap_pass(tx) -> None:
    """Apply KyprX declared defaults and Longive theme on a fresh install."""
    declared.note_reloads(tx, declared.write_declared(tx, defaults.SETTINGS))
    declared.write_declared_colours(tx, defaults.BUTTON_COLOURS)
    if tx.kwin.get(effects.PLUGINS_GROUP, f"{SCRIPT_PLUGIN}Enabled") is None:
        effects.set_plugin_enabled(tx.kwin, SCRIPT_PLUGIN, True)
        tx.reload_kwin = True
    now = theme.current()
    wanted = dict(defaults.COLOURS)
    p = theme.preset(wanted.get("preset", "")) or theme.default_preset(wanted.get("mode", "dark"))
    if p:
        steps = list(theme.plan(now, wanted, scheme_written=False))
        klassy.settle_look_and_feel(tx.klassy, theme.package_after(now, wanted))
        for description, action, plain in steps:
            tx.session_write(description, action, plain)
    shortcuts.release_spectacle_conflict()


def _v7_upgrade_pass(tx) -> None:
    """Migrate settings for existing installs updating to version 7."""
    for plugin in (SCRIPT_PLUGIN, effects.BLUR_PLUGIN, effects.TILING_PLUGIN, effects.GEOMETRY_PLUGIN):
        key = f"{plugin}Enabled"
        if tx.kwin.get(effects.PLUGINS_GROUP, key) is None:
            effects.set_plugin_enabled(tx.kwin, plugin, True)
            tx.reload_kwin = True
    if tx.klassy.get("Windeco", "WindowCornerRadius") == "2.5":
        tx.klassy.set("Windeco", "WindowCornerRadius", "7.5")
        tx.reload_kwin = True
    if tx.kwin.get(effects.BLUR_GROUP, "CornerRadius") == "2.5":
        tx.kwin.set(effects.BLUR_GROUP, "CornerRadius", "7.5")
        tx.reload_blur = True
    shortcuts.release_spectacle_conflict()


def run(log, cheatsheet_class: str, cheatsheet_title: str) -> bool:
    """Do whatever this install still needs. False means do not touch any window this start.

    Each pass runs when the stamped version is below the one that introduced it, so an install
    that was already brought across under the new name is not walked through that again for a
    pass that arrived later. A fresh install answers 0 and gets both. The version is stamped only
    when every pass that was due went through.
    """
    moved_ok = _move_dirs(log)
    if not moved_ok:
        log("REFUSING to go on: without the remembered state every open window would be treated "
            "as new and have the defaults written over it")
        return False

    version = _state_version()
    if version >= STATE_VERSION:
        return True
    if not keep_before_passes(log, version):
        return True

    if version < 3:
        log("bringing an install made under the previous name up to date")
        _rename_seen_class(log, cheatsheet_class)
        try:
            diff = writer.run(lambda tx: _rewrite_configs(tx, cheatsheet_class, cheatsheet_title))
        except Exception as e:  # noqa: BLE001 — a half-done rename is worse than a retry next start
            log(f"could not rewrite the old names in config: {logs.what(e)}", trouble=True)
            return True
        if diff:
            log(f"would rewrite the old names in config:\n{diff}" if writer.dry_run()
                else "rewrote the old names in config")
        _restore_cheatsheet_key(log)

    if version < 4:
        try:
            diff = writer.run(_layout_pass)
        except Exception as e:  # noqa: BLE001 — the order stays as it was, and says so
            log(f"could not put KyprX's layout order in place: {logs.what(e)}", trouble=True)
            return True
        declared = defaults.SETTINGS["tiling"][""]
        cycle = ", ".join(label for _, key, label in sorted(
            (int(declared[key]), key, label) for key, label in effects.LAYOUTS
            if int(declared[key]) > 0))
        if not diff:
            log("left the layout order as it is: it is already KyprX's, or it is somebody's own")
        elif writer.dry_run():
            log(f"would have put KyprX's layout order in place ({cycle}):\n{diff}")
        else:
            log(f"put KyprX's layout order in place: {cycle}")

    if version < 5:
        try:
            diff = writer.run(_title_bar_pass)
        except Exception as e:  # noqa: BLE001 — the stale names stay, and the next start tries again
            log(f"could not move the title bar's opacity keys to the names the decoration reads: "
                f"{logs.what(e)}", trouble=True)
            return True
        if not diff:
            log("no title bar opacity key under a stale name")
        elif writer.dry_run():
            log(f"would have moved the title bar's opacity keys to the names the decoration "
                f"reads:\n{diff}")
        else:
            log("moved the title bar's opacity keys to the names the decoration reads")

    if version < 6 and not move_working_copies(log):
        return True

    if version < 7:
        try:
            if version == 0:
                diff = writer.run(_bootstrap_pass)
                if diff and writer.dry_run():
                    log(f"would have applied KyprX defaults on fresh install:\n{diff}")
                elif diff:
                    log("applied KyprX defaults on fresh install")
            else:
                diff = writer.run(_v7_upgrade_pass)
                if diff and writer.dry_run():
                    log(f"would have brought settings up to date for version 7:\n{diff}")
                elif diff:
                    log("brought settings up to date for version 7")
        except Exception as e:  # noqa: BLE001
            log(f"could not bring settings up to date for version 7: {logs.what(e)}", trouble=True)
            return True

    _stamp_version(log)
    return True
