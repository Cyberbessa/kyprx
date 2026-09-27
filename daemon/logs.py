"""How the daemon's lines reach the journal, and what a line about a failure says.

The daemon writes plain lines to its output, and the systemd unit it runs under hands that output
to the journal: `journalctl --user -u kyprd` reads it. Two things make a failure findable there.

**A failure says what failed and where.** `what` turns a caught exception into its type, the
innermost place in this app's own code it passed through, and its message, as
`<type> at <file>:<line> in <function>: <message>` -- a bad key name in `shortcuts.from_word`
reads `ValueError at shortcuts.py:<line> in from_word: 'Blorp' is not a key name`, where `str()`
of a KeyError would give a quoted key and nothing else. This app's own frame and not the
innermost one, which is usually in the standard library or in dbus -- so the place named is not
always the function that logged the line. Never a traceback: that word in the daemon's output is
what `scripts/simulate.sh` reads as the daemon falling over.

**A failure is marked as one, for the journal.** journald reads a `<3>` at the start of a line as
"error" and takes it off the text (measured on this desk: the line kept its words, came back with
`PRIORITY=3`, and was the only line `journalctl -p err` showed). So `emit` puts it in front of
each line of a failure -- but only when the output really is the journal, which is what
`JOURNAL_STREAM` names: run by hand, or by `scripts/simulate.sh` into a file, the lines are
exactly what they were.
"""

from __future__ import annotations

import os
import sys
import traceback

#: This app's own code: the folder this file is in, with every link resolved.
HERE = os.path.dirname(os.path.realpath(__file__))

#: journald's word for "error", at the start of a line.
ERROR = "<3>"

_journal: bool | None = None


def to_journal() -> bool:
    """Is this process's output the journal itself? systemd says so in `JOURNAL_STREAM`, as the
    device and inode of the stream it connected -- compared with what the output is now, because
    a program started from a terminal that was itself started by the desktop can inherit the
    variable without its output going anywhere near the journal."""
    global _journal
    if _journal is None:
        try:
            dev, ino = (int(x) for x in os.environ.get("JOURNAL_STREAM", "").split(":"))
            here = os.fstat(sys.stdout.fileno())
            _journal = (here.st_dev, here.st_ino) == (dev, ino)
        except (ValueError, OSError, AttributeError):
            _journal = False
    return _journal


def what(e: BaseException) -> str:
    """A caught exception as one line: its type, where in this app it happened, and its message."""
    where = ""
    for frame in traceback.extract_tb(e.__traceback__):
        # Resolved before anything else, so a frame in kyprd.py reads the same whether the daemon
        # was started through the `~/.local/bin/kyprd` link or as `daemon/kyprd.py`; and code with
        # no file behind it (`<string>`, which dataclasses generate) is never this app's.
        if not os.path.isabs(frame.filename):
            continue
        path = os.path.realpath(frame.filename)
        if path.startswith(HERE + os.sep):
            where = f" at {os.path.basename(path)}:{frame.lineno} in {frame.name}"
    return f"{type(e).__name__}{where}: {e}"


def emit(text: str, trouble: bool = False) -> None:
    """Write one message. `trouble` marks every line of it as an error, for the journal only."""
    if trouble and to_journal():
        text = "\n".join(ERROR + line for line in text.split("\n"))
    print(text, flush=True)
