"""The form the Appearance, Effects and Tiling tabs are made of: fields drawn from `gui/fields.py`,
read from the daemon, and written back by themselves a moment after they change.

`SettingsPage` draws a page of `Field`s in sections, paints what each key reads as now -- the file's
value, or what its program ships, with the dot that says nothing has been written -- and sends only
the keys that changed, once the edits stop. Its subclasses add what one tab needs through `_load`,
`extra_changes` and `after`; `PluginPage` is the Effects tab's kind, a page whose subject -- a
plugin of the compositor -- can be switched off entirely.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QFormLayout, QLabel, QLineEdit, QScrollArea, QVBoxLayout,
                               QWidget)

from client import Client
from fields import Field
from widgets import (SECTION_HINTS, Choice, ColorButton, DoubleSpin, FieldLabel, Section, Spin,
                     unavailable, warning)


#: The entry a menu grows when there is no default to fall back on either — the setting is not in
#: the file and nothing tells this app what applies. Rare now, and honest where it happens.
UNKNOWN = "(not set)"


# ---------------------------------------------------------------------- generic form

class SettingsPage(QWidget):
    """A page of grouped fields that writes what changed, by itself, shortly after it changes.

    Reporting only the changed keys matters: writing a whole group every time would fill the
    config with keys nobody touched, and make every save look like a large change.

    **There is no Apply button any more, on any page.** Every other control in this window already
    wrote the moment it was touched -- the colours, the window table, the shortcuts, the wallpaper,
    the three controls above the tabs -- so a form that waited for a click was the odd one out, and
    a page left touched and never applied stayed stale for the rest of the session, because `load`
    refuses to repaint while anything on it is touched.

    What replaces the click is a pause. Every edit restarts a timer, and the write happens when the
    edits stop, so a drag along a spin box and a run through a menu are one write and not twenty.
    Two guards make that safe rather than merely quick, and both are in the controls this class
    builds, from `gui/widgets.py`: a number is read when it settles rather than as it is typed
    (`Spin`), and no control here can be changed by a wheel rolling past it (`NoWheel`).
    """

    #: Long enough for a sequence of edits to count as one, short enough that the window still
    #: answers. Deliberately well under the three seconds `scripts/simulate.sh` gives each tab
    #: before it kills it: a timer that has not fired by then is a write that check cannot see.
    DELAY = 700

    #: What the footer should say. The window owns that line; a page tells it what happened -- the
    #: same road `WindowsTab.copied` and `TopStrip.says` take.
    says = Signal(str)

    #: Which page in `daemon/defaults.py` this form is responsible for — the settings that used
    #: to be controls here and are now fixed. The values are never carried by the interface: a
    #: setting with no control has nothing to read a value back from, so the write sends the page's
    #: name and the daemon looks up what it means. Empty for a form that enforces nothing.
    enforces: str = ""

    def __init__(self, sections: list[tuple[str, list[Field]]], client: Client, parent=None):
        super().__init__(parent)
        self.c = client
        #: Set across the whole of a load, subclasses included, and checked by `queue`. It is what
        #: stops a page writing while it is being painted from the daemon's answer -- which is the
        #: one thing `scripts/simulate.sh` exists to catch, and which two of these pages were safe
        #: from only because nothing was connected to the widgets they paint by hand.
        self._loading = False
        self._pending = QTimer(self)
        self._pending.setSingleShot(True)
        self._pending.setInterval(self.DELAY)
        self._pending.timeout.connect(self.apply)
        self.fields: dict[tuple[str, str, str], Field] = {}
        self.widgets: dict[tuple[str, str, str], QWidget] = {}
        self.labels: dict[tuple[str, str, str], QLabel] = {}
        #: The whole label column of a row: the dot that says nothing has been written for this
        #: setting, and the name. `labels` is still the name alone, which is what everything else
        #: here reads and writes.
        self.rows: dict[tuple[str, str, str], FieldLabel] = {}
        self.originals: dict[tuple[str, str, str], str] = {}
        #: Only what someone actually touched is ever written. A widget showing a value for a key
        #: that is not in the file is showing a guess, and a guess must not become a setting.
        self.touched: set[tuple[str, str, str]] = set()
        self.extra_top = QVBoxLayout()
        self.extra_bottom = QVBoxLayout()
        #: Kept so a page can add a row to a section it did not define, which is how a note or a
        #: button ends up beside the control it belongs to instead of in a box of its own.
        self.section_forms: dict[str, QFormLayout] = {}
        #: Which section each field sits in, for a page that has to reach every control in one --
        #: a switch that governs a whole subject, say.
        self.section_of: dict[tuple[str, str, str], str] = {}
        #: The boxes themselves. `extra_top` and `extra_bottom` put something above or below all of
        #: them; `after` puts something **between** two, which the Tiling tab needs for a box it
        #: can only build once the daemon has said which layouts there are.
        self.section_boxes: dict[str, Section] = {}

        body = QWidget()
        column = self.column = QVBoxLayout(body)
        column.addLayout(self.extra_top)
        for title, fields in sections:
            box = Section(title, SECTION_HINTS.get(title, ""))
            self.section_boxes[title] = box
            form = QFormLayout(box)
            self.section_forms[title] = form
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
            for f in fields:
                ident = (f.source, f.group, f.key)
                self.fields[ident] = f
                self.section_of[ident] = title
                w = self._widget(f)
                self.widgets[ident] = w
                row = FieldLabel(f.label)
                self.rows[ident] = row
                label = row.label
                self.labels[ident] = label
                if f.hint:
                    label.setToolTip(f.hint)
                    w.setToolTip(f.hint)
                self._watch(ident, w)
                form.addRow(row, w)
            column.addWidget(box)
        column.addLayout(self.extra_bottom)
        column.addStretch()

        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(body)
        # No frame and no focus, the way the picker's own strip is set up. The widget style paints
        # a scroll area's frame in the theme's *focus* colour while it has focus and in the hover
        # colour while the pointer is over it -- and this one is the first tab-focusable widget on
        # every page, because `setWidget` above reparents the whole content behind it, so a tab
        # opened from the keyboard lit up a coloured rectangle round everything in it. The wheel
        # still scrolls: Qt hands it to whatever is under the pointer, focus or no focus.
        area.setFrameShape(QScrollArea.Shape.NoFrame)
        area.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout = QVBoxLayout(self)
        layout.addWidget(area)

    def after(self, title: str, widget: QWidget) -> None:
        """Put a widget straight after the named section, in the column the sections are stacked
        in. For a box that cannot be a section because its rows are not known until the daemon
        answers -- the layouts in the rotation, which the tiler names."""
        box = self.section_boxes.get(title)
        at = self.column.indexOf(box) + 1 if box is not None else self.column.count() - 1
        self.column.insertWidget(at, widget)

    def _watch(self, ident, w: QWidget) -> None:
        """Mark the field as touched, and start the clock.

        The two are not the same signal for a text field. `textEdited` marks it -- which is what
        stops the daemon repainting the box under somebody's fingers -- but the write waits for
        `editingFinished`, on Enter or on the focus leaving. A debounce over a keystroke signal
        would put `firef` in the never-tiled list and re-tile the screen to prove it.
        """
        mark = lambda *_: self.touched.add(ident)          # noqa: E731
        for signal in ("toggled", "valueChanged", "currentIndexChanged", "textEdited"):
            if hasattr(w, signal):
                getattr(w, signal).connect(mark)
        if isinstance(w, QLineEdit):
            w.editingFinished.connect(self.queue)
        else:
            for signal in ("toggled", "valueChanged", "currentIndexChanged"):
                if hasattr(w, signal):
                    getattr(w, signal).connect(self.queue)
        if isinstance(w, ColorButton):
            w.picked.connect(mark)
            w.picked.connect(self.queue)

    def queue(self, *_) -> None:
        """Something changed. Write it when the changing stops."""
        if self._loading:
            return
        self._pending.start()

    def flush(self) -> None:
        """Send whatever is waiting, now. The window calls this on the way out of the tab and on
        the way out of the window: a change somebody made and then walked away from is still a
        change they made."""
        if self._pending.isActive():
            self._pending.stop()
            self.apply()

    @staticmethod
    def _widget(f: Field) -> QWidget:
        if f.kind == "bool":
            return QCheckBox()
        if f.kind == "int":
            w = Spin()
            w.setRange(int(f.low), int(f.high))
            w.setSuffix(f.suffix)
            w.setMaximumWidth(140)
            return w
        if f.kind == "float":
            w = DoubleSpin()
            w.setRange(f.low, f.high)
            w.setSingleStep(f.step)
            w.setSuffix(f.suffix)
            w.setDecimals(2)
            w.setMaximumWidth(140)
            return w
        if f.kind == "choice":
            w = Choice()
            for value, label in f.choices:
                w.addItem(label, value)
            w.setMaximumWidth(280)
            return w
        if f.kind == "color":
            return ColorButton(f.label)
        if f.kind == "list":
            w = QLineEdit()
            w.setPlaceholderText("comma separated")
            return w
        return QLineEdit()

    def load(self, data: dict) -> None:
        """Repaint every widget from the config.

        Refuses while something is waiting to be applied. A settings page is a form: repainting it
        under someone's hands throws their edit away, and the daemon has every reason to say
        "something changed" several times a minute.

        **A widget for a key the file does not carry shows that key's real default**, which is not
        a nicety. When the defaults were missing, every unset switch was drawn off — including the
        ones that ship on — and `originals` recorded that false reading. Touching such a switch and
        putting it back then counted as a change and wrote the false value to the file. That is how
        one decoration setting ended up inverted in a config nobody meant to edit, and it is why
        `changes()` can trust `originals` now.

        **The flag is the point of the wrapper.** Every page here paints some widget of its own on
        top of what `_paint` does -- the two plugin switches, the twelve layout numbers -- and none
        of those is in `fields`, so the `touched` refusal never covered them. With everything
        applying by itself they would each write on the way up, which is the one defect
        `scripts/simulate.sh` was built to catch. Subclasses override `_load`, inside the flag.
        """
        if self.touched or self._pending.isActive():
            return
        self._loading = True
        try:
            self._load(data)
        finally:
            self._loading = False

    def _load(self, data: dict) -> None:
        for ident, f in self.fields.items():
            self._paint(ident, f, data)

    def refresh(self, data: dict, idents) -> None:
        """Repaint a few named fields, and leave the rest of the form exactly as it is.

        For the one thing `load` cannot do. Another part of this window makes the daemon write a
        key this page has a control for -- the window outline's colour, which a wallpaper moves --
        while the page is on screen; `load` refuses wholesale as long as anything here is touched,
        which is right for a form somebody is filling in and leaves that swatch showing a colour
        the file stopped holding, and the next write would put that stale value back.

        A field somebody has touched is never repainted, on the same reasoning: that value is
        theirs until it is written or they leave. It may then be written again over an identical value,
        which costs nothing -- a transaction with no change returns before it reloads anything.
        """
        for ident in idents:
            if ident in self.fields and ident not in self.touched:
                self._paint(ident, self.fields[ident], data)

    def _paint(self, ident, f: Field, data: dict) -> None:
        """One field, painted from the daemon's answer, and its `originals` entry with it."""
        source, group, key = ident
        bucket = data.get(source) or {}
        defaults = data.get(f"{source}_defaults") or {}
        if group:
            bucket = bucket.get(group) or {}
            # The defaults are shaped like the values they stand in for, group and all.
            defaults = defaults.get(group) or {}
        if f.writes:
            raw, stored = self._match_choice(f, bucket, defaults)
            known = bool(f.writes) and all(
                k in defaults for keys in f.writes.values() for k in keys)
        else:
            stored = key in bucket
            raw = bucket.get(key, defaults.get(key, ""))
            known = key in defaults
        # Three states, not two: written down in the file, inherited from a default that is
        # actually known, or genuinely unknown. Only the last greys the control out — the
        # middle one used to, back when an unwritten key meant this app was guessing.
        # The dot says "nothing is written for this"; the label greying says "and nothing tells
        # this app what applies either". Two different facts, and they used to share one
        # appearance -- which is why a control the compositor ignores now greys its *widget*.
        self.rows[ident].dot.show_mark(not stored)
        self.labels[ident].setEnabled(stored or known)
        w = self.widgets[ident]
        w.blockSignals(True)
        if f.kind == "bool":
            w.setChecked(str(raw).lower() == "true")
        elif f.kind == "int":
            w.setValue(int(float(raw or 0)))
        elif f.kind == "float":
            w.setValue(float(raw or 0))
        elif f.kind == "choice":
            if w.findData("") >= 0:
                w.removeItem(w.findData(""))
            if not known:
                w.insertItem(0, UNKNOWN, "")
            i = w.findData(str(raw))
            w.setCurrentIndex(i if i >= 0 else 0)
        elif f.kind == "color":
            w.set_value(str(raw))
        else:
            w.setText(str(raw))
        w.blockSignals(False)
        # Read the original back out of the widget rather than storing the text the file had.
        # The two are not always the same string for the same value: a schema writes `1.0`
        # where a spin box produces `1`, and `60` where another writes `60.0`. Comparing the
        # spellings made `changes()` see a difference that was not there, and write a key
        # nobody had touched. Comparing what the widget would produce, against what the widget
        # produces, cannot go wrong that way.
        self.originals[ident] = self._value(ident)

    @staticmethod
    def _match_choice(f: Field, bucket: dict, defaults: dict) -> tuple[str, bool]:
        """Which option of a multi-key choice the config is currently sitting on.

        Compares every key the option would write against what the file says, falling back to the
        default for a key the file does not carry. Returns the option and whether the file had an
        opinion of its own about any of them.

        The fallback matters and is not laziness. Some combinations of the keys are ones this menu
        cannot express — the desktop's own focus control is four policies crossed with a switch,
        and it leaves that switch alone for two of them, so a file can legitimately hold a pairing
        no option writes. Falling back to the option that agrees on the **main** key shows the
        policy that is actually in force. Falling back to the first option, which is what the
        obvious version does, would quietly claim a setting nobody chose.
        """
        def effective(key: str) -> str:
            return str(bucket.get(key, defaults.get(key, "")))

        stored = any(key in bucket for keys in f.writes.values() for key in keys)
        for value, keys in f.writes.items():
            if all(effective(k) == v for k, v in keys.items()):
                return value, stored
        for value, keys in f.writes.items():
            if f.key in keys and effective(f.key) == keys[f.key]:
                return value, stored
        return next(iter(f.writes), ""), stored

    def _value(self, ident) -> str:
        f, w = self.fields[ident], self.widgets[ident]
        if f.kind == "bool":
            return "true" if w.isChecked() else "false"
        if f.kind == "int":
            return str(w.value())
        if f.kind == "float":
            return f"{w.value():g}"
        if f.kind == "choice":
            return str(w.currentData())
        if f.kind == "color":
            return w.value()
        return w.text()

    def changes(self) -> dict:
        """What was touched and really differs, plus whatever sibling keys ride along.

        An empty value is dropped only for a `choice`, where empty means "(theme default)" and
        writing it would turn a placeholder into a setting. For text and lists an empty value is
        a decision — it is how a list is cleared — and dropping it made those fields impossible
        to empty at all.

        `originals` now holds the real default for a key the file does not carry, so a control put
        back where it was found writes nothing, and choosing the value something already has writes
        nothing either. Both used to write.
        """
        out: dict = {}
        for ident in sorted(self.touched):
            source, group, key = ident
            f = self.fields[ident]
            value = self._value(ident)
            if value == self.originals.get(ident):
                continue
            if value == "" and f.kind == "choice":
                continue
            written = f.writes.get(value, {}) if f.writes else {n: value for n in (key, *f.also)}
            for name, one in written.items():
                if group:
                    out.setdefault(source, {}).setdefault(group, {})[name] = one
                else:
                    out.setdefault(source, {})[name] = one
        return out

    def extra_changes(self) -> dict:
        """Subclasses add whatever their own widgets contributed."""
        return {}

    def _words(self, ident, value: str) -> str:
        """One value, in the words that are on screen rather than the ones in the file."""
        f = self.fields[ident]
        if f.kind == "bool":
            return "on" if str(value).lower() == "true" else "off"
        if f.kind == "choice":
            return next((label for option, label in f.choices if option == value), value or "—")
        return f"{value}{f.suffix}" if value else "nothing"

    def _said(self) -> str:
        """What is about to be written, named the way the form names it.

        There is no undo in this window and adding one would be a feature, so this is the whole of
        what a change leaves behind: the setting, what it was, and what it now is. It costs
        nothing -- `changes` already compares every value against `originals` to decide what to
        write -- and it cannot say something untrue, because it is read from the same pair.
        """
        moved = [f"{self.fields[i].label} {self._words(i, self.originals.get(i, ''))} → "
                 f"{self._words(i, self._value(i))}"
                 for i in sorted(self.touched)
                 if i in self.fields and self._value(i) != self.originals.get(i)]
        if not moved:
            return ""
        return ", ".join(moved[:2]) + (f" and {len(moved) - 2} more" if len(moved) > 2 else "")

    def apply(self) -> None:
        """Write what changed, and nothing else.

        **The emptiness test comes before the enforce key, and that order is the whole of live
        apply.** `enforce` names the settings this page is responsible for that have no control any
        more; it used to be added first, so on the two pages that declare one the payload was never
        empty and every press of *Apply* was a write. On a timer that would be a write every time a
        number was nudged and put back. Now nothing changed means nothing sent, and the settings a
        page enforces still ride along with every change that is real.
        """
        self._pending.stop()
        payload = self.changes()
        for source, values in self.extra_changes().items():
            payload.setdefault(source, {}).update(values)
        if not payload:
            # Nothing to write, so nothing is pending either -- and the page must be allowed to
            # take the file's word again, or a field touched and put back would leave it stale
            # for the rest of the session.
            self.touched.clear()
            return
        if self.enforces:
            payload["enforce"] = [self.enforces]
        said = self._said()
        if said:
            self.says.emit(said)
        self.c.set_groups(payload)
        # Applied, so nothing is pending any more and the page may take the file's word again.
        self.touched.clear()
        QTimer.singleShot(400, lambda: self.load(self.c.groups()))


# ---------------------------------------------------------------------- tabs with a plugin switch

class PluginPage(SettingsPage):
    """A settings page whose subject can be switched off entirely.

    The tiling page used to be one of these, with an explicit Enabled / Disabled menu rather than
    a tick. It is not any more: this app exists to deliver a tiling desktop, so tiling off is not
    one of its states, and the switch is a declared default instead.
    """

    def __init__(self, sections, client, plugins: list[tuple[str, str]], parent=None):
        super().__init__(sections, client, parent)
        self.plugin_boxes: dict[str, QCheckBox] = {}
        self._plugins_at_load: dict[str, bool] = {}
        #: Which section each switch governs, so everything under it can grey out with it.
        self._plugin_sections: dict[str, str] = {}
        #: Under each switch, what is wrong with the plugin it switches -- shown only then. A switch
        #: for a plugin that is not there, or that the compositor cannot run, would say it does
        #: something and do nothing; this one is greyed and says why instead.
        self._plugin_notes: dict[str, QLabel] = {}
        self._plugin_missing: dict[str, bool] = {}
        for plugin, label, section in plugins:
            widget = QCheckBox(label)
            self.plugin_boxes[plugin] = widget
            self._plugin_sections[plugin] = section
            widget.toggled.connect(self.queue)
            widget.toggled.connect(lambda _on, p=plugin: self._follow_plugin(p))
            # The first row of the section it governs, rather than a row of switches floating
            # above four boxes that did not answer to them. Spanning, so it reads as a heading.
            self.section_forms[section].insertRow(0, widget)
            self._plugin_notes[plugin] = warning()
            self.section_forms[section].insertRow(1, self._plugin_notes[plugin])

    def _follow_plugin(self, plugin: str) -> None:
        """Grey what a switch that is off has nothing to act on.

        The rows keep their values rather than being emptied or unticked -- the answers are still
        somebody's, and switching it back on brings them back exactly as they were.
        """
        on = self.plugin_boxes[plugin].isChecked() and not self._plugin_missing.get(plugin)
        section = self._plugin_sections[plugin]
        for ident in self.fields:
            # The widget and not the label: a greyed label in this window means the app does not
            # know what applies, which is a different thing and is `_paint`'s to say.
            if self.section_of.get(ident) == section:
                self.widgets[ident].setEnabled(on)

    def _load(self, data: dict) -> None:
        super()._load(data)
        enabled = data.get("plugins") or {}
        self._plugins_at_load = {p: bool(enabled.get(p, False)) for p in self.plugin_boxes}
        for plugin, box in self.plugin_boxes.items():
            # Guarded twice, and the flag is the one that matters: `load` holds `_loading` across
            # the whole of this, so `queue` refuses. The block is belt and braces, the pair
            # `ThemeBox` documents.
            box.blockSignals(True)
            box.setChecked(self._plugins_at_load[plugin])
            box.blockSignals(False)
            missing = unavailable(data, plugin)
            self._plugin_missing[plugin] = bool(missing)
            box.setEnabled(not missing)
            note = self._plugin_notes[plugin]
            note.setText(f"{missing} The Settings tab says what to do." if missing else "")
            note.setVisible(bool(missing))
            self._follow_plugin(plugin)

    def extra_changes(self) -> dict:
        changed = {p: b.isChecked() for p, b in self.plugin_boxes.items()
                   if b.isChecked() != self._plugins_at_load.get(p)}
        return {"plugins": changed} if changed else {}
