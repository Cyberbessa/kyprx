"""Pictures of wallpapers, small enough to draw a strip of and cached so it happens once.

Two kinds of source and two different costs, which is the whole shape of this file.

**An image is decoded, and decoding is not free.** The packages on a desktop like this one hold
7680x2160 images; decoding one to draw a 260-pixel card takes long enough that doing it for seventy
of them on every open is a picker that takes twenty seconds to appear. So the small version is
written to a cache and the second open is instant. `QImageReader.setScaledSize` is used where it
helps -- a JPEG can be decoded straight to a smaller size -- and for the formats where it cannot,
the cache is what pays for it.

**A video has no picture at all until one is taken out of it**, which means `ffmpeg`, which means a
process. One frame is pulled at a second in (the first frame of these is very often black) and
cached at a size that serves both the strip and the large preview, because taking a second frame at
a second size would double the only genuinely slow thing here.

**The version is in the directory name, not in a stamp file.** A stamp suits a set built whole in
one pass, where an interrupted build has to be rejected as a whole. This set is open-ended -- entries appear one at a time and there is no moment when it is complete --
so a stamp would have nothing to assert. A version in the path gives the same guarantee for free:
bump it and none of the old files is ever found again. Each file is written to a temporary name and
moved into place, so an interrupted build leaves no half picture behind.

Nothing here is held back in dry run, and that is deliberate rather than an oversight: this is a
derived cache, the same as the colours taken out of wallpapers, and `scripts/simulate.sh` does
not watch either of them. Holding it back would mean the one run that opens the picker to look at it is the one run
where it has nothing to show.

**Decoding answers with a `QImage`, and the `QPixmap` is made where it is drawn.** The picker
decodes on worker threads now, because doing it on the thread that paints was measured as its
stutter -- 94 to 177 ms per PNG wallpaper on this desk, once per stop of the selection, with the
window frozen for it -- and a `QPixmap` may only be made on the thread that draws. So the
`_image` functions are what a worker calls, and the older names wrap them for anything that
wants a pixmap on the spot.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import threading
import time

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QImage, QImageReader, QPixmap

#: Bumped when the shape of what is cached changes -- the size it is built at, the frame a video is
#: taken from. In the path, so an old set is simply never found again.
CACHE_VERSION = "v1"
CACHE_DIR = os.path.expanduser(f"~/.cache/kyprx/wallpapers/{CACHE_VERSION}")

#: What the strip is built at. Wider than a card, so the card can be drawn on a screen that scales.
THUMB_WIDTH = 480

#: What a frame pulled out of a video is kept at. One size for both the strip and the big preview:
#: a second frame at a second size doubles the only slow thing in this file, and a video frame
#: shown a little soft at full size is not worth that.
VIDEO_WIDTH = 960

#: How far into a video the frame is taken from. These very often open on black.
VIDEO_SECONDS = "1"

#: Long enough for a frame off a slow mount, short enough that a picker never looks hung.
FFMPEG_TIMEOUT = 20


def have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _stamp(path: str) -> str:
    """What identifies a source file: where it is, when it changed, and how big it is.

    The modification time is in the key rather than compared against the cache file's, so a
    wallpaper replaced by another of the same name gets a new picture instead of the old one.
    """
    try:
        info = os.stat(path)
        return f"{os.path.realpath(path)}|{info.st_mtime_ns}|{info.st_size}"
    except OSError:
        return os.path.realpath(path)


def _cache_path(source: str, width: int) -> str:
    digest = hashlib.sha256(f"{_stamp(source)}|{width}".encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{digest}.png")


def _save(image: QImage, path: str) -> None:
    """Write a picture where nothing can ever read half of one."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        temporary = path + ".new"
        if image.save(temporary, "PNG"):
            os.replace(temporary, path)
        elif os.path.exists(temporary):
            os.remove(temporary)
    except OSError:
        pass


def _read_scaled(path: str, width: int) -> QImage | None:
    """Decode an image no larger than it has to be.

    `setScaledSize` is what makes this cheap on the formats that can do it, and harmless on the
    ones that cannot -- a PNG is decoded whole and scaled afterwards, which on the 7680x2160
    packages this desk carries is 94 to 177 ms, and is why this runs on a worker. A file this
    build of Qt has no reader for comes back null rather than raising, and the caller draws a
    card with the name on it -- a wallpaper nobody can preview is still a wallpaper somebody may
    want.
    """
    reader = QImageReader(path)
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid() and size.width() > width:
        height = max(1, round(size.height() * width / size.width()))
        reader.setScaledSize(QSize(width, height))
    image = reader.read()
    return None if image.isNull() else image


def _video_frame(path: str, cancel: threading.Event | None = None) -> str | None:
    """One frame out of a video, cached. Returns where it is, or None if it could not be taken.

    `cancel` is the picker closing: a frame nobody will look at is not worth the rest of the
    process, and a worker still inside ffmpeg would otherwise hold the window's exit for it.
    """
    target = _cache_path(path, VIDEO_WIDTH)
    if os.path.exists(target):
        return target
    if not have_ffmpeg() or not os.path.isfile(path):
        return None
    os.makedirs(CACHE_DIR, exist_ok=True)
    temporary = target + ".new"
    # `-ss` before `-i` is the seek that does not decode everything up to the mark. A clip shorter
    # than the mark produces nothing rather than an error, so the second attempt starts at zero.
    #
    # `-f image2` is not decoration. The file is written under a temporary name so that nothing
    # can read half a picture, and that name ends in `.new` -- from which ffmpeg cannot guess a
    # format, and refuses to write anything at all. Measured: every video came back without a
    # picture, and the only complaint was on a stderr nobody was reading.
    for seek in (VIDEO_SECONDS, "0"):
        if cancel is not None and cancel.is_set():
            break
        if not _run_ffmpeg(["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", seek, "-i", path,
                            "-frames:v", "1", "-vf", f"scale={VIDEO_WIDTH}:-2", "-f", "image2",
                            "-y", temporary], cancel):
            break
        if os.path.exists(temporary) and os.path.getsize(temporary):
            try:
                os.replace(temporary, target)
                return target
            except OSError:
                break
    if os.path.exists(temporary):
        try:
            os.remove(temporary)
        except OSError:
            pass
    return None


def _run_ffmpeg(argv: list[str], cancel: threading.Event | None) -> bool:
    """Run ffmpeg to the end, to the timeout, or to the cancel -- whichever comes first.

    Polled rather than `subprocess.run(timeout=...)`, because that call cannot be interrupted
    from outside: a picker closed while a frame was being pulled waited the whole twenty seconds
    for it. False when the process was stopped or could not start.
    """
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
    except OSError:
        return False
    deadline = time.monotonic() + FFMPEG_TIMEOUT
    while proc.poll() is None:
        if time.monotonic() > deadline or (cancel is not None and cancel.is_set()):
            proc.terminate()
            try:
                proc.wait(2)
            except subprocess.TimeoutExpired:
                proc.kill()
            return False
        time.sleep(0.05)
    return True


def thumbnail_image(entry: dict, cancel: threading.Event | None = None) -> QImage | None:
    """The small picture for the strip, built once and read from the cache after that.

    Safe on a worker thread: everything here is a file, a decoder or a process.
    """
    if entry.get("kind") == "video":
        frame = _video_frame(entry.get("id", ""), cancel)
        if not frame:
            return None
        image = QImage(frame)
        return None if image.isNull() else image
    source = entry.get("preview") or ""
    if not source:
        return None
    target = _cache_path(source, THUMB_WIDTH)
    if os.path.exists(target):
        image = QImage(target)
        if not image.isNull():
            return image
    image = _read_scaled(source, THUMB_WIDTH)
    if image is None:
        return None
    _save(image, target)
    return image


def preview_image(entry: dict, width: int,
                  cancel: threading.Event | None = None) -> QImage | None:
    """The big picture beside the strip, or in the middle of the pages.

    Not cached on disk, and that is the deliberate half. There is one of these on screen at a
    time, and caching a second size of every wallpaper would cost twice the disk to save a decode
    that now happens on a worker while the thumbnail stands in for it -- the picker keeps the last
    few it decoded in memory instead, which is what a return to the same wallpaper reads. A video
    is the exception: its frame is already cached, because pulling a second one is a second
    process.
    """
    if entry.get("kind") == "video":
        frame = _video_frame(entry.get("id", ""), cancel)
        if not frame:
            return None
        image = QImage(frame)
        return None if image.isNull() else image
    source = entry.get("preview") or ""
    return _read_scaled(source, width) if source else None


def thumbnail(entry: dict) -> QPixmap | None:
    """`thumbnail_image`, as a pixmap, for the thread that draws."""
    image = thumbnail_image(entry)
    return None if image is None else QPixmap.fromImage(image)


def preview(entry: dict, width: int) -> QPixmap | None:
    """`preview_image`, as a pixmap, for the thread that draws."""
    image = preview_image(entry, width)
    return None if image is None else QPixmap.fromImage(image)


def fitted(pixmap: QPixmap, size: QSize) -> QPixmap:
    return pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)


def crop_box(pixmap: QPixmap, size: QSize) -> QRectF:
    """Which part of a picture fills a box of this shape, centred.

    The companion to `cropped`, for the places that draw straight from the source. A painter given
    a source rectangle scales in the same blit, so nothing is allocated and nothing is scaled
    twice -- which matters where the same big picture is drawn again on every keypress. `cropped`
    is still what a widget wants when the same result is drawn over and over at one size.
    """
    if pixmap.isNull() or size.isEmpty():
        return QRectF(pixmap.rect())
    scale = min(pixmap.width() / size.width(), pixmap.height() / size.height())
    width, height = size.width() * scale, size.height() * scale
    return QRectF((pixmap.width() - width) / 2, (pixmap.height() - height) / 2, width, height)


def cropped(pixmap: QPixmap, size: QSize) -> QPixmap:
    """Filled and trimmed, so a strip of cards is a strip and not a row of different shapes."""
    scaled = pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                           Qt.TransformationMode.SmoothTransformation)
    x = max(0, (scaled.width() - size.width()) // 2)
    y = max(0, (scaled.height() - size.height()) // 2)
    return scaled.copy(x, y, size.width(), size.height())
