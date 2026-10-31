# KyprX for Fedora, and for the Fedora systems that update as a whole (rpm-ostree). Built in COPR
# from the tag in the public repository; packaging/README.md says how, and how a release is made.
#
# The four projects KyprX is built on are required: KyprX is those four put to one use, and tiles
# the windows itself, so no tiling script is among them. Two are compiled against one version of
# KWin and are rebuilt for each by the repositories that carry them, which the COPR project names
# as its runtime dependencies (packaging/README.md), so enabling KyprX's repository offers to
# enable theirs. The other two, Geometry Change and the video plugin, are noarch and built in
# KyprX's own COPR (the two specs beside this one).

Name:           kyprx
Version:        0.3.0
Release:        1%{?dist}
Summary:        KDE-Native Hyprland Experience

# The code is GPL-3.0-or-later; the twelve colour schemes and the Plasma style's plasmarc copy
# blocks of Klassy's files and keep Klassy's licence; the software centre's metadata is CC0-1.0
# (REUSE.toml, CREDITS.md).
License:        GPL-3.0-or-later AND LGPL-2.0-or-later AND CC0-1.0
URL:            https://github.com/cyberbessa/kyprx
Source0:        %{url}/archive/refs/tags/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  systemd-rpm-macros
BuildRequires:  desktop-file-utils
BuildRequires:  appstream

Requires:       python3
Requires:       python3-pyside6
Requires:       python3-dbus
Requires:       python3-gobject
Requires:       gdk-pixbuf2
Requires:       kwin
Requires:       plasma-workspace
Requires:       kf6-kconfig
Requires:       hicolor-icon-theme
Requires:       klassy
Requires:       kwin-effects-better-blur-dx
Requires:       kwin-effects-geometry-change
Requires:       plasma-smart-video-wallpaper-reborn >= 2.15.0
# Thumbnails of video wallpapers, and a colour taken from a video. Everything else works without.
Recommends:     /usr/bin/ffmpeg

%description
KyprX gives KDE Plasma 6 on Wayland the look of a tiling window manager:
windows side by side, with no title bars, an outline, a see-through background
and blur behind them. It tiles the windows itself, in layouts you draw or pick
from presets, one for each number of windows. It gathers in one window the
settings of the four programs it is built on, Klassy, Better Blur DX, Geometry
Change and Smart Video Wallpaper Reborn, and adds colour presets, profiles, a
wallpaper picker and a shortcut cheatsheet.

Installing it changes nothing on the desktop: KyprX switches itself on the
first time it is opened. Removing it starts on its Settings tab, with "Remove
KyprX from this computer...".

%prep
%autosetup -n %{name}-%{version}

%build
# Nothing to build: Python run from where it is installed.

%install
bash packaging/stage.sh %{buildroot} %{_prefix}
%py_byte_compile %{python3} %{buildroot}%{_datadir}/%{name}

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/*.desktop
appstreamcli validate --no-net %{buildroot}%{_metainfodir}/org.cyberbessa.KyprX.metainfo.xml

%files
%license LICENSE LICENSES/*
%doc README.md
%{_bindir}/kyprd
%{_bindir}/kyprx
%{_datadir}/%{name}/
%{_userunitdir}/kyprd.service
%{_datadir}/dbus-1/services/org.cyberbessa.KyprX.service
%{_datadir}/applications/kyprx.desktop
%{_datadir}/applications/kyprx-cheatsheet.desktop
%{_datadir}/applications/kyprx-wallpaper.desktop
%{_datadir}/icons/hicolor/*/apps/kyprx.*
%{_datadir}/kwin/scripts/kyprx/
%{_datadir}/plasma/desktoptheme/kyprx/
%{_datadir}/color-schemes/KyprX*.colors
%{_metainfodir}/org.cyberbessa.KyprX.metainfo.xml

%changelog
* Sat Oct 31 2026 cyberbessa <grdz441yj@mozmail.com> - 0.3.0-1
- Column boxes for every window, an arrangement per desktop, no freeze past nine tiled windows, and the look left alone at a first start

* Fri Oct 30 2026 cyberbessa <grdz441yj@mozmail.com> - 0.2.1-1
- The Arch install is one line that fish, bash and zsh read alike

* Fri Oct 30 2026 cyberbessa <grdz441yj@mozmail.com> - 0.2.0-1
- KyprX tiles the windows itself, keeps everybody's window rules on Plasma 6.8, and sets a wallpaper per screen

* Tue Oct 20 2026 cyberbessa <grdz441yj@mozmail.com> - 0.1.4-1
- Fixes a crash of KyprX's window on the Shortcuts tab

* Tue Oct 20 2026 cyberbessa <grdz441yj@mozmail.com> - 0.1.3-1
- Fixes for KyprX's own keys, effects switched off in KDE, the wallpaper picker and the settings import

* Sun Oct 04 2026 cyberbessa <grdz441yj@mozmail.com> - 0.1.2-1
- Fixes for transparency at full opacity, the lock and log-out screens, and the wallpaper picker

* Sun Sep 27 2026 cyberbessa <grdz441yj@mozmail.com> - 0.1.1-1
- Post-release fixes for shortcuts, defaults, wallpaper discovery and portability

* Sun Sep 27 2026 cyberbessa <grdz441yj@mozmail.com> - 0.1.0-1
- First package.
