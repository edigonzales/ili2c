"""Access helpers for INTERLIS repositories."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlparse

from .cache import FetchError, RepositoryCache
from .models import ModelMetadata, _normalise_repository_uri

logger = logging.getLogger(__name__)


_NAMESPACE = "{http://www.interlis.ch/INTERLIS2.3}"
_MODEL_TAGS = (
    f"{_NAMESPACE}IliRepository09.RepositoryIndex.ModelMetadata",
    f"{_NAMESPACE}IliRepository20.RepositoryIndex.ModelMetadata",
)
_VALUE_TAG = f"{_NAMESPACE}value"
_BOOL_TRUE = {"true", "1", "yes"}


class RepositoryAccess:
    """Read metadata and files from model repositories."""

    def __init__(self, cache: Optional[RepositoryCache] = None, meta_ttl: float = 86400.0) -> None:
        self.cache = cache or RepositoryCache()
        self.meta_ttl = meta_ttl
        self._model_cache: Dict[str, List[ModelMetadata]] = {}
        self._site_cache: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Metadata access

    def get_models(self, repository_uri: str) -> List[ModelMetadata]:
        repository_uri = _normalise_repository_uri(repository_uri)
        if repository_uri in self._model_cache:
            return self._model_cache[repository_uri]
        parsed = urlparse(repository_uri)
        if parsed.scheme in {"http", "https"}:
            try:
                metadata = self._read_remote_models(repository_uri)
            except FetchError as exc:  # pragma: no cover - defensive logging
                logger.warning(
                    "Failed to fetch ilimodels.xml from %s (url=%s): %s",
                    repository_uri,
                    exc.url,
                    exc,
                )
                metadata = []
        else:
            metadata = self._read_directory_models(Path(repository_uri))
        self._model_cache[repository_uri] = metadata
        return metadata

    def get_connected_repositories(self, repository_uri: str) -> List[str]:
        repository_uri = _normalise_repository_uri(repository_uri)
        if repository_uri in self._site_cache:
            return self._site_cache[repository_uri]

        parsed = urlparse(repository_uri)
        locations: List[str] = []
        if parsed.scheme in {"http", "https"}:
            try:
                path = self.cache.fetch(repository_uri, "ilisite.xml", self.meta_ttl)
            except FetchError as exc:  # pragma: no cover - defensive logging
                logger.warning(
                    "Failed to fetch ilisite.xml from %s (url=%s): %s",
                    repository_uri,
                    exc.url,
                    exc,
                )
                path = None
        else:
            base = Path(repository_uri)
            if parsed.scheme == "file":
                base = Path(parsed.path)
            path = base / "ilisite.xml"
            if not path.exists():
                path = None
        if path is not None:
            try:
                locations = _parse_repository_locations(path)
            except ET.ParseError as exc:
                logger.warning("Failed to parse ilisite.xml from %s: %s", repository_uri, exc)
                locations = []
        self._site_cache[repository_uri] = locations
        return locations

    def _read_remote_models(self, repository_uri: str) -> List[ModelMetadata]:
        index_path = self.cache.fetch(repository_uri, "ilimodels.xml", self.meta_ttl)
        if index_path is None:
            return []
        try:
            models = list(_parse_model_index(index_path, repository_uri))
        except ET.ParseError as exc:
            logger.warning("Failed to parse ilimodels.xml from %s: %s", repository_uri, exc)
            return []
        return _latest_versions(models)

    def _read_directory_models(self, path: Path) -> List[ModelMetadata]:
        if not path.is_dir():
            return []
        models: List[ModelMetadata] = []
        for ili_path in path.rglob("*.ili"):
            rel = ili_path.relative_to(path).as_posix()
            metadata = ModelMetadata(
                name=ili_path.stem,
                schema_language="unknown",
                relative_path=rel,
                version="",
                repository_uri=str(path.resolve()),
            )
            models.append(metadata)
        return models

    # ------------------------------------------------------------------
    # File access

    def fetch_model_file(
        self, metadata: ModelMetadata, ttl: float
    ) -> Optional[Path]:
        return self.cache.fetch(metadata.repository_uri, metadata.relative_path, ttl, metadata.md5)


# ----------------------------------------------------------------------
# XML parsing helpers


def _parse_model_index(path: Path, repository_uri: str) -> Iterable[ModelMetadata]:
    tree = ET.parse(path)
    root = tree.getroot()
    for element in root.iter():
        if element.tag not in _MODEL_TAGS:
            continue
        data = _parse_model_metadata(element, repository_uri)
        if data is not None:
            yield data


def _parse_model_metadata(element: ET.Element, repository_uri: str) -> Optional[ModelMetadata]:
    text = _child_text
    name = text(element, "Name")
    schema_language = text(element, "SchemaLanguage")
    file_path = text(element, "File")
    version = text(element, "Version", default="")
    if not name or not schema_language or not file_path:
        return None
    metadata = ModelMetadata(
        name=name,
        schema_language=schema_language,
        relative_path=file_path,
        version=version,
        repository_uri=repository_uri,
        md5=text(element, "md5"),
        precursor_version=text(element, "precursorVersion"),
        browse_only=_parse_bool(text(element, "browseOnly")),
        version_comment=text(element, "versionComment"),
        issuer=text(element, "Issuer"),
        technical_contact=text(element, "technicalContact"),
        further_information=text(element, "furtherInformation"),
        further_metadata=text(element, "furtherMetadata"),
        name_language=text(element, "NameLanguage"),
        publishing_date=text(element, "publishingDate"),
        original=text(element, "original"),
        title=text(element, "Title"),
        short_description=text(element, "shortDescription"),
        tags=text(element, "Tags"),
    )
    for dep in element.findall(f"{_NAMESPACE}dependsOnModel/*"):
        value = dep.findtext(_VALUE_TAG)
        if value:
            metadata.dependencies.append(value.strip())
    for dep in element.findall(f"{_NAMESPACE}derivedModel/*"):
        value = dep.findtext(_VALUE_TAG)
        if value:
            metadata.derived_models.append(value.strip())
    for dep in element.findall(f"{_NAMESPACE}followupModel/*"):
        value = dep.findtext(_VALUE_TAG)
        if value:
            metadata.followup_models.append(value.strip())
    for dep in element.findall(f"{_NAMESPACE}knownWMS/*"):
        value = dep.findtext(_VALUE_TAG)
        if value:
            metadata.known_wms.append(value.strip())
    for dep in element.findall(f"{_NAMESPACE}knownWFS/*"):
        value = dep.findtext(_VALUE_TAG)
        if value:
            metadata.known_wfs.append(value.strip())
    for dep in element.findall(f"{_NAMESPACE}knownPortal/*"):
        value = dep.findtext(_VALUE_TAG)
        if value:
            metadata.known_portal.append(value.strip())
    return metadata


def _child_text(element: ET.Element, name: str, default: Optional[str] = None) -> Optional[str]:
    child = element.find(f"{_NAMESPACE}{name}")
    if child is None or child.text is None:
        return default
    return child.text.strip() or default


def _parse_bool(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in _BOOL_TRUE


def _parse_repository_locations(path: Path) -> List[str]:
    tree = ET.parse(path)
    root = tree.getroot()
    locations: List[str] = []
    for element in root.iter():
        if not element.tag.endswith("RepositoryLocation_"):
            continue
        value = element.findtext(_VALUE_TAG)
        if not value:
            continue
        value = value.strip()
        if not value:
            continue
        locations.append(_normalise_repository_uri(value))
    return locations


def _latest_versions(models: Iterable[ModelMetadata]) -> List[ModelMetadata]:
    grouped: Dict[str, List[ModelMetadata]] = defaultdict(list)
    for model in models:
        grouped[model.name].append(model)
    result: List[ModelMetadata] = []
    for versions in grouped.values():
        by_schema: Dict[str, List[ModelMetadata]] = defaultdict(list)
        for metadata in versions:
            by_schema[metadata.schema_language].append(metadata)
        for schema_versions in by_schema.values():
            latest = _resolve_latest_version(schema_versions)
            if latest is not None:
                result.append(latest)
    return result


def _resolve_latest_version(models: List[ModelMetadata]) -> Optional[ModelMetadata]:
    chain_candidates = [m for m in models if not m.browse_only]
    if not chain_candidates:
        return None
    by_version = {m.version: m for m in chain_candidates if m.version}
    start_candidates = [m for m in chain_candidates if not m.precursor_version]
    current = None
    if start_candidates:
        current = _pick_preferred(start_candidates)
    elif by_version:
        current = _pick_preferred(list(by_version.values()))
    else:
        current = chain_candidates[0]
    visited = set()
    last = current
    while current and current.version and current.version not in visited:
        visited.add(current.version)
        next_candidates = [m for m in chain_candidates if m.precursor_version == current.version]
        if not next_candidates:
            break
        current = _pick_preferred(next_candidates)
        last = current
    return last


def _pick_preferred(models: List[ModelMetadata]) -> ModelMetadata:
    def sort_key(metadata: ModelMetadata) -> tuple:
        return (
            _parse_date(metadata.publishing_date) or _parse_date(metadata.version) or datetime.min,
            metadata.version,
        )

    return sorted(models, key=sort_key)[-1]


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
