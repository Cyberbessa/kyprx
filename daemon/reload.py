"""Making the compositor, the decoration, the blur effect and the tiling script re-read config,
without a logout.

What was measured here is worth recording, because it is not what reading the sources suggests:

- **One `org.kde.KWin.reconfigure` is enough** for both the window rule and the decoration
  override, and it applies **retroactively**: a window already on screen changes without being
  reopened, in both directions. The decoration's own signals and the legacy settings-changed
  broadcast add nothing.
- **The blur effect has a cheaper reload of its own**, which leaves the rest of the compositor
  alone.
- **A KWin script re-reads itself only when it is unloaded and loaded again**, and the way to do
  that is `unloadScript` — *not* flipping its `Enabled` key. Measured, because this file said the
  opposite for a long time and was wrong: with the script running, writing `krohnkiteEnabled=false`
  and calling `reconfigure` leaves `isScriptLoaded` **true**. The compositor loads a script that
  has become enabled; it does not unload one that has become disabled. So the old off-on wrote a
  contended config file twice, slept for over a second, and reloaded nothing at all — which is why
  a changed gap only took effect at the next login. `unloadScript` followed by one `reconfigure`
  does it, writes nothing, and needs no sleep.
"""

from __future__ import annotations

import dbus
import dbus.lowlevel

KWIN = "org.kde.KWin"


def reconfigure_kwin() -> None:
    """Window rules, decoration overrides, virtual desktops, effects."""
    obj = dbus.SessionBus().get_object(KWIN, "/KWin")
    dbus.Interface(obj, KWIN).reconfigure()


def reconfigure_effect(name: str) -> None:
    """Reload a single effect — for blur, this beats reconfiguring everything."""
    obj = dbus.SessionBus().get_object(KWIN, "/Effects")
    dbus.Interface(obj, "org.kde.kwin.Effects").reconfigureEffect(name)


def effect_loaded(name: str) -> bool:
    obj = dbus.SessionBus().get_object(KWIN, "/Effects")
    props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
    return name in [str(x) for x in props.Get("org.kde.kwin.Effects", "loadedEffects")]


def effects_known() -> tuple[list[str], list[str]] | None:
    """The effects the compositor can load, and the ones it is running -- or None when it cannot
    be asked, which is no session at all rather than no effects.

    The first list is what the compositor found installed; the second what it has loaded. An
    effect that is on in `kwinrc` and in the first list but not the second is one the compositor
    tried and could not run: for a compiled plugin, one built for another version of KWin.
    """
    try:
        obj = dbus.SessionBus().get_object(KWIN, "/Effects")
        props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
        listed = [str(x) for x in props.Get("org.kde.kwin.Effects", "listOfEffects")]
        loaded = [str(x) for x in props.Get("org.kde.kwin.Effects", "loadedEffects")]
    except dbus.DBusException:
        return None
    return listed, loaded


def decoration_running() -> str | None:
    """The window decoration the compositor is drawing with, or None when it cannot be asked.

    Read from `supportInformation`, the text System Settings' *About this system* copies, whose
    `Decoration` section names the plugin (`Plugin: org.kde.klassy`) -- the only place the
    compositor says it. When the configured decoration cannot be loaded, the compositor falls back
    to its default and this names that instead.
    """
    try:
        obj = dbus.SessionBus().get_object(KWIN, "/KWin")
        info = str(dbus.Interface(obj, KWIN).supportInformation())
    except dbus.DBusException:
        return None
    return decoration_in(info)


def decoration_in(info: str) -> str:
    """The plugin named in the `Decoration` section of the compositor's support information."""
    lines = info.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "Decoration":
            for rest in lines[i + 1:]:
                if rest.startswith("Plugin:"):
                    return rest.split(":", 1)[1].strip()
                if not rest.strip():
                    break
    return ""


SCRIPTING_IFACE = "org.kde.kwin.Scripting"


def _scripting():
    return dbus.Interface(dbus.SessionBus().get_object(KWIN, "/Scripting"), SCRIPTING_IFACE)


def script_loaded(plugin: str) -> bool:
    """Whether the compositor is running this script **right now**.

    The live answer, not the config file's. They disagree exactly where it matters: a script whose
    `Enabled` key has just been set to false is still loaded and still running until something
    unloads it.
    """
    try:
        return bool(_scripting().isScriptLoaded(plugin))
    except dbus.DBusException:
        return False


def reload_script(plugin: str) -> None:
    """Make a KWin script re-read itself: unload it, then let one reconfigure load it back.

    **This writes nothing**, which is the whole difference from what it used to do. The old version
    flipped the script's `Enabled` key off and on through the config CLI, with sleeps either side
    and a `finally` to make sure it could not be left off on disk — and none of it worked:
    measured, `reconfigure` does not unload a script that has become disabled, so the key went
    false, the script kept running, the key went true, and the caller was told its settings had
    been re-read when nothing had happened.

    Unloading is the part the compositor only does when asked. Loading is the part it does on its
    own for every enabled script, which is why one `reconfigure` finishes the job.

    Nothing on disk changes, so the failure mode is mild and self-correcting: if the reconfigure
    does not land, the script is simply not running until the next one from any source.
    """
    if unload_script(plugin):
        reconfigure_kwin()


def unload_script(plugin: str) -> bool:
    """The first half of `reload_script`, on its own: unload the script, so that the next
    reconfigure -- whoever asks for it -- loads it back re-read.

    Apart from the reconfigure because `writer.Transaction.commit` already has one: a transaction
    that touches the tiler's list also touches the compositor's rules, and asking for both used to
    reconfigure twice in a row. Measured in the journal on every Float tick and on a daemon start
    that had to put the overlay's float entry back: two freezes of about 630 ms and two re-tiles
    for one change. True when there was a running script to unload.
    """
    if not script_loaded(plugin):
        # Either it is not meant to be running, or it already is not. Unloading nothing and then
        # asking the compositor to load whatever is enabled would start a script somebody has just
        # switched off.
        return False
    _scripting().unloadScript(plugin)
    return True


#: Where the decoration listens for "your colours are stale".
KLASSY_IFACE = "org.kde.Klassy.Style"
#: The one object path Klassy subscribes the decoration's colour cache on. `/KlassyStyle` is a
#: subscription too -- for `reparseConfiguration`, answered by the application style -- and is
#: deliberately not used here: nothing this app writes is an application-style setting.
DECORATION_PATH = "/KlassyDecoration"


def invalidate_colour_cache() -> None:
    """Tell the decoration to rebuild the colours it keeps: the button overrides and the outline.

    **One signal, addressed to the compositor**, and every word of that was measured.

    Klassy 6.7.2 listens for exactly five things on the bus, and the listening is not in the
    decoration at all: it is in `libklassycommon6`, which the decoration (inside the compositor)
    **and the application style (inside every Qt program on the session)** both load. Of the four
    signals this app used to broadcast, two were listened for by nobody -- `reparseConfiguration`
    on `/KlassyDecoration` and `updateDecorationColorCache` on `/KlassyStyle` are not subscriptions
    that exist -- and a third, `reparseConfiguration` on `/KlassyStyle`, reaches only the
    application style, which has nothing to do with a window's outline.

    What is left is the one below. Addressed rather than broadcast, because a broadcast of it is
    delivered to that shared library in **every** open application, each of which rebuilds its own
    palette for nothing; sent to the compositor alone it does the same work where the work belongs.

    The numbers, by the gap between one frame and the next while it happens (`scripts/stall.py`),
    with a quiet desktop reading 11 ms:

    * the compositor's reconfigure alone, about 630 ms -- and it does **not** move the outline;
    * this signal alone, about 650 ms -- and it does not move it either;
    * the two together, about 1.34 s, and that does;
    * what this app used to send -- the reconfigure and all four signals -- about 1.55 s.

    Re-applying the colour scheme does not move the outline either: tried, with the pair as the
    control in the same run.

    So the pair is the price of changing a colour the decoration keeps, and a fifth of it was
    being spent waking up applications that had no part in it.

    **Three things were tried and are not here**, each measured on the screen with a control in the
    same run -- which is the only way a negative here means anything, because with no decorated
    window in front the probe reads zero and looks like an answer.

    * Spacing the two apart: 1.79 s together against 1.76 s a quarter-second apart. The compositor
      does the work as one block either way.
    * `reloadConfig` in place of the reconfigure, which is what Klassy's own settings window sends:
      1.345 s against 1.359 s, the same number -- and the reconfigure is needed anyway for the
      window rules.
    * **Reaching the decoration without making the whole compositor re-read.** The decoration also
      subscribes `notifyChange` on `/KGlobalSettings`, wired to its *own* `reconfigure()` rather
      than the compositor's, so addressing that to the compositor looked like a way to pay the
      cheaper half alone. It is not: with `SettingsChanged`, with `PaletteChanged`, with
      `StyleChanged`, and on its own, the outline stayed the colour it was -- while the pair below,
      run as the control in every one of those passes, moved it every time.

    So the pair is the floor, and the floor is about 1.34 s: roughly 0.63 s of the compositor
    re-reading its configuration and 0.65 s of the decoration rebuilding the colours it keeps.
    Neither half is this app's work, and neither can be asked for alone.

    **The floor is not a constant, though, and most of it was this app's list.** Both halves are
    the decoration reading its per-window list again once for every window, so they grow with
    windows open times groups in the list. With 20 windows open and the list one group per
    application -- 53 of them -- the reconfigure alone froze the screen for 1.65 s and the signal
    for 1.71 s. The list is now kept with neighbours set alike in one group, which took the same
    two to 0.15 s and 0.14 s of the compositor's time: `klassy.MERGED` has the measurement.
    """
    bus = dbus.SessionBus()
    message = dbus.lowlevel.SignalMessage(DECORATION_PATH, KLASSY_IFACE,
                                          "updateDecorationColorCache")
    message.set_destination(KWIN)
    bus.send_message(message)
    bus.flush()


def notify(title: str, body: str) -> int:
    obj = dbus.SessionBus().get_object("org.freedesktop.Notifications",
                                       "/org/freedesktop/Notifications")
    iface = dbus.Interface(obj, "org.freedesktop.Notifications")
    return int(iface.Notify("KyprX", dbus.UInt32(0), "kyprx",
                            title, body, [], {"desktop-entry": "kyprx"}, 8000))
