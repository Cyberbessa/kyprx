"""Looking for a new version of KyprX, and bringing a working tree up to it -- only when asked.

*Look for a new version* runs `check`, `install.sh --update` runs `fetch`; nothing runs by itself,
and this is the one place KyprX talks to a network. A package is its package manager's: its
command is said, never run. A clone is fast-forwarded, never merged over changes of its own. A
release folder gets the newest release unpacked beside it; the old one is the user's to delete.
Nothing is removed first: a new version brings the old files up to date (`daemon/migrate.py`).
The daemon never imports this. `KYPRX_LATEST_URL` and `KYPRX_TARBALL_URL` serve a test.
"""

from __future__ import annotations

import gzip
import http.client
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zlib

import about

PACKAGE, CLONE, RELEASE = "package", "clone", "release"
NEWER, CURRENT, UNKNOWN = "newer", "current", "unknown"
LATEST = "https://api.github.com/repos/cyberbessa/kyprx/releases/latest"
TARBALL = "https://github.com/cyberbessa/kyprx/archive/refs/tags/v{version}.tar.gz"
#: A release's tarball is about 20 MB, screenshots included; a download past this is not one.
LIMIT = 200 * 1024 * 1024
#: What every older KyprX checks a newer release for, each by its own copy of this file: a tag
#: shaped `v<n>.<n>.<n>` (`_VERSION` and `TARBALL`, the shape `scripts/release.sh` makes), a
#: tarball under `LIMIT`, everything in one folder named `kyprx-<version>` (GitHub's name for it:
#: the repository and the tag, less its `v`), a `VERSION` there that says that version, and these
#: files. A release that misses one cannot be updated to from any version installed before it.
NEEDED = ("install.sh", "daemon/kyprd.py", "gui/kyprx.py", "kwin-script/metadata.json")
#: The Arch lines of `docs/user-guide/install.md`, held to it by tests/test_update_check.py.
ARCH_LINES = ('build=$(mktemp -d)\n'
              'curl -fL -o "$build/PKGBUILD" '
              'https://github.com/cyberbessa/kyprx/releases/latest/download/PKGBUILD\n'
              '(cd "${build:?}" && paru -Ui)\n'
              'rm -rf "$build"')
_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


class Refused(Exception):
    """An update that cannot go ahead, or a question with no answer, in words."""


def parse_version(text: str) -> tuple[int, ...] | None:
    match = _VERSION.match(text.strip())
    return tuple(int(part) for part in match.groups()) if match else None


def version_at(top: str) -> str:
    try:
        with open(os.path.join(top, "VERSION"), encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def kind(top: str = about.TOP) -> str:
    if about.from_package(top):
        return PACKAGE
    # A clone has a .git folder at its top, a worktree a .git file, a release's tarball neither.
    return CLONE if os.path.lexists(os.path.join(top, ".git")) else RELEASE


def update_command(top: str) -> str:
    return f"{shlex.quote(os.path.join(top, 'install.sh'))} --update"


def package_advice(system_name: str) -> tuple[str, str]:
    """The package manager's command on this system, and what follows it. Said, never run."""
    return {
        about.FEDORA: ("sudo dnf upgrade --refresh kyprx",
                       "If it finds nothing, try again later: the package is built a few minutes "
                       "after the release."),
        about.FEDORA_ATOMIC: ("rpm-ostree upgrade", "Then restart the computer."),
        about.ARCH: (ARCH_LINES, "In bash or zsh. Use makepkg -si in place of paru -Ui if that is "
                                 "how KyprX was installed; nothing is removed first."),
    }.get(system_name, ("update the kyprx package with your system's package manager", ""))


def _stderr(line: str) -> None:
    print(line, file=sys.stderr)


def _read(url: str, timeout: float, accept: str, into=None, limit: int = LIMIT) -> bytes:
    """What `url` holds, returned or written into the open file `into`; a failure is `Refused`."""
    agent = f"KyprX/{version_at(about.TOP) or 'unknown'}"
    request = urllib.request.Request(url, headers={"User-Agent": agent, "Accept": accept})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as reply:
            if into is None:
                return reply.read(limit)
            size = 0
            while chunk := reply.read(1 << 16):
                size += len(chunk)
                if size > limit:
                    raise Refused("the download is far larger than a release of KyprX")
                into.write(chunk)
            return b""
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            raise Refused("GitHub is not answering this network for now; try again in an hour") from e
        raise Refused(f"GitHub answered {e.code} for {url}") from e
    except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
        # HTTPException for http.client's own errors, a body cut short (IncompleteRead) among
        # them: none of them is an OSError.
        raise Refused(f"{url} could not be read: {getattr(e, 'reason', None) or e}") from e


def latest_release(timeout: float = 15) -> str:
    """The newest release's version: "0.1.5" for the tag "v0.1.5"."""
    raw = _read(os.environ.get("KYPRX_LATEST_URL") or LATEST, timeout,
                "application/vnd.github+json", limit=1_000_000)
    try:
        tag = str(json.loads(raw.decode("utf-8")).get("tag_name") or "")
    except (ValueError, AttributeError) as e:
        raise Refused("GitHub's answer about the newest release could not be read") from e
    if parse_version(tag) is None:
        raise Refused(f"the newest release is named {tag or 'nothing'}, which is not a version")
    return tag.removeprefix("v")


def _git(top: str, *args: str, quiet: bool = True, timeout: float = 120):
    """git in `top`; `quiet` never waits for a password nobody is there to type."""
    env = dict(os.environ, LC_ALL="C")
    if quiet:
        env["GIT_TERMINAL_PROMPT"] = "0"
        # Not enough alone: git asks the askpass program the session names -- KDE names
        # ksshaskpass, in systemd's user manager too -- before it asks any terminal, and a password
        # window opens. Measured with `git credential fill`: it ran SSH_ASKPASS with
        # GIT_TERMINAL_PROMPT=0 set, and with a terminal there to ask on as well, and refused once
        # GIT_ASKPASS was set empty, which also keeps git from core.askPass (gitcredentials(7) has
        # the order). SSH_ASKPASS_REQUIRE=never keeps ssh from its own askpass when the user's
        # GIT_SSH_COMMAND, kept below, has no BatchMode.
        env["GIT_ASKPASS"] = ""
        env["SSH_ASKPASS_REQUIRE"] = "never"
        env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    try:
        return subprocess.run(["git", "-C", top, *args], capture_output=True, text=True, env=env,
                              timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        return subprocess.CompletedProcess(["git", *args], 1, "", str(e))


def clone_state(top: str, quiet: bool = True) -> dict:
    """Against the branch it follows, by `ls-remote`, which writes nothing here (a fetch would)."""
    branch = _git(top, "symbolic-ref", "-q", "--short", "HEAD").stdout.strip()
    if not branch:
        return {"state": UNKNOWN, "detail": f"{top} is on no branch", "upstream": ""}
    upstream = _git(top, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").stdout.strip()
    remote = _git(top, "config", f"branch.{branch}.remote").stdout.strip()
    merge = _git(top, "config", f"branch.{branch}.merge").stdout.strip()
    if not (upstream and remote and merge):
        return {"state": UNKNOWN, "detail": f"the branch {branch} follows no remote branch",
                "upstream": ""}
    seen = _git(top, "ls-remote", remote, merge, quiet=quiet, timeout=60)
    theirs = (seen.stdout.split() or [""])[0]
    if seen.returncode != 0 or not theirs:
        why = (seen.stderr.strip().splitlines() or ["it did not answer"])[-1]
        return {"state": UNKNOWN, "detail": f"{upstream} could not be asked: {why}",
                "upstream": upstream}
    head = _git(top, "rev-parse", "HEAD").stdout.strip()
    if theirs == head or _git(top, "merge-base", "--is-ancestor", theirs, "HEAD").returncode == 0:
        return {"state": CURRENT, "detail": f"this working tree has everything {upstream} has",
                "upstream": upstream}
    return {"state": NEWER, "detail": f"{upstream} has changes this working tree does not have",
            "upstream": upstream}


def clone_changes(top: str) -> str:
    # --no-optional-locks: `check` runs this in the background, while somebody may be using git in
    # the same tree, and a plain status refreshes the index under its lock (git-status(1)).
    out = _git(top, "--no-optional-locks", "status", "--porcelain", "--untracked-files=no")
    if out.returncode != 0:
        return "git could not say whether this working tree has changes of its own"
    return "this working tree has changes of its own" if out.stdout.strip() else ""


def _release_blocked(top: str, version: str) -> str:
    parent = os.path.dirname(top)
    target = os.path.join(parent, f"kyprx-{version}")
    if os.path.lexists(target):
        return f"{target} is already there: run its install.sh, or move it away first"
    if not os.access(parent, os.W_OK):
        return f"{parent} cannot be written to"
    return ""


def check(top: str = about.TOP) -> dict:
    """What *Look for a new version* shows. Never raises: what is not known is in `detail`."""
    how, installed = kind(top), version_at(top)
    answer = {"kind": how, "installed": installed, "latest": "", "state": UNKNOWN, "detail": "",
              "command": update_command(top), "then": "", "can_update": False}
    if how == PACKAGE:
        answer["command"], answer["then"] = package_advice(about.system())
    if how == CLONE:
        answer.update(clone_state(top))
        busy = clone_changes(top) if answer["state"] == NEWER else ""
        answer["can_update"] = answer["state"] == NEWER and not busy
        if busy:
            answer["detail"] += f"; {busy}, so it is not updated over them"
        return answer
    try:
        latest = latest_release()
    except Refused as e:
        answer["detail"] = str(e)
        return answer
    mine = parse_version(installed)
    if mine is None:
        answer["detail"] = "this installation does not say which version it is"
        return answer
    answer["latest"] = latest
    if parse_version(latest) > mine:
        answer["state"], answer["detail"] = NEWER, f"KyprX {latest} is out, and this is {installed}"
    else:
        answer["state"], answer["detail"] = CURRENT, f"KyprX {installed} is the newest version"
    if how == RELEASE and answer["state"] == NEWER:
        blocked = _release_blocked(top, latest)
        answer["can_update"] = not blocked
        if blocked:
            answer["detail"] += f"; {blocked}"
    return answer


def fetch(top: str = about.TOP, dry: bool = False, say=None) -> str:
    """The folder to install from, or "" when nothing is newer. A dry run changes nothing."""
    say = say or _stderr
    how = kind(top)
    if how == PACKAGE:
        command, then = package_advice(about.system())
        raise Refused(f"this KyprX came in a package, and its package manager updates it:\n"
                      f"{command}\n{then}".rstrip())
    if how == CLONE:
        return _fetch_clone(top, dry, say, quiet=not (sys.stdin and sys.stdin.isatty()))
    return _fetch_release(top, dry, say)


def _fetch_clone(top: str, dry: bool, say, quiet: bool) -> str:
    stands = clone_state(top, quiet)
    if stands["state"] == UNKNOWN:
        raise Refused(stands["detail"])
    if stands["state"] == CURRENT:
        say(f"  {stands['detail']}")
        return ""
    busy = clone_changes(top)
    if busy:
        raise Refused(f"{busy}: commit them or put them aside, then update again")
    if dry:
        say(f"  would bring {top} up to {stands['upstream']} (git pull --ff-only)")
        return top
    before = _git(top, "rev-parse", "--short", "HEAD").stdout.strip()
    pulled = _git(top, "pull", "--ff-only", "--quiet", quiet=quiet, timeout=600)
    if pulled.returncode != 0:
        why = (pulled.stderr.strip().splitlines() or ["git said nothing"])[-1]
        raise Refused(f"git could not bring the new changes in: {why}")
    after = _git(top, "rev-parse", "--short", "HEAD").stdout.strip()
    if after == before:
        say("  nothing new came in")
        return ""
    say(f"  {top}: {before} -> {after}")
    return top


def _fetch_release(top: str, dry: bool, say) -> str:
    installed = version_at(top)
    mine = parse_version(installed)
    if mine is None:
        raise Refused(f"{top} does not say which version it is: its VERSION file holds none")
    latest = latest_release()
    if parse_version(latest) <= mine:
        say(f"  KyprX {installed} is the newest version")
        return ""
    blocked = _release_blocked(top, latest)
    if blocked:
        raise Refused(blocked)
    target = os.path.join(os.path.dirname(top), f"kyprx-{latest}")
    url = (os.environ.get("KYPRX_TARBALL_URL") or TARBALL).format(version=latest)
    if dry:
        say(f"  would download KyprX {latest} from {url} and unpack it as {target}")
        return target
    if not hasattr(tarfile, "data_filter"):
        raise Refused("unpacking a release safely needs Python 3.12 or later")
    say(f"  downloading KyprX {latest} from {url}")
    work = tempfile.mkdtemp(prefix=".kyprx-update-", dir=os.path.dirname(top))
    try:
        archive = os.path.join(work, "release.tar.gz")
        with open(archive, "wb") as out:
            _read(url, 300, "application/octet-stream", into=out)
        unpack(archive, latest, target, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    say(f"  unpacked as {target}")
    return target


def unpack(archive: str, version: str, target: str, work: str) -> None:
    """Whole or not at all: every member inside `kyprx-<version>/`, the `data` filter for the rest,
    unpacked in `work` and renamed into place only once checked."""
    folder = f"kyprx-{version}"
    try:
        # Read to its end first, where gzip checks the length and the CRC of the whole: tarfile
        # stops at the archive's end marker, short of them. Measured: without this, a download that
        # lost only its last bytes, or had a byte changed, unpacked without a word.
        with gzip.open(archive, "rb") as whole:
            while whole.read(1 << 20):
                pass
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar.getmembers():
                name = member.name.rstrip("/")
                if name != folder and not name.startswith(folder + "/"):
                    raise Refused(f"the release carries {member.name}, outside its folder "
                                  f"{folder}, so nothing of it was unpacked")
            tar.extractall(work, filter="data")
    except (tarfile.TarError, OSError, EOFError, zlib.error) as e:
        # EOFError is gzip's word for a download cut short, zlib.error and BadGzipFile -- an
        # OSError -- for a corrupt one: none is a TarError, and each is a refusal like the rest,
        # the temporary folder removed.
        raise Refused(f"the release could not be unpacked: {e}") from e
    unpacked = os.path.join(work, folder)
    said = version_at(unpacked)
    if said != version:
        raise Refused(f"the release says it is {said or 'no version'}, not {version}")
    for needed in NEEDED:
        if not os.path.isfile(os.path.join(unpacked, needed)):
            raise Refused(f"the release has no {needed}")
    try:
        os.rename(unpacked, target)
    except OSError as e:
        raise Refused(f"the release could not be put at {target}: {e.strerror or e}") from e


def main(argv: list[str]) -> int:
    if argv[:1] == ["check"]:
        answer = check()
        print(json.dumps(answer) if "--json" in argv else answer["detail"])
        return 0
    if argv[:1] == ["fetch"]:
        try:
            folder = fetch(dry="--dry-run" in argv)
        except Refused as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        if folder:
            print(folder)
        return 0
    print("usage: update.py check [--json] | update.py fetch [--dry-run]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
