"""A colour taken out of the wallpaper.

One picture in, one `r,g,b` out, and nothing else: no D-Bus, no config, no writes but a cache. The
deciding is somebody else's -- `daemon/theme.py` applies it, `daemon/kyprd_wallpaper.py` decides
when.

Three choices here are worth their reasons.

**Nothing new is installed for it.** Images go through `GdkPixbuf`, which the daemon already has by
way of `gi`, and which covers every suffix the picker lists -- `avif`, `heic`, `jxl` and `svg`
included, checked against the loaders on the machine. Videos go through `ffmpeg`, which is already
the optional dependency behind the picker's video thumbnails and is missing in exactly the same
way: with a sentence, not a failure.

**The average of a picture is grey.** Every photograph has a sky, a wall or a shadow big enough to
win a straight popularity contest, and the mean of the whole thing is mud. So the pixels are put in
coarse buckets and each bucket is weighted by *how saturated* its pixels are as well as how many
there are -- which is the rule Plasma's own extractor uses, population times chroma. Near-greys and
the two extremes are dropped before the count starts, so they cannot win at all. The winning bucket
is then averaged over its **real** pixels, so bucketing coarsely costs no precision in the answer.

**A colour out of a picture is not yet an accent.** A night photograph yields something almost
black, which as a highlight is a smudge. So the answer is pushed into the range the presets' own
accents already occupy -- measured across the twelve that have a colour, lightness 0.49 to 0.81 in
the dark ones and 0.39 to 0.58 in the light ones -- and given a floor on saturation. Hue is never
touched, because hue is the whole of what was asked for.

The two monochrome presets are deliberately left out of that measurement rather than folded into
it. Their selection colour is white and black, so including them would open the range to the whole
of it -- and a photograph pushed toward either end is the exact smudge the range exists to prevent.

Deliberately not k-means: it is seeded at random, so two runs over the same video can disagree, and
a wallpaper that recolours the desktop differently each time it is set is worse than one that picks
a slightly duller colour.
"""

from __future__ import annotations

import colorsys
import hashlib
import os
import shutil
import subprocess

import wallpaper

#: In the path rather than in a stamp file, the same as the picker's thumbnails: bumping it stops
#: the old set being found rather than needing it cleared out.
CACHE_VERSION = "v1"
CACHE_DIR = os.path.expanduser(f"~/.cache/kyprx/colours/{CACHE_VERSION}")

#: What everything is scaled to before it is counted. Plasma's own extractor uses 128 square, and
#: at that size the count is sixteen thousand pixels -- enough to be stable, small enough that the
#: whole of the arithmetic below is plain Python and still costs single-digit milliseconds.
SIZE = 128

#: How many frames of a video are counted, spread evenly across it. One frame is whatever the
#: opening happens to be, and openings are often black.
FRAMES = 5

FFMPEG_TIMEOUT = 40

#: Below this much difference between the brightest and dimmest channel, a pixel is grey and can
#: never be an accent however much of the picture it covers.
GREY = 24

#: Where the presets' own accents sit, measured across the twelve that have a colour -- the two
#: monochrome ones are left out on purpose, and the module note says why. An extracted colour is
#: pushed in here.
RANGE = {"dark": (0.50, 0.80), "light": (0.38, 0.60)}
SATURATION_FLOOR = 0.35


def have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


# ---------------------------------------------------------------- getting at the pixels

def _image_pixels(path: str) -> bytes | None:
    """`SIZE`-square RGB, three bytes a pixel and no padding -- or None when the picture would not
    open, which is a fact about this moment and not about the picture: a file still being copied
    in, a loader missing until a package lands. It used to answer the same empty bytes a picture
    with no colour in it does, and so was remembered as having none until the file changed."""
    try:
        import gi
        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import GdkPixbuf
        buf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, SIZE, SIZE, False)
    except Exception:  # noqa: BLE001 — a picture that will not open is a colour we do not have
        return None
    raw = buf.get_pixels()
    stride, channels = buf.get_rowstride(), buf.get_n_channels()
    width, height = buf.get_width(), buf.get_height()
    if channels == 3 and stride == width * 3:
        return bytes(raw)
    # A pixbuf may carry an alpha channel and pads every row to a stride of its own, so the buffer
    # is only a flat run of triples by accident. Repack rather than assume.
    out = bytearray()
    for y in range(height):
        row = y * stride
        for x in range(width):
            start = row + x * channels
            out += raw[start:start + 3]
    return bytes(out)


def _duration(path: str) -> float:
    try:
        done = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                               "-of", "default=nw=1:nk=1", path],
                              capture_output=True, text=True, timeout=FFMPEG_TIMEOUT, check=False)
        return float((done.stdout or "0").strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        return 0.0


def _frames(before_input: list[str], path: str, chain: str) -> bytes | None:
    """Run one ffmpeg pass and hand back the raw frames it printed.

    `None` when the pass did not finish -- no ffmpeg, a timeout -- as against `b""` for a pass
    that ran and printed nothing. The difference decides whether the answer is remembered: a clip
    with nothing in it is a fact about the clip, a timeout is a fact about the afternoon.

    Scaling happens inside the filter chain, never afterwards: there is no sense carrying five
    3440-wide frames out of the process to throw away all but a thumbnail of each. And the size is
    fixed square, so the output is a flat run of `SIZE * SIZE * 3` bytes per frame with no stride
    to reason about.
    """
    try:
        done = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", *before_input, "-i", path,
                               "-fps_mode", "passthrough", "-vf", chain,
                               "-frames:v", str(FRAMES), "-pix_fmt", "rgb24",
                               "-f", "rawvideo", "-"],
                              capture_output=True, timeout=FFMPEG_TIMEOUT, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout or b""


def _video_pixels(path: str) -> bytes | None:
    """Up to `FRAMES` frames spread across the clip, end to end in one buffer.

    **Keyframes, and the difference is not small.** `-skip_frame nokey` is a *decoder* option: the
    packets that are not keyframes are dropped before anything is decoded. The filter that looks
    equivalent decodes every frame and then throws it away, and so does asking for frames at fixed
    times. Measured on three of this desktop's own video wallpapers, 36 MB to 125 MB:

        362 ms against 3284,  293 against 3110,  502 against 3733

    and the colour that comes out is the same one, to a unit or two in a channel. It also needs no
    `ffprobe`, because only the timed recipe has to know how long the clip is.

    A clip that yields fewer than three keyframes cannot be said to have been sampled across, so
    that one falls back to the timed pass -- which is what this always used to do. Long or
    low-GOP sources are the case that wants it.
    """
    frames = _frames(["-skip_frame", "nokey"], path, f"scale={SIZE}:{SIZE}")
    if frames is None or len(frames) >= 3 * SIZE * SIZE * 3:
        return frames
    seconds = _duration(path)
    if seconds <= 0:
        return frames
    timed = _frames([], path, f"fps={FRAMES}/{seconds:g},scale={SIZE}:{SIZE}")
    if timed is None:
        return None
    return timed or frames


# ---------------------------------------------------------------- deciding which colour it is

def _dominant(pixels: bytes) -> tuple[int, int, int] | None:
    """The colour the picture is actually about, or None when it is not about any.

    Buckets four bits to a channel and weights each bucket by the saturation of the pixels that
    landed in it, which is population and chroma in one accumulator. The winner is then averaged
    over its real pixels, so the bucket being coarse costs nothing in the answer.
    """
    buckets: dict[tuple[int, int, int], list] = {}
    for i in range(0, len(pixels) - 2, 3):
        r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
        high, low = max(r, g, b), min(r, g, b)
        if high - low < GREY or high < 24 or low > 236:
            continue
        slot = buckets.setdefault((r >> 4, g >> 4, b >> 4), [0, 0, 0, 0, 0.0])
        slot[0] += 1
        slot[1] += r
        slot[2] += g
        slot[3] += b
        # Each pixel contributes its own saturation, so this one accumulator is population and
        # chroma at once -- which is the weighting, not two of them multiplied afterwards.
        slot[4] += (high - low) / high
    if not buckets:
        return None
    best = max(buckets.values(), key=lambda slot: slot[4])
    count = best[0]
    return round(best[1] / count), round(best[2] / count), round(best[3] / count)


def _fit(rgb: tuple[int, int, int], mode: str) -> str:
    """The colour, moved as little as possible into the range an accent has to live in."""
    hue, lightness, saturation = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    low, high = RANGE.get(mode, RANGE["dark"])
    lightness = min(max(lightness, low), high)
    saturation = max(saturation, SATURATION_FLOOR)
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    return f"{round(r * 255)},{round(g * 255)},{round(b * 255)}"


# ---------------------------------------------------------------- the cache

def _key(path: str, mode: str) -> str:
    info = os.stat(path)
    stamp = (f"{os.path.realpath(path)}|{info.st_mtime_ns}|{info.st_size}"
             f"|{mode}|{SIZE}|{FRAMES}|{GREY}")
    return hashlib.sha256(stamp.encode()).hexdigest()


def _cached(key: str) -> str | None:
    """What was remembered for this wallpaper: a colour, `""` for "nothing to take", or `None`
    for "never worked out". The file existing is the memory; its being empty is an answer."""
    try:
        with open(os.path.join(CACHE_DIR, key), encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return None


def _remember(key: str, colour: str) -> None:
    """Derived, and held to no promise about dry run -- the same as the picker's thumbnails.

    Nothing about this file changes what the next real run does: delete it and it is worked out
    again, and `scripts/simulate.sh` does not watch it for that reason.

    An empty answer is remembered too, and that was a measured omission: one video on this desk
    yields no colour at all, and with nothing written for it every pass of the picker's selection
    over it ran ffmpeg again -- half a second on the daemon's loop, five times in four minutes in
    one journal, for an answer that was never going to change.
    """
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        temporary = os.path.join(CACHE_DIR, key + ".new")
        with open(temporary, "w", encoding="utf-8") as fh:
            fh.write(colour)
        os.replace(temporary, os.path.join(CACHE_DIR, key))
    except OSError:
        pass


# ---------------------------------------------------------------- the one thing this is for

def known_colour(target: str, mode: str) -> str | None:
    """The colour of this wallpaper **if it has already been worked out**, else None.

    The difference between this and `colour_of` is who is waiting. Working one out costs a tenth
    of a second for a picture and a second and a half for a video, and `colour_of` was called from
    the one place where somebody is looking at a window while it happens — drawing the Appearance
    tab. A reply that says "not yet" and arrives at once is worth more there, because the tab is
    told again the moment the answer exists.

    `None` and `""` are different answers and both are needed: `None` is "nobody has worked it out
    yet", `""` is "there is no colour to be had from this one" -- and the second is remembered,
    so a wallpaper that gives nothing is looked at once.
    """
    path = wallpaper.picture_for(target)
    if not path:
        return ""
    try:
        key = _key(path, mode)
    except OSError:
        return ""
    return _cached(key)


def colour_of(target: str, mode: str) -> str:
    """The colour of this wallpaper, as `r,g,b`, or "" when there is not one to have."""
    path = wallpaper.picture_for(target)
    if not path:
        return ""
    try:
        key = _key(path, mode)
    except OSError:
        return ""
    known = _cached(key)
    if known is not None:
        return known
    video = path.lower().endswith(wallpaper.VIDEO_SUFFIXES)
    if video and not have_ffmpeg():
        return ""            # not remembered: installing ffmpeg is an answer that can change
    pixels = _video_pixels(path) if video else _image_pixels(path)
    if pixels is None:
        return ""            # it did not open or did not finish; not a fact about the wallpaper
    found = _dominant(pixels) if pixels else None
    colour = _fit(found, mode) if found else ""
    _remember(key, colour)
    return colour


def trouble(target: str) -> str:
    """Why there is no colour to be had from this one, in a sentence, or "" when there is."""
    path = wallpaper.picture_for(target)
    if not path:
        return "the wallpaper is not a file this can open"
    if path.lower().endswith(wallpaper.VIDEO_SUFFIXES) and not have_ffmpeg():
        return "ffmpeg is not installed, so a video has no picture to take a colour from"
    return ""
