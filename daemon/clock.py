"""A stopwatch for the steps a change is made of.

It exists because of a sentence that was true for two releases and could not be checked: "the
recolouring takes between one and five seconds". Which of the seven things it does took them was
nobody's guess but nobody's measurement either, and the first rule of this project is to say what
was measured.

So every step of the slow path is timed and reported as one line, and the line is the evidence a
change either helped or did not. Cheap enough to leave on for ever: one `time.monotonic()` either
side of work measured in hundreds of milliseconds.

The line is deliberately one line. A log that prints a row per step is a log nobody reads twice,
and the thing worth seeing is the shape -- which step is the big one -- rather than each number on
its own.
"""

from __future__ import annotations

import time
from contextlib import contextmanager


def _ms(seconds: float) -> str:
    return f"{seconds * 1000:.0f} ms" if seconds < 1 else f"{seconds:.2f} s"


@contextmanager
def step(trace, name: str):
    """`trace.step(name)`, and happy with no trace at all.

    For the places that are on the timed path sometimes and not others -- a transaction's reloads,
    which happen under a wallpaper change and under every ordinary Apply as well.
    """
    if trace is None:
        yield
        return
    with trace.step(name):
        yield


class Trace:
    """The steps of one change, in the order they happened, with how long each took."""

    def __init__(self, label: str):
        self.label = label
        self.started = time.monotonic()
        self.steps: list[tuple[str, float]] = []

    @contextmanager
    def step(self, name: str):
        """Time a block, whatever it does and whether or not it raises.

        Recorded on the way out even when it raised: a step that failed slowly is exactly the one
        worth knowing the length of.
        """
        began = time.monotonic()
        try:
            yield
        finally:
            self.steps.append((name, time.monotonic() - began))

    def wrap(self, name: str, action):
        """The same, around a callable that will be run later -- the shape a session write has."""
        def timed():
            with self.step(name):
                action()
        return timed

    def note(self, name: str, seconds: float) -> None:
        """A step somebody else timed."""
        self.steps.append((name, seconds))

    def line(self) -> str:
        """One line: every step with its time, and the whole thing at the end.

        The total is measured from the start rather than added up, so whatever happened **between**
        the steps is in it. That gap is the point of measuring at all: it is where a change that
        merely moved work somewhere else would hide.
        """
        inside = ", ".join(f"{name} {_ms(taken)}" for name, taken in self.steps)
        whole = time.monotonic() - self.started
        return f"{self.label}: {inside or '(nothing to do)'} — {_ms(whole)} in all"
