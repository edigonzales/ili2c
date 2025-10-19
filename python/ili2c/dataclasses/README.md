# INTERLIS dataclass generator

This package contains utilities for translating INTERLIS models into Python
`@dataclass` definitions.  The resulting classes provide a Python-native view of
the INTERLIS metamodels and expose detailed metadata needed for validation and
higher-level tooling.

## Why generate dataclasses?

* **Idiomatic access to INTERLIS metadata.**  The generator embeds INTERLIS
  constraints (mandatory flags, text length, bag/cardinality information, target
  classes, aliases, etc.) inside the `field.metadata["ili"]` dictionary.  This
  allows downstream code to perform validation, build forms, or drive code
  generation without re-parsing `.ili` files.
* **Type hints for consumers.**  Each dataclass attribute is annotated with the
  closest Python type (including `typing.Literal` for enumerations and
  `tuple[...]` for bags/lists).  Optional fields are annotated with `| None`,
  enabling static analysis and editor auto-completion.
* **Keeps INTERLIS knowledge close to the code.**  By checking the generated
  module into the repository, applications can import the structure definitions
  directly, while the generator stays responsible for staying in sync with new
  schema versions.

## How generation works

1. Parse the INTERLIS model using the existing `ili2c` parser.
2. Feed the resulting `Model` object to `DataclassGenerator`.
3. Render the collected classes, attributes, type hints, and metadata into a
   Python module.

The generator inspects both global table definitions and classes/structures
nested inside topics.  Type aliases are resolved so that common constructs (for
example `BOOLEAN`, numeric ranges, or references to other classes) surface as
sensible Python annotations.

## Usage examples

### Generating dataclasses for a model

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
using `importlib`.  The generator produces `@dataclass(kw_only=True)` classes,
so values must be passed via keyword arguments when instantiating.

### Working with the generated classes

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

Lists in INTERLIS map to tuples in the generated module.  Optional attributes
are annotated with `| None` and default to `None` if not mandatory.

### Integrating with SQLAlchemy

The metadata embedded in each field can drive ORM mappings without hard-coding
schema details.  The snippet below shows how to translate a generated dataclass
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

This approach automatically reflects INTERLIS constraints in the database
layer:

* Mandatory attributes become non-nullable columns.
* Text length limits transfer to `String(length)` columns, while free-form
  `TEXT` becomes `Text`.
* Identifier aliases (such as TIDs or OIDs) are treated as primary keys so
  transfer identifiers map cleanly to database identifiers.

### Running the full SQLAlchemy example

For a runnable, end-to-end integration have a look at
`ili2c.dataclasses.examples.sqlalchemy_example`.  The module generates
dataclasses for the bundled `SimpleModel.ili`, translates them into SQLAlchemy
tables backed by SQLite, writes sample data, and finally reconstructs the
dataclasses from database rows.

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

### Generating UI scaffolding without extra dependencies

The module `ili2c.dataclasses.examples.ui_scaffolding_example` demonstrates
how to turn a generated model into HTML forms using only the Python standard
library.  It inspects the same metadata as the SQLAlchemy example to choose
input types, mark mandatory fields, and provide repeatable sections for LIST
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
the HTML title (`--title`).  After the script finishes you can open the
generated file in a browser to experiment with the auto-generated form.  The
first section of the page summarises how many dataclasses were found and which
INTERLIS topics they belong to, followed by the fully expanded forms.

Because the implementation relies solely on standard-library modules, the
core library remains dependency-free.  If you later integrate with a
framework such as FastAPI or Django, keep those adapters in optional modules
so downstream projects can opt in without burdening the base package.

### Running the regression tests

The repository ships with snapshot-based tests that exercise the generator
against the IlisMeta16 and example models.  Run them via:

```bash
PYTHONPATH=python pytest python/tests/test_ilismeta_dataclasses.py
```

These tests ensure that metadata and type hints stay stable when updating the
parser or generator.

## Extending the generator

If you need to support additional INTERLIS constructs or change the emitted
Python shapes, adjust `python/ili2c/dataclasses/generator.py`.  The module
structure keeps rendering logic separate from the INTERLIS parser, making it
straightforward to plug in alternative output formats if desired.
