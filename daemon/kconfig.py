"""Reading and writing KConfig INI files.

Not configparser: KConfig's format differs from Python's INI in three ways that matter here —
compound group names (`[Tiling][uuid][]`), its own value escaping, and a lexicographic output
order by group and by key. Reproducing that order is what keeps diffs honest: writing keys out
of order would make the whole file show up as changed on every save, in a file that other tools
snapshot.

The group component separator is `\x1d`, the same one KConfig uses internally — that is what
makes `[Tiling][x][]` sort before `[Tiling][x][y]`.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
import xml.etree.ElementTree as ET


class WriteConflict(Exception):
    """The file changed on disk between `load()` and `save()`.

    This happens for real: Klassy's settings app, System Settings and any snapshot tooling write
    the same files. Callers catch this, reload and redo the change — never overwrite.
    """


SEP = "\x1d"

class _NoValue:
    """The one marker for a key with no value. Compared by identity everywhere, so a copy of it --
    `copy.deepcopy` of a group, which the checks do -- must be the marker itself and not a second
    object that looks like a value."""

    def __copy__(self):
        return self

    def __deepcopy__(self, _memo):
        return self

    def __reduce__(self):
        return "NO_VALUE"

    def __repr__(self):
        return "NO_VALUE"


#: A line that is only a key, with no `=` — KConfig's `[$d]` marker, meaning "this value went
#: back to its default". Keeping it distinct from the empty string is what makes the round trip
#: lossless.
NO_VALUE = _NoValue()

# Order matters: the backslash must be handled first when writing and last when reading.
_ESCAPES = [("\\", "\\\\"), ("\n", "\\n"), ("\t", "\\t"), ("\r", "\\r")]

_GROUP_RE = re.compile(r"^\[(.*)\]$")


def escape(value: str) -> str:
    """Raw value -> value the way KConfig writes it."""
    for raw, esc in _ESCAPES:
        value = value.replace(raw, esc)
    # A space at either edge becomes \s, otherwise KConfig eats it when reading. This is what
    # produces `wmclass=\sorg.telegram.desktop` in window rules: a Wayland app has an empty
    # resource name, so the "whole class" form starts with a space.
    if value.startswith(" "):
        value = "\\s" + value[1:]
    if value.endswith(" ") and not value.endswith("\\s"):
        value = value[:-1] + "\\s"
    return value


def unescape(value: str) -> str:
    """Value as stored in the file -> raw value."""
    out = []
    i = 0
    while i < len(value):
        c = value[i]
        if c == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            if nxt == "s":
                out.append(" ")
            elif nxt == "n":
                out.append("\n")
            elif nxt == "t":
                out.append("\t")
            elif nxt == "r":
                out.append("\r")
            elif nxt == "\\":
                out.append("\\")
            else:
                out.append(c)
                out.append(nxt)
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _parse_group_header(raw: str) -> str:
    """`Tiling][uuid][` (what sits between the outer brackets) -> name joined by the separator."""
    return SEP.join(raw.split("]["))


def _render_group_header(name: str) -> str:
    return "[" + "][".join(name.split(SEP)) + "]"


class KConfig:
    """One KConfig INI file, loaded whole.

    `groups` maps a group name (components joined by SEP) to a dict of key -> raw value.

    Never keep an instance alive between operations: the desktop writes these files too. Load,
    change, save, discard.
    """

    def __init__(self, path: str):
        self.path = os.path.expanduser(path)
        self.groups: dict[str, dict[str, str]] = {}
        self._preamble: dict[str, str] = {}  # keys before the first [group]
        self._digest_at_load = ""
        self.load()

    def _digest(self) -> str:
        if not os.path.exists(self.path):
            return ""
        with open(self.path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()

    # ---------------------------------------------------------------- reading

    def load(self) -> None:
        self.groups = {}
        self._preamble = {}
        self._digest_at_load = self._digest()
        if not os.path.exists(self.path):
            return
        current = None
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue
                m = _GROUP_RE.match(line)
                if m:
                    current = _parse_group_header(m.group(1))
                    self.groups.setdefault(current, {})
                    continue
                target = self._preamble if current is None else self.groups[current]
                if "=" in line:
                    key, _, value = line.partition("=")
                    target[key] = unescape(value)
                else:
                    target[line] = NO_VALUE

    # ---------------------------------------------------------------- queries

    def get(self, group: str, key: str, default=None):
        return self.groups.get(group, {}).get(key, default)

    def get_bool(self, group: str, key: str, default: bool = False) -> bool:
        raw = self.get(group, key)
        return default if raw is None or raw is NO_VALUE else str(raw).lower() == "true"

    def get_int(self, group: str, key: str, default: int = 0) -> int:
        raw = self.get(group, key)
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return default

    def group_names(self, prefix: str = "") -> list[str]:
        return sorted(g for g in self.groups if g.startswith(prefix))

    # ---------------------------------------------------------------- writing

    def set(self, group: str, key: str, value) -> None:
        if isinstance(value, bool):
            value = "true" if value else "false"
        self.groups.setdefault(group, {})[key] = str(value)

    def delete_key(self, group: str, key: str) -> None:
        self.groups.get(group, {}).pop(key, None)

    def delete_group(self, group: str) -> None:
        self.groups.pop(group, None)

    @staticmethod
    def _render_entry(key: str, value) -> str:
        return key if value is NO_VALUE else f"{key}={escape(value)}"

    def render(self) -> str:
        out = []
        for key in sorted(self._preamble):
            out.append(self._render_entry(key, self._preamble[key]))
        if self._preamble:
            out.append("")
        for name in sorted(self.groups):
            out.append(_render_group_header(name))
            for key in sorted(self.groups[name]):
                out.append(self._render_entry(key, self.groups[name][key]))
            out.append("")
        return "\n".join(out)

    def dirty(self) -> bool:
        """Would saving change anything?"""
        if not os.path.exists(self.path):
            return bool(self.groups or self._preamble)
        with open(self.path, encoding="utf-8") as fh:
            return fh.read() != self.render()

    def diff(self) -> str:
        """Unified diff of what `save()` would write. This is what dry-run mode reports."""
        import difflib

        old = open(self.path, encoding="utf-8").read() if os.path.exists(self.path) else ""
        return "".join(difflib.unified_diff(
            old.splitlines(keepends=True), self.render().splitlines(keepends=True),
            f"a/{os.path.basename(self.path)}", f"b/{os.path.basename(self.path)}"))

    def save(self, *, force: bool = False) -> None:
        """Write atomically, preserving the file mode.

        Refuses to write if the file changed on disk since `load()`, unless `force`.
        """
        if not force and self._digest() != self._digest_at_load:
            raise WriteConflict(self.path)
        data = self.render()
        directory = os.path.dirname(self.path)
        mode = os.stat(self.path).st_mode & 0o777 if os.path.exists(self.path) else 0o600
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".kyprx-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(data)
            os.chmod(tmp, mode)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        self._digest_at_load = self._digest()


# ---------------------------------------------------------------- what a program defaults to

def _expand(name: str, entry) -> list[str]:
    """A schema entry's real key names.

    Half of a decoration schema is parameterised — `ShowOutlineOnHover$(ShowOutlineOnHoverActive)`
    is two keys, `…Active` and `…Inactive`. Reading the name literally would produce a default
    nobody can ever look up.
    """
    if "$(" not in name:
        return [name]
    values = [v.text or "" for v in entry.iterfind(".//{*}parameter/{*}values/{*}value")]
    return [re.sub(r"\$\(\w+\)", v, name) for v in values] or [name]


def schema_defaults(path: str) -> dict[str, dict[str, str]]:
    """Every default a `.kcfg` schema declares, as `{group: {key: value}}`.

    Worth reading rather than hard-coding, and the reason is not tidiness. This app shows a
    setting the file does not carry as coming from a default — and without the real default it has
    to guess. It guessed "off" for everything, which for a setting that ships **on** is not a
    guess but a false statement, and the interface then wrote that false statement to the file the
    moment anyone touched the control. One decoration setting ended up inverted in a config nobody
    meant to edit, and a dark line under every title bar button was the visible half of it.

    Note `key=` wins over `name=`: a schema may name an entry in one spelling and store it in
    another, and it is the stored spelling that has to match the file.

    Returns an empty mapping when the schema is not installed. That is the honest fallback — the
    interface goes back to saying it does not know, rather than to saying something false.
    """
    if not os.path.exists(path):
        return {}
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return {}
    out: dict[str, dict[str, str]] = {}
    for group in root.iterfind("{*}group"):
        bucket = out.setdefault(group.get("name") or "", {})
        for entry in group.iterfind("{*}entry"):
            per_value: dict[str, str] = {}
            shared: str | None = None
            for node in entry.iterfind("{*}default"):
                text = (node.text or "").strip()
                if node.get("param"):
                    per_value[node.get("param")] = text
                else:
                    shared = text
            stored = entry.get("key") or entry.get("name") or ""
            for full in _expand(stored, entry):
                value = next((v for prm, v in per_value.items() if full.endswith(prm)), shared)
                if value is not None:
                    bucket[full] = value
    return {g: keys for g, keys in out.items() if keys}


def schema_keys(path: str) -> dict[str, set[str]] | None:
    """Every key a `.kcfg` schema names, as `{group: {key}}`, whether or not it has a default --
    or None when the schema is not installed or cannot be read.

    `schema_defaults` answers a different question and leaves out every entry with no default,
    which is exactly the kind of entry a check for a misspelt key cannot afford to miss. None
    rather than an empty mapping, because "not installed" and "names nothing" must not read the
    same to a caller that is about to say every key it holds is wrong.
    """
    if not os.path.exists(path):
        return None
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None
    out: dict[str, set[str]] = {}
    for group in root.iterfind("{*}group"):
        bucket = out.setdefault(group.get("name") or "", set())
        for entry in group.iterfind("{*}entry"):
            bucket.update(_expand(entry.get("key") or entry.get("name") or "", entry))
    return out
