"""Every value KyprX has an opinion about, declared once.

This is the app's taste, written down. It exists because the interface stopped asking: a setting
that would have the same answer every time is not a question, it is a default, and a default with
nowhere to live ends up duplicated between the control that set it and the code that assumed it.

Three rules govern what may go in here.

**Values only, never absences.** Every entry says "this key should read like this". Nothing here
can say "this key should not be in the file" -- taking a key away is a one-off pass in
`migrate.py`, gated on a version, not a standing opinion. The reason is that the files are shared:
a key this app did not write belongs to whoever did.

`BUTTON_COLOURS` is the one exception, and it is an exception because there "nothing" is a value
the decoration reads rather than the absence of one. A button-colour slot is an **override**: with
no entry the decoration picks the colour, which is a state, and it is the state this app wants for
every slot. Removal is already how that is expressed everywhere else in the code -- see
`klassy.set_button_colours`, which deletes rather than writing an empty value, because the
decoration treats any non-empty value as "there is an override here".

**No lists.** `floatingClass`, `ExcludedWindowClasses` and the blur effect's `WindowClasses` are
per-window surfaces, edited a row at a time on the Windows tab. A default for one of them would
be this file deciding what happens to somebody's window.

**What is declared is not the same as what is enforced.** `SETTINGS` is the whole opinion, and it
is what *Restore defaults* writes. `ENFORCED` is the much smaller part that a tab writes on Apply
-- exactly the settings that left the interface, and nothing that is still on screen. Enforcing a
control that is still visible would mean an Apply putting back the value somebody had just
changed on another row of the same form.

The title bar is the exception the other way round. Every one of its keys left the interface,
and none of them is enforced by any tab: they left it for the decoration's own dialog, which is
where they are meant to be changed, and an Apply on the Appearance tab putting them back would
undo exactly that. *Restore defaults* is the one thing that writes them.
"""

from __future__ import annotations

#: Bumped when the declarations below change in a way somebody would want to know about. It is
#: shown beside the *Restore defaults* button, so "the defaults" is a thing with a version rather
#: than whatever the app happened to think this week.
#:
#: 5: the title bar's four opacity keys under the names the decoration actually reads -- see
#: `TitleBarOpacity` below. The values are the ones version 4 meant; only now do they arrive.
#: 6: Longive as default theme, corner radius 7.5, and image wallpaper directory support.
#: 7: the strip layout without the file names and the switch that leaves KDE's own wallpapers out
#: of the picker's list (`kde_wallpapers` below). The id `strip` builds the strip without the
#: names from this version on -- the owner's word for the strip -- so a settings file from an
#: earlier version that says `strip` opens it without them; the strip with the names is
#: `strip-names`. Nothing is migrated. The picker's default layout is `pages`.
VERSION = 7

#: What a window gets the first time it is seen. `state.Defaults` and `policy.Switches` both take
#: their field values from here, so there is one place to change and no pair to keep in step.
#:
#: Float and "animate" are deliberately **not** here. Both are membership in a list that is global
#: to the compositor, not a property of a window, and applying them per window would put a write
#: to `[Script-krohnkite]` -- which restarts the tiler and re-tiles the screen -- inside the batch
#: that runs at login. See `apply_defaults` in `daemon/kyprd_windows.py`.
SWITCHES = {
    "titlebar": False,       # False means hidden, which is the whole point of the app
    "outline": True,
    "transparency": True,
    "blur": True,
}

#: How see-through a window is when its Transparency is ticked and it has no number of its own, as
#: the compositor counts it: a percentage, 100 being opaque.
#:
#: Ninety-two, and the number is not a taste picked here. It is what a rule written by hand on this
#: desk was already doing to every window, so the day this column arrived nothing looked different
#: — which is the only defensible starting value for a setting that takes over something somebody
#: had already arranged for themselves.
#:
#: It sits here rather than in `SETTINGS` below because it is not a key in anybody's config file:
#: it is a number this app writes into a window rule, one window at a time, and the one place it
#: is kept is `state.Config`.
TRANSPARENCY = 92

#: The rest of this app's own settings -- the ones in `~/.local/state/kyprx/config.json` rather
#: than in somebody else's config file. `TRANSPARENCY` above is the fourth and is not repeated
#: here, because it is a number the rest of the code asks for by that name.
#:
#: They are declared for one reason: *Restore defaults* writes them. Every one has a control on
#: screen and every one is an opinion -- new windows are adjusted, the app speaks up when
#: something failed, and the wallpaper does not choose the colour until somebody asks it to.
#:
#: `cheatsheet_keys` is deliberately absent, and the absence is the decision rather than an
#: oversight. Which of an action's several combinations the card prints is a choice made on the
#: Shortcuts tab, and *Restore defaults* says in as many words that it does not touch shortcuts.
#: Nothing here would rebind one -- but a button that quietly changed what the card shows would be
#: reading that promise the other way round from the person who read it.
OWN = {"paused": False, "notify": True, "auto_colour": False}

#: The wallpaper picker's choices. Declared here rather than spelled out in `state.py` so that
#: there is one place to read them from: `state.Config.load` takes the layout from here, and
#: `state.wallpaper_layout` falls back on this for any name that is not one of
#: `state.WALLPAPER_LAYOUTS`.
#:
#: The folders are emptied rather than remembered, and that loses nothing: the Wallpaper tab works
#: one out from the machine when there is none -- so restoring it to nothing is restoring it to
#: "ask the machine again".
#:
#: `kde_wallpapers` is whether the picker also lists the wallpapers the desktop itself ships -- the
#: `wallpapers/` and `backgrounds/` folders of the system's data directories. On, which is what
#: every install had before the switch existed, and so the default; off, the list is the chosen
#: pictures folder's alone, unless that folder renders nothing, where the system's wallpapers come
#: back with a note saying why (an empty picker says nothing to anybody).
WALLPAPER = {"video_dir": "", "image_dir": "", "layout": "pages", "kde_wallpapers": True}

#: The colours. Longive for dark, and no colour of your own and nothing soaking in.
COLOURS = {"mode": "dark", "preset": "longive", "accent": "", "tint": 0.0}


#: The decoration keeps every button-behaviour setting twice, once for the active window and once
#: for the inactive one. They are the same here, so the grid is written once and twinned.
def _both(**row) -> dict:
    return {f"{name}{state}": value
            for name, value in row.items() for state in ("Active", "Inactive")}


#: The button-behaviour grid, laid out the way the decoration's own dialog lays it out: three
#: states down, and icon / background / outline across, once for the ordinary buttons and once for
#: close.
#:
#: **The outlines are on under the pointer, and that is a correction.** They were declared off
#: here, with a measurement beside them: with a full-height shape, an outline about to be drawn
#: makes the decoration pull the button's background in by about 1.5 px on every side, and the gap
#: that opens at the bottom is a thin dark line under the button.
#:
#: That measurement was real and the conclusion drawn from it was wrong. The dark line's cause was
#: this app writing `UseTitleBarColorForAllBorders=false` -- see the commit that renamed the app,
#: which fixed it and said the outline workaround should go with it. The workaround did not go: it
#: was read back off the interface and declared here as a default, outliving by two releases the
#: defect it was patching.
#:
#: And on its own it caused a different one. With nothing stroking the button's edge, the seam
#: where the button's background meets the window's rounded corner had nothing over it, and it
#: showed as a hole -- one pixel, 35 % transparent, three pixels in from the edge at the top of a
#: hovered close button. Ticking the hover and press outlines back on closes it. Measured on the
#: screen, which is the only place it could be.
#:
#: The lesson is the one in AGENTS.md read backwards. It warns that a workaround without its reason
#: gets simplified back into the bug; this was a workaround that outlived its reason and became a
#: bug of its own.
_BUTTON_BEHAVIOUR = {
    # Icons: always drawn, in all three states.
    **_both(ShowIconNormally="true", ShowIconOnHover="true", ShowIconOnPress="true"),
    **_both(ShowCloseIconNormally="true", ShowCloseIconOnHover="true",
            ShowCloseIconOnPress="true"),
    # Backgrounds: nothing at rest, filled under the pointer and while held.
    **_both(ShowBackgroundNormally="false", ShowBackgroundOnHover="true",
            ShowBackgroundOnPress="true"),
    **_both(ShowCloseBackgroundNormally="false", ShowCloseBackgroundOnHover="true",
            ShowCloseBackgroundOnPress="true"),
    # Outlines: the same three states as the backgrounds. See above for why this matters.
    **_both(ShowOutlineNormally="false", ShowOutlineOnHover="true", ShowOutlineOnPress="true"),
    **_both(ShowCloseOutlineNormally="false", ShowCloseOutlineOnHover="true",
            ShowCloseOutlineOnPress="true"),
    # How each one fades as the state changes. The close button's background is the one that goes
    # the other way, thinning out rather than filling in.
    **_both(VaryColorIcon="No", VaryColorCloseIcon="No"),
    **_both(VaryColorBackground="Opaque", VaryColorOutline="Opaque"),
    **_both(VaryColorCloseBackground="Transparent", VaryColorCloseOutline="Opaque"),
    **_both(ButtonStateChecked="Press"),
    "UnisonHovering": "false",
}

#: Not declared, on purpose: `LockButtonBehaviourActiveInactive`, `LockCloseButtonBehaviourActive`
#: and `LockCloseButtonBehaviourInactive`. Those are the padlocks in the decoration's own dialog,
#: which keep its active and inactive tabs in step **while somebody is editing them**. They are
#: that dialog's own state and they change nothing about how a window is drawn, so they are not
#: this app's to have an opinion about.


#: The whole opinion, in the vocabulary the interface already speaks: source, then group (empty
#: for the sources that are one flat group), then key. Written by *Restore defaults*.
SETTINGS: dict[str, dict[str, dict[str, object]]] = {
    "klassy": {
        "Windeco": {
            #: A **static** style on purpose. The four Dynamic ones choose their minimise glyph
            #: when they paint, from which screen edge the panel is on -- measured with the
            #: decoration's own icon generator: KiteDynamic and KisweetDynamic exported different
            #: icons from their static twins with the panel where it was -- so a default naming
            #: one would look different from desk to desk. Material against MaterialCentered is
            #: one glyph too: Material's minimise bar sits on the maximise square's baseline,
            #: MaterialCentered's runs through the middle.
            "ButtonIconStyle": "StyleMaterial",
            #: The shape every measurement in `_BUTTON_BEHAVIOUR` was made on -- the pulled-in
            #: background, the hole at the corner -- so it is the shape those values are known
            #: to be right for.
            "ButtonShape": "ShapeFullHeightRectangle",
            #: Mirrored into the blur effect's own radius by the Appearance tab, which is the one
            #: place it is set. The two are declared equal so a restore leaves them agreeing.
            "WindowCornerRadius": "7.5",
            #: The title bar wears the theme's colour, not the application's. An application that
            #: paints its own header colour makes every window a different colour, which is the
            #: opposite of what a tiled screen wants.
            "MatchTitleBarToApplicationColor": "false",
            #: No rule under the bar. The theme ships this ON, so leaving the key out is not the
            #: same as turning it off.
            "DrawTitleBarSeparator": "false",
            #: The title itself: plain. The decoration ships it bold, and plain was chosen by eye
            #: against that. Underline and gradient ship off, and are declared so the opinion is
            #: deliberate rather than inherited -- on a fresh install neither writes anything.
            "BoldTitle": "false",
            "UnderlineTitle": "false",
            "DrawBackgroundGradient": "false",
            #: The stretch of **window** outline beside whatever button the mouse is over takes
            #: that button's colour: point at the close button and the line round the window goes
            #: red with it. Not to be confused with the button's own outline, which is
            #: `ShowOutline...` in `ButtonBehaviour` below; this session managed to confuse them
            #: once already.
            #:
            #: Wanted, and it happens to be what the decoration ships, so this entry writes nothing
            #: on a fresh install — it is here to say the opinion is deliberate rather than
            #: inherited, and to carry the record below.
            #:
            #: **Turning it off does not fix the pixel at the corner, and this is the record that
            #: it was tried.** The reasoning was good and the result was not: a screenshot of the
            #: hovered close button's top-right corner had no orange pixel in it at all, although
            #: the outline is orange, so the repaint was plainly happening there — and the one bad
            #: pixel sat exactly where the repainted stretch would meet the rest. Measured after
            #: switching it off: the pixel is still there.
            #:
            #: What that leaves is geometry, and the next thing to look at is that the outline is
            #: **2.25 px thick over a corner of radius 2**. The bad pixel is not a different
            #: colour, it is 35 % transparent — a hole letting the background through, three
            #: pixels in from the edge, which is inside the outline's own stroke. A stroke wider
            #: than the arc it follows passes over itself at the corner.
            "ColorizeWindowOutlineWithButton": "true",
            "RoundAllCornersWhenNoBorders": "true",
            "DrawBorderOnMaximizedWindows": "false",
            #: **Leave this ON.** It decides what colour the decoration paints behind itself, and
            #: turning it off exposes the frame colour -- dark and opaque -- in the gap a
            #: full-height button leaves. This app used to write `false` here, and that was the
            #: dark line under the buttons; the fix was to stop. Setting it false again brings the
            #: line back, and no amount of turning button outlines off fixes it for the button
            #: shapes that leave a gap on purpose.
            "UseTitleBarColorForAllBorders": "true",
        },
        "ButtonBehaviour": _BUTTON_BEHAVIOUR,
        "TitleBarOpacity": {
            #: Opaque, in both states -- and the two override flags with it, because without them
            #: the numbers are not read at all under any colour scheme this app ships. The
            #: decoration (`libbreezecommon/decorationcolors.cpp`,
            #: `generateDecorationPaletteGroup`) applies the opacity setting only when the
            #: scheme's `[WM] activeBackground` carries no alpha of its own **or** the flag for
            #: that state is on. Nine of the eleven schemes this app ships, and Klassy's own
            #: two, carry `activeBackground=r,g,b,191` -- a bar three quarters opaque, decided by
            #: the scheme -- so with the flag off the slider is ignored, the active bar stays at
            #: 75 %, and the decoration's own dialog greys the slider out with "Active opacity
            #: set by colour scheme". Carl's scheme is opaque, and so is the monochrome pair's,
            #: which is written that way rather than relying on this flag: a bar three quarters
            #: opaque measured as a **third** tone in a scheme whose whole point is one, and a
            #: scheme has to be right on a desk that is not running this app. The inactive flag is symmetry
            #: rather than measurement: every scheme seen here has an opaque `inactiveBackground`,
            #: so that slider applied already; the flag covers a scheme installed from elsewhere
            #: with an alpha on the inactive bar, and the dialog locks the pair anyway. A
            #: per-window override set to an opaque bar skips all of it.
            #:
            #: **The state goes last in these four names, and that is a correction.** They were
            #: declared as `ActiveTitleBarOpacity` and `OverrideActiveTitleBarOpacity`, which no
            #: version of the decoration installed here reads: its schema,
            #: `/usr/share/config.kcfg/klassy-decoration.kcfg`, names them `TitleBarOpacityActive`
            #: and `OverrideTitleBarOpacityActive`, and those are the spellings in its library. So
            #: *Restore* wrote two keys nothing read and the active bar stayed at the scheme's 75 %
            #: under nine presets out of eleven -- the very thing this block exists to stop. The
            #: stale spellings are renamed once by `migrate.py`, and `scripts/dry-run.sh` now checks
            #: every key declared for the decoration against that schema, so a name it does not
            #: know fails a check instead of writing nothing.
            #:
            #: Measured on the screen, with a dialog nobody manages over a backdrop switched between
            #: two colours, the bar compared with the dialog's body: under Klassy Dark, whose active
            #: bar carries alpha 191, the flag on left the bar opaque (it changed exactly as much as
            #: the body), off let a quarter of the backdrop through (3.93 times the body, 3.9
            #: predicted for 75 %), on again opaque. A stale name at 50 changed nothing; the right
            #: one at 50 let half through. **Under a colour of your own soaked in**, the scheme's
            #: `[WM]` colour is replaced by the tinted window colour, which has no alpha, so the bar
            #: is opaque whatever the flag says -- the flag matters for the presets worn plain.
            "TitleBarOpacityActive": "100",
            "TitleBarOpacityInactive": "100",
            "OverrideTitleBarOpacityActive": "true",
            "OverrideTitleBarOpacityInactive": "true",
            #: The three extras, off. At 100 % they have nothing to act on -- each is about what
            #: happens to a bar that is see-through -- and off is what the dialog shows as
            #: nothing about opacity being on. They ship on, so leaving them out is not the same
            #: as turning them off.
            "OpaqueMaximizedTitleBars": "false",
            "BlurTransparentTitleBars": "false",
            "ApplyOpacityToHeader": "false",
        },
        #: The decoration's own "Background & outline colours" opacity, which is one slider
        #: governing the colour it gives a button's background and its outline. It ships at 60,
        #: which makes a hovered button look half-there against a translucent title bar. At 100 the
        #: button reads as a button.
        #:
        #: Both states, because the decoration keeps this one twice like every other button
        #: setting, and a hovered button on an unfocused window is still a hovered button.
        "ButtonColors": {
            "ButtonBackgroundOpacityActive": "100",
            "ButtonBackgroundOpacityInactive": "100",
        },
        #: The decoration's own spacing, and deliberately nothing else: the values it ships, read
        #: out of its `klassy-decoration.kcfg`, declared so that *Restore defaults* puts them
        #: back after a change made in its dialog. Top and bottom together are the height of the
        #: bar; the side padding is the gap either side of the title. On a file that never carried
        #: the keys none of this writes anything -- `declared.write_declared` compares against the
        #: value that applies, shipped default included.
        "TitleBarSpacing": {
            "TitleBarTopMargin": "3.6",
            "TitleBarBottomMargin": "3.6",
            "TitleBarLeftMargin": "0",
            "TitleBarRightMargin": "0",
            "TitleSidePadding": "4",
        },
        "WindowOutlineStyle": {
            "WindowOutlineThickness": "2.25",
            "WindowOutlineStyleActive": "WindowOutlineCustomColor",
            "WindowOutlineCustomColorActive": "255,152,8",
            "WindowOutlineCustomColorOpacityActive": "100",
            "WindowOutlineStyleInactive": "WindowOutlineContrast",
            "WindowOutlineCustomColorInactive": "255,152,8",
            "WindowOutlineAccentColorOpacityActive": "100",
        },
    },
    #: The decoration does **not** pick the border size itself, and the size it is told to use is
    #: the ordinary one. Both are declared because both are read: with `BorderSizeAuto` off, the
    #: number beside it stops being decorative. Neither reaches a window this app manages — those
    #: carry "no border" in their own override, which wins — so this is about everything else.
    "decoration": {"": {"BorderSize": "Normal", "BorderSizeAuto": "false"}},
    "windows": {"": {
        "FocusPolicy": "FocusFollowsMouse",
        "NextFocusPrefersMouse": "true",
        "DelayFocusInterval": "50",
        "FocusStealingPreventionLevel": "1",
        "SeparateScreenFocus": "true",
    }},
    "blur": {"": {
        "BlurStrength": "6",
        "NoiseStrength": "5",
        #: Mirrored from the decoration's window corner radius by the Appearance tab, which is the
        #: single origin for it. The two are declared equal here so a restore leaves them agreeing.
        "CornerRadius": "7.5",
        "Brightness": "100",
        "Saturation": "150",
        "Contrast": "100",
        "BlurDecorations": "true",
        "BlurMenus": "true",
        "BlurDocks": "true",
        #: The per-window list turns blur OFF for what is in it. The Windows tab's Blur column
        #: reads the pair to know which way round it is.
        "BlurMatching": "false",
        "BlurNonMatching": "true",
    }},
    "geometry": {"": {"Duration": "250"}},
    "tiling": {"": {
        "screenGapTop": "10", "screenGapBottom": "10", "screenGapLeft": "10",
        "screenGapRight": "10", "screenGapBetween": "10",
        #: Three layouts in the cycle and no more: Spiral, then Quarter, then Binary tree -- the
        #: owner's choice, stated as the order the layout key walks. The other nine are 0, which
        #: the tiler reads as "not in the cycle", and they stay on the Tiling tab one number away.
        #: The tiler also builds nothing for a layout at 0, so a key bound to one of those directly
        #: does nothing until it is given a number again; none of the nine had one bound here.
        #:
        #: The order before this one lives in `migrate.PREVIOUS_LAYOUT_ORDER`, which is how a desk
        #: that was still on it is moved across once and a desk somebody arranged is not.
        "spiralLayoutOrder": "1", "quarterLayoutOrder": "2", "binaryTreeLayoutOrder": "3",
        "tileLayoutOrder": "0", "monocleLayoutOrder": "0", "threeColumnLayoutOrder": "0",
        "stackedLayoutOrder": "0", "columnsLayoutOrder": "0", "spreadLayoutOrder": "0",
        "floatingLayoutOrder": "0", "stairLayoutOrder": "0", "cascadeLayoutOrder": "0",
        "adjustLayout": "true", "adjustLayoutLive": "true", "keepTilingOnDrag": "true",
        "floatUtility": "true", "preventMinimize": "false", "preventProtrusion": "true",
        "monocleMaximize": "true", "newWindowPosition": "0", "noTileBorder": "false",
        "limitTileWidth": "false", "limitTileWidthRatio": "1.6",
    }},
    #: All three on. The tiler's switch used to be a control on the Tiling tab and is not any
    #: more: this app exists to put a tiling desktop on KDE, so "tiling off" is not one of its
    #: states. Switching it off is still possible, in the desktop's own settings -- and the next
    #: Apply on the Tiling tab turns it back on, which is the honest consequence of not having the
    #: control.
    "plugins": {"": {"krohnkite": True, "better_blur_dx": True,
                     "kwin4_effect_geometry_change": True}},
}

#: The per-button colour overrides, and the opinion is that there should not be any.
#:
#: Every colour on a button follows the colour scheme. The icon and the outline are the
#: decoration's job, and a colour picked for them is a colour that has to be picked again every
#: time the scheme changes; the background a button turns when you point at it is the one slot
#: that changes what a window looks like at a glance, and the same reasoning covers it -- a
#: hover colour chosen against one scheme is the wrong colour under the next. All three are
#: declared as "no override", which is written as a removal.
#:
#: `None` means remove the slot. The buttons are the three a window shows; the other eight the
#: decoration knows about are left exactly as they are, because this app has never had an
#: opinion about them and a slot it did not write is not its to delete.
BUTTON_COLOURS = {
    button: {"IconNormal": None, "OutlineNormal": None, "BackgroundHover": None}
    for button in ("Close", "Maximize", "Minimize")
}

#: *Take KyprX off this desk*, which the owner chose to mean **pure KDE**: every key `SETTINGS`
#: declares deleted, so each program is back on its own default rather than on one of this app's;
#: this app's own keys taken out of every window rule and decoration override; the three plugins
#: this app switches on switched off; and KDE's own Breeze global theme for the mode in force
#: (`theme.PURE`). Not the desk from before KyprX -- nothing recorded that -- but a consistent one,
#: and one step before uninstalling. The two it does not undo, because they are not this app's:
#: the desktop's own blur effect, which somebody else may have switched off, and a key taken from
#: another action with *Use it here*.
TAKE_OFF_PLUGINS = ("krohnkite", "better_blur_dx", "kwin4_effect_geometry_change")

#: What each tab writes on Apply, as `(source, group, key)`. **Only settings that left the
#: interface.** A key still on screen must never be in here, or applying one row would put back
#: the value somebody had just changed on another.
#:
#: The title bar's keys are in none of these, on purpose -- see the module note. `BUTTON_COLOURS`
#: is not here either: it goes through `klassy.set_button_colours` rather than as
#: `source/group/key`, and *Restore defaults* is its only writer.
ENFORCED: dict[str, tuple[tuple[str, str, str], ...]] = {
    #: The five frame settings that were controls on the Appearance tab only for as long as it took
    #: to find what was putting a hole at the corner of a hovered button. It was not any of them —
    #: see `_BUTTON_BEHAVIOUR` — so they went back to being fixed, at the values the hunt settled
    #: on. The corner radius is the one that stayed a control.
    "appearance": (
        ("klassy", "Windeco", "ColorizeWindowOutlineWithButton"),
        ("decoration", "", "BorderSize"),
        ("decoration", "", "BorderSizeAuto"),
        ("klassy", "Windeco", "RoundAllCornersWhenNoBorders"),
        ("klassy", "Windeco", "DrawBorderOnMaximizedWindows"),
        ("klassy", "Windeco", "UseTitleBarColorForAllBorders"),
    ),
    "tiling": (
        ("plugins", "", "krohnkite"),
    ),
}


def value(source: str, group: str, key: str):
    """One declared value. Raises rather than returning None: a name that is not in here is a
    typo, and a typo that silently writes nothing is the worst shape this could take."""
    return SETTINGS[source][group][key]


def slice_for(page: str) -> dict:
    """What `page` enforces, shaped exactly like `SETTINGS` -- source, group, key.

    The same shape as the whole declaration, including the empty group name for the sources that
    are one flat section, so the writer has one shape to handle and not two.
    """
    out: dict = {}
    for source, group, key in ENFORCED.get(page, ()):
        out.setdefault(source, {}).setdefault(group, {})[key] = value(source, group, key)
    return out
