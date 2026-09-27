"""One change, across up to four config files, with one reload at the end.

Everything this app writes goes through a `Transaction`, for three reasons.

**Order.** The window rule and the decoration override have to be on disk *before* anything
reloads. Reload in between and the decoration is created before the override exists: the window
flashes a doubled title bar, and the override misses it.

**Contention.** The same files are written by the decoration's settings app and by whatever else
manages them. A transaction loads each file once, saves it once, and refuses to write over a
change that landed in the meantime — the caller retries on top of the new state.

**Dry run.** This is the only place that knows whether writing is real. In dry run nothing is
written and nothing is reloaded; `commit()` returns the unified diff of what would have changed,
which is what makes it possible to exercise the whole interface against real config for free.

It also says so in plain words, before the diff, to whoever `set_reporter` named -- the daemon's
own log. The diff is exact and it is for machines: `scripts/drive.py` reads it line by line. It
never said what the desktop would do *after* the write, either -- stop the screen, lay every tiled
window out again -- because that is not in any file. `daemon/explain.py` says both.

**And changes this app does not make itself.** The wallpaper lives in a file the shell owns, so it
is written by asking the shell to write it. That is still a write, so it goes through here too --
see `session_write`.
"""

from __future__ import annotations

import os
from collections.abc import Callable

import clock
import effects
import logs
import reload as reloader
from kconfig import KConfig, WriteConflict

KLASSYRC = os.path.expanduser("~/.config/klassy/klassyrc")
PRESETSRC = os.path.expanduser("~/.config/klassy/windecopresetsrc")
KWINRULESRC = os.path.expanduser("~/.config/kwinrulesrc")
KWINRC = os.path.expanduser("~/.config/kwinrc")

_dry_run = False

#: Who is told, in plain words, what a dry run would have done. The daemon hands its own log in at
#: start, before its first transaction; nothing else sets it, and with nobody listening a dry run is
#: exactly as quiet as it always was.
_reporter: Callable[[str], None] | None = None


def set_dry_run(on: bool) -> None:
    global _dry_run
    _dry_run = on


def dry_run() -> bool:
    return _dry_run


def set_reporter(reporter: Callable[[str], None] | None) -> None:
    global _reporter
    _reporter = reporter


def report(text: str) -> None:
    """Say what a dry run held back, when there is something to say and somebody to say it to.

    The one door for every held-back effect that is not a transaction's -- this app's own files,
    a shortcut, a notification -- so that all of them reach the same log the same way.
    """
    if _dry_run and _reporter is not None and text:
        _reporter(text)


class Transaction:
    def __init__(self):
        self._files: dict[str, KConfig] = {}
        #: A stopwatch, when somebody upstream is keeping one. The reloads below are the only
        #: part of a change that happens in here rather than in the caller, and they are the part
        #: most likely to be the expensive one -- a compositor reconfigure re-creates every
        #: window's decoration.
        self.trace = None
        #: Changes the session makes on this app's behalf, as (what it would do, do it, the same in
        #: plain words). See `session_write`.
        self._session: list[tuple[str, Callable[[], None], str]] = []
        self.reload_kwin = False
        self.reload_blur = False
        self.reload_tiling = False
        self.reload_colours = False

    def config(self, path: str) -> KConfig:
        """The file, loaded once per transaction."""
        if path not in self._files:
            self._files[path] = KConfig(path)
        return self._files[path]

    @property
    def klassy(self) -> KConfig:
        return self.config(KLASSYRC)

    @property
    def presets(self) -> KConfig:
        return self.config(PRESETSRC)

    @property
    def rules(self) -> KConfig:
        return self.config(KWINRULESRC)

    @property
    def kwin(self) -> KConfig:
        return self.config(KWINRC)

    def session_write(self, description: str, action: Callable[[], None],
                      plain: str = "") -> None:
        """A change this app asks the session to make rather than making it.

        The wallpaper is what this exists for. It lives in a file plasmashell owns and rewrites on
        its way out, so writing that file here would be a change that silently undoes itself --
        the same trap the global shortcut registry has. The shell is asked to write it instead.

        It belongs here and not beside the reload flags because it **is** a write, not the
        announcement of one. Two things follow. Dry run has to hold it back, and the only trace a
        dry run leaves is what `commit` returns -- so `description` goes into `plan()`. Without
        that, a transaction whose only change is a session write has nothing to return and
        `commit` stops before running anything: it would do nothing at all, and say nothing.

        `plain` is the same change said to a person, for the dry-run report: what the step does
        to the desktop rather than which tool it runs. `description` stays as it is because
        `scripts/drive.py` reads it -- it is shaped like a diff on purpose, see `theme._line`.
        """
        self._session.append((description, action, plain))

    def changed(self) -> list[str]:
        return [p for p, cfg in self._files.items() if cfg.dirty()]

    def dirty_files(self) -> list[tuple[str, KConfig]]:
        """Every file this transaction would write, with the version it would write."""
        return [(p, cfg) for p, cfg in self._files.items() if cfg.dirty()]

    def session_steps(self) -> list[tuple[str, str]]:
        """Every change asked of another process, as (description, plain words)."""
        return [(description, plain) for description, _, plain in self._session]

    def report(self) -> str:
        """Everything `plan()` says, in plain words, and what the desktop would do after it.

        Imported here rather than at the top: the words are only ever wanted in a dry run, and a
        real run should not pay for loading a vocabulary it never prints.
        """
        import explain
        return explain.transaction(self)

    def diff(self) -> str:
        """What would change in the files. Exactly that, and nothing else -- see `plan`."""
        return "".join(cfg.diff() for cfg in self._files.values() if cfg.dirty())

    def plan(self) -> str:
        """Everything this transaction would do: the file diffs, then the changes it would ask
        another process to make.

        Kept apart from `diff()` because `diff()` is read as a unified diff by everything that
        handles it, and prose in the middle of one would quietly redefine it. A transaction with
        no session write has `plan() == diff()`.
        """
        return self.diff() + "".join(description for description, _, _ in self._session)

    def commit(self) -> str:
        """Write everything, then reload once. In dry run, write nothing and return the diff."""
        # `plan()` and not `diff()`, and this is the line that makes the difference load-bearing.
        # A transaction whose only change is a session write leaves no file dirty, so its `diff()`
        # is empty -- and an empty text returns here without running anything. Not a dry-run
        # nicety: the change would silently never happen, in a real run as much as in a dry one.
        text = self.plan()
        if not text:
            return ""
        if _dry_run:
            # Said here, before the caller logs the diff it is handed back -- so the plain words
            # come first and the diff after them, at every one of the call sites, without any of
            # them having to know. A report that failed to build must not take the dry run with
            # it: the diff below is still the whole truth.
            try:
                report(self.report())
            except Exception as e:  # noqa: BLE001 -- the words are a courtesy; the diff is not
                # One line and no traceback: `scripts/simulate.sh` fails a run on "Traceback", and
                # looks for this sentence by name instead, so a broken report is a finding of its own.
                report(f"the plain-words report is missing: {type(e).__name__}: {e}")
            return text
        for cfg in self._files.values():
            if cfg.dirty():
                cfg.save()
        # Before the reloads, and deliberately **not** inside the guard below: a session write that
        # fails is the change itself failing, and the caller has to hear about it. A reload that
        # fails is only an announcement that did not arrive.
        for _, action, _ in self._session:
            action()
        # Reloading comes after the write and must never undo it. A reload that fails leaves
        # config on disk that nobody has re-read yet — annoying, and put right by the next one.
        # An exception escaping from here leaves the caller believing the write failed when it
        # did not, which is worse: it invites a retry against a file that already has the change.
        try:
            with clock.step(self.trace, "reload"):
                # The tiler is unloaded first, so the one reconfigure below loads it back re-read.
                # It used to be reloaded last, with a reconfigure of its own inside the call, and
                # the journal showed the pair on every change to its list: about 630 ms of frozen
                # screen twice over, and the screen re-tiled twice, for one tick. Measured after,
                # by the gap between frames (`scripts/stall.py`) on two gap changes: one freeze
                # each, 558 ms and 656 ms, and one re-tile.
                if self.reload_tiling:
                    reloader.unload_script(effects.TILING_PLUGIN)
                if self.reload_kwin or self.reload_tiling:
                    reloader.reconfigure_kwin()
                if self.reload_colours:
                    reloader.invalidate_colour_cache()
                if self.reload_blur:
                    reloader.reconfigure_effect(effects.BLUR_PLUGIN)
        except Exception as e:  # noqa: BLE001 — it is already written; say so and carry on
            logs.emit(f"kyprd: written, but the reload did not go through: "
                      f"{logs.what(e)}", trouble=True)
        return text


def run(build, attempts: int = 3) -> str:
    """Run a transaction, redoing it if someone else wrote to the files in between.

    `build` takes a fresh `Transaction`, makes its changes and returns nothing. On a collision the
    change is rebuilt from scratch on top of the new state — never forced over it.
    """
    for attempt in range(attempts):
        tx = Transaction()
        build(tx)
        try:
            return tx.commit()
        except WriteConflict:
            if attempt == attempts - 1:
                raise
    return ""
