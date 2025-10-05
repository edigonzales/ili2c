import sys
from pathlib import Path

# Ensure the ``python`` package directory is importable when running tests from the
# repository root.
PYTHON_DIR = Path(__file__).resolve().parents[1]
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))
