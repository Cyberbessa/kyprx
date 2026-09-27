# How COPR makes a source package from this repository: its "make srpm" method runs this with
# `outdir` and `spec` set. Each spec's sources are fetched from where the spec says -- KyprX's own
# from the release tag on GitHub, the three others from their projects' releases -- and the source
# package is built from them. packaging/README.md has the COPR settings that use it.
spec ?= packaging/fedora/kyprx.spec
outdir ?= $(CURDIR)

srpm:
	dnf -y install rpmdevtools rpm-build
	spectool -g -C $(outdir) $(spec)
	rpmbuild -bs --define "_sourcedir $(outdir)" --define "_srcrpmdir $(outdir)" $(spec)
