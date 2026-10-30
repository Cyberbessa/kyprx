// KyprX's name card on one screen: an arrangement's name when Next Layout or Previous Layout moves
// to it -- with automatic tiling off, the name of the zone layout they move to -- that Toggle
// Automatic Tiling switched automatic tiling on or off, and the desktop a window went to when every
// zone of its screen was taken.
//
// Nothing here decides anything: the engine says what the card shows (`env.announce`, through
// `announce` in main.qml), and this draws it and hides it again. One is made per screen by an
// Instantiator in main.qml, as the zone windows are, with their four flags (ZoneOverlay.qml says
// what each does). Measured in the sandbox's facts scenario, a window made that way appears where
// its x and y say -- here, in the middle of its screen -- reaches the compositor's scripts as an
// internal window (pid -1, no class), which the engine and the window watcher leave out, is on
// every desktop, and is at the top of `Workspace.stackingOrder`.
//
// It replaces plasmashell's on-screen display, which the script called over the bus before: that
// one was small, and KWin put it at two thirds of the screen's height. This one is centred on the
// screen it speaks for and sized by that screen's logical size: the name is 5 % of its height,
// from 28 to 96 pixels, a name too long for one line is given the room of two and shrinks until
// it fits there, never cut, and the card is at most 60 % of the screen's width.
//
// It fades in and out by the compositor's FadingPopups effect, which takes a `Qt.ToolTip` window
// for a popup, and not by an animation of the window's `opacity` here: each step of one is a
// warning in the compositor's log (read in Qt's source).
import QtQuick
import QtQuick.Window

Window {
    id: card

    // The screen it is shown on, from the Instantiator's model (Workspace.screens).
    property var output: null
    property bool shown: false
    // What it says: the name, a line under it, and for an arrangement or a zone layout the zones
    // of its layout as fractions of the preview, in fill order, the master first. Shown as text,
    // never as markup: a name is whatever the person typed.
    property string heading: ""
    property string caption: ""
    property var zones: []

    // Its proportions, from the screen's logical size.
    readonly property real screenWidth: output ? Math.max(1, output.geometry.width) : 1920
    readonly property real screenHeight: output ? Math.max(1, output.geometry.height) : 1080
    readonly property int nameSize: Math.max(28, Math.min(96, Math.round(screenHeight * 0.05)))
    readonly property int lineSize: Math.max(12, Math.round(nameSize * 0.38))
    readonly property int edge: Math.round(nameSize * 0.6)
    readonly property int widest: Math.max(1, Math.floor(screenWidth * 0.6) - 2 * edge)
    readonly property int previewHeight: zones.length ? 3 * nameSize : 0
    readonly property int previewWidth: zones.length
        ? Math.min(widest, Math.round(previewHeight * screenWidth / screenHeight)) : 0
    readonly property int zoneGap: Math.max(1, Math.round(nameSize / 24))
    // The name on one line when it fits; otherwise in the room of two lines, as large as fits
    // there (`Text.Fit`). Not with a limit of two lines: measured with Qt Quick 6.11, `Text.Fit`
    // then cut the name at its full size rather than shrink it.
    readonly property bool wraps: nameRun.advanceWidth > widest
    readonly property int nameWidth: Math.min(widest, Math.ceil(nameRun.advanceWidth))
    readonly property int nameHeight: Math.ceil(nameLine.height) * (wraps ? 2 : 1)
    readonly property int lineWidth: Math.min(widest, Math.ceil(lineRun.advanceWidth))
    readonly property int contentWidth: Math.max(1, previewWidth, nameWidth, lineWidth)
    // Where each part goes, worked out here rather than by a Column: a Column places its items at
    // the next polish, after the window is shown, and the card was measured to show first at a
    // height without its preview and then grow (tests/test_script_qml.py, offscreen).
    readonly property int gap: Math.round(edge / 2)
    readonly property int nameTop: edge + (zones.length ? previewHeight + gap : 0)
    readonly property int lineTop: nameTop + nameHeight + gap
    readonly property int fullHeight: edge + (caption !== ""
        ? lineTop + Math.ceil(lineText.implicitHeight) : nameTop + nameHeight)

    readonly property color tint: system.highlight

    function wash(alpha) {
        return Qt.rgba(tint.r, tint.g, tint.b, alpha);
    }

    // Shown for a moment, and again from the start when it is asked for while it shows.
    function announce(heading, caption, zones) {
        card.heading = String(heading || "");
        card.caption = String(caption || "");
        card.zones = zones || [];
        card.shown = true;
        hold.restart();
    }

    title: "KyprX name"
    flags: Qt.ToolTip | Qt.BypassWindowManagerHint | Qt.FramelessWindowHint
           | Qt.WindowTransparentForInput
    color: "transparent"
    visible: shown
    width: contentWidth + 2 * edge
    height: fullHeight
    x: output ? output.geometry.x + Math.round((output.geometry.width - width) / 2) : 0
    y: output ? output.geometry.y + Math.round((output.geometry.height - height) / 2) : 0

    SystemPalette {
        id: system
        colorGroup: SystemPalette.Active
    }

    TextMetrics {
        id: nameRun
        font.pixelSize: card.nameSize
        font.weight: Font.DemiBold
        text: card.heading
    }

    FontMetrics {
        id: nameLine
        font.pixelSize: card.nameSize
        font.weight: Font.DemiBold
    }

    TextMetrics {
        id: lineRun
        font.pixelSize: card.lineSize
        text: card.caption
    }

    Timer {
        id: hold
        interval: 1300
        repeat: false
        onTriggered: card.shown = false
    }

    Rectangle {
        anchors.fill: parent
        radius: Math.round(card.nameSize * 0.45)
        color: Qt.rgba(system.window.r, system.window.g, system.window.b, 0.92)
        border.width: 1
        border.color: Qt.rgba(system.windowText.r, system.windowText.g, system.windowText.b, 0.3)
    }

    Item {
        id: preview
        x: card.edge + Math.round((card.contentWidth - card.previewWidth) / 2)
        y: card.edge
        width: card.previewWidth
        height: card.previewHeight
        visible: card.zones.length > 0

        Repeater {
            model: card.zones

            Rectangle {
                required property var modelData
                required property int index

                // Each edge rounded where it falls, so that two neighbours share it.
                readonly property int x0: Math.round(modelData.x * preview.width)
                readonly property int y0: Math.round(modelData.y * preview.height)
                readonly property int x1: Math.round((modelData.x + modelData.width)
                                                     * preview.width)
                readonly property int y1: Math.round((modelData.y + modelData.height)
                                                     * preview.height)

                x: x0 + card.zoneGap
                y: y0 + card.zoneGap
                width: Math.max(1, x1 - x0 - 2 * card.zoneGap)
                height: Math.max(1, y1 - y0 - 2 * card.zoneGap)
                radius: card.zoneGap
                color: card.wash(index === 0 ? 0.55 : 0.25)
            }
        }
    }

    Text {
        objectName: "heading"
        x: card.edge
        y: card.nameTop
        width: card.contentWidth
        height: card.nameHeight
        text: card.heading
        textFormat: Text.PlainText
        font.pixelSize: card.nameSize
        font.weight: Font.DemiBold
        fontSizeMode: Text.Fit
        minimumPixelSize: Math.max(8, Math.round(card.nameSize / 4))
        wrapMode: Text.Wrap
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        color: system.windowText
    }

    Text {
        id: lineText
        objectName: "caption"
        x: card.edge
        y: card.lineTop
        width: card.contentWidth
        visible: card.caption !== ""
        text: card.caption
        textFormat: Text.PlainText
        font.pixelSize: card.lineSize
        wrapMode: Text.Wrap
        horizontalAlignment: Text.AlignHCenter
        // The text colour thinned to 175 of 255, as the settings window's Hint mark is: the
        // measured reason, and what it keeps readable, are at `Hint` in gui/widgets.py.
        color: Qt.rgba(system.windowText.r, system.windowText.g, system.windowText.b, 175 / 255)
    }
}
