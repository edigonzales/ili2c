"""Python utilities to interact with INTERLIS model repositories."""

from .manager import IliRepositoryManager
from .models import ModelMetadata

__all__ = ["IliRepositoryManager", "ModelMetadata"]
