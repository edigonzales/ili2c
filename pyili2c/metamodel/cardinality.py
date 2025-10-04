"""Cardinality helper matching the ili2c API."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Cardinality:
    minimum: int = 1
    maximum: int = 1

    def getMinimum(self) -> int:
        return self.minimum

    def getMaximum(self) -> int:
        return self.maximum

    def setMinimum(self, value: int) -> None:
        self.minimum = value

    def setMaximum(self, value: int) -> None:
        self.maximum = value

