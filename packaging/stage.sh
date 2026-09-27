#!/usr/bin/env bash
# Lay KyprX out as a system package installs it: under PREFIX, inside DESTDIR.
#
# Both package recipes call this, so the Fedora package and the Arch one install the same files in
# the same places; MAP.md has the table. It copies and nothing else. It never touches the session
# that runs it -- no unit reloaded, no compositor asked anything, no config written -- because a
# package is built on a machine that is not the one it is installed on, and installed as root for
# every user of that one. What a user's own session needs once, switching the compositor script
# on, the daemon does the first time KyprX is opened (`Daemon.switch_the_script_on`).
#
# How it differs from install.sh, which puts KyprX in one user's home folder:
#   - everything is a copy: a package owns its files, and there is no working tree to link to;
#   - the Plasma style keeps its `colors` file inside it. install.sh keeps that file apart, in a
#     folder spelled with every link resolved, because under the home folder a link was measured
#     to freeze the panel's colours (see the comment in install.sh). Nothing under PREFIX is
#     reached through a link, so the file stays where Plasma looks first, and the session needs no
#     environment script to find it;
#   - the colour schemes are installed whole: KDE's Colours page saves an edited scheme in the
#     user's own folder and never writes these.
#
# Usage: packaging/stage.sh DESTDIR [PREFIX]    PREFIX defaults to /usr
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
(( $# >= 1 )) || { sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; exit 2; }
DESTDIR="$1"
PREFIX="${2:-/usr}"
[[ "$PREFIX" == /* ]] || { echo "error: PREFIX must be an absolute path: $PREFIX" >&2; exit 2; }

ROOT="$DESTDIR$PREFIX"
CODE="$ROOT/share/kyprx"

put() {  # put MODE SOURCE TARGET -- a copy with the mode given, its folder made first
  install -D -m "$1" "$2" "$3"
}

# The code, laid out the way it is in the working tree: `daemon/`, `gui/`, and at the top the two
# files the code finds through its own real path -- VERSION (daemon/about.py) and CREDITS.md (the
# Settings tab's Credits box). The two entry files keep their execute bit; the links in bin/ are
# what runs them.
for f in "$HERE"/daemon/*.py "$HERE"/gui/*.py; do
  rel=${f#"$HERE"/}
  case "$rel" in
    daemon/kyprd.py|gui/kyprx.py) put 0755 "$f" "$CODE/$rel" ;;
    *)                            put 0644 "$f" "$CODE/$rel" ;;
  esac
done
put 0644 "$HERE/VERSION" "$CODE/VERSION"
put 0644 "$HERE/CREDITS.md" "$CODE/CREDITS.md"

# Relative links, so they point at the right file both here, inside DESTDIR, and once installed.
install -d -m 0755 "$ROOT/bin"
ln -sfn ../share/kyprx/daemon/kyprd.py "$ROOT/bin/kyprd"
ln -sfn ../share/kyprx/gui/kyprx.py "$ROOT/bin/kyprx"

# The files that name the program by its path: the unit, the D-Bus activation file and the three
# desktop entries, each with the installed bin/ written in where install.sh writes ~/.local/bin.
fill() {  # fill SOURCE TARGET
  install -d -m 0755 "$(dirname "$2")"
  sed "s|@BIN@|$PREFIX/bin|g" "$1" > "$2"
  chmod 0644 "$2"
}
fill "$HERE/share/kyprd.service" "$ROOT/lib/systemd/user/kyprd.service"
fill "$HERE/share/org.cyberbessa.KyprX.service" "$ROOT/share/dbus-1/services/org.cyberbessa.KyprX.service"
for entry in kyprx kyprx-cheatsheet kyprx-wallpaper; do
  fill "$HERE/share/$entry.desktop" "$ROOT/share/applications/$entry.desktop"
done

# The icon, at the same relative paths install.sh links it at.
(cd "$HERE/share/icons" && find hicolor -type f) | while read -r icon; do
  put 0644 "$HERE/share/icons/$icon" "$ROOT/share/icons/$icon"
done

# The compositor script, under the id its folder has to carry.
(cd "$HERE/kwin-script" && find . -type f) | while read -r file; do
  put 0644 "$HERE/kwin-script/$file" "$ROOT/share/kwin/scripts/kyprx/${file#./}"
done

# The Plasma style, whole: metadata.json, plasmarc and colors. See the top of this file.
for file in metadata.json plasmarc colors; do
  put 0644 "$HERE/share/desktoptheme/kyprx/$file" "$ROOT/share/plasma/desktoptheme/kyprx/$file"
done

for scheme in "$HERE"/share/color-schemes/*.colors; do
  put 0644 "$scheme" "$ROOT/share/color-schemes/$(basename "$scheme")"
done

# What a software centre shows for KyprX.
put 0644 "$HERE/share/org.cyberbessa.KyprX.metainfo.xml" "$ROOT/share/metainfo/org.cyberbessa.KyprX.metainfo.xml"
