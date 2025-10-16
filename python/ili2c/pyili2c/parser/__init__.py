"""INTERLIS parser entry points."""

from .._vendor import ensure_antlr4_runtime

ensure_antlr4_runtime()

from .core import ParserSettings, parse  # noqa: E402,F401

__all__ = ["ParserSettings", "parse"]
