# ili2c Python Utilities

This directory contains the Python ports of selected ili2c functionality:

- `pyili2c` – a lightweight INTERLIS metamodel and parser.
- `ilirepository` – helpers for interacting with INTERLIS model repositories.
- `tests` – pytest-based regression tests that exercise both packages.

The project is managed with a standalone `pyproject.toml`, allowing the code to be
installed with modern tools such as [uv](https://docs.astral.sh/uv/) or `pip`.

## Dependencies

The parser depends on the upstream
[`antlr4-python3-runtime`](https://pypi.org/project/antlr4-python3-runtime/)
package. It is declared in `pyproject.toml` and installed automatically when
you install the project, so no vendored copy is required.

## Quick start with uv

The commands below assume you are working from this `python/` directory.

1. Create a virtual environment:

   ```bash
   uv venv
   ```

2. Activate it (Linux/macOS):

   ```bash
   source .venv/bin/activate
   ```

3. Install the project with its optional test dependencies:

   ```bash
   uv pip install -e .[test]
   ```

4. Run the tests:

   ```bash
   python -m pytest
   ```

The `pyproject.toml` configures pytest to look inside `tests/`. From elsewhere
in the repository, you can run `python -m pytest python/tests`.
