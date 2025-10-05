# ili2c Python Utilities

This directory contains the Python ports of selected ili2c functionality:

- `pyili2c` – a lightweight INTERLIS metamodel and parser.
- `ilirepository` – helpers for interacting with INTERLIS model repositories.
- `tests` – pytest-based regression tests that exercise both packages.
- `antlr4` – a vendored copy of the [`antlr4-python3-runtime`](https://pypi.org/project/antlr4-python3-runtime/) wheel (v4.13.1).

The project is managed with a standalone `pyproject.toml`, allowing the code to be
installed with modern tools such as [uv](https://docs.astral.sh/uv/) or `pip`.
