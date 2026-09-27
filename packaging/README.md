# Packaging

How KyprX is packaged for Fedora (COPR) and for Arch (the AUR), what has to be set up once on each
service, and what a release is. What a package installs, and where, is in the table
What a package installs.

| File | What it is |
|---|---|
| `packaging/stage.sh` | lays KyprX out under a prefix, the way both recipes install it |
| `packaging/fedora/kyprx.spec` | KyprX's own RPM |
| `packaging/fedora/kwin-scripts-krohnkite.spec` | Krohnkite, built in KyprX's COPR: no Fedora repository its author keeps carries it |
| `packaging/fedora/kwin-effects-geometry-change.spec` | Geometry Change, for the same reason |
| `packaging/fedora/plasma-smart-video-wallpaper-reborn.spec` | the video plugin at 2.15.0, which KyprX needs and Fedora's own package and its author's repository do not yet carry; under Fedora's name, so a newer one supersedes it |
| `.copr/Makefile` | how COPR makes a source package from this repository |
| `packaging/arch/PKGBUILD` | KyprX's AUR package |
| `packaging/public/README.md` | the public repository's `README.md`: its front page, with the badges and the Ko-fi button |
| `packaging/public/.github/FUNDING.yml` | what puts the *Sponsor* button, to Ko-fi, on the public repository's page |
| `packaging/public/screenshots/` | what the public README shows: the settings window's seven tabs as PNGs (`tab-<tab>.png`), and four screen recordings as animated AVIF -- the wallpaper picker, a wallpaper's colour taken by the desktop, transparency and the cheatsheet -- referenced from the README as `screenshots/<name>` |

The five projects KyprX is built on are required by both packages. Two of them are compiled
against one version of KWin, and KyprX never builds those: the repositories that carry them
rebuild them for each Plasma release, which is work that has to follow Plasma's calendar.

## The repositories KyprX depends on

On Fedora, KyprX's COPR names these as its runtime dependencies, so `dnf copr enable` offers to
enable them too. On a system that updates as a whole, whose repositories are added by hand, the
same ones are added the same way.

| Project | Repository | Where it comes from |
|---|---|---|
| Klassy | `https://download.opensuse.org/repositories/home:/paulmcauley/Fedora_$releasever/` | its author's own repository, on the openSUSE build service |
| Better Blur DX | `copr://infinality/kwin-effects-better-blur-dx` | a COPR that rebuilds it for each Plasma release |
| Krohnkite, Geometry Change, the video plugin | KyprX's own COPR | the three specs here |

## Once: the COPR project

The project is `cyberbessa/kyprx`, and it is set up like this; `copr-cli`, with the API token from
copr.fedorainfracloud.org/api saved as `~/.config/copr`, does every step from a terminal.

1. A Fedora account, and in COPR a project named `kyprx`, with the chroots of the Fedora releases
   where both Klassy and Better Blur DX are built -- `fedora-43` and `fedora-44`, each for `x86_64`
   and `aarch64`. Klassy's repository has no Fedora 45 yet and Better Blur DX's has no Rawhide, and
   a chroot where either is missing would offer a KyprX nobody can install. *Follow Fedora
   branching* is ticked, and *AppStream metadata* is on, so software centres find KyprX.
2. In the project's settings, *Runtime dependencies*: the Klassy and Better Blur DX lines of the
   table above. Measured: the repository file COPR serves carries both as sections of their own,
   enabled, and `dnf copr enable` enables them together with KyprX's.
3. Four packages, each with the source type *SCM*: the clone URL
   `https://github.com/Cyberbessa/kyprx` -- spelled the way GitHub spells the account, capital C
   included -- the spec file `packaging/fedora/<package>.spec`, and the SRPM build method *make
   srpm*, which runs `.copr/Makefile`.
4. For `kyprx`, *Auto-rebuild* on, with the GitHub webhook COPR's *Integrations* page gives,
   registered on the public repository for its *push* and *create* events. What COPR does with them
   was read in its code (`webhooks_general.py`, `packages_logic.py`) and then seen: it rebuilds a
   package when a push brings a commit, and only when the package's clone URL is the one in the
   push **letter for letter** -- with `cyberbessa` in lower case the push was accepted and nothing
   was built. A tag alone rebuilds nothing, because COPR takes a tag as `kyprx-0.1.0`, not `v0.1.0`;
   each release reaches the public repository as a commit, so the push is what builds it.
   `copr-cli new-webhook-secret kyprx` makes a new secret -- it asks for a yes first, and prints
   `Generated new token:` -- and the webhook on GitHub has to be given it. The three others are
   rebuilt by hand, when their spec changes.

## Once: the AUR package

An AUR account with an SSH key, then a clone that commits under the maintainer's public name and
address -- the AUR's history is public, and a commit takes the machine's own git identity
otherwise:

```sh
git clone ssh://aur@aur.archlinux.org/kyprx.git
git -C kyprx config user.name cyberbessa
git -C kyprx config user.email grdz441yj@mozmail.com
```

Every AUR dependency of KyprX's -- `klassy`, `kwin-effects-better-blur-dx`,
`kwin-scripts-krohnkite`, `kwin-effects-geometry-change`,
`plasma6-wallpapers-smart-video-wallpaper-reborn` -- is somebody else's package, kept by them.

## A release

1. On the private repository, the version is raised everywhere it is written: `VERSION`, the
   spec's `Version` and a `%changelog` entry, the PKGBUILD's `pkgver`, and a `<release>` in
   `share/org.cyberbessa.KyprX.metainfo.xml`. The maintainer's release script does it and tags
   the commit; the dry run checks that the four agree.
2. The release is exported to the public repository as one commit with the same tag, signed with
   the maintainer's public name and address, and pushed. The tag is what COPR builds from.
3. In the AUR clone: the new `PKGBUILD`, its checksum filled in (`updpkgsums`), and a new
   `.SRCINFO` (`makepkg --printsrcinfo > .SRCINFO`), committed and pushed. Both commands need an
   Arch system; a container is enough.
4. On the GitHub release, that `PKGBUILD`, checksum filled in. Until KyprX is in the AUR it is
   how Arch installs it -- `paru -Ui` in a folder holding it builds KyprX and brings the five from
   the AUR, `kwin-scripts-krohnkite-git` installed first while Krohnkite's own package fails its
   checksum -- and the install guide points at `releases/latest/download/PKGBUILD`, so a release
   without it breaks that line. Measured on a clean Arch: `paru -Ui` installed it with all five,
   and `makepkg -si` did with the five present. No built package goes beside it: it would carry
   KyprX's files and none of the five -- Klassy and Better Blur DX are built against one KWin and
   cannot travel prebuilt -- so it would install only where they already are.

A new version of one of the three projects built here is a new `Version` in its spec, a
`%changelog` entry, and a rebuild of that package in COPR.

## The screenshots

The tabs are PNGs as Spectacle saved them, window and shadow on a transparent background. The four
recordings are animated AVIF, made from Spectacle's WebM whole and unedited, at 2560 pixels wide
and 60 frames a second: 2.2 to 4.4 MB each, 14 MB for the four.

**An image, because a page on GitHub does not play a video file kept in the repository**, and it
does show an image: GitHub serves `.avif` as `image/avif`, as it serves `.png` and `.webp`
(measured, from `raw.githubusercontent.com`). **AVIF and not animated WebP**, because an animated
WebP stores each frame on its own, and with a video wallpaper moving behind the windows every frame
is new: to stay near 2 MB a clip, the WebPs had to be 1280 pixels wide at 15 frames a second and
quality 55, and the text in them came out visibly smeared. AVIF is AV1, which codes a frame from the
ones around it; at 2560 pixels and 60 frames a second its frames are, side by side, the recording's
own. Current Firefox, Chrome and Safari play it; a browser that cannot shows the first frame. A new
recording goes the same way:

```sh
ffmpeg -i recording.webm -vf "fps=60,scale=2560:-2:flags=lanczos" \
  -c:v libsvtav1 -preset 6 -crf 28 -pix_fmt yuv420p -f avif packaging/public/screenshots/<name>.avif
```

## Building locally

Both recipes can be built from a tarball of the tree, in throwaway containers, without touching
the machine they run on:

```sh
git archive --prefix=kyprx-0.1.0/ -o kyprx-0.1.0.tar.gz HEAD
podman run --rm -v "$PWD":/src:ro,z registry.fedoraproject.org/fedora:44 bash -c '
  dnf -y install rpm-build rpmdevtools python3-devel systemd-rpm-macros desktop-file-utils appstream
  mkdir -p ~/rpmbuild/SOURCES && cp /src/kyprx-0.1.0.tar.gz ~/rpmbuild/SOURCES/
  rpmbuild -ba /src/packaging/fedora/kyprx.spec'
```

On Arch the same with `makepkg -d` in a copy of `packaging/arch/` whose `source` points at the
tarball: `-d` because the AUR dependencies are not in Arch's own repositories.
