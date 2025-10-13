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
path = Path(manager.get_model_file("DMAV_Grundstuecke_V1_0", schema_language="ili2_4"))
print(path.read_text()[:200])
```

### How repository caching works

The repository helpers mirror HTTP repositories onto the local file system via
`RepositoryCache`.  The cache stores two kinds of artefacts:

- `ilimodels.xml` index files for each configured repository.  Metadata requests
  such as `IliRepositoryManager.find_model` ask `RepositoryAccess` to retrieve
  the repository index.  `RepositoryAccess` resolves the index by calling
  `RepositoryCache.fetch(repository_uri, "ilimodels.xml", meta_ttl)`, which
  downloads the XML once and reuses the local copy until the metadata
  time-to-live (default: 24 hours) expires.
- `ilisite.xml` repository graph files.  The manager walks repositories in
  breadth-first order and therefore calls `RepositoryAccess.get_connected_repositories`
  for each site.  The helper downloads and caches the `ilisite.xml` file in the
  same way as the model index.
- Individual model files.  When `IliRepositoryManager.get_model_file` is
  invoked, `RepositoryAccess.fetch_model_file` delegates to
  `RepositoryCache.fetch(metadata.repository_uri, metadata.relative_path,
  model_ttl, metadata.md5)`.  The cache saves the model under the repository
  folder and honours the model TTL (default: seven days) and MD5 checksum when
  deciding whether to re-download the file.

`RepositoryCache` maps each repository URL to a dedicated directory inside the
cache root (`$ILI_CACHE` or `~/.pyilicache`).  For HTTP repositories it sanitises
path components to create safe file names (or uses MD5 hashes when the
`ILI_CACHE_FILENAME=MD5` environment variable is set).  When asked to fetch a
resource it:

1. Checks whether a cached file already exists.
2. Validates the TTL and optional MD5 checksum.
3. Downloads the remote file with `urllib.request.urlopen` if the cache entry is
   missing, expired or fails the checksum.
4. Returns the local `Path` to the cached file for subsequent consumers.

The following sequence diagram illustrates `IliRepositoryManager.get_model_file`:

```mermaid
sequenceDiagram
    actor User
    participant Manager as IliRepositoryManager
    participant Access as RepositoryAccess
    participant Cache as RepositoryCache
    participant Repo as INTERLIS Repository

    User->>Manager: get_model_file(name)
    loop Repositories (breadth-first)
        Manager->>Access: get_models(repository)
        Access->>Cache: fetch("ilimodels.xml", ttl=meta_ttl)
        alt Cache miss or expired entry
            Cache->>Repo: HTTP GET ilimodels.xml
            Repo-->>Cache: Repository index
        else Cached entry valid
            Note right of Cache: Reuse cached metadata
        end
        Cache-->>Access: Path to ilimodels.xml
        Access-->>Manager: ModelMetadata*
        Manager->>Access: get_connected_repositories(repository)
        Access->>Cache: fetch("ilisite.xml", ttl=meta_ttl)
        alt Cache miss or expired entry
            Cache->>Repo: HTTP GET ilisite.xml
            Repo-->>Cache: Repository graph
        else Cached entry valid
            Note right of Cache: Reuse cached graph
        end
        Cache-->>Access: Path to ilisite.xml
        Access-->>Manager: Connected URIs
    end
    Manager->>Access: fetch_model_file(metadata, ttl=model_ttl)
    Access->>Cache: fetch(metadata.relative_path, ttl=model_ttl, md5)
    alt Cache miss or expired entry
        Cache->>Repo: HTTP GET model file
        Repo-->>Cache: .ili content
    else Cached entry valid
        Note right of Cache: Reuse cached model
    end
    Access-->>Manager: Path
    Manager-->>User: Local path string
```

Only the requested model file is downloaded.  Imported models are listed in the
`ModelMetadata.dependencies` collection and can be fetched on demand by calling
`get_model_file` for each dependency.  Any repositories linked through
`ilisite.xml` files are traversed in breadth-first order, and their metadata and
repository graph documents are cached alongside downloaded models.

### Parse a transfer description

```python
import logging
from pathlib import Path

from ili2c.pyili2c.parser import ParserSettings, parse
from ili2c.pyili2c.mermaid import render

logging.basicConfig(level=logging.INFO)

model_path = Path("path/to/model.ili")
transfer_description = parse(model_path)

print(f"Parsed {len(transfer_description.models)} models")
print(render(transfer_description))
```

`parse` accepts a `ParserSettings` instance that controls how imported models
are resolved.  The parser searches the current model directory by default and
falls back to the standard repositories listed in the default ILIDIRS string,
`"%ILI_DIR;https://models.interlis.ch"`.  Imported models are first resolved next
to the referencing model, then across any additional directories from `ILIDIRS`,
and finally via `IliRepositoryManager`, which walks remote repositories in
breadth-first order using their `ilisite.xml` links.  Downloaded metadata and
model files are cached on the local file system, while models discovered through
`%ILI_DIR` entries are read directly without being mirrored.  To override the
lookup paths you can adjust the ILIDIRS configuration before invoking the
parser:

```python
from pathlib import Path

from ili2c.pyili2c.parser import ParserSettings, parse

settings = ParserSettings()
settings.set_ilidirs("%ILI_DIR;https://models.interlis.ch;https://example.com/models")

transfer_description = parse(Path("path/to/model.ili"), settings=settings)
```

### Enable parser logging

The parser emits diagnostic messages via Python's standard logging framework
under the `ili2c.pyili2c.parser` logger.  Configure logging before invoking
`parse` to see the progress information:

```python
import logging
from pathlib import Path

from ili2c.pyili2c.parser import parse

logging.basicConfig(level=logging.INFO)

model_path = Path("path/to/model.ili")
parse(model_path)
```

You can customise the output format or log level by adjusting the
`logging.basicConfig` call or by configuring handlers on the
`ili2c.pyili2c.parser` logger directly.

Once parsed you can iterate through the INTERLIS structure using the metamodel
helpers.  The example below prints every model, topic and class found in the
transfer description, along with the attribute names defined on each class:

```python
for model in transfer_description.getModels():
    print("Model", model.getName())
    for topic in model.getTopics():
        print("  Topic", topic.getName())
        for cls in topic.getClasses():
            attribute_names = [attr.getName() for attr in cls.getAttributes()]
            print("    Class", cls.getName(), "attributes:", ", ".join(attribute_names))

```

### Understanding `Model` helpers

The Python metamodel mirrors the structure of the Java implementation quite
closely.  `Model` inherits from the generic container base class and therefore
exposes helper methods only where they are broadly useful—such as `getTopics`,
which is simply a convenience wrapper.  Model-level classes (for example,
tables or structures declared outside a topic) are still attached directly to
the model container and can be retrieved through
`model.elements_of_type(Table)` or any other `elements_of_type(...)` query.
Because the generic API already covers this access pattern, there is no
dedicated `Model.getClasses()` helper.

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
