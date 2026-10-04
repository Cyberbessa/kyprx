# Appearance

The Appearance tab decides what the desktop looks like: its colours, and the frame around every
window. It has four boxes, from top to bottom: **Profiles**, **Colours**, **Window** and
**Title bar**.

When Klassy is not installed, or the desktop is not running it, an orange band across the top of
the tab says so: the title bar, the outline and the corner are Klassy's settings, and do nothing
without it. [What KyprX needs](settings.md#what-kyprx-needs) says what to do.

Changes apply by themselves a moment after you stop making them, and a grey dot in front of a
setting's name means nothing has been written for it yet; both are explained on
[The KyprX window](README.md). Where this page gives *KyprX's default*, it is the value that
**Restore KyprX's defaults…** on the [Settings](settings.md) tab puts back.

## Profiles

A profile is this tab kept under a name, so that you can try other colours and come back.

A profile carries:

- the **Opacity** number;
- the colours: Dark or Light, the preset, a colour of your own, and how far it soaks in;
- the **Corner radius**, together with the blur's corner, which follows it;
- the window outline: its thickness, the two styles, the two custom colours and the two opacities.

A profile does not carry which windows are see-through or a window's own opacity (both are set on
the [Windows](windows.md) tab), the title bar, the other effects, the tiling, the shortcuts or the
wallpaper. **Colour from the wallpaper** is always stored as off.

### The list

One row per profile, in the order they were saved:

- **Profile**: the name, with a strip of the preset's colours, and your own colour at the end when
  the profile has one. An empty outline instead of colours means the preset's colour scheme is not
  on this computer.
- **Colours**: the mode, the preset, then *your colour* with its three numbers (and *soaking N %*
  when it soaks in), or *the preset's own colours*.
- **Opacity**: the number, or *opaque* at 100 %. *as it is* means the profile carries no opacity,
  and loading it leaves the number alone.
- **Frame**: the corner radius, the outline's thickness, and the styles of the focused window and
  the other windows.

The row in **bold** is the profile the desktop is wearing now. Loading it would change nothing. The
line under the list names it, or says **None of these is what is on the desktop now.** While there
are no profiles, the list is hidden and the line says how to make one.

Double-clicking a row loads it.

### The buttons

- **Save what is on the desktop as…** asks for a name and suggests the name of the preset on the
  desktop. A name can be up to 80 characters. Names are compared without regard to capital
  letters, so *Nord* and *nord* are the same profile; saving under a name already in the list asks
  **Replace this profile?** first. Saving is refused, with the reason on the line, when the global
  theme is not one of Klassy's or when the colours on the desktop are not one of the presets: pick
  a mode or a preset under **Colours** first.
- **Load** puts the selected profile on the desktop. The box is greyed while it works, and the line
  at the bottom of the window says **Putting** *name* **on… the desktop's own tools take a second
  or two**. Greyed on the bold row, and on a profile that cannot be loaded here.
- **Update** overwrites the selected profile with what is on the desktop now, after asking. Greyed
  on the bold row.
- **Rename…** gives the selected profile another name. What it holds does not change.
- **Delete** forgets the selected profile, after asking. The desktop does not change. It sits apart
  from the others, on the right, because it cannot be undone.

**Load**, **Update**, **Rename…** and **Delete** are greyed while no row is selected. The
questions **Replace this profile?**, **Update this profile?** and **Delete this profile?** have
**No** as the answer Enter gives.

### What loading does

**Loading a profile unticks Colour from the wallpaper**, in the strip above the tabs. Left ticked,
the next wallpaper set from the picker would recolour the desktop over the profile. Tick it again
to hand the colour back to the wallpaper.

Only what differs from the desktop is written. The window outline is put back as the profile
saved it: the colour a preset puts on the outline when you choose it under **Colours** is not
applied on a load.

The screen can stop up to twice while a profile goes on: once for the opacity, the corner and the
outline, and once for the colours. How long each stop lasts was measured — see the comment in
`daemon/kyprd_profiles.py` (`ProfilesPart.apply_look`).

The **Profile** menu above the tabs lists the same profiles and puts one on the same way
([The KyprX window](README.md#profile)).

### A profile that cannot be loaded here

A profile whose preset cannot be used on this computer is still listed. Its row is dimmed and its
tooltip gives the reason. Selecting it adds *name* **cannot be loaded here:** *reason* to the line,
and **Load** is greyed. The usual reason is a colour scheme that is not installed, for example a
profile made with Carl on a computer without Carl. A profile naming a preset that does not exist,
or a preset of the other mode, is shown the same way. It can still be updated, renamed or deleted.

If the file the profiles are kept in cannot be read, the line under the list gives the reason, and
every change is refused until the file is put right, so that nothing is saved over it. The file is
listed in MAP.

## Colours

The desktop's colours, for the windows and the panel alike. Only the colours change: under every
preset the global theme, the application style and the window decoration stay Klassy's, and the
panel wears KyprX's own Plasma style, which takes its colours from the colour scheme
(KDE Plasma).

KyprX's default: **Dark**, **Klassy Dark**, no colour of your own.

### The orange band

When the desktop is not set up the way KyprX expects, an orange band at the top of the box starts
**Not what this app expects.** and lists what it found:

- the global theme is not one of Klassy's, so the Dark and Light switch cannot tell which mode this
  is;
- the application style is not Klassy;
- the window decoration is not Klassy.

It ends **Picking a mode here puts it back.** Any change in this box applies Klassy's global theme
for the mode first when the desktop is not already on it, and that sets all three. When the global
theme is already Klassy's and only the application style or the decoration is wrong, nothing here
re-applies it except switching to the other mode and back.

### Mode

**Dark** and **Light**. Switching shows that mode's presets and puts on the first one that can be
used, **Klassy Dark** or **Klassy Light**. That counts as choosing a preset, with everything
choosing a preset does (below).

Switching mode is the one change here that does more than colours. It applies Klassy's global theme
for that mode, which also changes the defaults that sit under your own settings, the cursor and the
splash screen among them. A setting of your own that the global theme would remove, such as an icon
theme you chose yourself, is put back straight after it.

### The presets

The cards show the presets of the mode in force, four to a row:

- **Dark**: Klassy Dark, Carl, Catppuccin Mocha, Nord, Gruvbox Dark, Dracula, Solarized Dark,
  Monochrome Dark.
- **Light**: Klassy Light, Catppuccin Latte, Solarized Light, Gruvbox Light, Rosé Pine Dawn,
  Monochrome Light.

**Klassy Dark** and **Klassy Light** are the colour schemes Klassy's global theme applies by
itself: choosing one is the way back to Klassy's own colours. **Carl** is a colour scheme by another
author, installed separately and left exactly as it is found (Carl). The
other eleven are colour schemes KyprX installs itself.

Each card is drawn from its colour scheme's own file: the card in the window colour, a content area
in the view colour, a short selected row in the selection colour, and the name in the text colour.
Under the pointer a card is washed with its own text colour, and a thin ring in the window's
highlight colour shows where the keyboard is. Its tooltip carries the preset's note and, when it
cannot be chosen, the reason.

A card that cannot be chosen looks different:

- When the preset's colour scheme is not installed (Carl, on a computer without it), the card is an
  outline with the preset's name and **not installed**, and cannot be clicked.
- When KyprX's own Plasma style is missing, every card is drawn faded and none can be chosen; the
  tooltip says **the Plasma style kyprx is not installed**.

**The ring and the line under the cards.** The preset on the desktop wears a thick ring in its own
text colour, and the line under the cards names it, for example **Nord is on. The panel follows its
colours.** When the desktop's colour scheme is none of these, no card has the ring, the line says
**The colours on this desktop are not one of these.** and asks you to pick one, and the rows for a
colour of your own stay greyed until you do.

**What choosing a preset puts back.** A preset is its own colours, so choosing one:

- drops a colour of your own and its soaking (choose the colour again afterwards to keep one);
- puts the preset's own selection colour on the focused window's outline, and sets **Focused
  window**, under **Window**, to **Custom colour**, whatever style it was on, **None** included.
  **Other windows** is left as it is.

Choosing the preset that is already on changes nothing.

**The lock screen and the log-out screen.** These two screens are KDE's, and they draw in a colour
set of their own. Their dark background and light text stay the same on every preset, even the
light ones, and neither a colour of your own nor a preset's light colours change them. Two things
on the lock screen do follow the preset. The box you type your password in is drawn like any other
text box, so it wears the preset's colours — light under a light preset — and so does the ring
around it. The small buttons (the virtual keyboard, the keyboard layout, the music controls) light
up in the preset's highlight when you point at them or reach them with Tab. The window ring and the
highlights keep following the preset too, as they do on KDE's own Colours page.

### The wallpaper's colour

While **Colour from the wallpaper** is ticked in the strip above the tabs
([The KyprX window](README.md#colour-from-the-wallpaper)), every wallpaper set from the picker
hands its colour to the desktop. That colour becomes your own colour on the preset in force (on the
mode's Klassy preset when the colours are not one of the presets), soaks into the backgrounds at
the strength already soaking in, or at 25 % when nothing is, and is put on the window outline
wherever the outline's style reads a custom colour. How the colour is worked out is on the
[Wallpaper](wallpaper.md#colour-from-the-wallpaper) page.

While the tick is on, a row above **Your own colour** says what the wallpaper on screen offers:

- **This colour came from your wallpaper.** The colour on the desktop is the wallpaper's.
- **Your wallpaper offers** *three numbers*. **The colour below is yours, and stands until the next
  wallpaper.**, with a **Take it** button. You have chosen another colour since, or the wallpaper
  was changed outside KyprX, which never recolours the desktop by itself.
- **working out what colour this wallpaper gives — one moment**, while KyprX works out the colour
  of a wallpaper it has not seen before. The row changes by itself when the answer is ready.
- **this wallpaper has no colour to give**, or the reason the wallpaper could not be read.

**Take it** makes the offered colour your own colour, ticks **Let it soak into the backgrounds** at
the strength shown, and applies it. Because it is the wallpaper's colour, the window outline
follows it too, wherever the outline's style reads a custom colour.

With the tick off, the row is hidden.

### Your own colour

**Your own colour** opens a colour picker. The colour goes on top of the preset: on its own it
reaches highlights, links and the selection. On the lock screen it reaches what follows the preset
there (the password box and the small buttons); the dark background and light text of the lock
screen and the log-out screen stay as they are. It is greyed until a preset has the ring.

**Clear**, beside it, goes back to the colours the preset came with, without changing preset. It
is greyed while there is no colour of your own.

A colour you choose here stays with the windows and the panel and does not move the window outline.
**Take the theme colour**, under **Window**, puts the outline on it.

**Let it soak into the backgrounds** pulls every other colour toward yours as well, backgrounds
included, as far as the number beside it says: from 5 to 90 %. While nothing soaks in, the number
shows 25 %. It is greyed until there is a colour of your own, and the number is greyed until the
box is ticked. KyprX's default: not ticked.

The preset's own colour scheme file is never changed: KyprX writes a copy of it with your colour in
it (MAP). While a colour soaks in, the
title bar takes the tinted window colour as well (KDE Plasma).

### The line about the window outline

The last line of the box says where the window outline takes its colour from:

- a style that draws from the colour scheme, so no colour here reaches it, although choosing a
  preset still puts that preset's colour on it;
- a colour of its own, set under **Window**;
- the same colour as your own colour;
- a colour of its own that differs from your own colour, with a pointer to **Take the theme
  colour**.

The line calls the place those are set *Outline*; it is the **Window** box below.

### When the screen stops

Every change of colours runs the desktop's own colour tools, and every open application repaints:
the screen stops for a moment. A change that also moves the window outline makes the decoration
read its settings again, and the screen stops a second time.

- **Once**: a colour of your own chosen by hand, **Clear**, ticking or unticking **Let it soak into
  the backgrounds**, and its number.
- **Twice**, when the outline actually changes: choosing a preset, switching **Mode**, and
  **Take it**.
- **Not at all**: choosing what is already on.

How long each stop lasts was measured — see the comment in `daemon/kyprd_theme.py`
(`ThemePart.set_theme`).
[Troubleshooting](../troubleshooting.md#the-screen-stops-for-a-moment-when-the-colours-change) has
more.

While a change goes on, the box is greyed and the line at the bottom of the window says
**Putting** *preset* **on… the desktop's own tools take a second or two**. If the change fails,
the line says why, in the words KyprX's background service gave, and the box shows the desktop as
it is.

## Window

What a window looks like: how see-through it is, how round its corners are, and the ring around it,
called the outline.

| Row | What it sets | Range | KyprX's default |
|---|---|---|---|
| **Opacity** | How solid a see-through window is; 100 % is opaque | 1 to 100 % | 92 % |
| **Corner radius** | How round a window's corners are | 0 to 30 px, in steps of 0.5 | 2.5 px |
| **Outline** | How thick the ring around a window is | 0 to 10 px, in steps of 0.25 | 2.25 px |
| **Focused window** | Where the ring around the window you are using takes its colour from | one of seven styles | Custom colour |
| **Its custom colour** | The colour of that ring on a custom style | any colour | orange, 255,152,8 |
| **Its opacity** | How solid that custom colour is drawn | 0 to 100 % | 100 % |
| **Its accent opacity** | How solid that ring is drawn on an accent style | 0 to 100 % | 100 % |
| **Other windows** | Where the ring around every other window takes its colour from | one of seven styles | Contrast |
| **Their custom colour** | The colour of those rings on a custom style | any colour | orange, 255,152,8 |

**Opacity** reaches every window whose **Transparency** is ticked on the [Windows](windows.md) tab
and that has no opacity of its own there, and no other window. Which windows are see-through is
chosen on that tab; how see-through they are is chosen once, here.

**100 % is the one number KyprX has to remember things at.** There, a ticked window and an unticked
one look the same -- both are drawn fully opaque -- so KyprX keeps the ticks made while the number
stands at 100 %, and the [Windows](windows.md) tab shows them ticked. Moving the number below 100 %
puts every kept tick back on the desk on its own, at the new number.

**Corner radius** is the one place the corner is set. The blur behind a window keeps a corner of
its own, and this row writes both, so that the blur never shows past the rounded corner; the
[Effects](effects.md) tab has no corner.

**The seven styles** of **Focused window** and **Other windows** are **None**, **Shadow colour**,
**Contrast**, **Accent colour**, **Accent with contrast**, **Custom colour** and **Custom with
contrast**. **None** draws no ring. **Contrast** takes the window's text colour. **Accent colour**
and **Accent with contrast** take the colour scheme's highlight colour, which your own colour
replaces when you have one. **Custom colour** and **Custom with contrast** take the colour in the
row below them; **Custom with contrast** mixes it with the window's text colour. The decoration
draws the ring (Klassy).

**Greyed rows.** A row the chosen style does not read is greyed rather than hidden:

- **Its custom colour** and **Its opacity** count only while **Focused window** is **Custom
  colour** or **Custom with contrast**.
- **Its accent opacity** counts only while **Focused window** is **Accent colour** or **Accent with
  contrast**.
- **Their custom colour** counts only while **Other windows** is **Custom colour** or **Custom with
  contrast**.

**Take the theme colour** puts your own colour, as it is on the desktop, into **Its custom
colour**, and into **Their custom colour** as well when **Other windows** is on a custom style.
It is then written like any other change. It is greyed unless there is a colour of your own on the
desktop and **Focused window** is **Custom colour** or **Custom with contrast**. A preset's colours
alone cannot be taken this way; choosing a preset already puts its colour on the ring.

**The screen.** A change to **Opacity** or **Corner radius** makes the compositor read its settings
again, and the screen stops briefly. A change to any of the outline's rows also makes the
decoration rebuild the colours it keeps, and the stop is longer. Both were measured — see the
comment in `daemon/reload.py` (`invalidate_colour_cache`).

**Frame settings KyprX keeps fixed.** Every change to one of the rows below **Opacity** also puts
six settings of the decoration that have no row here back to KyprX's values:

- the stretch of outline beside the title bar button under the pointer takes that button's colour;
- the border size is Normal, and the decoration does not pick one itself;
- a window without borders is rounded at all four corners;
- a maximised window has no border;
- the borders take the title bar's colour.

Change one of them in the decoration's own settings and it comes back with the next change in this
box.

## Title bar

This box has no settings. Its line says **The title bar is the decoration's own settings, and what
you change there stays.** Nothing on this tab writes the title bar, and a profile does not carry
it. The KyprX folder and the copies of the desk keep it as it is, with the rest of the decoration's
settings ([Settings](settings.md)).

**Title bar settings…** opens the decoration's own settings: Klassy's settings program when it is
installed, otherwise Klassy's page in System Settings. When neither can be found, the button does
nothing. The dialog cannot be told which tab to open on, so it opens on its first tab; the title
bar is its **Titlebar** tab, one click away. The same button is on the [Settings](settings.md) tab,
and during a dry run both are greyed ([The KyprX window](README.md#dry-run)).

KyprX's own title bar is what **Restore KyprX's defaults…** puts back:

- Klassy's **Material** icons, on buttons that fill the full height of the bar as plain rectangles;
- buttons that always show their icon, and show their background and outline only under the
  pointer or while pressed, the close button included;
- button backgrounds and outlines drawn at full strength, on the focused window and on the others;
- no colour of their own for the icon, the outline or the background under the pointer on the
  close, maximise and minimise buttons, so that those follow the colour scheme; the decoration's
  other buttons are left as they are;
- an opaque title bar, focused or not, whatever the colour scheme asks for, with the three extras
  for a see-through bar switched off (opaque when maximised, blur behind the bar, opacity applied
  to the application's header);
- the title bar in the colour scheme's colour rather than the colour an application paints its own
  header;
- a plain title, neither bold nor underlined, no gradient on the bar, and no line under it;
- Klassy's own spacing, which sets the bar's height and the gap either side of the title.

The keys behind each item are on the Klassy page.

## Good to know

- **The monochrome presets keep five colours.** Monochrome Dark and Monochrome Light are black,
  white and grey all through, backgrounds, text, selection and focus rings included, except five
  text colours that carry meaning: error (red), neutral (amber), success (green), link (blue) and
  visited link (purple). Their selection colour is white in the dark one and black in the light
  one, and that is the colour the focused window's outline takes when you choose them. Their cards
  show one area fewer than most, because the window and the content area are the same colour.
- **Nothing here needs a logout.** The colours are applied by the desktop's own tools, so open
  applications repaint where they are.
- **The file manager's pictures of folders follow.** After a change that moves the colours, KyprX
  deletes the pictures the file manager keeps of folders, which were drawn in the old colours, so
  that they are drawn again in the new ones. Pictures of files are left alone.
