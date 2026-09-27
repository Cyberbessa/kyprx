# Smart Video Wallpaper Reborn, the video wallpaper plugin KyprX drives, for Fedora. KyprX needs
# 2.15.0 or newer (wallpaper.VIDEO_PLUGIN_FIXED), and Fedora's own package and its author's
# repository both carry older ones, so KyprX's COPR builds it -- under Fedora's own name, so that a
# newer one from either supersedes this one when it arrives. Built without the optional compiled
# part (BUILD_PLUGIN, the Day-Night cycle), which KyprX does not use: what is left is QML, noarch,
# and does not have to follow Plasma's version -- the same as the release tarball.

%global plugin  luisbocanegra.smart.video.wallpaper.reborn

Name:           plasma-smart-video-wallpaper-reborn
Version:        2.15.0
Release:        1%{?dist}
Summary:        Plasma 6 wallpaper plugin to play videos on the desktop

License:        GPL-2.0-or-later
URL:            https://github.com/luisbocanegra/plasma-smart-video-wallpaper-reborn
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  cmake
BuildRequires:  extra-cmake-modules
BuildRequires:  gettext
BuildRequires:  cmake(KF6I18n)
BuildRequires:  cmake(Plasma)
# Asked for by Plasma's own CMake configuration, and not pulled in by it (measured: the build
# stops without it).
BuildRequires:  cmake(KF6CoreAddons)
Requires:       plasma-workspace
Requires:       qt6-qtmultimedia

%description
A wallpaper plugin for KDE Plasma 6 that plays videos on the desktop and the
lock screen, pausing them when windows cover the desktop, when on battery, or
on a schedule.

%prep
%autosetup -n %{name}-%{version}

%build
%cmake -DBUILD_PLUGIN=OFF
%cmake_build

%install
%cmake_install
chmod 0755 %{buildroot}%{_datadir}/plasma/wallpapers/%{plugin}/contents/ui/tools/gdbus_get_signal.sh

%files
%license LICENSE
%{_datadir}/plasma/wallpapers/%{plugin}/
%{_datadir}/locale/*/LC_MESSAGES/*.mo

%changelog
* Fri Sep 25 2026 cyberbessa <grdz441yj@mozmail.com> - 2.15.0-1
- Built for KyprX, which needs 2.15.0 or newer, without the optional compiled part.
