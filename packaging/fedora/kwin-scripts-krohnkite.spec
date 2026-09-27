# Krohnkite, the tiling script KyprX is built on, for Fedora: a package of JavaScript for KWin, so
# nothing is compiled and nothing has to follow KWin's version. Built in KyprX's own COPR because
# no Fedora repository its author keeps carries it. The same name, source and layout as the AUR's
# kwin-scripts-krohnkite. A new version is a new Version here and a rebuild (packaging/README.md).

%global script  krohnkite

Name:           kwin-scripts-krohnkite
Version:        0.9.9.2
Release:        1%{?dist}
Summary:        A dynamic tiling script for KWin

License:        MIT
URL:            https://codeberg.org/anametologin/Krohnkite
Source0:        %{url}/releases/download/%{version}/%{script}.kwinscript
Source1:        %{url}/archive/%{version}.tar.gz#/%{script}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  bsdtar
Requires:       kwin

%description
Krohnkite tiles windows automatically in KWin, the window manager of KDE Plasma
6: a dynamic tiling script in the manner of dwm, with several layouts and
keyboard shortcuts for each action.

%prep
%setup -q -c -T
bsdtar -xf %{SOURCE1}

%build

%install
install -d %{buildroot}%{_datadir}/kwin/scripts/%{script}
bsdtar --no-same-owner -xf %{SOURCE0} -C %{buildroot}%{_datadir}/kwin/scripts/%{script}
find %{buildroot}%{_datadir}/kwin/scripts/%{script} -type d -exec chmod 0755 {} +
find %{buildroot}%{_datadir}/kwin/scripts/%{script} -type f -exec chmod 0644 {} +

%files
%license %{script}/LICENSE
%{_datadir}/kwin/scripts/%{script}/

%changelog
* Fri Sep 25 2026 cyberbessa <grdz441yj@mozmail.com> - 0.9.9.2-1
- First package, for KyprX.
