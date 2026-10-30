"""The KyprX folder: `~/.config/kyprx/`, the whole setup as a handful of readable files.

This is the dotfiles half of the app. Everything KyprX controls on this desk is described here, one
file per part, in JSON with its keys in order and no dates inside, so a `git diff` of the folder is
the change and nothing else. Copy the folder to another machine, or put it back over a clean
install, and the daemon applies it.

**The folder is a description, and the desk is where it takes effect.** The daemon works from its
own copies (`~/.local/state/kyprx/`) and from the desktop's config files, and it writes the folder
itself a few seconds after anything changes -- a change made here, or one made in the decoration's
own dialog, which it notices by watching the files. So the folder is never the thing being read to
decide what a window looks like; it is what somebody reads, versions, carries elsewhere and edits.

**Which side a change came from** is the one hard question, and it is answered by remembering the
last moment the two agreed: the folder's files as they were then, and the desk's description as it
was then (`BASE`). Against that, a part whose file moved came from outside -- a copy, a `git pull`,
an edit -- and a part whose description moved came from the desk. Only what moved travels, in
either direction:

* the desk's side is written into the folder part by part, and only the parts the desk changed, so
  a part this machine could not apply (a wallpaper file that is not here) is never sent back out
  by an unrelated change -- two machines sharing a folder would otherwise take turns reapplying it;
* the folder's side is merged key by key with what the desk has now, three ways (`merge`): a key
  the folder changed wins, a key only the desk changed stays, and a key both changed goes the
  folder's way and is named in what the daemon says. The tiling's zone layouts and arrangements
  are one value, never merged inside (`ATOMIC`): whichever side changed them brings the whole of
  them, and the same ones written in the other version are no change (`tiling.alike`).

With nothing remembered -- a new machine with a copied folder, or the memory deleted -- the folder
is applied whole. That is what restoring over a clean install means.

**What is left out, and why.** Facts about this machine rather than about the setup: which windows
it has met, which applications refuse a server-side decoration, the decoration's bundled presets
(only a preset some override points at travels), whether new windows are being adjusted (*Adjust
new windows*, `paused`), and which screen's wallpaper the colour comes from (`colour_screen`),
whose name is this machine's. Carrying them would have two machines
with one folder correcting each other for ever. A window at the defaults is not listed either: what
is not written is the default, so a new window appearing does not change a file.

**Files are text somebody may have written.** Nothing here is applied until every file reads; a
file that does not is named with its line, and never written over. A folder written by a newer
KyprX is left alone entirely. And nothing is applied while git is in the middle of something in the
repository around the folder, or while the files are still moving: a checkout or a copy is applied
when it has finished, not half-way.
"""

from __future__ import annotations

import json
import os

import snapshot
import tiling
import writer

#: Bumped when a file changes shape. `MIGRATIONS` takes an older folder forward one step at a time;
#: a newer one is refused, because applying half of what a later version meant is worse than
#: applying nothing.
#:
#: The zone layouts and arrangements in `tiling.json` coming in a second version is not a new
#: shape, because the value says its own version. A KyprX that reads version 2 reads version 1 for
#: good (`daemon/tiling.py`), and one that reads only version 1 refuses a version-2 value for its
#: version alone, saying a newer KyprX wrote it -- one problem, so nothing of the folder is applied
#: there, as with a folder of a newer shape. A desk keeps version 1 until its zone layouts or
#: arrangements are edited, and so does the folder it writes, which every KyprX reads: bumping
#: this would have the older ones refuse that folder too, for nothing in it they cannot read.
FORMAT = 1

#: The folder itself -- the same place the copies of the desk live under.
PATH = snapshot.FOLDER
MANIFEST = "kyprx.json"

#: Each part of the setup, and the file it lives in. `tiling` is KyprX's own engine, a file of its
#: own rather than a part of `kwin.json`: its group is this app's rather than the compositor's, and
#: its arrangements are written out as what they are instead of one long line. A file a folder of
#: this shape did not have before is not a new shape: an older KyprX reads every file it knows and
#: none it does not, and a folder without it is a part that is simply absent -- see `parse`.
AREAS = ("settings", "profiles", "windows", "decoration", "kwin", "tiling", "shortcuts",
         "colours", "wallpaper")
FILES = {area: f"{area}.json" for area in AREAS}

#: What the daemon remembers about the last moment folder and desk agreed. Machine-local on
#: purpose: it is a fact about this desk, not part of the setup.
BASE = os.path.join(os.path.expanduser("~/.local/state/kyprx"), "folder-base.json")

#: Written whenever absent, and never overwritten: a file there, edited or not, is the owner's.
#: One that is deleted is written again by the next pass that brings the folder into step
#: (`ensure_extras`, called from `FolderPart._folder_mirror`).
IGNORES = ("# Copies of the desk KyprX keeps before a big change. Local; not part of the setup.\n"
           "snapshots/\n"
           "# A file half written: KyprX writes each file beside itself and then moves it into place.\n"
           "*.new\n")
STIGNORE = ("// Copies of the desk KyprX keeps before a big change. Local; not part of the setup.\n"
            "snapshots\n"
            "// A file half written: KyprX writes each file beside itself and then moves it into place.\n"
            "*.new\n")
README = """# The KyprX folder

Everything KyprX controls on this desk, one file per part. KyprX writes these files itself a few
seconds after anything changes, so they are always the desk as it is.

- `settings.json` -- KyprX's own settings: notifications, colour from the wallpaper, the opacity
  of see-through windows, what a new window gets, which key the cheatsheet shows.
- `profiles.json` -- the profiles made on the Appearance tab.
- `windows.json` -- the Windows tab: every window that differs from what a new window gets.
- `decoration.json` -- the window decoration's (Klassy's) settings, and its per-window settings
  that are not columns on the Windows tab.
- `kwin.json` -- focus, borders, the blur and the window animation, and whether those two are
  switched on.
- `tiling.json` -- the tiling: whether it is on and tiles windows as they open, whether names show
  on screen, where a new window goes and what it does when the arrangement is full, where a new
  desktop goes, the gaps, the zone layouts and the arrangements, and the windows that float or are
  never tiled. A window on the Windows tab says whether it floats in `windows.json` instead.
- `shortcuts.json` -- the keys of the actions on the Shortcuts tab.
- `colours.json` -- the mode, the colour preset, a colour of your own and how far it soaks in.
- `wallpaper.json` -- the wallpaper of every activity and screen, by the path of its file, when a
  video pauses, and the picker's choices.
- `kyprx.json` -- which shape these files are in.
- `snapshots/` -- copies of the desk taken before every big change. Not part of the setup.

**Copy this folder to another machine** -- or put it back over a fresh install -- and KyprX applies
it by itself. So does a `git pull`, a checkout, or an edit made here by hand: KyprX waits until the
files stop moving and git has finished, keeps a copy of the desk first, and applies only what
changed. *Go back to a copy...* on KyprX's Settings tab undoes it.

Wallpapers are referred to by path, never copied in: bring your wallpaper folder along too.
"""

#: Every text of `README.md` an earlier KyprX wrote, each exactly. A file that is still one of them,
#: byte for byte, is this app's own words that nobody has touched, and is brought up to date
#: (`ensure_extras`); one that is anything else -- edited, or written by somebody -- is the
#: owner's, and is left exactly as it is. The text `README` replaces goes in here each time it
#: changes, and `README` itself never does: a file rewritten with the words it already has would
#: wake the watch on the folder for nothing, pass after pass.
README_BEFORE = ("""# The KyprX folder

Everything KyprX controls on this desk, one file per part. KyprX writes these files itself a few
seconds after anything changes, so they are always the desk as it is.

- `settings.json` -- KyprX's own settings: notifications, colour from the wallpaper, the opacity
  of see-through windows, what a new window gets, which key the cheatsheet shows.
- `profiles.json` -- the profiles made on the Appearance tab.
- `windows.json` -- the Windows tab: every window that differs from what a new window gets.
- `decoration.json` -- the window decoration's (Klassy's) settings, and its per-window settings
  that are not columns on the Windows tab.
- `kwin.json` -- focus, borders, blur, the window animation, the tiling and its layout order,
  and which of those are switched on.
- `shortcuts.json` -- the keys of the actions on the Shortcuts tab.
- `colours.json` -- the mode, the colour preset, a colour of your own and how far it soaks in.
- `wallpaper.json` -- the wallpaper on screen, by the path of its file, and the picker's choices.
- `kyprx.json` -- which shape these files are in.
- `snapshots/` -- copies of the desk taken before every big change. Not part of the setup.

**Copy this folder to another machine** -- or put it back over a fresh install -- and KyprX applies
it by itself. So does a `git pull`, a checkout, or an edit made here by hand: KyprX waits until the
files stop moving and git has finished, keeps a copy of the desk first, and applies only what
changed. *Go back to a copy...* on KyprX's Settings tab undoes it.

Wallpapers are referred to by path, never copied in: bring your wallpaper folder along too.
""", """# The KyprX folder

Everything KyprX controls on this desk, one file per part. KyprX writes these files itself a few
seconds after anything changes, so they are always the desk as it is.

- `settings.json` -- KyprX's own settings: notifications, colour from the wallpaper, the opacity
  of see-through windows, what a new window gets, which key the cheatsheet shows.
- `profiles.json` -- the profiles made on the Appearance tab.
- `windows.json` -- the Windows tab: every window that differs from what a new window gets.
- `decoration.json` -- the window decoration's (Klassy's) settings, and its per-window settings
  that are not columns on the Windows tab.
- `kwin.json` -- focus, borders, the blur and the window animation, and whether those two are
  switched on.
- `tiling.json` -- the tiling: whether it is on and tiles windows as they open, the gaps, where a
  new window goes, the arrangements, and the windows that float or are never tiled. A window on
  the Windows tab says whether it floats in `windows.json` instead.
- `shortcuts.json` -- the keys of the actions on the Shortcuts tab.
- `colours.json` -- the mode, the colour preset, a colour of your own and how far it soaks in.
- `wallpaper.json` -- the wallpaper on screen, by the path of its file, and the picker's choices.
- `kyprx.json` -- which shape these files are in.
- `snapshots/` -- copies of the desk taken before every big change. Not part of the setup.

**Copy this folder to another machine** -- or put it back over a fresh install -- and KyprX applies
it by itself. So does a `git pull`, a checkout, or an edit made here by hand: KyprX waits until the
files stop moving and git has finished, keeps a copy of the desk first, and applies only what
changed. *Go back to a copy...* on KyprX's Settings tab undoes it.

Wallpapers are referred to by path, never copied in: bring your wallpaper folder along too.
""", """# The KyprX folder

Everything KyprX controls on this desk, one file per part. KyprX writes these files itself a few
seconds after anything changes, so they are always the desk as it is.

- `settings.json` -- KyprX's own settings: notifications, colour from the wallpaper, the opacity
  of see-through windows, what a new window gets, which key the cheatsheet shows.
- `profiles.json` -- the profiles made on the Appearance tab.
- `windows.json` -- the Windows tab: every window that differs from what a new window gets.
- `decoration.json` -- the window decoration's (Klassy's) settings, and its per-window settings
  that are not columns on the Windows tab.
- `kwin.json` -- focus, borders, the blur and the window animation, and whether those two are
  switched on.
- `tiling.json` -- the tiling: whether it is on and tiles windows as they open, the gaps, where a
  new window goes and what it does when the arrangement is full, the zone layouts and the
  arrangements, and the windows that float or are never tiled. A window on the Windows tab says
  whether it floats in `windows.json` instead.
- `shortcuts.json` -- the keys of the actions on the Shortcuts tab.
- `colours.json` -- the mode, the colour preset, a colour of your own and how far it soaks in.
- `wallpaper.json` -- the wallpaper on screen, by the path of its file, and the picker's choices.
- `kyprx.json` -- which shape these files are in.
- `snapshots/` -- copies of the desk taken before every big change. Not part of the setup.

**Copy this folder to another machine** -- or put it back over a fresh install -- and KyprX applies
it by itself. So does a `git pull`, a checkout, or an edit made here by hand: KyprX waits until the
files stop moving and git has finished, keeps a copy of the desk first, and applies only what
changed. *Go back to a copy...* on KyprX's Settings tab undoes it.

Wallpapers are referred to by path, never copied in: bring your wallpaper folder along too.
""",)

#: Folder shapes older than `FORMAT`, each taken one step forward. Empty while there has only been
#: one shape; the first change adds `1: step_to_2` here rather than a second reader.
MIGRATIONS: dict = {}


def render(data) -> str:
    """One part as its file: keys in order, two spaces, a newline at the end -- the shape a diff
    of it reads best in, and the only shape this app writes."""
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def manifest() -> dict:
    return {"format": FORMAT, "written_by": "KyprX",
            "about": "Everything KyprX controls on this desk. See README.md beside this file."}


# ---------------------------------------------------------------- reading

def read_texts(path: str = PATH) -> tuple[dict[str, str], list[str]]:
    """Every file of the folder that is there, as text, and a sentence for each that cannot be
    read as text at all."""
    texts, trouble = {}, []
    for name in [MANIFEST] + list(FILES.values()):
        target = os.path.join(path, name)
        if not os.path.exists(target):
            continue
        try:
            with open(target, encoding="utf-8") as fh:
                texts[name] = fh.read()
        except (OSError, UnicodeDecodeError) as e:
            trouble.append(f"{name} cannot be read: {e}")
    return texts, trouble


def parse(texts: dict[str, str]) -> tuple[dict, int, list[str]]:
    """The folder's parts as data, its format, and what is wrong with it -- each problem a
    sentence naming the file and, for bad JSON, the line.

    A part whose file is not there is simply absent: that part is not applied, and the next write
    puts the file back. A folder with no `kyprx.json` is taken to be of the current shape, and the
    caller says so.
    """
    problems, areas = [], {}
    fmt = FORMAT
    if MANIFEST in texts:
        try:
            found = json.loads(texts[MANIFEST])
            fmt = int((found or {}).get("format", FORMAT)) if isinstance(found, dict) else -1
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            problems.append(f"{MANIFEST} is not readable: {e}")
            fmt = -1
        if fmt > FORMAT:
            problems.append(f"this folder was written by a newer KyprX (shape {fmt}; this one "
                            f"reads up to {FORMAT}), so it is left exactly as it is")
        elif fmt < 1 and not problems:
            problems.append(f"{MANIFEST} does not say which shape the folder is in")
    for area, name in FILES.items():
        if name not in texts:
            continue
        try:
            data = json.loads(texts[name])
        except json.JSONDecodeError as e:
            problems.append(f"{name}, line {e.lineno}, column {e.colno}: {e.msg}")
            continue
        except ValueError:
            # After the clause above, which catches a subclass of this. A whole number longer than
            # Python turns digits into (4300 by default, `sys.get_int_max_str_digits`) is refused
            # by the reader with a plain ValueError and no line -- measured on Python 3.14 -- which
            # stopped the folder's pass with Python's words and no file named, and went back
            # across the bus from `PreviewFolder` as an exception.
            problems.append(f"{name} holds a number too long to read")
            continue
        if not isinstance(data, dict):
            problems.append(f"{name} is not an object with names in it")
            continue
        areas[area] = data
    while not problems and fmt < FORMAT:
        step = MIGRATIONS.get(fmt)
        if step is None:
            problems.append(f"no way from shape {fmt} to {FORMAT}")
            break
        areas, fmt = step(areas), fmt + 1
    return areas, fmt, problems


def texts_of(areas: dict) -> dict[str, str]:
    """What each part's file would say."""
    return {FILES[area]: render(data) for area, data in areas.items() if data is not None}


# ---------------------------------------------------------------- three ways

#: A name that is not there, in `merge`. One object for the whole module, so "absent" on one side
#: compares equal to "absent" on another.
_ABSENT = object()

#: What `merge` takes whole rather than name by name: part by part, each value by its path inside
#: the part. The daemon hands it to `arrival_target`, which hands each part's to `merge`.
#:
#: The tiling's zone layouts and arrangements are one value, `arrangements` in `tiling.json`, and
#: no merge of its inside can be trusted. An arrangement names zone layouts of the pool by their
#: ids, so a pool from one side under the arrangements of the other can name a zone layout that is
#: not there, or one that changed under it: a folder that renamed a zone layout and a desk that
#: took an arrangement out, merged name by name, would make a value neither of them wrote. And one
#: side in version 1 and the other in version 2 are two shapes with nothing in them to merge.
ATOMIC: dict[str, frozenset[str]] = {"tiling": frozenset({"/arrangements"})}


def merge(was_theirs, theirs, was_ours, ours, path: str = "",
          atomic: frozenset[str] = frozenset()) -> tuple[object, list[str]]:
    """What a part becomes when the folder changed it and the desk may have too.

    `was_theirs` is the folder's file as it was when the two last agreed and `theirs` as it is now;
    `was_ours` is the desk's description then and `ours` now. The two bases are kept apart because
    they need not be equal: a part this machine could not apply in full is remembered as the folder
    said it and as the desk ended up.

    Returns the merged value and the paths both sides changed -- which the folder won, and which
    are said. Objects are merged name by name, all the way down; anything else -- a number, a
    string, a list -- is one value. A name the folder took out is taken out, unless the desk
    changed it since.

    A path in `atomic` (`ATOMIC`) is one value too, and is told changed or not by `tiling.alike`
    rather than by how it is written, pair by pair: the folder's now against its then, the desk's
    now against its then, and the desk's now against the folder's. So the same zone layouts and
    arrangements in version 1 on one side and version 2 on the other are no change at all -- which
    is what a machine whose desk keeps version 1 sends with every change it makes, a gap say: that
    alone must not undo an edit made on this one -- while two values in version 1 that differ are a
    change, whatever their upgrades say. The absent marker and a text -- arrangements that could
    not be read, carried as they are -- are each alike only to themselves: there is nothing in them
    to read. The side that wins brings its own value exactly as it has it: one in version 1 stays
    version 1, which is what the desk writes when it applies one, unless the desk already says the
    same (`DeskPart._tiling_value_alike`).
    """
    if path in atomic:
        # Asked of each pair, never of one key made from each side: whether two are alike turns
        # on both -- on whether they are in one version -- so no key of one side alone can say it.
        if tiling.alike(theirs, was_theirs):
            return ours, []
        if tiling.alike(ours, was_ours) or tiling.alike(ours, theirs):
            return theirs, []
        return theirs, [path]
    if theirs == was_theirs:
        return ours, []
    if ours == was_ours or ours == theirs:
        return theirs, []
    if all(isinstance(v, dict) for v in (was_theirs, theirs, was_ours, ours)):
        out, conflicts = {}, []
        for key in sorted(set(was_theirs) | set(theirs) | set(was_ours) | set(ours)):
            value, found = merge(was_theirs.get(key, _ABSENT), theirs.get(key, _ABSENT),
                                 was_ours.get(key, _ABSENT), ours.get(key, _ABSENT),
                                 f"{path}/{key}", atomic)
            conflicts.extend(found)
            if value is not _ABSENT:
                out[key] = value
        return out, conflicts
    return theirs, [path or "/"]


# ---------------------------------------------------------------- deciding, in both directions

def arrivals(texts: dict[str, str], base: dict | None) -> list[str]:
    """The folder's files that changed from outside since the last agreement -- a copy, a pull, an
    edit. A file that is gone is not one: it is written back from the desk.

    None at all for a folder nobody has written yet and nothing remembered: a first start, or an
    install from before the folder existed, has nothing to apply and everything to write.
    """
    if base is None and MANIFEST not in texts:
        return []
    was = (base or {}).get("folder") or {}
    return sorted(n for n, t in texts.items() if t != was.get(n))


def arrival_target(arrived: list[str], areas: dict, base: dict | None, desk: dict, *,
                   atomic: dict[str, frozenset[str]]) -> tuple[dict, list[str], bool]:
    """What applying an arrival writes: `(target, conflicts, whole)`.

    With nothing remembered, the whole folder -- a new machine. Otherwise each part whose file
    arrived, merged three ways (`merge`) with what the desk has now, each value `atomic` names for
    its part taken whole (`ATOMIC` is the daemon's); a part the desk cannot be read for right now
    goes in as the folder has it.

    `atomic` has no default on purpose: a caller that left it out would merge the inside of the
    zone layouts and arrangements, quietly, and only for a folder and a desk that both changed.
    """
    if base is None:
        return {a: areas[a] for a in AREAS if a in areas}, [], True
    before, _, _ = parse(base.get("folder") or {})
    target, conflicts = {}, []
    for area in AREAS:
        name = FILES[area]
        if name not in arrived or area not in areas:
            continue
        if desk.get(area) is None:
            target[area] = areas[area]
            continue
        merged, found = merge(before.get(area), areas[area], (base.get("desk") or {}).get(area),
                              desk[area], atomic=atomic.get(area, frozenset()))
        target[area] = merged
        conflicts.extend(f"{name}{path}" for path in found)
    return target, conflicts, False


def mirror_plan(texts: dict[str, str], base: dict | None, desk: dict,
                dry_run: bool = False) -> tuple[dict[str, str], dict]:
    """What writing the desk into the folder writes, and the agreement after it: `(writes, agreed)`.

    **Only the parts the desk changed since the last agreement**, a file that is missing, and on
    the first pass all of it. Not every part whose file differs from the desk: a part this machine
    could not apply -- a wallpaper file that is not here -- differs from its file for ever, and
    writing it back out would send it to the machine it came from, which would apply it and send
    its own back. `scripts/dry-run.sh` step 15 has two machines prove it, and the loop the other
    rule makes.

    In a dry run nothing is written, so what is agreed is the folder as it really is beside the
    desk as described; remembering the files that would have been written would make the next pass
    find the real ones "changed from outside".
    """
    agreed = {"folder": dict((base or {}).get("folder") or {}),
              "desk": dict((base or {}).get("desk") or {})}
    writes: dict[str, str] = {}
    for area in AREAS:
        data, name = desk.get(area), FILES[area]
        if data is None:
            continue
        on_disk = texts.get(name)
        if on_disk is not None and base is not None and data == agreed["desk"].get(area):
            continue
        text = render(data)
        if text != on_disk:
            writes[name] = text
        agreed["folder"][name] = text
        agreed["desk"][area] = data
    if MANIFEST not in texts:
        writes[MANIFEST] = render(manifest())
        agreed["folder"][MANIFEST] = writes[MANIFEST]
    if dry_run:
        for name in writes:
            if name in texts:
                agreed["folder"][name] = texts[name]
            else:
                agreed["folder"].pop(name, None)
    return writes, agreed


# ---------------------------------------------------------------- git, and files still moving

def git_busy(path: str = PATH) -> str:
    """What git is in the middle of in the repository around the folder, or "" when nothing.

    Looked for the way git itself marks it: a lock on the index, or a merge, rebase, cherry-pick or
    revert under way. A folder that is its own repository and one that sits deep inside a dotfiles
    repository are both found, by walking up from where the folder really is.
    """
    here = os.path.realpath(path)
    while True:
        dot = os.path.join(here, ".git")
        if os.path.isfile(dot):
            try:
                with open(dot, encoding="utf-8") as fh:
                    line = fh.read().strip()
                if line.startswith("gitdir:"):
                    dot = os.path.normpath(os.path.join(here, line[len("gitdir:"):].strip()))
            except OSError:
                return ""
        if os.path.isdir(dot):
            for marker, what in (("index.lock", "writing its index"),
                                 ("MERGE_HEAD", "a merge"), ("rebase-merge", "a rebase"),
                                 ("rebase-apply", "a rebase"),
                                 ("CHERRY_PICK_HEAD", "a cherry-pick"),
                                 ("REVERT_HEAD", "a revert")):
                if os.path.exists(os.path.join(dot, marker)):
                    return what
            return ""
        parent = os.path.dirname(here)
        if parent == here:
            return ""
        here = parent


# ---------------------------------------------------------------- writing

def write_text(name: str, text: str, path: str = PATH) -> None:
    """One file of the folder, atomically -- and into whatever a link there points at, rather than
    over the link. A folder kept in a dotfiles repository is often a link to it, or holds links to
    it file by file; replacing a link with a file would quietly stop the repository hearing about
    anything again. Never called in dry run; the caller says what it would have written instead."""
    target = os.path.realpath(os.path.join(path, name))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + ".new"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, target)


def ensure_extras(path: str = PATH) -> list[str]:
    """`README.md`, `.gitignore` and `.stignore`, each written when absent -- and `README.md` also
    when it is still an earlier KyprX's text, untouched (`README_BEFORE`), so the folder's own
    description names the files it has now. Anything else there is the owner's and is never
    written over. Returns what was written. In dry run, nothing."""
    wrote = []
    for name, text in (("README.md", README), (".gitignore", IGNORES), (".stignore", STIGNORE)):
        target = os.path.join(path, name)
        if os.path.lexists(target) and not (name == "README.md" and _readme_before(target)):
            continue
        if writer.dry_run():
            continue
        write_text(name, text, path)
        wrote.append(name)
    return wrote


def _readme_before(target: str) -> bool:
    """Is this file, byte for byte, a `README.md` an earlier KyprX wrote? Read through a link the
    way `write_text` writes through one; a file that cannot be read is somebody's, and is not."""
    try:
        with open(target, "rb") as fh:
            found = fh.read()
    except OSError:
        return False
    return found != README.encode("utf-8") and any(found == text.encode("utf-8")
                                                   for text in README_BEFORE)


# ---------------------------------------------------------------- what was agreed

def load_base() -> dict | None:
    """The last moment folder and desk agreed: `{"folder": {file: text}, "desk": {area: data}}`, or
    None when nothing is remembered."""
    try:
        with open(BASE, encoding="utf-8") as fh:
            found = json.load(fh)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(found, dict) or not isinstance(found.get("folder"), dict):
        return None
    found.setdefault("desk", {})
    return found


def save_base(base: dict) -> None:
    """Remember an agreement. In dry run, not at all: the next real run must see the folder as the
    real run last left it."""
    if writer.dry_run():
        return
    os.makedirs(os.path.dirname(BASE), exist_ok=True)
    tmp = BASE + ".new"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(base, fh, ensure_ascii=False, sort_keys=True)
    os.replace(tmp, BASE)
