#!/usr/bin/env bash
# Install KyprX for the current user. THIS CHANGES YOUR SESSION.
#
# It never installs a dependency. Package managers on immutable systems want a reboot, and
# add-ons want a network and a human decision. The preflight checks and stops, listing what is
# missing and where it comes from.
#
# What it does: links the compositor script, the daemon and the interface into the places the
# session looks in, writes the D-Bus activation file and the desktop entry, and makes the
# compositor load the script again. The script carries this app's shortcuts and its tiling, and
# registers its keys only as it loads -- so that reload is what puts them in place.
#
# --update brings this install up to the newest version in place, keeping the setup: a git clone
# is fast-forwarded to the branch it follows, a folder unpacked from a release gets the newest
# release unpacked beside it, and then the new version's installer runs and restarts the
# background service. Nothing is removed first.
#
# --uninstall removes what this script put in place, once 'Remove KyprX from this computer…', on
# KyprX's Settings tab, has taken KyprX's settings off the desk; while they are still there it
# stops and says so. --force removes the files anyway, and leaves those settings as they are.
#
# Usage: ./install.sh [--dry-run] | ./install.sh --update [--dry-run]
#        ./install.sh --uninstall [--force] [--dry-run]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin"
SHARE="${XDG_DATA_HOME:-$HOME/.local/share}"
KWIN_SCRIPT="$SHARE/kwin/scripts/kyprx"
SERVICES="$SHARE/dbus-1/services"
APPS="$SHARE/applications"
SCHEMES="$SHARE/color-schemes"
THEMES="$SHARE/plasma/desktoptheme"
ICONS="$SHARE/icons"
UNITS="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
#: A data directory of this app's own, spelled with every link resolved, which the session is told
#: to search: `realpath` because on this desktop the home directory is itself reached through a
#: link, and the one file that goes here has to be found by a path with none in it. See below.
DATA="$(realpath "$SHARE")/kyprx/data"
ENV_SCRIPT="${XDG_CONFIG_HOME:-$HOME/.config}/plasma-workspace/env/kyprx.sh"
PLUGIN_ID="kyprx"

DRY=0
MODE=install
#: --uninstall --force: remove the files although KyprX's settings are still on the desk.
FORCE=0

#: Handed by --update to the new version's installer (`update_all`): the version it came from,
#: and the folder it ran from when the new one was unpacked beside it.
FROM=""
PREVIOUS=""

die()  { echo "error: $*" >&2; exit 1; }
say()  { printf '%s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }
do_it() { (( DRY )) && { printf '  %-12s %s\n' "would" "$*"; return 0; }; eval "$@"; }

#: The icon's installed files, as paths under `hicolor/` -- the same relative path on both sides,
#: which is the whole of the icon theme layout. The picture the sizes are made from, and the mark
#: the public page shows, sit one level up, in share/icons/, and are not installed.
icon_files() { (cd "$HERE/share/icons" && find hicolor -type f | sort); }

#: Links this app made to icon files that are no longer in the tree -- the scalable drawing, once
#: the icon became a picture. Each one dangles, and nothing else would ever remove it: `icon_files`
#: only knows the files there are now. Only a link into this tree, only one that dangles; the two
#: paths compared resolved, because the same tree has two names where /home is a link to /var/home
#: and a link made under one is read back under the other.
stale_icon_links() {
  local link tree
  tree=$(realpath -m "$HERE/share/icons")
  while read -r link; do
    [[ "$(realpath -m "$(readlink "$link")")" == "$tree/"* && ! -e "$link" ]] && printf '%s\n' "$link"
  done < <(find "$ICONS/hicolor" -type l -path '*/apps/kyprx.*' 2>/dev/null)
  return 0
}

#: Whether the compositor has KyprX's script loaded after the reload below, asked the way the
#: daemon asks (`reload.script_loaded`) for about five seconds. It may not be: the compositor reads
#: a script it has not loaded before only once it has been running for about a minute -- until then
#: it goes by the list of packages it read as it started, measured in a nested KWin -- and one that
#: is not running at all, as from a text console, loads nothing. Either way the next login loads
#: it, and that is said. Loaded is no proof of the new code, though: a declarative script the
#: session already ran comes back as it was first read, which the message at the end says.
wait_until_the_script_is_loaded() {
  for _ in {1..25}; do
    [[ "$(busctl --user call org.kde.KWin /Scripting org.kde.kwin.Scripting isScriptLoaded s \
          "$PLUGIN_ID" 2>/dev/null)" == "b true" ]] && return 0
    sleep 0.2
  done
  say "  KyprX's new compositor script is not running yet: it starts at the next login, so log"
  say "  out and back in."
  return 0
}

#: The folder may carry a cache of what is in it, and a cache is rebuilt after its folder changes
#: -- what every package that installs an icon does. None there, none made.
icon_cache() {
  [[ -e "$ICONS/hicolor/icon-theme.cache" ]] && command -v gtk-update-icon-cache >/dev/null &&
    do_it "gtk-update-icon-cache -f -t '$ICONS/hicolor' >/dev/null 2>&1 || true"
  return 0
}

# ---------------------------------------------------------------- prerequisites
#
# Two halves. What the two programs themselves run on, looked for here: the three Python libraries
# and five of the desktop's own tools. Then the four projects KyprX is built on, looked for by
# daemon/requirements.py -- the same check the daemon makes and the Settings tab shows, so what
# stops an install here is exactly what the window would say afterwards. It finds each one by its
# own files and asks the running compositor whether it runs, so it works on any distribution; the
# package names it prints are the ones for this system.

preflight() {
  local missing=() out
  python3 -c 'import PySide6, dbus, gi' >/dev/null 2>&1 ||
    missing+=("PySide6, dbus-python and PyGObject for Python 3 — the daemon and the interface — your distribution's packages")
  command -v kwriteconfig6 >/dev/null || missing+=("kwriteconfig6 — switching the script on — KDE Frameworks' kconfig")
  command -v kreadconfig6 >/dev/null || missing+=("kreadconfig6 — reading desktop configuration — KDE Frameworks' kconfig")
  command -v plasma-apply-colorscheme >/dev/null ||
    missing+=("plasma-apply-colorscheme — the colour presets on the Appearance tab — plasma-workspace")
  command -v plasma-apply-lookandfeel >/dev/null ||
    missing+=("plasma-apply-lookandfeel — light and dark global themes — plasma-workspace")
  command -v plasma-apply-desktoptheme >/dev/null ||
    missing+=("plasma-apply-desktoptheme — the panel's style — plasma-workspace")
  if (( ${#missing[@]} == 0 )); then
    out=$(python3 "$HERE/daemon/requirements.py" 2>&1) && return 0
  fi

  echo "missing prerequisites — this script installs nothing:" >&2
  (( ${#missing[@]} )) && printf '  %s\n' "${missing[@]}" >&2
  [[ -n "${out:-}" ]] && printf '%s\n' "$out" >&2
  echo >&2
  echo "see the table in README.md" >&2
  exit 1
}

# ---------------------------------------------------------------- install

#: Everything an install made under this app's previous name left in the session.
#:
#: Not tidiness. The compositor script is *linked*, so an old directory left beside the new one
#: points at this same working tree: with both `Enabled` keys true the one script loads twice
#: under two ids, reports every window twice and registers the same shortcut names twice. The old
#: D-Bus activation file is the same shape of problem — it names a bus the new daemon does not
#: claim, and would go on activating a unit whose command no longer exists.
#:
#: What the old daemon wrote into config files is not here. That is the daemon's own one-off pass,
#: because it is the half that has to go through a transaction.
sweep_previous_name() {
  local old_script="$SHARE/kwin/scripts/cybekde"
  local found=0
  for target in "$old_script" "$BIN/cybe-kded" "$BIN/cybe-kde" \
                "$SERVICES/org.cyberbessa.CybeKde.service" "$UNITS/cybe-kded.service" \
                "$APPS/cybe-kde.desktop" "$APPS/cybe-kde-cheatsheet.desktop"; do
    [[ -e "$target" || -L "$target" ]] || continue
    (( found )) || step "clearing the previous name"
    found=1
    do_it "rm -f '$target'"
    (( DRY )) || say "  removed $target"
  done

  if [[ -f "${XDG_CONFIG_HOME:-$HOME/.config}/kwinrc" ]] &&
     grep -q '^cybekdeEnabled=' "${XDG_CONFIG_HOME:-$HOME/.config}/kwinrc" 2>/dev/null; then
    (( found )) || step "clearing the previous name"
    found=1
    do_it "kwriteconfig6 --file kwinrc --group Plugins --key cybekdeEnabled --delete"
    (( DRY )) || say "  removed kwinrc [Plugins] cybekdeEnabled"
  fi

  (( found )) && do_it "systemctl --user stop cybe-kded 2>/dev/null || true"
  return 0
}

install_all() {
  preflight
  sweep_previous_name

  step "compositor script"
  # A link rather than a copy: the compositor reads the script and never writes to it, so the
  # working tree can be the source and an edit is the installed file at once. The compositor runs
  # an edit from the next login on, though, not straight away: the last step says why.
  do_it "mkdir -p '$(dirname "$KWIN_SCRIPT")'"
  do_it "ln -sfn '$HERE/kwin-script' '$KWIN_SCRIPT'"
  say "  $KWIN_SCRIPT -> kwin-script/"

  step "daemon and interface"
  do_it "mkdir -p '$BIN'"
  do_it "ln -sf '$HERE/daemon/kyprd.py' '$BIN/kyprd'"
  do_it "ln -sf '$HERE/gui/kyprx.py' '$BIN/kyprx'"
  say "  $BIN/kyprd and $BIN/kyprx"

  step "D-Bus activation and menu entry"
  # The activation file names a systemd unit rather than just a command, which is the pattern the
  # desktop's own services use. Without it every activation gets an anonymous, throwaway unit with
  # a recycled number, and there is no stable name to stop or restart — which is how `pkill`
  # became the way to restart this, and `pkill` races the very activation it is trying to stop.
  do_it "mkdir -p '$SERVICES' '$APPS' '$UNITS'"
  do_it "sed 's|@BIN@|$BIN|g' '$HERE/share/kyprd.service' > '$UNITS/kyprd.service'"
  do_it "systemctl --user daemon-reload"
  do_it "sed 's|@BIN@|$BIN|g' '$HERE/share/org.cyberbessa.KyprX.service' > '$SERVICES/org.cyberbessa.KyprX.service'"
  do_it "sed 's|@BIN@|$BIN|g' '$HERE/share/kyprx.desktop' > '$APPS/kyprx.desktop'"
  # The overlay has a desktop entry again, and for a different reason than it used to. It is not
  # there to hang a shortcut on — the compositor script owns that key. It is there because the
  # overlay runs under a window class of its own, and an application id with no entry behind it
  # makes the desktop portal complain on every launch.
  do_it "sed 's|@BIN@|$BIN|g' '$HERE/share/kyprx-cheatsheet.desktop' > '$APPS/kyprx-cheatsheet.desktop'"
  do_it "sed 's|@BIN@|$BIN|g' '$HERE/share/kyprx-wallpaper.desktop' > '$APPS/kyprx-wallpaper.desktop'"
  do_it "update-desktop-database '$APPS' >/dev/null 2>&1 || true"
  # The session bus reads activation files when it starts and when asked to -- dbus-broker never
  # watches their folders, dbus-daemon never watches the user's (dbus-broker-launch(1),
  # dbus-daemon(1)) -- so until it is asked, nothing can start the daemon before the next login.
  do_it "busctl --user call org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus ReloadConfig >/dev/null 2>&1 || true"
  say "  $SERVICES/org.cyberbessa.KyprX.service"
  say "  $UNITS/kyprd.service"
  say "  $APPS/kyprx.desktop, $APPS/kyprx-cheatsheet.desktop and $APPS/kyprx-wallpaper.desktop"

  step "icon"
  # Linked file by file, never as a folder: `hicolor` is shared with every other application, so
  # only the files in it are this app's. A link like the rest, so a re-export shows at once.
  while read -r icon; do
    do_it "mkdir -p '$ICONS/$(dirname "$icon")'"
    do_it "ln -sf '$HERE/share/icons/$icon' '$ICONS/$icon'"
  done < <(icon_files)
  while read -r link; do do_it "rm -f '$link'"; done < <(stale_icon_links)
  icon_cache
  say "  $ICONS/hicolor: kyprx, $(icon_files | wc -l) files"

  step "colour schemes and the Plasma style"
  # The style is installed in two places, and the split is the whole finding. Where Plasma looks
  # for packages it gets a **copy** of `metadata.json` and `plasmarc` -- and deliberately not its
  # `colors`. That file fixes only the lock and log-out screens' set, and nothing the panel draws
  # in (a style whose colours file carries a palette for one of those sets paints the panel from
  # it and never reads the scheme; one that names none of them follows the scheme, and it exists
  # so that the shell, which asks every theme directory for it on every item it draws and never
  # remembers a miss, finds it at once). But it has to be found by a path with no symbolic link in
  # it: KConfig canonicalises a file name on open and the shared-config lookup compares the name
  # as asked for, so through a link the two libraries that read it each get an object of their
  # own, and only libplasma's is re-read when the scheme changes -- the panel's text followed the
  # wallpaper's colour and its background froze. Measured, and on this desktop the home directory
  # is itself reached through a link, so nothing under it qualifies. So the `colors` goes to a
  # directory spelled with every link resolved, and the session is told to search it, through the
  # environment script the desktop sources at login. Until the next login the file is not found,
  # which is exactly the previous behaviour: the panel follows, the shell probes.
  # `scripts/probe.py --follow` is the check, and `scripts/probe.py` counts the probes.
  #
  # Removed before it is made, and that is not tidiness: a link may still be there from an
  # earlier install, and a directory of the same name put there by hand once left a theme
  # package nested in itself.
  do_it "mkdir -p '$THEMES'"
  do_it "rm -rf '$THEMES/kyprx'"
  do_it "mkdir -p '$THEMES/kyprx'"
  do_it "cp '$HERE/share/desktoptheme/kyprx/metadata.json' '$HERE/share/desktoptheme/kyprx/plasmarc' '$THEMES/kyprx/'"
  say "  $THEMES/kyprx (a copy, without its colours file)"
  do_it "mkdir -p '$DATA/plasma/desktoptheme/kyprx' '$(dirname "$ENV_SCRIPT")'"
  do_it "cp '$HERE/share/desktoptheme/kyprx/colors' '$DATA/plasma/desktoptheme/kyprx/colors'"
  do_it "sed 's|@DATA@|$DATA|g' '$HERE/share/kyprx-env.sh' > '$ENV_SCRIPT'"
  say "  $DATA/plasma/desktoptheme/kyprx/colors (the colours file, by a path with no link in it)"
  say "  $ENV_SCRIPT (the session searches there from the next login on)"
  # An earlier version of this app kept a second style here, `kyprx-panel`, and wrote its colours
  # into it. Nothing reads it now: every preset wears `kyprx`, and the daemon writes into no
  # package. Left in place it is one more entry on the desktop's Plasma Style page, frozen at
  # whatever palette was last written into it -- so it goes, but only when the desktop is not
  # wearing it. This script never changes what is on screen; picking any preset on the Appearance
  # tab is what moves off it, and the install after that removes it. What is worn is read the way
  # the desktop reads it, the user's file and then the global theme's layer under it, rather than
  # grepped out of one file that may not say -- and an empty answer is safe, because that layer
  # never names this one.
  if [[ -e "$THEMES/kyprx-panel" ]]; then
    if [[ "$(kreadconfig6 --file plasmarc --group Theme --key name 2>/dev/null || true)" == "kyprx-panel" ]]; then
      say "  $THEMES/kyprx-panel is left in place: the desktop is wearing it. Pick any preset on"
      say "  the Appearance tab to move off it, and the next install removes it"
    else
      do_it "rm -rf '$THEMES/kyprx-panel'"
      (( DRY )) || say "  removed $THEMES/kyprx-panel, which nothing reads now"
    fi
  fi
  # The schemes are copies, and here a copy is the point rather than a concession. A colour scheme
  # is meant to be edited -- the desktop's own colour page writes these very files -- so one
  # already in place is somebody's, and is never overwritten.
  do_it "mkdir -p '$SCHEMES'"
  kept=0; added=0
  for scheme in "$HERE"/share/color-schemes/*.colors; do
    name=$(basename "$scheme")
    if [[ -e "$SCHEMES/$name" ]]; then kept=$((kept + 1)); continue; fi
    do_it "cp '$scheme' '$SCHEMES/$name'"
    added=$((added + 1))
  done
  say "  $SCHEMES: $added added, $kept left exactly as they were"

  step "switching the script on and making it re-read itself"
  # Switching it on is not enough on a re-install, where the key is already true and the
  # compositor therefore does nothing -- and an action added to the compositor script would not
  # exist until the next logout, with nothing saying so.
  #
  # Nor is flipping the key off and on: the compositor acts on the key only when a reconfigure
  # runs, 200 ms after it is asked, so a key back on by then reloads nothing (daemon/reload.py has
  # the finding). `unloadScript` is the part it only does when asked; one `reconfigure` afterwards
  # loads every enabled script back, this one included.
  #
  # Loaded back is not read again, though, once the session has read it. The script is
  # declarative, and KWin runs every declarative script in the one QML engine it keeps for the
  # whole session, which holds on to what it compiled from each file -- the QML and its modules
  # alike -- and never reads them again. So this step reads the script's files only in a session
  # that has not loaded it yet (a first install, or one over a KyprX whose script was JavaScript),
  # and a change to them takes effect at the next login; the message at the end says so.
  do_it "kwriteconfig6 --file kwinrc --group Plugins --key ${PLUGIN_ID}Enabled true"
  do_it "busctl --user call org.kde.KWin /Scripting org.kde.kwin.Scripting unloadScript s '${PLUGIN_ID}' >/dev/null 2>&1 || true"
  do_it "busctl --user call org.kde.KWin /KWin org.kde.KWin reconfigure >/dev/null 2>&1 || true"
  say "  kwinrc [Plugins] ${PLUGIN_ID}Enabled=true, and the script re-read so its shortcuts exist"
  do_it "wait_until_the_script_is_loaded"

  (( DRY )) && return 0
  [[ -n "$FROM" ]] && return 0  # an update says its own last words (`after_update`)
  echo
  say "done. Open KyprX from the menu, or run 'kyprx'."
  say
  say "To try everything out without writing anything, close the interface first:"
  say "  systemctl --user stop kyprd"
  say "  kyprd --dry-run &"
  say "  kyprx"
  say
  say "To restart it normally:  systemctl --user restart kyprd"
  say
  say "If KyprX was already running, restart it that way now: until then the daemon keeps its old"
  say "code."
  say "A change to the compositor script takes effect only after logging out and back in: KWin"
  say "keeps a declarative script's code cached for the whole session."
}

# ---------------------------------------------------------------- update

#: daemon/update.py fetches the code -- a fast-forward for a clone, the newest release unpacked
#: beside a release folder -- and prints the folder to install from, or nothing. That folder's own
#: installer then runs, the new version's, told where the update came from. `exec`, because bash
#: reads a script while it runs it, and a pull may just have rewritten this one.
update_all() {
  (( EUID != 0 )) || die "run the update as yourself, not as root: KyprX lives in your own folders"
  local from next
  from=$(cat "$HERE/VERSION" 2>/dev/null || true)
  step "the newest version"
  if (( DRY )); then
    next=$(python3 "$HERE/daemon/update.py" fetch --dry-run) || exit 1
  else
    next=$(python3 "$HERE/daemon/update.py" fetch) || exit 1
  fi
  if [[ -z "$next" ]]; then
    say "  nothing to update"
    return 0
  fi
  local hand=(--updated-from "${from:-unknown}")
  [[ "$(realpath -m "$next")" == "$(realpath -m "$HERE")" ]] || hand+=(--previous-tree "$HERE")
  if (( DRY )); then
    do_it "bash $(printf '%q ' "$next/install.sh" "${hand[@]}")"
    do_it "systemctl --user try-restart kyprd"
    return 0
  fi
  exec bash "$next/install.sh" "${hand[@]}"
}

#: The end of an update, in the new version's installer: `try-restart` starts nothing that was not
#: running -- the next call to KyprX's bus name starts the new version -- and what is left to do.
after_update() {
  local now
  now=$(cat "$HERE/VERSION" 2>/dev/null || true)
  step "restarting KyprX's background service"
  # Not ignored, unlike a stop: this is where the new version first runs, and a background service
  # that does not start again on it is an update that did not take, whatever came before it.
  do_it "systemctl --user try-restart kyprd" ||
    die "KyprX's background service did not start again on the new version: journalctl --user -u kyprd says why"
  (( DRY )) && return 0
  echo
  say "KyprX is updated from $FROM to ${now:-this version}, and your setup is kept."
  say "A KyprX window opened with its key has closed: open it again. One opened from the menu"
  say "asks to be closed and opened again."
  say "KyprX's part inside the compositor is the new version from the next login: log out and"
  say "back in. Until then it tiles as it did."
  if [[ -n "$PREVIOUS" ]]; then
    say "Nothing of KyprX runs from $PREVIOUS any more: delete it when you like."
  fi
  return 0
}

# ---------------------------------------------------------------- uninstall

uninstall_all() {
  # The Settings tab's removal comes first, and only it can: what it takes back -- the tiling's
  # settings, KyprX's keys in the shortcut registry, the overlays' rules, and KDE as KDE has it when
  # asked -- is done by the daemon this script is about to remove, and the docs saying "button
  # first" stopped nobody: run alone, this left all of it, with Meta+/, Meta+K, Meta+R, Meta+T and
  # the tiling's keys still taken by actions nothing would ever run again. The daemon keeps what it
  # remembers about this machine in ~/.local/state/kyprx/ whatever XDG_STATE_HOME says
  # (KNOWN-ISSUES.md), and that removal deletes the folder: finding it means it has not run, or that
  # KyprX was opened again since, which brings back what it took away.
  local settled=1
  [[ -e "$HOME/.local/state/kyprx" ]] && settled=0
  if (( ! settled && ! FORCE )); then
    say "KyprX's settings are still on this desk ($HOME/.local/state/kyprx/ is there)."
    say "Start with 'Remove KyprX from this computer…', at the bottom of KyprX's Settings tab: it"
    say "asks whether KDE goes back as KDE has it and whether your KyprX folder stays, takes back"
    say "what only KyprX used, and then gives you this command. To remove only the files this"
    say "script put in place and leave everything else as it is, run it again with --force."
    (( DRY )) || exit 1
    say
    say "-- dry run: what removing the files would do, all the same --"
  fi

  step "switching the script off"
  # `unloadScript` is what takes it out of the running compositor at once: the reconfigure
  # unloads a script switched off only once it runs, 200 ms after it is asked (daemon/reload.py
  # has the finding). The switch is deleted
  # rather than set to false: with no key the script is off, and nothing of this app's is left in
  # kwinrc -- the same as the daemon does when KyprX is removed from the Settings tab.
  do_it "kwriteconfig6 --file kwinrc --group Plugins --key ${PLUGIN_ID}Enabled --delete"
  do_it "busctl --user call org.kde.KWin /Scripting org.kde.kwin.Scripting unloadScript s '${PLUGIN_ID}' >/dev/null 2>&1 || true"
  do_it "busctl --user call org.kde.KWin /KWin org.kde.KWin reconfigure >/dev/null 2>&1 || true"

  step "removing the links and files"
  do_it "systemctl --user stop kyprd 2>/dev/null || true"
  for target in "$KWIN_SCRIPT" "$BIN/kyprd" "$BIN/kyprx" \
                "$SERVICES/org.cyberbessa.KyprX.service" "$UNITS/kyprd.service" \
                "$APPS/kyprx.desktop" "$APPS/kyprx-cheatsheet.desktop" \
                "$APPS/kyprx-wallpaper.desktop"; do
    [[ -e "$target" || -L "$target" ]] || continue
    do_it "rm -f '$target'"
    (( DRY )) || say "  removed $target"
  done
  removed=0
  while read -r icon; do
    [[ -e "$ICONS/$icon" || -L "$ICONS/$icon" ]] || continue
    do_it "rm -f '$ICONS/$icon'"
    removed=$((removed + 1))
  done < <(icon_files)
  while read -r link; do do_it "rm -f '$link'"; removed=$((removed + 1)); done < <(stale_icon_links)
  (( removed )) && icon_cache
  (( removed && ! DRY )) && say "  removed the icon, $removed files, from $ICONS/hicolor"

  [[ -L "$THEMES/kyprx" || -e "$THEMES/kyprx" ]] && do_it "rm -rf '$THEMES/kyprx'"
  # And the second style an earlier version kept beside it, when it is still there.
  [[ -e "$THEMES/kyprx-panel" ]] && do_it "rm -rf '$THEMES/kyprx-panel'"
  [[ -e "$DATA" ]] && do_it "rm -rf '$(dirname "$DATA")'"
  [[ -e "$ENV_SCRIPT" ]] && do_it "rm -f '$ENV_SCRIPT'"
  # Two files the desktop writes in KyprX's name (`STATE_CONFIG` and `STYLE_CACHE` in
  # daemon/kyprd_installation.py say what and why): what KDE's file dialog remembers for KyprX, and
  # the shell's cache of KyprX's panel style. The Settings tab's removal takes the cache only while
  # the panel is not wearing the style; its files are gone now, so it goes here either way.
  for owned in "${XDG_STATE_HOME:-$HOME/.local/state}/KyprXstaterc" \
               "${XDG_CACHE_HOME:-$HOME/.cache}/plasma_theme_kyprx.kcache"; do
    [[ -e "$owned" ]] && do_it "rm -f '$owned'"
  done
  # Only the ones still what was installed. A scheme somebody has since tuned is theirs, and taking
  # it away with the app would be taking away their work. Compared with the comment lines left out:
  # the licence notice at the head of each file arrived after some of them were installed, and a
  # copy that differs from this one by nothing but that notice is still exactly what was put there.
  tuned=0
  for scheme in "$HERE"/share/color-schemes/*.colors; do
    name=$(basename "$scheme")
    [[ -e "$SCHEMES/$name" ]] || continue
    if cmp -s <(grep -v '^#' "$scheme") <(grep -v '^#' "$SCHEMES/$name"); then
      do_it "rm -f '$SCHEMES/$name'"
    else tuned=$((tuned + 1)); fi
  done
  (( tuned )) && say "  left $tuned colour scheme(s) in $SCHEMES that had been edited"

  do_it "update-desktop-database '$APPS' >/dev/null 2>&1 || true"
  do_it "systemctl --user daemon-reload"
  do_it "busctl --user call org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus ReloadConfig >/dev/null 2>&1 || true"

  echo
  if (( DRY )); then
    say "-- dry run: nothing was removed --"
    return 0
  fi
  say "This removed the files this script put in place, and nothing it did not."
  if (( settled )); then
    say "What 'Remove KyprX from this computer…' leaves on purpose stays: the desktops KyprX's"
    say "tiling made, as ordinary desktops; the keys KyprX took from other actions, which are left"
    say "without one -- System Settings, Shortcuts, gives them back; and, when you chose to leave"
    say "the desktop as it was, the look and window behaviour KyprX gave it."
  else
    say "KyprX's settings were still on this desk, and stay: the window rules and decoration"
    say "overrides KyprX wrote are still in effect, its tiling's settings and its keys stay in"
    say "kwinrc and in the desktop's shortcut list, your setup stays in ~/.config/kyprx/, and what"
    say "it remembered about this machine in ~/.local/state/kyprx/ and ~/.cache/kyprx/. To take"
    say "those back, install KyprX again and use 'Remove KyprX from this computer…' first."
  fi
  say
  say "KyprX tiled the windows itself, so KyprX tiles none of them now."
}

# ---------------------------------------------------------------- main

while (( $# )); do
  case "$1" in
    --dry-run)       DRY=1 ;;
    --uninstall)     MODE=uninstall ;;
    --force)         FORCE=1 ;;
    --update)        MODE=update ;;
    # Every older version's `update_all` hands the two below to this installer, the newest: they
    # are kept as they are, or each update from an older KyprX stops at "unknown argument" with
    # its new code already in place (docs/modules/installer.md, "Why it is this way").
    --updated-from)  (( $# > 1 )) || die "--updated-from needs a version"; FROM=$2; shift ;;
    --previous-tree) (( $# > 1 )) || die "--previous-tree needs a folder"; PREVIOUS=$2; shift ;;
    -h|--help)       sed -n '2,23p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done

(( FORCE )) && [[ "$MODE" != uninstall ]] && die "--force goes with --uninstall"
(( DRY )) && say "-- dry run: nothing will be written --"
"${MODE}_all"
# An `if`, not `&&`: as the last command, a false test would be the script's exit status.
if [[ "$MODE" == install && -n "$FROM" ]]; then after_update; fi
