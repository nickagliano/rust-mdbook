"""Verify that the packaged upstream source is exactly the pinned release.

Checks, in order:
  1. the mdBook/ submodule gitlink (what this repo commits) equals the pinned commit;
  2. the checked-out mdBook/ working tree is at that commit and unmodified;
  3. upstream's tag still resolves to the pinned commit (skipped with --offline);
  4. mdBook/Cargo.toml's package version matches the tag;
  5. pyproject.toml's version is the tag's version, optionally with a .postN suffix;
  6. LICENSE in this repo is byte-identical to upstream's LICENSE.

Exits non-zero on the first failed check. Stdlib only; requires Python 3.11+.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUBMODULE = "mdBook"
TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def load_pin() -> tuple[str, str, str]:
    pin = tomllib.loads((ROOT / "upstream.toml").read_text())["upstream"]
    return pin["repository"], pin["tag"], pin["commit"]


def remote_tag_commit(repository: str, tag: str) -> str:
    """Return the commit `tag` points to upstream, peeling annotated tags."""
    out = git("ls-remote", "--tags", repository, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}")
    refs = dict(reversed(line.split("\t")) for line in out.splitlines())
    if not refs:
        raise SystemExit(f"error: tag {tag} not found in {repository}")
    return refs.get(f"refs/tags/{tag}^{{}}", refs.get(f"refs/tags/{tag}"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--offline", action="store_true", help="skip the check against the upstream remote"
    )
    args = parser.parse_args()

    repository, tag, commit = load_pin()
    failures: list[str] = []

    def check(ok: bool, message: str) -> None:
        print(("ok    " if ok else "FAIL  ") + message)
        if not ok:
            failures.append(message)

    match = TAG_RE.match(tag)
    if not match:
        raise SystemExit(f"error: pinned tag {tag!r} is not of the form vX.Y.Z")
    upstream_version = match.group(1)

    gitlink = git("ls-tree", "HEAD", SUBMODULE).split()
    gitlink_sha = gitlink[2] if len(gitlink) >= 3 and gitlink[1] == "commit" else None
    # Fall back to the index so the check also works before the first commit.
    if gitlink_sha is None:
        staged = git("ls-files", "--stage", SUBMODULE).split()
        gitlink_sha = staged[1] if staged and staged[0] == "160000" else None
    check(gitlink_sha == commit, f"submodule gitlink {gitlink_sha} == pinned {commit}")

    head = git("rev-parse", "HEAD", cwd=ROOT / SUBMODULE)
    check(head == commit, f"mdBook/ checkout {head} == pinned {commit}")
    dirty = git("status", "--porcelain", "--untracked-files=no", cwd=ROOT / SUBMODULE)
    check(not dirty, "mdBook/ has no local modifications")

    if args.offline:
        print("skip  upstream tag check (--offline)")
    else:
        remote = remote_tag_commit(repository, tag)
        check(remote == commit, f"upstream {tag} -> {remote} == pinned {commit}")

    cargo = tomllib.loads((ROOT / SUBMODULE / "Cargo.toml").read_text())
    cargo_version = cargo["package"]["version"]
    check(
        cargo_version == upstream_version,
        f"mdBook/Cargo.toml version {cargo_version} == tag {tag}",
    )

    py_version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    check(
        re.fullmatch(re.escape(upstream_version) + r"(\.post\d+)?", py_version) is not None,
        f"pyproject version {py_version} is {upstream_version}[.postN]",
    )

    same_license = (ROOT / "LICENSE").read_bytes() == (ROOT / SUBMODULE / "LICENSE").read_bytes()
    check(same_license, "LICENSE is identical to mdBook/LICENSE")

    if failures:
        print(f"\n{len(failures)} check(s) failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
