"""Bump the pinned upstream mdBook release if a newer one exists.

Looks up upstream's latest (non-prerelease) GitHub release, and if it is newer
than the pin in upstream.toml: moves the mdBook/ submodule to the tag's commit,
rewrites upstream.toml, resets pyproject.toml's version to the new upstream
version, and re-copies LICENSE. It never commits, pushes, or publishes.

Writes `bumped`, `tag` and `version` to $GITHUB_OUTPUT when set. Needs the `gh`
CLI (authenticated via GH_TOKEN) and git. Requires Python 3.11+.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

from verify_upstream import ROOT, SUBMODULE, TAG_RE, git, load_pin, remote_tag_commit


def latest_release_tag(repository: str) -> str:
    slug = repository.removeprefix("https://github.com/")
    return subprocess.run(
        ["gh", "api", f"repos/{slug}/releases/latest", "--jq", ".tag_name"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def version_tuple(tag: str) -> tuple[int, ...]:
    match = TAG_RE.match(tag)
    if not match:
        # Tags flow into branch names and shell commands; reject anything unexpected.
        raise SystemExit(f"error: refusing unexpected tag {tag!r} (want vX.Y.Z)")
    return tuple(int(part) for part in match.group(1).split("."))


def replace_once(path, pattern: str, replacement: str) -> None:
    text = path.read_text()
    new, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise SystemExit(f"error: pattern {pattern!r} not found in {path.name}")
    path.write_text(new)


def set_output(**values: str) -> None:
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a") as fh:
            for key, value in values.items():
                fh.write(f"{key}={value}\n")


def main() -> int:
    repository, current_tag, _ = load_pin()
    latest_tag = latest_release_tag(repository)

    if version_tuple(latest_tag) <= version_tuple(current_tag):
        print(f"Up to date: pinned {current_tag}, latest upstream release {latest_tag}")
        set_output(bumped="false")
        return 0

    commit = remote_tag_commit(repository, latest_tag)
    version = latest_tag.removeprefix("v")
    print(f"Bumping {current_tag} -> {latest_tag} ({commit})")

    submodule = ROOT / SUBMODULE
    git("fetch", "--depth", "1", "origin", commit, cwd=submodule)
    git("-c", "advice.detachedHead=false", "checkout", commit, cwd=submodule)
    git("add", SUBMODULE)

    replace_once(ROOT / "upstream.toml", r'^tag = ".*"$', f'tag = "{latest_tag}"')
    replace_once(ROOT / "upstream.toml", r'^commit = ".*"$', f'commit = "{commit}"')
    replace_once(ROOT / "pyproject.toml", r'^version = ".*"$', f'version = "{version}"')
    shutil.copyfile(submodule / "LICENSE", ROOT / "LICENSE")

    set_output(bumped="true", tag=latest_tag, version=version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
