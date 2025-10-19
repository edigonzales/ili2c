# ili2c Python module

The Python edition of **ili2c** brings a focused subset of the INTERLIS toolchain
into pure Python. It provides a light-weight metamodel that mirrors the Java
API, a parser backed by ANTLR grammars, rendering helpers, and repository tools
for discovering and caching INTERLIS models.

## Installation

```bash
pip install ili2c-python
```

You can also install directly from a clone of this repository:

```bash
pip install .
```

When developing locally, install the optional `test` extra to run the pytest suite:

```bash
pip install .[test]
```

## Package layout and features

The top-level package is `ili2c` with two subpackages:

### `ili2c.pyili2c`

* `parser` contains `parse()` and `ParserSettings`, combining the ANTLR grammar
  with repository discovery. It loads `.ili` files and recursively resolves
  imports into a `TransferDescription` tree that mirrors the Java API.
* `metamodel` offers the Python data structures (e.g. `TransferDescription`,
  `Model`, `Topic`, `Table`, `Attribute`) with helper methods such as
  `getModels()`, `find_model()`, and `elements_of_type()` for navigating a
  parsed model graph.
* `mermaid` converts transfer descriptions into Mermaid class diagrams—ideal
  for quickly visualising the content of an INTERLIS model.

### `ili2c.ilirepository`

* `IliRepositoryManager` walks configured repository URLs, follows links from
  `ilisite.xml`, picks the freshest version of each model, and can download the
  corresponding `.ili` file locally.
* `RepositoryAccess` reads `ilimodels.xml` metadata from HTTP(S) repositories or
  the file system and turns them into `ModelMetadata` records.
* `RepositoryCache` keeps HTTP downloads on disk, honours configurable TTLs,
  supports MD5 validation, and can sanitise paths so that repeated parses reuse
  cached models instead of hitting the network.

## Parsing models

The parser resolves imports via `ParserSettings`. Configure model directories
and repositories up front, then call `parse()`:

```python
import logging
from pathlib import Path

from ili2c.pyili2c import parser
from ili2c.pyili2c.metamodel import Table

logging.basicConfig(level=logging.INFO)

settings = parser.ParserSettings(
    ilidirs=["examples/models"],
    repositories=["http://models.interlis.ch/"],
)

transfer_description = parser.parse(
    Path("examples/models/DM01INTERLIS2_3.ili"),
    settings=settings,
)

for model in transfer_description.getModels():
    logging.info("Loaded model %%s (schema %%s)", model.getName(), model.getSchemaLanguage())
```

`ParserSettings` understands semicolon separated `ILI_DIR` strings, local
folders, HTTP(S) repositories, and the `%ILI_DIR` placeholder. The parser stores
already parsed files in a cache to avoid re-reading the same model twice.

### Discovering model elements

The `TransferDescription` returned by the parser mirrors the Java API. Use
`find_model()` to locate a model, then traverse its topics and tables or use the
recursive `elements_of_type()` helper:

```python
import logging

from ili2c.pyili2c import parser
from ili2c.pyili2c.metamodel import Table, TransferDescription

logging.basicConfig(level=logging.INFO)

transfer_description: TransferDescription = parser.parse("path/to/model.ili")
model = transfer_description.find_model("DM01INTERLIS2_3")
if model is None:
    raise RuntimeError("model not found")

logging.info("Model %s imports: %s", model.getName(), list(model.getImports()))

for topic in model.getTopics():
    logging.info("Topic %s contains %d classes", topic.getName(), len(topic.getClasses()))

for table in model.elements_of_type(Table):
    logging.info("Class %s has %d attributes", table.getScopedName(), len(table.getAttributes()))
```

`Table` instances expose methods such as `getAttributes()`, `getConstraints()`,
`isAbstract()`, and `getExtending()` which mirror the Java original. Use them to
inspect inheritance trees, mandatory attributes, or association ends.

### Rendering Mermaid diagrams

Turn a parsed model into a diagram to share with collaborators:

```python
import logging

from ili2c.pyili2c import parser
from ili2c.pyili2c.mermaid import render

logging.basicConfig(level=logging.INFO)

transfer_description = parser.parse("path/to/model.ili")
mermaid_source = render(transfer_description)
logging.info("Generated diagram:\n%s", mermaid_source)
```

The output can be pasted into any Mermaid-compatible viewer.

## Working with repositories

The repository manager can discover models, fetch metadata, and download files:

```python
import logging

from ili2c.ilirepository import IliRepositoryManager

logging.basicConfig(level=logging.INFO)

manager = IliRepositoryManager(["https://models.interlis.ch/"])
for metadata in manager.list_models():
    logging.info("%s %s -> %s", metadata.name, metadata.version, metadata.full_url)

metadata = manager.find_model("DM01INTERLIS2_3")
if metadata:
    local_path = manager.get_model_file(metadata.name)
    logging.info("Cached copy stored at %s", local_path)
```

`IliRepositoryManager` ranks multiple revisions by publishing date or version
number and walks the repository network discovered via `ilisite.xml` so that
linked repositories are searched automatically.

### Repository cache behaviour

`RepositoryCache` stores downloads inside a configurable folder. Override it via
`ILI_CACHE` or by passing `base_dir`. The cache key is derived from the URL and
may use hashed filenames when `ILI_CACHE_FILENAME=MD5` is set. Each request can
specify a TTL—`0` forces a re-download, `None` keeps the first copy indefinitely,
and positive values trigger refreshes once the files grow stale. When MD5 hashes
are provided the cache verifies them and re-fetches if they no longer match.

### Sequence of resolving an import

```mermaid
sequenceDiagram
    participant User
    participant Parser
    participant Settings
    participant Manager
    participant Access
    participant Cache
    participant Repository

    User->>Parser: parse(path, settings)
    Parser->>Settings: resolve ilidirs & repositories
    Parser->>Manager: get_model_file(import_name)
    Manager->>Access: get_models(repository)
    Access->>Cache: fetch(ilimodels.xml)
    Cache->>Repository: HTTP GET /ilimodels.xml
    Repository-->>Cache: XML metadata
    Cache-->>Access: cached path
    Access-->>Manager: latest ModelMetadata
    Manager->>Cache: fetch(model.ili)
    Cache->>Repository: HTTP GET /model.ili
    Repository-->>Cache: ILI file
    Cache-->>Manager: local path
    Manager-->>Parser: filesystem path
    Parser-->>User: TransferDescription with imported model
```

## Tips for exploring models

* Configure `logging` to `INFO` or `DEBUG` to observe cache hits, HTTP requests,
  and import resolution decisions.
* `TransferDescription.getModels()` returns immutable tuples—store mutable data
  on your own objects if needed.
* Use `Model.elements_of_type(...)` to search for specific element kinds
  anywhere inside a model without walking the nested structure manually.
* Combine the Mermaid renderer with `elements_of_type()` filters to render
  minimal diagrams that focus on selected topics or tables.

## Troubleshooting

* If the parser cannot locate an import, ensure the model name (case-insensitive)
  matches the filename and that the directory is listed in `ilidirs`.
* For repository downloads behind a proxy, export the standard `HTTP_PROXY`
  environment variables—`urllib` honours them automatically.
* To inspect cached files, open the directory reported in log messages; removing
  files forces the cache to fetch them again on the next parse.

## Dataclass generator

The `ili2c.dataclasses` package contains utilities for translating INTERLIS
models into Python `@dataclass` definitions. The resulting classes provide a
Python-native view of the INTERLIS metamodels and expose detailed metadata
needed for validation and higher-level tooling.

### Why generate dataclasses?

* **Idiomatic access to INTERLIS metadata.** The generator embeds INTERLIS
  constraints (mandatory flags, text length, bag/cardinality information, target
  classes, aliases, etc.) inside the `field.metadata["ili"]` dictionary. This
  allows downstream code to perform validation, build forms, or drive code
  generation without re-parsing `.ili` files.
* **Type hints for consumers.** Each dataclass attribute is annotated with the
  closest Python type (including `typing.Literal` for enumerations and
  `tuple[...]` for bags/lists). Optional fields are annotated with `| None`,
  enabling static analysis and editor auto-completion.
* **Keeps INTERLIS knowledge close to the code.** By checking the generated
  module into the repository, applications can import the structure definitions
  directly, while the generator stays responsible for staying in sync with new
  schema versions.

### How generation works

1. Parse the INTERLIS model using the existing `ili2c` parser.
2. Feed the resulting `Model` object to `DataclassGenerator`.
3. Render the collected classes, attributes, type hints, and metadata into a
   Python module.

The generator inspects both global table definitions and classes/structures
nested inside topics. Type aliases are resolved so that common constructs (for
example `BOOLEAN`, numeric ranges, or references to other classes) surface as
sensible Python annotations.

### Usage examples

#### Generating dataclasses for a model

```python
from pathlib import Path

from ili2c.dataclasses.generator import DataclassGenerator
from ili2c.pyili2c.parser import parse

model_path = Path("examples/models/Foo.ili")
model = parse(model_path).getModels()[0]
module_text = DataclassGenerator(model).build_module()

Path("foo_model.py").write_text(module_text)
```

The resulting module can be committed to the repository or imported dynamically
using `importlib`. The generator produces `@dataclass(kw_only=True)` classes, so
values must be passed via keyword arguments when instantiating.

#### Working with the generated classes

```python
from ili2c.dataclasses import ilismeta16

meta = ilismeta16.MetaElement(
    name="Example",
    definition="…",
    documentation=(),
)

# Accessing INTERLIS metadata
field_info = ilismeta16.MetaElement.__dataclass_fields__["name"].metadata["ili"]
print(field_info["mandatory"])  # -> True
print(field_info["max_length"])  # -> 1024
```

Lists in INTERLIS map to tuples in the generated module. Optional attributes are
annotated with `| None` and default to `None` if not mandatory.

#### Integrating with SQLAlchemy

The metadata embedded in each field can drive ORM mappings without hard-coding
schema details. The snippet below shows how to translate a generated dataclass
into a SQLAlchemy table definition:

```python
from dataclasses import fields
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

from ili2c.dataclasses import ilismeta16

metadata = MetaData()

def _column_for(field):
    info = field.metadata["ili"]

    # Determine the best-fitting SQLAlchemy type.
    if info.get("python_type") == "int":
        column_type = Integer
    elif info.get("alias_kind") == "boolean":
        column_type = Boolean
    else:
        max_length = info.get("max_length")
        column_type = String(max_length) if max_length else Text

    kwargs = {"nullable": not info["mandatory"]}

    if info.get("identifier_category") in {"oid", "tid"}:
        kwargs["primary_key"] = True

    return Column(field.name, column_type, **kwargs)

meta_element_table = Table(
    "meta_element",
    metadata,
    *(_column_for(field) for field in fields(ilismeta16.MetaElement)),
)

# Bind metadata to an engine, create tables, etc.
```

This approach automatically reflects INTERLIS constraints in the database layer:

* Mandatory attributes become non-nullable columns.
* Text length limits transfer to `String(length)` columns, while free-form
  `TEXT` becomes `Text`.
* Identifier aliases (such as TIDs or OIDs) are treated as primary keys so
  transfer identifiers map cleanly to database identifiers.

#### Running the full SQLAlchemy example

For a runnable, end-to-end integration have a look at
`ili2c.dataclasses.examples.sqlalchemy_example`. The module generates dataclasses
for the bundled `SimpleModel.ili`, translates them into SQLAlchemy tables backed
by SQLite, writes sample data, and finally reconstructs the dataclasses from
database rows.

> **Optional dependency**: SQLAlchemy is not required for the core
> `ili2c.dataclasses` package. Install it explicitly (for example with
> `pip install ili2c-python[examples]` or `pip install sqlalchemy`) before
> running the example or its regression test.

Execute the example directly:

```bash
PYTHONPATH=python python -m ili2c.dataclasses.examples.sqlalchemy_example \
    --database demo.sqlite
```

Sample output:

```
Created 1 building(s) in demo.sqlite
  Building #1: Hauptstrasse 1, Nebenweg 5
```

The example is covered by an automated test, so the full pipeline stays
working:

```bash
PYTHONPATH=python pytest python/tests/test_sqlalchemy_example.py
```

If SQLAlchemy is not installed the test is skipped automatically, keeping the
base test suite dependency-free.

#### Generating UI scaffolding without extra dependencies

The module `ili2c.dataclasses.examples.ui_scaffolding_example` demonstrates how
to turn a generated model into HTML forms using only the Python standard
library. It inspects the same metadata as the SQLAlchemy example to choose input
types, mark mandatory fields, and provide repeatable sections for LIST
attributes—no third-party UI framework required.

Key capabilities of the script:

* renders one HTML form per generated dataclass, grouped by INTERLIS topic;
* emits `<select>` elements for enumerations, checkboxes for boolean aliases,
  and repeatable sub-sections for bags/lists;
* surfaces `field.metadata["ili"]` hints (mandatory, max length, identifier
  flags) as HTML attributes and inline help text; and
* preserves documentation strings so the resulting page doubles as a schema
  reference.

Run the example to create a standalone HTML document (the bundled
`SimpleModel.ili` is used by default):

```bash
PYTHONPATH=python python -m ili2c.dataclasses.examples.ui_scaffolding_example \
    --output demo_form.html
```

Optional flags let you point at a different `.ili` model (`--model`) or change
the HTML title (`--title`). After the script finishes you can open the generated
file in a browser to experiment with the auto-generated form. The first section
of the page summarises how many dataclasses were found and which INTERLIS topics
they belong to, followed by the fully expanded forms.

Because the implementation relies solely on standard-library modules, the core
library remains dependency-free. If you later integrate with a framework such as
FastAPI or Django, keep those adapters in optional modules so downstream
projects can opt in without burdening the base package.

#### Running the regression tests

The repository ships with snapshot-based tests that exercise the generator
against the IlisMeta16 and example models. Run them via:

```bash
PYTHONPATH=python pytest python/tests/test_ilismeta_dataclasses.py
```

These tests ensure that metadata and type hints stay stable when updating the
parser or generator.

### Extending the generator

If you need to support additional INTERLIS constructs or change the emitted
Python shapes, adjust `python/ili2c/dataclasses/generator.py`. The module
structure keeps rendering logic separate from the INTERLIS parser, making it
straightforward to plug in alternative output formats if desired.
