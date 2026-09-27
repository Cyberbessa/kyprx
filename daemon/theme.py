"""The desktop's colours: light or dark, one of a few presets, and a colour of your own.

Nothing here is written to the files the desktop owns. The colour scheme, the Plasma style and the
global theme are *chosen*, by asking the tools that own them -- which is the only way running
windows repaint without a logout. The one thing this module writes is a colour scheme of its own,
and it writes it through `daemon/writer.py` like everything else.

Everything below was measured on Plasma 6.7.5, and most of it is not what reading the
documentation suggests.

- **The shell follows the colour scheme only when the Plasma style carries no palette of its
  own.** A style whose `colors` file carries a palette paints the panel from it and never reads
  `kdeglobals`; a style with no `colors` file, or one with nothing in it, follows the scheme --
  KConfig layers `kdeglobals` under every file it opens. Of every style installed on a stock
  desktop only `default` has no palette -- `klassy-dark`, `klassy-light` and every third-party
  style tried here ship one. That is why changing the colour scheme used to leave the panel
  exactly where it was, and it is why this app ships a Plasma style of its own whose `colors`
  file is deliberately empty, `share/desktoptheme/kyprx`. Empty rather than absent for a
  measured reason, written in the file itself.

- **Applying a global theme does not write the user's config; it rewrites a layer underneath.**
  The package's `defaults` are copied into `~/.config/kdedefaults/` and the matching user keys are
  deleted. So every read here cascades -- the user's file, then that layer -- or the application
  style reads as unset on a desktop where it is plainly Klassy. And one apply rewrites all six
  files in that directory, the cursor and splash defaults included, which is why it happens only
  when the mode is actually wrong.

- **A scheme's identifier is its file name**, and it need not match the `[General] ColorScheme=`
  inside it. `ChromeOSDark.colors` on this machine says `OrchisDark`, and both names are offered.
  The schemes this app ships keep the two identical, and everything here matches on the file name,
  because that is what the tool takes.

- **Re-applying the scheme already in force does nothing, and reports success doing it.** So a
  change that alters the palette without altering its name -- a new accent, a new tint -- cannot
  land by asking for the same scheme again. It needs a bounce through another one, and `plan()`
  emits that only when it is needed.

- **Writing `kdeglobals [General] AccentColor` is enough, and is the only thing that lasts.**
  Applying any scheme bakes the accent into the palette out of that key. The tool's own
  `--accent-color` option does the baking but never stores the key, so the tone is lost the next
  time anything applies a scheme -- which is why it is not used here.

- **`[General] TintFactor` in the scheme file is what carries a colour into the backgrounds.**
  Without it the accent reaches highlights, links, focus and selection only. With it, Plasma tints
  every other colour toward the accent in OKLab, preserving perceptual lightness: the Klassy Dark
  window background, `42,46,50`, becomes `45,44,57` at 0.15, `49,39,67` at 0.40 and `58,26,88` at
  0.90. It costs exactly one thing, measured: with `TintFactor` present, the title bar's `[WM]`
  colour is overwritten with the tinted window colour, so the bar stops being a shade lighter than
  the window -- and the tinted colour carries **no alpha** (measured: `kdeglobals [WM]
  activeBackground=57,37,31` under Dracula soaked in at 25 %), so under a colour of your own the bar
  is opaque whether or not anything overrides the scheme. Worn plain, nine of the eleven schemes
  here carry an alpha on the active bar, and there it is Klassy's `TitleBarOpacityActive`, with
  the scheme's own alpha overridden, that keeps it opaque (`daemon/defaults.py`, which has the
  measurement).
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

import kconfig
from kwin_config import DECORATION_GROUP

CONFIG = os.path.expanduser(os.environ.get("XDG_CONFIG_HOME") or "~/.config")

#: The layer a global theme writes, and the one every read here falls back to.
KDEDEFAULTS = os.path.join(CONFIG, "kdedefaults")

DATA_HOME = os.path.expanduser(os.environ.get("XDG_DATA_HOME") or "~/.local/share")

#: Where a scheme this app writes goes. Reading looks wider -- see `_scheme_dirs`.
SCHEMES_HOME = os.path.join(DATA_HOME, "color-schemes")

#: The one Plasma style, worn by every preset: Plasma's own panel artwork, and an empty `colors`
#: file, so the panel takes the colour scheme's -- a colour of your own included. One package
#: serves both modes, because the artwork recolours itself from the scheme as it is drawn. Its
#: `FallbackTheme` names klassy-dark, which Plasma 6 reads for wallpaper defaults only -- the
#: artwork on screen is `default`'s, measured.
STYLE = "kyprx"

PACKAGES = {"dark": "org.kde.klassydarkbottompanel.desktop",
            "light": "org.kde.klassylightbottompanel.desktop"}

#: KDE's own global themes, which *Take KyprX off this desk* applies -- see `pure_plan`.
PURE = {"dark": "org.kde.breezedark.desktop", "light": "org.kde.breeze.desktop"}

#: What the packages above set when they are applied. Kept here because applying one makes these
#: true whatever was chosen before, and `plan()` has to compare against what will be, not what is.
BASE_SCHEME = {"dark": "KlassyDark", "light": "KlassyLight"}
BASE_STYLE = {"dark": "klassy-dark", "light": "klassy-light"}

#: The scheme a bounce goes through when the palette has to be re-applied under an unchanged name.
#: Chosen for brightness rather than convenience: bouncing a dark desktop through a light scheme
#: is a white flash. Both ship with Plasma itself.
BOUNCE = {"dark": "BreezeDark", "light": "BreezeLight"}

#: The scheme written when a colour of your own is asked to reach the backgrounds. It is the
#: chosen preset's own scheme with two keys added, and it says which preset it came from so that
#: nothing has to be remembered anywhere else.
CUSTOM = "KyprXCustom"
FROM_PRESET = "KyprXPreset"

#: The five keys this app means to take over from the global theme. Everything else the package
#: names is somebody's own choice.
#:
#: Applying a global theme does not overwrite a user's key, it **deletes** it -- so every other key
#: the package's `defaults` names is a setting about to vanish without a word. Measured: one switch
#: from dark to light and back took the icon theme with it, because the package names
#: `[Icons] Theme` and this desktop had set it by hand. `plan()` reads them before the apply and
#: puts them back after it.
OURS = frozenset({
    ("kdeglobals", "General", "ColorScheme"),
    ("kdeglobals", "KDE", "widgetStyle"),
    ("kwinrc", DECORATION_GROUP, "library"),
    ("kwinrc", DECORATION_GROUP, "theme"),
    ("plasmarc", "Theme", "name"),
})

#: `AccentColor` as Plasma spells "none": an invalid colour, meaning follow the scheme.
NO_ACCENT = "0,0,0,0"

#: How far a colour of your own soaks into the backgrounds when that is asked for. Plasma's own
#: default is 0.15, which on a dark scheme moves a background by about three units in each
#: channel -- true, and not visible. This is the smallest value that reads as a tint.
DEFAULT_TINT = 0.25


@dataclass(frozen=True)
class Preset:
    id: str
    name: str
    mode: str
    #: The `.colors` file's base name, which is also its `[General] ColorScheme=` and the argument
    #: the tool takes. All three are the same string on purpose -- see the note above.
    scheme: str
    note: str = ""


#: Klassy {Dark,Light} is the scheme the global theme applies by itself and is the state to
#: return to -- for the colours: the panel stays on `STYLE` and follows them, where the global theme
#: would put Klassy's own style there. Every preset wears `STYLE`, which is why no row says so.
PRESETS = [
    Preset("klassy-dark", "Klassy Dark", "dark", "KlassyDark",
           "what the global theme applies by itself"),
    Preset("longive", "Longive", "dark", "KyprXLongive"),
    Preset("catppuccin-mocha", "Catppuccin Mocha", "dark", "KyprXCatppuccinMocha"),
    Preset("nord", "Nord", "dark", "KyprXNord"),
    Preset("gruvbox-dark", "Gruvbox Dark", "dark", "KyprXGruvboxDark"),
    Preset("dracula", "Dracula", "dark", "KyprXDracula"),
    Preset("solarized-dark", "Solarized Dark", "dark", "KyprXSolarizedDark"),
    Preset("monochrome-dark", "Monochrome Dark", "dark", "KyprXMonochromeDark"),
    Preset("klassy-light", "Klassy Light", "light", "KlassyLight",
           "what the global theme applies by itself"),
    Preset("catppuccin-latte", "Catppuccin Latte", "light", "KyprXCatppuccinLatte"),
    Preset("solarized-light", "Solarized Light", "light", "KyprXSolarizedLight"),
    Preset("gruvbox-light", "Gruvbox Light", "light", "KyprXGruvboxLight"),
    Preset("rose-pine-dawn", "Rosé Pine Dawn", "light", "KyprXRosePineDawn"),
    Preset("monochrome-light", "Monochrome Light", "light", "KyprXMonochromeLight"),
]

MODES = ("dark", "light")


def preset(preset_id: str) -> Preset | None:
    if preset_id == "carl":
        preset_id = "longive"
    return next((p for p in PRESETS if p.id == preset_id), None)


def default_preset(mode: str) -> Preset:
    """The preset a mode falls back to: Longive for dark, and Klassy Light for light."""
    if mode == "dark":
        found = preset("longive")
        if found:
            return found
    return next(p for p in PRESETS if p.mode == mode and p.scheme == BASE_SCHEME[mode])


# ---------------------------------------------------------------- reading what is in force

def _pair(name: str) -> tuple[kconfig.KConfig, kconfig.KConfig]:
    """A config file as the desktop reads it: the user's, then the global theme's layer."""
    return (kconfig.KConfig(os.path.join(CONFIG, name)),
            kconfig.KConfig(os.path.join(KDEDEFAULTS, name)))


def _get(pair, group: str, key: str) -> str:
    for cfg in pair:
        value = cfg.get(group, key)
        if value is not None and value is not kconfig.NO_VALUE:
            return str(value)
    return ""


def _float(value, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def is_colour(value: str) -> bool:
    """Is this the way this app spells a colour -- three numbers, as the decoration stores them?

    The spelling is `ColorButton`'s, and it is also Plasma's own for `AccentColor`, so the value
    travels from the picker to `kdeglobals` without being reshaped on the way.
    """
    parts = str(value).split(",")
    return (len(parts) == 3
            and all(p.strip().isdigit() and 0 <= int(p) <= 255 for p in parts))


def _dirs(leaf: str) -> list[str]:
    """Every directory the session looks in for `leaf`, in the session's own spelling.

    Deduplicated by `realpath` but kept as written, for the same reason `daemon/wallpaper.py`
    does it: resolving outright breaks matching on a layout where the home directory is itself a
    link.
    """
    roots = [DATA_HOME]
    roots += (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    out, seen = [], set()
    for root in roots:
        if not root:
            continue
        path = os.path.join(os.path.expanduser(root), leaf)
        key = os.path.realpath(path)
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


def scheme_path(scheme: str) -> str:
    """Where this scheme's file is, or "" when it is not installed."""
    if not scheme:
        return ""
    for folder in _dirs("color-schemes"):
        path = os.path.join(folder, scheme + ".colors")
        if os.path.exists(path):
            return path
    return ""


def style_path(style: str) -> str:
    if not style:
        return ""
    for folder in _dirs("plasma/desktoptheme"):
        path = os.path.join(folder, style)
        if os.path.exists(os.path.join(path, "metadata.json")):
            return path
    return ""


def package_defaults(package: str) -> list[tuple[str, str, str]]:
    """Every (file, group, key) a look-and-feel package's `defaults` names.

    The file's headers come in two shapes -- `[file][group]`, and a bare `[group]` that means
    `kdeglobals`. Both are in the Klassy packages, so both are read.
    """
    path = ""
    for folder in _dirs("plasma/look-and-feel"):
        candidate = os.path.join(folder, package, "contents", "defaults")
        if os.path.exists(candidate):
            path = candidate
            break
    if not path:
        return []
    out, where = [], None
    for raw in open(path, encoding="utf-8", errors="replace"):
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            inside = line[1:-1]
            where = tuple(inside.split("][")) if "][" in inside else ("kdeglobals", inside)
            continue
        if where and "=" in line and not line.startswith("#"):
            out.append((where[0], where[1], line.split("=", 1)[0].strip()))
    return out


def at_risk(package: str) -> list[tuple[str, str, str, str]]:
    """What applying `package` would take away: the keys set in the user's own layer that the
    package names and this app is not taking over, with the values they hold now."""
    out = []
    for name, group, key in package_defaults(package):
        if (name, group, key) in OURS:
            continue
        value = kconfig.KConfig(os.path.join(CONFIG, name)).get(group, key)
        if value is not None and value is not kconfig.NO_VALUE and str(value):
            out.append((name, group, key, str(value)))
    return out


def follows_colours(style: str) -> bool:
    """Does the panel take its colours from the colour scheme, wearing this Plasma style?

    The measured rule, and the whole reason this app ships a style of its own: a style whose
    `colors` file carries a palette paints from that file and never looks at the scheme. A file
    with no `[Colors:*]` group in it is not a palette -- KConfig layers `kdeglobals` under it, so
    the style follows the scheme exactly as one with no file does. That is what `kyprx` ships,
    and the file says why.
    """
    path = style_path(style)
    if not path:
        return False
    palette = os.path.join(path, "colors")
    if not os.path.exists(palette):
        return True
    return not any(group.startswith("Colors:") for group in kconfig.KConfig(palette).groups)


def current() -> dict:
    """What the desktop is wearing now, read the way the desktop reads it."""
    globals_, plasma, kwin = _pair("kdeglobals"), _pair("plasmarc"), _pair("kwinrc")
    package = _get(globals_, "KDE", "LookAndFeelPackage")
    scheme = _get(globals_, "General", "ColorScheme")
    accent = _get(globals_, "General", "AccentColor")
    now = {
        "package": package,
        "mode": next((m for m, p in PACKAGES.items() if p == package), ""),
        "scheme": scheme,
        "style": _get(plasma, "Theme", "name"),
        "accent": "" if accent in ("", NO_ACCENT) else accent,
        #: Plasma ships a background service that overwrites the accent on every wallpaper change
        #: when this is on. Left true it would fight everything below, so `plan()` turns it off.
        "from_wallpaper": _get(globals_, "General", "accentColorFromWallpaper").lower() == "true",
        "tint": 0.0,
        "preset": "",
        "widget_style": _get(globals_, "KDE", "widgetStyle"),
        "decoration": _get(kwin, DECORATION_GROUP, "library"),
    }
    if scheme == CUSTOM:
        # The derived scheme says which preset it came from, so nothing has to be remembered in a
        # settings file that could disagree with the desktop.
        cfg = kconfig.KConfig(scheme_path(CUSTOM) or os.path.join(SCHEMES_HOME, CUSTOM + ".colors"))
        from_preset = str(cfg.get("General", FROM_PRESET, "") or "")
        if from_preset == "carl":
            from_preset = "longive"
        now["preset"] = from_preset
        now["tint"] = _float(cfg.get("General", "TintFactor", 0))
    else:
        now["preset"] = next((p.id for p in PRESETS if p.scheme == scheme), "")
    return now


def swatch(scheme: str) -> list[str]:
    """Four colours out of the scheme's own file, for drawing it: the window, a content area, the
    selection and the text. Read rather than declared, so what is shown is what will be applied."""
    path = scheme_path(scheme)
    if not path:
        return []
    cfg = kconfig.KConfig(path)
    wanted = [("Colors:Window", "BackgroundNormal"), ("Colors:View", "BackgroundNormal"),
              ("Colors:Selection", "BackgroundNormal"), ("Colors:Window", "ForegroundNormal")]
    out = [str(cfg.get(g, k, "") or "") for g, k in wanted]
    return out if all(out) else []


#: The one colour of a preset's that leaves the palette: the ring around the window.
SELECTION = ("Colors:Selection", "BackgroundNormal")


def selection_colour(scheme: str) -> str:
    """The colour a preset hands to the window outline: its own selection colour.

    Read out of the scheme's file rather than declared beside the row, so a preset cannot lie about
    it -- it is the very value the third band of its swatch is drawn in, from the same two names.

    Empty when the scheme is not installed or carries no such colour, and empty is the answer that
    means "leave the outline alone" -- never a colour picked here to stand in for one.
    """
    path = scheme_path(scheme)
    if not path:
        return ""
    raw = str(kconfig.KConfig(path).get(*SELECTION, "") or "")
    # A scheme may carry an alpha on that colour. The decoration's key is three numbers and keeps
    # its opacity in a key of its own, `WindowOutlineCustomColorOpacityActive`, so a fourth
    # component written here would be a value it reads as a colour it cannot parse.
    parts = [p.strip() for p in raw.split(",")[:3]]
    return ",".join(parts) if len(parts) == 3 and all(parts) else ""


def available(p: Preset) -> str:
    """"" when this preset can be applied, otherwise the sentence saying why not."""
    if not scheme_path(p.scheme):
        return f"the colour scheme {p.scheme} is not installed"
    if not style_path(STYLE):
        # Every preset wears it, and install.sh is what puts it there.
        return f"the Plasma style {STYLE} is not installed"
    return ""


def invariants(now: dict) -> list[str]:
    """What is not as this app expects. Reported, never repaired here.

    Repairing means applying the global theme, which rewrites six files in `kdedefaults` -- that
    is somebody pressing Apply, not a daemon starting up.
    """
    out = []
    if not now["mode"]:
        out.append(f"the global theme is {now['package'] or '(unset)'}, which is not one of "
                   f"Klassy's -- the light and dark switch cannot tell which mode this is")
    if now["widget_style"] and now["widget_style"] != "Klassy":
        out.append(f"the application style is {now['widget_style']}, not Klassy")
    if now["decoration"] and now["decoration"] != "org.kde.klassy":
        out.append(f"the window decoration is {now['decoration']}, not Klassy")
    return out


# ---------------------------------------------------------------- the derived scheme

def custom_path() -> str:
    return os.path.join(SCHEMES_HOME, CUSTOM + ".colors")


def ensure_custom(tx, p: Preset, tint: float) -> bool:
    """Write the preset's scheme out again with a tint factor on it. True if the file changed.

    Rebuilt from the preset's file every time rather than patched in place, so that a preset whose
    own colours changed -- and one of them is somebody's, tuned by hand -- is followed rather than
    frozen at whatever it was the first time this ran.
    """
    base = scheme_path(p.scheme)
    if not base:
        raise RuntimeError(f"the colour scheme {p.scheme} is not installed")
    source = kconfig.KConfig(base)
    cfg = tx.config(custom_path())
    for group in list(cfg.groups):
        cfg.delete_group(group)
    for group, entries in source.groups.items():
        for key, value in entries.items():
            cfg.set(group, key, value)
    cfg.set("General", "ColorScheme", CUSTOM)
    cfg.set("General", "Name", f"{p.name} + your colour (KyprX)")
    cfg.set("General", "TintFactor", f"{tint:g}")
    cfg.set("General", FROM_PRESET, p.id)
    return cfg.dirty()


def drop_custom(tx) -> bool:
    """Take the derived scheme away again. True if there was one.

    Removing the file is not this app's to do -- it may be what the desktop is wearing at the
    moment the tint is switched off, and a scheme that vanishes underneath Plasma is a desktop
    with no colours. `plan()` moves off it first; the file is simply left, harmless and inert,
    the way any unselected scheme is.
    """
    return os.path.exists(custom_path())


# ---------------------------------------------------------------- applying

def _run(argv: list[str], where: dict | None = None) -> None:
    """Run one of the desktop's own tools, and turn a failure into something readable.

    A timeout because these build a Qt application to do their work and the daemon's loop is one
    thread: a tool that hangs would take the whole daemon with it. Measured: asking for the scheme
    already in force is not a failure -- it prints "already set" and exits 0 -- but nothing here
    ever asks, which is what `plan()` is for.
    """
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False,
                              env=where)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{argv[0]} did not finish within a minute") from None
    except FileNotFoundError:
        raise RuntimeError(f"{argv[0]} is not installed -- it comes with plasma-workspace") from None
    if done.returncode != 0:
        detail = (done.stderr or done.stdout or "").strip().splitlines()
        raise RuntimeError(f"{argv[0]} failed: {detail[0] if detail else done.returncode}")


def _line(what: str, tool: str, was: str, now: str) -> str:
    """A step's description, shaped like the diff it is not.

    Everything that reads a transaction's plan reads a unified diff, and the session writes are
    the part that has no file to diff -- so they are written to read the same way rather than as
    prose in the middle of one.
    """
    return f"--- {what}\n+++ {tool}\n-{was or '(none)'}\n+{now or '(none)'}\n"


def _scheme_words(scheme: str, p: Preset, tint: float) -> str:
    """A colour scheme as a person would name it: the preset, or the preset with a colour in it."""
    if scheme == CUSTOM:
        return f"{p.name} with your colour soaked in at {round(tint * 100)} %"
    named = next((q.name for q in PRESETS if q.scheme == scheme), "")
    return named or scheme or "none"


def plan(now: dict, wanted: dict,
         scheme_written: bool = False) -> list[tuple[str, Callable, str]]:
    """Every step this change needs, and none that it does not. Empty when it is already so.

    Answering with nothing is the property `scripts/drive.py` asserts: a setter that reports a
    change when nothing changed is a tab that writes by itself, and here it would also be three
    Qt programs and a repaint of the whole desktop.

    The order is forced. Applying the global theme reverts the colour scheme, the Plasma style,
    the icon theme and the decoration to the package's own -- so anything done before it is
    thrown away, and everything after it has to compare against what the package will have made
    true rather than against what is true now.

    Each step is (description, action, plain words). The description is shaped like a diff and
    `scripts/drive.py` reads it; the plain words are what a dry run tells a person, and they say
    what a step does to the desktop, including what the description leaves out -- that the global
    theme rewrites six files, that a scheme applied again repaints every application.
    """
    mode = wanted["mode"]
    p = preset(wanted["preset"]) or default_preset(mode)
    accent = wanted.get("accent") or ""
    tint = _float(wanted.get("tint"), 0.0) if accent else 0.0
    use_custom = bool(accent) and tint > 0

    steps: list[tuple[str, Callable, str]] = []
    scheme_now, style_now = now["scheme"], now["style"]
    # The scheme being left, named by what it is -- its own preset and tint -- and not by the ones
    # being put on: "Dracula with your colour at 25 %", not "Klassy Dark with your colour at 0 %".
    p_now = preset(now.get("preset") or "") or p
    tint_now = _float(now.get("tint"), 0.0)

    if now["package"] != PACKAGES[mode]:
        steps.append((_line("the global theme", "plasma-apply-lookandfeel",
                            now["package"], PACKAGES[mode]),
                      partial(_run, ["plasma-apply-lookandfeel", "-a", PACKAGES[mode]]),
                      f"switch the global theme to Klassy's {mode} one "
                      f"(plasma-apply-lookandfeel) -- it rewrites the six files in "
                      f"~/.config/kdedefaults, the cursor and splash screen among them"))
        scheme_now, style_now = BASE_SCHEME[mode], BASE_STYLE[mode]
        # And then everything that apply just deleted, put back. See `OURS`: the icon theme is the
        # one that bites on an ordinary desktop, and it bit here first.
        kept = at_risk(PACKAGES[mode])
        for i, (name, group, key, value) in enumerate(kept):
            # The whole list is described once, on the first of them, because it is one decision
            # and not several -- and the rest carry no description for the same reason the second
            # half of a bounce does not.
            described = ("--- what the global theme would have taken\n+++ kwriteconfig6\n"
                         + "".join(f" {f} [{g}] {k}={v}\n" for f, g, k, v in kept)) if i == 0 else ""
            plain = ("put back what the global theme would have taken: "
                     + "; ".join(f"{k} in {f}" for f, g, k, v in kept)) if i == 0 else ""
            steps.append((described,
                          partial(_run, ["kwriteconfig6", "--file", name, "--group", group,
                                         "--key", key, "--notify", value]),
                          plain))

    if now.get("from_wallpaper"):
        # Two things choosing the accent is one too many, and the other one wins last.
        steps.append((_line("who chooses the accent", "kwriteconfig6",
                            "Plasma, from the wallpaper", "KyprX"),
                      partial(_run, ["kwriteconfig6", "--file", "kdeglobals", "--group", "General",
                                     "--key", "accentColorFromWallpaper", "--notify", "false"]),
                      "stop Plasma choosing the accent colour from the wallpaper by itself"))

    if now["accent"] != accent:
        value = accent or NO_ACCENT
        steps.append((_line("your own colour", "kwriteconfig6", now["accent"], accent),
                      partial(_run, ["kwriteconfig6", "--file", "kdeglobals", "--group", "General",
                                     "--key", "AccentColor", "--notify", value]),
                      f"your own colour: {now['accent'] or 'none'} → {accent or 'none'}"))
        if accent:
            # So the desktop's own colour page agrees about which colour was last chosen.
            steps.append(("", partial(_run, ["kwriteconfig6", "--file", "kdeglobals", "--group",
                                             "General", "--key", "LastUsedCustomAccentColor",
                                             "--notify", accent]),
                          "note it as the last colour chosen, for the desktop's own colour page"))

    target = CUSTOM if use_custom else p.scheme
    # The palette is a function of the scheme file and the accent, and the tool compares names
    # only -- so a change to either, under an unchanged name, has to go the long way round.
    restated = scheme_written or now["accent"] != accent
    if scheme_now != target:
        steps.append((_line("the colours", "plasma-apply-colorscheme", scheme_now, target),
                      partial(_run, ["plasma-apply-colorscheme", target]),
                      f"apply the colour scheme: {_scheme_words(scheme_now, p_now, tint_now)} → "
                      f"{_scheme_words(target, p, tint)} -- every application repaints, and the "
                      f"screen stops for a moment"))
    elif restated:
        # One apply instead of two. The tool compares **names** and does nothing at all when handed
        # the one already in force, so this used to go the long way round through another scheme --
        # a second full apply, a second repaint of the whole session, about four hundred
        # milliseconds of it. Writing the key to a different name first costs thirteen and buys the
        # same mismatch.
        #
        # The name written is always one that **exists**: the preset's own scheme, or the mode's
        # Breeze when that is what is being applied anyway. If the apply that follows fails, the
        # desktop is left naming a real scheme rather than one that was never there. It is written
        # without `--notify` on purpose -- nothing should repaint for a value that is about to be
        # replaced a millisecond later.
        sentinel = p.scheme if p.scheme != target else BOUNCE[mode]
        steps.append((_line("the colours", "plasma-apply-colorscheme", scheme_now, target),
                      partial(_run, ["kwriteconfig6", "--file", "kdeglobals", "--group", "General",
                                     "--key", "ColorScheme", sentinel]),
                      f"apply {_scheme_words(target, p, tint)} again, with its new colours -- "
                      f"naming {sentinel} for a moment first, because the tool skips a scheme "
                      f"that is already in force -- every application repaints, and the screen "
                      f"stops for a moment"))
        steps.append(("", partial(_run, ["plasma-apply-colorscheme", target]), ""))

    if style_now != STYLE:
        # The one style every preset wears. Its contents never change under its name -- the package
        # is a copy install.sh makes, and its colours file is empty on purpose -- so unlike the
        # scheme above there is nothing to bounce: when the name is right, the panel is.
        steps.append((_line("the panel", "plasma-apply-desktoptheme", style_now, STYLE),
                      partial(_run, ["plasma-apply-desktoptheme", STYLE]),
                      # The style being left is not named: `scripts/drive.py` reads the name of
                      # the second style this app once kept as a road opening to the panel.
                      "put the panel on KyprX's own Plasma style, which follows the colours"))
    return steps


def package_after(now: dict, wanted: dict) -> str:
    """The global theme `plan` would apply for `wanted`, or "" when it would apply none."""
    package = PACKAGES.get(str(wanted.get("mode") or ""), "")
    return package if package and now.get("package") != package else ""


def pure_package(now: dict) -> str:
    """The global theme `pure_plan` would apply, or "" when the desktop already wears it."""
    mode = now.get("mode") or ("light" if "light" in str(now.get("package")) else "dark")
    return PURE[mode] if now.get("package") != PURE[mode] else ""


def pure_plan(now: dict) -> list[tuple[str, Callable, str]]:
    """The steps that put KDE's own look back: Breeze's global theme for the mode in force, and no
    colour of this app's. Empty when the desktop already wears it.

    The package is applied the way `plan` applies Klassy's, and for the same measured reason the
    same things are put back after it: applying a global theme deletes every key it names, and the
    ones this app never meant to take -- an icon theme chosen by hand, say -- are written back. The
    five this app took over (`OURS`) are the ones Breeze now takes back, which is the point.
    """
    mode = now.get("mode") or ("light" if "light" in str(now.get("package")) else "dark")
    package = PURE[mode]
    steps: list[tuple[str, Callable, str]] = []
    if now.get("package") != package:
        steps.append((_line("the global theme", "plasma-apply-lookandfeel", now.get("package", ""),
                            package),
                      partial(_run, ["plasma-apply-lookandfeel", "-a", package]),
                      f"switch the global theme to KDE's own Breeze {mode} one "
                      f"(plasma-apply-lookandfeel) -- its colours, its panel style, its window "
                      f"decoration; it rewrites the six files in ~/.config/kdedefaults"))
        kept = at_risk(package)
        for i, (name, group, key, value) in enumerate(kept):
            described = ("--- what the global theme would have taken\n+++ kwriteconfig6\n"
                         + "".join(f" {f} [{g}] {k}={v}\n" for f, g, k, v in kept)) if i == 0 else ""
            plain = ("put back what the global theme would have taken: "
                     + "; ".join(f"{k} in {f}" for f, g, k, v in kept)) if i == 0 else ""
            steps.append((described,
                          partial(_run, ["kwriteconfig6", "--file", name, "--group", group,
                                         "--key", key, "--notify", value]),
                          plain))
    if now.get("accent"):
        steps.append((_line("your own colour", "kwriteconfig6", now["accent"], ""),
                      partial(_run, ["kwriteconfig6", "--file", "kdeglobals", "--group", "General",
                                     "--key", "AccentColor", "--notify", NO_ACCENT]),
                      f"your own colour: {now['accent']} → none"))
    return steps
