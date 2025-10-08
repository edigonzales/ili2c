"""Foundational metamodel objects shared by all INTERLIS elements."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Type, TypeVar


@dataclass
class Element:
    """Base class for every INTERLIS metamodel element."""

    name: Optional[str] = None
    container: Optional["Container"] = field(default=None, repr=False, compare=False)

    def getName(self) -> Optional[str]:
        """Mirror the Java API naming."""

        return self.name

    def setName(self, name: Optional[str]) -> None:
        self.name = name

    def getContainer(self) -> Optional["Container"]:
        return self.container

    def setContainer(self, container: Optional["Container"]) -> None:
        self.container = container

    def getScopedName(self) -> str:
        """Return the fully qualified scoped name (``Model.Topic.Element``)."""

        parts: List[str] = []
        current: Optional[Element] = self
        while current is not None:
            if current.getName():
                parts.append(current.getName())
            current = current.getContainer()
        return ".".join(reversed(parts))

    def path(self) -> str:
        """Compatibility helper mirroring the earlier prototype API."""

        return self.getScopedName()

    # Java convenience
    def __str__(self) -> str:  # pragma: no cover - debugging helper
        scoped = self.getScopedName()
        return f"{self.__class__.__name__}({scoped or '<unnamed>'})"


T_Element = TypeVar("T_Element", bound="Element")


@dataclass
class Container(Element):
    """Container elements keep an ordered collection of child elements."""

    _elements: List[Element] = field(default_factory=list, init=False, repr=False)

    def __iter__(self) -> Iterator[Element]:
        return iter(self._elements)

    # The Java metamodel exposes ``iterator``.
    def iterator(self) -> Iterator[Element]:
        return self.__iter__()

    def add(self, element: Element) -> None:
        if element is None:
            raise ValueError("container elements cannot add None")
        element.setContainer(self)
        self._elements.append(element)

    def remove(self, element: Element) -> None:
        self._elements.remove(element)
        element.setContainer(None)

    def elements(self) -> List[Element]:
        return list(self._elements)

    def elements_of_type(self, cls: Type[T_Element]) -> List[T_Element]:
        return [e for e in self._elements if isinstance(e, cls)]

    def clear(self) -> None:
        for element in list(self._elements):
            element.setContainer(None)
        self._elements.clear()
