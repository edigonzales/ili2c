"""Function metamodel element."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .domain import Domain
from .element import Element
from .types import Type


@dataclass
class FormalArgument(Element):
    """Represents a function argument in the INTERLIS metamodel."""

    type: Optional[Type | Domain] = None

    def getType(self) -> Optional[Type | Domain]:
        return self.type

    def setType(self, type_: Optional[Type | Domain]) -> None:
        self.type = type_


@dataclass
class Function(Element):
    """Function definition mirroring the ili2c Java API."""

    arguments: List[FormalArgument] = field(default_factory=list)
    return_type: Optional[Type | Domain] = None

    def addArgument(self, argument: FormalArgument) -> None:
        if not isinstance(argument, FormalArgument):
            raise TypeError("expected FormalArgument")
        argument.setContainer(self)
        self.arguments.append(argument)

    def getArguments(self) -> List[FormalArgument]:
        return list(self.arguments)

    def setReturnType(self, type_: Optional[Type | Domain]) -> None:
        self.return_type = type_

    def getReturnType(self) -> Optional[Type | Domain]:
        return self.return_type
