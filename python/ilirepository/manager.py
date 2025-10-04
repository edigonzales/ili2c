"""High level facade mirroring the Java ``IliManager`` logic."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Iterable, List, Optional

from .cache import RepositoryCache
from .models import ModelMetadata
from .repository import RepositoryAccess

logger = logging.getLogger(__name__)


class IliRepositoryManager:
    """A small Pythonic port of ``ch.interlis.ilirepository.IliManager``."""

    def __init__(
        self,
        repositories: Optional[Iterable[str]] = None,
        cache: Optional[RepositoryCache] = None,
        meta_ttl: float = 86400.0,
        model_ttl: float = 7 * 24 * 3600.0,
    ) -> None:
        self.repositories = list(repositories or [])
        self.cache = cache or RepositoryCache()
        self.access = RepositoryAccess(self.cache, meta_ttl=meta_ttl)
        self.model_ttl = model_ttl

    def set_repositories(self, repositories: Iterable[str]) -> None:
        self.repositories = list(repositories)

    def list_models(self, name: Optional[str] = None) -> List[ModelMetadata]:
        result: List[ModelMetadata] = []
        for repository in self.repositories:
            metadata = self.access.get_models(repository)
            if name is None:
                result.extend(metadata)
            else:
                result.extend(m for m in metadata if m.name == name)
        return result

    def find_model(
        self, name: str, schema_language: Optional[str] = None
    ) -> Optional[ModelMetadata]:
        candidates = []
        for repository in self.repositories:
            for metadata in self.access.get_models(repository):
                if metadata.name != name:
                    continue
                if schema_language and metadata.schema_language != schema_language:
                    continue
                candidates.append(metadata)
        if not candidates:
            return None
        if schema_language is None:
            grouped = defaultdict(list)
            for metadata in candidates:
                grouped[metadata.schema_language].append(metadata)
            best_per_schema = [self._pick_preferred(group) for group in grouped.values()]
            return self._pick_preferred(best_per_schema)
        return self._pick_preferred(candidates)

    def get_model_file(
        self, name: str, schema_language: Optional[str] = None
    ) -> Optional[str]:
        metadata = self.find_model(name, schema_language=schema_language)
        if metadata is None:
            return None
        path = self.access.fetch_model_file(metadata, ttl=self.model_ttl)
        if path is None:
            return None
        return str(path)

    @staticmethod
    def _pick_preferred(models: Iterable[ModelMetadata]) -> ModelMetadata:
        def key(metadata: ModelMetadata):
            return (
                _parse_date(metadata.publishing_date) or _parse_date(metadata.version) or datetime.min,
                metadata.version,
            )

        return sorted(models, key=key)[-1]


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
