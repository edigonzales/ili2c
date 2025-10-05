# ili2c - The INTERLIS Compiler
Checks the syntactical correctness of an [INTERLIS](https://www.interlis.ch/content/index.php?language=e "Interlis - The tool to describe, integrate and coordinate geodata.") data model.

## Build Status
- master branch [![build status](https://www.travis-ci.org/claeis/ili2c.svg?branch=master)](https://www.travis-ci.org/claeis/ili2c)
- stable branch [![build status](https://www.travis-ci.org/claeis/ili2c.svg?branch=stable)](https://www.travis-ci.org/claeis/ili2c)

## License
ili2c is licensed under the [LGPL](https://www.gnu.org/licenses/lgpl.txt) (Lesser GNU Public License).

## System Configuration
For the current version of ili2c, you will need a JAVA software development kit (JDK) version 1.6 or a more recent version
must be installed on your system. A free version of the JAVA software development kit (JDK) is available [here](http://www.oracle.com/technetwork/java/javase/downloads/index.html) .
Also required is the build tool ant. [Download](http://ant.apache.org) and install it as documented there.

## Installation
In order to install the INTERLIS Compiler, extract the ZIP file into a new directory.

## How to compile it?
To compile the INTERLIS Compiler, change to the newly created directory and enter the following command at the commandline prompt:

- Unix
~~~
ant jar
~~~
- Windows
~~~
ant jar
~~~
To build a binary distribution, use
~~~
ant bindist
~~~

## Python utilities

Python ports of the ili2c metamodel, parser, and repository helpers now live in
the [`python/`](python/) directory. The layout groups the source code and its
pytest suite side by side:

```
python/
├── ilirepository/
├── pyili2c/
└── tests/
```

### Working with uv

[uv](https://docs.astral.sh/uv/) offers a convenient workflow for the Python
codebase. The following commands assume you are in the repository root:

1. Create a virtual environment (stored in `.venv/`):

   ```bash
   uv venv
   ```

2. Activate the environment (Linux/macOS):

   ```bash
   source .venv/bin/activate
   ```

   On Windows PowerShell use:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Install the Python packages (including optional test dependencies):

   ```bash
   uv pip install -e python[test]
   ```

4. Run the test suite:

   ```bash
   uv run pytest
   ```

   `uv run` automatically picks up the `python/pyproject.toml` file and executes
   `pytest` with the configured settings. To run only the repository tests you
   can use `uv run pytest python/tests/test_repository_manager.py`.
