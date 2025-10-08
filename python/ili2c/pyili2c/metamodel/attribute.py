"""Attribute definitions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .cardinality import Cardinality
from .domain import Domain
from .element import Element
from .types import Type


@dataclass
class AttributeDef(Element):
    domain: Optional[Type | Domain] = None
    cardinality: Optional[Cardinality] = None
    mandatory: bool = False

    def getDomain(self) -> Optional[Type | Domain]:
        return self.domain

    def setDomain(self, domain: Optional[Type | Domain]) -> None:
        self.domain = domain

    def getCardinality(self) -> Optional[Cardinality]:
        return self.cardinality

    def setCardinality(self, card: Optional[Cardinality]) -> None:
        self.cardinality = card

    def isDomainBoolean(self) -> bool:
        domain = self.getDomain()
        if isinstance(domain, Domain):
            return domain.isBoolean()
        if isinstance(domain, Type):
            return domain.isBoolean()
        return False

    def isMandatory(self) -> bool:
        return self.mandatory

    def setMandatory(self, mandatory: bool) -> None:
        self.mandatory = mandatory

