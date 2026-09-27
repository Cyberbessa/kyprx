# KyprX for Fedora, and for the Fedora systems that update as a whole (rpm-ostree). Built in COPR
# from the tag in the public repository; packaging/README.md says how, and how a release is made.
#
# The five projects KyprX is built on are required: KyprX is those five put to one use. Two are
# compiled against one version of KWin and are rebuilt for each by the repositories that carry
# them, which the COPR project names as its runtime dependencies (packaging/README.md), so enabling
# KyprX's repository offers to enable theirs. The other three are noarch: Krohnkite and Geometry
# Change are built in KyprX's own COPR (the two specs beside this one), the video plugin comes from
# its author's repository.

Name:           kyprx
Version:        0.1.0
Release:        1%{?dist}
Summary:        KDE-Native Hyprland Experience

# The code is GPL-3.0-or-later; the eleven colour schemes and the Plasma style's plasmarc copy
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
Requires:       kwin-scripts-krohnkite
Requires:       kwin-effects-geometry-change
Requires:       plasma-smart-video-wallpaper-reborn >= 2.15.0
# Thumbnails of video wallpapers, and a colour taken from a video. Everything else works without.
Recommends:     /usr/bin/ffmpeg

%description
KyprX gives KDE Plasma 6 on Wayland the look of a tiling window manager:
windows side by side, with no title bars, an outline, a see-through background
and blur behind them. It gathers in one window the settings of Klassy, Better
Blur DX, Krohnkite, Geometry Change and Smart Video Wallpaper Reborn, and adds
colour presets, profiles, a wallpaper picker and a shortcut cheatsheet.

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
* Sun Sep 27 2026 cyberbessa <grdz441yj@mozmail.com> - 0.1.0-1
- First package.
