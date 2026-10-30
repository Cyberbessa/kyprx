// The geometry of KyprX's tiling: rectangles from a layout, dividers from a moved edge, the room a
// window's minimum is given, and the zone or the thumbnail under the cursor. Nothing else -- no
// KWin, no Qt, no state.
//
// A layout is a tree in `daemon/tiling.py`'s format -- an arrangement's layout for a number of
// windows and a zone layout of the pool are trees alike: a zone `{}`, or a split
// `{"split": "h" | "v", "sizes": [...], "parts": [...]}` whose parts lie side by side (`h`) or top
// to bottom (`v`), each a share of the split in percent. A layout's root may carry `master`, the
// index of the zone (depth-first) that is filled first. A path is the list of part indices from
// the root down to a node; `[]` is the root.
//
// Every function answers from its arguments alone and never changes a tree it is given: the ones
// that edit return a new tree. That is what lets the engine keep a layout per arrangement and per
// window count and try a change before keeping it, and it is what lets the checks hold these
// rectangles to `gui/splits.py`'s -- the Tiling tab draws its thumbnails with that module, so the
// two have to agree to the pixel (tests/test_tiling_geometry.py).
//
// Nothing here touches `Qt`, `console` or `print`, at the top or anywhere else. Inside the
// compositor a module sees all three; the checks import these files into a plain QJSEngine, where
// a module sees none of them (measured: `typeof Qt` is "undefined" there).

// The smallest share a part keeps, in percent -- daemon/tiling.py's MIN_SHARE.
export const MIN_SHARE = 5;

// How far Grow and Shrink move a divider: this many percent of the split it belongs to.
export const STEP = 5;

// How far apart two rectangles may be, in pixels on every edge, and still count as the same: a
// write that landed, a window back where it started. Two because the compositor works in
// fractional pixels and an application may round its own size.
export const TOLERANCE = 2;

// What the focus and move keys count a window that overlaps as, before its own distance: more
// than any screen is wide (`towards`).
const BEYOND = 1000000;

// The selector drawn at the top of a screen while a window is dragged, a thumbnail for the whole
// screen and for each zone layout a drag offers: how tall each thumbnail is at most and at least,
// the room between two, and how far the row sits from the top of the usable area.
export const THUMB = Object.freeze({height: 72, least: 36, gap: 14, margin: 18});

// ------------------------------------------------------------------------- trees

export function isZone(node) {
    return !node || !node.split;
}

export function keyOf(path) {
    return path.join(".");
}

export function copyTree(node) {
    return JSON.parse(JSON.stringify(node));
}

// A tree as text with every object's keys in order, as the daemon writes a tree's canonical text:
// two trees are one layout when theirs are one text, whatever order their keys came in. The answer
// names an arrangement's layouts by their trees and not by the zone layouts they are, so this is
// what the engine finds a zone layout by (`homesOf` in engine.mjs).
export function textOf(node) {
    return JSON.stringify(node, function (key, value) {
        if (!value || typeof value !== "object" || Array.isArray(value)) {
            return value;
        }
        const sorted = {};
        Object.keys(value).sort().forEach(function (name) { sorted[name] = value[name]; });
        return sorted;
    });
}

// Every zone's path, depth-first: the order `master` counts in.
export function leafPaths(node, path) {
    const here = path || [];
    if (isZone(node)) {
        return [here];
    }
    let found = [];
    for (let i = 0; i < node.parts.length; i++) {
        found = found.concat(leafPaths(node.parts[i], here.concat([i])));
    }
    return found;
}

export function zoneCount(node) {
    return leafPaths(node).length;
}

export function masterOf(root) {
    const master = root && root.master;
    return Number.isInteger(master) && master >= 0 && master < zoneCount(root) ? master : 0;
}

// The order windows fill the zones in: the master zone first, then the rest depth-first. The
// first window of a screen's order goes to the first of these, and so on.
export function fillOrder(root) {
    const paths = leafPaths(root);
    const master = masterOf(root);
    return [paths[master]].concat(paths.slice(0, master), paths.slice(master + 1));
}

export function nodeAt(root, path) {
    let node = root;
    for (let i = 0; i < path.length; i++) {
        node = node.parts[path[i]];
    }
    return node;
}

// ------------------------------------------------------------------------- rectangles

export function rectOf(r) {
    return {x: Number(r.x), y: Number(r.y), width: Number(r.width), height: Number(r.height)};
}

// Half up, as `gui/splits.py`'s `nearest` rounds; the two have to land a share on the same pixel.
export function nearest(value) {
    return Math.floor(value + 0.5);
}

export function near(a, b, tolerance) {
    const t = tolerance === undefined ? TOLERANCE : tolerance;
    return !!a && !!b && Math.abs(a.x - b.x) <= t && Math.abs(a.y - b.y) <= t
        && Math.abs(a.width - b.width) <= t && Math.abs(a.height - b.height) <= t;
}

export function contains(rect, point) {
    return point.x >= rect.x && point.x < rect.x + rect.width
        && point.y >= rect.y && point.y < rect.y + rect.height;
}

// The index of the first rectangle the point is in, or -1.
export function hit(rects, point) {
    for (let i = 0; i < rects.length; i++) {
        if (contains(rects[i], point)) {
            return i;
        }
    }
    return -1;
}

// How far `to` is from `from` in a direction ("left", "right", "up", "down"), for the focus and
// move keys; -1 when its centre is not that way at all.
//
// A window wholly on that side -- as tiled neighbours are, across a gap -- counts by the room
// between the two edges; one that overlaps (floating windows do) only by its centre, and after
// every window wholly there. Either way twice the gap between the two across the direction is
// added, nothing where they overlap there, so the window beside one wins over a nearer one
// diagonally off -- and from the lower of two stacked windows, up is the one above it, not the
// tall one beside both.
export function towards(from, to, direction) {
    const fx = from.x + from.width / 2;
    const fy = from.y + from.height / 2;
    const tx = to.x + to.width / 2;
    const ty = to.y + to.height / 2;
    const along = {left: fx - tx, right: tx - fx, up: fy - ty, down: ty - fy}[direction];
    if (!(along > 0)) {
        return -1;
    }
    const edges = {left: from.x - (to.x + to.width), right: to.x - (from.x + from.width),
                   up: from.y - (to.y + to.height), down: to.y - (from.y + from.height)}[direction];
    const sideways = direction === "left" || direction === "right"
        ? Math.max(0, Math.max(from.y, to.y) - Math.min(from.y + from.height, to.y + to.height))
        : Math.max(0, Math.max(from.x, to.x) - Math.min(from.x + from.width, to.x + to.width));
    return (edges >= -TOLERANCE ? Math.max(0, edges) : BEYOND + along) + 2 * sideways;
}

export function relative(rect, origin) {
    return {x: rect.x - origin.x, y: rect.y - origin.y, width: rect.width, height: rect.height};
}

// The usable area less the gaps at its four edges, in whole pixels and never outside the area:
// a client area can come in fractions on a scaled screen.
export function inner(area, gaps) {
    const g = gaps || {};
    const x0 = Math.ceil(area.x) + (g.left || 0);
    const y0 = Math.ceil(area.y) + (g.top || 0);
    const x1 = Math.floor(area.x + area.width) - (g.right || 0);
    const y1 = Math.floor(area.y + area.height) - (g.bottom || 0);
    return {x: x0, y: y0, width: Math.max(0, x1 - x0), height: Math.max(0, y1 - y0)};
}

// The gap between two zones, split between them: a zone's left and top inner edges move in by
// the larger half, its right and bottom ones by the smaller, so two neighbours are always exactly
// `between` apart, odd or even.
export function halves(between) {
    const g = Math.max(0, Math.floor(between || 0));
    return {lead: Math.ceil(g / 2), trail: Math.floor(g / 2)};
}

// What a split of `length` whole pixels gives each of its parts, in whole pixels: each edge is
// placed from the running total of the shares, so the parts add up to the split exactly -- the
// last one ends where the split ends. `layoutRects` cuts every split by this, and so does `fit`,
// so the two can never disagree about a part.
export function pixelLengths(sizes, length) {
    const last = sizes.length - 1;
    const out = [];
    let start = 0;
    let total = 0;
    for (let i = 0; i <= last; i++) {
        total += sizes[i];
        const end = i === last ? length
            : Math.min(length, Math.max(start, nearest(length * total / 100)));
        out.push(end - start);
        start = end;
    }
    return out;
}

// Every node's rectangle in a frame, with no gaps: `{zones, splits}`, each keyed by `keyOf(path)`.
//
// The same rule as `layout_rects` in gui/splits.py: each split is cut by `pixelLengths`, so its
// parts tile it exactly and a layout covers its frame with nothing left over and nothing twice.
// Shares need not be whole numbers: a layout the person has resized with the mouse holds fractions
// until it is put back, and one fitted around a window's minimum (`fit`) holds them for as long as
// it is laid out.
export function layoutRects(root, frame) {
    const zones = {};
    const splits = {};
    function place(node, path, x, y, w, h) {
        const rect = {x: x, y: y, width: w, height: h};
        if (isZone(node)) {
            zones[keyOf(path)] = rect;
            return;
        }
        splits[keyOf(path)] = rect;
        const side = node.split === "h";
        const lengths = pixelLengths(node.sizes, side ? w : h);
        let start = 0;
        for (let i = 0; i < lengths.length; i++) {
            if (side) {
                place(node.parts[i], path.concat([i]), x + start, y, lengths[i], h);
            } else {
                place(node.parts[i], path.concat([i]), x, y + start, w, lengths[i]);
            }
            start += lengths[i];
        }
    }
    place(root, [], frame.x, frame.y, Math.max(0, Math.floor(frame.width)),
          Math.max(0, Math.floor(frame.height)));
    return {zones: zones, splits: splits};
}

// The zones' cells in fill order: the area less its outer gaps, divided by the layout, with no gap
// between neighbours. What the cursor is tested against, so that a gap is never a place where a
// drop lands on nothing.
export function cells(root, area, gaps) {
    const box = inner(area, gaps);
    const placed = layoutRects(root, box).zones;
    return fillOrder(root).map(function (path) {
        return placed[keyOf(path)];
    });
}

// The zones' rectangles in fill order, as windows are placed in them: the area less its outer
// gaps, divided by the layout, each inner edge moved in by its half of the gap between.
export function zoneRects(root, area, gaps) {
    const box = inner(area, gaps);
    const half = halves(gaps && gaps.between);
    const placed = layoutRects(root, box).zones;
    return fillOrder(root).map(function (path) {
        const r = placed[keyOf(path)];
        let x0 = r.x;
        let y0 = r.y;
        let x1 = r.x + r.width;
        let y1 = r.y + r.height;
        if (x0 > box.x) {
            x0 += half.lead;
        }
        if (y0 > box.y) {
            y0 += half.lead;
        }
        if (x1 < box.x + box.width) {
            x1 -= half.trail;
        }
        if (y1 < box.y + box.height) {
            y1 -= half.trail;
        }
        return {x: x0, y: y0, width: Math.max(0, x1 - x0), height: Math.max(0, y1 - y0)};
    });
}

// ------------------------------------------------------------------------- more windows than layouts

// A zone in two, the way gui/splits.py's `split` does it, so that on a screen of 16:9 the layout of
// one zone more the engine cascades to from an arrangement's last one is the very tree `grow`
// there makes of it -- the rule tests/test_tiling_geometry.py holds the cascade to: split the way
// its own split already runs, the zone becomes one more part of that split, halving its share (the
// first half keeps the odd percent); split the other way, it becomes a split of its own, a level
// deeper. The new zone is the second half, and the master stays the same zone.
//
// Where `split` would refuse -- a share too small to halve into two whole parts of MIN_SHARE, a
// split deeper than the format allows -- the engine nests instead: a layout above the last one an
// arrangement holds lives only in memory and is never written back.
export function splitZone(root, path, direction) {
    const tree = copyTree(root);
    const position = leafPaths(tree).map(keyOf).indexOf(keyOf(path));
    let master = masterOf(tree);
    const fresh = {split: direction, sizes: [50, 50], parts: [{}, {}]};
    let out = tree;
    if (path.length === 0) {
        out = fresh;
    } else {
        const parent = nodeAt(tree, path.slice(0, -1));
        const i = path[path.length - 1];
        const share = parent.sizes[i];
        if (parent.split === direction && share >= 2 * MIN_SHARE) {
            const second = Math.floor(share / 2);
            parent.sizes.splice(i, 1, share - second, second);
            parent.parts.splice(i + 1, 0, {});
        } else {
            parent.parts[i] = fresh;
        }
    }
    if (master > position) {
        master += 1;
    }
    delete out.master;
    if (master) {
        out.master = master;
    }
    return out;
}

// The layout for `count` windows when an arrangement holds fewer layouts: its last one, with the
// last zone in fill order split along its longer side, in the frame's pixels, until there are
// enough zones. The newest window takes the second half each time.
export function cascade(root, count, frame) {
    let tree = copyTree(root);
    for (let guard = 0; zoneCount(tree) < count && guard < 256; guard++) {
        const order = fillOrder(tree);
        const last = order[order.length - 1];
        const r = layoutRects(tree, frame).zones[keyOf(last)];
        tree = splitZone(tree, last, r.width > r.height ? "h" : "v");
    }
    return tree;
}

// The tree for `count` windows: the arrangement's own layout for that many, or the cascade from
// its last. `frame` is the area the cascade measures its longer sides in.
export function treeFor(layouts, count, frame) {
    if (count <= layouts.length) {
        return copyTree(layouts[count - 1]);
    }
    return cascade(layouts[layouts.length - 1], count, frame);
}

// ------------------------------------------------------------------------- dividers

// The divider on one side of a zone: the nearest split above it that runs across that side and
// in which the zone's branch has a neighbour on that side. `{split: path, index}` -- the divider
// between part `index` and the next -- or null where that side of the zone is the screen's edge.
export function dividerAt(root, path, side) {
    const direction = side === "left" || side === "right" ? "h" : "v";
    const after = side === "right" || side === "bottom";
    for (let depth = path.length - 1; depth >= 0; depth--) {
        const splitPath = path.slice(0, depth);
        const node = nodeAt(root, splitPath);
        const i = path[depth];
        if (node.split !== direction) {
            continue;
        }
        if (after && i < node.parts.length - 1) {
            return {split: splitPath, index: i};
        }
        if (!after && i > 0) {
            return {split: splitPath, index: i - 1};
        }
    }
    return null;
}

function sharesBefore(sizes, count) {
    let total = 0;
    for (let i = 0; i < count; i++) {
        total += sizes[i];
    }
    return total;
}

// The least a node can be along one axis, in pixels, from which on what its windows need there
// is theirs: at that length and at every longer one. Parts across the axis need as much as the
// widest of them. Parts along it add up, and each also keeps its MIN_SHARE of the node, in whole
// pixels rounded up as `fit` gives it -- summed alone, a split nested in a split the same way could
// be squeezed until a part of it with nothing to hold was cut to nothing. A node with nothing to
// hold needs nothing: `fit` never moves the lines of a split none of whose windows is short.
//
// Every longer length, and not only this one, because a divider can hand a part any length from
// its least up (`spread`, `placeDivider`), and a longer split does not always hold what a shorter
// one held: each time the length passes a multiple of 100 / MIN_SHARE, every part held at its share
// asks a pixel more while the length grows by one. A part that needs 864 and two that need nothing
// fit 960 with 48 each, and not 961, which asks 864 + 49 + 49: taken as their least, 960 left the
// first window 327 px wide in a column of 961, where a column a pixel wider holds it (worked out
// by hand in tests/test_tiling_geometry.py).
export function minExtent(node, path, axis, minOf) {
    if (isZone(node)) {
        const least = minOf ? minOf(path) : null;
        return least ? (least[axis] || 0) : 0;
    }
    const along = (node.split === "h") === (axis === "width");
    const each = [];
    let sum = 0;
    for (let i = 0; i < node.parts.length; i++) {
        each.push(minExtent(node.parts[i], path.concat([i]), axis, minOf));
        sum += each[i];
    }
    if (!along) {
        return Math.max.apply(null, [0].concat(each));
    }
    if (!sum) {
        return 0;
    }
    const asked = function (share) {
        let total = 0;
        for (let i = 0; i < each.length; i++) {
            total += Math.max(each[i], share);
        }
        return total;
    };
    // The least length every part fits in with its share of it. No length below what the parts
    // ask for at a shorter one can hold them, since a longer split asks no less of any part: so
    // from their own sum, each turn goes straight to what the last one asked, and the first that
    // holds them is the least.
    let length = sum;
    for (let guard = 0; guard < 64; guard++) {
        const total = asked(Math.ceil(length * MIN_SHARE / 100));
        if (total <= length) {
            break;
        }
        length = total;
    }
    // Then the shares above that length's, each at the first length that has it: where the parts
    // ask more there than that length, no length of that share short of what they ask holds them,
    // and the least is past those. From one share to the next, the first length grows by
    // 100 / MIN_SHARE and what the parts ask by a pixel for each part at most, so with fewer parts
    // than that, once a share holds them from its first length every later one does. Over the 5442
    // fits tests/test_tiling_geometry.py holds to the oracle, the first loop took four turns at
    // most and the second stopped at its first share every time (measured); the guards only stop a
    // split of twenty parts or more, which neither a zone layout (nine zones at most) nor the
    // cascade makes.
    for (let share = Math.ceil(length * MIN_SHARE / 100) + 1, guard = 0; guard < 64;
         share++, guard++) {
        const first = Math.floor((share - 1) * 100 / MIN_SHARE) + 1;
        const total = asked(share);
        if (total <= first) {
            break;
        }
        length = Math.min(total, Math.floor(share * 100 / MIN_SHARE) + 1);
    }
    return length;
}

function span(root, box, ref) {
    const node = nodeAt(root, ref.split);
    const rect = layoutRects(root, box).splits[keyOf(ref.split)];
    const across = node.split === "h";
    return {node: node, across: across, start: across ? rect.x : rect.y,
            length: across ? rect.width : rect.height};
}

// Where a divider is, in pixels along its split's axis.
export function dividerPosition(root, box, ref) {
    const s = span(root, box, ref);
    return s.start + nearest(s.length * sharesBefore(s.node.sizes, ref.index + 1) / 100);
}

// The layout with one divider at `position`, in pixels. Only the two parts on either side of it
// give or take, as on the Tiling tab; every other part keeps its share. Held where neither part
// drops below MIN_SHARE nor below what its windows need (`minOf(path)` -> {width, height} for a
// zone), and left where it is when the two already have no room to give.
export function placeDivider(root, box, ref, position, minOf) {
    const s = span(root, box, ref);
    if (s.length <= 0) {
        return root;
    }
    const i = ref.index;
    const before = sharesBefore(s.node.sizes, i);
    const pair = s.node.sizes[i] + s.node.sizes[i + 1];
    const axis = s.across ? "width" : "height";
    const firstLeast = minExtent(s.node.parts[i], ref.split.concat([i]), axis, minOf);
    const secondLeast = minExtent(s.node.parts[i + 1], ref.split.concat([i + 1]), axis, minOf);
    const a = s.start + s.length * before / 100;
    const b = s.start + s.length * (before + pair) / 100;
    const shareLeast = s.length * MIN_SHARE / 100;
    const low = Math.max(a + shareLeast, a + firstLeast);
    const high = Math.min(b - shareLeast, b - secondLeast);
    if (low > high) {
        return root;
    }
    const at = Math.max(low, Math.min(high, position));
    const share = (at - s.start) / s.length * 100 - before;
    const tree = copyTree(root);
    const node = nodeAt(tree, ref.split);
    node.sizes[i] = share;
    node.sizes[i + 1] = pair - share;
    return tree;
}

// The divider Grow and Shrink move for a zone along one axis ("width" or "height"): of the one
// on its far side (right, bottom) and the one on its near side, the nearer to the zone in the
// tree, and the far one when both are as near. `{ref, far}` or null.
export function nearestDivider(root, path, axis) {
    const far = dividerAt(root, path, axis === "width" ? "right" : "bottom");
    const close = dividerAt(root, path, axis === "width" ? "left" : "top");
    if (far && (!close || far.split.length >= close.split.length)) {
        return {ref: far, far: true};
    }
    return close ? {ref: close, far: false} : null;
}

// Grow or Shrink: the zone's nearest divider moved STEP percent of its split, away from the zone
// to grow it and towards it to shrink it. The same tree when there is no divider to move or no
// room to move it.
export function stepped(root, box, path, axis, grow, minOf) {
    const found = nearestDivider(root, path, axis);
    if (!found) {
        return root;
    }
    const s = span(root, box, found.ref);
    if (s.length <= 0) {
        return root;
    }
    const total = sharesBefore(s.node.sizes, found.ref.index + 1);
    const sign = found.far === grow ? 1 : -1;
    const position = s.start + s.length * (total + sign * STEP) / 100;
    return placeDivider(root, box, found.ref, position, minOf);
}

// The layout after a window resized from `before` to `after` with the mouse: each edge that
// moved takes the divider on that side of its zone with it, by as much as it moved. An edge on
// the screen's side has no divider, and the window goes back to its zone there when it is placed.
export function resized(root, area, gaps, path, before, after, minOf) {
    const box = inner(area, gaps);
    const moves = [
        ["left", after.x - before.x],
        ["right", (after.x + after.width) - (before.x + before.width)],
        ["top", after.y - before.y],
        ["bottom", (after.y + after.height) - (before.y + before.height)],
    ];
    let tree = root;
    for (let k = 0; k < moves.length; k++) {
        const side = moves[k][0];
        const delta = moves[k][1];
        if (Math.abs(delta) < 1) {
            continue;
        }
        const ref = dividerAt(tree, path, side);
        if (ref) {
            tree = placeDivider(tree, box, ref, dividerPosition(tree, box, ref) + delta, minOf);
        }
    }
    return tree;
}

// ------------------------------------------------------------------------- room

// Whether a rectangle holds what a window needs (`needs` in rules.mjs, {width, height}), or
// nothing is needed. Exact: a zone a pixel short is short. TOLERANCE is for judging where a write
// landed and never takes part in a minimum: the compositor does not hold a window to its minimum
// (rules.mjs), so a zone even a pixel short of it is a window laid out smaller than its
// application can draw it.
export function holds(rect, need) {
    return !need || (need.width <= rect.width && need.height <= rect.height);
}

// What each zone's cell -- its part of the area less the outer gaps, no gap between -- has to be
// for the window in it to have what it needs. `needs` is in fill order, one per zone: the window's
// {width, height}, or null for a zone whose window needs nothing of it. That is the need, in whole
// pixels, and on each side where the zone has a neighbour the half of the gap between it gives up
// there, the larger half on its left and top and the smaller on its right and bottom: exactly what
// `zoneRects` takes off. `minOf(path)` -> {width, height} or null, as `minExtent` and the dividers
// take it.
//
// The sides are read off the tree (`dividerAt`), where zoneRects asks the pixels whether an edge
// is inside the box. The two agree for every part at least a pixel long, and MIN_SHARE keeps every
// part that long on any split of 20 pixels or more.
export function leastOf(root, gaps, needs) {
    const half = halves(gaps && gaps.between);
    const order = fillOrder(root);
    const byPath = {};
    for (let k = 0; k < order.length; k++) {
        const need = needs ? needs[k] : null;
        if (!need) {
            continue;
        }
        const path = order[k];
        const side = function (name, gap) {
            return dividerAt(root, path, name) ? gap : 0;
        };
        byPath[keyOf(path)] = {
            width: Math.ceil(need.width || 0) + side("left", half.lead) + side("right", half.trail),
            height: Math.ceil(need.height || 0) + side("top", half.lead)
                + side("bottom", half.trail)};
    }
    return function (path) {
        return byPath[keyOf(path)] || null;
    };
}

// One split's parts in whole pixels with room made for what each needs: `lengths` as the split is
// cut now, `needs` what each part needs along it (`minExtent`), `least` its MIN_SHARE of the split
// in whole pixels. Null when no part is short of its need, or when the split cannot give every part
// its floor -- its need, and never less than `least`. Otherwise each part below its floor is raised
// to exactly that, and the pixels that takes come from the parts above their floors, in proportion
// to how far above they are; the pixels a proportion leaves over go one each to the largest
// remainders, the earlier part first between equals.
//
// Only a window's need sets it off. A part a pixel under MIN_SHARE from rounding is no reason to
// move a divider: every layout with no minimum in it would be rewritten, and stop being the one the
// Tiling tab shows. `fit` asks only when a window in the split would be left short (`leftShort`):
// a part's need counts a split inside it at MIN_SHARE too, which a part can be under and hold
// every window in it all the same.
export function spread(lengths, needs, least) {
    let short = false;
    let room = 0;
    let wanted = 0;
    for (let i = 0; i < lengths.length; i++) {
        short = short || lengths[i] < needs[i];
        room += lengths[i];
        wanted += Math.max(needs[i], least);
    }
    if (!short || wanted > room) {
        return null;
    }
    const floors = [];
    const above = [];
    let raised = 0;
    let spare = 0;
    for (let i = 0; i < lengths.length; i++) {
        floors.push(Math.max(needs[i], least));
        above.push(Math.max(0, lengths[i] - floors[i]));
        raised += Math.max(0, floors[i] - lengths[i]);
        spare += above[i];
    }
    // Whole numbers throughout, and products of two lengths at most -- far below 2^53, so each
    // division is exact to its floor. `spare` is at least `raised`, since the floors fit, so no
    // part gives more than it has above its floor.
    const taken = [];
    let left = raised;
    for (let i = 0; i < lengths.length; i++) {
        taken.push(Math.floor(raised * above[i] / spare));
        left -= taken[i];
    }
    const byRemainder = above.map(function (a, i) { return i; }).sort(function (i, j) {
        return (raised * above[j] - taken[j] * spare) - (raised * above[i] - taken[i] * spare)
            || i - j;
    });
    for (let k = 0; k < left; k++) {
        taken[byRemainder[k]] += 1;
    }
    return lengths.map(function (length, i) { return Math.max(length, floors[i]) - taken[i]; });
}

// Whether a node `length` pixels long along one axis leaves a window in it short there once `fit`
// has made what room it can inside it: a zone, when it is shorter than its cell (`minOf`); parts
// across the axis, when any of them does at that length; parts along it, when one of them does as
// the node is cut now (`pixelLengths`) and the parts cannot all have their own least and their
// MIN_SHARE, which is when `fit` leaves the node's lines where they are.
//
// What decides whether `fit` moves a line, rather than `minExtent`: a split in a part counts at
// MIN_SHARE there, rounded up, and the Tiling tab's own cut can give a part a pixel under that --
// 94 of a split of 1890 at 5 %, where MIN_SHARE asks 95 -- with every window in it holding its
// minimum. Judged by `minExtent` alone, such a part was short by that pixel, and the line beside it
// moved a pixel for no window, which the engine logged as room made with no window named (measured
// on a split of 95 and 5 in the right half of 3800 px, the hand case in
// tests/test_tiling_geometry.py).
function leftShort(node, path, axis, minOf, length) {
    if (isZone(node)) {
        return length < minExtent(node, path, axis, minOf);
    }
    const along = (node.split === "h") === (axis === "width");
    const lengths = along ? pixelLengths(node.sizes, length) : null;
    let short = false;
    for (let i = 0; i < node.parts.length && !short; i++) {
        short = leftShort(node.parts[i], path.concat([i]), axis, minOf,
                          along ? lengths[i] : length);
    }
    if (!short || !along) {
        return short;
    }
    const share = Math.ceil(length * MIN_SHARE / 100);
    let asked = 0;
    for (let i = 0; i < node.parts.length; i++) {
        asked += Math.max(minExtent(node.parts[i], path.concat([i]), axis, minOf), share);
    }
    return asked > length;
}

// A layout with room made in it for what its windows need: `root` with its dividers moved just far
// enough for each zone's window to have its `needs` (in fill order, as `leastOf` takes them), and
// only where that takes no part below its own need or below MIN_SHARE. {tree, rects, misfits}: the
// tree, its zones' rectangles in fill order as `zoneRects` lays them out, and the zones (by fill
// order) whose window still has less than it needs. `tree` is `root` itself when nothing moved.
//
// Split by split from the root down, each cut into whole pixels as `layoutRects` cuts it, and each
// part handed on at the length it now has. A split moves only when, cut as it is, a window in one
// of its parts would be left short (`leftShort`), and then every part gets at least its floor -- a
// length from which on what is inside it holds (`minExtent`). A split that cannot give every part
// its floor is left as it is, its parts are still fitted inside, and what stays short is said in
// `misfits`, judged on the final rectangles.
//
// Exact to the pixel, not to TOLERANCE: `inner` makes the box whole pixels, and `pixelLengths`
// gives every part whole pixels. A split that moves is given whole pixels by `spread` and written
// back as shares `100·P_i/L - 100·P_(i-1)/L`, P being the running position; `layoutRects`' running
// total of those shares is `100·P_i/L` within about 1e-13, and its rounding lands on P_i itself,
// with half a pixel to spare. `zoneRects` then takes off the whole half gaps `leastOf` counted, so
// a zone given room holds its window's need with no pixel missing, and often none to spare. A
// split that does not move keeps its shares, fractions or not, and gui/splits.py cuts by the same
// rule: the Tiling tab and the sandbox's oracle (`room` in scripts/tilecheck.py) draw a fitted
// layout on the same pixels.
export function fit(root, area, gaps, needs) {
    const box = inner(area, gaps);
    const least = leastOf(root, gaps, needs);
    let tree = null;
    function walk(node, path, w, h) {
        if (isZone(node)) {
            return;
        }
        const across = node.split === "h";
        const length = across ? w : h;
        const axis = across ? "width" : "height";
        const lengths = pixelLengths(node.sizes, length);
        const wanted = node.parts.map(function (part, i) {
            return minExtent(part, path.concat([i]), axis, least);
        });
        const short = node.parts.some(function (part, i) {
            return leftShort(part, path.concat([i]), axis, least, lengths[i]);
        });
        const next = short ? spread(lengths, wanted, Math.ceil(length * MIN_SHARE / 100)) : null;
        if (next) {
            tree = tree || copyTree(root);
            let at = 0;
            nodeAt(tree, path).sizes = next.map(function (d) {
                const before = at;
                at += d;
                return 100 * at / length - 100 * before / length;
            });
        }
        const used = next || lengths;
        for (let i = 0; i < node.parts.length; i++) {
            walk(node.parts[i], path.concat([i]), across ? used[i] : w, across ? h : used[i]);
        }
    }
    walk(root, [], box.width, box.height);
    const out = tree || root;
    const rects = zoneRects(out, area, gaps);
    const misfits = [];
    for (let k = 0; k < rects.length; k++) {
        if (!holds(rects[k], needs ? needs[k] : null)) {
            misfits.push(k);
        }
    }
    return {tree: out, rects: rects, misfits: misfits};
}

// When the dividers cannot make the room: windows traded between zones until each has what it
// needs, or no trade helps. `needs[k]` is what window k needs, window k being in zone k of the fill
// order to begin with; `movable[k]` says whether window k may change zones; `prefer` is the windows
// in the order they are tried in, which the engine gives newest first. Each window still short, in
// that order, is tried in each zone in fill order: the two windows trade places, the layout is
// fitted again, and the trade is kept only when both of them have what they need afterwards and
// no other window lost it. The windows left short are then strictly fewer, so this ends; after a
// trade the windows are tried again from the first. At most n * n fits in all, 81 for nine windows:
// the compositor runs this on its own thread.
//
// {order, fit}: `order[z]` is the window now in zone z, and `fit` is `fit` of the layout with them.
export function exchange(root, area, gaps, needs, movable, prefer) {
    let order = needs.map(function (need, k) { return k; });
    const needsIn = function (o) {
        return o.map(function (k) { return needs[k]; });
    };
    const shortIn = function (f, o) {
        return f.misfits.map(function (z) { return o[z]; });
    };
    let current = fit(root, area, gaps, needsIn(order));
    let budget = needs.length * needs.length;
    let traded = true;
    while (traded && current.misfits.length && budget > 0) {
        traded = false;
        const short = shortIn(current, order);
        for (let a = 0; a < prefer.length && !traded && budget > 0; a++) {
            const m = prefer[a];
            if (!movable[m] || short.indexOf(m) < 0) {
                continue;
            }
            const from = order.indexOf(m);
            for (let to = 0; to < order.length && !traded && budget > 0; to++) {
                const p = order[to];
                if (p === m || !movable[p]) {
                    continue;
                }
                budget -= 1;
                const trial = order.slice();
                trial[from] = p;
                trial[to] = m;
                const f = fit(root, area, gaps, needsIn(trial));
                const after = shortIn(f, trial);
                // m was short and is not now, so a set of short windows that holds no newcomer
                // is a strictly smaller one.
                if (after.indexOf(m) < 0 && after.indexOf(p) < 0
                        && after.every(function (k) { return short.indexOf(k) >= 0; })) {
                    order = trial;
                    current = f;
                    traded = true;
                }
            }
        }
    }
    return {order: order, fit: current};
}

// ------------------------------------------------------------------------- floating, and the selector

// A rectangle `fraction` of the area's size, centred on it, and never smaller than `least`
// ({width, height}, what the window needs) -- not even where that is more than the area holds.
export function centred(area, fraction, least) {
    const w = Math.max(Math.round(area.width * fraction), least ? least.width : 0);
    const h = Math.max(Math.round(area.height * fraction), least ? least.height : 0);
    return {x: Math.round(area.x + (area.width - w) / 2),
            y: Math.round(area.y + (area.height - h) / 2), width: w, height: h};
}

// A rectangle at the zone's corner, grown to what the window needs where the zone is smaller:
// the compositor does not hold a window to its minimum size, so the engine has to.
export function atLeast(rect, least) {
    return {x: rect.x, y: rect.y, width: Math.max(rect.width, least ? least.width : 0),
            height: Math.max(rect.height, least ? least.height : 0)};
}

// The selector's thumbnails, one for each of its entries -- the whole screen and the zone layouts
// a drag offers -- in a centred row at the top of the usable area, each in the screen's
// proportions. Smaller when the row would not fit.
export function thumbnails(area, count, aspect) {
    if (count <= 0 || area.width <= 0 || area.height <= 0) {
        return [];
    }
    const ratio = aspect > 0 ? aspect : 16 / 9;
    let h = Math.max(THUMB.least, Math.min(THUMB.height, Math.floor(area.height / 10)));
    let w = Math.round(h * ratio);
    const room = area.width - 2 * THUMB.margin - (count - 1) * THUMB.gap;
    if (count * w > room && room > 0) {
        w = Math.floor(room / count);
        h = Math.floor(w / ratio);
    }
    const total = count * w + (count - 1) * THUMB.gap;
    const x0 = Math.round(area.x + (area.width - total) / 2);
    const y0 = Math.round(area.y + THUMB.margin);
    const out = [];
    for (let i = 0; i < count; i++) {
        out.push({x: x0 + i * (w + THUMB.gap), y: y0, width: w, height: h});
    }
    return out;
}

// The rectangle around a row of thumbnails, padded by half the room between two: the band where
// the cursor is on the selector rather than on a zone.
export function band(thumbs) {
    if (!thumbs.length) {
        return null;
    }
    const pad = Math.ceil(THUMB.gap / 2);
    const first = thumbs[0];
    const last = thumbs[thumbs.length - 1];
    return {x: first.x - pad, y: first.y - pad, width: last.x + last.width - first.x + 2 * pad,
            height: first.height + 2 * pad};
}
