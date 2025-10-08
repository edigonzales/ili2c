"""Association role definition."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .cardinality import Cardinality
from .element import Element
from .viewable import AbstractClassDef


@dataclass
class RoleDef(Element):
    destination: Optional[AbstractClassDef] = None
    cardinality: Optional[Cardinality] = None
    external: bool = False

    def getDestination(self) -> Optional[AbstractClassDef]:
        return self.destination

    def setDestination(self, dest: Optional[AbstractClassDef]) -> None:
        self.destination = dest

    def getCardinality(self) -> Optional[Cardinality]:
        return self.cardinality

    def setCardinality(self, card: Optional[Cardinality]) -> None:
        self.cardinality = card

    def isExternal(self) -> bool:
        return self.external

    def setExternal(self, external: bool) -> None:
        self.external = external

