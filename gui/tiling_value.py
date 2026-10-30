"""The Tiling tab's zone layouts and arrangements: one value, which two boxes edit.

`kwinrc [Script-kyprx] arrangements` holds the zone layouts and the arrangements together, as one
JSON value whose rules are `gui/splits.py`'s. Two boxes of the tab edit it -- the Arrangements box
(`gui/arrangements_box.py`) its arrangements, and the Zone layouts box (`gui/zone_layouts_box.py`)
its zone layouts -- and `TilingValue` is that value as the window holds it: the one place either
box reads it from and hands its edits to, so that what one box changes the other shows at once,
and the page sends one text for both.

The page paints it from the daemon's answer (`load`), once per answer; asks it what to send
(`extra_changes`), tells it what was sent (`sent`), and asks it for the change in words (`said`).
Each box keeps its own selection -- an arrangement and a number of windows, a zone layout and its
zone -- and paints again whenever the value is shown anew (`shown`), whichever box made the edit.

The two kinds of question either box asks are here too (`sure`, `ask_name`), because what makes
the value busy is a question open over it, in either box. And a few words both boxes show, kept
here so the two say them the same way: a name is somebody's text, and is shown as it is spelled
wherever it appears (`plain_tip`), and never wider than a line has room for (`fitted`).

No button of either box carries a name, and one that comes to carry one needs its `&` doubled: a
button takes `&` as the mark of the letter its shortcut is on, and draws the text without it.
Measured offscreen: a button reading *Make a copy for Tom's & Jerry* asked for 9 px less than the
same words with the `&` doubled, which is the `&` gone.
"""

from __future__ import annotations

import copy
import html
import json
from contextlib import contextmanager

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QInputDialog, QMessageBox

import splits


#: Why nothing in the two boxes can be changed, shown once, at the top of the Zone layouts box.
#:
#: The daemon sends KyprX's own zone layouts and arrangements in `tiling_defaults` and its reading
#: of the file in `tiling_arrangements`, both in the version this window reads; without both, a box
#: that painted something would be painting a guess, and a guess compared with nothing would be sent
#: as a change. A daemon from before the zone layouts sends its arrangements in version 1, which
#: this window does not read (`gui/splits.py`), and that is the case this sentence is for: a new
#: window opened while the background service still runs the code from before an update, which it
#: does until it is started again -- the login does that, since the service is part of the
#: graphical session (`share/kyprd.service`). Nothing is offered meanwhile, the reset least of all:
#: taking the key away is no answer to a window that cannot read what the key holds.
UNREADABLE = ("The zone layouts and arrangements cannot be read here, so nothing in these boxes "
              "is sent. Right after an update, that is the background service still running the "
              "KyprX from before it: logging out and back in starts the new one.")

#: A value whose version is newer than this window's: shown, and left alone whole -- the reset as
#: well, which would throw away whatever the newer version added.
NEWER = ("These zone layouts and arrangements were written by a newer KyprX, so this one changes "
         "none of them and sends nothing. It tiles with its own meanwhile, which are shown here.")

#: A stored value the daemon could not read. The tiler goes on with KyprX's own, so those are what
#: is shown; the one thing offered is putting them back, which replaces what is stored.
PROBLEM = ("The zone layouts and arrangements stored on this desk cannot be read: {problem} KyprX "
           "tiles with its own meanwhile, which are shown here. Nothing else in these boxes can be "
           "changed until they are put back.")

#: What the window's line says once the reset is made.
BACK = "KyprX's zone layouts and arrangements are back"


def plain_tip(text: str) -> str:
    """A tooltip that shows a name as it is spelled.

    Qt shows a tooltip as rich text whenever the text looks like it (`Qt::mightBeRichText`), and
    takes a name as markup then. Measured offscreen: the label a tooltip is shown on is left to
    guess, takes `<b>Work</b> & Co` for rich text, and so reads it as `Work` in bold and `& Co`.
    So a tooltip that can carry a name is escaped and given as rich text on purpose, which shows
    every character as it is; a line break stays one.
    """
    if not text:
        return ""
    return "<p>" + html.escape(text, quote=False).replace("\n", "<br>") + "</p>"


#: The most room a name takes on one line of a heading, in pixels. Forty letters of
#: an ordinary name are well under it; forty of the widest -- `W`, measured in KDE's default font
#: at the window's narrowest -- are not, and one line that long cannot wrap, so the window scrolled
#: sideways for it. Past this the name ends in an ellipsis; the whole of it is in the list above.
NAME_ROOM = 360


def fitted(widget, text: str, width: int = NAME_ROOM) -> str:
    """`text` as `widget`'s font draws it in `width` pixels at most: whole when it fits, cut short
    with an ellipsis when it does not."""
    return widget.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, width)


def listed(names: list[str]) -> str:
    """`A`, `A and B`, `A, B and C`."""
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


class TilingValue(QObject):
    """The zone layouts and arrangements as both boxes edit them.

    **The baseline is the daemon's own reading, made canonical** (`splits.canonical`), and never
    the text in the file: two spellings of one value are one value, and a value compared by its
    spelling would send a change nobody made the first time the file was written by hand -- or, for
    a desk whose file is still in version 1, every time the tab was opened, since what the daemon
    sends is that file's upgrade to version 2. After a write it is the canonical text sent, which
    is the text the daemon writes, until the next reading. Nothing is offered before the first
    reading that could be trusted -- no baseline, nothing in `extra_changes` -- and a reading that
    cannot be trusted takes the baseline away again.

    **Busy** means a question or a menu of either box is open (`asking`), or a mouse button is
    down on the builder (`hold`). A question runs an event loop of its own, and the page repainting
    the boxes inside it would pull the value out from under the answer -- the same fault
    `ShortcutsTab.reload` stands down for. So the page asks `busy` first, and a paint refused for
    it is owed rather than dropped: `idle` says when to pay it. An answer applies to the value as
    it is once the question has gone, which is the daemon's latest by then, so whatever a box does
    after one checks that what it asked about is still there.

    **Putting KyprX's own back is sent at once** (`put_back`, `send_now`), not when the page's
    clock runs out. What it sends is `null`, which takes the key away, and the daemon keeps a copy
    of the desk before it does (`SetGroups`). Left on the clock, an edit made in the next moment
    would turn the `null` into the edited text, and the zone layouts and arrangements the reset
    replaced would be written over with no copy kept.
    """

    #: An edit was taken: the page starts its clock.
    changed = Signal()
    #: A value to paint, from the daemon or from an edit: both boxes paint it again. True when what
    #: their lines said may no longer be true -- an edit made since, or a reading that is not the
    #: value they showed; false for a reading of the value they show already, which is what the
    #: re-read after the page's own write is, so that a line is not gone before it can be read.
    shown = Signal(bool)
    #: Nothing of either box is open any more: a paint the page owes can be paid.
    idle = Signal()
    #: Send now: the reset is made (see the class docstring).
    send_now = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        #: The zone layouts and arrangements as edited here, normalised; None until a reading
        #: could be trusted.
        self.value: dict | None = None
        #: What the file holds, as the canonical text of the daemon's reading -- or what was sent
        #: since (`sent`).
        self.baseline = ""
        #: KyprX's own, from `tiling_defaults`, and their canonical text.
        self.defaults: dict | None = None
        self.default_text = ""
        #: Whether the file stores a value at all; nothing stored means KyprX's own.
        self.stored = False
        #: Whether the last reading could be trusted.
        self.loaded = False
        #: Why nothing in the boxes can be changed, said at the top of the Zone layouts box; ""
        #: when it can.
        self.locked = UNREADABLE
        #: Whether putting KyprX's own back is offered while locked.
        self.reset_allowed = False
        #: Set by `put_back`: what is sent is then `null`, for as long as what is shown is still
        #: KyprX's own, and until it is sent.
        self.reset = False
        self._asked = 0
        self._builders: list = []

    # ---------------------------------------------------------------- reading the daemon

    def load(self, data: dict) -> None:
        """Take the daemon's answer, and have both boxes paint it.

        Only with KyprX's own in `tiling_defaults` -- the daemon that sends them is the one that
        reads the key -- and from `tiling_arrangements`, the daemon's own reading, both in the
        version this window reads; without both, nothing here can be changed or sent
        (`UNREADABLE`).
        """
        before = (self.value, self.locked)
        self.reset = False
        defaults = data.get("tiling_defaults") or {}
        reading = data.get("tiling_arrangements") or {}
        try:
            if "arrangements" not in defaults:
                raise splits.ArrangementsError(UNREADABLE)
            shipped = defaults["arrangements"]
            default_value = (splits.parse(shipped) if isinstance(shipped, str)
                             else splits.validate(shipped))
            value = splits.validate(reading.get("value"))
        except splits.ArrangementsError:
            self.value, self.baseline, self.loaded = None, "", False
            self.defaults, self.default_text = None, ""
            self.locked, self.reset_allowed = UNREADABLE, False
            self.shown.emit((self.value, self.locked) != before)
            return
        self.value = value
        self.baseline = splits.canonical(value)
        self.defaults = default_value
        self.default_text = splits.canonical(default_value)
        self.stored = bool(reading.get("stored"))
        self.loaded = True
        problem = str(reading.get("problem") or "").strip()
        if self._newer(reading.get("value"), (data.get("tiling") or {}).get("arrangements")):
            self.locked, self.reset_allowed = NEWER, False
        elif problem:
            self.locked, self.reset_allowed = PROBLEM.format(problem=problem), True
        else:
            self.locked, self.reset_allowed = "", False
        self.shown.emit((self.value, self.locked) != before)

    @staticmethod
    def _newer(value, stored) -> bool:
        """Whether either the daemon's reading or the stored text says a version above this one's.

        Read off the stored text and not off the sentence the daemon wrote about it: words are for
        people, and change; the number is the fact.
        """
        candidates = [value]
        if isinstance(stored, str):
            try:
                candidates.append(json.loads(stored))
            except (ValueError, RecursionError):
                # Measured: a text nested a million deep stops the reader with a RecursionError,
                # which is not a ValueError; uncaught, it escapes the whole paint, band and all.
                # The daemon's reading already says what is wrong with such a text.
                pass
        for candidate in candidates:
            version = candidate.get("version") if isinstance(candidate, dict) else None
            if isinstance(version, int) and not isinstance(version, bool) \
                    and version > splits.FORMAT:
                return True
        return False

    def editable(self) -> bool:
        return self.loaded and self.value is not None and not self.locked

    # ---------------------------------------------------------------- what the page asks

    def extra_changes(self) -> dict:
        """The value to write, as its canonical text -- or `None` after `put_back`, which takes
        the key away -- and nothing when nothing changed, or when nothing here could be trusted to
        compare with."""
        if not self.editable():
            return {}
        text = splits.canonical(self.value)
        if self.reset:
            return {"tiling": {"arrangements": None if text == self.default_text else text}}
        return {"tiling": {"arrangements": text}} if text != self.baseline else {}

    def sent(self, tiling: dict) -> None:
        """The page sent `tiling` and the daemon took it: what it carried of the value is what the
        file holds now, and so the baseline -- the text sent, or, for `None`, KyprX's own with
        nothing stored. The page's re-read after a write waits while an edit is pending
        (`SettingsPage.apply`), and an edit put back meanwhile must be compared with this and not
        with the reading from before the write."""
        if "arrangements" not in tiling:
            return
        text = tiling["arrangements"]
        self.baseline = self.default_text if text is None else text
        self.stored = text is not None
        self.reset = False

    def said(self) -> str:
        """What is about to be written, in the boxes' words, for the window's line."""
        if not self.editable():
            return ""
        said: list[str] = []
        before = self.defaults if self.reset else json.loads(self.baseline)
        if self.reset:
            said.append(BACK)
        said += splits.describe(before, self.value)
        if not said:
            return ""
        return ", ".join(said[:2]) + (f" and {len(said) - 2} more" if len(said) > 2 else "")

    # ---------------------------------------------------------------- editing

    def commit(self, value, told: str = "") -> str:
        """Take an edited value: checked whole, painted by both boxes, and sent once the page's
        clock runs out.

        The answer is what the box that made the edit says in its line: `told` -- what the edit
        did besides itself -- when it is taken, the reason when it is refused, and nothing when the
        boxes are locked, which say why already. A refused value is painted all the same, so that
        a tick the edit moved goes back to what the value says.
        """
        if not self.editable() or value is None:
            return ""
        try:
            normal = splits.validate(value)
        except splits.ArrangementsError as e:
            self.shown.emit(False)
            return str(e)
        self.value = normal
        self.shown.emit(True)
        self.changed.emit()
        return told

    def reset_offered(self) -> bool:
        """Whether putting KyprX's own back would change anything, and may: while locked, only
        where the lock allows it; otherwise when what is shown is not KyprX's own, or the file
        stores a value -- KyprX's own spelt out, or in version 1 -- that it would take away."""
        if not self.loaded or self.defaults is None:
            return False
        if self.locked:
            return self.reset_allowed
        return self.value is not None and (splits.canonical(self.value) != self.default_text
                                           or (self.stored and not self.reset))

    def put_back(self) -> bool:
        """Every zone layout and arrangement replaced by KyprX's own, sent at once (the class
        docstring says why). The question is the box's to ask; this is the answer, and it applies
        to the value as it is once the question has gone."""
        if not self.reset_offered():
            return False
        self.value = copy.deepcopy(self.defaults)
        self.reset = True
        self.locked = ""
        self.shown.emit(True)
        self.changed.emit()
        self.send_now.emit()
        return True

    # ---------------------------------------------------------------- the questions

    def sure(self, parent, question: str, detail: str) -> bool:
        """Ask a Yes or No question over `parent`, busy while it is open. True when the answer was
        **no**: `No` is the default here, as everywhere in this window -- a question that goes
        away on Enter should not be one that has just thrown something away. Plain text, because
        what it asks names zone layouts and arrangements."""
        box = QMessageBox(QMessageBox.Icon.Question, question, detail,
                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, parent)
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        with self.asking():
            answer = box.exec()
        box.deleteLater()
        return answer != QMessageBox.StandardButton.Yes

    def ask_name(self, parent, title: str, label: str, text: str = "") -> str | None:
        """Ask for a name over `parent`, busy while the question is open; None when it is
        cancelled."""
        with self.asking():
            name, ok = QInputDialog.getText(parent, title, label, text=text)
        return name if ok else None

    # ---------------------------------------------------------------- busy

    def hold(self, builder) -> None:
        """Count a mouse button down on `builder` as busy, and its release as the end of it."""
        self._builders.append(builder)
        builder.released.connect(self._maybe_idle)

    def busy(self) -> bool:
        return self._asked > 0 or any(builder.held for builder in self._builders)

    @contextmanager
    def asking(self):
        """Busy for as long as the block runs -- a question or a menu is open in it."""
        self._asked += 1
        try:
            yield
        finally:
            self._asked -= 1
            self._maybe_idle()

    def _maybe_idle(self) -> None:
        if not self.busy():
            self.idle.emit()
