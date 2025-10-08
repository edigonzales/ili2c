"""Public Python API for the ili2c toolkit."""

from .ilirepository import IliRepositoryManager, ModelMetadata  # re-export

__all__ = [
    "IliRepositoryManager",
    "ModelMetadata",
]
