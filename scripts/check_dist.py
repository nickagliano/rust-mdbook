"""Install a built wheel or sdist into a fresh venv and smoke-test it.

For each distribution given:
  - its filename version must equal pyproject.toml's version;
  - it must contain the MPL-2.0 LICENSE;
  - after installing it into a brand-new venv, `mdbook --version` must print
    exactly `mdbook v<pinned upstream version>`.

Installing an sdist compiles mdBook from source, so it needs a Rust toolchain
and network access for the build backend. Stdlib only; requires Python 3.11+.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def expected_versions() -> tuple[str, str]:
    tag = tomllib.loads((ROOT / "upstream.toml").read_text())["upstream"]["tag"]
    py_version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    return tag.removeprefix("v"), py_version


def dist_version(path: Path) -> str:
    # Wheel: name-version-pytag-abitag-plattag.whl; sdist: name-version.tar.gz
    if path.name.endswith(".whl"):
        return path.name.split("-")[1]
    return path.name.removesuffix(".tar.gz").split("-", 1)[1]


def has_license(path: Path) -> bool:
    if path.name.endswith(".whl"):
        with zipfile.ZipFile(path) as wheel:
            names = wheel.namelist()
        return any(".dist-info/licenses/" in n and n.endswith("/LICENSE") for n in names)
    with tarfile.open(path) as sdist:
        return any(n.count("/") == 1 and n.endswith("/LICENSE") for n in sdist.getnames())


def check(path: Path) -> list[str]:
    upstream_version, py_version = expected_versions()
    failures = []

    version = dist_version(path)
    if version != py_version:
        failures.append(f"{path.name}: filename version {version} != pyproject {py_version}")
    if not has_license(path):
        failures.append(f"{path.name}: LICENSE not found in distribution")

    with tempfile.TemporaryDirectory() as tmp:
        venv = Path(tmp) / "venv"
        subprocess.run([sys.executable, "-m", "venv", venv], check=True)
        bindir = venv / ("Scripts" if os.name == "nt" else "bin")
        pip = [bindir / "python", "-m", "pip", "install", "--no-deps", "--disable-pip-version-check"]
        if path.name.endswith(".whl"):
            pip += ["--no-index", "--only-binary", ":all:"]
        subprocess.run([*pip, path], check=True)

        exe = bindir / ("mdbook.exe" if os.name == "nt" else "mdbook")
        out = subprocess.run([exe, "--version"], check=True, capture_output=True, text=True)
        got = out.stdout.strip()
        want = f"mdbook v{upstream_version}"
        print(f"{path.name}: `mdbook --version` -> {got!r}")
        if got != want:
            failures.append(f"{path.name}: `mdbook --version` printed {got!r}, expected {want!r}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dists", nargs="+", type=Path, help="wheel or sdist files")
    args = parser.parse_args()

    failures = [f for path in args.dists for f in check(path)]
    for failure in failures:
        print(f"FAIL  {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
