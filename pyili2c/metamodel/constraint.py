"""Constraint placeholder."""
from __future__ import annotations

from dataclasses import dataclass

from .element import Element


@dataclass
class Constraint(Element):
    expression: str | None = None
    mandatory: bool = False

    def isMandatory(self) -> bool:
        return self.mandatory

    def setMandatory(self, mandatory: bool) -> None:
        self.mandatory = mandatory
