"""High level facade mirroring the Java ``IliManager`` logic."""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from datetime import datetime
from typing import Iterable, Iterator, List, Optional, Set

from .cache import RepositoryCache
from .models import ModelMetadata, _normalise_repository_uri
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
        for repository in self._iter_repositories():
            metadata = self.access.get_models(repository)
            if name is None:
                result.extend(metadata)
            else:
                result.extend(m for m in metadata if m.name == name)
        return result

    def find_model(
        self, name: str, schema_language: Optional[str] = None
    ) -> Optional[ModelMetadata]:
        if schema_language is not None:
            return self._find_with_schema(name, schema_language)

        candidates = []
        for repository in self._iter_repositories():
            for metadata in self.access.get_models(repository):
                if metadata.name != name:
                    continue
                candidates.append(metadata)
        if not candidates:
            return None
        grouped = defaultdict(list)
        for metadata in candidates:
            grouped[metadata.schema_language].append(metadata)
        best_per_schema = [self._pick_preferred(group) for group in grouped.values()]
        return self._pick_preferred(best_per_schema)

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

    def _iter_repositories(self) -> Iterator[str]:
        visited: Set[str] = set()
        queue: deque[str] = deque(
            _normalise_repository_uri(uri) for uri in self.repositories if uri
        )
        while queue:
            repository = queue.popleft()
            if not repository or repository in visited:
                continue
            visited.add(repository)
            for child in self.access.get_connected_repositories(repository):
                child_norm = _normalise_repository_uri(child)
                if child_norm and child_norm not in visited:
                    queue.append(child_norm)
            yield repository

    @staticmethod
    def _pick_preferred(models: Iterable[ModelMetadata]) -> ModelMetadata:
        def key(metadata: ModelMetadata):
            return (
                _parse_date(metadata.publishing_date) or _parse_date(metadata.version) or datetime.min,
                metadata.version,
            )

        return sorted(models, key=key)[-1]

    def _find_with_schema(self, name: str, schema_language: str) -> Optional[ModelMetadata]:
        for repository in self._iter_repositories():
            matches = [
                metadata
                for metadata in self.access.get_models(repository)
                if metadata.name == name and metadata.schema_language == schema_language
            ]
            if not matches:
                continue
            return self._pick_preferred(matches)
        return None


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
