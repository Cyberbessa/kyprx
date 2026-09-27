"""The overlay the shortcut key opens, and the little keys it is made of.

Kept apart from the rest of the interface because it shares almost nothing with it: no settings
form, no daemon writes, one read and a window. What it does have is drawing code, and drawing code
grows.

**A shortcut is taken apart by arithmetic, not by splitting text.** The compositor hands over a
single integer in which the modifiers are bits, so `Meta+Alt+;` comes apart into `Meta`, `Alt`
and `;` with nothing to guess at. Splitting the printed form on `+` is the obvious alternative and
it is wrong exactly where it matters: `+`, `;` and `[` are keys, and three of the shortcuts on this
desktop use them.

**The keys are drawn, not written.** A rounded face with a lighter top, a darker edge and a shadow
underneath is what makes a label read as a key rather than as a word in a box, and it costs one
function. Nothing here depends on an icon theme or on a font carrying symbols nobody guarantees —
the arrows are the only glyphs used, and they exist everywhere.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetrics, QGuiApplication,
                           QLinearGradient, QPainter, QPalette, QPen)
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

#: How much bigger than the old card. One number, so the whole thing grows together rather than
#: drifting apart one padding at a time.
SCALE = 1.2

#: Qt's modifier bits, in the order a keyboard is usually described. Everything below 0x02000000
#: is the key itself.
MODIFIERS = ((0x10000000, "Meta"), (0x04000000, "Ctrl"), (0x08000000, "Alt"), (0x02000000, "Shift"))
KEY_MASK = 0x01ffffff

#: Keys worth a glyph. Arrows read faster than their names at this size, and `Pg↑`/`Pg↓` keep the
#: pairing with them visible. Everything else keeps the name the desktop prints.
#:
#: **Tab is spelled out.** Its glyph, `⇥`, is an arrow among four other arrows on this card, and
#: three of the rows here use it -- so the one key that is not a direction was drawn as one.
GLYPHS = {"Up": "↑", "Down": "↓", "Left": "←", "Right": "→",
          "PgUp": "Pg↑", "PgDown": "Pg↓", "Tab": "TAB", "Return": "↵", "Enter": "↵",
          "Backspace": "⌫", "Del": "⌦"}

#: The modifier names, as a set: every one of them is drawn the width of the widest, so the keys
#: line up in columns down the card instead of each row starting wherever its own text ends.
MODIFIER_LABELS = {label for _bit, label in MODIFIERS}

#: Names that arrive on the front of an action's friendly name and say only who registered it.
#: The card already groups by that.
#:
#: The old spelling stays in the list. The friendly name is whatever the registry holds, and the
#: registry keeps what the compositor script last registered — so between a rename and the next
#: time the script runs, the old prefix is still what arrives. Stripping both costs nothing and
#: is the difference between a tidy card and one showing a raw string.
NAME_PREFIXES = ("Krohnkite: ", "KyprX: ", "CYBE-KDE: ")


def action_label(name: str) -> str:
    """An action's name without whoever registered it in front, and starting with a capital.

    The capital is the only thing this changes about the name itself, and only the first letter:
    this app's own three actions are registered in lower case where every other name on the card
    is not, and `str.title()` would turn *KRunner* into *Krunner*.
    """
    for prefix in NAME_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name[:1].upper() + name[1:]


def key_caps(combined: int) -> list[str]:
    """One key sequence step, as the keys you actually press."""
    from PySide6.QtGui import QKeySequence

    caps = [label for bit, label in MODIFIERS if combined & bit]
    key = combined & KEY_MASK
    if key:
        name = QKeySequence(key).toString()
        caps.append(GLYPHS.get(name, name))
    return caps


def key_text(keys: list[int]) -> str:
    """The same sequence as text, for the places that are a table rather than a picture."""
    from PySide6.QtGui import QKeySequence

    return QKeySequence(*keys[:4]).toString() if keys else ""


class KeyCaps(QWidget):
    """One action's keys, drawn as keys.

    Takes a list of sequences and separates them with a thin `/`, which is what it is for: the
    card passes exactly one, but the Shortcuts tab's row label shows everything an action carries.
    """

    def __init__(self, sequences: list[list[int]], scale: float = SCALE, parent=None):
        super().__init__(parent)
        self.scale = scale
        self.tokens: list[tuple[str, str]] = []
        for index, sequence in enumerate(sequences):
            if index:
                self.tokens.append(("sep", "/"))
            for step in sequence[:1]:           # a second step is vanishingly rare; show the first
                self.tokens.extend(("cap", cap) for cap in key_caps(step))
        if not self.tokens:
            self.tokens = [("sep", "not bound")]

        self.font = QFont()
        self.font.setPointSizeF(self.font.pointSizeF() * scale)
        self.font.setBold(True)
        self._metrics = QFontMetrics(self.font)
        # Tight on the vertical: a key is taller than the line of text it replaces, and with
        # twenty-five rows a couple of pixels each turns into a card half a screen high.
        self.pad_h = round(9 * scale)
        self.pad_v = round(4 * scale)
        self.gap = round(5 * scale)
        #: Every modifier is drawn this wide, whichever one it is. Without it `Meta Alt ↑` and
        #: `Meta Shift ↑` put their arrow in two different places, and a column of shortcuts that
        #: differ by one modifier reads as a ragged edge rather than as a column.
        self._modifier_width = max(self._metrics.horizontalAdvance(label)
                                   for label in MODIFIER_LABELS) + self.pad_h * 2
        self.depth = 2
        self.radius = 5 * scale
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(),
                           self.sizePolicy().verticalPolicy())

    # ---------------------------------------------------------------- geometry

    def _width(self, kind: str, text: str) -> float:
        if kind == "sep":
            return self._metrics.horizontalAdvance(text) + self.gap
        floor = self._modifier_width if text in MODIFIER_LABELS else 30 * self.scale
        return max(self._metrics.horizontalAdvance(text) + self.pad_h * 2, floor)

    def _cap_height(self) -> float:
        return self._metrics.height() + self.pad_v * 2

    def sizeHint(self) -> QSize:
        width = sum(self._width(k, t) for k, t in self.tokens) + self.gap * (len(self.tokens) - 1)
        return QSize(round(width), round(self._cap_height() + self.depth))

    # ---------------------------------------------------------------- painting

    def paintEvent(self, event):  # noqa: N802 — Qt's spelling
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.font)

        text_colour = self.palette().windowText().color()
        face = self.palette().window().color()
        # A key has to stand off its background whichever way round the theme is.
        face = face.lighter(160) if face.lightness() < 128 else face.darker(112)
        edge = face.lighter(135) if face.lightness() < 128 else face.darker(125)
        shadow = QColor(0, 0, 0, 90)

        x = 0.0
        height = self._cap_height()
        for kind, text in self.tokens:
            width = self._width(kind, text)
            if kind == "sep":
                painter.setPen(QPen(text_colour.darker(150)))
                painter.drawText(QRectF(x, 0, width, height),
                                 Qt.AlignmentFlag.AlignCenter, text)
                x += width + self.gap
                continue
            body = QRectF(x, 0, width, height)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(shadow)
            painter.drawRoundedRect(body.translated(0, self.depth), self.radius, self.radius)
            gradient = QLinearGradient(body.topLeft(), body.bottomLeft())
            gradient.setColorAt(0.0, face.lighter(118))
            gradient.setColorAt(1.0, face)
            painter.setBrush(QBrush(gradient))
            painter.setPen(QPen(edge, 1))
            painter.drawRoundedRect(body, self.radius, self.radius)
            painter.setPen(QPen(text_colour))
            painter.drawText(body, Qt.AlignmentFlag.AlignCenter, text)
            x += width + self.gap
        painter.end()


#: What an overlay falls back to when neither the decoration's config nor its own schema says.
#: These are the decoration's own shipped numbers rather than anything chosen here, so that even
#: the last resort is its answer and not an invention. There is deliberately no colour: a colour
#: invented here is one that looks right on the theme it was invented under and wrong on the rest.
CARD_FALLBACK = {"radius": 4.0, "thickness": 1.0}

#: Klassy's outline styles, and where each one's colour comes from. Taken from its own schema,
#: `/usr/share/config.kcfg/klassy-decoration.kcfg`, including the fact that **each style has an
#: opacity key of its own** -- there is no one "outline opacity".
#:
#: Only two of the seven name a colour. Two more name the accent, which the toolkit already knows.
#: The last two, Contrast and Shadow, Klassy derives against the title bar with a formula it does
#: not publish and does not expose -- `org.kde.Klassy.Style` is not even a name on the bus, it only
#: receives signals, and the cache it rebuilds lives inside the compositor. So those two are
#: **approximated**, which is worth saying out loud rather than discovering later.
#:
#: `role` is what to ask the palette for; `key` is a colour to read from config; `alpha` is the
#: opacity key. A style missing from here draws nothing.
OUTLINE_STYLES = {
    "WindowOutlineNone": None,
    "WindowOutlineCustomColor": {"key": "WindowOutlineCustomColorActive",
                                 "alpha": "WindowOutlineCustomColorOpacityActive"},
    "WindowOutlineCustomWithContrast": {"key": "WindowOutlineCustomColorActive",
                                        "alpha": "WindowOutlineCustomWithContrastOpacityActive"},
    "WindowOutlineAccentColor": {"role": QPalette.ColorRole.Highlight,
                                 "alpha": "WindowOutlineAccentColorOpacityActive"},
    "WindowOutlineAccentWithContrast": {"role": QPalette.ColorRole.Highlight,
                                        "alpha": "WindowOutlineAccentWithContrastOpacityActive"},
    # Approximated. Klassy takes this one from the colour scheme too -- its
    # `WindowOutlineContrastFromColorScheme` defaults to true -- so the theme's own text colour is
    # the closest thing here that moves when the theme does.
    "WindowOutlineContrast": {"role": QPalette.ColorRole.WindowText,
                              "alpha": "WindowOutlineContrastOpacityActive"},
    # Approximated, and the least of a guess of the three: a shadow is black.
    "WindowOutlineShadowColor": {"colour": QColor(0, 0, 0),
                                 "alpha": "WindowOutlineShadowColorOpacity"},
}

#: What Klassy uses when the file says nothing about the style. From the same schema.
DEFAULT_OUTLINE_STYLE = "WindowOutlineContrast"

#: The overlay's title. The compositor is told where to put this window by matching on it, and the
#: tiler is told to leave it alone by matching on it — so the daemon holds the same string, and the
#: two must not drift.
TITLE = "KyprX shortcuts"

#: How the groups are arranged: one entry per column, naming the groups stacked in it top to
#: bottom. Two columns and not one per group, because the three groups are three very different
#: lengths -- the tiling one is five times the last -- and a column per group makes the card as
#: tall as the longest and as wide as three, with the difference left as a hole in the corner.
#: Stacked, the two short ones together come to about the length of the long one.
#:
#: A group this does not name keeps a column of its own at the end, so a group added to
#: `daemon/shortcuts.py` appears rather than disappearing.
COLUMNS = (("Tiling",), ("Window management", "KyprX"))


def _rgb(text) -> QColor | None:
    """Klassy's `r,g,b`, whichever way it was spaced.

    The spacing is not hypothetical: the config on this desktop holds `255,152,8` and the schema's
    own default holds `0, 0, 0`. A parser that splits and does not strip reads one of the two.
    """
    parts = [p.strip() for p in str(text).split(",")]
    if len(parts) != 3:
        return None
    try:
        return QColor(*(int(p) for p in parts))
    except ValueError:
        return None


def _percent(text, fallback: int = 100) -> int:
    try:
        return max(0, min(100, round(float(text))))
    except (TypeError, ValueError):
        return fallback


def card_look(client, see_through: bool = False) -> dict:
    """An overlay's corner and border, taken from the decoration rather than invented here.

    The point is that these windows look like the others. Their corner is the window corner
    radius, their border the window outline — same thickness, same colour. Hard-coding them
    happened to match once and would have drifted the first time either was changed.

    **The style is read before the colour, and that was the bug.** This used to go straight to
    `WindowOutlineCustomColorActive`, which is only one of seven answers and is a stale leftover
    under the other six. So an overlay went on painting a custom orange while every real window's
    outline had become the accent colour, or had gone. Which of the seven is in force is
    `WindowOutlineStyleActive`, and everything else follows from it — including the opacity, of
    which there is one key per style rather than one overall.

    Two things are not reproduced. `ColorizeWindowOutlineWithButton` is not read at all, because
    the real outline takes the colour of the button under the pointer and there is no window button
    here to point at. And the exact Contrast and Shadow shades, for the reason in `OUTLINE_STYLES`.

    On the module rather than on the class because there are two overlays now, and reaching into a
    class to borrow a static method is how the second one ends up with its own copy.
    """
    groups = client.groups() or {}
    live = groups.get("klassy") or {}
    # The decoration's own schema, which already travels in the same reply. Falling straight to a
    # constant here is what made a key somebody had reset read as this app's invention rather than
    # as the decoration's default.
    shipped = groups.get("klassy_defaults") or {}

    def setting(group: str, key: str, fallback=""):
        for source in ((live.get(group) or {}), (shipped.get(group) or {})):
            value = source.get(key)
            if value not in (None, ""):
                return value
        return fallback

    def number(group: str, key: str, fallback: float) -> float:
        try:
            return float(setting(group, key, fallback))
        except (TypeError, ValueError):
            return fallback

    look = {
        "radius": number("Windeco", "WindowCornerRadius", CARD_FALLBACK["radius"]),
        "thickness": number("WindowOutlineStyle", "WindowOutlineThickness",
                            CARD_FALLBACK["thickness"]),
        "colour": QColor(0, 0, 0, 0),
        # How see-through the card is, asked for rather than assumed. The number is the one on the
        # Appearance tab -- the same one every window this app manages is drawn at -- so an overlay
        # that wants to look like the rest of the desk is drawn like the rest of the desk, and
        # moving that control moves this with it.
        #
        # The picker asks for none of it and is pinned fully opaque besides: it shows pictures, and
        # a picture with the desktop mixed into it is a picture that lies about what you are
        # choosing.
        "opacity": _percent((client.settings() or {}).get("transparency"), 100) if see_through
                   else 100,
    }
    style = str(setting("WindowOutlineStyle", "WindowOutlineStyleActive",
                        DEFAULT_OUTLINE_STYLE))
    recipe = OUTLINE_STYLES.get(style, OUTLINE_STYLES[DEFAULT_OUTLINE_STYLE])
    if recipe is None:
        look["thickness"] = 0.0          # the outline is off, so the overlay has none either
        return look

    palette = QGuiApplication.palette()
    if "role" in recipe:
        colour = QColor(palette.color(recipe["role"]))
    elif "colour" in recipe:
        colour = QColor(recipe["colour"])
    else:
        colour = _rgb(setting("WindowOutlineStyle", recipe["key"]))
    if colour is None:
        colour = QColor(palette.color(QPalette.ColorRole.WindowText))
    colour.setAlpha(round(_percent(setting("WindowOutlineStyle", recipe["alpha"])) * 255 / 100))
    look["colour"] = colour
    return look


def card_style(look: dict, name: str = "card") -> str:
    """The stylesheet that turns a plain widget into one of those cards.

    The background is spelled out rather than left as `palette(window)`, because it may carry an
    alpha: a card the desktop shows through is what makes the compositor's blur visible behind it,
    and blur painted behind an opaque window is work nobody sees. The text and the keys are painted
    on top of it and stay solid -- it is the card that is see-through, not what is written on it.
    """
    colour = look["colour"]
    border = "none" if look["thickness"] <= 0 else (
        f"{look['thickness']:g}px solid "
        f"rgba({colour.red()},{colour.green()},{colour.blue()},{colour.alphaF():.3f})")
    window = QGuiApplication.palette().window().color()
    background = (f"rgba({window.red()},{window.green()},{window.blue()},"
                  f"{look.get('opacity', 100) / 100:.3f})")
    return (f"#{name} {{ background: {background}; border: {border}; "
            f"border-radius: {look['radius']:g}px; }}")


class Cheatsheet(QWidget):
    """The shortcut list as an overlay, laid out to be read at a glance.

    Two things about the window itself, both of which took measuring.

    **It is fixed size, and that is what makes it float.** A list of shortcuts has one right size,
    so this costs nothing — and a window the compositor cannot resize is one the tiler will not
    tile. That matters because the obvious lever does not work: this is declared a dialog, and on
    Wayland a dialog is not a dialog to the compositor. The window type never reaches it, so the
    tiler's "float dialogs" setting never sees this window.

    **It cannot place itself.** A Wayland client has no call for positioning its own top-level, and
    the toolkit discards the coordinates outright. Centring is a window rule the daemon keeps; see
    `daemon/rules.py:overlay_placement`.
    """

    def __init__(self, client):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle(TITLE)

        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(card_style(card_look(client, see_through=True)))
        grid = QHBoxLayout(card)
        margin_h, margin_v = round(30 * SCALE), round(24 * SCALE)
        grid.setContentsMargins(margin_h, margin_v, margin_h, margin_v)
        #: Wider between the columns than inside one, so three columns read as three lists rather
        #: than as one wide table with gaps in it.
        grid.setSpacing(round(48 * SCALE))

        groups: dict[str, list] = {}
        for action in client.shortcuts().get("actions") or []:
            groups.setdefault(action["group"], []).append(action)

        named = {group for column in COLUMNS for group in column}
        arranged = [[group for group in column if group in groups] for column in COLUMNS]
        arranged += [[group] for group in groups if group not in named]

        for stacked in arranged:
            if not stacked:
                continue
            column = QVBoxLayout()
            #: One rhythm down the card: the same gap between every two rows, and a bigger one
            #: under a group's name so the name belongs to what is under it.
            column.setSpacing(round(5 * SCALE))
            for index, group in enumerate(stacked):
                if index:
                    #: Between two groups sharing a column, and wider than anything inside one:
                    #: this gap is the only thing saying where one list ends and the next begins.
                    column.addSpacing(round(22 * SCALE))
                title = QLabel(group)
                font = QFont()
                font.setBold(True)
                font.setPointSizeF((font.pointSizeF() + 2) * SCALE)
                title.setFont(font)
                column.addWidget(title)
                column.addSpacing(round(6 * SCALE))
                for action in groups[group]:
                    line = QHBoxLayout()
                    #: At least this much between the name and the keys, whatever the widths are:
                    #: without it the longest name in a column touches its own shortcut.
                    line.setSpacing(round(24 * SCALE))
                    name = QLabel(action_label(action["name"]))
                    name_font = QFont()
                    name_font.setPointSizeF(name_font.pointSizeF() * SCALE)
                    name.setFont(name_font)
                    line.addWidget(name)
                    line.addStretch()
                    # One combination per row, not all of them. An action can carry several —
                    # KRunner carries three — and a card that printed every one would be wider and
                    # less readable than the thing it is helping you remember. Which one is shown
                    # is chosen on the Shortcuts tab; `show` is the daemon's answer, resolved.
                    shown = action.get("show") or (action["keys"][0] if action["keys"] else [])
                    line.addWidget(KeyCaps([shown] if shown else []))
                    column.addLayout(line)
            column.addStretch()
            grid.addLayout(column)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)
        self.setFixedSize(self.sizeHint())

    def keyPressEvent(self, event):  # noqa: N802 — Qt's spelling
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.close()

    def mousePressEvent(self, event):  # noqa: N802
        self.close()

    def focusOutEvent(self, event):  # noqa: N802
        self.close()
