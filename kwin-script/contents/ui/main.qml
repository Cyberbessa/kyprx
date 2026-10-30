// KyprX's compositor script: its window watcher, its keys and its tiling engine.
//
// KWin loads this file (a `declarativescript` package, `metadata.json`) and keeps one QML engine
// for it for the whole session. The work is in the modules under `../code/`, which this file hands
// everything they may touch in one object (`env`), because a module sees `Qt`, `console` and
// `print` but not `Workspace`, `Options` or `KWin` (measured in a nested KWin 6.7.5).
//
// Four things the shape of this script hides, the first three about the watcher:
//
// 1. At `windowAdded` the window's class is sometimes not the final one, and its decoration may
//    not exist yet. So that message is a trigger, not the truth: the daemon lets things settle
//    and then asks for a full inventory, and the tiling reads the window's rules again on
//    `windowClassChanged` and `captionChanged`.
// 2. A compositor script has timers. This one is declarative, with QML's `Timer` and
//    `Qt.callLater`, and both ran in a nested KWin 6.7.5, where three `Qt.callLater` calls of one
//    function in one turn ran it once (measured); a plain-JavaScript script is handed a `QTimer`
//    (read in KWin's source, not measured). So `windowClassChanged` is listened to for what it
//    says -- the real name has arrived -- and not as a stand-in for "tell me again later".
// 3. **The inventory lives here, and the daemon asks for it through a shortcut.** That is not the
//    obvious design, and the obvious one was measured to be broken: a second script the daemon
//    loaded, ran and unloaded on demand, addressed by the id `loadScript` returns. The compositor
//    numbers scripts with the size of its own list, so those ids are **reused after any unload**:
//    the new script's object path is already taken by a live one, registering it fails, and
//    `run()` lands on somebody else's script. No error is raised anywhere. Measured: the daemon
//    sat there having run the tiling script instead, its window list frozen at one entry, and the
//    interface showed a single row. A shortcut is addressed by name, so it cannot be confused with
//    anything; `KyprXTiling` reaches the tiling engine the same way.
// 4. KyprX's keys are registered here, a `ShortcutHandler` each, for a related reason: registered
//    from the daemon a key was accepted by the shortcut registry and never grabbed by the
//    compositor -- twice, once as a component of the app's own and once as a desktop entry. An
//    action registered from inside a compositor script lands in the registry's `kwin` component
//    and its key works. A default key applies only until the registry holds one for the action; a
//    key set on the Shortcuts tab stays across a reload of this script (measured), and an action
//    this script no longer registers stays in the registry, doing nothing.
//
// And four about the script as a whole:
//
// - **A change to these files reaches the compositor at the next login, not before.** Edited at
//   the same path, `main.qml` and the modules stay the old ones after `unloadScript` and a
//   reconfigure, for the rest of the session; only a folder never loaded before loads fresh, and
//   neither a `?v=` query nor a dynamic `import()` is accepted (all measured). So the daemon holds
//   the version this script says it is (`scriptVersion`, which `Tiling()` is told and which has to
//   equal `KPlugin.Version` in metadata.json) against the version installed, and when they differ
//   KyprX says to log out and back in (the `old-script` state in daemon/tiling.py).
// - **The zone overlays and the name cards are top-level windows**, one of each per screen from
//   the Instantiators below: a Window declared inside this Item never became visible (measured).
//   See ZoneOverlay.qml and NameWindow.qml.
// - **The names shown on screen are KyprX's own card** (NameWindow.qml), and not plasmashell's
//   on-screen display, which this script called over the bus before: that one was small, and KWin
//   put it at two thirds of the screen's height; the card is centred on the screen it speaks for
//   and sized by it. It says an arrangement's name when the layout keys move to it -- with
//   automatic tiling off, the name of the zone layout they move to -- that Toggle Automatic Tiling
//   switched automatic tiling on or off, and where a window went when every zone of its screen
//   was taken.
// - **Component.onDestruction runs** when the script is unloaded, and a call made there still
//   arrives (measured): the engine gives back the screen edges and the keep-above it set there.
import QtQuick
import org.kde.kwin
import "../code/engine.mjs" as Engine
import "../code/watcher.mjs" as Watcher

Item {
    id: root

    // SCRIPT_VERSION: what this script says it is when it asks for the tiling settings. It has to
    // equal `KPlugin.Version` in ../../metadata.json (tests/test_script_contract.py).
    readonly property string scriptVersion: "0.7"

    property var env: null
    property var engine: null
    property var watcher: null

    function log(text) {
        console.log("KyprX: " + text);
    }

    // One instance per method, each reused: a DBusCall takes its arguments at the moment of
    // `call()`, so setting them first and calling again delivers each call's own (measured, three
    // calls in a row on one instance).
    function report(reason, json) {
        reportCall.arguments = [String(reason), String(json)];
        reportCall.call();
    }

    function pull() {
        tilingCall.call();
    }

    function overlays() {
        const out = [];
        for (let i = 0; i < overlayWindows.count; i++) {
            const overlay = overlayWindows.objectAt(i);
            if (overlay) {
                out.push(overlay);
            }
        }
        return out;
    }

    // What the engine has a name card say, `{output, heading, caption, zones}`, on the screen it
    // names; the card shows it for a moment (NameWindow.qml). Answers the card, or null when no
    // screen has that name.
    function announce(payload) {
        for (let i = 0; payload && i < nameWindows.count; i++) {
            const card = nameWindows.objectAt(i);
            if (card && card.output && String(card.output.name) === String(payload.output)) {
                card.announce(payload.heading, payload.caption, payload.zones);
                return card;
            }
        }
        return null;
    }

    function act(name) {
        if (root.engine) {
            root.engine.action(name);
        }
    }

    // Toggle Automatic Tiling, as the engine asks for it (`toggleAuto` in engine.mjs): the daemon
    // writes the setting the other way and tells the tiling, whose next answer switches it.
    function toggleAutomaticTiling() {
        toggleCall.call();
    }

    DBusCall {
        id: reportCall
        service: "org.cyberbessa.KyprX"
        path: "/Windows"
        dbusInterface: "org.cyberbessa.KyprX.Windows"
        method: "Report"
    }

    // The tiling settings. `finished` carries the answer as the first element of its list;
    // `failed` carries nothing (a daemon that is not running, a method it does not have, the wrong
    // arguments -- measured), and then nothing changes: before any answer the engine places
    // nothing, and an answer already acted on stays in force.
    DBusCall {
        id: tilingCall
        service: "org.cyberbessa.KyprX"
        path: "/Windows"
        dbusInterface: "org.cyberbessa.KyprX.Windows"
        method: "Tiling"
        arguments: [root.scriptVersion]
        onFinished: function (returnValue) {
            if (root.engine && returnValue && returnValue.length) {
                root.engine.answer(String(returnValue[0]));
            }
        }
        onFailed: function () {
            root.log("could not ask the daemon for the tiling settings");
        }
    }

    DBusCall {
        id: cheatsheetCall
        service: "org.cyberbessa.KyprX"
        path: "/Windows"
        dbusInterface: "org.cyberbessa.KyprX.Windows"
        method: "ShowCheatsheet"
    }

    DBusCall {
        id: wallpaperCall
        service: "org.cyberbessa.KyprX"
        path: "/Windows"
        dbusInterface: "org.cyberbessa.KyprX.Windows"
        method: "ShowWallpaper"
    }

    DBusCall {
        id: settingsCall
        service: "org.cyberbessa.KyprX"
        path: "/Windows"
        dbusInterface: "org.cyberbessa.KyprX.Windows"
        method: "ShowSettings"
    }

    // Its answer, "ok" or "error: ..." with the reason, is not read: a key the daemon refuses --
    // KyprX's tiling not running, KyprX off the desk -- changes nothing, and the daemon's log says
    // why.
    DBusCall {
        id: toggleCall
        service: "org.cyberbessa.KyprX"
        path: "/Windows"
        dbusInterface: "org.cyberbessa.KyprX.Windows"
        method: "ToggleAutomaticTiling"
        onFailed: function () {
            root.log("could not ask the daemon to switch automatic tiling");
        }
    }

    // While an edge is dragged, the neighbours follow at most every 33 ms.
    Timer {
        id: liveTimer
        interval: 33
        repeat: false
        onTriggered: {
            if (root.engine) {
                root.engine.liveTick();
            }
        }
    }

    // How long the end of a resize waits for the window's last size before it is judged.
    Timer {
        id: commitTimer
        interval: 300
        repeat: false
        onTriggered: {
            if (root.engine) {
                root.engine.commitTick();
            }
        }
    }

    // How long the zones manual tiling's layout keys show stay on the screen: as long as the name
    // card that says their name (NameWindow.qml).
    Timer {
        id: previewTimer
        interval: 1300
        repeat: false
        onTriggered: {
            if (root.engine) {
                root.engine.previewTick();
            }
        }
    }

    // How long a desktop KyprX made waits, empty and not shown, before the engine removes it.
    // The engine starts it again at every window that closes or changes desktops and every switch
    // of desktop or activity, so a desktop the person only passes through is left alone.
    Timer {
        id: cleanupTimer
        interval: 3000
        repeat: false
        onTriggered: {
            if (root.engine) {
                root.engine.cleanupTick();
            }
        }
    }

    // How long a tiled window must stay still, after something other than KyprX moved or resized
    // it, before the engine looks at it again: one whole turn of this timer with no change, so
    // between one and two turns after its last change (engine.mjs, `reassert`). An estimate, not a
    // measurement: longer than the gaps inside an application's burst of moves, short enough that
    // a window out of its zone is put back before it is in the way.
    Timer {
        id: quietTimer
        interval: 250
        repeat: false
        onTriggered: {
            if (root.engine) {
                root.engine.quietTick();
            }
        }
    }

    // One zone window per screen. Each takes its screen by the delegate's `index` from the same
    // list, which is how the spike's overlays were made and shown.
    Instantiator {
        id: overlayWindows
        model: Workspace.screens
        delegate: ZoneOverlay {
            output: Workspace.screens[index]
        }
    }

    // And one name card per screen, made the same way.
    Instantiator {
        id: nameWindows
        model: Workspace.screens
        delegate: NameWindow {
            output: Workspace.screens[index]
        }
    }

    Connections {
        target: Workspace

        function onWindowAdded(window) {
            if (root.watcher) {
                root.watcher.added(window);
            }
            if (root.engine) {
                root.engine.windowAdded(window);
            }
        }

        function onWindowRemoved(window) {
            if (root.engine) {
                root.engine.windowRemoved(window);
            }
            if (root.watcher) {
                root.watcher.removed(window);
            }
        }

        function onWindowActivated(window) {
            if (root.engine) {
                root.engine.windowActivated(window);
            }
        }

        function onCurrentDesktopChanged() {
            if (root.engine) {
                root.engine.desktopsChanged();
            }
        }

        function onDesktopsChanged() {
            if (root.engine) {
                root.engine.desktopsChanged();
            }
        }

        // Each activity has surfaces of its own (engine.mjs). A window moved to another activity
        // says so itself, with its own `activitiesChanged`.
        function onCurrentActivityChanged() {
            if (root.engine) {
                root.engine.activityChanged();
            }
        }

        function onScreensChanged() {
            if (root.engine) {
                root.engine.screensChanged();
            }
        }

        function onVirtualScreenGeometryChanged() {
            if (root.engine) {
                root.engine.screensChanged();
            }
        }
    }

    Connections {
        target: Options

        function onConfigChanged() {
            if (root.engine) {
                root.engine.optionsChanged();
            }
        }
    }

    // ---------------------------------------------------------------- the actions
    //
    // Names, texts and default keys exactly as daemon/shortcuts.py has them (`ACTION_TEXTS`,
    // `ACTION_DEFAULTS`, over `SCRIPT_ACTIONS`); tests/test_script_contract.py holds the two to
    // each other. The first two have no key: nobody presses them, and the daemon fires them by
    // name with `invokeShortcut` -- an action with no key fires that way (measured).

    ShortcutHandler {
        name: "KyprXInventory"
        text: "KyprX: re-read the window list"
        sequence: ""
        // The daemon asks for the window list when it starts, so this is also how it hears this
        // script's version right after it comes up, and stops saying no script has asked.
        onActivated: {
            if (root.watcher) {
                root.watcher.inventory();
            }
            root.pull();
        }
    }

    ShortcutHandler {
        name: "KyprXTiling"
        text: "KyprX: re-read the tiling settings"
        sequence: ""
        onActivated: root.pull()
    }

    ShortcutHandler {
        name: "KyprXCheatsheet"
        text: "KyprX: shortcut cheatsheet"
        sequence: "Meta+/"
        onActivated: cheatsheetCall.call()
    }

    // Meta+R is what end-4/dots-hyprland binds its own wallpaper selector to. Spectacle's region
    // recording registers it as well, and the daemon takes a key back from any other action while
    // one of these three -- or Toggle Automatic Tiling, below -- holds it (claim_kyprx_keys in
    // daemon/kyprd_shortcuts.py says why).
    ShortcutHandler {
        name: "KyprXWallpaper"
        text: "KyprX: wallpaper picker"
        sequence: "Meta+R"
        onActivated: wallpaperCall.call()
    }

    ShortcutHandler {
        name: "KyprXSettings"
        text: "KyprX: settings"
        sequence: "Meta+K"
        onActivated: settingsCall.call()
    }

    ShortcutHandler {
        name: "KyprXFocusLeft"
        text: "KyprX: Focus Left"
        sequence: "Meta+Ctrl+H"
        onActivated: root.act("KyprXFocusLeft")
    }

    ShortcutHandler {
        name: "KyprXFocusDown"
        text: "KyprX: Focus Down"
        sequence: "Meta+Ctrl+J"
        onActivated: root.act("KyprXFocusDown")
    }

    ShortcutHandler {
        name: "KyprXFocusUp"
        text: "KyprX: Focus Up"
        sequence: "Meta+Ctrl+K"
        onActivated: root.act("KyprXFocusUp")
    }

    ShortcutHandler {
        name: "KyprXFocusRight"
        text: "KyprX: Focus Right"
        sequence: "Meta+Ctrl+L"
        onActivated: root.act("KyprXFocusRight")
    }

    ShortcutHandler {
        name: "KyprXMoveLeft"
        text: "KyprX: Move Left"
        sequence: "Meta+Shift+H"
        onActivated: root.act("KyprXMoveLeft")
    }

    ShortcutHandler {
        name: "KyprXMoveDown"
        text: "KyprX: Move Down"
        sequence: "Meta+Shift+J"
        onActivated: root.act("KyprXMoveDown")
    }

    ShortcutHandler {
        name: "KyprXMoveUp"
        text: "KyprX: Move Up"
        sequence: "Meta+Shift+K"
        onActivated: root.act("KyprXMoveUp")
    }

    ShortcutHandler {
        name: "KyprXMoveRight"
        text: "KyprX: Move Right"
        sequence: "Meta+Shift+L"
        onActivated: root.act("KyprXMoveRight")
    }

    ShortcutHandler {
        name: "KyprXShrinkWidth"
        text: "KyprX: Shrink Width"
        sequence: "Meta+Ctrl+Shift+H"
        onActivated: root.act("KyprXShrinkWidth")
    }

    ShortcutHandler {
        name: "KyprXGrowHeight"
        text: "KyprX: Grow Height"
        sequence: "Meta+Ctrl+Shift+J"
        onActivated: root.act("KyprXGrowHeight")
    }

    ShortcutHandler {
        name: "KyprXShrinkHeight"
        text: "KyprX: Shrink Height"
        sequence: "Meta+Ctrl+Shift+K"
        onActivated: root.act("KyprXShrinkHeight")
    }

    ShortcutHandler {
        name: "KyprXGrowWidth"
        text: "KyprX: Grow Width"
        sequence: "Meta+Ctrl+Shift+L"
        onActivated: root.act("KyprXGrowWidth")
    }

    ShortcutHandler {
        name: "KyprXToggleFloat"
        text: "KyprX: Toggle Float"
        sequence: "Meta+F"
        onActivated: root.act("KyprXToggleFloat")
    }

    ShortcutHandler {
        name: "KyprXSetMaster"
        text: "KyprX: Set Master"
        sequence: "Meta+Return"
        onActivated: root.act("KyprXSetMaster")
    }

    ShortcutHandler {
        name: "KyprXRotate"
        text: "KyprX: Rotate"
        sequence: "Meta+O"
        onActivated: root.act("KyprXRotate")
    }

    ShortcutHandler {
        name: "KyprXRotateBack"
        text: "KyprX: Rotate Back"
        sequence: "Meta+Shift+O"
        onActivated: root.act("KyprXRotateBack")
    }

    // Through the engine, which asks the daemon to write the setting (`toggleAuto` in engine.mjs),
    // and so only while the engine tiles. Meta+T is KWin's own Edit Tiles on a stock desk, and the
    // daemon takes it back from that action at every start (claim_kyprx_keys).
    ShortcutHandler {
        name: "KyprXToggleAutomaticTiling"
        text: "KyprX: Toggle Automatic Tiling"
        sequence: "Meta+T"
        onActivated: root.act("KyprXToggleAutomaticTiling")
    }

    ShortcutHandler {
        name: "KyprXNextLayout"
        text: "KyprX: Next Layout"
        sequence: "Meta+\\"
        onActivated: root.act("KyprXNextLayout")
    }

    ShortcutHandler {
        name: "KyprXPreviousLayout"
        text: "KyprX: Previous Layout"
        sequence: "Meta+|"
        onActivated: root.act("KyprXPreviousLayout")
    }

    Component.onCompleted: {
        root.env = {
            Workspace: Workspace,
            Options: Options,
            KWin: KWin,
            owner: root,
            rect: Qt.rect,
            later: Qt.callLater,
            now: function () { return Date.now(); },
            report: root.report,
            announce: root.announce,
            toggleAutomaticTiling: root.toggleAutomaticTiling,
            log: root.log,
            overlays: root.overlays,
            timers: {live: liveTimer, commit: commitTimer, preview: previewTimer,
                     cleanup: cleanupTimer, quiet: quietTimer},
        };
        root.watcher = Watcher.create(root.env);
        root.engine = Engine.create(root.env);
        root.engine.start();
        // Whatever was already open when the script came up. This is also what starts the daemon
        // at login: a call to a bus name nobody holds starts the service that owns it.
        root.watcher.inventory();
        root.pull();
    }

    Component.onDestruction: {
        if (root.watcher) {
            root.watcher.dispose();
        }
        if (root.engine) {
            root.engine.dispose();
        }
    }
}
