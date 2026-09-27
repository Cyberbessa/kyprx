# Written by KyprX's install.sh, and removed by `install.sh --uninstall`. Sourced by the desktop at
# the start of every session, before anything of Plasma's is running -- which is why it takes a
# logout to begin to matter.
#
# One more place for the session to look for data, spelled without a single symbolic link in it.
# The Plasma style this app ships has a colours file whose whole point is to be *found* -- the shell
# asks every theme directory for it on every item it draws and never remembers a miss -- and to
# carry no palette, so the panel follows the colour scheme live. Found through a link it does the
# first and not the second: the two libraries that read it each get a config object of their own
# (the name is canonicalised on open and compared as asked for), and only one of them is re-read
# when the scheme changes, so the panel's background froze on the palette it had. On this desktop
# the home directory itself is reached through a link, so nothing under it can be that file's
# home. This directory can. See MAP.md in the repository, and scripts/probe.py --follow.
export XDG_DATA_DIRS="@DATA@:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
