# Developer guide

This document explains how to work on the Python flavour of **ili2c**. It covers
local setup, the test suite, and the internal architecture of the parser and
repository helpers.

## Environment setup

1. Use Python 3.10 or newer as defined in `setup.cfg`.
2. Create and activate a virtual environment.
3. Install the package in editable mode together with the test extras:
   
   ```bash
   pip install --editable ./python[test]
   ```

The editable install exposes the ANTLR runtime and makes the bundled parser
artifacts available without an extra build step.

## Running the tests

The Python package uses `pytest`. Execute the suite from the repository root:

```bash
cd python
pytest
```

Tests that talk to remote repositories are marked with `@pytest.mark.network`.
Use `pytest -m "not network"` to run the offline subset or set the environment up
with network access when validating repository behaviour.

## Repository layout

* `ili2c/pyili2c/metamodel.py` implements the simplified INTERLIS metamodel
  (`TransferDescription`, `Model`, `Topic`, `Table`, `Attribute`, …). These
  classes intentionally mimic the Java API and provide navigation helpers such as
  `elements_of_type()` for deep searches.
* `ili2c/pyili2c/parser/core.py` glues the ANTLR-generated lexer/parser together
  with `ParserSettings`. It resolves `%ILI_DIR` placeholders, walks
  `ParserSettings.repositories`, and reuses a shared `RepositoryCache` when
  fetching imports.
* `ili2c/pyili2c/parser/generated/grammars_antlr4/` holds the generated parser
  code. The source grammar lives in the repository root under `grammars-antlr4`.
  Re-generate the Python artefacts with:
  
  ```bash
  antlr4 -Dlanguage=Python3 -visitor -listener \
    -o python/ili2c/pyili2c/parser/generated/grammars_antlr4 \
    grammars-antlr4/InterlisLexer.g4 grammars-antlr4/InterlisParser.g4
  ```

  After re-generating, run `pytest` to confirm the new grammar still parses the
  bundled examples.
* `ili2c/pyili2c/mermaid.py` traverses transfer descriptions and converts them
  into Mermaid diagrams. Most rendering behaviour resides in the private
  `_MermaidRenderer` class.
* `ili2c/ilirepository/` contains the high-level repository facade and the file
  cache implementation. `IliRepositoryManager` handles recursion through
  connected repositories, while `RepositoryCache` persists HTTP responses and
  honours TTL/MD5 parameters.

## Working with the parser

`ParserSettings` centralises everything related to model discovery. It tracks raw
`ILI_DIR` strings, separates directories from repository URIs, and lazily creates
an `IliRepositoryManager`. The `_ParseContext` class caches already-parsed files
so that recursive imports do not reprocess the same `.ili` file.

When extending the parser, keep the following in mind:

* Always resolve imports via `_ParseContext._resolve_import()` to ensure
  directory lookups, repository searches, and schema-language-specific downloads
  continue to work.
* Store the source path on new metamodel classes when appropriate so that the
  repository cache can link elements back to their origin (`model._source`).
* Maintain API parity with the Java implementation where feasible—many clients
  depend on familiar method names (`getTopics()`, `getAttributes()`, …).

## Repository cache internals

`RepositoryCache` chooses the cache folder from the `ILI_CACHE` environment
variable or defaults to `~/.pyilicache`. It can hash filenames (set
`ILI_CACHE_FILENAME=MD5`) to avoid path collisions, sanitises illegal characters,
and refreshes entries based on the TTL provided by repository helpers. Cache
reads and writes emit `logging` events—enable `logging.getLogger("ili2c")` at
`INFO` level while developing to inspect the flow.

## Logging and diagnostics

The code base uses the standard library `logging` module. Examples in the user
documentation call `logging.basicConfig(level=logging.INFO)` so that repository
hits, cache refreshes, and parser decisions become visible. During development,
raise the level to `DEBUG` to see detailed traces from `_resolve_import()` and
HTTP fetches. Avoid adding print statements; emit structured logs instead.

## Release checklist

1. Ensure the README and CHANGELOG (if applicable) describe new features.
2. Bump the `version` in `setup.cfg` when shipping a new build.
3. Run the full test suite (`pytest`) and, optionally, the network-marked tests
   if repository-facing behaviour changed.
4. Commit regenerated ANTLR artefacts whenever the grammar changes.
