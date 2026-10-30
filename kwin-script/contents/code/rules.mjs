// Which windows the tiling takes, which ones float, and which it never touches.
//
// Three layers, read in this order. The first is fixed: kinds of window that are never an
// application's own (a panel, a menu, a notification), KyprX's and the compositor's internal
// windows, the classes the daemon says are never tiled, a window that cannot be resized; and
// windows that always float -- one on every desktop, and with `floatUtility` the dialogs and
// utility windows. The second is the person's: the classes and titles on the Windows tab's
// lists, read again whenever a window's class or title changes. The third is the person's hand:
// Toggle Float, which the engine keeps per window and which wins over the second layer and over
// the dialogs of the first (`engine.mjs`).
//
// The lists arrive in the daemon's answer (`Tiling()` on /Windows) already resolved: `ignore`
// holds the daemon's own classes before the person's, so the person's list adds to them and never
// replaces them (`daemon/tiling.py`, `resolve`).

// Kinds of window that are never tiled, as the true-or-false properties KWin gives every window.
export const NEVER_TYPES = Object.freeze([
    "desktopWindow", "dock", "splash", "notification", "onScreenDisplay", "criticalNotification",
    "appletPopup", "tooltip", "popupWindow", "dropdownMenu", "popupMenu", "comboBox", "dndIcon",
    "toolbar", "menu", "specialWindow",
]);

// And the kinds that float when `floatUtility` is on. All four are asked because the protocols
// say it differently: on Wayland a QDialog child of a window and a Qt.Tool window both arrived as
// `transient` with `dialog` false, while an X11 dialog arrived with `dialog` true (measured in a
// nested KWin 6.7.5).
export const FLOAT_TYPES = Object.freeze(["dialog", "modal", "utility", "transient"]);

// A window the compositor or a script made for itself rather than an application's. KyprX's own
// overlays and KWin's debug console both arrived in `windowAdded` with pid -1 and no class or
// resource name -- and with `normalWindow` true, which is why this is asked before any question
// about the kind of window (measured in a nested KWin 6.7.5). KWin's outline is a window of the
// same kind, by its source.
export function internal(w) {
    return Number(w.pid) < 0 && String(w.resourceClass || "") === "";
}

// A glob where `*` is any run of characters and everything else is itself.
export function globMatch(pattern, text) {
    const parts = pattern.split("*");
    if (parts.length === 1) {
        return pattern === text;
    }
    if (!text.startsWith(parts[0])) {
        return false;
    }
    let at = parts[0].length;
    for (let i = 1; i < parts.length - 1; i++) {
        const found = text.indexOf(parts[i], at);
        if (found < 0) {
            return false;
        }
        at = found + parts[i].length;
    }
    const tail = parts[parts.length - 1];
    return text.length - at >= tail.length && text.endsWith(tail);
}

// One entry of a class list against a window, on its class or its resource name, case ignored:
// `[term]` is a part of the name, an entry with `*` a glob, anything else the whole name. The
// words for this are daemon/tiling.py's, at `KEYS`. On Wayland the class is the application's
// desktop file name (`org.kde.dolphin`) and the resource name its program (`dolphin`), so an
// entry written either way finds it.
export function classMatches(entry, w) {
    const e = String(entry || "").trim();
    if (!e) {
        return false;
    }
    const names = [String(w.resourceClass || "").toLowerCase(),
                   String(w.resourceName || "").toLowerCase()].filter(function (n) {
        return n !== "";
    });
    if (e.length > 2 && e[0] === "[" && e[e.length - 1] === "]") {
        const part = e.slice(1, -1).toLowerCase();
        return names.some(function (n) { return n.includes(part); });
    }
    const wanted = e.toLowerCase();
    if (e.includes("*")) {
        return names.some(function (n) { return globMatch(wanted, n); });
    }
    return names.some(function (n) { return n === wanted; });
}

// A title entry is a part of the title, case counting.
export function titleMatches(entry, caption) {
    const e = String(entry || "");
    return e !== "" && String(caption || "").includes(e);
}

export function anyClass(list, w) {
    return (list || []).some(function (entry) { return classMatches(entry, w); });
}

export function anyTitle(list, caption) {
    return (list || []).some(function (entry) { return titleMatches(entry, caption); });
}

// A screen the person keeps out of the tiling, by the name the compositor gives the output.
export function screenIgnored(settings, outputName) {
    return ((settings.ignore && settings.ignore.screens) || []).indexOf(String(outputName)) >= 0;
}

// Layers one and two for one window: `{kind, fixed, focusable, why}`.
//
// `kind` is "never", "float" or "tile". `fixed` says the person's hand cannot change it: a window
// the tiling never takes, or one on every desktop, which belongs to no single screen's layout.
// `focusable` is whether the focus keys may land on it: a window left alone by a list still can,
// a panel or a menu cannot.
export function classify(w, settings) {
    if (internal(w)) {
        return {kind: "never", fixed: true, focusable: false, why: "internal"};
    }
    for (let i = 0; i < NEVER_TYPES.length; i++) {
        if (w[NEVER_TYPES[i]] === true) {
            return {kind: "never", fixed: true, focusable: false, why: NEVER_TYPES[i]};
        }
    }
    const ignore = settings.ignore || {};
    if (anyClass(ignore.classes, w)) {
        return {kind: "never", fixed: true, focusable: true, why: "a class never tiled"};
    }
    if (anyTitle(ignore.titles, w.caption)) {
        return {kind: "never", fixed: true, focusable: true, why: "a title never tiled"};
    }
    if (w.resizeable === false) {
        return {kind: "never", fixed: true, focusable: true, why: "not resizeable"};
    }
    if (w.onAllDesktops === true) {
        return {kind: "float", fixed: true, focusable: true, why: "on all desktops"};
    }
    if (settings.floatUtility) {
        for (let i = 0; i < FLOAT_TYPES.length; i++) {
            if (w[FLOAT_TYPES[i]] === true) {
                return {kind: "float", fixed: false, focusable: true, why: FLOAT_TYPES[i]};
            }
        }
    }
    const float = settings.float || {};
    if (anyClass(float.classes, w)) {
        return {kind: "float", fixed: false, focusable: true, why: "a floating class"};
    }
    if (anyTitle(float.titles, w.caption)) {
        return {kind: "float", fixed: false, focusable: true, why: "a floating title"};
    }
    return {kind: "tile", fixed: false, focusable: true, why: ""};
}

// What a window needs of a zone, as a frame: its minimum size, which the application sets for
// its content, plus what the frame adds around the content (title bar and borders). Zero where
// the application sets no minimum.
//
// The compositor does not hold a window to its minimum: a client whose minimum is 400 x 300 was
// set to 200 x 150 by a script and stayed there, on Wayland and on X11 alike (measured in a nested
// KWin 6.7.5). So the engine never asks for less than this: a zone smaller than it gets the room
// first (`plan` in engine.mjs, which judges a zone with `holds` in geometry.mjs), and a window that
// grows past its zone later has its screen laid out again (`grown` there).
export function needs(w) {
    return needsWith(w, frameExtra(w));
}

// What the frame adds around the content on each axis -- title bar and borders -- or null on an
// axis where the content has no size to measure it against: a window laid out at its title bar's
// height alone, or one whose content is not there yet. The engine holds it per window rather than
// reading it fresh at every pass (`needsOf` in engine.mjs says why).
export function frameExtra(w) {
    const frame = w.frameGeometry;
    const client = w.clientGeometry;
    const both = !!frame && !!client;
    return {width: both && client.width > 0 ? Math.max(0, frame.width - client.width) : null,
            height: both && client.height > 0 ? Math.max(0, frame.height - client.height) : null};
}

// `needs` with what the frame adds given (`extra`, as `frameExtra` answers it; null counts as
// nothing), rounded up to whole pixels.
export function needsWith(w, extra) {
    const least = w.minSize;
    if (!least || !(least.width > 0 || least.height > 0)) {
        return {width: 0, height: 0};
    }
    const extraW = extra && extra.width ? extra.width : 0;
    const extraH = extra && extra.height ? extra.height : 0;
    return {width: Math.ceil((least.width || 0) + extraW),
            height: Math.ceil((least.height || 0) + extraH)};
}
