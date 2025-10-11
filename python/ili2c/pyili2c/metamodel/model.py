"""Model related container classes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .element import Container


@dataclass
class Model(Container):
    name: str = ""
    file_name: Optional[str] = None
    schema_version: Optional[str] = None
    schema_language: Optional[str] = None

    def __post_init__(self) -> None:
        self.setName(self.name)

    def getFileName(self) -> Optional[str]:
        return self.file_name

    def setFileName(self, name: Optional[str]) -> None:
        self.file_name = name

    def getSchemaVersion(self) -> Optional[str]:  # noqa: N802 - Java style
        return self.schema_version

    def setSchemaVersion(self, version: Optional[str]) -> None:
        self.schema_version = version

    def getSchemaLanguage(self) -> Optional[str]:  # noqa: N802 - Java style
        return self.schema_language

    def setSchemaLanguage(self, language: Optional[str]) -> None:
        self.schema_language = language

    def add_topic(self, topic: "Topic") -> None:
        self.add(topic)

    # Java-style alias
    def addTopic(self, topic: "Topic") -> None:  # noqa: N802 - Java naming
        self.add_topic(topic)

    def getTopics(self) -> list["Topic"]:
        return self.elements_of_type(Topic)

    @property
    def topics(self) -> list["Topic"]:
        return self.getTopics()


@dataclass
class DataModel(Model):
    """Specialised model that corresponds to INTERLIS data models."""


@dataclass
class Topic(Container):
    name: str = ""
    viewables_public: bool = True

    def __post_init__(self) -> None:
        self.setName(self.name)

    def add_viewable(self, viewable: "Viewable") -> None:
        self.add(viewable)

    def add_class(self, table: "Table") -> None:
        self.add_viewable(table)

    def addViewable(self, viewable: "Viewable") -> None:  # noqa: N802
        self.add_viewable(viewable)

    def addClass(self, table: "Table") -> None:  # noqa: N802
        self.add_class(table)

    def getClasses(self) -> list["Table"]:
        return self.elements_of_type(Table)

    @property
    def classes(self) -> list["Table"]:
        return self.getClasses()

    def isViewablesPublic(self) -> bool:
        return self.viewables_public


# Late imports to avoid cycles
from .viewable import Table, Viewable  # noqa: E402  pylint: disable=wrong-import-position

