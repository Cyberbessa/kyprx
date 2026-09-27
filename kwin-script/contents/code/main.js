// KyprX's window watcher.
//
// The one piece that sees a window being born: the compositor does not put that on the bus. It
// decides nothing — it says what happened and passes on the little it knows. The daemon decides.
//
// Four things the shape of this file hides:
//
// 1. At `windowAdded` the window's class is sometimes not the final one, and its decoration may
//    not exist yet. So that message is a trigger, not the truth: the daemon lets things settle
//    and then asks for a full inventory.
// 2. A compositor script in plain JavaScript has no timer. `windowClassChanged` plays the part
//    of "tell me again once you know the real name".
// 3. **The inventory lives here, and the daemon asks for it through a shortcut.** That is not the
//    obvious design, and the obvious one was measured to be broken. It used to be a second script
//    the daemon loaded, ran and unloaded on demand — addressing it by the id `loadScript` returns.
//    The compositor numbers scripts with the size of its own list, so those ids are **reused after
//    any unload**: the new script's object path is already taken by a live one, registering it
//    fails, and `run()` lands on somebody else's script. No error is raised anywhere. Measured: the
//    daemon sat there having run the tiling script instead, its window list frozen at one entry,
//    and the interface showed a single row. A shortcut is addressed by name, so it cannot be
//    confused with anything.
// 4. The cheatsheet key is registered here too, for a related reason: registered from the daemon
//    it was accepted by the shortcut registry and never grabbed by the compositor — twice, once as
//    a component of the app's own and once as a desktop entry. `registerShortcut` from inside a
//    compositor script is what the tiling script does, and those keys work.

// Window types that are never an application window with a title bar of its own.
var SKIP = ["dock", "desktopWindow", "popupWindow", "splash", "notification", "utility",
            "toolbar", "menu", "dropdownMenu", "popupMenu", "tooltip", "onScreenDisplay",
            "criticalNotification", "appletPopup", "dndIcon"];

function portrait(w) {
    var skipped = [];
    for (var i = 0; i < SKIP.length; i++) {
        if (w[SKIP[i]] === true) skipped.push(SKIP[i]);
    }
    return {
        cls: String(w.resourceClass || ""),
        nm: String(w.resourceName || ""),
        cap: String(w.caption || ""),
        uuid: String(w.internalId),
        deco: w.decorationHasAlpha === true,
        inset: Math.round((w.clientGeometry.y - w.frameGeometry.y) * 10) / 10,
        normal: w.normalWindow === true,
        special: w.specialWindow === true,
        skipped: skipped
    };
}

function report(reason, list) {
    callDBus("org.cyberbessa.KyprX", "/Windows", "org.cyberbessa.KyprX.Windows",
             "Report", reason, JSON.stringify(list));
}

// Every window, as far as each one can be read.
//
// One `try` per window, and that is the whole point of the loop's shape. `portrait` reaches into
// `clientGeometry` and `frameGeometry`, and a window that is being torn down while this runs has
// neither. Built as one expression, a single such window threw before `report` was ever reached
// and the daemon got **nothing** — indistinguishable, from its side, from the compositor being
// silent. One window missing from a report is a far smaller lie than an empty report.
function inventory() {
    var out = [];
    var list = workspace.windowList();
    for (var i = 0; i < list.length; i++) {
        try {
            out.push(portrait(list[i]));
        } catch (e) {
            // Nothing useful to say about a window that cannot be read; the rest still counts.
        }
    }
    report("inventory", out);
}

workspace.windowAdded.connect(function (w) {
    try {
        report("appeared", [portrait(w)]);
    } catch (e) {
        // The daemon asks for a full inventory after things settle anyway.
    }
    w.windowClassChanged.connect(function () {
        try {
            report("class", [portrait(w)]);
        } catch (e) {
            // Same.
        }
    });
});

workspace.windowRemoved.connect(function (w) {
    report("gone", [{ cls: String(w.resourceClass || ""), uuid: String(w.internalId) }]);
});

// ---------------------------------------------------------------- what the daemon can ask for
//
// One action with no default key. It is not a shortcut anybody presses — it is the only channel
// a compositor script has for being *called*, and `invokeShortcut` addresses it by name. Leaving
// the key empty is how the tiling script declares an action nobody has bound yet, so this is its
// own vocabulary, not a trick.
registerShortcut("KyprXInventory", "KyprX: re-read the window list", "", inventory);

// The cheatsheet key. The default is only a default: once the registry holds a key for this
// action, the compositor keeps it and ignores the string below. That is what makes the Shortcuts
// tab's edit stick across a reload of this script.
registerShortcut("KyprXCheatsheet", "KyprX: shortcut cheatsheet", "Meta+/", function () {
    callDBus("org.cyberbessa.KyprX", "/Windows", "org.cyberbessa.KyprX.Windows",
             "ShowCheatsheet");
});

// The wallpaper picker, by the same route. Meta+R is the default shortcut;
// any conflict with Spectacle's RecordRegion on a fresh install is released by KyprX.
registerShortcut("KyprXWallpaper", "KyprX: wallpaper picker", "Meta+R", function () {
    callDBus("org.cyberbessa.KyprX", "/Windows", "org.cyberbessa.KyprX.Windows",
             "ShowWallpaper");
});

// And the settings window, for the same reason and by the same route. An action added here does
// not exist until the compositor loads this script again, and it does that only when the script
// has been unloaded — NOT when its Enabled key is flipped, which is measured, and the measurement
// is in daemon/reload.py. install.sh unloads it and reconfigures; the Settings tab says so while
// an action is still missing.
registerShortcut("KyprXSettings", "KyprX: settings", "Meta+K", function () {
    callDBus("org.cyberbessa.KyprX", "/Windows", "org.cyberbessa.KyprX.Windows",
             "ShowSettings");
});

// On load: whatever was already open when the script came up.
inventory();
