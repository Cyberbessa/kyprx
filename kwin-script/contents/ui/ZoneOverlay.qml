// One screen's zones, and the selector of zone layouts with the name of one under it, drawn while
// a window is dragged -- or, with the cursor at the top edge, the area a window let go there is
// maximized to, as one zone named Maximize; and, for a moment, the zones manual tiling's layout
// keys move a screen to.
//
// Nothing here decides anything: drag.mjs sets every property below, in this window's own
// coordinates, and this only draws them. One is made per screen by the Instantiator in main.qml,
// which is what makes it a top-level window; declared inside the script's root Item, a Window never
// became visible (measured in a nested KWin 6.7.5).
//
// The flags make it something no window manager rule, effect or click treats as a window:
// `Qt.ToolTip` keeps the Scale effect from animating it in -- with it only FadingPopups fades it,
// without it Scale ran on every show (measured) -- `BypassWindowManagerHint` and
// `FramelessWindowHint` keep the compositor from deciding where it goes or framing it, and
// `WindowTransparentForInput` lets every click and every hover through to the windows under it,
// which is why the cursor is hit-tested in JavaScript rather than here. Shown, it took no focus
// from the active window (measured). It reaches the compositor's scripts as an internal window
// (pid -1, no class), which the engine and the window watcher leave out.
import QtQuick
import QtQuick.Window

Window {
    id: overlay

    // The output this window covers, from the Instantiator's model (Workspace.screens).
    property var output: null
    property bool shown: false
    // The zones of the zone layout a drag offers on this screen, and the one under the cursor.
    property var zones: []
    property int hovered: -1
    // The selector, on the screen under the cursor only: a thumbnail for the whole screen and for
    // each zone layout a drag offers, each with its own zones; the one under the cursor, and the
    // one whose zones are shown.
    property var thumbs: []
    property int hoveredThumb: -1
    property int currentThumb: -1
    // The name of the zone layout whose zones are shown -- the one under the cursor, when it is on
    // a thumbnail -- under the selector's row; at the top edge, "Maximize", there or, with no row,
    // at the top of the area. Shown as text, never as markup: a name is whatever the person typed.
    property string label: ""

    readonly property color tint: system.highlight

    function wash(alpha) {
        return Qt.rgba(tint.r, tint.g, tint.b, alpha);
    }

    title: "KyprX zones"
    flags: Qt.ToolTip | Qt.BypassWindowManagerHint | Qt.FramelessWindowHint
           | Qt.WindowTransparentForInput
    color: "transparent"
    visible: shown
    x: output ? output.geometry.x : 0
    y: output ? output.geometry.y : 0
    width: output ? Math.max(1, output.geometry.width) : 1
    height: output ? Math.max(1, output.geometry.height) : 1

    SystemPalette {
        id: system
        colorGroup: SystemPalette.Active
    }

    Repeater {
        model: overlay.zones

        Rectangle {
            required property var modelData
            required property int index

            x: modelData.x
            y: modelData.y
            width: modelData.width
            height: modelData.height
            radius: 10
            color: overlay.wash(index === overlay.hovered ? 0.35 : 0.08)
            border.width: 2
            border.color: overlay.wash(index === overlay.hovered ? 0.95 : 0.45)
        }
    }

    Repeater {
        model: overlay.thumbs

        Rectangle {
            id: thumb

            required property var modelData
            required property int index

            x: modelData.x
            y: modelData.y
            width: modelData.width
            height: modelData.height
            radius: 6
            color: Qt.rgba(system.window.r, system.window.g, system.window.b, 0.9)
            border.width: index === overlay.hoveredThumb ? 3 : 1
            border.color: index === overlay.hoveredThumb ? overlay.tint
                          : Qt.rgba(system.windowText.r, system.windowText.g,
                                    system.windowText.b, 0.3)

            Repeater {
                model: thumb.modelData.zones

                Rectangle {
                    required property var modelData

                    x: modelData.x
                    y: modelData.y
                    width: modelData.width
                    height: modelData.height
                    radius: 2
                    color: overlay.wash(thumb.index === overlay.currentThumb ? 0.55 : 0.25)
                }
            }
        }
    }

    // The name, on a plate of the thumbnails' own colours, centred under their row. With no row --
    // the top edge of a drag that shows no selector: a tiled window's with automatic tiling, a
    // window the tiling never takes, a screen kept out of the tiling -- at the top of the zone
    // under the cursor, which is then the area the window would be maximized to, centred on it.
    Rectangle {
        id: plate

        // The row as one rectangle, from both its ends in one binding: read through two
        // properties, one end was seen to change before the other and a binding read the other
        // as null (tests/test_script_qml.py, offscreen).
        readonly property var row: {
            const list = overlay.thumbs;
            if (!list.length) {
                return null;
            }
            const first = list[0];
            const last = list[list.length - 1];
            return {x: first.x, y: first.y, width: last.x + last.width - first.x,
                    height: first.height};
        }
        // The zone under the cursor, from the list and the index in one binding, the index held
        // to the list: drag.mjs sets the two one after the other (`draw`).
        readonly property var spot: {
            const list = overlay.zones;
            const i = overlay.hovered;
            return i >= 0 && i < list.length ? list[i] : null;
        }
        readonly property int pad: Math.round(labelText.font.pixelSize * 0.6)

        visible: overlay.label !== "" && (row !== null || spot !== null)
        x: row ? Math.round(row.x + (row.width - width) / 2)
           : spot ? Math.round(spot.x + (spot.width - width) / 2) : 0
        y: row ? row.y + row.height + Math.round(pad / 2) : spot ? spot.y + 2 * pad : 0
        width: Math.ceil(labelText.implicitWidth) + 2 * pad
        height: Math.ceil(labelText.implicitHeight) + pad
        radius: 6
        color: Qt.rgba(system.window.r, system.window.g, system.window.b, 0.9)
        border.width: 1
        border.color: Qt.rgba(system.windowText.r, system.windowText.g, system.windowText.b, 0.3)

        Text {
            id: labelText
            objectName: "label"
            anchors.centerIn: parent
            text: overlay.label
            textFormat: Text.PlainText
            // A fifth of a thumbnail's height: 14 px beside the tallest, never below 12.
            font.pixelSize: Math.max(12, Math.round((plate.row ? plate.row.height : 72) / 5))
            font.weight: Font.DemiBold
            color: system.windowText
        }
    }
}
