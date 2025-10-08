"""Data structures shared across the INTERLIS repository helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin


def _normalise_repository_uri(uri: str) -> str:
    if not uri:
        return uri
    if not uri.endswith("/"):
        return uri + "/"
    return uri


@dataclass
class ModelMetadata:
    """Metadata about a single INTERLIS model."""

    name: str
    schema_language: str
    relative_path: str
    version: str
    repository_uri: str
    md5: Optional[str] = None
    precursor_version: Optional[str] = None
    browse_only: bool = False
    dependencies: List[str] = field(default_factory=list)
    version_comment: Optional[str] = None
    issuer: Optional[str] = None
    technical_contact: Optional[str] = None
    further_information: Optional[str] = None
    further_metadata: Optional[str] = None
    name_language: Optional[str] = None
    publishing_date: Optional[str] = None
    original: Optional[str] = None
    derived_models: List[str] = field(default_factory=list)
    followup_models: List[str] = field(default_factory=list)
    known_wms: List[str] = field(default_factory=list)
    known_wfs: List[str] = field(default_factory=list)
    known_portal: List[str] = field(default_factory=list)
    title: Optional[str] = None
    short_description: Optional[str] = None
    tags: Optional[str] = None

    def __post_init__(self) -> None:
        self.repository_uri = _normalise_repository_uri(self.repository_uri)
        if self.md5:
            self.md5 = self.md5.lower()
        if self.precursor_version:
            self.precursor_version = self.precursor_version.strip() or None

    @property
    def relative_parts(self) -> List[str]:
        parts: List[str] = []
        for part in self.relative_path.split("/"):
            if not part or part == ".":
                continue
            if part == "..":
                # The repository metadata should never ask to traverse upwards.
                # Ignore the component to avoid escaping the cache folder.
                continue
            parts.append(part)
        return parts

    @property
    def full_url(self) -> str:
        return urljoin(self.repository_uri, "/".join(self.relative_parts))

    def with_repository(self, repository_uri: str) -> "ModelMetadata":
        data = self.__dict__.copy()
        data["repository_uri"] = repository_uri
        return ModelMetadata(**data)
