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

**The card is packed by arithmetic, not by a table.** Its groups are very different lengths, and
which of them to stack in which column depends on all of them at once: a table written for one set
of lengths leaves a hole beside the short columns as soon as a key is added to a group or a group
is split. So each group is built once and measured (`GroupBlock`), and `arrange` tries every way of
stacking them for the screen the card opens on -- pure arithmetic on the measurements, which is
what lets a check hold it to every way there is.
"""

from __future__ import annotations

from typing import NamedTuple

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

#: The modifier names, as a set: every one of them is drawn the width of the widest. Every row of
#: a column starts its keys at the same place (`Cheatsheet._card`), and this is what keeps them in
#: line after that: the key after `Meta Ctrl` and the one after `Meta Shift` start at one x too.
MODIFIER_LABELS = {label for _bit, label in MODIFIERS}

#: Names that arrive on the front of an action's friendly name and say only who registered it.
#: The card already groups by that.
#:
#: The old spelling stays in the list. The friendly name is whatever the registry holds, and the
#: registry keeps what the compositor script last registered — so between a rename and the next
#: time the script runs, the old prefix is still what arrives. Stripping both costs nothing and
#: is the difference between a tidy card and one showing a raw string.
NAME_PREFIXES = ("KyprX: ", "CYBE-KDE: ")


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
    """One action's keys, drawn as keys, from the left edge of the widget.

    Takes a list of sequences and separates them with a thin `/`. The card passes exactly one, the
    one the daemon's `show` names; the Shortcuts tab writes an action's keys as text (`key_text`)
    and draws none of these. Drawing from the left edge is what lets the card line a column up: a
    widget made as wide as the column's widest starts its first key where every other row does.
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
        # thirty rows and more a couple of pixels each turns into a card half a screen high.
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

#: The card's measures, each multiplied by `SCALE` once and here, because the packer below works
#: out the size of a card from them before any card is built (`arrange`), and `Cheatsheet._card`
#: then builds it with the same numbers -- one copy of each, so the two cannot drift apart.
MARGIN_H, MARGIN_V = round(30 * SCALE), round(24 * SCALE)
#: Wider between the columns than inside one, so three columns read as three lists rather than as
#: one wide table with gaps in it.
COLUMN_GAP = round(48 * SCALE)
#: One rhythm down a group: the same gap between every two rows, and a bigger one under a group's
#: name so the name belongs to what is under it.
ROW_GAP = round(5 * SCALE)
TITLE_GAP = round(6 * SCALE)
#: Between two groups sharing a column, and wider than anything inside one: this gap is the only
#: thing saying where one list ends and the next begins.
GROUP_GAP = round(22 * SCALE) + ROW_GAP
#: At least this much between the name and the keys, whatever the widths are: without it the
#: longest name in a column touches its own shortcut.
NAME_GAP = round(24 * SCALE)

#: How many columns the card is tried with, fewest first: the first whose card fits the height of
#: the screen it opens on is the one built (`arrange`). Two keep the card narrow, and on a 1920x1080
#: screen they fit; a screen with a usable height of 864 pixels -- 1080 at 125 % -- does not have
#: the room for two once a panel is there, and gets three.
COLUMN_COUNTS = (2, 3)


class Block(NamedTuple):
    """One group of the card as the packer sees it, measured once from the widgets it is made of.

    `height` is the whole group's, its name over its rows; `title` is the width of that name, and
    `name` and `keys` the widths of its widest action name and its widest row of keys. The widths
    are kept apart rather than added up, because a column draws every row's keys as wide as its
    widest (`column_width`).
    """

    height: int
    title: int
    name: int
    keys: int


def column_height(blocks: list[Block]) -> int:
    """The height of these groups stacked in one column."""
    return sum(block.height for block in blocks) + GROUP_GAP * (len(blocks) - 1)


def column_width(blocks: list[Block]) -> int:
    """The width of these groups stacked in one column: the widest name of any of them, the gap,
    and the widest keys of any of them -- every row's keys are drawn that wide, so a short name in
    one group sits beside a long key from another -- or the widest group name, when that is more."""
    return max(max(block.title for block in blocks),
               max(block.name for block in blocks) + NAME_GAP + max(block.keys for block in blocks))


def card_size(blocks: list[Block], columns) -> tuple[int, int]:
    """The card's width and height with the groups numbered in `columns` stacked so: one tuple of
    group numbers per column, top to bottom."""
    stacks = [[blocks[i] for i in column] for column in columns]
    width = (MARGIN_H * 2 + sum(column_width(stack) for stack in stacks)
             + COLUMN_GAP * (len(stacks) - 1))
    return width, MARGIN_V * 2 + max(column_height(stack) for stack in stacks)


def arrangements(count: int, n: int):
    """Every way of stacking `count` groups in `n` columns, none of them empty.

    A column keeps its groups in the order they arrive in, and the columns are in the order of
    their first group, so each way comes up once: these are the partitions of the groups into `n`
    sets, of which five groups have 15 in two columns and 25 in three. A group is never split
    across two columns -- a list that went on at the top of the next one would be read as two.
    """
    def place(columns: list[list[int]], group: int):
        if count - group < n - len(columns):        # too few groups left to fill every column
            return
        if group == count:
            yield tuple(tuple(column) for column in columns)
            return
        for column in columns:
            column.append(group)
            yield from place(columns, group + 1)
            column.pop()
        if len(columns) < n:
            columns.append([group])
            yield from place(columns, group + 1)
            columns.pop()

    yield from place([], 0)


def inversions(columns) -> int:
    """How far the card's reading order -- down the first column, then down the next -- is from
    the order the groups arrive in: the number of pairs of groups it reads the wrong way round."""
    order = [group for column in columns for group in column]
    return sum(1 for i, early in enumerate(order) for late in order[i + 1:] if early > late)


def _merit(blocks: list[Block], columns) -> tuple[int, int, int, int]:
    heights = [column_height([blocks[i] for i in column]) for column in columns]
    return (max(heights), inversions(columns), max(heights) - min(heights),
            card_size(blocks, columns)[0])


def pack(blocks: list[Block], n: int, room_width: int):
    """The best way of stacking these groups in `n` columns, as one tuple of group numbers per
    column. Pure arithmetic on the measurements, no Qt, so a check can hold it to every way there
    is (`tests/test_cheatsheet_fits.py`).

    Of the ways no wider than `room_width` -- all of them, when none is -- the one that is best by,
    in this order:

    1. **The shortest tallest column.** It is the card's height, the one thing that has to fit
       the screen. It is also the least room left empty: in `n` columns the groups and the gaps
       between them take the same height whichever way they are stacked, so what is left beside
       the shorter columns is `n` times the tallest less that.
    2. **The fewest pairs of groups read the wrong way round** (`inversions`). Among cards of one
       height the one closest to the order the daemon sends -- the Shortcuts tab's -- reads best:
       the focus keys before the resize keys, the windows' keys before KyprX's own.
    3. **The smallest difference between the tallest column and the shortest**: of the same empty
       room, the least of it in one place.
    4. **The narrowest card.**

    Measured offscreen in KDE's default font with KyprX's and the desktop's default keys: on a
    1920x1080 screen, two columns of Focus and move over Resize and arrange, and Layouts over
    Window management over KyprX, every group in the daemon's order, 738 and 803 px tall and 998
    wide. The width rule is not hypothetical: a 1440x900 screen needs three columns and has no
    room for the best three, 1484 wide, so it gets Focus and move, then Resize and arrange over
    Layouts, then Window management over KyprX, 1424 wide.
    """
    candidates = list(arrangements(len(blocks), n))
    fitting = [columns for columns in candidates
               if card_size(blocks, columns)[0] <= room_width] or candidates
    return min(fitting, key=lambda columns: _merit(blocks, columns))


def arrange(blocks: list[Block], room_width: int, room_height: int):
    """The card for a screen with this much room: packed in the fewest columns of `COLUMN_COUNTS`
    whose card fits `room_height`, or in the most when none does. Never more columns than groups.

    Measured offscreen, in the font and with the keys `pack` names: on a 1536x864 screen, the 1080
    one at 125 %, the room is 820 px and the best two columns make a card 861 tall, so it is three
    -- Focus and move over Layouts, then Resize and arrange over KyprX, then Window management, a
    card 596 px tall and 1484 wide. The tallest column decides before the order does there: the
    way that keeps every group in the daemon's order -- Focus and move alone, then Resize and
    arrange over Layouts, then Window management over KyprX -- has a column 618 px tall, 80 more
    than this one's 538, and this one reads two pairs of groups the wrong way round.
    """
    if not blocks:
        return ()
    columns = ()
    for n in COLUMN_COUNTS:
        columns = pack(blocks, min(n, len(blocks)), room_width)
        if card_size(blocks, columns)[1] <= room_height:
            break
    return columns


#: The height a Plasma panel takes by default, kept free below the card even when the screen
#: reports all of its height as available -- which is what a window on Wayland can be told.
PANEL = 44


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


class GroupBlock(QWidget):
    """One group of the card: its name in bold over one row per action, the action's name on the
    left and its keys on the right.

    Built once, and measured once (`measured`), before the card knows which column it goes in:
    which column is worked out from those measurements (`arrange`), and then the block itself is
    put there. `caps` are its keys, which the card makes as wide as the widest in the column
    (`align`).
    """

    def __init__(self, group: str, actions: list[dict], parent=None):
        super().__init__(parent)
        self.group = group
        rows = QVBoxLayout(self)
        rows.setContentsMargins(0, 0, 0, 0)
        rows.setSpacing(ROW_GAP)
        title = QLabel(group)
        font = QFont()
        font.setBold(True)
        font.setPointSizeF((font.pointSizeF() + 2) * SCALE)
        title.setFont(font)
        rows.addWidget(title)
        rows.addSpacing(TITLE_GAP)
        names: list[QLabel] = []
        self.caps: list[KeyCaps] = []
        self._lines: list[QHBoxLayout] = []
        for action in actions:
            line = QHBoxLayout()
            line.setSpacing(NAME_GAP)
            name = QLabel(action_label(action["name"]))
            name_font = QFont()
            name_font.setPointSizeF(name_font.pointSizeF() * SCALE)
            name.setFont(name_font)
            line.addWidget(name)
            line.addStretch()
            # One combination per row, not all of them. An action can carry several — KRunner
            # carries three — and a card that printed every one would be wider and less readable
            # than the thing it is helping you remember. Which one is shown is chosen on the
            # Shortcuts tab; `show` is the daemon's answer, resolved.
            shown = action.get("show") or (action["keys"][0] if action["keys"] else [])
            caps = KeyCaps([shown] if shown else [])
            line.addWidget(caps)
            rows.addLayout(line)
            names.append(name)
            self.caps.append(caps)
            self._lines.append(line)
        self.measured = Block(
            height=self.sizeHint().height(), title=title.sizeHint().width(),
            name=max((name.sizeHint().width() for name in names), default=0),
            keys=max((caps.sizeHint().width() for caps in self.caps), default=0))

    def align(self, width: int) -> None:
        """Every row's keys drawn `width` wide, so they start where the rest of the column's do.

        Every layout of the block is told, because none of them hears it otherwise before the
        window is shown: a widget that has not been shown yet tells no layout its size changed
        (`QWidget::updateGeometry` stops at a hidden widget), and a layout keeps the size it worked
        out first until it is told. Left untold, the rows report the widths measured before this,
        the window is fixed at the size they add up to (`Cheatsheet`), and the columns are
        squeezed into it: measured offscreen on a 1920x1080 screen, a card 115 px narrower than
        its columns, with the longest name in it cut off.
        """
        for caps in self.caps:
            caps.setFixedWidth(width)
        for line in self._lines:
            line.invalidate()
        self.layout().invalidate()


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

    **Its columns come from the screen it opens on**, the way the picker's size does: the screen
    the daemon names in the `Shortcuts` answer (`screen`), or Qt's primary one when it names none
    this window knows. Each group is built once (`GroupBlock`) and measured, and `arrange` stacks
    the groups in the fewest columns whose card fits that screen's height with a panel on it, in
    the stacking with the shortest tallest column that fits its width (`pack` says how it
    chooses). `room` stands in for the screen, for a check that has to know the card fits a screen
    it is not running on.
    """

    def __init__(self, client, room: QSize | None = None):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle(TITLE)

        data = client.shortcuts() or {}
        screen = self._target_screen(str(data.get("screen") or ""))
        if screen is not None:
            self.setScreen(screen)
        self.room = room if room is not None else self._room(screen)

        groups: dict[str, list] = {}
        for action in data.get("actions") or []:
            groups.setdefault(action["group"], []).append(action)
        blocks = [GroupBlock(group, actions) for group, actions in groups.items()]
        chosen = arrange([block.measured for block in blocks],
                         self.room.width(), self.room.height())
        stacks = [[blocks[i] for i in column] for column in chosen]
        #: How many columns the card was built with, which groups are in each, top to bottom, and
        #: how tall each column is as `arrange` worked it out -- for whoever needs to know what
        #: fitted, and for the check that holds the built card to that arithmetic.
        self.columns = len(stacks)
        self.arranged = [[block.group for block in stack] for stack in stacks]
        self.heights = [column_height([block.measured for block in stack]) for stack in stacks]
        card = self._card(stacks, card_style(card_look(client, see_through=True)))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)
        self.setFixedSize(self.sizeHint())

    @staticmethod
    def _target_screen(name: str):
        """The `QScreen` the daemon named, or Qt's primary screen -- offscreen, where the one
        screen has no name, or with no compositor to ask. The picker's rule, `_target_screen`."""
        for screen in QGuiApplication.screens():
            if name and screen.name() == name:
                return screen
        return QGuiApplication.primaryScreen()

    @staticmethod
    def _room(screen) -> QSize:
        """What the card may take of that screen: what it says is available, and never the height
        a panel takes."""
        if screen is None:
            return QSize(1600, 900 - PANEL)
        available, whole = screen.availableGeometry(), screen.geometry()
        return QSize(available.width(), min(available.height(), whole.height() - PANEL))

    @staticmethod
    def _card(stacks: list[list[GroupBlock]], style: str) -> QWidget:
        """The card itself, with these groups stacked in these columns."""
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(style)
        grid = QHBoxLayout(card)
        grid.setContentsMargins(MARGIN_H, MARGIN_V, MARGIN_H, MARGIN_V)
        grid.setSpacing(COLUMN_GAP)
        for stack in stacks:
            column = QVBoxLayout()
            column.setSpacing(GROUP_GAP)
            # Every row's keys as wide as the widest in the column, so each row's first key starts
            # at one x down the whole column, across the groups stacked in it too. The keys follow
            # a stretch, so a row's keys end at the column's edge; left to its own width, a row
            # starts its keys wherever its own last key puts its first. Measured in KDE's default
            # font, the eight resize keys alone are 105, 107, 174 and 243 px wide -- Meta+F,
            # Meta+Return, Meta+Shift+O, Meta+Ctrl+Shift+H -- which put `Meta` at four places.
            # Equal modifier widths only line up rows with as many keys as each other
            # (`MODIFIER_LABELS`).
            widest = max(block.measured.keys for block in stack)
            for block in stack:
                block.align(widest)
                column.addWidget(block)
            column.addStretch()
            grid.addLayout(column)
        card.ensurePolished()
        return card

    def keyPressEvent(self, event):  # noqa: N802 — Qt's spelling
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.close()

    def mousePressEvent(self, event):  # noqa: N802
        self.close()

    def focusOutEvent(self, event):  # noqa: N802
        self.close()
