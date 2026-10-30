// What a window being dragged or resized with the mouse does to the tiling: the zones and the
// selector of zone layouts shown while it moves, where it lands when it is let go, and the dividers
// an edge takes with it; and the zones manual tiling's layout keys show for a moment.
//
// **When the zones show.** With manual tiling, on every drag. With automatic tiling, on the drag of
// a floating window, and on the drag of a tiled one only while Shift is held. No compositor script
// can read a modifier key, so Shift is read from what the compositor does with it: holding Shift
// during a drag makes KWin draw its own outline of a tile, a window that arrives in `windowAdded`
// with `outline` true, and a drop with Shift held leaves the window in one of KWin's own tiles
// (`w.tile`). Hence the latch: on when the outline arrives during a drag; off only when the
// outline goes while the window is still moving (`move` true) -- Shift let go mid-drag -- because
// the outline also goes at the drop; and at the drop, Shift counts when the latch is on or the
// window has a KWin tile, after which the latch is cleared. The outline itself is made invisible,
// since KyprX's zones are what the drag is about. Measured in the sandbox (scripts/sandbox.sh,
// which drives drags through the compositor's fake input): with Shift held, the outline arrived in
// `windowAdded` with `outline` true, pid -1 and no caption, its opacity went to 0 and the zones
// showed; let go over a zone, the window was never put in one of KWin's own tiles -- its `tile`
// did not change -- so the latch is what counts there. If KWin stops drawing that outline, Shift
// stops showing the zones and nothing else changes; with KWin's own tile layout empty there is no
// outline to see (read in its source, not measured).
//
// **Every drag that ends, ends the same way** (`finished`): first the window is taken out of any
// KWin tile -- Shift with Esc, and a Shift drop outside KyprX's zones, both leave it in one -- then
// it is held against the snapshot taken when the drag began. A window the tiling never takes is
// the exception, left to the compositor with its outline and its tile: those are KWin's own
// tiling, which such a window may well be meant for. Back where it started means Esc, and the
// drag does nothing more -- the engine looks again at a tiled window its application had moved
// out of its zone before it was taken (`droppedInPlace`). Over a zone, it is put there and floats.
// Anywhere else, a tiled window in a layout swaps with the tiled window under the cursor or goes
// back to its place, and any other window is counted where it is let go (`engine.mjs`,
// `dropped`).
//
// **A resize moves dividers.** Each edge the window's frame moved takes the divider on that side
// of its zone with it, held by MIN_SHARE and by what the neighbours need; the neighbours follow
// every 33 ms while the edge moves when `live` is on. At the end the compositor's last word on
// the window's size may not have arrived yet: on Wayland a size a script writes lands 2 to 7 ms
// later, when the application has drawn it, and the size Esc puts back lands the same way -- Esc
// ended a resize at once, at the size pulled to, and the size put back arrived 6 to 7 ms after
// (both measured; a moved window was already back where it started when its drag ended). So the
// decision waits for the window's next `frameGeometryChanged`, up to 300 ms: back to the snapshot
// is Esc, and the dividers and the neighbours go back too; anything else is kept. A drag that took
// a window out of maximization waits the same way before it is judged: at
// `interactiveMoveResizeStarted` its `maximizeMode` still says maximized (measured: 3). Esc counts
// only on its own -- with Meta still held from a Meta and right-button resize the key is Meta+Esc,
// and the compositor carried the resize on to the release (measured).
//
// While an edge moves, the layout is worked out again from the snapshot each time, never from the
// last step, so a long drag does not drift; the window itself is left to the compositor until it
// is let go.
//
// **The selector** is a row of thumbnails across the top of the screen under the cursor: the whole
// screen, then the zone layouts a drag offers, in the pool's order -- the first twelve, and the
// screen's own after them when it is not among those (`bar` in engine.mjs) -- with the name of the
// one under the cursor, or else of the one shown, under the row. The thumbnail under the cursor
// becomes the screen's zone layout (`zone`), whose zones are the ones shown and dropped into. Each
// screen's row stays as the drag first drew it: a thumbnail that took the screen off a zone layout
// past the first twelve would otherwise take that one's thumbnail out from under the cursor, and
// the row would close up and move.
//
// **Manual tiling's layout keys** show the zones of the zone layout they move a screen to, on that
// screen alone, for a moment (`preview`, and main.qml's preview timer), with no selector: the name
// card says the name. A move or a resize that starts takes the zone windows back at once, and the
// timer hides nothing while one is under way -- the zone windows are the drag's then.
//
// `cursorPosChanged` is listened to only while a window moves: the selector's thumbnails and the
// zones are hit-tested in JavaScript against the cursor, since the overlays let every click and
// every hover through to the windows below them.

import * as G from "./geometry.mjs";

// The gaps of a thumbnail's own small zones, in pixels.
export const THUMB_GAPS = Object.freeze({top: 3, bottom: 3, left: 3, right: 3, between: 3});

// Take a window out of whichever of KWin's own tiles holds it. True when one did. Measured in the
// sandbox, in a declarative script: a window has `tile`, a tile has `manage` and `unmanage`, and a
// window put in a tile with `manage` is out of it again, `tile` null, after `unmanage`.
export function untile(w) {
    const tile = w.tile;
    if (!tile) {
        return false;
    }
    if (typeof tile.unmanage === "function") {
        tile.unmanage(w);
    }
    return true;
}

export function create(env, core) {
    const W = env.Workspace;
    const s = {
        disposed: false,
        move: null,
        resize: null,
        commit: null,
        outline: false,
        listening: false,
        drawn: new Map(),
        // The zone window manual tiling's layout keys drew on, until the preview timer runs out.
        preview: null,
    };

    function timer(name) {
        return env.timers && env.timers[name] ? env.timers[name] : null;
    }

    function busy(rec) {
        return (!!s.move && s.move.rec === rec) || (!!s.resize && s.resize.rec === rec)
            || (!!s.commit && s.commit.rec === rec);
    }

    // Whether the compositor has a window being moved or resized, whichever window it is: its
    // `move` or `resize`, which are true from before its `interactiveMoveResizeStarted` to before
    // its `interactiveMoveResizeFinished` (read in KWin 6.7.5's source, `Window`). That they are
    // true as a drag starts is also what `started` rests on, which the sandbox's drags measure.
    function held() {
        const list = W.windows;
        for (let i = 0; !!list && i < list.length; i++) {
            if (list[i].move === true || list[i].resize === true) {
                return true;
            }
        }
        return false;
    }

    function onCursor() {
        if (!s.disposed && s.move) {
            refresh();
        }
    }

    function listen(on) {
        const signal = W.cursorPosChanged;
        if (!signal) {
            return;
        }
        if (on && !s.listening) {
            signal.connect(env.owner, onCursor);
            s.listening = true;
        } else if (!on && s.listening) {
            signal.disconnect(env.owner, onCursor);
            s.listening = false;
        }
    }

    // ------------------------------------------------------------------- the overlays

    function overlays() {
        return env.overlays ? env.overlays() : [];
    }

    // What one screen shows: the zones of its surface's zone layout, and, on the screen under the
    // cursor, the selector, from `bars` -- the move's own, each screen's row as the drag first
    // drew it -- and the name of the zone layout shown, which is the one under the cursor when the
    // cursor is on a thumbnail.
    function viewOf(output, cursor, here, bars) {
        const none = {zones: [], cells: [], thumbs: [], trees: [], hovered: -1,
                      hoveredThumb: -1, current: -1, label: ""};
        const surface = core.surfaceOfOutput(output);
        if (!surface || core.ignored(surface)) {
            return none;
        }
        const area = core.areaOf(surface.output, surface.desktop);
        if (!area) {
            return none;
        }
        let list = [];
        let thumbs = [];
        let hoveredThumb = -1;
        if (here) {
            list = bars.get(surface.key) || core.bar(surface);
            bars.set(surface.key, list);
            const screen = G.rectOf(output.geometry);
            thumbs = G.thumbnails(area, list.length,
                                  screen.height > 0 ? screen.width / screen.height : 0);
            hoveredThumb = G.hit(thumbs, cursor);
            if (hoveredThumb >= 0) {
                surface.zone = list[hoveredThumb].id;
            }
        }
        const zone = core.zoneOf(surface);
        const cells = G.cells(zone.tree, area, core.gaps());
        const onSelector = thumbs.length > 0 && G.contains(G.band(thumbs), cursor);
        return {zones: G.zoneRects(zone.tree, area, core.gaps()), cells: cells, thumbs: thumbs,
                trees: list.map(function (z) { return z.tree; }),
                hovered: here && !onSelector ? G.hit(cells, cursor) : -1,
                hoveredThumb: hoveredThumb,
                current: list.findIndex(function (z) { return z.id === zone.id; }),
                label: here ? String(zone.name) : ""};
    }

    function assign(overlay, name, value) {
        let drawn = s.drawn.get(overlay);
        if (!drawn) {
            drawn = {};
            s.drawn.set(overlay, drawn);
        }
        const text = JSON.stringify(value);
        if (drawn[name] !== text) {
            drawn[name] = text;
            overlay[name] = value;
        }
    }

    function draw(overlay, view, origin) {
        assign(overlay, "zones", view.zones.map(function (r) { return G.relative(r, origin); }));
        assign(overlay, "hovered", view.hovered);
        assign(overlay, "thumbs", view.thumbs.map(function (t, i) {
            return {x: t.x - origin.x, y: t.y - origin.y, width: t.width, height: t.height,
                    zones: G.zoneRects(view.trees[i], {x: 0, y: 0, width: t.width,
                                                       height: t.height}, THUMB_GAPS)};
        }));
        assign(overlay, "hoveredThumb", view.hoveredThumb);
        assign(overlay, "currentThumb", view.current);
        assign(overlay, "label", view.label);
        assign(overlay, "shown", view.zones.length > 0 || view.thumbs.length > 0);
    }

    function hide(overlay) {
        assign(overlay, "shown", false);
        assign(overlay, "hovered", -1);
        assign(overlay, "hoveredThumb", -1);
    }

    function hideAll() {
        overlays().forEach(hide);
    }

    // The zone under the cursor as it is now, on the screen it is on: the rectangle a window let
    // go there is given, or null.
    function zoneAt(cursor, bars) {
        const output = core.outputAt(cursor);
        if (!output) {
            return null;
        }
        const view = viewOf(output, cursor, true, bars);
        return view.hovered >= 0 ? view.zones[view.hovered] : null;
    }

    function refresh() {
        const m = s.move;
        if (!m) {
            return;
        }
        const active = !core.auto() || !m.tiled || m.latch;
        if (!active) {
            if (m.active) {
                hideAll();
            }
            m.active = false;
            return;
        }
        m.active = true;
        const cursor = core.cursor();
        const at = core.outputAt(cursor);
        overlays().forEach(function (overlay) {
            const output = overlay.output;
            if (!output) {
                return;
            }
            const here = !!at && String(output.name) === String(at.name);
            draw(overlay, viewOf(output, cursor, here, m.bars), G.rectOf(output.geometry));
        });
    }

    // ------------------------------------------------------------------- manual tiling's keys

    // The zones of the zone layout a screen offers now, on that screen alone, with no selector and
    // no name, until the preview timer runs out. Not while a move is under way -- that one's zone
    // windows show the screen's zone layout as it is, so they are drawn again -- nor while a resize
    // is, which can only be one that began before automatic tiling was switched off; and not
    // without the timer that takes them away. So the zone windows are never the preview's while a
    // window is held, and the timer has nothing of a drag's to hide. One at a time: the keys
    // pressed on another screen take them from the first.
    function preview(surface) {
        if (s.move) {
            refresh();
            return;
        }
        const t = timer("preview");
        if (!t || s.resize) {
            return;
        }
        const overlay = overlays().find(function (o) {
            return !!o.output && String(o.output.name) === surface.output;
        }) || null;
        const area = overlay ? core.areaOf(surface.output, surface.desktop) : null;
        if (!area) {
            return;
        }
        if (s.preview && s.preview !== overlay) {
            hide(s.preview);
        }
        const origin = G.rectOf(overlay.output.geometry);
        assign(overlay, "zones", G.zoneRects(core.zoneOf(surface).tree, area, core.gaps())
            .map(function (r) { return G.relative(r, origin); }));
        assign(overlay, "hovered", -1);
        assign(overlay, "thumbs", []);
        assign(overlay, "hoveredThumb", -1);
        assign(overlay, "currentThumb", -1);
        assign(overlay, "label", "");
        assign(overlay, "shown", true);
        s.preview = overlay;
        t.restart();
    }

    function endPreview() {
        const t = timer("preview");
        if (t) {
            t.stop();
        }
        if (s.preview) {
            hide(s.preview);
            s.preview = null;
        }
    }

    // ------------------------------------------------------------------- the end of a drag

    function decide() {
        const c = s.commit;
        if (!c) {
            return;
        }
        s.commit = null;
        const t = timer("commit");
        if (t) {
            t.stop();
        }
        if (!core.on()) {
            return;
        }
        const now = G.rectOf(c.rec.w.frameGeometry);
        const back = G.near(now, c.start);
        if (c.kind === "resize") {
            core.adjust(c.key, c.slot, back ? c.had
                : G.resized(c.tree, c.area, c.gaps, c.path, c.start, now, c.minOf));
            core.untarget(c.rec);
            core.schedule(c.key);
        } else if (!back) {
            core.dropped(c.rec, c.drop);
        }
    }

    function wait(commit) {
        s.commit = commit;
        const t = timer("commit");
        if (t) {
            t.restart();
        } else {
            decide();
        }
    }

    function clear() {
        s.move = null;
        s.resize = null;
        s.commit = null;
        s.preview = null;
        listen(false);
        hideAll();
        ["live", "commit", "preview"].forEach(function (name) {
            const t = timer(name);
            if (t) {
                t.stop();
            }
        });
    }

    return {
        busy: busy,

        // Whether any window is held: a move or a resize under way, of any window at all, or one
        // of the tiling's still being judged after it ended. The engine sends no window to another
        // desktop meanwhile -- a switch of desktop under the person's hand would take the screen
        // from what they are dragging, and the compositor takes the window being moved or resized
        // along to the desktop switched to (read in KWin 6.7.5's source,
        // `Workspace::updateWindowVisibilityOnDesktopChange`; not measured). The compositor is
        // asked (`held`) because this module holds only what the tiling takes part in: a move of
        // a window the tiling never takes, a resize of a floating window -- KyprX's settings
        // window among them -- and a resize on a screen kept out of the tiling leave nothing here.
        busyAny: function () {
            return !!s.commit || held();
        },

        started: function (rec) {
            if (s.disposed) {
                return;
            }
            // Whatever is dragged, the zones a layout key showed go.
            endPreview();
            if (!core.on() || core.kindOf(rec) === "never") {
                return;
            }
            // A drag that starts while the last one is still being judged settles that one first.
            if (s.commit) {
                decide();
            }
            const w = rec.w;
            const start = G.rectOf(w.frameGeometry);
            if (w.move === true) {
                s.move = {rec: rec, start: start, maximized: core.keepsSlot(rec),
                          tiled: core.auto() && core.kindOf(rec) === "tile", latch: s.outline,
                          active: false, bars: new Map()};
                listen(true);
                refresh();
            } else if (w.resize === true) {
                const snap = core.snapshot(rec);
                if (snap) {
                    s.resize = Object.assign(snap, {rec: rec, start: start, pending: null});
                }
            }
        },

        stepped: function (rec, geometry) {
            const r = s.resize;
            if (s.disposed || !r || r.rec !== rec) {
                return;
            }
            const now = G.rectOf(geometry || rec.w.frameGeometry);
            r.pending = G.resized(r.tree, r.area, r.gaps, r.path, r.start, now, r.minOf);
            const t = timer("live");
            if (core.live() && t && !t.running) {
                t.start();
            }
        },

        finished: function (rec) {
            if (s.disposed) {
                return;
            }
            if (!core.on()) {
                clear();
                return;
            }
            // A window the tiling never takes is left to the compositor, KWin's own tiles and all.
            if (!busy(rec) && core.kindOf(rec) === "never") {
                return;
            }
            const kwinTile = untile(rec.w);
            if (s.move && s.move.rec === rec) {
                const m = s.move;
                s.move = null;
                listen(false);
                hideAll();
                const shifted = m.latch || kwinTile;
                s.outline = false;
                const cursor = core.cursor();
                const drop = {cursor: cursor,
                              zone: !core.auto() || !m.tiled || shifted ? zoneAt(cursor, m.bars)
                                  : null};
                if (m.maximized) {
                    wait({kind: "move", rec: rec, start: m.start, drop: drop});
                } else if (!G.near(G.rectOf(rec.w.frameGeometry), m.start)) {
                    core.dropped(rec, drop);
                } else {
                    core.droppedInPlace(rec);
                }
            } else if (s.resize && s.resize.rec === rec) {
                const r = s.resize;
                s.resize = null;
                const t = timer("live");
                if (t) {
                    t.stop();
                }
                wait(Object.assign(r, {kind: "resize"}));
            }
        },

        // Every `frameGeometryChanged` of a window the engine knows passes here first. True when
        // the drag has it: the window is the person's while they hold it.
        geometryChanged: function (rec) {
            if (s.disposed) {
                return false;
            }
            if (s.commit && s.commit.rec === rec) {
                decide();
                return true;
            }
            return busy(rec);
        },

        outlineAdded: function (w) {
            if (s.disposed || !core.on()) {
                return;
            }
            s.outline = true;
            if (s.move) {
                w.opacity = 0;
                s.move.latch = true;
                refresh();
            }
        },

        outlineRemoved: function () {
            if (s.disposed) {
                return;
            }
            s.outline = false;
            if (s.move && s.move.rec.w.move === true) {
                s.move.latch = false;
                refresh();
            }
        },

        liveTick: function () {
            const r = s.resize;
            if (s.disposed || !r || !r.pending || !core.on()) {
                return;
            }
            core.adjust(r.key, r.slot, r.pending);
            core.schedule(r.key);
        },

        commitTick: function () {
            if (!s.disposed) {
                decide();
            }
        },

        preview: function (surface) {
            if (!s.disposed) {
                preview(surface);
            }
        },

        // The preview timer ran out. A move or a resize that started since has taken the preview
        // away already (`started`), and then nothing is left here to hide.
        previewTick: function () {
            if (s.disposed || !s.preview) {
                return;
            }
            hide(s.preview);
            s.preview = null;
        },

        forget: function (rec) {
            if (busy(rec)) {
                clear();
            }
        },

        cancel: clear,

        dispose: function () {
            clear();
            s.disposed = true;
        },

        peek: function () {
            return {move: s.move ? {id: s.move.rec.id, latch: s.move.latch, active: s.move.active}
                    : null,
                    resize: s.resize ? s.resize.rec.id : "", commit: s.commit ? s.commit.kind : "",
                    listening: s.listening, outline: s.outline,
                    preview: s.preview && s.preview.output ? String(s.preview.output.name) : ""};
        },
    };
}
