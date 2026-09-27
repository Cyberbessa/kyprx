# Geometry Change, the window animation KyprX switches on, for Fedora: a package of JavaScript for
# KWin, so nothing is compiled and nothing has to follow KWin's version. Built in KyprX's own COPR
# because no Fedora repository carries it. The same name, source and layout as the AUR's
# kwin-effects-geometry-change.

%global effect  kwin4_effect_geometry_change

Name:           kwin-effects-geometry-change
Version:        1.5
Release:        1%{?dist}
Summary:        A KWin animation for windows moved or resized by programs or scripts

License:        GPL-3.0-or-later
URL:            https://github.com/peterfajdiga/%{effect}
Source0:        %{url}/releases/download/v%{version}/%{effect}_%(echo %{version} | tr . _).tar.gz
Source1:        https://raw.githubusercontent.com/peterfajdiga/%{effect}/v%{version}/LICENSE

BuildArch:      noarch
Requires:       kwin

%description
Geometry Change animates windows that are moved or resized by programs or by
scripts, such as a tiling script, the way KWin already animates windows moved
by hand.

%prep
%setup -q -c
cp -p %{SOURCE1} .

%build

%install
install -d %{buildroot}%{_datadir}/kwin/effects/%{effect}
cp -r %{effect}/* %{buildroot}%{_datadir}/kwin/effects/%{effect}/
find %{buildroot}%{_datadir}/kwin/effects/%{effect} -type d -exec chmod 0755 {} +
find %{buildroot}%{_datadir}/kwin/effects/%{effect} -type f -exec chmod 0644 {} +

%files
%license LICENSE
%{_datadir}/kwin/effects/%{effect}/

%changelog
* Fri Sep 25 2026 cyberbessa <grdz441yj@mozmail.com> - 1.5-1
- First package, for KyprX.
