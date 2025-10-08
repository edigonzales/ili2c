"""Subset of the INTERLIS predefined model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from .domain import Domain
from .model import DataModel
from .types import FormattedType


@dataclass
class PredefinedModel(DataModel):
    INTERLIS: ClassVar[str] = "INTERLIS"
    _instance: ClassVar["PredefinedModel" | None] = None

    def __post_init__(self) -> None:
        self.setName(self.INTERLIS)
        self.XmlDate = Domain("XmlDate")
        self.XmlDateTime = Domain("XmlDateTime")
        self.XmlTime = Domain("XmlTime")

        self.XmlDate.setType(FormattedType(defined_base_domain=self.XmlDate))
        self.XmlDateTime.setType(FormattedType(defined_base_domain=self.XmlDateTime))
        self.XmlTime.setType(FormattedType(defined_base_domain=self.XmlTime))

        for domain in (self.XmlDate, self.XmlDateTime, self.XmlTime):
            self.add(domain)

    @classmethod
    def getInstance(cls) -> "PredefinedModel":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

