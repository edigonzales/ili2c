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
