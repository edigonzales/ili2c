# ili2c Python module

`ili2c-python` packages the Python helpers that accompany the [ili2c](https://github.com/claeis/ili2c)
toolchain.  It exposes a single import namespace, `ili2c`, which groups
utilities for working with INTERLIS repositories, the metamodel, and the
parser.

## Features

- `ili2c.ilirepository` – download and cache models from INTERLIS repositories.
- `ili2c.pyili2c.metamodel` – a lightweight Python view of the INTERLIS metamodel.
- `ili2c.pyili2c.parser` – parse INTERLIS 2 transfer descriptions.
- `ili2c.pyili2c.mermaid` – render INTERLIS structures to Mermaid diagrams.

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

## Quick start

### Discover models in an INTERLIS repository

```python
from ili2c.ilirepository import IliRepositoryManager

manager = IliRepositoryManager(repositories=["https://models.interlis.ch/"])
model = manager.find_model("RoadsExgm2ien", schema_language="ili2_4")
print(model.name, model.version)
for dependency in model.dependencies:
    print("requires", dependency)
```

### Download a model file

```python
from pathlib import Path
from ili2c.ilirepository import IliRepositoryManager

manager = IliRepositoryManager(repositories=["https://models.interlis.ch/"])
path = Path(manager.get_model_file("DM01AVCH24LV95D", schema_language="ili2_4"))
print(path.read_text()[:200])
```

### Parse a transfer description

```python
from ili2c.pyili2c.parser import parse
from ili2c.pyili2c.mermaid import render

with open("path/to/model.ili", "r", encoding="utf8") as fh:
    transfer_description = parse(fh.read())

print(f"Parsed {len(transfer_description.models)} models")
print(render(transfer_description))
```

Once parsed you can iterate through the INTERLIS structure using the
metamodel helpers.  The example below prints every model, topic and class
found in the transfer description, along with the attribute names defined on
each class:

```python
for model in transfer_description.getModels():
    print("Model", model.getName())
    for topic in model.getTopics():
        print("  Topic", topic.getName())
        for cls in topic.getClasses():
            attribute_names = [attr.getName() for attr in cls.getAttributes()]
            print("    Class", cls.getName(), "attributes:", ", ".join(attribute_names))
```

## Repository layout

```
python/
├── ili2c/                # Python module published to PyPI
│   ├── ilirepository/    # Repository client utilities
│   └── pyili2c/          # Metamodel, parser, and visualisation helpers
├── tests/                # Pytest suite for the module
├── pyproject.toml        # PEP 621 metadata and build configuration
├── setup.cfg             # Legacy setuptools configuration
└── setup.py              # Compatibility entry point for build backends
```

Additional developer documentation is available in
[`DEVELOPMENT.md`](DEVELOPMENT.md).
