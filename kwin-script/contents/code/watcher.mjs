// KyprX's window watcher: what the daemon is told about windows.
//
// The one piece that sees a window being born: the compositor does not put that on the bus. It
// decides nothing -- it says what happened and passes on the little it knows, and the daemon
// decides. The reasons for its shape are points 1 to 3 at the top of `../ui/main.qml`: a report at
// `windowAdded` is a trigger and not the truth, and the daemon asks for the whole list by firing a
// named action rather than by loading a script.
//
// What it sends is what the daemon reads (`Window.from_report` in daemon/policy.py): the reasons,
// the fields of an entry and the fifteen kinds it marks. The compositor's and KyprX's own internal
// windows are left out (`rules.internal`), because they are no application's and the daemon has
// nothing to decide about them: the zone overlays this script shows during a drag are such
// windows, and so is the outline the compositor draws while Shift is held.

import { internal } from "./rules.mjs";

// Window types that are never an application window with a title bar of its own: an entry lists
// the ones that are true in `skipped`, and `policy.SKIP_TYPES` in daemon/policy.py holds the same
// fifteen names.
export const SKIP = Object.freeze([
    "dock", "desktopWindow", "popupWindow", "splash", "notification", "utility", "toolbar", "menu",
    "dropdownMenu", "popupMenu", "tooltip", "onScreenDisplay", "criticalNotification",
    "appletPopup", "dndIcon",
]);

// One window as the daemon reads it (`Window.from_report` in daemon/policy.py).
export function portrait(w) {
    const skipped = [];
    for (let i = 0; i < SKIP.length; i++) {
        if (w[SKIP[i]] === true) {
            skipped.push(SKIP[i]);
        }
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
        skipped: skipped,
    };
}

// The watcher, for one load of the script. `env.report(reason, json)` sends a report -- the
// daemon's `Report(ss)` on /Windows -- and `env.owner` is the script's root item, which every
// connection made here names (see the top of `engine.mjs` for why).
export function create(env) {
    const state = {disposed: false};

    function report(reason, list) {
        env.report(reason, JSON.stringify(list));
    }

    // Every window, as far as each one can be read.
    //
    // One `try` per window, and that is the whole point of the loop's shape. `portrait` reaches
    // into `clientGeometry` and `frameGeometry`, and a window that is being torn down while this
    // runs has neither. Built as one expression, a single such window threw before the report was
    // ever sent and the daemon got **nothing** -- indistinguishable, from its side, from the
    // compositor being silent. One window missing from a report is a far smaller lie than an
    // empty report.
    function inventory() {
        if (state.disposed) {
            return;
        }
        const out = [];
        const list = env.Workspace.windows;
        for (let i = 0; i < list.length; i++) {
            try {
                if (!internal(list[i])) {
                    out.push(portrait(list[i]));
                }
            } catch (e) {
                // Nothing useful to say about a window that cannot be read; the rest still counts.
            }
        }
        report("inventory", out);
    }

    function added(w) {
        if (state.disposed || internal(w)) {
            return;
        }
        try {
            report("appeared", [portrait(w)]);
        } catch (e) {
            // The daemon asks for a full inventory after things settle anyway.
        }
        w.windowClassChanged.connect(env.owner, function () {
            if (state.disposed) {
                return;
            }
            try {
                report("class", [portrait(w)]);
            } catch (e) {
                // Same.
            }
        });
    }

    function removed(w) {
        if (state.disposed || internal(w)) {
            return;
        }
        report("gone", [{cls: String(w.resourceClass || ""), uuid: String(w.internalId)}]);
    }

    return {
        inventory: inventory,
        added: added,
        removed: removed,
        dispose: function () { state.disposed = true; },
    };
}
