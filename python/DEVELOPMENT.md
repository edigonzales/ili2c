# Developer guide

This document explains how to work on the `ili2c-python` module locally.

## Prerequisites

- Python 3.10 or newer
- [pipx](https://pipx.pypa.io/), [uv](https://docs.astral.sh/uv/), or the
  system `pip` for dependency management
- GNU Make (optional) if you prefer scripted workflows

## Installing dependencies

Create a virtual environment and install the project in editable mode with the
optional testing dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[test] # pip install -e '.[test]' on zsh
```

The project metadata lives in `setup.py` and `setup.cfg`; either `pip` or
`python -m build` will pick up the configuration.

## Running the tests

The project uses [pytest](https://pytest.org/):

```bash
pytest
```

To limit the run to a single test module:

```bash
pytest tests/pyili2c/test_parser.py
```

## Static checks

Add your preferred tooling (e.g. `ruff`, `mypy`) to a local virtual environment
and run it before opening a pull request.  The default GitHub Action described
below runs `pytest` as a minimum safety net.

## Building distributions

Build a source distribution and wheel using the standard library tooling:

```bash
python -m build
```

Artifacts are written to the `dist/` directory.

## Publishing to PyPI

The automated workflow publishes to PyPI when a GitHub Release is created.  To
publish manually:

```bash
python -m build
python -m twine upload dist/*
```

Set the `TWINE_USERNAME` and `TWINE_PASSWORD` environment variables (or use a
`.pypirc` file) before running `twine`.

## GitHub Actions workflow

The repository contains `.github/workflows/python-package.yml`, which performs
three tasks:

1. Install dependencies and run the test suite for every push and pull request.
2. Build the wheel and source distribution artifacts.
3. Publish the package to PyPI whenever a tag starting with `v` is pushed,
   assuming the `PYPI_API_TOKEN` secret is configured in the repository
   settings.

## Code style

- Follow standard Python style conventions (`black`, `ruff`, `isort`).
- Keep modules importable from `ili2c.*` to maintain the public API.
- Update documentation and tests alongside code changes.
