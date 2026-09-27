"""Folder previews the file manager keeps, and why a recolour has to forget them.

Most folder icons follow the desktop's colour: the icon set paints a folder's body with the
scheme's highlight colour, and the icon loader draws them again whenever the scheme moves. Two on
this desk did not, and they were not icons. Dolphin's picture of a folder *with little thumbnails
inside* is drawn once by the thumbnail worker, with the colour in force that day, and kept on
disk under the freedesktop thumbnail cache, keyed on the folder's own modification time -- so it
is shown again for as long as the folder itself has not changed:

    folder      folder last changed   preview drawn   shown
    Downloads   09-17 15:37           09-17 15:39     the preview, in a week-old colour
    Pictures    09-08 10:09           09-08 10:35     the preview, in a week-old colour
    Documents   09-17 23:37           09-09           preview stale, so the live icon: the new colour

So after every colour change this app makes, the previews of folders are forgotten and the file
managers are told, through the same broadcast the desktop's own file operations use, that those
folders changed; Dolphin draws them again, in the colour now in force. **Only folders.** A file's
thumbnail is a picture of the file and carries no colour of the desktop's; a folder's is a picture
of an icon, and does. 130 of the 3,593 thumbnails on this desk were folders, found in 59 ms.

This is the one place this app removes something from a cache that is not its own. It is a
derived cache -- delete it and it is built again, on sight -- and the entries removed are exactly
the ones that were showing something untrue.
"""

from __future__ import annotations

import glob
import os
import threading

import dbus
import dbus.lowlevel

CACHE = os.path.join(os.path.expanduser(os.environ.get("XDG_CACHE_HOME") or "~/.cache"),
                     "thumbnails")

#: How much of each file is read. A thumbnail's text chunks -- its URI, its type, its size -- come
#: before the picture data, well inside this.
HEAD = 4096

#: The interface every file manager listens on for "these changed", and the object path it is
#: broadcast from. `KDirNotify` in the KIO sources; a broadcast rather than an addressed signal,
#: because whoever is showing a folder is who has to hear it.
KDIRNOTIFY = "org.kde.KDirNotify"


def _text_chunks(head: bytes) -> dict[str, str]:
    """The `tEXt` chunks at the front of a PNG, as a dict. A chunk is a length, a type, the data
    and a CRC; a text chunk's data is a key, a NUL and a value. Read this way rather than searched
    for, because the CRC bytes that follow a value can be anything, printable included."""
    out: dict[str, str] = {}
    position = 8
    while position + 8 <= len(head):
        length = int.from_bytes(head[position:position + 4], "big")
        kind = head[position + 4:position + 8]
        data = head[position + 8:position + 8 + length]
        if kind == b"tEXt" and len(data) == length:
            key, _, value = data.partition(b"\x00")
            out[key.decode("latin-1")] = value.decode("utf-8", "replace")
        if kind in (b"IDAT", b"IEND"):
            break
        position += 12 + length
    return out


#: What each preview was found to be the last time it was read, by its path: the file's identity
#: then (inode, time, size), and the folder's URI when it pictures a folder, None when it pictures a
#: file. For as long as the daemon runs.
#:
#: **The scan is on the way to every colour change, and reading every preview was most of it.**
#: It runs while the change is being put together, before the first of the desktop's tools, so its
#: time is added to the wait between choosing a wallpaper and the new colours. Measured on this
#: desk's 5,000 previews: 96 ms when they were all in the page cache and 843 to 909 ms when they
#: were not -- which is what they were for the first change after a while, and the daemon's
#: stopwatch had between 0.1 and 1.15 s unaccounted for before the first step of a change.
#: Looking at the files' dates took 29 ms. A preview does not stop or start being a picture of a
#: folder, and one that is redrawn is a new file, so only a file not seen before is read.
_seen: dict[str, tuple[tuple[int, int, int], str | None]] = {}
_seen_lock = threading.Lock()


def folder_previews() -> list[tuple[str, str]]:
    """Every cached preview that is a picture of a folder: (file, the folder's URI).

    Only a preview not seen before is read (`_seen`). Safe to call from a thread of its own, which
    is how `remember` fills it without the loop waiting."""
    found = []
    with _seen_lock:
        present = set()
        for path in glob.glob(os.path.join(CACHE, "*", "*.png")):
            try:
                st = os.stat(path)
            except OSError:
                continue
            stamp = (st.st_ino, st.st_mtime_ns, st.st_size)
            present.add(path)
            known = _seen.get(path)
            if known is None or known[0] != stamp:
                try:
                    with open(path, "rb") as fh:
                        head = fh.read(HEAD)
                except OSError:
                    continue
                chunks = _text_chunks(head)
                folder = (chunks.get("Thumb::URI", "")
                          if chunks.get("Thumb::Mimetype") == "inode/directory" else None)
                known = _seen[path] = (stamp, folder)
            if known[1] is not None:
                found.append((path, known[1]))
        for gone in _seen.keys() - present:
            del _seen[gone]
    return found


def remember() -> None:
    """Read every preview once, on a thread of its own, so that the first colour change is not
    the one that waits for it. Nothing is deleted and nothing is written."""
    threading.Thread(target=folder_previews, name="folder previews", daemon=True).start()


def describe(entries: list[tuple[str, str]]) -> str:
    """The session write's description, shaped like the diff it is not -- see `theme._line`."""
    return (f"--- folder previews\n+++ {KDIRNOTIFY}\n"
            f"-{len(entries)} kept from before the colour moved\n"
            f"+{'forgotten, and the file managers told' if entries else '(none to forget)'}\n")


def plain(entries: list[tuple[str, str]]) -> str:
    """The same step for a person: that files are deleted, and which ones.

    The count stays on this line and on this line only, next to the words `scripts/drive.py`
    already sets aside when it compares two runs: the file manager draws new folder previews while
    a run goes on, so the number is the one part of a plan that moves by itself."""
    if not entries:
        return ""
    return (f"delete the file manager's pictures of folders, drawn in the old colours, from "
            f"~/.cache/thumbnails, and tell the file managers to draw them again "
            f"({len(entries)} kept from before the colour moved)")


def forget_and_announce(entries: list[tuple[str, str]]) -> None:
    """Remove the previews, then tell the file managers the folders changed. In that order: told
    first, a file manager would draw the stale picture again from the cache."""
    gone = []
    for path, uri in entries:
        try:
            os.unlink(path)
        except OSError:
            continue
        if uri:
            gone.append(uri)
    if gone:
        announce(gone)


def announce(uris: list[str]) -> None:
    bus = dbus.SessionBus()
    message = dbus.lowlevel.SignalMessage("/", KDIRNOTIFY, "FilesChanged")
    message.append(dbus.Array(uris, signature="s"))
    bus.send_message(message)
    bus.flush()
