"""Vendor helpers for optional third-party dependencies."""
from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys
from types import ModuleType

_VENDOR_ROOT = Path(__file__).resolve().parent


def ensure_antlr4_runtime() -> ModuleType:
    """Ensure the ``antlr4`` runtime is importable.

    If the runtime is not available in the Python environment, fall back to the
    vendored copy that ships with the project.  The vendored package matches the
    version used to generate the parser (ANTLR 4.13.2).
    """

    try:
        return import_module("antlr4")
    except ModuleNotFoundError as exc:
        if exc.name != "antlr4":
            raise
        vendor_dir = _VENDOR_ROOT
        if str(vendor_dir) not in sys.path:
            sys.path.insert(0, str(vendor_dir))
        return import_module("antlr4")
