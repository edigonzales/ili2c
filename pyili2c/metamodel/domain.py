"""Domain definitions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .element import Element


@dataclass
class Domain(Element):
    type: Optional["Type"] = None
    extending: Optional["Domain"] = None
    abstract: bool = False
    final: bool = False

    def getType(self) -> Optional["Type"]:
        return self.type

    def setType(self, type_: Optional["Type"]) -> None:
        self.type = type_

    def getExtending(self) -> Optional["Domain"]:
        return self.extending

    def setExtending(self, extending: Optional["Domain"]) -> None:
        self.extending = extending

    def isAbstract(self) -> bool:
        return self.abstract

    def setAbstract(self, abstract: bool) -> None:
        self.abstract = abstract

    def isFinal(self) -> bool:
        return self.final

    def setFinal(self, final: bool) -> None:
        self.final = final

    def isBoolean(self) -> bool:
        if self.type is None:
            return False
        return self.type.isBoolean()


# Circular import
from .types import Type  # noqa: E402  pylint: disable=wrong-import-position

