# mdbook (unofficial PyPI package)

> **This is an unofficial repackaging.** It isn't affiliated with or endorsed by
> the mdBook maintainers or the Rust project. For mdBook itself (docs, issues,
> source), go to **[rust-lang/mdBook](https://github.com/rust-lang/mdBook)**.
> Report a packaging problem (a wheel that won't install, a missing platform)
> [here](https://github.com/nickagliano/mdbook-python/issues), and anything about
> mdBook's behavior upstream.

[mdBook](https://github.com/rust-lang/mdBook) is a command-line tool for
building books from Markdown files. This package ships the unmodified upstream
`mdbook` binary inside Python wheels, so you can install it with `pip` or `uv`
and pin it in `pyproject.toml` along with the rest of your tools. You don't need
a Rust toolchain.

## Install

```sh
pip install mdbook
```

or as a dev dependency with uv:

```sh
uv add --dev mdbook
```

or run it once without installing:

```sh
uvx mdbook --version
```

Either way, the `mdbook` executable ends up on your `PATH` (inside the active
virtualenv). There's no Python API; the package only contains the binary.

## Usage

The command is upstream's `mdbook`, unchanged:

```sh
mdbook init my-book
mdbook build my-book
mdbook serve my-book --open
```

For everything else, see the [mdBook User Guide](https://rust-lang.github.io/mdBook/).

## Versioning

The package version mirrors the upstream release tag it was built from:

| PyPI version  | Built from upstream                 |
| ------------- | ----------------------------------- |
| `0.5.4`       | `v0.5.4`                            |
| `0.5.4.post1` | `v0.5.4` (packaging-only fix)       |
| `0.5.5`       | `v0.5.5`                            |

A `.postN` release contains the same mdBook source as its base version. Only
the packaging changed. `mdbook --version` always prints the upstream version
(`mdbook v0.5.4`).

To pin the upstream version, including any packaging fixes, use a compatible
range: `mdbook>=0.5.4,<0.5.5`.

## Platforms

Prebuilt wheels:

| OS      | Architectures      | Notes                         |
| ------- | ------------------ | ----------------------------- |
| macOS   | arm64, x86_64      |                               |
| Linux   | x86_64, aarch64    | manylinux2014 (glibc ≥ 2.17)  |
| Linux   | x86_64, aarch64    | musllinux_1_2 (e.g. Alpine)   |
| Windows | x86_64             |                               |

On any other platform, pip falls back to the source distribution and compiles
mdBook locally. That requires a [Rust toolchain](https://rustup.rs/) at least
as new as upstream's `rust-version` (1.88 for mdBook 0.5.4).

## How it's built

- Upstream source comes in as a git submodule (`mdBook/`), pinned to the
  exact release tag. `upstream.toml` records the tag and its commit SHA. Every
  build runs `scripts/verify_upstream.py`, which fails if the submodule, the
  recorded SHA, and the upstream tag disagree (for example, if the tag was
  moved).
- Wheels are built with [maturin](https://github.com/PyO3/maturin) in binary
  mode (`bindings = "bin"`), using upstream's `Cargo.lock` unchanged
  (`locked = true`) and upstream's default features.
- In CI, each wheel is installed into a fresh virtualenv on its own platform,
  and `mdbook --version` has to match the pinned version.
- Every GitHub Action is pinned to a full commit SHA. Releases go to PyPI
  through [trusted publishing](https://docs.pypi.org/trusted-publishers/) (OIDC),
  so no API tokens are involved, and come with PEP 740 attestations.
- A scheduled workflow watches for new upstream releases and opens a PR that
  bumps the pin. It never publishes. A maintainer reviews, merges, and starts
  the release by hand.

## License

mdBook is licensed under the [Mozilla Public License 2.0](LICENSE). The
`LICENSE` file in this repository is upstream's, copied verbatim, and it's
included in every wheel and in the sdist. This repository's packaging files are
under the same license.

As MPL-2.0 requires, the source for the binaries in these wheels is available:
it's the upstream tag recorded in [`upstream.toml`](upstream.toml) (at
<https://github.com/rust-lang/mdBook>), and it's also included in this package's
sdist on PyPI.

## Development

```sh
git clone --recurse-submodules https://github.com/nickagliano/mdbook-python
cd mdbook-python
python scripts/verify_upstream.py        # check the pin
uvx maturin build --release --out dist   # build a wheel for this machine
python scripts/check_dist.py dist/*.whl  # install it in a fresh venv and test it
```

To release: run the **Release** workflow from `master`, first with
`index: testpypi`, then with `index: pypi`.
