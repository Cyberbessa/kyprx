// KyprX's tiling engine: which windows are tiled, where each one goes, and what the keys do.
//
// The engine runs inside the compositor because only a compositor script sees a window being born
// and can set where a window is. It reads none of its settings itself: `KWin.readConfig` sees a
// change to `kwinrc` only after the compositor reconfigures (read in KWin 6.7.5's source), and a
// reconfigure stalls the screen. So the daemon resolves the settings into one answer and the
// script asks for it over the bus (`Tiling()` on /Windows, in main.qml) at load, each time the
// daemon fires `KyprXTiling` after a write, and each time it fires `KyprXInventory`. An answer is
// acted on only when its text differs from the last one acted on.
//
// A screen's desktop on one activity is a **surface**, keyed by the output's name, the desktop's id
// and the activity's id, and each keeps its own arrangement, the order of its windows (by
// `internalId`, the first one in the master zone), the layout per arrangement and per window count
// as the person last resized it, and the zone layout a drag offers there (`zone`), which manual
// tiling's layout keys move along the selector. One per activity as well as per desktop: every
// activity shows the same desktops, each with windows of its own, and keyed by desktop alone the
// windows of two activities would share one order and one arrangement. Where no activity manager
// runs -- the nested KWin of scripts/sandbox.sh has none: its bus had no owner for
// org.kde.ActivityManager, and every window's `activities` was empty -- `Workspace.currentActivity`
// is empty, the key has no activity in it, and every window counts as on the activity in use. All
// of it lives in memory, in the object `create` returns, and none of it at module scope: KWin keeps
// one QML engine for the whole session, so whatever a module held at its top would outlive the
// script.
//
// Five things the shape of this file hides:
//
// 1. **Every connection names the script's root item as its owner** (`signal.connect(env.owner,
//    fn)`, in `hook`). A one-argument `connect` made from a module survives `unloadScript` -- the
//    handler kept running on the next window after the script was gone, and a reload stacked a
//    second one -- while one that names the root item is cut when the item goes (measured in a
//    nested KWin 6.7.5). Each handler checks `disposed` too, which costs nothing.
// 2. **A write is recorded before it is made, and what a tiled window does after it is answered
//    only once the window is still.** On Wayland a read of `frameGeometry` straight after setting
//    a new size answers the old rectangle, and `frameGeometryChanged` brings the new one 2 to 7 ms
//    later -- a write that only moves the window lands at once -- and on X11 the signal comes
//    inside the write (all measured). So the target is stored first, and a change inside the write,
//    or the first after it on Wayland, is the write landing (`writing`, `landing`). Any other
//    change of a tiled window's rectangle that is not the person's drag, a maximize or full screen,
//    or a move to another screen or desktop -- each of which has its own way (drag.mjs, `changed`,
//    `moved`) -- is its application's, or KWin's acting for it: KWin grants an X11 window's own
//    move and resize for a window a script placed and refuses it for a maximized or quick-tiled
//    one, a Wayland window's own size is taken with its corner kept, and a window that raises its
//    minimum ends at least that big (all measured in the sandbox's facts scenario, with Qt test
//    windows, whose toolkit asks for the size itself as it raises its minimum); and `minSize` has
//    no change signal (read in KWin 6.7's source), so that change is all a script hears of a
//    raised minimum. Such a window is put back in its zone, but never while it moves: it is
//    looked at once it has been still for a whole turn of main.qml's quiet timer (`reassert`) --
//    and not at all while KWin's own quick-tile key holds it (`w.tile`, which that key sets:
//    measured there too). One that answers its zone with a size of its own in the zone's corner
//    -- a terminal sizing itself to whole characters -- keeps it after one more write; one that
//    keeps moving away is put back at most MOST_BACK times in AGAIN_MS, and then where it puts
//    itself stands, rather than a fight with no end.
// 3. **The usable area comes from `Workspace.clientArea(Workspace.MaximizeArea, output, desktop)`.**
//    The enum is on Workspace. `KWin.MaximizeArea` is undefined in a declarative script, and
//    `clientArea` given undefined quietly answers option 0, the placement area (measured).
// 4. **The compositor's own screen-edge tiling is switched off in memory while this tiles**:
//    `Options.electricBorderMaximize` and `electricBorderTiling` are set false on the Options
//    object, which changes nothing on disk; a reconfigure reads the person's values back and says
//    so with `configChanged` (measured), so each `configChanged` takes those fresh values as the
//    ones to give back and sets them false again. They are given back when the tiling stops and
//    when the script goes. The side edges' quick tiling would fight the zones, and the top edge's
//    maximize draws its preview with the very outline Shift draws (`setElectricBorderMaximizing`
//    shows the Workspace's outline, read in KWin 6.7's source), which the drag would take for Shift
//    and hide (drag.mjs). So KyprX maximizes a window let go at the top edge itself, by KWin's own
//    rule, while the person's value for it -- the one kept to give back -- is on
//    (`maximizeAtTop`); the side edges stay off.
// 5. **What the compositor says while it is being called is put off.** `Workspace.createDesktop`
//    and `removeDesktop` bring `desktopsChanged` before they return (measured in the sandbox's
//    facts scenario), a switch of desktop brings `currentDesktopChanged` once per screen, and
//    main.qml hands each to this engine at once. So whatever those signals start here waits for
//    later -- the windows counted again (`placesAgain`), KyprX's desktops looked over (the cleanup
//    timer) -- and the step that made the call (`overflow`) is never re-entered halfway through.
//    The one handler that acts at once, a window's own `desktopsChanged`, finds nothing to do
//    for the window being moved there: the rules have not read it yet.

import * as Drag from "./drag.mjs";
import * as G from "./geometry.mjs";
import * as R from "./rules.mjs";

// The shape of `Tiling()`'s answer this engine reads: daemon/tiling.py's ANSWER_VERSION.
export const ANSWER_VERSION = 1;

// A window Toggle Float takes out of the tiling is put in the middle of the usable area, at this
// much of its size; so is a window that opens with every zone taken, when it is to float.
export const FLOAT_FRACTION = 0.75;

// The most of the usable area KyprX's settings window is given, on each side, when it opens in
// the middle of its screen at its own size.
export const OWN_MOST = 0.9;

// How long after the tiling starts a window that opens with every zone taken takes the screen
// with it to its new desktop. An estimate of how long a login takes to open the applications it
// starts, not a measurement: the measured fact is that activation tells nothing apart (see
// `overflow`), so this is the only line between a window the person opened and one that opened by
// itself.
export const FOLLOW_AFTER_MS = 30000;

// How long after the engine took a screen to the desktop a window went to, a window that arrives
// on the desktop the screen left counts as the rest of that burst (`burst`). An estimate, not a
// measurement -- no scenario of the sandbox opens a burst, and only the engine harness fakes one:
// meant to be longer than an application takes to show the windows it made together, and short
// enough that a window put on that desktop later -- by a window rule, by its application, by a
// session being restored -- does not count.
export const BURST_MS = 2000;

// How many times within AGAIN_MS a tiled window that moves or resizes itself is put back in its
// zone before where it puts itself stands (`reassert`). An estimate of "several times in a row",
// not a measurement: room for an application that puts its window back where it last had it, in a
// burst or two, as it opens, and few jumps from one that fights. What real applications send --
// Steam's bursts among them -- is not measured.
export const MOST_BACK = 3;

// How long the times a window was put back count, and how long a window whose own rectangle
// stands has to be still before a move of its own, or a pass of its screen that gives it the same
// zone, starts a new round (`byItself`, `stillThere`). An estimate, not a measurement.
export const AGAIN_MS = 10000;

// The most windows a surface lays out at once: a window that joins one with this many tiled waits
// for room, floating, as one that gives way does, and is tiled again by itself as soon as one of
// them goes (`planned`). The same as the most layouts an arrangement has (`MAX_WINDOWS` in
// daemon/tiling.py, held to this by tests/test_script_contract.py), and the largest case the room
// was measured on: nine windows that each need a whole column's height took 1399 fits, 170 to 200
// ms in PySide6's QJSEngine, for the pass the ninth joined in (`roomNine`). Past it nothing capped
// the room's search, which grows with the cube of the windows: squeezing in by splitting the last
// zone, the owner saw the screen freeze at every window opening or closing past a dozen, the
// cascade's zones too small for each window's minimum and every pass trying each window's leaving
// over again.
export const MOST_TILED = 9;

// The most desktops a script can have. Measured in the sandbox's facts scenario: from one, 24
// `createDesktop` calls made 24 desktops, and the next was ignored without a word.
export const MAX_DESKTOPS = 25;

// What joins a desktop's name to the number of a desktop KyprX made after it: "Room · 2". U+00B7,
// with a space either side.
export const CHAIN_MARK = " \u00b7 ";

// How many of the zone layouts a drag offers the selector lists after the whole screen, in the
// pool's order: as many as the Tiling tab lets a drag offer (`MAX_DRAG` in gui/splits.py, held
// to this by tests/test_script_contract.py). A pool can offer more -- the upgrade from version 1
// offers every layout manual tiling showed -- and one past these is listed only while it is a
// screen's own (`bar`).
export const MAX_OFFERED = 12;

// The whole screen, as the selector's first entry and as a screen's `zone` "": one zone, the
// usable area less its gaps. It is no zone layout of the pool -- those have two zones at least, and
// an id of one character at least -- so it is there whatever the pool holds.
export const WHOLE_SCREEN = Object.freeze({id: "", name: "Whole screen", tree: Object.freeze({})});

// What the name card says under a zone layout's name when manual tiling's layout keys move to it.
export const ZONES_CAPTION = "Zones offered when you drag a window";

// What the name card says when Toggle Automatic Tiling has switched automatic tiling on or off.
export const AUTO_ON = "Automatic tiling on";
export const AUTO_OFF = "Automatic tiling off";

// How long after Toggle Automatic Tiling is pressed an answer that switches automatic tiling counts
// as the key's, and is said on the name card (`autoSaid`). An estimate, not a measurement: long
// enough for the daemon to write the setting and tell the tiling, and for the script's call for
// its settings to be answered; short enough that a switch made on the Tiling tab some time after a
// key the daemon refused is not taken for the key's.
export const TOGGLE_MS = 3000;

// What each of the tiling keys does: the action id, as daemon/shortcuts.py names it, and the
// engine's step with its arguments.
export const ACTIONS = Object.freeze({
    KyprXFocusLeft: Object.freeze(["focus", "left"]),
    KyprXFocusDown: Object.freeze(["focus", "down"]),
    KyprXFocusUp: Object.freeze(["focus", "up"]),
    KyprXFocusRight: Object.freeze(["focus", "right"]),
    KyprXMoveLeft: Object.freeze(["move", "left"]),
    KyprXMoveDown: Object.freeze(["move", "down"]),
    KyprXMoveUp: Object.freeze(["move", "up"]),
    KyprXMoveRight: Object.freeze(["move", "right"]),
    KyprXShrinkWidth: Object.freeze(["resize", "width", false]),
    KyprXGrowHeight: Object.freeze(["resize", "height", true]),
    KyprXShrinkHeight: Object.freeze(["resize", "height", false]),
    KyprXGrowWidth: Object.freeze(["resize", "width", true]),
    KyprXToggleFloat: Object.freeze(["toggleFloat"]),
    KyprXSetMaster: Object.freeze(["setMaster"]),
    KyprXRotate: Object.freeze(["rotate", 1]),
    KyprXRotateBack: Object.freeze(["rotate", -1]),
    KyprXToggleAutomaticTiling: Object.freeze(["toggleAuto"]),
    KyprXNextLayout: Object.freeze(["cycle", 1]),
    KyprXPreviousLayout: Object.freeze(["cycle", -1]),
});

function strings(list) {
    return Array.isArray(list) ? list.map(String) : [];
}

function whole(value, fallback) {
    const n = Number(value);
    return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : fallback;
}

// The daemon's answer as the engine uses it, every field read with its default. Arrangements
// without a layout to tile by are left out, and an answer left with none tiles nothing: the daemon
// validates them, so that is a daemon this script does not understand rather than a choice.
//
// Two defaults are the careful reading rather than the daemon's own. `overflow` absent is 2, the
// cascade: an answer that does not say what a window that finds every zone taken does comes from
// a daemon that knows nothing else. And `dry` is anything but `dryRun: false`: a daemon that does
// not say it writes is taken to write nothing, and then the engine makes and removes no desktop,
// because the compositor writes `kwinrc [Desktops]` the moment one comes or goes.
//
// The zone layouts come as `pool` (`poolOf`), and with them, through `slots`, each arrangement's
// own (`homesOf`): `zones` finds a zone layout by its id, and `homes` an arrangement's own by the
// arrangement's. `desktops` is the arrangement each desktop starts on, by the desktop's name, as
// the Tiling tab chose it (`startOf`); an answer from before it has none, and every desktop starts
// on the first arrangement in the rotation, as it did.
export function settingsOf(answer) {
    const gaps = answer.gaps || {};
    const float = answer.float || {};
    const ignore = answer.ignore || {};
    const arrangements = (Array.isArray(answer.arrangements) ? answer.arrangements : [])
        .filter(function (a) {
            return a && typeof a.id === "string" && Array.isArray(a.layouts) && a.layouts.length;
        });
    const pool = poolOf(answer, arrangements);
    const zones = new Map();
    pool.forEach(function (z) {
        if (!zones.has(z.id)) {
            zones.set(z.id, z);
        }
    });
    return {
        tiling: answer.tiling === true && arrangements.length > 0,
        auto: answer.auto !== false,
        osd: answer.osd !== false,
        live: answer.live !== false,
        floatUtility: answer.floatUtility !== false,
        newWindow: [0, 1, 2, 3].indexOf(answer.newWindow) >= 0 ? answer.newWindow : 0,
        overflow: [0, 1, 2].indexOf(answer.overflow) >= 0 ? answer.overflow : 2,
        newDesktop: answer.newDesktop === 1 ? 1 : 0,
        dry: answer.dryRun !== false,
        gaps: {top: whole(gaps.top, 0), bottom: whole(gaps.bottom, 0), left: whole(gaps.left, 0),
               right: whole(gaps.right, 0), between: whole(gaps.between, 0)},
        float: {classes: strings(float.classes), titles: strings(float.titles),
                centred: strings(float.centred), above: strings(float.above)},
        ignore: {classes: strings(ignore.classes), titles: strings(ignore.titles),
                 screens: strings(ignore.screens)},
        arrangements: arrangements,
        pool: pool,
        zones: zones,
        // `slots` name zone layouts of the answer's pool, and none of one made here.
        homes: homesOf(arrangements, pool, Array.isArray(answer.pool) ? answer.slots : null),
        desktops: desktopsOf(answer.desktops),
    };
}

// The arrangement chosen for each desktop, by name, in a Map: an entry that is not text to text is
// passed over, and so is anything that is not an object.
function desktopsOf(chosen) {
    const out = new Map();
    if (!chosen || typeof chosen !== "object" || Array.isArray(chosen)) {
        return out;
    }
    Object.keys(chosen).forEach(function (name) {
        if (typeof chosen[name] === "string") {
            out.set(name, chosen[name]);
        }
    });
    return out;
}

// The zone layouts, in the pool's order, each `{id, name, drag, tree, text}`: the answer's `pool`,
// an entry without a string id or a tree left out. An answer without one comes from a daemon from
// before the pool, and then they are made from its arrangements' layouts of two zones or more, one
// for each tree, each offered on a drag and named after the arrangement that has it first.
function poolOf(answer, arrangements) {
    if (Array.isArray(answer.pool)) {
        return answer.pool.filter(function (z) {
            return !!z && typeof z.id === "string" && !!z.tree && typeof z.tree === "object"
                && !Array.isArray(z.tree);
        }).map(function (z) {
            return {id: z.id, name: typeof z.name === "string" ? z.name : z.id,
                    drag: z.drag !== false, tree: z.tree, text: G.textOf(z.tree)};
        });
    }
    const made = [];
    const seen = new Set();
    arrangements.forEach(function (a) {
        a.layouts.forEach(function (tree, i) {
            const text = G.textOf(tree);
            const count = G.zoneCount(tree);
            if (count >= 2 && !seen.has(text)) {
                seen.add(text);
                made.push({id: a.id + "-" + (i + 1),
                           name: String(a.name || a.id) + " (" + count + " zones)",
                           drag: true, tree: tree, text: text});
            }
        });
    });
    return made;
}

// Each arrangement's own zone layout, by the arrangement's id: the one a screen on it offers a drag
// until the person picks another, and goes back to. Of its layouts, the one for the most windows
// whose zone layout a drag offers -- the answer's `manual` says which number of windows that is --
// or else the first zone layout a drag offers, and "" (the whole screen) when none is. From a
// daemon from before the pool, `manual` is the layout manual tiling showed, and that is the one.
//
// Which zone layout that layout is, `slots` says: the ids of an arrangement's zone layouts, by its
// id, in the order of its layouts. A tree alone would not say it -- the rules let two zone layouts
// hold one tree, and *Duplicate* under the Tiling tab's Zone layouts leaves two like that until the
// copy is changed, the copy free to be an arrangement's choice meanwhile -- and the arrangement's
// own would be shown under the other's name, or an arrangement that uses no zone layout a drag
// offers would get one with its tree rather than the first. The id is taken only for a zone
// layout a drag offers that holds the very tree the arrangement has there. From a daemon from
// before the pool, which sends no `slots`, it is the first zone layout a drag offers with that
// tree.
function homesOf(arrangements, pool, slots) {
    const first = pool.find(function (z) { return z.drag; });
    const named = slots && typeof slots === "object" && !Array.isArray(slots) ? slots : {};
    const homes = new Map();
    arrangements.forEach(function (a) {
        const count = Math.min(Math.max(1, Math.floor(Number(a.manual)) || 1), a.layouts.length);
        const text = count >= 2 ? G.textOf(a.layouts[count - 1]) : null;
        const ids = Object.prototype.hasOwnProperty.call(named, a.id)
            && Array.isArray(named[a.id]) ? named[a.id] : [];
        const found = text === null ? null : pool.find(function (z) {
            return z.drag && z.text === text && (!ids.length || z.id === ids[count - 1]);
        }) || null;
        homes.set(a.id, found ? found.id : first ? first.id : "");
    });
    return homes;
}

// A desktop's name read as one KyprX made: `{base, n}` for "<base> · <n>", n a whole number from
// 2 written without a leading zero, and null for any other name. Whether it is one of KyprX's
// depends on the other desktops too: the base has to be another desktop's exact name (`create`,
// `markOf`).
export function chainName(name) {
    const text = String(name);
    const at = text.lastIndexOf(CHAIN_MARK);
    if (at < 0) {
        return null;
    }
    const digits = text.slice(at + CHAIN_MARK.length);
    const n = Number(digits);
    if (digits === "" || String(n) !== digits || !Number.isInteger(n) || n < 2) {
        return null;
    }
    return {base: text.slice(0, at), n: n};
}

function listOf(items) {
    const out = [];
    if (!items) {
        return out;
    }
    for (let i = 0; i < items.length; i++) {
        out.push(items[i]);
    }
    return out;
}

// The engine for one load of the script.
//
// `env` is what main.qml hands every module: `Workspace`, `Options`, `owner` (the root item),
// `rect` (Qt.rect), `later` (Qt.callLater), `now()` (the time in milliseconds), `announce(card)`
// (KyprX's name card on one screen: `{output, heading, caption, zones}`),
// `toggleAutomaticTiling()` (the daemon asked to switch automatic tiling, `ToggleAutomaticTiling`
// on /Windows), `log(text)`, `overlays()` (the zone windows, one per screen) and `timers` ({live,
// commit, preview, cleanup, quiet}, QML Timers whose `triggered` main.qml routes to `liveTick`,
// `commitTick`, `previewTick`, `cleanupTick` and `quietTick`).
export function create(env) {
    const W = env.Workspace;
    const state = {
        disposed: false,
        settings: null,
        // The last answer that carried arrangements, which an edit to them is read against
        // (`edited`).
        made: null,
        text: "",
        on: false,
        // When the tiling last started (`env.now()`): a window that opens with every zone taken
        // takes the screen with it only FOLLOW_AFTER_MS after it.
        onSince: 0,
        // The engine's own switches of a screen to the desktop a window went to (`elsewhere`), by
        // the screen's name: the id of the desktop the screen left, and when (`env.now()`). What
        // the rest of a burst is told by (`burst`).
        followed: new Map(),
        borders: null,
        focus: [],
        // How many windows the engine has taken in, and how many times a window has joined a
        // surface's tiling: the counts windows are ranked by when one gives way for room
        // (`joinedOn`, `newer`).
        born: 0,
        joins: 0,
        records: new Map(),
        surfaces: new Map(),
        dirty: new Set(),
        // The tiled windows to look at once they are still, by id (`reassert`).
        due: new Set(),
        rulesDue: new Set(),
        // The windows whose keep-above this engine set, by id, to be given back (`raise`).
        raised: new Set(),
        // The windows this engine keeps above KyprX's settings window, one pair each
        // (`constrainOver`).
        pairs: [],
        // The desktops of windows that just closed, by id, each with the id of the window: one of
        // KyprX's left with nothing on it while a screen shows it sends that screen back to the
        // desktop it came from, a moment later (`leftEmpty`).
        emptied: new Map(),
        // When Toggle Automatic Tiling was last pressed (`env.now()`), or -1: the answer that
        // switches automatic tiling within TOGGLE_MS of it is the key's, and its name card shows
        // (`autoSaid`). -1 and not 0 for none, because a clock can start at 0.
        autoAskedAt: -1,
    };

    function log(text) {
        if (env.log) {
            env.log(text);
        }
    }

    // Without a clock every moment is the tiling's first, and no window takes the screen with it.
    function now() {
        return env.now ? Number(env.now()) || 0 : 0;
    }

    function hook(object, name, fn) {
        const signal = object[name];
        if (signal && typeof signal.connect === "function") {
            signal.connect(env.owner, fn);
        }
    }

    // ------------------------------------------------------------------- what drag.mjs reaches for
    //
    // Made here, before the functions below that call `drag`, although every one of those runs
    // only after `create` has returned. A closure that names a `const` declared further down runs,
    // but is compiled with a warning in the compositor's log, once per use (measured in the
    // sandbox: `Variable "drag" is used before its declaration`); everything `core` names is a
    // function declaration, which is there from the start.
    const core = {
        on: function () { return state.on && !!state.settings; },
        auto: function () { return !!state.settings && state.settings.auto; },
        live: function () { return !!state.settings && state.settings.live; },
        gaps: function () { return state.settings.gaps; },
        // Whether a window let go at the top edge is maximized: the person's own value of the
        // compositor's top-edge maximize, as the last reconfigure read it (point 4 at the top).
        maximizeAtTop: function () { return !!state.borders && state.borders.maximize === true; },
        log: log,
        kindOf: kindOf,
        keepsSlot: keepsSlot,
        cursor: function () { return {x: Number(W.cursorPos.x), y: Number(W.cursorPos.y)}; },
        outputs: outputs,
        outputAt: outputAt,
        surfaceOfOutput: surfaceOfOutput,
        ignored: ignored,
        zoneOf: zoneOf,
        bar: bar,
        areaOf: areaOf,
        schedule: schedule,
        untarget: untarget,
        dropped: dropped,
        droppedInPlace: droppedInPlace,
        snapshot: function (rec) {
            if (!core.on() || !state.settings.auto || kindOf(rec) !== "tile" || !rec.key) {
                return null;
            }
            const s = state.surfaces.get(rec.key);
            const list = s ? members(s) : [];
            const area = s ? areaOf(s.output, s.desktop) : null;
            if (!area || list.indexOf(rec.id) < 0) {
                return null;
            }
            const gaps = state.settings.gaps;
            const a = arrangementOf(s);
            const slot = a.id + ":" + list.length;
            const kept = s.adjusted.get(slot);
            // From the lines as they are shown; Esc goes back to the layout kept before.
            const tree = G.copyTree(shownFor(s, slot, list) || kept
                                    || G.treeFor(a.layouts, list.length, G.inner(area, gaps)));
            return {key: s.key, slot: slot, tree: tree, had: kept ? G.copyTree(kept) : null,
                    area: area, gaps: gaps, path: G.fillOrder(tree)[list.indexOf(rec.id)],
                    minOf: minsFor(list, tree)};
        },
        adjust: function (key, slot, tree) {
            const s = state.surfaces.get(key);
            if (s && tree) {
                s.adjusted.set(slot, tree);
            } else if (s) {
                s.adjusted.delete(slot);
            }
        },
    };

    const drag = Drag.create(env, core);

    // ------------------------------------------------------------------- screens and desktops

    function outputs() {
        return listOf(W.screens);
    }

    function outputNamed(name) {
        return outputs().find(function (o) { return String(o.name) === name; }) || null;
    }

    function outputAt(point) {
        return outputs().find(function (o) {
            return G.contains(G.rectOf(o.geometry), point);
        }) || null;
    }

    function desktopWithId(id) {
        return listOf(W.desktops).find(function (d) { return String(d.id) === id; }) || null;
    }

    // The desktop a screen shows. Asked per screen, because a desktop can be chosen per screen;
    // the workspace's one current desktop where that cannot be asked.
    function currentDesktopFor(output) {
        let d = null;
        try {
            if (output && typeof W.currentDesktopForScreen === "function") {
                d = W.currentDesktopForScreen(output);
            }
        } catch (e) {
            d = null;
        }
        return d || W.currentDesktop || null;
    }

    // The activity in use, by the compositor's id for it; "" where no activity manager runs. Then
    // KWin keeps every window's list of activities empty, which is every activity (read in KWin
    // 6.7.5's source, `Window::setOnActivities`), and so every window is counted as on this one.
    function activityNow() {
        return String(W.currentActivity || "");
    }

    // The activity whose surface a window is counted on: the one in use when the window is on it
    // -- an empty list is every activity -- or else the first of its own, a surface not on screen.
    // A window that opens is on the activity in use only (read in KWin 6.7.5's source).
    function activityOf(w) {
        const now = activityNow();
        if (!now) {
            return "";
        }
        const list = listOf(w.activities).map(String);
        return !list.length || list.indexOf(now) >= 0 ? now : list[0];
    }

    function onActivity(w) {
        return activityOf(w) === activityNow();
    }

    function keyFor(outputName, desktopId, activity) {
        return outputName + "|" + desktopId + (activity ? "|" + activity : "");
    }

    // Where a window is: its screen, of its desktops the one that screen shows, or its first, and
    // its activity (`activityOf`). None for a window on every desktop, which belongs to no one
    // surface. A window with a write of the engine's on its way (`rec`) is on the screen it is
    // being moved to: the compositor says which screen it is on only once the move has landed.
    function placeOf(w, rec) {
        let output = w.output;
        if (rec && rec.target && rec.landing) {
            output = outputAt({x: rec.target.x + rec.target.width / 2,
                               y: rec.target.y + rec.target.height / 2}) || output;
        }
        const desktops = listOf(w.desktops);
        if (!output || !desktops.length || w.onAllDesktops === true) {
            return null;
        }
        const shown = currentDesktopFor(output);
        const desktop = desktops.find(function (d) {
            return shown && String(d.id) === String(shown.id);
        }) || desktops[0];
        const outputName = String(output.name);
        const activity = activityOf(w);
        return {key: keyFor(outputName, String(desktop.id), activity), outputName: outputName,
                desktopId: String(desktop.id), activity: activity};
    }

    function visibleKeys() {
        const out = [];
        const activity = activityNow();
        outputs().forEach(function (o) {
            const d = currentDesktopFor(o);
            if (d) {
                out.push(keyFor(String(o.name), String(d.id), activity));
            }
        });
        return out;
    }

    // A surface's `zone` is the id of the zone layout a drag offers there, "" for the whole screen,
    // and null until its arrangement gives it one (`zoneOf`). `shown` is what its last pass laid
    // it out by, `{slot, tree, ids, fitted}` (`layout`), and `plan` that pass's plan with what it
    // was worked out from (`plan`).
    function surfaceFor(outputName, desktopId, activity) {
        const key = keyFor(outputName, desktopId, activity);
        let s = state.surfaces.get(key);
        if (!s) {
            s = {key: key, output: outputName, desktop: desktopId, activity: activity,
                 arrangement: "", zone: null, order: [], adjusted: new Map(), placed: new Map(),
                 cells: [], shown: null, plan: null};
            state.surfaces.set(key, s);
        }
        return s;
    }

    function surfaceOfOutput(output) {
        const d = currentDesktopFor(output);
        return d ? surfaceFor(String(output.name), String(d.id), activityNow()) : null;
    }

    // A screen the person keeps out of the tiling. Its windows keep their place in its surfaces'
    // order, and each is put in its zone again if the screen is let back in (`layout`), but none
    // is laid out, swapped with, resized, turned by the order keys or touched by Toggle Float
    // there, Next Layout and Previous Layout change nothing (`cycle`), and no zone is offered.
    function ignored(s) {
        return !!s && !!state.settings && R.screenIgnored(state.settings, s.output);
    }

    function ignoredKey(key) {
        return !!key && ignored(state.surfaces.get(key));
    }

    function areaOf(outputName, desktopId) {
        const output = outputNamed(outputName);
        const desktop = desktopWithId(desktopId);
        return output && desktop ? areaFor(output, desktop) : null;
    }

    function areaFor(output, desktop) {
        if (!output) {
            return null;
        }
        return G.rectOf(W.clientArea(W.MaximizeArea, output, desktop));
    }

    function desktopList() {
        return listOf(W.desktops);
    }

    function shownAnywhere(d) {
        return outputs().some(function (o) {
            const shown = currentDesktopFor(o);
            return !!shown && String(shown.id) === String(d.id);
        });
    }

    function isOn(w, d) {
        return listOf(w.desktops).some(function (x) { return String(x.id) === String(d.id); });
    }

    // A screen put on a desktop: the call takes the desktop first and the screen second (measured
    // in the sandbox: the other way round is refused). Where desktops cannot be chosen per screen,
    // the workspace's one current desktop.
    function showDesktop(desktop, output) {
        if (typeof W.setCurrentDesktopForScreen === "function") {
            W.setCurrentDesktopForScreen(desktop, output);
        } else {
            W.currentDesktop = desktop;
        }
    }

    // ------------------------------------------------------------------- KyprX's desktops
    //
    // A desktop KyprX made for a window that found every zone taken is known by its name alone:
    // "<base> · <n>" (`chainName`), where <base> is the exact name of another desktop -- the one
    // the window came from -- and <n> a number from 2. Nothing about them is remembered, so one
    // made in an earlier session is found too, and one the person renames becomes theirs. A
    // base's chain is its made desktops, in the order the compositor lists them.

    function markOf(d, list) {
        const mark = chainName(d.name);
        if (!mark) {
            return null;
        }
        return list.some(function (x) {
            return String(x.id) !== String(d.id) && String(x.name) === mark.base;
        }) ? mark : null;
    }

    // The name a desktop's chain goes by: its base when it is one of KyprX's, its own otherwise.
    // So a full "Room · 2" makes "Room · 3", never "Room · 2 · 2"; and the person's own
    // "Work · 2", with no "Work" beside it, makes "Work · 2 · 2", which is then found as KyprX's.
    function baseName(d, list) {
        const mark = markOf(d, list);
        return mark ? mark.base : String(d.name);
    }

    function chainOf(base, list) {
        return list.filter(function (d) {
            const mark = markOf(d, list);
            return !!mark && mark.base === base;
        });
    }

    function desktopNamed(name, list) {
        return list.find(function (d) { return String(d.name) === name; }) || null;
    }

    // ------------------------------------------------------------------- arrangements

    function rotation() {
        return state.settings.arrangements.filter(function (a) { return a.cycle !== false; });
    }

    // The surface's arrangement. A new surface starts on the one its desktop starts on
    // (`startOf`), and one whose arrangement is gone -- deleted on the Tiling tab -- goes back to
    // it.
    function arrangementOf(s) {
        const list = state.settings.arrangements;
        let a = list.find(function (x) { return x.id === s.arrangement; }) || null;
        if (!a) {
            a = startOf(s);
            putOn(s, a);
        }
        return a;
    }

    // The arrangement a surface's desktop starts on: the one the Tiling tab chose for the
    // desktop's name -- for one KyprX made, the name of the desktop it was made from
    // (`baseName`) -- when it is an arrangement of the answer's, and the first in the rotation
    // otherwise. By name, as the tab chooses it, so that the choice outlives a login, where a
    // desktop keeps its name; and Next and Previous Layout move a screen on from it until the
    // next one, as they always did.
    function startOf(s) {
        const list = desktopList();
        const d = list.find(function (x) { return String(x.id) === s.desktop; }) || null;
        const chosen = d ? state.settings.desktops.get(baseName(d, list)) : undefined;
        const all = state.settings.arrangements;
        return all.find(function (x) { return x.id === chosen; }) || rotation()[0] || all[0];
    }

    // The names of the desktops whose chosen arrangement differs between two answers.
    function choicesMoved(before, after) {
        const was = before ? before.desktops : new Map();
        const names = new Set(Array.from(was.keys()).concat(Array.from(after.desktops.keys())));
        return Array.from(names).filter(function (name) {
            return was.get(name) !== after.desktops.get(name);
        });
    }

    // Every surface of a desktop whose chosen arrangement changed onto it at once, on every
    // screen and activity -- those of the desktops KyprX made from it too -- and only those: an
    // answer that changes something else leaves a screen Next Layout moved where it is.
    function startAgain(names) {
        if (!names.length) {
            return;
        }
        const list = desktopList();
        state.surfaces.forEach(function (s) {
            const d = list.find(function (x) { return String(x.id) === s.desktop; }) || null;
            if (d && names.indexOf(baseName(d, list)) >= 0) {
                putOn(s, startOf(s));
            }
        });
    }

    // A surface onto an arrangement, and its zone layout with it, to the arrangement's own.
    function putOn(s, a) {
        s.arrangement = a.id;
        s.zone = homeOf(a);
    }

    function homeOf(a) {
        const home = state.settings.homes.get(a.id);
        return typeof home === "string" ? home : "";
    }

    // The zone layout a drag offers on a surface (`zone`): an entry of the pool, or the whole
    // screen. One that is not in the pool any more, or that a drag no longer offers, is put back on
    // the arrangement's own before it is answered. "" -- the whole screen, picked in the selector
    // or with the layout keys -- is always there, and stays.
    function zoneOf(s) {
        const a = arrangementOf(s);
        const zones = state.settings.zones;
        if (s.zone !== "" && !(zones.has(s.zone) && zones.get(s.zone).drag)) {
            s.zone = homeOf(a);
        }
        return s.zone === "" ? WHOLE_SCREEN : zones.get(s.zone);
    }

    // The selector a drag shows on a surface's screen, and the list manual tiling's layout keys
    // walk there: the whole screen, the first MAX_OFFERED zone layouts a drag offers in the pool's
    // order, and the surface's own after them when it is not among those.
    function bar(s) {
        const own = zoneOf(s);
        const list = [WHOLE_SCREEN].concat(state.settings.pool.filter(function (z) {
            return z.drag;
        }).slice(0, MAX_OFFERED));
        if (list.indexOf(own) < 0) {
            list.push(own);
        }
        return list;
    }

    function treeOf(s, a, count, box) {
        const kept = s.adjusted.get(a.id + ":" + count);
        return kept ? kept : G.treeFor(a.layouts, count, box);
    }

    // ------------------------------------------------------------------- windows

    // What a window is to the tiling now: "never", "float" or "tile" -- what it asks to be
    // (`wanted`), except that a window asking to tile floats while its screen has no room for it
    // (`outOfRoom`, set by `layout`): the engine never makes a window smaller than it can be.
    function kindOf(rec) {
        const kind = wanted(rec);
        return kind === "tile" && rec.outOfRoom ? "float" : kind;
    }

    // What a window asks to be, room or not. The first layer decides alone where it is fixed; then
    // the person's Toggle Float, then the rules.
    function wanted(rec) {
        const rule = rec.rule;
        if (!rule || rule.kind === "never") {
            return "never";
        }
        if (rule.fixed) {
            return rule.kind;
        }
        if (rec.override) {
            return rec.override;
        }
        return rule.kind;
    }

    // A maximized or full-screen window keeps its place in the layout and is not moved.
    function keepsSlot(rec) {
        return rec.w.fullScreen === true || (Number(rec.w.maximizeMode) || 0) !== 0;
    }

    function isMember(rec, s) {
        return !!rec && rec.key === s.key && kindOf(rec) === "tile" && rec.w.minimized !== true
            && !ignored(s);
    }

    // The windows a surface lays out, in its order. Minimized ones leave the count, and a screen
    // kept out of the tiling has none.
    function members(s) {
        return s.order.filter(function (id) { return isMember(state.records.get(id), s); });
    }

    // A window a surface would lay out if it had room: one of its members, or one asking to tile
    // there that floats until there is room for it (`plan`).
    function isCandidate(rec, s) {
        return !!rec && rec.key === s.key && wanted(rec) === "tile" && rec.w.minimized !== true
            && !ignored(s);
    }

    function candidates(s) {
        return s.order.filter(function (id) { return isCandidate(state.records.get(id), s); });
    }

    // A window the engine may put in another zone, or float for room: not one that keeps its slot,
    // and not one in the person's hand.
    function movable(rec) {
        return !keepsSlot(rec) && !drag.busy(rec);
    }

    // What a window needs of its zone (`needsOf`), and nothing for one that keeps its slot, which
    // is not laid out in it.
    function needOf(rec) {
        return keepsSlot(rec) ? null : needsOf(rec);
    }

    // What a window needs of a zone, with what its frame adds held per window (`rec.extra`): a
    // larger reading is taken at once, a smaller one only when it is smaller by more than
    // TOLERANCE, and an axis with no content to measure against keeps what it had. Read fresh at
    // every pass, the need would not hold still: at a fractional scale an X11 window's frame less
    // its content moves by a pixel from one write to the next (a need of 999 x 745, then
    // 999 x 746, measured in the sandbox at 1.2), and a window laid out at its title bar's height
    // alone has no content to measure the bar against (its need lost the bar, found by a random
    // search of the harness). Either way the plan, the lines and the writes would change at every
    // pass, each pass bringing the next. A title bar that goes -- KyprX hiding it -- is smaller by
    // far more than TOLERANCE, and is taken.
    function needsOf(rec) {
        const seen = R.frameExtra(rec.w);
        rec.extra = {width: steadyExtra(rec.extra.width, seen.width),
                     height: steadyExtra(rec.extra.height, seen.height)};
        return R.needsWith(rec.w, rec.extra);
    }

    function steadyExtra(held, seen) {
        if (seen === null) {
            return held;
        }
        return held === null || seen > held || held - seen > G.TOLERANCE ? seen : held;
    }

    // When a window joined a surface's tiling, by the engine's own count (`state.joins`), kept on
    // the window for each surface it joined (`joins`, by the surface's key): a window back on a
    // surface -- a desktop shown again for a window on two, a window brought back from another
    // screen or desktop -- has the place it had there, and so has a window minimized and restored.
    // Toggle Float, the rules floating a window or leaving it out (`judge`), and the tiling
    // stopping or going manual, take it away. A window that has not joined yet ranks as the
    // newest.
    function joinedOn(rec, s) {
        return rec.joins.has(s.key) ? rec.joins.get(s.key) : Infinity;
    }

    // Which of two windows joined a surface later, for a sort with the newest first; of two that
    // joined together, or have not joined yet, the one that opened later.
    function newer(x, y, s) {
        const a = joinedOn(x, s);
        const b = joinedOn(y, s);
        if (a !== b) {
            return a > b ? -1 : 1;
        }
        return y.born - x.born;
    }

    // The windows a surface would lay out that have not joined it join it now, in the order they
    // opened in. Only as the surface is laid out, so that a window on a desktop nobody looks at
    // joins it when it is shown; the place of a window in the order cannot say it instead, since
    // Move, Set Master, Rotate and `newWindow` change that. A window that no longer asks to tile --
    // floated by the rules -- waits for room no more.
    function noteJoins(s) {
        const fresh = [];
        s.order.forEach(function (id) {
            const rec = state.records.get(id);
            if (!rec) {
                return;
            }
            if (isCandidate(rec, s)) {
                if (!rec.joins.has(s.key)) {
                    fresh.push(rec);
                }
            } else if (wanted(rec) !== "tile") {
                rec.outOfRoom = false;
            }
        });
        fresh.sort(function (x, y) { return x.born - y.born; }).forEach(function (rec) {
            state.joins += 1;
            rec.joins.set(s.key, state.joins);
        });
    }

    function activeRecord() {
        const w = W.activeWindow;
        return w ? state.records.get(String(w.internalId)) || null : null;
    }

    function isActive(w) {
        const active = W.activeWindow;
        return !!active && String(active.internalId) === String(w.internalId);
    }

    // An application's own window, rather than a dialog of one: what opens in the middle of the
    // screen, is kept above the others, or goes to a desktop of its own. A dialog stays with its
    // window, and above it without keep-above of its own (measured in the sandbox's facts
    // scenario).
    function mainWindow(w) {
        return w.transient !== true && w.modal !== true && w.dialog !== true;
    }

    // A window the focus may go to now: one the focus keys may land on, not minimized, on the
    // activity in use, and on a desktop a screen shows or on every desktop. Never one only on
    // another activity, hidden but not minimized: made the active window, it would have the
    // compositor switch to that activity (read in KWin 6.7.5's source, `Workspace::activateWindow`).
    function inSight(rec, visible) {
        if (!rec.rule || !rec.rule.focusable || rec.w.minimized === true || !onActivity(rec.w)) {
            return false;
        }
        if (rec.w.onAllDesktops === true) {
            return true;
        }
        const place = placeOf(rec.w);
        return !!place && visible.indexOf(place.key) >= 0;
    }

    function activeSurface() {
        const rec = activeRecord();
        if (rec && rec.key && state.surfaces.has(rec.key)) {
            return state.surfaces.get(rec.key);
        }
        const output = W.activeScreen;
        return output ? surfaceOfOutput(output) : null;
    }

    function focusedIn(s, except) {
        for (let i = 0; i < state.focus.length; i++) {
            const id = state.focus[i];
            if (id !== except && isMember(state.records.get(id), s)) {
                return id;
            }
        }
        return "";
    }

    // A window into a surface's order: at the end, as the master, or before or after the focused
    // window (`newWindowPosition` 0 to 3). The focused window is the most recent one other than
    // the new window, which the compositor has usually activated already by `windowAdded`.
    function insert(s, rec, position) {
        if (s.order.indexOf(rec.id) >= 0) {
            return;
        }
        let at = s.order.length;
        if (position === 1) {
            at = 0;
        } else if (position === 2 || position === 3) {
            const focused = focusedIn(s, rec.id);
            if (focused) {
                at = s.order.indexOf(focused) + (position === 3 ? 1 : 0);
            }
        }
        s.order.splice(at, 0, rec.id);
    }

    function takeOut(rec) {
        const s = rec.key ? state.surfaces.get(rec.key) : null;
        if (s) {
            const i = s.order.indexOf(rec.id);
            if (i >= 0) {
                s.order.splice(i, 1);
            }
            s.placed.delete(rec.id);
            schedule(s.key);
        }
    }

    // A window into the surface it is on now. One that arrives there (`fresh`) goes where a new
    // window goes, any other at the end; one the tiling never takes is in no surface at all.
    //
    // A window waiting for room on one surface waits on no other: where it arrives, it is laid out,
    // or floated for room, as any window that arrives there is.
    function settle(rec, fresh) {
        const place = kindOf(rec) === "never" ? null : placeOf(rec.w, rec);
        const key = place ? place.key : "";
        if (rec.key !== key) {
            takeOut(rec);
            rec.key = key;
            untarget(rec);
            rec.outOfRoom = false;
        }
        if (!place) {
            return;
        }
        const s = surfaceFor(place.outputName, place.desktopId, place.activity);
        if (s.order.indexOf(rec.id) < 0) {
            insert(s, rec, fresh && kindOf(rec) === "tile" ? state.settings.newWindow : 0);
        }
        schedule(s.key);
    }

    // The rules for one window, and the window into its surface. `fresh` places it where a new
    // window goes.
    //
    // A window that no longer asks to tile -- floated by a title or class rule, put on every
    // desktop, or one the tiling never takes -- forgets when it joined the surface it is on, as a
    // window floated by Toggle Float does: asking to tile again, it joins as the newest, and with
    // no room it is the one that floats, not the window that took the room it left. Kept, it came
    // back ahead of that window, which was written and raised back out into the middle (seen in
    // tests/engine_harness.mjs, `roomRuleFloat`). Minimized, a window still asks to tile, and keeps
    // its place.
    function judge(rec, fresh) {
        const before = kindOf(rec);
        rec.rule = R.classify(rec.w, state.settings);
        if (kindOf(rec) !== before) {
            untarget(rec);
        }
        if (wanted(rec) !== "tile") {
            rec.joins.delete(rec.key);
        }
        settle(rec, fresh);
    }

    function adopt(w) {
        const id = String(w.internalId);
        let rec = state.records.get(id);
        if (rec) {
            return rec;
        }
        state.born += 1;
        // Of the engine's writes, the last one (`written`) and the one in progress (`writing`,
        // `inside`, `landing`, `sentAt`, `waited`, `answering`: `write`, `send`); and what the
        // window did by itself since (`stirred`, `drift`: `reassert`).
        rec = {id: id, w: w, rule: null, override: "", outOfRoom: false, joins: new Map(),
               born: state.born, key: "", target: null, written: null, writing: false,
               inside: false, landing: false, sentAt: 0, waited: false, answering: false,
               stirred: false, drift: {back: [], answer: null, stands: "", moved: 0, grown: false},
               extra: {width: null, height: null}, laidFor: null};
        state.records.set(id, rec);
        hook(w, "windowClassChanged", function () { rulesAgain(rec); });
        hook(w, "captionChanged", function () { rulesAgain(rec); });
        hook(w, "desktopsChanged", function () { moved(rec); rulesAgain(rec); tidySoon(); });
        hook(w, "activitiesChanged", function () { moved(rec); });
        hook(w, "outputChanged", function () { moved(rec); });
        hook(w, "minimizedChanged", function () { changed(rec); });
        hook(w, "maximizedChanged", function () { changed(rec); });
        hook(w, "fullScreenChanged", function () { changed(rec); });
        hook(w, "frameGeometryChanged", function () { geometryChanged(rec); });
        hook(w, "interactiveMoveResizeStarted", function () {
            if (!state.disposed) {
                drag.started(rec);
            }
        });
        hook(w, "interactiveMoveResizeStepped", function (geometry) {
            if (!state.disposed) {
                drag.stepped(rec, geometry);
            }
        });
        hook(w, "interactiveMoveResizeFinished", function () {
            if (!state.disposed) {
                drag.finished(rec);
            }
        });
        return rec;
    }

    // The rules run again when a window's class or title changes -- a class is often not final at
    // `windowAdded` -- and later, so that a burst of changes is read once.
    function rulesAgain(rec) {
        if (state.disposed) {
            return;
        }
        state.rulesDue.add(rec.id);
        env.later(flushRules);
    }

    function flushRules() {
        if (state.disposed || !state.settings) {
            return;
        }
        const ids = Array.from(state.rulesDue);
        state.rulesDue.clear();
        ids.forEach(function (id) {
            const rec = state.records.get(id);
            // A window the rules let in only now -- its class came late -- is a new window to the
            // tiling, and goes where a new window goes.
            if (rec) {
                judge(rec, kindOf(rec) === "never");
            }
        });
    }

    function moved(rec) {
        if (state.disposed || !state.settings || drag.busy(rec)) {
            return;
        }
        settle(rec, true);
    }

    function changed(rec) {
        if (state.disposed || !state.settings) {
            return;
        }
        untarget(rec);
        if (rec.key) {
            schedule(rec.key);
        }
    }

    // A window the engine no longer holds to a zone. `landing` says a write to that zone is on its
    // way, and goes with it: left behind, it would be waited for once more at the window's next
    // look (`reassert`).
    function untarget(rec) {
        rec.target = null;
        rec.landing = false;
    }

    // ------------------------------------------------------------------- laying out

    function schedule(key) {
        if (!key || state.disposed) {
            return;
        }
        state.dirty.add(key);
        env.later(flush);
    }

    function scheduleVisible() {
        visibleKeys().forEach(schedule);
    }

    // A panel takes its strip of a screen out of the usable area, and the compositor tells a
    // script nothing when that area changes, so a panel that comes, goes, or changes size or edge
    // has every screen on show laid out again. Otherwise the tiled windows would keep their
    // rectangles -- short of a strip set free, or pushed off a new one by the compositor's own
    // check -- until something else laid the screen out. The layout reads the new area: the
    // compositor works it out before `windowAdded`, and for a panel that goes or changes, in a
    // timer of no delay started before the signal or in the same call that moves the panel, both
    // of which come before what `Qt.callLater` put off (read in KWin 6.7.5's source --
    // `addWaylandWindow`, `removeWindow`, LayerShellV1Window -- and in Qt's event loop; not
    // measured). A panel whose reserved strip changes while its size does not -- its visibility
    // setting changed -- gives no sign at all.
    function isPanel(w) {
        return w.dock === true;
    }

    function flush() {
        if (state.disposed) {
            return;
        }
        const keys = Array.from(state.dirty);
        state.dirty.clear();
        const visible = visibleKeys();
        keys.forEach(function (key) {
            // A desktop nobody looks at is laid out when it is shown.
            if (visible.indexOf(key) >= 0) {
                try {
                    layout(state.surfaces.get(key));
                } catch (e) {
                    log("could not lay out " + key + ": " + e);
                }
            }
        });
    }

    // What each zone's window needs of its cell, by the zone's path: what a divider is held back
    // by. The need, and the half of the gap between that the zone gives up on each side where it
    // has a neighbour (`G.leastOf`) -- as the room made for a window counts it, so a key, an edge
    // and that room agree to the pixel.
    function minsFor(list, tree) {
        return G.leastOf(tree, state.settings.gaps, list.map(function (id) {
            return needOf(state.records.get(id));
        }));
    }

    // The tree a surface was last laid out by, when that was for these windows in this order and
    // under this slot: what the keys and an edge start from. A layout with its lines moved for
    // room is what the person sees, so one press is one step from where they see the line --
    // started from the layout's own, the first Shrink would land on the line room was made at and
    // do nothing -- and what they resize from it is kept, lines moved for room and all.
    function shownFor(s, slot, list) {
        return s.shown && s.shown.slot === slot && s.shown.ids.join("\n") === list.join("\n")
            ? s.shown.tree : null;
    }

    // ------------------------------------------------------------------- room
    //
    // The compositor does not hold a window to its minimum size (rules.mjs, `needs`), so a zone
    // smaller than a window can be is one its window is drawn too small for, or spills out of over
    // its neighbours. On the desk this was written for -- one screen, its usable area less its
    // gaps 2806 x 1180 -- Balanced's stacked zones are 585 px tall, and an X11 window whose minimum
    // is 722 px at an Xwayland scale of 1.2 needs 601.7 for its content alone (both read off that
    // desk). So each pass works out which of a surface's windows it lays out, in which zones and by
    // which lines (`plan`), each step only when the one before leaves a window short:
    //
    // 0. A window that does not fit the area less its gaps even alone floats at once, whenever it
    //    joined: no layout has room for it, and kept in, it would have every newer window give way
    //    in vain.
    // 1. The lines move (`G.fit`): a zone too small takes just the pixels it lacks from its
    //    neighbours, none of which goes below its own window's minimum or MIN_SHARE.
    // 2. Windows trade zones (`G.exchange`), the newest still short first, each tried in the zones
    //    in fill order, and only a trade after which both fit and no other window stops fitting.
    // 3. A window gives way: of the windows whose leaving lets the rest fit after 1 and 2, the one
    //    that joined the surface last (`joinedOn`); when no one window's leaving does, the newest
    //    of those still short, and the choice is made again among the rest.
    //
    // Before any of it, past MOST_TILED windows the ones that joined last wait for room without
    // being tried, so a pass never works out the room of more than MOST_TILED windows, whatever
    // the setting for a window that finds every zone taken.
    //
    // A window that keeps its slot, or is in the person's hand, is never traded and never the one
    // that gives way, and stays what it was to the room: tiled, what a held one needs counts all
    // the same -- one that keeps its slot needs nothing of it, since it is not laid out in it --
    // and waiting for room, it waits on, taking no zone meanwhile. A window that gives way floats
    // until there is room for it (`floatForRoom`), and is tiled again by itself at the first pass
    // that finds room. The lines moved for room hold for that pass alone -- the next starts from
    // the layout's own again (`treeOf`), so they go back by themselves once the window that needed
    // them goes or needs less -- and a trade is kept in the surface's order, which every key, the
    // drag and the name card read a window's zone from.

    // A surface's plan, `{order, list, base, tree, rects, out}`: the order its windows are to be
    // in, with the zones traded for room; the windows laid out in fill order, the layout's own tree
    // for them and the tree with its lines moved for room, their rectangles; and the windows that
    // float for want of room. It writes nothing, so the name card asks it too.
    //
    // Worked out again from the order with its trades until that order no longer changes, so that
    // the next pass, which starts from it, comes to the same plan. Which trades are found depends
    // on the order they are tried from (`G.exchange` moves only a window still short), and the
    // order a trade leaves is the next pass's start: from it, the next pass found another window
    // whose leaving let the rest fit, and an unrelated pass -- a title changing -- floated a tiled
    // window and tiled the one floated before (`roomOnePass` in tests/engine_harness.mjs: windows
    // that need 689, 1225, nothing and 952 px). In a random search of 9000 runs of windows with
    // random minimums opening and closing, at three overflow settings, on Wayland and X11 (a
    // scratch search, not one of the checks), 49507 of the 52050 plans settled at once, 2516 after
    // one more turn and 27 after two, and none was left unsettled (measured). The guard stops at
    // as many turns as windows, and an order not settled by then is laid out as it is.
    //
    // The last one is kept and given again while nothing it is worked out from has changed -- the
    // windows and their order, what each needs, which can move and which of those that cannot are
    // waiting, when each joined, the usable area, the arrangement and the layouts kept for it, the
    // settings -- since a pass runs at every change of a window's place, and a plan can be long to
    // work out; and so is it from the order it settled at, which the next pass starts from. Nine
    // windows that each need a whole column's height (`roomNine` in tests/engine_harness.mjs) took
    // 1399 fits, 170 to 200 ms in PySide6's QJSEngine, for the pass the ninth joined in; the four
    // windows of the desk's case took 9 fits in all; `roomOnePass`'s fourth window, whose plan
    // settles a turn later, 31 fits for its pass and none for the next, against 12 and 13 when the
    // next pass did the turn instead (all measured in that engine, the same V4 the compositor runs
    // scripts in, and not in the compositor).
    function plan(s, area) {
        const a = arrangementOf(s);
        const known = new Map();
        let order = candidates(s);
        order.forEach(function (id) {
            const rec = state.records.get(id);
            known.set(id, {rec: rec, need: needOf(rec), movable: movable(rec)});
        });
        const kept = Array.from(s.adjusted.entries()).filter(function (entry) {
            return entry[0].indexOf(a.id + ":") === 0;
        });
        const keyOf = function (ids) {
            return JSON.stringify([area, a.id, kept, ids.map(function (id) {
                const k = known.get(id);
                return [id, k.need, k.movable, joinedOn(k.rec, s), k.rec.born,
                        !k.movable && k.rec.outOfRoom];
            })]);
        };
        const key = keyOf(order);
        if (s.plan && s.plan.settings === state.settings && s.plan.keys.indexOf(key) >= 0) {
            return s.plan.result;
        }
        let result = planned(s, a, area, order, known);
        let next = traded(order, result.list);
        for (let guard = 0; guard < order.length && next.join("\n") !== order.join("\n"); guard++) {
            order = next;
            result = planned(s, a, area, order, known);
            next = traded(order, result.list);
        }
        const settled = next.join("\n") === order.join("\n");
        result.order = next;
        s.plan = {settings: state.settings, keys: settled ? [key, keyOf(next)] : [key],
                  result: result};
        return result;
    }

    // `order` with the windows of `list` in the places they hold in it, in the order of `list`:
    // how a trade of zones is kept, the windows swapping places among their own positions, as
    // Rotate turns them, and every other window staying where it is.
    function traded(order, list) {
        const out = order.slice();
        const at = list.map(function (id) { return order.indexOf(id); }).sort(function (x, y) {
            return x - y;
        });
        at.forEach(function (position, k) { out[position] = list[k]; });
        return out;
    }

    function planned(s, a, area, list, known) {
        const box = G.inner(area, state.settings.gaps);
        const out = [];
        const newestFirst = function (x, y) {
            return newer(known.get(x).rec, known.get(y).rec, s);
        };
        const without = function (ids, id) {
            return ids.filter(function (x) { return x !== id; });
        };
        let left = list.filter(function (id) {
            const k = known.get(id);
            if (k.movable ? !G.holds(box, k.need) : k.rec.outOfRoom) {
                out.push(id);
                return false;
            }
            return true;
        });
        // Past MOST_TILED, the newest that can move wait, untried (the comment on MOST_TILED).
        const over = left.filter(function (id) { return known.get(id).movable; })
            .sort(newestFirst);
        for (let i = 0; left.length > MOST_TILED && i < over.length; i++) {
            left = without(left, over[i]);
            out.push(over[i]);
        }
        let tried = attempt(s, a, area, left, known);
        for (let guard = 0; guard < list.length && shortOf(tried, known).length; guard++) {
            const order = left.filter(function (id) { return known.get(id).movable; })
                .sort(newestFirst);
            const rests = new Map();
            let victim = "";
            for (let i = 0; i < order.length && !victim; i++) {
                rests.set(order[i], attempt(s, a, area, without(left, order[i]), known));
                if (!shortOf(rests.get(order[i]), known).length) {
                    victim = order[i];
                }
            }
            // No one window's leaving helps: every window that can move was tried, the newest of
            // those still short among them, and what is left without it is the next round's start.
            if (!victim) {
                victim = shortOf(tried, known).sort(newestFirst)[0];
            }
            left = without(left, victim);
            out.push(victim);
            tried = rests.get(victim);
        }
        return {list: tried.order, base: tried.base, tree: tried.fit.tree, rects: tried.fit.rects,
                out: out};
    }

    // The windows of `ids`, in that order, on the surface's layout for that many: its lines moved
    // for what each needs, and then, when a window that can move is still short, zones traded.
    // `{order, base, fit}`: the windows in fill order after any trade, the layout's own tree, and
    // what `G.fit` made of it for them.
    function attempt(s, a, area, ids, known) {
        if (!ids.length) {
            return {order: [], base: null, fit: {tree: null, rects: [], misfits: []}};
        }
        const gaps = state.settings.gaps;
        const base = treeOf(s, a, ids.length, G.inner(area, gaps));
        const facts = ids.map(function (id) { return known.get(id); });
        const needs = facts.map(function (k) { return k.need; });
        const fitted = G.fit(base, area, gaps, needs);
        if (!fitted.misfits.some(function (z) { return facts[z].movable; })) {
            return {order: ids, base: base, fit: fitted};
        }
        const prefer = facts.map(function (k, i) { return i; }).sort(function (i, j) {
            return newer(facts[i].rec, facts[j].rec, s);
        });
        const traded = G.exchange(base, area, gaps, needs,
                                  facts.map(function (k) { return k.movable; }), prefer);
        return {order: traded.order.map(function (i) { return ids[i]; }), base: base,
                fit: traded.fit};
    }

    // The windows an attempt leaves short that could give way: those that can move.
    function shortOf(tried, known) {
        return tried.fit.misfits.map(function (z) { return tried.order[z]; }).filter(function (id) {
            return known.get(id).movable;
        });
    }

    // "a", "a and b", "a, b and c".
    function together(names) {
        return names.length < 2 ? names.join("")
            : names.slice(0, -1).join(", ") + " and " + names[names.length - 1];
    }

    function size(r) {
        return r.width + " x " + r.height;
    }

    function needsAny(need) {
        return !!need && (need.width > 0 || need.height > 0);
    }

    // Zones traded for room are kept in the surface's order (`traded`), and each ring of windows
    // laid out that moved is said, with what those of them that need anything need: the windows of
    // `list` in the order they were in, against `list`.
    function keepTrades(s, order, list) {
        const was = s.order.filter(function (id) { return list.indexOf(id) >= 0; });
        const now = traded(s.order, order);
        now.forEach(function (id, position) { s.order[position] = id; });
        const seen = new Set();
        for (let k = 0; k < list.length; k++) {
            if (seen.has(k) || list[k] === was[k]) {
                continue;
            }
            const names = [];
            const needing = [];
            for (let j = k; !seen.has(j); j = was.indexOf(list[j])) {
                seen.add(j);
                const rec = state.records.get(list[j]);
                const need = needOf(rec);
                names.push(nameOf(rec));
                if (needsAny(need)) {
                    needing.push(nameOf(rec) + " needs " + size(need));
                }
            }
            log("to make room on " + s.key + ", " + together(names) + " trade zones"
                + (needing.length ? " (" + needing.join(", ") + ")" : ""));
        }
    }

    // Whether the lines of a surface's layout are moved for room is said when that changes, with
    // what each window short in the layout's own lines needs, and what its zone there is.
    function sayFitted(s, was, p, area) {
        const now = !!(s.shown && s.shown.fitted);
        if (now === was) {
            return;
        }
        if (!now) {
            log("the lines on " + s.key + " are the layout's own again");
            return;
        }
        const own = G.zoneRects(p.base, area, state.settings.gaps);
        const short = [];
        p.list.forEach(function (id, k) {
            const rec = state.records.get(id);
            const need = needOf(rec);
            if (!G.holds(own[k], need)) {
                short.push(nameOf(rec) + " needs " + size(need) + ", its zone of the layout is "
                           + size(own[k]));
            }
        });
        log("the lines on " + s.key + " move to give each window its minimum: "
            + short.join("; "));
    }

    function layout(s) {
        if (!s || !state.on || !state.settings.auto) {
            return;
        }
        // A screen kept out of the tiling lays nothing out, and its windows forget where the engine
        // put them. `place` writes nothing to a window whose target is its zone already, and only
        // a window moved by a drag forgets its target by itself: one resized by its edge there, or
        // moved by a key of the compositor's or by its application, would otherwise be taken for
        // one its application moved when the screen is let back in (`stillThere`, as a window on
        // a desktop nobody looked at is) -- put back as that, counted, and left where it is once
        // where it puts itself stands. A write still on its way there is not tried again either.
        if (ignored(s)) {
            s.order.forEach(function (id) {
                const rec = state.records.get(id);
                if (rec) {
                    untarget(rec);
                }
            });
            return;
        }
        const area = areaOf(s.output, s.desktop);
        if (!area) {
            return;
        }
        const gaps = state.settings.gaps;
        noteJoins(s);
        const p = plan(s, area);
        keepTrades(s, p.order, p.list);
        p.list.forEach(function (id) {
            const rec = state.records.get(id);
            if (rec.outOfRoom) {
                rec.outOfRoom = false;
                untarget(rec);
                holdAbove(rec, "tile");
                const need = needsOf(rec);
                log(nameOf(rec) + " is tiled again on " + s.output + ": there is room for it now"
                    + (needsAny(need) ? " (it needs " + size(need) + ")" : ""));
            }
        });
        const was = !!(s.shown && s.shown.fitted);
        s.placed = new Map();
        s.cells = [];
        s.shown = p.list.length ? {slot: arrangementOf(s).id + ":" + p.list.length, tree: p.tree,
                                   ids: p.list.slice(), fitted: p.tree !== p.base} : null;
        sayFitted(s, was, p, area);
        if (p.list.length) {
            const cellRects = G.cells(p.tree, area, gaps);
            for (let k = 0; k < p.list.length; k++) {
                const rec = state.records.get(p.list[k]);
                s.placed.set(rec.id, p.rects[k]);
                s.cells.push({id: rec.id, rect: cellRects[k]});
                rec.laidFor = needOf(rec);
                if (!keepsSlot(rec) && !drag.busy(rec)) {
                    place(rec, p.rects[k]);
                }
            }
        }
        // After the tiled windows, so that the raise is the pass's last change to what is in front.
        p.out.forEach(function (id) {
            const rec = state.records.get(id);
            if (!rec.outOfRoom) {
                rec.outOfRoom = true;
                untarget(rec);
                floatForRoom(rec, s, area, p.list.length);
            }
        });
    }

    // A window that gives way for room: written once, as it leaves the tiling -- in the middle of
    // the usable area at FLOAT_FRACTION of its size, never smaller than it needs, as Toggle Float
    // leaves a window -- and raised once, so that it is not left under the windows it is centred
    // over, where nobody would know it was there. Nothing keeps it above: a click on a tiled window
    // covers it again, as it would any floating window.
    //
    // `Workspace.raiseWindow` puts the window above the others and nothing more: measured in the
    // sandbox's facts scenario, on a Wayland and on an X11 window below the active one, it went to
    // the top of `Workspace.stackingOrder` while the active window stayed the active one and
    // neither was kept above -- the person's focus is not taken. Without it nothing is raised, and
    // a throw is logged and goes no further: the window has floated all the same.
    function floatForRoom(rec, s, area, tiled) {
        const need = needsOf(rec);
        rec.laidFor = need;
        write(rec, aside(area, need));
        if (typeof W.raiseWindow === "function") {
            try {
                W.raiseWindow(rec.w);
            } catch (e) {
                log("could not raise " + nameOf(rec) + ": " + e);
            }
        }
        holdAbove(rec, "float");
        const box = G.inner(area, state.settings.gaps);
        if (!G.holds(box, need)) {
            log(nameOf(rec) + " floats in the middle of " + s.output + ": it needs " + size(need)
                + ", and the area less its gaps is " + size(box));
        } else {
            log(nameOf(rec) + " floats in the middle of " + s.output + " until there is room for it"
                + " among the " + tiled + " windows tiled there"
                + (needsAny(need) ? " (it needs " + size(need) + ")" : ""));
        }
    }

    // The middle of the usable area at FLOAT_FRACTION of its size, or, on an axis where the window
    // needs more than the area has, the area's own edge: centred, the window would start above the
    // screen or past its left side -- over the next screen, or with its title bar out of reach.
    function aside(area, need) {
        const r = G.centred(area, FLOAT_FRACTION, need);
        return {x: r.width > area.width ? Math.ceil(area.x) : r.x,
                y: r.height > area.height ? Math.ceil(area.y) : r.y,
                width: r.width, height: r.height};
    }

    // Every write of the engine's goes through here, and the last one is kept: see `place`. What
    // the compositor makes of the window inside the write -- X11's change -- is the write landing
    // (`writing`, `geometryChanged`).
    function write(rec, rect) {
        rec.written = rect;
        rec.writing = true;
        try {
            rec.w.frameGeometry = env.rect(rect.x, rect.y, rect.width, rect.height);
        } finally {
            rec.writing = false;
        }
    }

    // The target is stored before the write: on X11 the change arrives inside it.
    //
    // A window already where it is to go is not written to -- unless the engine's last write sent
    // it somewhere else. On Wayland that write may still be on its way: the window reads as where
    // it was until it lands, and when it lands the window is taken as settled where it should not
    // be. Seen in the sandbox (scripts/sandbox.sh), under load: a window tiled again and closed a
    // few milliseconds later left its neighbour at the smaller zone it had for three windows, for
    // good, because the way back to the zone for two was skipped as "already there".
    //
    // Within TOLERANCE counts as there only where it also holds what the window needs: room is made
    // to the pixel (`G.fit`), and a zone that moved by a pixel or two to give a window its minimum
    // has to be written, or the window would stay those pixels short of it.
    function place(rec, rect) {
        const need = needsOf(rec);
        if (rec.target && G.near(rec.target, rect) && G.holds(rec.target, need)) {
            stillThere(rec);
            return;
        }
        rec.target = rect;
        anotherZone(rec);
        const elsewhere = !!rec.written && !G.near(rec.written, rect);
        const frame = G.rectOf(rec.w.frameGeometry);
        if (!elsewhere && G.near(frame, rect) && G.holds(frame, need)) {
            rec.landing = false;
            return;
        }
        send(rec);
    }

    // The window written to its zone, and looked at once it is still: whatever it does until then
    // is its answer to the write (`answering`). X11's change, and a Wayland window's that only
    // moves, come inside the write (`inside`); a Wayland window's new size lands 2 to 7 ms later
    // (`landing`), and may land later still under load (`reassert`).
    function send(rec) {
        rec.inside = false;
        rec.landing = true;
        rec.answering = true;
        rec.waited = false;
        rec.sentAt = now();
        write(rec, rec.target);
        rec.landing = !rec.inside && !G.near(G.rectOf(rec.w.frameGeometry), rec.target);
        lookAgain(rec);
    }

    function geometryChanged(rec) {
        if (state.disposed || drag.geometryChanged(rec)) {
            return;
        }
        if (isPanel(rec.w)) {
            scheduleVisible();
            return;
        }
        if (rec.writing) {
            rec.inside = true;
            return;
        }
        if (!core.on() || !state.settings.auto) {
            return;
        }
        // A window waiting for room has no zone to be put back in, but a need of its that drops
        // can make the room it waits for (`shrunk`).
        if (!rec.target) {
            if (rec.outOfRoom) {
                shrunk(rec);
            }
            return;
        }
        rec.landing = false;
        if (grown(rec) || shrunk(rec) || G.near(G.rectOf(rec.w.frameGeometry), rec.target)) {
            return;
        }
        if (byItself(rec)) {
            lookAgain(rec);
        }
    }

    // ------------------------------------------------------------------- a window that moves
    // itself
    //
    // A tiled window whose rectangle changes by its application's doing (point 2 at the top) is
    // put on a list (`due`), and main.qml's quiet timer looks at it once it has been still for one
    // whole turn -- between one and two turns after its last change -- so nothing is answered while
    // it moves, and a burst of moves costs one write at most. What the window did is kept on its
    // record (`drift`): the times it was put back (`back`), where it stood when it last was
    // (`answer`), whether where it puts itself stands, and why (`stands`: "size" for a size of its
    // own in its zone's corner, "place" for a window put back MOST_BACK times within AGAIN_MS),
    // when it last moved by its own doing (`moved`), and whether its growing past its zone was
    // said (`grown`). The times it was put back count over the last AGAIN_MS whatever the layout does
    // meanwhile -- a zone of its own again clears only the rest (`anotherZone`) -- so a window
    // that fights is put back at most MOST_BACK times in any AGAIN_MS, however often its screen is
    // laid out again.

    function quietTimer() {
        return env.timers && env.timers.quiet ? env.timers.quiet : null;
    }

    // One timer for every window, started unless it runs already: each window keeps its own
    // `stirred`, so one that keeps moving holds no other back. Without the timer, at the next turn
    // of the event loop.
    function quietly() {
        const t = quietTimer();
        if (!t) {
            env.later(flushDue);
        } else if (!t.running) {
            t.start();
        }
    }

    function lookAgain(rec) {
        rec.stirred = true;
        state.due.add(rec.id);
        quietly();
    }

    function stopQuiet() {
        const t = quietTimer();
        if (t) {
            t.stop();
        }
    }

    // The quiet timer ran out: each window due that has not moved during that turn is looked at,
    // and one that has waits for one more.
    function flushDue() {
        if (state.disposed) {
            return;
        }
        Array.from(state.due).forEach(function (id) {
            const rec = state.records.get(id);
            if (!rec) {
                state.due.delete(id);
                return;
            }
            if (rec.stirred) {
                rec.stirred = false;
                return;
            }
            state.due.delete(id);
            try {
                reassert(rec);
            } catch (e) {
                log("could not put " + nameOf(rec) + " back in its zone: " + e);
            }
        });
        if (state.due.size) {
            quietly();
        }
    }

    // The times in `times` within the last AGAIN_MS; one ahead of the clock -- a clock set back --
    // counts as past it.
    function lately(times, at) {
        return times.filter(function (t) { return at - t >= 0 && at - t < AGAIN_MS; });
    }

    // Whether the window has not moved by its own doing for AGAIN_MS, a clock set back counting as
    // past it.
    function stillLong(rec) {
        const since = now() - rec.drift.moved;
        return since < 0 || since >= AGAIN_MS;
    }

    // A change of the window's own, its answer to a write of the engine's or not: the window is not
    // still (`moved`). It is looked at once still, unless where it puts itself stands and it had
    // not been still for AGAIN_MS; after that, it starts a new round.
    //
    // A size of its own stands where it stood, and only there: in its zone's corner, at that size.
    // A window that leaves it -- its application restoring a saved place, or growing it over its
    // neighbours -- answers its zone no more, and is looked at as any window that moves itself,
    // counted towards MOST_BACK. Left standing, it was never put back: a pass that gives the same
    // zone looks again only at a window put back MOST_BACK times (`stillThere`), and one moved
    // within AGAIN_MS of its size standing stayed over its neighbour until its zone changed (seen
    // in tests/engine_harness.mjs, `ownSize`).
    function byItself(rec) {
        const d = rec.drift;
        const long = stillLong(rec);
        d.moved = now();
        if (!d.stands) {
            return true;
        }
        const frame = G.rectOf(rec.w.frameGeometry);
        const kept = d.stands === "size" && !!d.answer && G.near(frame, d.answer)
            && cornered(frame, rec.target);
        if (!long && (d.stands === "place" || kept)) {
            return false;
        }
        d.stands = "";
        d.answer = null;
        return true;
    }

    // A zone of its own again: what the window answered the last one with no longer counts, and
    // where it puts itself stands again at once only when it was put back MOST_BACK times within
    // AGAIN_MS already -- a screen laid out again and again gives a window that fights no new round
    // each time.
    function anotherZone(rec) {
        const d = rec.drift;
        d.back = lately(d.back, now());
        d.answer = null;
        d.grown = false;
        d.stands = d.back.length >= MOST_BACK ? "place" : "";
    }

    // The same zone again, for a window nothing else looks at: one its application moved while its
    // desktop was not shown is looked at once still, and so is one where it put itself stood after
    // it was put back MOST_BACK times, once it has been still for AGAIN_MS -- left where it put
    // itself until then, or until its zone changes. One that answered its zone with a size of its
    // own is in its zone already, and is left so: once it leaves that size in its corner, it is
    // looked at as it moves (`byItself`).
    function stillThere(rec) {
        const d = rec.drift;
        if (d.stands === "place" && stillLong(rec)) {
            d.stands = "";
            d.answer = null;
        }
        if (!rec.landing && !d.stands && !state.due.has(rec.id)
                && !G.near(G.rectOf(rec.w.frameGeometry), rec.target)) {
            lookAgain(rec);
        }
    }

    // Grown past its zone: the window needs more of it than the zone the last pass gave it (`plan`)
    // -- its application raised its minimum, which KWin grows the window to and a script hears of
    // only as this change, or its title bar came after it was laid out. Its screen is laid out
    // again, which makes the room, and it is said once for each zone. Not for a window that keeps
    // its slot, which needs nothing of the zone.
    function grown(rec) {
        const s = rec.key ? state.surfaces.get(rec.key) : null;
        const zone = (s ? s.placed.get(rec.id) : null) || rec.target;
        const need = needsOf(rec);
        if (keepsSlot(rec) || G.holds(zone, need)) {
            return false;
        }
        if (!rec.drift.grown) {
            rec.drift.grown = true;
            log(nameOf(rec) + " grew past its zone: it needs " + size(need) + ", its zone is "
                + size(zone) + ", and its screen is laid out again");
        }
        schedule(rec.key);
        return true;
    }

    // A window that needs less than its screen was laid out for -- its title bar gone, which KyprX
    // itself hides a moment after a kind of window it has not seen opens -- has its screen laid out
    // again wherever that can change something: where the lines were moved for room, so that they
    // go back as far as they can; where a window waits for room, which this may make; and for a
    // window that is the one waiting, against what it was floated for (`floatForRoom`). It is said
    // once for each such change. A window the pass leaves the zone it had is then out of it -- its
    // frame closed in -- and is written back as any window out of its zone is, and counted.
    function shrunk(rec) {
        const s = rec.key ? state.surfaces.get(rec.key) : null;
        const was = rec.laidFor;
        if (!s || !was || keepsSlot(rec)
                || !(rec.outOfRoom || (s.shown && s.shown.fitted) || waiting(s))) {
            return false;
        }
        const need = needsOf(rec);
        if (need.width >= was.width && need.height >= was.height) {
            return false;
        }
        rec.laidFor = need;
        log(nameOf(rec) + " needs " + size(need) + " where it was " + (rec.outOfRoom
            ? "floated for room" : "laid out") + " needing " + size(was)
            + ": its screen is laid out again");
        schedule(rec.key);
        return true;
    }

    // Whether a window of the surface waits for room.
    function waiting(s) {
        return s.order.some(function (id) {
            const r = state.records.get(id);
            return !!r && r.outOfRoom && isCandidate(r, s);
        });
    }

    // At the zone's top left corner, and no larger than the zone: a size of the window's own in its
    // zone. A Wayland window cannot place itself, so its own size keeps the corner; an X11 window
    // put somewhere else is not answering its zone, and one larger than it covers its neighbours.
    function cornered(frame, zone) {
        return Math.abs(frame.x - zone.x) <= G.TOLERANCE && Math.abs(frame.y - zone.y) <= G.TOLERANCE
            && frame.width <= zone.width + G.TOLERANCE && frame.height <= zone.height + G.TOLERANCE;
    }

    function where(r) {
        return size(r) + " at " + r.x + ", " + r.y;
    }

    // A tiled window looked at once still, out of its zone. Put back by a write -- unless it is no
    // longer one the engine lays out there, where its screen is not on show (`stillThere` looks
    // at it when it is), or where it puts itself stands. One that answers each write with the same
    // rectangle in its zone's corner keeps it after one more write, as a terminal sizing itself to
    // whole characters would. One out of its zone again after being put back MOST_BACK times
    // within AGAIN_MS is left where it puts itself.
    function reassert(rec) {
        // A write still on its way a turn or two later is waited for once more, counted for
        // nothing: a landing later than that is not measured, but a burst of windows at login is
        // where one would come. After that, a write that brought no change at all is answered by
        // where the window is -- an X11 write the window answers with the very rectangle it had
        // brings none -- and the log line says how long it was waited for.
        if (rec.landing && !rec.waited) {
            rec.waited = true;
            log("the write to " + nameOf(rec) + " has brought no change in " + (now() - rec.sentAt)
                + " ms: it is looked at once more before anything is counted");
            lookAgain(rec);
            return;
        }
        rec.landing = false;
        const answered = rec.answering;
        rec.answering = false;
        const s = rec.key ? state.surfaces.get(rec.key) : null;
        const d = rec.drift;
        if (!core.on() || !state.settings.auto || !rec.target || !s || !isMember(rec, s)
                || !!d.stands || keepsSlot(rec) || drag.busy(rec) || !!rec.w.tile
                || visibleKeys().indexOf(s.key) < 0) {
            return;
        }
        // Grown past its zone is asked first: a write that lands inside itself on X11 is not
        // looked at by `geometryChanged`, and a window in its zone may need more of it than it had
        // when the zone was worked out -- its frame read larger at the landing.
        if (grown(rec) || shrunk(rec)) {
            return;
        }
        const frame = G.rectOf(rec.w.frameGeometry);
        if (G.near(frame, rec.target)) {
            d.answer = null;
            return;
        }
        const at = now();
        if (answered && !!d.answer && G.near(frame, d.answer) && cornered(frame, rec.target)) {
            d.stands = "size";
            d.moved = at;
            log(nameOf(rec) + " answers its zone with a size of its own, in its corner: that size"
                + " stands (" + size(frame) + " in a zone of " + size(rec.target) + ")");
            return;
        }
        d.back = lately(d.back, at);
        if (d.back.length >= MOST_BACK) {
            d.stands = "place";
            d.moved = at;
            log(nameOf(rec) + " is out of its zone again after being put back " + MOST_BACK
                + " times in " + AGAIN_MS / 1000 + " s: where it put itself stands (" + where(frame)
                + ")");
            return;
        }
        d.back.push(at);
        d.answer = frame;
        log("put " + nameOf(rec) + " back in its zone (" + d.back.length + " of " + MOST_BACK
            + "): it was at " + where(frame) + ", its zone is " + where(rec.target));
        send(rec);
    }

    // ------------------------------------------------------------------- the settings

    function bordersOff() {
        const O = env.Options;
        if (!O) {
            return;
        }
        state.borders = {maximize: O.electricBorderMaximize === true,
                         tiling: O.electricBorderTiling === true};
        O.electricBorderMaximize = false;
        O.electricBorderTiling = false;
    }

    function bordersBack() {
        const O = env.Options;
        if (!O || !state.borders) {
            return;
        }
        O.electricBorderMaximize = state.borders.maximize;
        O.electricBorderTiling = state.borders.tiling;
        state.borders = null;
    }

    function standDown() {
        const was = state.on;
        state.on = false;
        drag.cancel();
        lowerAll();
        bordersBack();
        stopTidying();
        state.dirty.clear();
        state.due.clear();
        stopQuiet();
        state.records.forEach(function (rec) {
            untarget(rec);
            forgetRoom(rec);
        });
        if (was) {
            log("tiling stopped");
        }
    }

    // A window no longer laid out by the engine, as the tiling stops or goes manual: it waits for
    // room no more, and joins again, in the order the windows opened in, when the engine lays its
    // screen out again.
    function forgetRoom(rec) {
        rec.outOfRoom = false;
        rec.joins.clear();
    }

    // The level of focus stealing prevention is logged because it is the first thing to ask of a
    // session where a window took the screen with it, or did not: measured in the facts scenario,
    // a window that opens is the active one at `windowAdded` at Low and Medium alike, which is why
    // the time since this moment decides instead (`overflow`).
    function takeOver() {
        state.on = true;
        state.onSince = now();
        bordersOff();
        log("tiling started");
        const O = env.Options;
        if (O) {
            log("focus stealing prevention is at level " + O.focusStealingPreventionLevel);
        }
    }

    // An edit to the arrangements and the zone layouts, as it reaches the surfaces. The layouts a
    // surface keeps as the person resized them belong to the arrangement they were made from, and
    // go when that arrangement's layouts change. An arrangement whose own zone layout changed --
    // another one of its layouts is offered on a drag, or no longer offered -- takes every surface
    // on it to the new one; a zone layout picked in the selector or with the layout keys stays
    // until then.
    //
    // Read against the last answer that carried arrangements (`state.made`), whatever its
    // `tiling`, and not against the answer before: one with tiling off can carry an edit -- a copy
    // of the desk, the KyprX folder or a backup put back -- and the daemon's answer when it could
    // not resolve the settings carries no arrangements at all, so either way the edit was missed.
    // By id in Maps, because an id is any lower-case word and `constructor` is one. A surface on an
    // arrangement whose layouts changed forgets the tree it was laid out by too, so that no key
    // starts from it before the next pass (`shownFor`).
    function edited(before, after) {
        if (!before) {
            return;
        }
        const was = new Map();
        before.arrangements.forEach(function (a) { was.set(a.id, a); });
        const stale = [];
        const homes = new Map();
        after.arrangements.forEach(function (a) {
            const old = was.get(a.id);
            if (!old) {
                return;
            }
            if (JSON.stringify(old.layouts) !== JSON.stringify(a.layouts)) {
                stale.push(a.id + ":");
            }
            if (before.homes.get(a.id) !== after.homes.get(a.id)) {
                homes.set(a.id, after.homes.get(a.id));
            }
        });
        state.surfaces.forEach(function (s) {
            Array.from(s.adjusted.keys()).forEach(function (slot) {
                if (stale.some(function (prefix) { return slot.indexOf(prefix) === 0; })) {
                    s.adjusted.delete(slot);
                }
            });
            if (homes.has(s.arrangement)) {
                s.zone = homes.get(s.arrangement);
            }
            if (stale.indexOf(s.arrangement + ":") >= 0) {
                s.shown = null;
            }
        });
    }

    function apply(settings) {
        const before = state.settings;
        const wasOn = state.on;
        // Automatic tiling switched by this answer, from wherever: the name card says it only for
        // Toggle Automatic Tiling's (`autoSaid`).
        const flipped = !!before && before.auto !== settings.auto;
        // Against the last answer that carried arrangements, as `edited` reads: the daemon's
        // answer when it could not resolve the settings carries none, and no choice either.
        const chose = settings.arrangements.length ? choicesMoved(state.made, settings) : [];
        if (settings.arrangements.length) {
            edited(state.made, settings);
            state.made = settings;
        }
        state.settings = settings;
        startAgain(chose);
        if (!settings.tiling) {
            // The key does nothing while nothing tiles, and a press before the tiling stopped is
            // not one an answer after it is said for.
            state.autoAskedAt = -1;
            standDown();
            return;
        }
        if (!state.on) {
            takeOver();
        }
        if (before && !before.auto && settings.auto) {
            // Manual tiling to automatic: every window is placed again, wherever it was left -- one
            // with no room centred and raised again, as it leaves the tiling.
            state.records.forEach(untarget);
        } else if (before && before.auto && !settings.auto) {
            state.records.forEach(forgetRoom);
        }
        // In the order the compositor lists its windows -- the order they opened in (measured) --
        // so that the first answer lays out what was already open the same way every time.
        listOf(W.windows).forEach(function (w) {
            const rec = state.records.get(String(w.internalId));
            if (rec) {
                judge(rec, false);
            }
        });
        // A surface whose arrangement is gone goes to the first in the rotation, and one whose
        // zone layout is gone, or no longer offered on a drag, back to its arrangement's own.
        state.surfaces.forEach(function (s) {
            if (s.arrangement) {
                zoneOf(s);
            }
        });
        // KyprX's own windows already open are kept above as the tiling starts; one that opens
        // later is, as it opens. Where they are is left alone: only a window that opens is put
        // in the middle of its screen.
        if (!wasOn) {
            state.records.forEach(function (rec) { holdAbove(rec, kindOf(rec)); });
        }
        // A first look over KyprX's desktops, a moment after a daemon that writes lets the engine
        // tile: one left empty by an earlier session goes, as one emptied in this one does.
        if (!settings.dry && (!wasOn || before.dry)) {
            tidySoon();
        }
        scheduleVisible();
        // Last, and on its own: a card that cannot be worked out costs the card, and nothing of
        // the answer applied above.
        if (flipped) {
            try {
                autoSaid();
            } catch (e) {
                log("could not say that automatic tiling switched: " + e);
            }
        }
    }

    // ------------------------------------------------------------------- KyprX's own windows
    //
    // The daemon names three groups of classes in `float` (`_own_windows` in daemon/tiling.py):
    // `classes`, which float -- KyprX's settings window first; `centred`, whose window opens in the
    // middle of its screen; and `above`, which are kept above the other windows while they float,
    // the cheatsheet and the wallpaper picker as well. Toggle Float tiles the settings window and
    // takes its keep-above away until it floats again. Only the keep-above this engine set is
    // ever taken away or given back: a window that was kept above already, by a window rule or by
    // the person, is left as it is.

    function aboveClass(w) {
        return mainWindow(w) && R.anyClass(state.settings.float.above, w);
    }

    function raise(rec) {
        if (state.raised.has(rec.id) || rec.w.keepAbove === true) {
            return;
        }
        rec.w.keepAbove = true;
        state.raised.add(rec.id);
    }

    // The keep-above this engine set taken away, and with it every window kept above this one.
    function lower(rec) {
        if (!state.raised.has(rec.id)) {
            return;
        }
        state.raised.delete(rec.id);
        unconstrainWhere(function (pair) { return pair.below === rec.id; });
        rec.w.keepAbove = false;
    }

    function lowerAll() {
        unconstrainWhere(function () { return true; });
        Array.from(state.raised).forEach(function (id) {
            const rec = state.records.get(id);
            if (rec) {
                lower(rec);
            }
        });
        state.raised.clear();
    }

    // Kept above while it floats, as `kind` -- what the window is to the tiling now -- says.
    function holdAbove(rec, kind) {
        if (!aboveClass(rec.w)) {
            return;
        }
        if (kind === "tile") {
            lower(rec);
        } else {
            raise(rec);
        }
    }

    // A window that opens in the middle of its screen at its own size, each side held between
    // what it needs and OWN_MOST of the usable area. Not on a screen kept out of the tiling, and
    // not maximized or full screen.
    function centre(rec) {
        const w = rec.w;
        const output = w.output;
        if (keepsSlot(rec) || !output || R.screenIgnored(state.settings, String(output.name))) {
            return;
        }
        const desktops = listOf(w.desktops);
        const shown = currentDesktopFor(output);
        const desktop = desktops.find(function (d) {
            return !!shown && String(d.id) === String(shown.id);
        }) || desktops[0] || shown;
        const area = areaFor(output, desktop);
        if (!area) {
            return;
        }
        const own = G.rectOf(w.frameGeometry);
        const least = needsOf(rec);
        const width = Math.max(least.width, Math.min(own.width, Math.floor(area.width * OWN_MOST)));
        const height = Math.max(least.height,
                                Math.min(own.height, Math.floor(area.height * OWN_MOST)));
        write(rec, {x: Math.round(area.x + (area.width - width) / 2),
                    y: Math.round(area.y + (area.height - height) / 2),
                    width: width, height: height});
    }

    // A window that opens while KyprX's settings window is the active one goes above it, as the
    // compositor's own constraint, rather than under it, kept above as that window is. The window
    // that was active is the most recent one other than the new window: the compositor activates
    // the new one before `windowAdded` (measured). A dialog stays above its own window already, a
    // panel, a menu or a notification has a layer of its own, and the cheatsheet and the picker
    // are kept above themselves.
    function constrainOver(rec, rule) {
        const w = rec.w;
        if (typeof W.constrain !== "function" || !rule.focusable || !mainWindow(w)
                || R.anyClass(state.settings.float.above, w)) {
            return;
        }
        const before = state.focus.find(function (id) { return id !== rec.id; });
        const under = before && state.raised.has(before) ? state.records.get(before) : null;
        if (!under || !R.anyClass(state.settings.float.centred, under.w)) {
            return;
        }
        W.constrain(under.w, w);
        state.pairs.push({below: under.id, above: rec.id, under: under.w, over: w});
    }

    function unconstrainWhere(test) {
        const going = state.pairs.filter(test);
        state.pairs = state.pairs.filter(function (pair) { return !test(pair); });
        going.forEach(function (pair) {
            try {
                if (typeof W.unconstrain === "function") {
                    W.unconstrain(pair.under, pair.over);
                }
            } catch (e) {
                log("could not let a window go from above KyprX's settings: " + e);
            }
        });
    }

    // What a window that opens is to KyprX's own: in the middle of its screen, kept above, or put
    // above the settings window. Before the tiling reads it, while it is on, and never the cause
    // of a window not being tiled: a throw here is logged and the window goes on. `rule` is what
    // the rules say of the window (`R.classify`).
    function own(rec, rule) {
        if (!core.on()) {
            return;
        }
        try {
            if (rule.kind !== "tile" && mainWindow(rec.w)
                    && R.anyClass(state.settings.float.centred, rec.w)) {
                centre(rec);
            }
            holdAbove(rec, rule.kind);
            constrainOver(rec, rule);
        } catch (e) {
            log("could not place " + nameOf(rec) + " as KyprX's own: " + e);
        }
    }

    function nameOf(rec) {
        return String(rec.w.resourceClass || rec.id);
    }

    // KyprX's name card on one screen (`env.announce`, NameWindow.qml), when `osd` lets it show.
    function announce(card) {
        if (!state.settings.osd || !env.announce) {
            return;
        }
        try {
            env.announce(card);
        } catch (e) {
            log("could not show a name on screen: " + e);
        }
    }

    // ------------------------------------------------------------------- a window that opens with
    // every zone taken
    //
    // A window that opens on a screen that already has a window in every zone of its
    // arrangement's last layout -- the fifth on Balanced -- goes to a desktop of its own
    // (`overflow` 0), floats in the middle of the screen (1), or squeezes in by splitting the last
    // zone (2), the cascade every window got before. It is decided here, as the window opens, and
    // nowhere else: a window that comes back from being minimized, from floating or from another
    // screen, one the rules let in only when its class comes, and one the person moves onto a full
    // desktop squeeze in as before, whatever the setting.
    //
    // The desktop is the first of the origin's chain whose surface on this screen and activity
    // has room, or else a new one named "<base> · <n>" with the smallest number free: made after
    // the last desktop (`newDesktop` 0), so that the keys that go to a desktop by its number keep
    // going to the same one, or right after the chain -- after the origin while the chain is
    // empty (1). Its surface takes the origin's arrangement, and the zone layout a drag offers
    // there: the desktop goes on from the one it came from.
    //
    // The screen goes with the window only when the person opened it, and nothing a script can
    // read says who did. Measured in the facts scenario: a new window, Wayland and X11, was already
    // the active window when `windowAdded` reached the script, at focus stealing prevention Low
    // and Medium alike, so being active is as true of a window that opened by itself as of one
    // the person opened. Time is what is left: a login opens the applications it starts in its
    // first moments, so a window active at `windowAdded` takes the screen with it only
    // FOLLOW_AFTER_MS after the tiling started. Any other goes quietly, the focus goes back to the
    // window that had it, and the name card says where it went.
    //
    // Nothing of a decision about a window outlives `windowAdded` -- only the engine's own switch
    // of a screen is kept, for the rest of a burst (`burst`): the window goes, floats or squeezes
    // in there and then, and the tiling reads it (`judge`) only afterwards, so that it never passes
    // through the origin's order. In a dry run (`dry`) no desktop is made -- the compositor writes
    // `kwinrc [Desktops]` the moment one comes, and that write goes through no door of KyprX's --
    // and the window floats instead.
    function overflow(rec, active, rule) {
        const settings = state.settings;
        const w = rec.w;
        if (!core.on() || !settings.auto || settings.overflow === 2) {
            return;
        }
        // A window whose class has not come yet is read by the rules as a guess (point 1 at the
        // top of main.qml), and a desktop is not made on a guess: nothing takes the window back
        // when its class comes and says it floats.
        if (String(w.resourceClass || "") === "" || rule.kind !== "tile"
                || !mainWindow(w) || w.utility === true || w.minimized === true
                || w.onAllDesktops === true || !w.output) {
            return;
        }
        const desktops = listOf(w.desktops);
        if (desktops.length !== 1) {
            return;
        }
        const output = w.output;
        const origin = desktops[0];
        const list = desktopList();
        const s = surfaceFor(String(output.name), String(origin.id), activityOf(w));
        // A window waiting for room counts as one of the screen's windows: it has a zone again as
        // soon as there is room (`plan`), and counted out, the next window would join a screen
        // already short of room and float as the newest, instead of doing what `overflow` says.
        // The new window's own minimum is not foreseen: an application can set it after its window
        // is shown, `minSize` has no change signal (read in KWin 6.7.5's source), and a desktop
        // made on a guess cannot be taken back.
        if (ignored(s) || (visibleKeys().indexOf(s.key) < 0 && !burst(output, origin, s, list))
                || candidates(s).length < arrangementOf(s).layouts.length) {
            return;
        }
        // Nor while a window is held (`drag.busyAny`). Asked last: it reads every window the
        // compositor has, and most windows that open -- a menu, a tooltip, a dialog -- are turned
        // away above without it.
        if (drag.busyAny()) {
            return;
        }
        if (settings.overflow === 1 || settings.dry) {
            if (settings.overflow === 0) {
                log("would have opened " + nameOf(rec) + " on a new desktop; a dry run makes none,"
                    + " so it floats");
            }
            floatHere(rec, output, origin);
            return;
        }
        elsewhere(rec, active, output, origin, s, list);
    }

    // The rest of a burst: a window an application made before the screen went to a desktop of
    // the same chain arrives on the desktop it was made on, which the screen no longer shows -- a
    // Wayland window is put on the desktop shown when its application makes it, and keeps it when
    // it is first shown (read in KWin 6.7.5's source, `XdgToplevelWindow`; not measured). Only
    // that: a window on the desktop the engine's own switch took this screen from, within
    // BURST_MS of it (`followed`; a clock set back since counts as past it), while the screen
    // shows a desktop of that chain. A window that arrives on a desktop the screen does not show
    // at any other time -- put there by a window rule, by its application or by a session being
    // restored, or after the person took the screen to the chain themselves -- squeezes in where
    // it was put.
    function burst(output, origin, s, list) {
        const went = state.followed.get(String(output.name));
        const since = went ? now() - went.at : -1;
        if (!went || went.from !== String(origin.id) || since < 0 || since > BURST_MS) {
            return false;
        }
        const shown = currentDesktopFor(output);
        if (!shown || String(shown.id) === String(origin.id) || s.activity !== activityNow()) {
            return false;
        }
        const mark = markOf(shown, list);
        return !!mark && mark.base === baseName(origin, list);
    }

    // Floating in the middle of the usable area, at FLOAT_FRACTION of its size, as Toggle Float
    // leaves a window; Toggle Float tiles it again, and it squeezes in.
    function floatHere(rec, output, desktop) {
        rec.override = "float";
        const area = areaFor(output, desktop);
        if (area) {
            rec.w.setMaximize(false, false);
            write(rec, G.centred(area, FLOAT_FRACTION, needsOf(rec)));
        }
    }

    // Whether a desktop of the chain has a zone free on this screen and activity, by its
    // surface's arrangement, or the origin's for a surface that has none yet. A window waiting for
    // room there takes one, as on the origin (`overflow`).
    function roomOn(outputName, d, origin) {
        const t = state.surfaces.get(keyFor(outputName, String(d.id), origin.activity));
        const a = t && t.arrangement ? arrangementOf(t) : arrangementOf(origin);
        return (t ? candidates(t).length : 0) < a.layouts.length;
    }

    // A desktop made for the chain, found by the id that was not there before: the call answers
    // nothing (measured). Null at MAX_DESKTOPS, or when the compositor made none.
    function makeDesktop(base, chain, origin, list) {
        if (list.length >= MAX_DESKTOPS) {
            return null;
        }
        const names = list.map(function (d) { return String(d.name); });
        let n = 2;
        while (names.indexOf(base + CHAIN_MARK + n) >= 0) {
            n += 1;
        }
        let position = list.length;
        if (state.settings.newDesktop === 1) {
            const after = chain.length ? chain[chain.length - 1] : origin;
            const at = list.findIndex(function (d) { return String(d.id) === String(after.id); });
            position = at >= 0 ? at + 1 : list.length;
        }
        const before = list.map(function (d) { return String(d.id); });
        W.createDesktop(position, base + CHAIN_MARK + n);
        return desktopList().find(function (d) { return before.indexOf(String(d.id)) < 0; })
            || null;
    }

    function noRoom(rec, output, origin) {
        log("no room for another desktop: " + nameOf(rec) + " floats");
        floatHere(rec, output, origin);
        announce({output: String(output.name), heading: "No room for another desktop",
                  caption: "The window floats", zones: []});
    }

    // The focus back to the window that had it last among those a screen shows: the window that
    // took it went where no screen looks.
    function focusBack(rec) {
        const visible = visibleKeys();
        const id = state.focus.find(function (x) {
            const other = x !== rec.id ? state.records.get(x) : null;
            return !!other && inSight(other, visible);
        });
        if (id) {
            W.activeWindow = state.records.get(id).w;
        }
    }

    function removeIfBare(d) {
        const there = desktopList().find(function (x) { return String(x.id) === String(d.id); });
        if (there && !shownAnywhere(there) && bare(there, "")) {
            W.removeDesktop(there);
        }
    }

    // The window to a desktop of its own. On a throw, what this did is put back -- the window on
    // its origin, the screen too if it went, a desktop made for it removed while it is empty --
    // and the window squeezes in where it opened.
    function elsewhere(rec, active, output, origin, s, list) {
        const w = rec.w;
        const outputName = String(output.name);
        const chain = chainOf(baseName(origin, list), list);
        let made = null;
        let moved = false;
        let switched = false;
        try {
            let target = chain.find(function (d) { return roomOn(outputName, d, s); }) || null;
            if (!target) {
                made = makeDesktop(baseName(origin, list), chain, origin, list);
                target = made;
            }
            if (!target) {
                noRoom(rec, output, origin);
                return;
            }
            const t = surfaceFor(outputName, String(target.id), s.activity);
            if (!t.arrangement) {
                t.arrangement = s.arrangement;
                t.zone = s.zone;
            }
            w.desktops = [target];
            moved = true;
            const landed = listOf(w.desktops);
            if (landed.length !== 1 || String(landed[0].id) !== String(target.id)) {
                // A window rule that forces the window's desktop refuses the write without a
                // word, and the window reads back where it was (measured in the facts scenario).
                moved = false;
                if (made) {
                    removeIfBare(made);
                }
                log(nameOf(rec) + " stays on " + origin.name + ", where a window rule keeps it");
                return;
            }
            const follow = active && now() - state.onSince >= FOLLOW_AFTER_MS;
            if (follow) {
                showDesktop(target, output);
                switched = true;
                state.followed.set(outputName, {from: String(origin.id), at: now()});
                W.activeWindow = w;
            } else if (active) {
                focusBack(rec);
            }
            log("sent " + nameOf(rec) + " to " + target.name + (made ? ", made for it" : "")
                + (follow ? ", and the screen went with it" : ", quietly"));
            announce({output: outputName, heading: String(target.name),
                      caption: String(origin.name) + " was full", zones: []});
        } catch (e) {
            log("could not open " + nameOf(rec) + " on a desktop of its own: " + e);
            putBack(function () {
                if (moved) {
                    w.desktops = [origin];
                }
            });
            putBack(function () {
                if (switched) {
                    state.followed.delete(outputName);
                    showDesktop(origin, output);
                    W.activeWindow = w;
                }
            });
            putBack(function () {
                if (made) {
                    removeIfBare(made);
                }
            });
        }
    }

    // One step of putting back what a failed `elsewhere` did, each tried whatever the one before
    // it did.
    function putBack(step) {
        try {
            step();
        } catch (e) {
            log("and could not put back all that was done: " + e);
        }
    }

    // ------------------------------------------------------------------- KyprX's desktops going
    //
    // A desktop KyprX made goes once nothing is on it and no screen shows it, a moment later:
    // main.qml's cleanup timer, 3 s, which every window that closes or changes desktops, every
    // desktop that comes or goes, and every switch of desktop or activity starts again, so a
    // desktop the person only passes through is not taken from under them. When the last window
    // of one closes while a screen shows it, that screen goes back to the desktop its chain came
    // from, which lets it go. All of it only while the engine tiles for a daemon that writes, and
    // never as the tiling stops or the script goes: a desktop removed then is one nobody asked to
    // lose.

    function ownsDesktops() {
        return core.on() && !state.settings.dry;
    }

    function tidySoon() {
        const t = env.timers ? env.timers.cleanup : null;
        if (!state.disposed && t && ownsDesktops()) {
            t.restart();
        }
    }

    function stopTidying() {
        const t = env.timers ? env.timers.cleanup : null;
        if (t) {
            t.stop();
        }
    }

    // Whether nothing is on a desktop. Every window the compositor lists counts, minimized ones
    // and those of other activities as well; not one on every desktop, which is on none in
    // particular, nor `except`, the id of a window that is closing.
    function bare(d, except) {
        return !listOf(W.windows).some(function (w) {
            return String(w.internalId) !== except && !R.internal(w) && w.onAllDesktops !== true
                && isOn(w, d);
        });
    }

    function tidy() {
        if (typeof W.removeDesktop !== "function") {
            return;
        }
        desktopList().forEach(function (d) {
            const name = String(d.name);
            try {
                const list = desktopList();
                const there = list.some(function (x) { return String(x.id) === String(d.id); });
                const mark = there ? markOf(d, list) : null;
                const base = mark ? desktopNamed(mark.base, list) : null;
                if (!base || shownAnywhere(d) || !bare(d, "")) {
                    return;
                }
                W.removeDesktop(d);
                log("removed " + name + ", a desktop KyprX made, which nothing was on");
            } catch (e) {
                log("could not remove the desktop " + name + ": " + e);
            }
        });
        // And the surfaces of every desktop that is gone, whoever removed it.
        const alive = desktopList().map(function (d) { return String(d.id); });
        Array.from(state.surfaces.keys()).forEach(function (key) {
            if (alive.indexOf(state.surfaces.get(key).desktop) < 0) {
                state.surfaces.delete(key);
            }
        });
    }

    // A window that closed, and the desktops it was on: put off until the compositor is done with
    // it, rather than switching desktops from inside its `windowRemoved`. Its own list -- measured
    // in the sandbox, a closing window still names its desktop when `windowRemoved` reaches a
    // script -- and the desktop of the surface it was counted on besides, which costs nothing.
    function leftEmpty(rec, w) {
        if (!ownsDesktops()) {
            return;
        }
        const ids = [];
        try {
            listOf(w.desktops).forEach(function (d) { ids.push(String(d.id)); });
        } catch (e) {
            // The surface below still says where it was.
        }
        const s = rec.key ? state.surfaces.get(rec.key) : null;
        if (s && ids.indexOf(s.desktop) < 0) {
            ids.push(s.desktop);
        }
        ids.forEach(function (id) { state.emptied.set(id, rec.id); });
        if (ids.length) {
            env.later(flushEmptied);
        }
    }

    function flushEmptied() {
        const due = Array.from(state.emptied.entries());
        state.emptied.clear();
        if (state.disposed || !ownsDesktops()) {
            return;
        }
        due.forEach(function (entry) {
            const list = desktopList();
            const d = list.find(function (x) { return String(x.id) === entry[0]; }) || null;
            const mark = d ? markOf(d, list) : null;
            const base = mark ? desktopNamed(mark.base, list) : null;
            if (!base || !bare(d, entry[1])) {
                return;
            }
            outputs().forEach(function (o) {
                const shown = currentDesktopFor(o);
                if (!shown || String(shown.id) !== String(d.id)) {
                    return;
                }
                try {
                    showDesktop(base, o);
                    log("the last window on " + d.name + " closed: back to " + base.name);
                } catch (e) {
                    log("could not take the screen back to " + base.name + ": " + e);
                }
            });
        });
    }

    // ------------------------------------------------------------------- the keys

    // Of the windows that way, the nearest; of two as near, the one focused more recently -- from
    // the master zone, right goes back to whichever of the two stacked beside it was last used.
    function nearestWay(from, candidates, direction) {
        let best = null;
        let bestScore = -1;
        let bestRank = 0;
        candidates.forEach(function (candidate) {
            const score = G.towards(from, candidate.rect, direction);
            if (score < 0) {
                return;
            }
            const seen = state.focus.indexOf(candidate.id);
            const rank = seen < 0 ? state.focus.length : seen;
            if (best === null || score < bestScore || (score === bestScore && rank < bestRank)) {
                best = candidate;
                bestScore = score;
                bestRank = rank;
            }
        });
        return best;
    }

    // Focus goes to the nearest window shown that way, on any screen (`inSight`).
    function focus(direction) {
        const active = activeRecord();
        const from = active ? G.rectOf(active.w.frameGeometry)
            : {x: Number(W.cursorPos.x), y: Number(W.cursorPos.y), width: 0, height: 0};
        const visible = visibleKeys();
        const candidates = [];
        state.records.forEach(function (rec) {
            if (rec !== active && inSight(rec, visible)) {
                candidates.push({id: rec.id, rect: G.rectOf(rec.w.frameGeometry), rec: rec});
            }
        });
        const best = nearestWay(from, candidates, direction);
        if (best) {
            W.activeWindow = best.rec.w;
        }
    }

    function swapInOrder(s, a, b) {
        const i = s.order.indexOf(a);
        const j = s.order.indexOf(b);
        if (i >= 0 && j >= 0) {
            s.order[i] = b;
            s.order[j] = a;
        }
    }

    function tiledActive() {
        if (!state.settings.auto) {
            return null;
        }
        const rec = activeRecord();
        if (!rec || !rec.key || kindOf(rec) !== "tile") {
            return null;
        }
        const s = state.surfaces.get(rec.key);
        return s && members(s).indexOf(rec.id) >= 0 ? {rec: rec, s: s} : null;
    }

    // Move swaps the focused window with the tiled window that way on the same screen.
    function move(direction) {
        const found = tiledActive();
        if (!found || !found.s.placed.has(found.rec.id)) {
            return;
        }
        const candidates = [];
        members(found.s).forEach(function (id) {
            if (id !== found.rec.id && found.s.placed.has(id)) {
                candidates.push({id: id, rect: found.s.placed.get(id)});
            }
        });
        const best = nearestWay(found.s.placed.get(found.rec.id), candidates, direction);
        if (best) {
            swapInOrder(found.s, found.rec.id, best.id);
            schedule(found.s.key);
        }
    }

    function setMaster() {
        const found = tiledActive();
        if (!found) {
            return;
        }
        const list = members(found.s);
        const other = list[0] === found.rec.id ? list[1] : list[0];
        if (other) {
            swapInOrder(found.s, found.rec.id, other);
            schedule(found.s.key);
        }
    }

    // The windows of a surface turned one place round, the last into the master zone (`step` 1)
    // or the master to the end (-1). Only the windows laid out move; a minimized one keeps its place.
    function rotate(step) {
        if (!state.settings.auto) {
            return;
        }
        const s = activeSurface();
        if (!s) {
            return;
        }
        const list = members(s);
        if (list.length < 2) {
            return;
        }
        const turned = step > 0 ? [list[list.length - 1]].concat(list.slice(0, -1))
            : list.slice(1).concat([list[0]]);
        const at = list.map(function (id) { return s.order.indexOf(id); });
        at.forEach(function (position, k) { s.order[position] = turned[k]; });
        schedule(s.key);
    }

    function resize(axis, grow) {
        const found = tiledActive();
        if (!found) {
            return;
        }
        const s = found.s;
        const area = areaOf(s.output, s.desktop);
        if (!area) {
            return;
        }
        const list = members(s);
        const box = G.inner(area, state.settings.gaps);
        const a = arrangementOf(s);
        const slot = a.id + ":" + list.length;
        const tree = shownFor(s, slot, list) || treeOf(s, a, list.length, box);
        const path = G.fillOrder(tree)[list.indexOf(found.rec.id)];
        const next = G.stepped(tree, box, path, axis, grow, minsFor(list, tree));
        if (next !== tree) {
            s.adjusted.set(slot, next);
            schedule(s.key);
        }
    }

    // Toggle Float, in automatic tiling only: with manual tiling every window floats already, and
    // so does every window on a screen kept out of the tiling. KyprX's settings window loses the
    // keep-above it floats with while it is tiled, and has it again when it floats (`holdAbove`).
    function toggleFloat() {
        if (!state.settings.auto) {
            return;
        }
        const rec = activeRecord();
        if (!rec || !rec.rule || rec.rule.fixed || ignoredKey(rec.key)) {
            return;
        }
        const tiled = kindOf(rec) === "tile";
        rec.override = tiled ? "float" : "tile";
        // Either way the window joins again, when it is to tile, as the newest: one floating for
        // want of room asks to be tiled, and with still no room floats again, written and raised
        // again.
        rec.outOfRoom = false;
        rec.joins.delete(rec.key);
        untarget(rec);
        if (tiled) {
            const place = placeOf(rec.w);
            const area = place ? areaOf(place.outputName, place.desktopId) : null;
            if (area) {
                rec.w.setMaximize(false, false);
                write(rec, G.centred(area, FLOAT_FRACTION, needsOf(rec)));
            }
        }
        holdAbove(rec, kindOf(rec));
        settle(rec, false);
    }

    // Next Layout and Previous Layout on the screen in use. With automatic tiling, the next
    // arrangement in the rotation, or the one before, and its name card; with manual tiling no
    // window is laid out, so they move the zone layout a drag offers there instead (`walk`).
    // Nothing on a screen kept out of the tiling, where neither changes anything, and so no name
    // shown.
    function cycle(step) {
        const s = activeSurface();
        if (!s || ignored(s)) {
            return;
        }
        if (!state.settings.auto) {
            walk(s, step);
            return;
        }
        const current = arrangementOf(s);
        const turn = rotation();
        if (!turn.length) {
            return;
        }
        let i = turn.map(function (a) { return a.id; }).indexOf(current.id);
        i = i < 0 ? (step > 0 ? 0 : turn.length - 1) : (i + step + turn.length) % turn.length;
        const next = turn[i];
        if (next.id !== current.id) {
            putOn(s, next);
            schedule(s.key);
        }
        announce(arrangementCard(s));
    }

    // A surface's arrangement as its screen's name card says it: the name, how many windows it
    // lays out there, and the zones of the layout in force for them -- for two at the least, where
    // the one zone of a single window would show nothing of the arrangement -- as fractions of the
    // usable area less its gaps, in fill order, the master first. What Next Layout shows, and
    // Toggle Automatic Tiling switching it on (`autoSaid`).
    //
    // The windows and the zones are the ones the screen is about to be laid out with (`plan`): a
    // window waiting for room is not counted, and the lines are moved for room where they will be.
    function arrangementCard(s) {
        const a = arrangementOf(s);
        const area = areaOf(s.output, s.desktop);
        const p = area ? plan(s, area) : null;
        const count = p ? p.list.length : members(s).length;
        const tree = !area ? null : count >= 2 ? p.tree
            : treeOf(s, a, 2, G.inner(area, state.settings.gaps));
        return {output: s.output, heading: String(a.name || a.id),
                caption: count > 1 ? "Arrangement \u00b7 " + count + " windows" : "Arrangement",
                zones: tree ? cardZones(area, tree) : []};
    }

    // Toggle Automatic Tiling: the daemon is asked to write `autoTiling` the other way
    // (`env.toggleAutomaticTiling`, `ToggleAutomaticTiling` on /Windows), and the answer after
    // that write is what switches it here, as for the Tiling tab's box -- never a switch of the
    // engine's own, which the next answer would undo, and so nothing at all in a dry run, which
    // writes nothing. When it was pressed is kept, for that answer's name card (`autoSaid`).
    function toggleAuto() {
        state.autoAskedAt = now();
        if (env.toggleAutomaticTiling) {
            env.toggleAutomaticTiling();
        }
    }

    // An answer has switched automatic tiling. Said on the name card of the screen in use only
    // when it comes within TOGGLE_MS of Toggle Automatic Tiling, and once for each press: switched
    // on the Tiling tab, by a copy of the desk or by the KyprX folder, it shows nothing. On, the
    // screen's arrangement as Next Layout says it, under AUTO_ON; off, the zone layout a drag
    // offers there now, under AUTO_OFF. On a screen kept out of the tiling, where neither is in
    // force, the heading alone. `announce` holds it to Show names on screen.
    function autoSaid() {
        const at = state.autoAskedAt;
        state.autoAskedAt = -1;
        const since = now() - at;
        if (at < 0 || since < 0 || since > TOGGLE_MS) {
            return;
        }
        const s = activeSurface();
        if (!s) {
            return;
        }
        const heading = state.settings.auto ? AUTO_ON : AUTO_OFF;
        if (ignored(s)) {
            announce({output: s.output, heading: heading, caption: "", zones: []});
        } else if (state.settings.auto) {
            const card = arrangementCard(s);
            announce({output: s.output, heading: heading, caption: card.heading,
                      zones: card.zones});
        } else {
            const z = zoneOf(s);
            announce({output: s.output, heading: heading, caption: String(z.name),
                      zones: cardZones(areaOf(s.output, s.desktop), z.tree)});
        }
    }

    // Manual tiling's layout keys: the screen's zone layout moves one place along the selector's
    // list (`bar`), the name card says which it is now, and drag.mjs draws its zones on that
    // screen for a moment -- whether names are shown or not: with no window laid out, the zones are
    // all there is to see of what the key did.
    function walk(s, step) {
        const list = bar(s);
        const at = list.indexOf(zoneOf(s));
        const next = list[(at + step + list.length) % list.length];
        s.zone = next.id;
        announce({output: s.output, heading: String(next.name), caption: ZONES_CAPTION,
                  zones: cardZones(areaOf(s.output, s.desktop), next.tree)});
        drag.preview(s);
    }

    // A tree's zones as the name card draws them: fractions of the usable area less its gaps, in
    // fill order, the master first.
    function cardZones(area, tree) {
        const gaps = state.settings.gaps;
        const box = area ? G.inner(area, gaps) : null;
        if (!box || box.width <= 0 || box.height <= 0) {
            return [];
        }
        return G.cells(tree, area, gaps).map(function (r) {
            return {x: (r.x - box.x) / box.width, y: (r.y - box.y) / box.height,
                    width: r.width / box.width, height: r.height / box.height};
        });
    }

    // ------------------------------------------------------------------- where a window let go
    // after a drag goes (`core.dropped`)

    function moveDesktop(rec, desktopId) {
        const desktop = desktopWithId(desktopId);
        const on = listOf(rec.w.desktops).some(function (d) { return String(d.id) === desktopId; });
        if (desktop && !on) {
            rec.w.desktops = [desktop];
        }
    }

    // A tiled window let go over another tiled window takes that one's place, and the other takes
    // its own -- across screens too.
    function swapWith(a, b) {
        const sa = state.surfaces.get(a.key);
        const sb = state.surfaces.get(b.key);
        if (!sa || !sb) {
            return;
        }
        untarget(a);
        untarget(b);
        if (sa === sb) {
            swapInOrder(sa, a.id, b.id);
            schedule(sa.key);
            return;
        }
        const i = sa.order.indexOf(a.id);
        const j = sb.order.indexOf(b.id);
        if (i < 0 || j < 0) {
            return;
        }
        sa.order[i] = b.id;
        sb.order[j] = a.id;
        a.key = sb.key;
        b.key = sa.key;
        moveDesktop(a, sb.desktop);
        moveDesktop(b, sa.desktop);
        schedule(sa.key);
        schedule(sb.key);
    }

    // The tiled window under a point. None on a screen kept out of the tiling, whose cells are
    // the ones it had before it was: a layout stops there without forgetting them.
    function memberAt(point, except) {
        const output = outputAt(point);
        const s = output ? surfaceOfOutput(output) : null;
        if (!s || ignored(s)) {
            return null;
        }
        const cell = s.cells.find(function (c) {
            return c.id !== except && G.contains(c.rect, point);
        });
        return cell ? state.records.get(cell.id) || null : null;
    }

    // A window let go after a drag. At the top edge (`maximize`) it is maximized -- a tiled window
    // keeps its place in the layout, on the screen it was let go on, and takes it again when it is
    // restored (`keepsSlot`). Over a zone it is put there and floats -- a tiled window that came by
    // Shift leaves the tiling. Anywhere else a tiled window swaps with the tiled window under the
    // cursor or goes back to its place, and a floating one stays where it was let go. A tiled
    // window in no layout where it comes from -- on a screen kept out of the tiling -- has no place
    // to swap or go back to, so it is counted where it was let go, as a floating one is.
    function dropped(rec, drop) {
        if (state.disposed || !state.on || !state.records.has(rec.id)) {
            return;
        }
        untarget(rec);
        const from = rec.key;
        if (drop.maximize) {
            rec.w.setMaximize(true, true);
            settle(rec, false);
            schedule(from);
            return;
        }
        if (drop.zone) {
            rec.w.setMaximize(false, false);
            write(rec, G.atLeast(drop.zone, needsOf(rec)));
            // Put there by the person's hand, a window waiting for room waits no more: it floats as
            // a window floated by hand does.
            if (state.settings.auto && (kindOf(rec) === "tile" || rec.outOfRoom)) {
                rec.override = "float";
                rec.outOfRoom = false;
                holdAbove(rec, "float");
            }
            settle(rec, false);
            schedule(from);
            return;
        }
        const home = from ? state.surfaces.get(from) : null;
        if (state.settings.auto && !!home && isMember(rec, home)) {
            const other = memberAt(drop.cursor, rec.id);
            if (other) {
                swapWith(rec, other);
            }
            schedule(rec.key);
            return;
        }
        settle(rec, false);
    }

    // A window let go where it was taken: Esc to the drag, which changed nothing. A tiled window
    // out of its zone there was moved by its application before it was taken, and was not looked
    // at while it was in the person's hand (`reassert`): it is looked at once still, as it would
    // have been. Left as it was, the next pass over its screen put it back, whatever started that
    // pass (seen in tests/engine_harness.mjs, `ownMovesHeld`).
    function droppedInPlace(rec) {
        if (state.disposed || !core.on() || !state.settings.auto || !rec.target
                || G.near(G.rectOf(rec.w.frameGeometry), rec.target)) {
            return;
        }
        lookAgain(rec);
    }

    function placesAgain() {
        if (!state.disposed) {
            env.later(flushPlaces);
        }
    }

    // Many signals say a desktop, a screen or the activity changed -- the current desktop, the list
    // of them, the screens, the current activity -- and often several at once, so they are read
    // once, later: one switch of the desktop was measured to bring `currentDesktopChanged` once per
    // screen, the first while the other screen still showed the desktop before, and a switch of
    // the activity first puts each screen on the desktop it last showed there (read in KWin
    // 6.7.5's source, `Activities::slotCurrentChanged`). A window that is counted somewhere else
    // after it -- one on two desktops, now shown on the other, or one on every activity -- did not
    // arrive anywhere new, so it goes at the end rather than where a new window goes.
    function flushPlaces() {
        if (state.disposed || !state.settings) {
            return;
        }
        state.records.forEach(function (rec) {
            if (!drag.busy(rec)) {
                settle(rec, false);
            }
        });
        scheduleVisible();
    }

    return {
        // Every window already open when the script loads.
        start: function () {
            listOf(W.windows).forEach(function (w) {
                if (!R.internal(w)) {
                    adopt(w);
                }
            });
        },

        // The daemon's answer, as text. Acted on only when it differs from the last one.
        answer: function (text) {
            if (state.disposed) {
                return false;
            }
            const raw = String(text);
            if (raw === state.text) {
                return false;
            }
            state.text = raw;
            let obj = null;
            try {
                obj = JSON.parse(raw);
            } catch (e) {
                log("could not read the tiling settings: " + e);
                return false;
            }
            if (!obj || obj.version !== ANSWER_VERSION) {
                // A newer daemon's answer is not guessed at: nothing is tiled until the script
                // that reads it is loaded, at the next login.
                log("the tiling settings come in a shape this script does not read: "
                    + (obj ? obj.version : "none"));
                apply(settingsOf({tiling: false}));
                return true;
            }
            if (obj.error) {
                log("the daemon could not resolve the tiling settings: " + obj.error);
            }
            apply(settingsOf(obj));
            return true;
        },

        windowAdded: function (w) {
            if (state.disposed) {
                return;
            }
            // The outline is one of the compositor's internal windows, so it is looked at before
            // they are left out.
            if (w.outline === true) {
                drag.outlineAdded(w);
            }
            if (R.internal(w)) {
                return;
            }
            const rec = adopt(w);
            if (state.settings) {
                // Read before anything here can change it: the compositor has made the window
                // the active one by now, where it lets it be (measured).
                const active = isActive(w);
                const rule = R.classify(w, state.settings);
                own(rec, rule);
                overflow(rec, active, rule);
                judge(rec, true);
            }
            if (isPanel(w)) {
                scheduleVisible();
            }
        },

        windowRemoved: function (w) {
            if (state.disposed) {
                return;
            }
            if (w.outline === true) {
                drag.outlineRemoved(w);
            }
            const rec = state.records.get(String(w.internalId));
            if (!rec) {
                return;
            }
            drag.forget(rec);
            takeOut(rec);
            // An X11 window hidden and shown again goes, and comes back as a new window with an
            // id of its own, so nothing is kept for it.
            state.due.delete(rec.id);
            state.records.delete(rec.id);
            state.focus = state.focus.filter(function (id) { return id !== rec.id; });
            // A window that goes keeps nothing of the engine's: its keep-above is not given back
            // to a window that is closing, and no window is kept above it, or it above another.
            state.raised.delete(rec.id);
            unconstrainWhere(function (pair) {
                return pair.below === rec.id || pair.above === rec.id;
            });
            if (isPanel(w)) {
                scheduleVisible();
            }
            leftEmpty(rec, w);
            tidySoon();
        },

        // A window that becomes the active one. KyprX's settings window made active again lets go
        // of every window held above it (`constrainOver`): it is the window kept above the others,
        // and one opened from it stays above it only until the person comes back to it.
        windowActivated: function (w) {
            if (state.disposed || !w || R.internal(w)) {
                return;
            }
            const id = String(w.internalId);
            state.focus = [id].concat(state.focus.filter(function (x) { return x !== id; }))
                .slice(0, 64);
            if (state.raised.has(id)) {
                unconstrainWhere(function (pair) { return pair.below === id; });
            }
        },

        // Workspace.desktopsChanged and currentDesktopChanged alike: the windows counted again,
        // and KyprX's desktops looked over a moment later.
        desktopsChanged: function () {
            placesAgain();
            tidySoon();
        },
        screensChanged: placesAgain,
        // Workspace.currentActivityChanged: every window is counted again on the surfaces of the
        // activity now in use, and those are laid out.
        activityChanged: function () {
            placesAgain();
            tidySoon();
        },

        // Options.configChanged: the compositor read its settings again, so the screen edges hold
        // the person's values; those are the ones to give back, and they go off again.
        optionsChanged: function () {
            if (!state.disposed && state.on) {
                bordersOff();
            }
        },

        // One of the tiling keys, by its action id. False when it is not one or the engine is
        // not tiling.
        action: function (name) {
            if (state.disposed || !state.on || !state.settings
                    || !Object.prototype.hasOwnProperty.call(ACTIONS, name)) {
                return false;
            }
            const spec = ACTIONS[name];
            try {
                if (spec[0] === "focus") {
                    focus(spec[1]);
                } else if (spec[0] === "move") {
                    move(spec[1]);
                } else if (spec[0] === "resize") {
                    resize(spec[1], spec[2]);
                } else if (spec[0] === "toggleFloat") {
                    toggleFloat();
                } else if (spec[0] === "setMaster") {
                    setMaster();
                } else if (spec[0] === "rotate") {
                    rotate(spec[1]);
                } else if (spec[0] === "toggleAuto") {
                    toggleAuto();
                } else if (spec[0] === "cycle") {
                    cycle(spec[1]);
                }
            } catch (e) {
                log("could not do " + name + ": " + e);
            }
            return true;
        },

        liveTick: function () {
            if (!state.disposed) {
                drag.liveTick();
            }
        },

        commitTick: function () {
            if (!state.disposed) {
                drag.commitTick();
            }
        },

        // main.qml's preview timer ran out: the zones manual tiling's layout keys drew go, unless
        // a drag has the zone windows by now (`drag.mjs`).
        previewTick: function () {
            if (!state.disposed) {
                drag.previewTick();
            }
        },

        // main.qml's cleanup timer ran out: KyprX's desktops are looked over (`tidy`).
        cleanupTick: function () {
            if (!state.disposed && ownsDesktops()) {
                tidy();
            }
        },

        // main.qml's quiet timer ran out: the windows due that have been still for a whole turn
        // of it are looked at (`reassert`).
        quietTick: function () {
            if (!state.disposed) {
                flushDue();
            }
        },

        // Component.onDestruction: the script is going. The keep-above this engine set and the
        // screen edges are given back, and nothing here answers again. No desktop is removed: one
        // KyprX made and left empty goes at the next look over them, in this session or the next.
        dispose: function () {
            if (state.disposed) {
                return;
            }
            drag.dispose();
            lowerAll();
            bordersBack();
            stopTidying();
            state.due.clear();
            stopQuiet();
            state.disposed = true;
        },

        // What the engine holds, as plain data, for the checks and for reading a session's log --
        // and the desktops it takes for KyprX's by their names, which it does not hold.
        peek: function () {
            const surfaces = {};
            state.surfaces.forEach(function (s, key) {
                surfaces[key] = {activity: s.activity, arrangement: s.arrangement,
                                 zone: s.zone, order: s.order.slice(),
                                 adjusted: Array.from(s.adjusted.keys()),
                                 fitted: !!(s.shown && s.shown.fitted),
                                 shown: s.shown ? G.textOf(s.shown.tree) : ""};
            });
            const windows = {};
            state.records.forEach(function (rec, id) {
                windows[id] = {kind: kindOf(rec), key: rec.key, override: rec.override,
                               outOfRoom: rec.outOfRoom,
                               joined: rec.key && rec.joins.has(rec.key) ? rec.joins.get(rec.key)
                                   : 0,
                               back: lately(rec.drift.back, now()).length,
                               stands: !!rec.drift.stands,
                               extra: {width: rec.extra.width, height: rec.extra.height},
                               why: rec.rule ? rec.rule.why : ""};
            });
            const list = desktopList();
            const made = list.filter(function (d) { return !!markOf(d, list); })
                .map(function (d) { return {id: String(d.id), name: String(d.name)}; });
            return {on: state.on, auto: core.auto(), borders: state.borders, surfaces: surfaces,
                    windows: windows, due: Array.from(state.due), drag: drag.peek(),
                    dry: !!state.settings && state.settings.dry, onSince: state.onSince,
                    raised: Array.from(state.raised),
                    constraints: state.pairs.map(function (p) { return [p.below, p.above]; }),
                    kyprxDesktops: made};
        },
    };
}
