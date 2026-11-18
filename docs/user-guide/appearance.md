# Appearance

The Appearance tab decides what the desktop looks like: its colours, and the frame around every
window. Four boxes, from top to bottom: **Profiles**, **Colours**, **Window** and
**Title bar**.

When Klassy is missing or not running, an orange band across the top of the tab says so: the
title bar, the outline and the corner are Klassy's settings, and do nothing without it.
[What KyprX needs](settings.md#what-kyprx-needs) says what to do.

## Profiles

A profile is this tab kept under a name, so that you can try other colours and come back.

A profile carries:

- the **Opacity** number;
- the colours: Dark or Light, the preset, a colour of your own, and how far it soaks in;
- the **Corner radius**, together with the blur's corner, which follows it;
- the window outline: its thickness, the two styles, the two custom colours and the two
  opacities.

A profile does not carry which windows are see-through or a window's own opacity (both are set on
the [Windows](windows.md) tab), the title bar, the other effects, the tiling, the shortcuts or
the wallpaper. **Colour from the wallpaper** is always stored as off.

### The list

One row per profile, in the order they were saved:

- **Profile**: the name, with a strip of the preset's colours, and your own colour at the end
  when there is one. An empty outline instead of colours means the preset's colour scheme is not
  on this computer.
- **Colours**: the mode, the preset, then *your colour* with its three numbers (and *soaking
  N %*), or *the preset's own colours*.
- **Opacity**: the number, or *opaque* at 100 %. *as it is* means the profile carries no opacity.
- **Frame**: the corner radius, the outline's thickness, and the two styles.

The row in **bold** is the profile the desktop is wearing; loading it would change nothing, and
the line under the list names it, or says **None of these is what is on the desktop now.** While
there are no profiles, the list is hidden and the line says **No profiles yet.** *Save what is on
the desktop as…* **keeps this tab under a name of your own.** Double-clicking a row loads it.

### The buttons

- **Save what is on the desktop as…** asks for a name (up to 80 characters) and suggests the
  preset's. Names are compared without regard to capital letters, and saving under a name already
  in the list asks **Replace this profile?** first. Saving is refused, with the reason on the
  line, when the global theme is not one of Klassy's or the colours are not one of the presets:
  pick a mode or a preset under **Colours** first.
- **Load** puts the selected profile on the desktop. Greyed while it works, on the bold row, and
  on a profile that cannot be loaded here. While it works, the line at the bottom says
  **Putting** *name* **on… the desktop's own tools take a second or two**.
- **Update** overwrites the selected profile with what is on the desktop now, after asking.
  Greyed on the bold row.
- **Rename…** gives the selected profile another name. What it holds does not change.
- **Delete** forgets the selected profile, after asking. It sits apart from the others, on the
  right, because it cannot be undone.

**Load**, **Update**, **Rename…** and **Delete** are greyed while no row is selected. The
questions -- **Replace this profile?**, **Update this profile?** and **Delete this profile?** --
all have **No** as the answer Enter gives.

### What loading does

Loading unticks **Colour from the wallpaper** in the strip above the tabs -- left ticked, the next
wallpaper set from the picker would recolour the desktop over the profile. Only what differs from
the desktop is written. The window outline is put back as the profile saved it; the colour a
preset puts on the outline is not applied on a load.

The screen can stop up to twice while a profile goes on: once for the opacity, the corner and the
outline, and once for the colours (measured; see the comment in `daemon/kyprd_profiles.py`).

The **Profile** menu above the tabs lists the same profiles and puts one on the same way
([The KyprX window](README.md#profile)).

### A profile that cannot be loaded here

A profile whose preset cannot be used here is still listed: its row is dimmed, its tooltip gives
the reason, selecting it adds *name* **cannot be loaded here:** *reason* to the line, and
**Load** is greyed. The usual reason is a colour scheme that is not installed on this computer.
It can still be updated, renamed or deleted.

If the file the profiles are kept in cannot be read, the line under the list gives the reason and
every change is refused until the file is put right, so that nothing is saved over it
(MAP).

## Colours

The desktop's colours, for the windows and the panel alike. Only the colours change: under every
preset the global theme, the application style and the window decoration stay Klassy's, and the
panel wears KyprX's own Plasma style, which takes its colours from the colour scheme.

KyprX's default: **Dark**, **Longive**, no colour of your own. **Restore KyprX's defaults…**
puts it on, and so does **Put KyprX's look on**; nothing else does by itself.

### KyprX's look, the first time

KyprX's first start leaves your look as it is. It puts on only Klassy's window frames, drawn in
your colours, with the outline round the active window in your accent colour. The first time the
settings window opens after that, it asks whether to put KyprX's look on as well, and lists
exactly what would change:

- **Put KyprX's look on** keeps a copy of the desk first, then puts it on: Klassy's global theme,
  KyprX's default colours, its panel style and an amber outline. **Go back to a copy…** on the
  [Settings](settings.md#go-back-to-a-copy) tab puts back what KyprX writes. A copy holds colours
  only when they were one of KyprX's presets, so a global theme and colours of your own come back
  from System Settings, where you chose them.
- **Keep my look**, the default, changes nothing. Closing the question, or pressing Esc, counts
  as that.

Either answer is remembered, and the question is not asked again. An update never asks it, and
neither does a new install whose [KyprX folder](settings.md#your-kyprx-folder) brought a colour
preset with it: the folder's colours are the answer. After
[Remove KyprX from this computer…](settings.md#remove-kyprx-from-this-computer), installing KyprX
again asks again.

### The orange band

When the desktop is not set up the way KyprX expects, an orange band at the top of the box starts
**Not what this app expects.** and lists what it found: the global theme is not one of Klassy's
(so the Dark and Light switch cannot tell which mode this is), the application style is not
Klassy, or the window decoration is not Klassy. It ends **Picking a mode here puts it back.**

Any change in this box applies Klassy's global theme for the mode first when the desktop is not
already on it, and that sets all three. When the global theme is already Klassy's and only the
application style or the decoration is wrong, nothing here re-applies it except switching to the
other mode and back.

After **Keep my look**, the same findings are said as your own choice rather than a fault, in
plain text: it starts **You kept your own look**, and ends **Picking a mode or a preset here puts
KyprX's look on.** That lasts until KyprX's colours go on some other way -- a mode or a preset
picked here, a profile loaded, **Restore KyprX's defaults…**, a copy of the desk, a KyprX folder
that wears a preset.

### Mode

**Dark** and **Light**. Switching shows that mode's presets and puts on the first one that can be
used, **Klassy Dark** or **Klassy Light**, counting as choosing a preset.

Switching mode is the one change here that does more than colours. It applies Klassy's global
theme for that mode, which also changes the defaults beneath your own settings, the cursor and
the splash screen among them. A setting of your own the global theme would remove, such as an
icon theme you chose yourself, is put back straight after it.

### The presets

The cards show the presets of the mode in force, four to a row:

- **Dark**: Klassy Dark, Longive, Catppuccin Mocha, Nord, Gruvbox Dark, Dracula, Solarized Dark,
  Monochrome Dark.
- **Light**: Klassy Light, Catppuccin Latte, Solarized Light, Gruvbox Light, Rosé Pine Dawn,
  Monochrome Light.

**Klassy Dark** and **Klassy Light** are the colour schemes Klassy's global theme applies by
itself: choosing one is the way back to Klassy's own colours. **Longive** is KyprX's own:
monochrome surfaces with one soft orange accent. It and the other eleven are colour schemes KyprX
installs itself. A profile or folder naming the preset `carl` gets Longive.

Each card is drawn from its colour scheme's own file. Under the pointer a card is washed with its
own text colour, and a thin ring shows where the keyboard is. Its tooltip carries the preset's
note and, when it cannot be chosen, the reason. A card that cannot be chosen looks different:

- the preset's colour scheme not installed: an outline card with the name and **not installed**,
  not clickable;
- KyprX's own Plasma style missing: every card drawn faded, none clickable, the tooltip saying
  **the Plasma style kyprx is not installed**.

The preset on the desktop wears a thick ring in its own text colour, and the line under the cards
names it, as **Nord is on. The panel follows its colours.** When the desktop's colour scheme is
none of these, no card has the ring, the line says **The colours on this desktop are not one of
these.** and asks you to pick one, and the rows for a colour of your own stay greyed until you
do.

**What choosing a preset puts back.** A preset is its own colours, so choosing one:

- drops a colour of your own and its soaking (choose the colour again afterwards to keep one);
- puts the preset's own selection colour on the focused window's outline, setting **Focused
  window**, under **Window**, to **Custom colour**, whatever style it was on, **None** included.
  **Other windows** is left as it is.

Choosing the preset that is already on changes nothing.

**The monochrome presets keep five colours.** Monochrome Dark and Monochrome Light are black,
white and grey all through, except five text colours that carry meaning: error (red), neutral
(amber), success (green), link (blue) and visited link (purple). Their selection colour is white
in the dark one and black in the light one, and that is the colour the focused window's outline
takes. Their cards show one area fewer, because the window and the content area are the same
colour.

**The lock screen and the log-out screen** draw in a colour set of their own. Their dark
background and light text stay the same on every preset, even the light ones, and neither a
colour of your own nor a light preset changes them. What does follow the preset: the password box
and the ring around it, and the small buttons' highlight under the pointer or Tab -- as on KDE's
own Colours page.

### The wallpaper's colour

While **Colour from the wallpaper** is ticked in the strip above the tabs
([The KyprX window](README.md#colour-from-the-wallpaper)), a wallpaper set from the picker hands
its colour to the desktop. The colour becomes your own colour on the preset in force (on the
mode's Klassy preset when the colours are not one of the presets), soaks into the backgrounds at
the strength already soaking in, or 25 % when nothing is, and goes on the window outline wherever
the outline's style reads a custom colour. How the colour is worked out is on the
[Wallpaper](wallpaper.md#colour-from-the-wallpaper) page.

**Colour from the wallpaper of** is a menu above that row, there only with more than one screen.
It lists **the primary screen** and then each screen by its name, such as `DP-1`, with the
monitor's maker and model and the wallpaper it shows. Choose a screen and, while the tick is on,
the desktop takes that screen's wallpaper colour at once; from then on a wallpaper set on that
screen, or on every screen, hands its colour over, and one set on another screen leaves the
colours alone. A chosen screen not connected now is shown as such, and the primary screen gives
the colour until it is back. KyprX's default: the primary screen. The choice belongs to this
computer, because a screen's name does: the KyprX folder does not carry it, and neither
**Restore KyprX's defaults…** nor going back to a copy changes it.

While the tick is on, a row above **Your own colour** says what the wallpaper offers:

- **This colour came from your wallpaper.** The colour on the desktop is the wallpaper's.
- **Your wallpaper offers** *three numbers* -- with more than one screen, **The wallpaper of**
  *the screen* **offers** *three numbers* -- **The colour below is yours, and stands until the
  next wallpaper.**, with a **Take it** button. You chose another colour since, or the wallpaper
  changed outside KyprX, which never recolours the desktop by itself.
- **working out what colour this wallpaper gives — one moment**, while KyprX works out the colour
  of a wallpaper it has not seen before; the row changes by itself when the answer is ready.
- **this wallpaper has no colour to give**, or the reason the wallpaper could not be read.

**Take it** makes the offered colour your own, ticks **Let it soak into the backgrounds**
at the strength shown, and applies it, outline included. With the tick off, the row is hidden.

### Your own colour

**Your own colour** opens a colour picker. The colour goes on top of the preset: on its own it
reaches highlights, links and the selection, and on the lock screen what follows the preset
there. It is greyed until a preset has the ring.

**Clear**, beside it, goes back to the colours the preset came with, without changing preset.

A colour chosen here stays with the windows and the panel and does not move the window outline;
**Take the theme colour**, under **Window**, puts the outline on it.

**Let it soak into the backgrounds** pulls every other colour toward yours as well, as far as the
number beside it says: from 5 to 90 %. While nothing soaks in, the number shows 25 %. KyprX's
default: not ticked. The preset's own colour scheme file is never changed: KyprX writes a copy of
it with your colour in it
(MAP). While a colour soaks in, the
title bar takes the tinted window colour as well.

Nothing here needs a logout: the colours are applied by the desktop's own tools, so open
applications repaint where they are.

### The line about the window outline

The last line of the box says where the window outline takes its colour from: a style drawing
from the colour scheme (no colour here reaches it, though choosing a preset still puts that
preset's colour on it); a colour of its own, set under **Window**; the same colour as your own;
or a colour of its own that differs from yours, with a pointer to **Take the theme colour**.

### When the screen stops

Every change of colours runs the desktop's own colour tools, and every open application repaints:
the screen stops for a moment. A change that also moves the window outline makes the decoration
read its settings again, and the screen stops a second time.

- **Once**: a colour of your own chosen by hand, **Clear**, ticking or unticking **Let it soak
  into the backgrounds**, and its number.
- **Twice**, when the outline actually changes: choosing a preset, switching **Mode**, and
  **Take it**.
- **Not at all**: choosing what is already on.

How long each stop lasts was measured; see the comment in `daemon/kyprd_theme.py`
(`ThemePart.set_theme`).
[Troubleshooting](../troubleshooting.md#the-screen-stops-for-a-moment-when-the-colours-change) has
more. While a change goes on, the box is greyed and the line at the bottom says so. If it fails,
the line says why and the box shows the desktop as it is.

After a change that moves the colours, KyprX deletes the pictures the file manager keeps of
folders, which were drawn in the old colours, so that they are drawn again in the new ones.
Pictures of files are left alone.

## Window

What a window looks like: how see-through it is, how round its corners are, and the ring around
it, called the outline.

| Row | What it sets | Range | KyprX's default |
|---|---|---|---|
| **Opacity** | How solid a see-through window is; 100 % is opaque | 1 to 100 % | 92 % |
| **Corner radius** | How round a window's corners are | 0 to 30 px, in steps of 0.5 | 7.5 px |
| **Outline** | How thick the ring around a window is | 0 to 10 px, in steps of 0.25 | 2.25 px |
| **Focused window** | Where the ring around the window you are using takes its colour from | one of seven styles | Custom colour |
| **Its custom colour** | The colour of that ring on a custom style | any colour | orange, 255,152,8 |
| **Its opacity** | How solid that custom colour is drawn | 0 to 100 % | 100 % |
| **Its accent opacity** | How solid that ring is drawn on an accent style | 0 to 100 % | 100 % |
| **Other windows** | Where the ring around every other window takes its colour from | one of seven styles | Contrast |
| **Their custom colour** | The colour of those rings on a custom style | any colour | orange, 255,152,8 |

**Opacity** reaches every window whose **Transparency** is ticked on the
[Windows](windows.md) tab and that has no opacity of its own there, and no other window. At
**100 %** a ticked window and an unticked one look the same, so KyprX keeps the ticks made while
the number stands there, and moving it below 100 % puts every kept tick back on the desk at the
new number ([Windows](windows.md#transparency)).

**Corner radius** is the one place the corner is set: this row writes both the window's corner
and the blur's, so the blur never shows past the rounded corner. The
[Effects](effects.md) tab has no corner.

**The seven styles** of **Focused window** and **Other windows** are **None**, **Shadow
colour**, **Contrast**, **Accent colour**, **Accent with contrast**, **Custom colour** and
**Custom with contrast**. **None** draws no ring. **Contrast** takes the window's text colour.
The two accent styles take the colour scheme's highlight colour, which your own colour replaces
when you have one. The two custom styles take the colour in the row below them; **Custom with
contrast** mixes it with the window's text colour. The decoration draws the ring
(Klassy).

A row the chosen style does not read is greyed rather than hidden: the two custom rows of
**Focused window** count only on its custom styles, **Its accent opacity** only on its accent
styles, and **Their custom colour** only while **Other windows** is on a custom style.

**Take the theme colour** puts your own colour, as it is on the desktop, into **Its custom
colour**, and into **Their custom colour** as well when **Other windows** is on a custom style.
It is greyed unless there is a colour of your own on the desktop and **Focused window** is on a
custom style; a preset's colours alone cannot be taken this way, as choosing a preset already
puts its colour on the ring.

A change to **Opacity** or **Corner radius** makes the compositor read its settings again, and
the screen stops briefly; a change to any of the outline's rows also makes the decoration rebuild
the colours it keeps, and the stop is longer (measured; see the comment in `daemon/reload.py`,
`invalidate_colour_cache`).

**Every change to one of the rows below Opacity** also puts six settings of the decoration that
have no row here back to KyprX's values: the stretch of outline beside the title bar button under
the pointer takes that button's colour; the border size is Normal, and the decoration does not
pick one itself; a window without borders is rounded at all four corners; a maximised window has
no border; the borders take the title bar's colour. Change one of them in the decoration's own
settings and it comes back with the next change in this box.

## Title bar

This box has no settings; its line says **The title bar is the decoration's own settings, and
what you change there stays.** Nothing on this tab writes the title bar, and a profile does not
carry it. The KyprX folder and the copies of the desk keep it as it is, with the rest of the
decoration's settings.

**Title bar settings…** opens the decoration's own settings: Klassy's settings program when it is
installed, otherwise Klassy's page in System Settings. When neither can be found, the button does
nothing. The dialog cannot be told which tab to open on; the title bar is its **Titlebar** tab,
one click away. During a dry run the button is greyed
([The KyprX window](README.md#dry-run)), because Klassy's own settings save for real.

KyprX's own title bar is what **Restore KyprX's defaults…** puts back:

- Klassy's **Material** icons, on buttons that fill the full height of the bar as plain
  rectangles;
- buttons that always show their icon, and show their background and outline only under the
  pointer or while pressed, the close button included;
- button backgrounds and outlines drawn at full strength, on the focused window and on the
  others;
- no colour of their own for the icon, the outline or the background under the pointer on the
  close, maximise and minimise buttons, so that those follow the colour scheme; the decoration's
  other buttons are left as they are;
- an opaque title bar, focused or not, whatever the colour scheme asks for, with the three extras
  for a see-through bar switched off (opaque when maximised, blur behind the bar, opacity applied
  to the application's header);
- the title bar in the colour scheme's colour rather than the colour an application paints its
  own header;
- a plain title, neither bold nor underlined, no gradient on the bar, and no line under it;
- Klassy's own spacing, which sets the bar's height and the gap either side of the title.

The keys behind each item are on the Klassy page.
